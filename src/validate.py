"""
Module: src/validate.py
Purpose: Validate standard status (Active, Superseded, Withdrawn) and resolve explicit supersedence relationships.

Adheres to strict evidence constraints:
- Only reports a successor when explicitly supported by source evidence in the database.
- Does not invent successor standards.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import re
import sqlite3
from src.standards import StandardsDatabase


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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_standard_status(
    standard_identifier: str,
    db: Optional[StandardsDatabase] = None
) -> StandardValidationResult:
    """
    Validates the status of a standard identifier (e.g. 'IS 10611', 'IS 778', 'IS 15000:2024').
    Checks:
    - Active
    - Superseded
    - Withdrawn
    - Explicit SUPERSEDES / SUPERSEDED_BY relationships in standards.db

    If an outdated or superseded standard is queried, retrieves the successor standard
    and authoritative evidence when recorded in our database.
    """
    database = db or StandardsDatabase()
    std_clean = standard_identifier.strip()

    # Extract digits / key identifier (e.g. "10611" from "IS 10611")
    digits_match = re.search(r'\b(?:IS\s*(?:/|\s*)?(?:ISO|IEC)?\s*)?(\d{3,5})\b', std_clean, re.IGNORECASE)
    std_num_digits = digits_match.group(1) if digits_match else std_clean

    with database._get_connection() as conn:
        cursor = conn.cursor()

        # 1. Check if another standard in DB explicitly SUPERSEDES this standard
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
                standard_metadata=None
            )

        # 2. Check direct standard record in standards table
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

            return StandardValidationResult(
                standard_identifier=std_clean,
                is_known=True,
                status=raw_status,
                is_active=is_active,
                successor_standard=successor_std,
                successor_title=None,
                evidence=evidence_str,
                relationship_type="SUPERSEDED_BY" if successor_std else None,
                warning_message=warning_msg,
                standard_metadata=std_data
            )

        # 3. Not found in local database
        return StandardValidationResult(
            standard_identifier=std_clean,
            is_known=False,
            status="Unknown",
            is_active=False,
            successor_standard=None,
            successor_title=None,
            evidence=None,
            relationship_type=None,
            warning_message=f"Standard {std_clean} was not found in the local standards database; requires verification.",
            standard_metadata=None
        )
