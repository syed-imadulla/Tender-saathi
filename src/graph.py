"""
Module: src/graph.py
Purpose: Lightweight Evidence & Relationship Graph for BIS Standards.

Enforces Milestone 5 constraints:
- Strictly depth = 1 traversal (no speculative multi-hop traversal).
- Deterministic, explainable, SQLite-backed.
- Preserves provenance (VERIFIED, CURATED, INFERRED).
- Evidence propagation constraint: Graph connectivity does NOT automatically mean
  the target standard applies to the tender; items are presented as
  "Related standards to review".
- Preserves explicit relationships only (SUPERSEDES, REFERENCES, CODE_OF_PRACTICE_FOR,
  IDENTICAL_ADOPTION, etc.). Does NOT infer relationships from title similarity or years.
"""

import re
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Set

from src.standards import StandardsDatabase
from src.validate import validate_standard_status, StandardValidationResult


# ---------------------------------------------------------------------------
# Graph Data Models
# ---------------------------------------------------------------------------

@dataclass
class StandardRelationship:
    """Represents a directed evidentiary relationship between two standards."""
    source_standard: str                  # Canonical or display representation of source
    target_standard: str                  # Canonical or display representation of target
    relationship_type: str                # SUPERSEDES, REFERENCES, CODE_OF_PRACTICE_FOR, IDENTICAL_ADOPTION, SUPERSEDED_BY
    evidence: str                         # Verbatim clause / snippet or foreword statement
    provenance: str                       # VERIFIED, CURATED, INFERRED
    source_url: Optional[str] = None      # Portal URL if available
    confidence: float = 1.0               # 0.0 to 1.0
    direction: str = "OUTGOING"           # "OUTGOING" (source -> target) or "INCOMING" (target <- source)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RelatedStandardResult:
    """Represents a related standard discovered via the graph for engineering review."""
    standard_number: str                  # e.g. "IS 2491 : 2024"
    title: str                            # Official or known title
    relationship_type: str                # SUPERSEDES, REFERENCES, CODE_OF_PRACTICE_FOR, etc.
    direction: str                        # "OUTGOING" or "INCOMING"
    lifecycle_status: str                 # "Active", "Superseded", "Withdrawn", "Unknown"
    provenance: str                       # "VERIFIED", "CURATED", "INFERRED"
    evidence_strength: str                # "STRONG", "MODERATE", "WEAK", "NONE"
    evidence_text: str                    # Stored relationship evidence
    source_url: Optional[str] = None
    review_note: str = "Related standard to review"  # Non-authoritative guidance

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Graph Engine
# ---------------------------------------------------------------------------

class StandardsGraph:
    """
    Lightweight, deterministic Evidence & Relationship Graph layer over standards.db.
    Provides depth=1 relationship exploration without speculative hops or LLMs.
    """

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db or StandardsDatabase()

    def _normalize_id(self, identifier: str) -> str:
        """Extracts core digits and prefix for flexible matching."""
        if not identifier:
            return ""
        norm = re.sub(r'\s+', ' ', identifier.strip()).upper()
        return norm

    def _extract_digits(self, identifier: str) -> Optional[str]:
        """Extracts numeric standard code (e.g. '10611' from 'IS 10611:1983')."""
        m = re.search(r'\b\d{3,5}\b', identifier)
        return m.group(0) if m else None

    def get_direct_relationships(
        self,
        standard_identifier: str,
        depth: int = 1
    ) -> List[StandardRelationship]:
        """
        Retrieves all direct explicit relationships for a standard.
        Strictly enforces depth = 1.
        """
        if depth != 1:
            raise ValueError(f"Milestone 5 strictly supports depth = 1. Requested depth: {depth}")

        norm_id = self._normalize_id(standard_identifier)
        digits = self._extract_digits(norm_id)
        relationships: List[StandardRelationship] = []

        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Outgoing from standard_relationships table
            cursor.execute("""
            SELECT s.standard_number AS src_num, s.year AS src_yr, s.verification_status, s.source_url,
                   r.target_standard, r.relationship_type, r.evidence
            FROM standard_relationships r
            JOIN standards s ON s.standard_id = r.source_standard_id
            WHERE s.standard_id = ? OR s.standard_number LIKE ? OR s.standard_id LIKE ?
            """, (norm_id, f"%{norm_id}%", f"%{digits}%" if digits else norm_id))

            for row in cursor.fetchall():
                src_repr = f"{row['src_num']} : {row['src_yr']}" if row['src_yr'] else row['src_num']
                relationships.append(StandardRelationship(
                    source_standard=src_repr,
                    target_standard=row['target_standard'],
                    relationship_type=row['relationship_type'],
                    evidence=row['evidence'],
                    provenance=row['verification_status'] or "CURATED",
                    source_url=row['source_url'],
                    confidence=1.0 if row['verification_status'] == "VERIFIED" else 0.85,
                    direction="OUTGOING"
                ))

            # 2. Outgoing Normative References from standard_references table
            cursor.execute("""
            SELECT s.standard_number AS src_num, s.year AS src_yr, s.verification_status, s.source_url,
                   ref.referenced_standard_number, ref.referenced_year, ref.referenced_title, ref.citing_clause
            FROM standard_references ref
            JOIN standards s ON s.standard_id = ref.standard_id
            WHERE s.standard_id = ? OR s.standard_number LIKE ? OR s.standard_id LIKE ?
            """, (norm_id, f"%{norm_id}%", f"%{digits}%" if digits else norm_id))

            for row in cursor.fetchall():
                src_repr = f"{row['src_num']} : {row['src_yr']}" if row['src_yr'] else row['src_num']
                tgt_repr = f"{row['referenced_standard_number']} : {row['referenced_year']}" if row['referenced_year'] else row['referenced_standard_number']
                clause_info = row['citing_clause'] or "Normative References"
                relationships.append(StandardRelationship(
                    source_standard=src_repr,
                    target_standard=tgt_repr,
                    relationship_type="REFERENCES",
                    evidence=f"Cited under {clause_info} in {src_repr}.",
                    provenance=row['verification_status'] or "VERIFIED",
                    source_url=row['source_url'],
                    confidence=0.95 if row['verification_status'] == "VERIFIED" else 0.80,
                    direction="OUTGOING"
                ))

            # 3. Incoming relationships from standard_relationships table
            # (Where this standard is the target_standard)
            cursor.execute("""
            SELECT s.standard_number AS src_num, s.year AS src_yr, s.verification_status, s.source_url,
                   r.target_standard, r.relationship_type, r.evidence
            FROM standard_relationships r
            JOIN standards s ON s.standard_id = r.source_standard_id
            WHERE r.target_standard LIKE ? OR ( ? != '' AND r.target_standard LIKE ? )
            """, (f"%{norm_id}%", digits or "", f"%{digits}%" if digits else ""))

            for row in cursor.fetchall():
                src_repr = f"{row['src_num']} : {row['src_yr']}" if row['src_yr'] else row['src_num']
                # Avoid self-referencing duplicates
                if src_repr != norm_id:
                    relationships.append(StandardRelationship(
                        source_standard=src_repr,
                        target_standard=row['target_standard'],
                        relationship_type=row['relationship_type'],
                        evidence=row['evidence'],
                        provenance=row['verification_status'] or "CURATED",
                        source_url=row['source_url'],
                        confidence=1.0 if row['verification_status'] == "VERIFIED" else 0.85,
                        direction="INCOMING"
                    ))

            # 4. Incoming references from standard_references table
            cursor.execute("""
            SELECT s.standard_number AS src_num, s.year AS src_yr, s.verification_status, s.source_url,
                   ref.referenced_standard_number, ref.referenced_year, ref.referenced_title, ref.citing_clause
            FROM standard_references ref
            JOIN standards s ON s.standard_id = ref.standard_id
            WHERE ref.referenced_standard_number LIKE ? OR ( ? != '' AND ref.referenced_standard_number LIKE ? )
            """, (f"%{norm_id}%", digits or "", f"%{digits}%" if digits else ""))

            for row in cursor.fetchall():
                src_repr = f"{row['src_num']} : {row['src_yr']}" if row['src_yr'] else row['src_num']
                tgt_repr = f"{row['referenced_standard_number']} : {row['referenced_year']}" if row['referenced_year'] else row['referenced_standard_number']
                if src_repr != norm_id:
                    clause_info = row['citing_clause'] or "Normative References"
                    relationships.append(StandardRelationship(
                        source_standard=src_repr,
                        target_standard=tgt_repr,
                        relationship_type="REFERENCES",
                        evidence=f"Cited as normative reference in {src_repr} ({clause_info}).",
                        provenance=row['verification_status'] or "VERIFIED",
                        source_url=row['source_url'],
                        confidence=0.90 if row['verification_status'] == "VERIFIED" else 0.75,
                        direction="INCOMING"
                    ))

        return relationships

    def get_related_standards(
        self,
        standard_identifier: str,
        limit: int = 10
    ) -> List[RelatedStandardResult]:
        """
        Discovers related standards connected at depth = 1.
        Enforces evidence propagation rule:
        Outputs are labeled as 'Related standards to review', NOT automatically applicable.
        """
        direct_rels = self.get_direct_relationships(standard_identifier, depth=1)
        results: List[RelatedStandardResult] = []
        seen_stds: Set[str] = set()

        id_digits = self._extract_digits(standard_identifier)
        id_norm = self._normalize_id(standard_identifier)

        for rel in direct_rels:
            # For outgoing, related entity is target_standard; for incoming, related entity is source_standard
            related_name = rel.target_standard if rel.direction == "OUTGOING" else rel.source_standard
            clean_name = related_name.strip()
            clean_digits = self._extract_digits(clean_name)
            clean_norm = self._normalize_id(clean_name)

            # Prevent self-references
            if id_digits and clean_digits and id_digits == clean_digits:
                continue
            if id_norm == clean_norm or clean_name in seen_stds:
                continue
            seen_stds.add(clean_name)

            # Resolve metadata and lifecycle of the related standard
            std_info = self._resolve_standard_info(clean_name)

            # Determine evidence strength of the relationship
            # Graph connectivity does NOT independently create STRONG evidence for tender applicability
            if rel.provenance == "VERIFIED":
                ev_strength = "STRONG" if rel.relationship_type in ["SUPERSEDES", "CODE_OF_PRACTICE_FOR"] else "MODERATE"
            elif rel.provenance == "CURATED":
                ev_strength = "MODERATE"
            else:
                ev_strength = "WEAK"

            # Create explanatory review note based on relationship type
            if rel.relationship_type == "SUPERSEDES":
                if rel.direction == "OUTGOING":
                    note = f"Authoritative successor standard supersedes {clean_name}. Review legacy specifications."
                else:
                    note = f"Authoritative replacement standard is {clean_name}. Current cited standard is obsolete."
            elif rel.relationship_type == "REFERENCES":
                if rel.direction == "OUTGOING":
                    note = f"Normative reference cited within primary standard. Review for co-application."
                else:
                    note = f"Primary standard is cited by {clean_name}. Review for broader installation context."
            elif rel.relationship_type == "CODE_OF_PRACTICE_FOR":
                if rel.direction == "OUTGOING":
                    note = f"Laying / civil installation code of practice associated with {clean_name}."
                else:
                    note = f"Product manufacturing standard associated with installation code {clean_name}."
            elif rel.relationship_type == "IDENTICAL_ADOPTION":
                note = f"Identical international standard adoption (ISO/IEC)."
            else:
                note = "Related standard in official BIS catalogue for review."

            results.append(RelatedStandardResult(
                standard_number=clean_name,
                title=std_info["title"],
                relationship_type=rel.relationship_type,
                direction=rel.direction,
                lifecycle_status=std_info["status"],
                provenance=rel.provenance,
                evidence_strength=ev_strength,
                evidence_text=rel.evidence,
                source_url=std_info["source_url"] or rel.source_url,
                review_note=note
            ))

            if len(results) >= limit:
                break

        return results

    def _resolve_standard_info(self, standard_identifier: str) -> Dict[str, Any]:
        """Resolves metadata and lifecycle status for a standard identifier."""
        digits = self._extract_digits(standard_identifier)
        norm = self._normalize_id(standard_identifier)

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT standard_number, year, full_title, status, source_url
            FROM standards
            WHERE standard_id = ? OR standard_number = ? OR ( ? != '' AND standard_number LIKE ? )
            LIMIT 1
            """, (norm, norm, digits or "", f"%{digits}%" if digits else ""))
            row = cursor.fetchone()

            if row:
                return {
                    "title": row["full_title"],
                    "status": row["status"],
                    "source_url": row["source_url"]
                }

        # Fallback to validate_standard_status
        val_res = validate_standard_status(standard_identifier, self.db)
        if val_res.is_known:
            return {
                "title": val_res.successor_title or (val_res.standard_metadata.get("full_title") if val_res.standard_metadata else "Standard in BIS Catalogue"),
                "status": val_res.status,
                "source_url": None
            }

        return {
            "title": "Title not in local index",
            "status": "Unknown",
            "source_url": None
        }

    def explain_relationship(
        self,
        source_identifier: str,
        target_identifier: str
    ) -> Optional[str]:
        """
        Returns a human-readable evidence-grounded explanation of the relationship between two standards.
        """
        rels = self.get_direct_relationships(source_identifier, depth=1)
        tgt_norm = self._normalize_id(target_identifier)
        tgt_digits = self._extract_digits(target_identifier)

        for r in rels:
            r_tgt_norm = self._normalize_id(r.target_standard)
            r_tgt_digits = self._extract_digits(r.target_standard)
            if tgt_norm in r_tgt_norm or (tgt_digits and tgt_digits == r_tgt_digits):
                return (
                    f"Relationship: {r.source_standard} {r.relationship_type} {r.target_standard}. "
                    f"Evidence: \"{r.evidence}\" (Provenance: {r.provenance})."
                )
        return None
