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

import os
import json
import sqlite3
import re
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Set

from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.standards import (
    StandardsDatabase,
    CANONICAL_RELATIONSHIP_TYPES,
    LEGACY_RELATIONSHIP_ALIASES,
    ALLOWED_PROVENANCE_LEVELS,
    PROHIBITED_PROVENANCE_LEVELS,
    RelationshipType,
    normalize_relationship_type,
    StandardRole,
    classify_standard_role
)
from src.validate import validate_standard_status, StandardValidationResult


SUPPORTED_RELATIONSHIP_TYPES = CANONICAL_RELATIONSHIP_TYPES | set(LEGACY_RELATIONSHIP_ALIASES.keys())


# ---------------------------------------------------------------------------
# Graph Data Models
# ---------------------------------------------------------------------------

@dataclass
class StandardRelationship:
    """
    Represents a directed evidentiary relationship between two standards.
    Strictly enforces canonical relationship taxonomy and provenance invariants:
    - Production graph relationships may ONLY use VERIFIED or CURATED provenance.
    - INFERRED provenance is strictly rejected with ValueError.
    - Mandatory fields: source_standard, target_standard, relationship_type, evidence,
      evidence_clause, provenance, confidence, source.
    """
    source_standard: str                  # Canonical or display representation of source
    target_standard: str                  # Canonical or display representation of target
    relationship_type: str                # Typed canonical relationship or legacy alias
    evidence: str                         # Verbatim clause / snippet or foreword statement
    evidence_clause: Optional[str] = None # Clause / section where evidence appears
    provenance: str = "VERIFIED"          # Must strictly be "VERIFIED" or "CURATED"
    confidence: float = 1.0               # 0.0 to 1.0
    source: str = "BSB_EDGE_MANUALLY_VERIFIED" # Official evidentiary source
    source_url: Optional[str] = None      # Portal URL if available
    direction: str = "OUTGOING"           # "OUTGOING" (source -> target) or "INCOMING" (target <- source)

    def __post_init__(self):
        # 1. Enforce non-empty source_standard and target_standard
        if not self.source_standard or not str(self.source_standard).strip():
            raise ValueError("source_standard must be a non-empty string.")
        if not self.target_standard or not str(self.target_standard).strip():
            raise ValueError("target_standard must be a non-empty string.")
        self.source_standard = str(self.source_standard).strip()
        self.target_standard = str(self.target_standard).strip()

        # 2. Enforce non-empty evidence
        if not self.evidence or not str(self.evidence).strip():
            raise ValueError("evidence must be a non-empty string.")
        self.evidence = str(self.evidence).strip()

        # 3. Enforce strict provenance invariant: ONLY VERIFIED or CURATED; INFERRED is rejected
        prov_norm = str(self.provenance or "").strip().upper()
        if prov_norm not in ALLOWED_PROVENANCE_LEVELS:
            raise ValueError(
                f"Invalid relationship provenance: '{self.provenance}'. "
                f"Production graph relationships may ONLY use: {sorted(ALLOWED_PROVENANCE_LEVELS)}. "
                f"INFERRED provenance is strictly rejected."
            )
        self.provenance = prov_norm

        # 4. Enforce confidence within [0.0, 1.0]
        try:
            conf_val = float(self.confidence)
            if not (0.0 <= conf_val <= 1.0):
                raise ValueError
            self.confidence = conf_val
        except (TypeError, ValueError):
            raise ValueError(f"confidence must be a float between 0.0 and 1.0, got: {self.confidence}")

        # 5. Enforce non-empty source
        if not self.source or not str(self.source).strip():
            raise ValueError("source must be a non-empty string.")
        self.source = str(self.source).strip()

        # 6. Extract or normalize evidence_clause
        if not self.evidence_clause and self.evidence:
            m = re.search(r'\b(Clause\s+\d+(?:\.\d+)*|Foreword|Section\s+\d+|Annex\s+[A-Z])\b', self.evidence, re.IGNORECASE)
            if m:
                self.evidence_clause = m.group(1).title()

        # 7. Normalize relationship_type and handle SUPERSEDED_BY reversal
        raw_type = str(self.relationship_type or "").strip().upper()
        if raw_type == "SUPERSEDED_BY":
            # Reverse relationship: target_standard SUPERSEDES source_standard
            self.source_standard, self.target_standard = self.target_standard, self.source_standard
            self.relationship_type = RelationshipType("SUPERSEDES")
            if self.direction == "OUTGOING":
                self.direction = "INCOMING"
            elif self.direction == "INCOMING":
                self.direction = "OUTGOING"
        else:
            self.relationship_type = RelationshipType(raw_type)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["relationship_type"] = self.relationship_type
        return d


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


@dataclass
class TraversedReference:
    """
    Represents an evidence-grounded cross-reference discovered via graph traversal.
    Preserves source standard, originating clause, canonical target standard,
    explicit vs informative reference classification, lifecycle status, and evidence snippet.
    """
    source_standard: str                  # Originating standard identifier (e.g. "IS 800 : 2007")
    originating_clause: str               # Grounded clause identifier where reference appears (e.g. "2.2")
    target_standard: str                  # Canonical target standard identifier (e.g. "IS 2062 : 2011")
    target_title: str                     # Title of target standard from catalogue / index
    relationship_type: str                # NORMATIVE_REFERENCE, CODE_OF_PRACTICE, TEST_METHOD, etc.
    reference_kind: str                   # "EXPLICIT_NORMATIVE", "INFORMATIVE", "CODE_OF_PRACTICE", "TEST_METHOD"
    hop_depth: int                        # Current depth hop (1 or 2)
    lifecycle_status: str                 # "Active", "Withdrawn", "Superseded", "Unknown"
    is_active: bool                       # True if lifecycle_status == "Active"
    originating_evidence: str             # Verbatim sentence or citation passage
    source_citation: str                  # Originating standard or gazette reference
    provenance: str = "VERIFIED"          # Strictly "VERIFIED" or "CURATED"
    is_contextually_relevant: bool = False # Whether requirement keywords warrant this dependency
    relevance_reason: str = ""            # Explanation of contextual relevance
    review_note: str = "Related standard for engineering review"

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

    def __init__(self, db: Optional[StandardsDatabase] = None, relationships_json_path: str = "data/standards/relationships.json"):
        self.db = db or StandardsDatabase()
        self.relationships_json_path = relationships_json_path
        self._cached_file_relationships: Optional[List[Dict[str, Any]]] = None

    def _load_file_relationships(self) -> List[Dict[str, Any]]:
        """Loads relationships from relationships.json if present."""
        if self._cached_file_relationships is not None:
            return self._cached_file_relationships
        import json
        import os
        if os.path.exists(self.relationships_json_path):
            try:
                with open(self.relationships_json_path, "r", encoding="utf-8") as f:
                    self._cached_file_relationships = json.load(f)
            except Exception:
                self._cached_file_relationships = []
        else:
            self._cached_file_relationships = []
        return self._cached_file_relationships

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
        Strictly enforces depth = 1 by default.
        """
        if depth != 1:
            raise ValueError(f"Milestone 5 strictly supports depth = 1. Requested depth: {depth}")

        norm_id = self._normalize_id(standard_identifier)
        digits = self._extract_digits(norm_id)
        relationships: List[StandardRelationship] = []
        seen_keys: Set[tuple] = set()

        # Helper to deduplicate
        def add_rel(rel: StandardRelationship):
            key = (
                self._extract_digits(rel.source_standard),
                self._extract_digits(rel.target_standard),
                rel.relationship_type,
                rel.direction
            )
            if key not in seen_keys:
                seen_keys.add(key)
                relationships.append(rel)

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
                add_rel(StandardRelationship(
                    source_standard=src_repr,
                    target_standard=row['target_standard'],
                    relationship_type=row['relationship_type'],
                    evidence=row['evidence'],
                    provenance=row['verification_status'] or "CURATED",
                    source_url=row['source_url'],
                    confidence=1.0 if row['verification_status'] == "VERIFIED" else 0.85,
                    direction="OUTGOING",
                    source="SQLITE_DB"
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
                add_rel(StandardRelationship(
                    source_standard=src_repr,
                    target_standard=tgt_repr,
                    relationship_type="REFERENCES",
                    evidence=f"Cited under {clause_info} in {src_repr}.",
                    provenance=row['verification_status'] or "VERIFIED",
                    source_url=row['source_url'],
                    confidence=0.95 if row['verification_status'] == "VERIFIED" else 0.80,
                    direction="OUTGOING",
                    source="SQLITE_DB"
                ))

            # 3. Incoming relationships from standard_relationships table
            cursor.execute("""
            SELECT s.standard_number AS src_num, s.year AS src_yr, s.verification_status, s.source_url,
                   r.target_standard, r.relationship_type, r.evidence
            FROM standard_relationships r
            JOIN standards s ON s.standard_id = r.source_standard_id
            WHERE r.target_standard LIKE ? OR ( ? != '' AND r.target_standard LIKE ? )
            """, (f"%{norm_id}%", digits or "", f"%{digits}%" if digits else ""))

            for row in cursor.fetchall():
                src_repr = f"{row['src_num']} : {row['src_yr']}" if row['src_yr'] else row['src_num']
                if src_repr != norm_id:
                    add_rel(StandardRelationship(
                        source_standard=src_repr,
                        target_standard=row['target_standard'],
                        relationship_type=row['relationship_type'],
                        evidence=row['evidence'],
                        provenance=row['verification_status'] or "CURATED",
                        source_url=row['source_url'],
                        confidence=1.0 if row['verification_status'] == "VERIFIED" else 0.85,
                        direction="INCOMING",
                        source="SQLITE_DB"
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
                    add_rel(StandardRelationship(
                        source_standard=src_repr,
                        target_standard=tgt_repr,
                        relationship_type="REFERENCES",
                        evidence=f"Cited as normative reference in {src_repr} ({clause_info}).",
                        provenance=row['verification_status'] or "VERIFIED",
                        source_url=row['source_url'],
                        confidence=0.90 if row['verification_status'] == "VERIFIED" else 0.75,
                        direction="INCOMING",
                        source="SQLITE_DB"
                    ))

        # 5. Supplementary relationships from relationships.json
        file_rels = self._load_file_relationships()
        for fr in file_rels:
            src_str = fr.get("source_standard") or fr.get("source", "")
            tgt_str = fr.get("target_standard") or fr.get("target", "")
            rel_type = fr.get("relationship_type", "REFERENCES")
            ev_str = fr.get("evidence", "")
            prov = fr.get("provenance", "CURATED")
            conf = fr.get("confidence", 0.9)
            src_source = fr.get("evidence_source") or fr.get("source_dataset", "RELATIONSHIPS_JSON")

            src_digits = self._extract_digits(src_str)
            tgt_digits = self._extract_digits(tgt_str)

            # Match outgoing (query is source)
            if (digits and src_digits and digits == src_digits) or (norm_id and norm_id in src_str.upper()):
                add_rel(StandardRelationship(
                    source_standard=src_str,
                    target_standard=tgt_str,
                    relationship_type=rel_type,
                    evidence=ev_str,
                    provenance=prov,
                    confidence=conf,
                    direction="OUTGOING",
                    source=src_source
                ))
            # Match incoming (query is target)
            elif (digits and tgt_digits and digits == tgt_digits) or (norm_id and norm_id in tgt_str.upper()):
                add_rel(StandardRelationship(
                    source_standard=src_str,
                    target_standard=tgt_str,
                    relationship_type=rel_type,
                    evidence=ev_str,
                    provenance=prov,
                    confidence=conf,
                    direction="INCOMING",
                    source=src_source
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
            if rel.provenance == "VERIFIED":
                ev_strength = "STRONG" if rel.relationship_type in ["SUPERSEDES", "CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"] else "MODERATE"
            elif rel.provenance == "CURATED":
                ev_strength = "MODERATE"
            else:
                ev_strength = "WEAK"

            # Create explanatory review note based on relationship type
            # NOTE: Every note MUST contain the word 'review' for consistent advisory semantics
            if rel.relationship_type in ["SUPERSEDES", "SUPERSEDED_BY"]:
                if rel.direction == "OUTGOING":
                    note = f"Authoritative successor standard supersedes {clean_name}. Review legacy specifications."
                else:
                    note = f"Authoritative replacement standard is {clean_name}. Current cited standard is obsolete. Review replacement."
            elif rel.relationship_type in ["REFERENCES", "NORMATIVE_REFERENCE"]:
                if rel.direction == "OUTGOING":
                    note = f"Normative reference cited within primary standard. Review for co-application."
                else:
                    note = f"Primary standard is cited by {clean_name}. Review for broader installation context."
            elif rel.relationship_type in ["CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"]:
                if rel.direction == "OUTGOING":
                    note = f"Laying / civil installation code of practice associated with {clean_name}. Review for installation compliance."
                else:
                    note = f"Product manufacturing standard associated with installation code {clean_name}. Review for manufacturing specs."
            elif rel.relationship_type == "TEST_METHOD":
                note = f"Official test method standard for parameter verification and quality assurance. Review for testing protocol compliance."
            elif rel.relationship_type == "INSTALLATION_STANDARD":
                note = f"Installation, laying, and jointing standard associated with {clean_name}. Review for installation execution."
            elif rel.relationship_type == "TERMINOLOGY_STANDARD":
                note = f"Terminology and vocabulary standard. Review for technical definitions."
            elif rel.relationship_type == "SAFETY_STANDARD":
                note = f"Operational or personal safety standard. Review for mandatory safety protocol compliance."
            elif rel.relationship_type == "ALLIED_STANDARD":
                note = f"Allied product or component standard. Review for equipment interface compatibility."
            elif rel.relationship_type == "CERTIFICATION_RELATED":
                note = f"Certification and conformity assessment standard. Review for quality verification."
            elif rel.relationship_type == "QCO_RELATED":
                note = f"Quality Control Order related standard. Review for statutory compliance."
            elif rel.relationship_type == "IDENTICAL_ADOPTION":
                note = f"Identical international standard adoption (ISO/IEC). Review for international equivalence."
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

    def traverse_cross_references(
        self,
        start_standard: str,
        grounded_clause: Optional[str] = None,
        max_depth: int = 1,
        max_results: int = 10,
        tender_context: Optional[str] = None
    ) -> List[TraversedReference]:
        """
        Executes bounded, evidence-grounded cross-reference traversal starting from an explicit standard
        and its grounded clause.
        
        Strict constraints:
        - Max depth strictly bounded: default 1, maximum permitted 2. Raises ValueError if depth > 2 or depth < 1.
        - Cycle detection: avoids revisited standards.
        - Provenance preservation: each traversed edge retains originating clause and evidence snippet.
        - Lifecycle awareness: identifies whether referenced standards are Active, Withdrawn, or Superseded.
        - Contextual relevance: flags whether the reference applies to tender_context.
        - Graph relationship alone NEVER implies CLAUSE_VERIFIED.
        """
        if max_depth < 1 or max_depth > 2:
            raise ValueError(f"Cross-reference traversal depth must be between 1 and 2, got {max_depth}")

        norm_start = self._normalize_id(start_standard)
        start_digits = self._extract_digits(norm_start)
        parsed_start = StandardIdentifierNormalizer.parse(start_standard)
        canonical_start = parsed_start.canonical_id if parsed_start.is_valid else norm_start

        visited_stds: Set[str] = {canonical_start}
        if start_digits:
            visited_stds.add(start_digits)

        traversed_results: List[TraversedReference] = []

        # Internal helper to extract citations from corpus_passages
        def _get_corpus_citations(std_num: str, clause_id: Optional[str]) -> List[Dict[str, Any]]:
            citations = []
            corpus_db_path = "data/standards/corpus.db"
            if not os.path.exists(corpus_db_path):
                return citations

            digits = self._extract_digits(std_num)
            try:
                with sqlite3.connect(corpus_db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    q = "SELECT standard_number, clause_identifier, passage_text, edition_year FROM corpus_passages WHERE (standard_number = ? OR ( ? != '' AND standard_number LIKE ? ))"
                    params = [std_num, digits or "", f"%{digits}%" if digits else ""]
                    if clause_id:
                        q += " AND clause_identifier = ?"
                        params.append(clause_id)

                    rows = cur.execute(q, params).fetchall()
                    for r in rows:
                        p_text = r["passage_text"]
                        cid = r["clause_identifier"]
                        sentences = re.split(r'(?<=[.!?])\s+', p_text)
                        for sent in sentences:
                            matches = re.finditer(r'\b(IS\s*(?:\(Part\s*\d+\))?\s*(?:/|\s*)?\d+(?:\s*\(Part\s*\d+\))?(?:\s*:\s*\d{4})?)\b', sent, re.IGNORECASE)
                            for m in matches:
                                raw_cite = m.group(1).strip()
                                parsed = StandardIdentifierNormalizer.parse(raw_cite)
                                if parsed.is_valid and parsed.canonical_id != canonical_start:
                                    sent_lower = sent.lower()
                                    if any(k in sent_lower for k in ["test", "testing", "method", "hydrostatic"]):
                                        ref_kind = "TEST_METHOD"
                                        rel_type = "TEST_METHOD"
                                    elif any(k in sent_lower for k in ["code of practice", "loading", "earthquake", "wind"]):
                                        ref_kind = "CODE_OF_PRACTICE"
                                        rel_type = "CODE_OF_PRACTICE"
                                    elif any(k in sent_lower for k in ["shall conform", "conforming to", "requirements of", "shall be"]):
                                        ref_kind = "EXPLICIT_NORMATIVE"
                                        rel_type = "NORMATIVE_REFERENCE"
                                    else:
                                        ref_kind = "INFORMATIVE"
                                        rel_type = "REFERENCES"

                                    citations.append({
                                        "source_standard": r["standard_number"],
                                        "clause_identifier": cid,
                                        "target_raw": raw_cite,
                                        "target_canonical": parsed.canonical_id,
                                        "relationship_type": rel_type,
                                        "reference_kind": ref_kind,
                                        "evidence": sent.strip(),
                                        "provenance": "VERIFIED"
                                    })
            except Exception:
                pass
            return citations

        # Queue for breadth-first traversal: (current_std, current_clause, depth)
        queue = [(start_standard, grounded_clause, 1)]

        while queue and len(traversed_results) < max_results:
            curr_std, curr_clause, curr_depth = queue.pop(0)

            # 1. Check corpus passages for exact clause citations
            corpus_cites = _get_corpus_citations(curr_std, curr_clause)
            for c in corpus_cites:
                tgt_canon = c["target_canonical"]
                tgt_digits = self._extract_digits(tgt_canon)
                if tgt_canon in visited_stds or (tgt_digits and tgt_digits in visited_stds):
                    continue

                visited_stds.add(tgt_canon)
                if tgt_digits:
                    visited_stds.add(tgt_digits)

                tgt_info = self._resolve_standard_info(tgt_canon)
                lifecycle = tgt_info.get("status", "Unknown")
                is_act = (str(lifecycle).upper() == "ACTIVE")

                is_rel = False
                rel_reason = ""
                if tender_context:
                    tc_lower = tender_context.lower()
                    title_lower = (tgt_info.get("title") or "").lower()
                    keywords = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', title_lower) if w not in ["standard", "indian", "specification", "code", "practice", "part"]]
                    matches = [k for k in keywords if k in tc_lower]
                    if matches:
                        is_rel = True
                        rel_reason = f"Tender requirement mentions relevant scope terms ({', '.join(matches[:3])}) matching {tgt_canon}."
                    elif any(k in tc_lower for k in ["pipe", "valve", "steel", "fitting", "joint", "testing", "load", "structure"]):
                        is_rel = True
                        rel_reason = f"Supporting standard relevant to tender engineering domain ({c['relationship_type']})."

                ref_item = TraversedReference(
                    source_standard=c["source_standard"],
                    originating_clause=c["clause_identifier"],
                    target_standard=tgt_canon,
                    target_title=tgt_info.get("title", "Standard in BIS Catalogue"),
                    relationship_type=c["relationship_type"],
                    reference_kind=c["reference_kind"],
                    hop_depth=curr_depth,
                    lifecycle_status=lifecycle,
                    is_active=is_act,
                    originating_evidence=c["evidence"],
                    source_citation=f"{c['source_standard']} Clause {c['clause_identifier']}",
                    provenance=c["provenance"],
                    is_contextually_relevant=is_rel,
                    relevance_reason=rel_reason,
                    review_note=f"Cross-referenced under Clause {c['clause_identifier']} of {c['source_standard']} for review."
                )
                traversed_results.append(ref_item)

                if curr_depth < max_depth and len(traversed_results) < max_results:
                    queue.append((tgt_canon, None, curr_depth + 1))

            # 2. Check standard_relationships / relationships.json
            direct_rels = self.get_direct_relationships(curr_std, depth=1)
            for r in direct_rels:
                if r.direction != "OUTGOING":
                    continue
                tgt_clean = r.target_standard.strip()
                parsed_tgt = StandardIdentifierNormalizer.parse(tgt_clean)
                tgt_canon = parsed_tgt.canonical_id if parsed_tgt.is_valid else tgt_clean
                tgt_digits = self._extract_digits(tgt_canon)

                if tgt_canon in visited_stds or (tgt_digits and tgt_digits in visited_stds):
                    continue

                visited_stds.add(tgt_canon)
                if tgt_digits:
                    visited_stds.add(tgt_digits)

                tgt_info = self._resolve_standard_info(tgt_clean)
                lifecycle = tgt_info.get("status", "Unknown")
                is_act = (str(lifecycle).upper() == "ACTIVE")

                is_rel = False
                rel_reason = ""
                if tender_context:
                    tc_lower = tender_context.lower()
                    title_lower = (tgt_info.get("title") or "").lower()
                    keywords = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', title_lower) if w not in ["standard", "indian", "specification", "code", "practice", "part"]]
                    matches = [k for k in keywords if k in tc_lower]
                    if matches:
                        is_rel = True
                        rel_reason = f"Tender requirement mentions terms ({', '.join(matches[:3])}) matching {tgt_canon}."

                ref_kind = "EXPLICIT_NORMATIVE" if r.relationship_type in ["NORMATIVE_REFERENCE", "SUPERSEDES"] else "INFORMATIVE"
                if "test" in str(r.relationship_type).lower():
                    ref_kind = "TEST_METHOD"
                elif "code_of_practice" in str(r.relationship_type).lower():
                    ref_kind = "CODE_OF_PRACTICE"

                clause_repr = r.evidence_clause or curr_clause or "General"

                ref_item = TraversedReference(
                    source_standard=r.source_standard,
                    originating_clause=clause_repr,
                    target_standard=tgt_canon,
                    target_title=tgt_info.get("title", "Standard in BIS Catalogue"),
                    relationship_type=r.relationship_type,
                    reference_kind=ref_kind,
                    hop_depth=curr_depth,
                    lifecycle_status=lifecycle,
                    is_active=is_act,
                    originating_evidence=r.evidence,
                    source_citation=f"{r.source_standard} ({clause_repr})",
                    provenance=r.provenance,
                    is_contextually_relevant=is_rel,
                    relevance_reason=rel_reason,
                    review_note=f"Cross-referenced in {r.source_standard} ({r.relationship_type}) for review."
                )
                traversed_results.append(ref_item)

                if curr_depth < max_depth and len(traversed_results) < max_results:
                    queue.append((tgt_canon, None, curr_depth + 1))

        return traversed_results[:max_results]
