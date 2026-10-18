"""
Module: src/validate.py
Purpose: Validate standard status (Active, Superseded, Withdrawn) across the national BIS catalogue and resolve explicit supersedence relationships.

Adheres to strict evidence constraints:
- Only reports a successor when explicitly supported by source evidence in the database.
- Does not invent successor standards.
- Grounded in data/catalogue/bis_catalogue.db for national registry validation.
- Distinguishes FOUND_ACTIVE, FOUND_WITHDRAWN_OR_SUPERSEDED, FOUND_STATUS_UNKNOWN, and NOT_FOUND.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
import re
import sqlite3
from src.standards import StandardsDatabase
from src.catalogue.access import get_national_catalogue, CatalogueStandardMatch


@dataclass
class StandardValidationResult:
    standard_identifier: str
    is_known: bool
    status: str                             # "Active", "Superseded", "Withdrawn", "Unknown"
    is_active: bool
    successor_standard: Optional[str] = None
    successor_title: Optional[str] = None
    evidence: Optional[str] = None
    relationship_type: Optional[str] = None
    warning_message: Optional[str] = None
    standard_metadata: Optional[Dict[str, Any]] = None
    # Phase 24 National Catalogue Integration fields:
    recognition_state: str = "NOT_FOUND"    # FOUND_ACTIVE, FOUND_WITHDRAWN_OR_SUPERSEDED, FOUND_STATUS_UNKNOWN, NOT_FOUND
    is_catalogue_only: bool = False
    ambiguity_warnings: List[str] = field(default_factory=list)
    catalogue_record: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_standard_status(
    standard_identifier: str,
    db: Optional[StandardsDatabase] = None
) -> StandardValidationResult:
    """
    Validates the status of a standard identifier (e.g. 'IS 10611', 'IS 778', 'IS 8112', 'IS 15000:2024').
    
    Resolution Order:
    1. Check explicit SUPERSEDES relationships in curated standards.db.
    2. Check direct record in curated standards.db (preserves rich scope clauses).
    3. Query national BIS catalogue (data/catalogue/bis_catalogue.db, 35k+ records).
    4. If absent from both: mark NOT_FOUND / is_known=False.
    """
    database = db or StandardsDatabase()
    std_clean = standard_identifier.strip()
    national_cat = get_national_catalogue()

    # Extract digits / key identifier (e.g. "10611" from "IS 10611")
    digits_match = re.search(r'\b(?:IS\s*(?:/|\s*)?(?:ISO|IEC)?\s*)?(\d{3,5})\b', std_clean, re.IGNORECASE)
    std_num_digits = digits_match.group(1) if digits_match else std_clean

    with database._get_connection() as conn:
        cursor = conn.cursor()

        # 1. Check if another standard in curated DB explicitly SUPERSEDES this standard
        cursor.execute("""
        SELECT s.standard_id, s.standard_number, s.year, s.full_title, s.status,
               r.relationship_type, r.evidence, r.target_standard
        FROM standard_relationships r
        JOIN standards s ON s.standard_id = r.source_standard_id
        WHERE r.relationship_type = 'SUPERSEDES' AND (
            r.target_standard LIKE ? OR r.target_standard LIKE ?
        )
        """, (f"%{std_clean}%", f"%{std_num_digits}%"))
        superseding_match = cursor.fetchone()

        if superseding_match:
            row = dict(superseding_match)
            successor_repr = f"{row['standard_number']} : {row['year']}" if row['year'] else row['standard_number']
            return StandardValidationResult(
                standard_identifier=std_clean,
                is_known=True,
                status="Superseded",
                is_active=False,
                successor_standard=successor_repr,
                successor_title=row['full_title'],
                evidence=row['evidence'],
                relationship_type="SUPERSEDED_BY",
                warning_message=(
                    f"CRITICAL: {std_clean} is SUPERSEDED by {successor_repr} "
                    f"('{row['full_title']}'). Evidence: {row['evidence']}"
                ),
                standard_metadata=None,
                recognition_state="FOUND_WITHDRAWN_OR_SUPERSEDED",
                is_catalogue_only=False
            )

        # 2. Check direct standard record in curated standards table
        cursor.execute("""
        SELECT * FROM standards
        WHERE standard_id = ? 
           OR standard_number = ? 
           OR original_standard_identifier = ?
           OR standard_number LIKE ?
        """, (std_clean, std_clean, std_clean, f"%{std_num_digits}%"))
        direct_match = cursor.fetchone()

        if direct_match:
            std_data = dict(direct_match)
            raw_status = (std_data.get("status") or "Active").strip()
            is_active = (raw_status.lower() == "active")

            # Check if this standard record has SUPERSEDED_BY relationship outgoing
            cursor.execute("""
            SELECT relationship_type, target_standard, evidence
            FROM standard_relationships
            WHERE source_standard_id = ? AND relationship_type = 'SUPERSEDED_BY'
            """, (std_data["standard_id"],))
            rel = cursor.fetchone()

            successor_std = None
            evidence_str = None
            warning_msg = None

            if rel:
                rel_dict = dict(rel)
                successor_std = rel_dict["target_standard"]
                evidence_str = rel_dict["evidence"]
                warning_msg = f"Standard {std_data['standard_number']} is superseded by {successor_std}."
            elif not is_active:
                warning_msg = f"Standard {std_data['standard_number']} has non-active status: {raw_status}."

            # Lifecycle / Older Edition Check:
            # If an explicit edition year was cited, verify against current active revision year
            ym = re.search(r'\b(19\d\d|20\d\d)\b', std_clean)
            cited_year = int(ym.group(1)) if ym else None
            db_year = std_data.get("year")
            is_older_edition = False

            if cited_year:
                if db_year and cited_year < db_year:
                    is_older_edition = True
                    is_active = False
                    successor_std = f"{std_data['standard_number']} : {db_year}"
                    warning_msg = (
                        f"Cited edition {cited_year} of standard {std_data['standard_number']} is superseded "
                        f"by current active edition {db_year}."
                    )
                elif cited_year <= 2005:
                    is_older_edition = True
                    is_active = False
                    warning_msg = (
                        f"Cited edition {cited_year} of standard {std_data['standard_number']} is an older "
                        f"historical revision requiring technical review for modern revision compliance."
                    )

            rel_type = "OLDER_VERSION" if is_older_edition else ("SUPERSEDED_BY" if successor_std else None)
            recog_state = "FOUND_ACTIVE" if is_active else "FOUND_WITHDRAWN_OR_SUPERSEDED"

            # Optional cross-check against national catalogue for enriched provenance
            cat_match = national_cat.lookup_by_identifier(std_clean)
            ambiguity_warnings = []
            cat_rec = None
            if cat_match:
                cat_rec = cat_match.to_dict()
                if (not is_active) and cat_match.ambiguity_message:
                    ambiguity_warnings.append(cat_match.ambiguity_message)

            return StandardValidationResult(
                standard_identifier=std_clean,
                is_known=True,
                status="Superseded" if (successor_std or is_older_edition) else raw_status,
                is_active=is_active,
                successor_standard=successor_std,
                successor_title=std_data.get("full_title") if is_older_edition else None,
                evidence=evidence_str or (f"Catalogue active edition is {db_year}" if is_older_edition and db_year else None),
                relationship_type=rel_type,
                warning_message=warning_msg,
                standard_metadata=std_data,
                recognition_state=recog_state,
                is_catalogue_only=False,
                ambiguity_warnings=ambiguity_warnings,
                catalogue_record=cat_rec
            )

    # 3. Not found in curated database — Query National BIS Catalogue (35k+ records)
    cat_match = national_cat.lookup_by_identifier(std_clean)
    if cat_match:
        ambiguity_warnings = []
        if cat_match.ambiguity_message:
            ambiguity_warnings.append(cat_match.ambiguity_message)

        cat_status_upper = (cat_match.status or "").strip().upper()

        if cat_status_upper == "ACTIVE":
            recog_state = "FOUND_ACTIVE"
            is_active = True
            disp_status = "Active"
            warning_msg = cat_match.ambiguity_message
        elif cat_status_upper in ["WITHDRAWN", "SUPERSEDED"]:
            recog_state = "FOUND_WITHDRAWN_OR_SUPERSEDED"
            is_active = False
            disp_status = "Withdrawn" if cat_status_upper == "WITHDRAWN" else "Superseded"
            base_warn = f"Standard {cat_match.standard_number} has status '{cat_match.status}' in the national BIS catalogue."
            warning_msg = f"{base_warn} {cat_match.ambiguity_message}" if cat_match.ambiguity_message else base_warn
        else:
            recog_state = "FOUND_STATUS_UNKNOWN"
            is_active = False
            disp_status = "Unknown"
            base_warn = f"Standard {cat_match.standard_number} is registered in the national catalogue, but its active lifecycle status is unclassified/unknown."
            warning_msg = f"{base_warn} {cat_match.ambiguity_message}" if cat_match.ambiguity_message else base_warn

        cat_dict = cat_match.to_dict()
        metadata_dict = {
            "standard_id": cat_match.canonical_id,
            "standard_number": cat_match.standard_number,
            "year": cat_match.year,
            "full_title": cat_match.title,
            "status": disp_status,
            "technical_committee": cat_match.technical_committee,
            "department": cat_match.department,
            "source_url": cat_match.source_url,
            "source": cat_match.source,
            "is_catalogue_only": True,
            "is_active": cat_match.is_active,
            "iso_equivalence": cat_match.iso_equivalence,
        }

        return StandardValidationResult(
            standard_identifier=std_clean,
            is_known=True,
            status=disp_status,
            is_active=is_active,
            successor_standard=None,
            successor_title=None,
            evidence=f"Authoritative national BIS catalogue entry ({cat_match.technical_committee or 'BIS'}); scope text unindexed in local corpus.",
            relationship_type=None,
            warning_message=warning_msg,
            standard_metadata=metadata_dict,
            recognition_state=recog_state,
            is_catalogue_only=True,
            ambiguity_warnings=ambiguity_warnings,
            catalogue_record=cat_dict
        )

    # 4. Absent from both curated standards.db and national bis_catalogue.db
    return StandardValidationResult(
        standard_identifier=std_clean,
        is_known=False,
        status="Unknown",
        is_active=False,
        successor_standard=None,
        successor_title=None,
        evidence=None,
        relationship_type=None,
        warning_message=f"Standard '{std_clean}' was not found in either the national BIS catalogue or the curated standards database; requires verification.",
        standard_metadata=None,
        recognition_state="NOT_FOUND",
        is_catalogue_only=False,
        ambiguity_warnings=[]
    )
