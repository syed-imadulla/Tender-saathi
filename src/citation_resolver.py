"""
Module: src/citation_resolver.py
Purpose: High-precision explicit Indian Standard (BIS) citation detection and resolution.

Strict Retrieval Precedence:
EXACT_EXPLICIT_CITATION > EXACT_NORMALIZED_IDENTIFIER > HIGH_CONFIDENCE_IDENTIFIER_MATCH > HYBRID_RELEVANCE > SEMANTIC_SIMILARITY

Preserves:
- canonical_id
- standard_number
- part
- section
- year
- lifecycle (Active, Withdrawn, Superseded, Unknown)
- provenance and source URLs
"""

import re
import sqlite3
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier
from src.standards import StandardsDatabase

logger = logging.getLogger("citation_resolver")


class CitationPrecedence:
    EXACT_EXPLICIT_CITATION = "EXACT_EXPLICIT_CITATION"
    EXACT_NORMALIZED_IDENTIFIER = "EXACT_NORMALIZED_IDENTIFIER"
    HIGH_CONFIDENCE_IDENTIFIER_MATCH = "HIGH_CONFIDENCE_IDENTIFIER_MATCH"


@dataclass
class ResolvedCitation:
    """Represents an authoritative standard record resolved from an explicit citation."""
    raw_citation: str
    precedence: str
    canonical_id: str
    standard_number: str
    base_standard_number: str
    title: str
    status: str
    part: Optional[int] = None
    section: Optional[int] = None
    year: Optional[int] = None
    is_active: Optional[int] = None
    technical_committee: Optional[str] = None
    department: Optional[str] = None
    aspect: Optional[str] = None
    source: str = "BIS"
    source_url: Optional[str] = None
    raw_record: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExactCitationResolver:
    """Dedicated exact citation resolution path for tender requirements."""

    # Robust regex to extract all IS / SP compound standard citations from free text
    CITATION_REGEX = re.compile(
        r'\b((?:IS|SP)(?:\s*/\s*(?:ISO|IEC|IEEE|CISPR|QC|EN)(?:\s*/\s*(?:TR|TS|PAS|GUIDE))?)?'
        r'\s*[-/]?\s*\d+(?:[\s\-/]*(?:Part|Pt\.?|Sec\.?|Section)?[\s\-/]*\d+(?:\s*(?:/|\s+)\s*(?:Sec\.?|Section)\s*[-/]?\s*\d+)?)?'
        r'(?:\s*\(.*?\))?(?:\s*:\s*(?:19|20)\d{2}|\s*[-/]\s*(?:19|20)\d{2})?)\b',
        re.IGNORECASE
    )

    def __init__(self, db: Optional[StandardsDatabase] = None):
        if db is not None:
            self.db = db
        else:
            from src.catalogue.provider import get_default_catalogue_provider
            self.db = get_default_catalogue_provider()

    def extract_citations(self, text: str) -> List[str]:
        """Extracts all explicit standard citation substrings from text."""
        if not text or not isinstance(text, str):
            return []
        matches = self.CITATION_REGEX.findall(text)
        cleaned = []
        for m in matches:
            m_clean = m.strip()
            # Must contain at least one digit
            if re.search(r'\d', m_clean):
                cleaned.append(m_clean)
        return cleaned

    def resolve_citation(self, citation_str: str) -> Optional[ResolvedCitation]:
        """
        Resolves a single citation candidate string against the BIS catalogue.
        Applies strict precedence:
        1. EXACT_EXPLICIT_CITATION
        2. EXACT_NORMALIZED_IDENTIFIER
        3. HIGH_CONFIDENCE_IDENTIFIER_MATCH
        """
        if not citation_str or not citation_str.strip():
            return None

        parsed: CanonicalStandardIdentifier = StandardIdentifierNormalizer.parse(citation_str)
        if not parsed.is_valid:
            return None

        with self.db._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Check whether catalogue_standards or standards table exists
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='catalogue_standards'")
            has_cat_table = bool(cur.fetchone())

            # 1. Precedence 1: EXACT_EXPLICIT_CITATION (exact canonical_id match)
            if has_cat_table:
                cur.execute("SELECT * FROM catalogue_standards WHERE canonical_id = ?", (parsed.canonical_id,))
                row = cur.fetchone()
                if row:
                    return self._build_resolved_from_row(
                        citation_str, CitationPrecedence.EXACT_EXPLICIT_CITATION, parsed, dict(row)
                    )
            else:
                cur.execute("SELECT * FROM standards WHERE standard_id = ?", (parsed.canonical_id,))
                row = cur.fetchone()
                if row:
                    return self._build_resolved_from_compat_row(
                        citation_str, CitationPrecedence.EXACT_EXPLICIT_CITATION, parsed, dict(row)
                    )

            # 2. Precedence 2: EXACT_NORMALIZED_IDENTIFIER (exact standard_number match)
            if has_cat_table:
                cur.execute("SELECT * FROM catalogue_standards WHERE standard_number = ?", (parsed.canonical_number,))
                row = cur.fetchone()
                if row:
                    return self._build_resolved_from_row(
                        citation_str, CitationPrecedence.EXACT_NORMALIZED_IDENTIFIER, parsed, dict(row)
                    )
            else:
                cur.execute("SELECT * FROM standards WHERE standard_number = ?", (parsed.canonical_number,))
                row = cur.fetchone()
                if row:
                    return self._build_resolved_from_compat_row(
                        citation_str, CitationPrecedence.EXACT_NORMALIZED_IDENTIFIER, parsed, dict(row)
                    )

            # 3. Precedence 3: HIGH_CONFIDENCE_IDENTIFIER_MATCH
            # When year is omitted in query (e.g. "IS 15778" or "IS 1554 (Part 1)")
            # Match by base_standard_number
            if has_cat_table:
                cur.execute(
                    "SELECT * FROM catalogue_standards WHERE base_standard_number = ? ORDER BY year DESC",
                    (parsed.base_standard_number,)
                )
                rows = [dict(r) for r in cur.fetchall()]
                if not rows:
                    cur.execute(
                        "SELECT * FROM catalogue_standards WHERE base_standard_number LIKE ? ORDER BY year DESC",
                        (f"{parsed.base_standard_number} %",)
                    )
                    rows = [dict(r) for r in cur.fetchall()]
                if rows:
                    # If multiple revisions exist, prefer Active, else newest year
                    best_row = rows[0]
                    for r in rows:
                        if str(r.get("status", "")).upper() == "ACTIVE":
                            best_row = r
                            break
                    return self._build_resolved_from_row(
                        citation_str, CitationPrecedence.HIGH_CONFIDENCE_IDENTIFIER_MATCH, parsed, best_row
                    )
            else:
                # In standards table, match standard_number LIKE 'base_standard_number%'
                cur.execute(
                    "SELECT * FROM standards WHERE standard_number LIKE ? ORDER BY year DESC",
                    (f"{parsed.base_standard_number}%",)
                )
                rows = [dict(r) for r in cur.fetchall()]
                if rows:
                    best_row = rows[0]
                    for r in rows:
                        if str(r.get("status", "")).upper() == "ACTIVE":
                            best_row = r
                            break
                    return self._build_resolved_from_compat_row(
                        citation_str, CitationPrecedence.HIGH_CONFIDENCE_IDENTIFIER_MATCH, parsed, best_row
                    )

        return None

    def resolve_from_text(self, text: str) -> List[ResolvedCitation]:
        """Extracts and resolves all valid standard citations from raw text."""
        citations = self.extract_citations(text)
        resolved_list = []
        seen_ids = set()

        for c in citations:
            resolved = self.resolve_citation(c)
            if resolved and resolved.canonical_id not in seen_ids:
                seen_ids.add(resolved.canonical_id)
                resolved_list.append(resolved)

        return resolved_list

    def _build_resolved_from_row(
        self,
        raw_citation: str,
        precedence: str,
        parsed: CanonicalStandardIdentifier,
        row: Dict[str, Any]
    ) -> ResolvedCitation:
        return ResolvedCitation(
            raw_citation=raw_citation,
            precedence=precedence,
            canonical_id=row["canonical_id"],
            standard_number=row["standard_number"],
            base_standard_number=row.get("base_standard_number", parsed.base_standard_number),
            title=row.get("title") or row.get("full_title", ""),
            status=row.get("status", "UNKNOWN"),
            part=row.get("part") if row.get("part") is not None else parsed.part,
            section=row.get("section") if row.get("section") is not None else parsed.section,
            year=row.get("year") if row.get("year") is not None else parsed.year,
            is_active=row.get("is_active"),
            technical_committee=row.get("technical_committee"),
            department=row.get("department"),
            aspect=row.get("aspect"),
            source=row.get("source", "BIS"),
            source_url=row.get("source_url"),
            raw_record=row
        )

    def _build_resolved_from_compat_row(
        self,
        raw_citation: str,
        precedence: str,
        parsed: CanonicalStandardIdentifier,
        row: Dict[str, Any]
    ) -> ResolvedCitation:
        return ResolvedCitation(
            raw_citation=raw_citation,
            precedence=precedence,
            canonical_id=row["standard_id"],
            standard_number=row["standard_number"],
            base_standard_number=parsed.base_standard_number,
            title=row.get("full_title", ""),
            status=row.get("status", "UNKNOWN"),
            part=parsed.part,
            section=parsed.section,
            year=row.get("year") if row.get("year") is not None else parsed.year,
            is_active=1 if str(row.get("status", "")).upper() == "ACTIVE" else 0,
            technical_committee=row.get("technical_committee"),
            department=None,
            aspect=None,
            source=row.get("source", "BIS"),
            source_url=row.get("source_url"),
            raw_record=row
        )
