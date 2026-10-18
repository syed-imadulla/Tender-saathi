"""
Module: src/catalogue/access.py
Purpose: Reusable, thread-safe, read-only data access layer for the national BIS catalogue.

Security & Safety:
- STRICTLY READ-ONLY (SELECT queries only).
- Parameterized SQL statements to eliminate injection risks.
- Graceful degradation if data/catalogue/bis_catalogue.db is absent or locked.
- Never fabricates missing records or metadata.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import os
import sqlite3
import logging
from contextlib import contextmanager

from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier

logger = logging.getLogger(__name__)

DEFAULT_CATALOGUE_DB_PATH = "data/catalogue/bis_catalogue.db"


@dataclass
class CatalogueStandardMatch:
    """Represents a validated standard match from the national BIS catalogue."""
    canonical_id: str
    standard_number: str
    base_standard_number: str
    prefix: str
    base_number: str
    part: Optional[int]
    section: Optional[int]
    year: Optional[int]
    title: str
    technical_committee: Optional[str]
    department: Optional[str]
    status: str                         # ACTIVE, WITHDRAWN, SUPERSEDED, UNKNOWN
    is_active: Optional[bool]
    amendment_count: int
    source_url: Optional[str]
    iso_equivalence: Optional[str]
    source: str
    all_editions: List[Dict[str, Any]] = field(default_factory=list)
    is_ambiguous_edition: bool = False
    ambiguity_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "standard_number": self.standard_number,
            "base_standard_number": self.base_standard_number,
            "prefix": self.prefix,
            "base_number": self.base_number,
            "part": self.part,
            "section": self.section,
            "year": self.year,
            "title": self.title,
            "technical_committee": self.technical_committee,
            "department": self.department,
            "status": self.status,
            "is_active": self.is_active,
            "amendment_count": self.amendment_count,
            "source_url": self.source_url,
            "iso_equivalence": self.iso_equivalence,
            "source": self.source,
            "is_ambiguous_edition": self.is_ambiguous_edition,
            "ambiguity_message": self.ambiguity_message,
            "total_editions_found": len(self.all_editions),
        }


class NationalCatalogueDatabase:
    """Read-only access provider for data/catalogue/bis_catalogue.db."""

    def __init__(self, db_path: str = DEFAULT_CATALOGUE_DB_PATH):
        self.db_path = db_path
        self.normalizer = StandardIdentifierNormalizer()

    def is_available(self) -> bool:
        """Checks if the national catalogue database file exists and is readable."""
        return os.path.exists(self.db_path) and os.path.isfile(self.db_path)

    @contextmanager
    def _get_connection(self):
        """Yields a read-only SQLite connection."""
        if not self.is_available():
            raise FileNotFoundError(f"National BIS catalogue database not found at '{self.db_path}'")
        
        # URI mode ro (read-only) prevents any accidental writes or journal locks
        uri_path = f"file:{os.path.abspath(self.db_path)}?mode=ro"
        conn = sqlite3.connect(uri_path, uri=True, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def lookup_by_identifier(self, identifier: str) -> Optional[CatalogueStandardMatch]:
        """
        Resolves a standard identifier against the national catalogue.
        
        Handles:
        - Exact canonical slug lookup (e.g. 'IS-8112-2013', 'IS-1180-Part-1-2014').
        - Unversioned base queries (e.g. 'IS 8112', 'IS 2712', 'IS/IEC 61439-3').
        - Parentheses and punctuation variants.
        - Multiple editions: selects latest active/non-withdrawn edition as primary,
          recording all editions and flagging ambiguity for review.
        """
        if not identifier or not str(identifier).strip():
            return None

        if not self.is_available():
            logger.warning("National catalogue lookup skipped: database file not available at %s", self.db_path)
            return None

        raw = str(identifier).strip()
        parsed = self.normalizer.parse(raw)
        if not parsed or not parsed.is_valid:
            # Fallback cleanup
            clean_str = raw.replace('(', '').replace(')', '').strip()
            parsed = self.normalizer.parse(clean_str)

        if not parsed or not parsed.is_valid or not parsed.base_number:
            return None

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Case 1: Year was explicitly provided in the query
                if parsed.year:
                    # Try exact canonical_id lookup first
                    canonical_slug = parsed.canonical_id
                    cursor.execute("""
                        SELECT * FROM catalogue_standards 
                        WHERE canonical_id = ?
                    """, (canonical_slug,))
                    row = cursor.fetchone()

                    # Fallback to base_number + prefix + year + part
                    if not row:
                        cursor.execute("""
                            SELECT * FROM catalogue_standards
                            WHERE base_number = ? AND prefix = ? AND year = ?
                              AND (part IS ? OR part = ?)
                              AND (section IS ? OR section = ?)
                        """, (
                            parsed.base_number, parsed.prefix, parsed.year,
                            parsed.part, parsed.part,
                            parsed.section, parsed.section
                        ))
                        row = cursor.fetchone()

                    if row:
                        row_dict = dict(row)
                        return self._row_to_match(row_dict, all_editions=[row_dict], is_ambiguous=False)

                # Case 2: Year was omitted or specific year wasn't found - fetch all editions for this standard/part
                query = """
                    SELECT * FROM catalogue_standards
                    WHERE base_number = ? AND prefix = ?
                      AND (part IS ? OR part = ?)
                      AND (section IS ? OR section = ?)
                    ORDER BY 
                      CASE 
                        WHEN status = 'ACTIVE' THEN 1 
                        WHEN status = 'UNKNOWN' THEN 2 
                        ELSE 3 
                      END, 
                      year DESC
                """
                cursor.execute(query, (
                    parsed.base_number, parsed.prefix,
                    parsed.part, parsed.part,
                    parsed.section, parsed.section
                ))
                rows = [dict(r) for r in cursor.fetchall()]

                # Fallback: if no rows found by prefix + base_number, try base_number alone if prefix is generic 'IS'
                if not rows and parsed.prefix in ["IS", ""]:
                    alt_query = """
                        SELECT * FROM catalogue_standards
                        WHERE base_number = ?
                          AND (part IS ? OR part = ?)
                          AND (section IS ? OR section = ?)
                        ORDER BY 
                          CASE 
                            WHEN status = 'ACTIVE' THEN 1 
                            WHEN status = 'UNKNOWN' THEN 2 
                            ELSE 3 
                          END, 
                          year DESC
                    """
                    cursor.execute(alt_query, (
                        parsed.base_number,
                        parsed.part, parsed.part,
                        parsed.section, parsed.section
                    ))
                    rows = [dict(r) for r in cursor.fetchall()]

                # Fallback: If query did not specify a part (parsed.part is None), but the standard exists as a multi-part series
                if not rows and parsed.part is None:
                    multi_part_query = """
                        SELECT * FROM catalogue_standards
                        WHERE base_number = ? AND (prefix = ? OR ? IN ('IS', ''))
                        ORDER BY 
                          part ASC,
                          CASE 
                            WHEN status = 'ACTIVE' THEN 1 
                            WHEN status = 'UNKNOWN' THEN 2 
                            ELSE 3 
                          END, 
                          year DESC
                    """
                    cursor.execute(multi_part_query, (parsed.base_number, parsed.prefix, parsed.prefix))
                    rows = [dict(r) for r in cursor.fetchall()]
                    if rows:
                        parts_found = sorted(list(set(r.get("part") for r in rows if r.get("part") is not None)))
                        primary_row = rows[0]
                        ambiguity_msg = (
                            f"Cited standard '{raw}' is a multi-part standard series with {len(parts_found)} parts "
                            f"(Parts {', '.join(str(p) for p in parts_found[:5])}{'...' if len(parts_found) > 5 else ''}) in the national catalogue. "
                            f"Defaulted to Part {primary_row.get('part', 1)}. Clarification of specific part is recommended."
                        )
                        return self._row_to_match(primary_row, all_editions=rows, is_ambiguous=True, ambiguity_msg=ambiguity_msg)

                if not rows:
                    return None

                primary_row = rows[0]
                is_ambiguous = len(rows) > 1
                ambiguity_msg = None
                if is_ambiguous:
                    editions_summary = ", ".join([
                        f"{r.get('standard_number') or r['canonical_id']} ({r.get('status', 'UNKNOWN')})"
                        for r in rows
                    ])
                    ambiguity_msg = (
                        f"Cited standard '{raw}' matches {len(rows)} editions in the national catalogue: {editions_summary}. "
                        f"Resolved to latest candidate '{primary_row.get('standard_number')}'. Manual review recommended."
                    )

                return self._row_to_match(primary_row, all_editions=rows, is_ambiguous=is_ambiguous, ambiguity_msg=ambiguity_msg)

        except Exception as e:
            logger.error("Error querying national BIS catalogue: %s", e)
            return None

    def find_all_editions(
        self,
        base_number: str,
        prefix: str = "IS",
        part: Optional[int] = None,
        section: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves all historical and active editions for a base standard number."""
        if not self.is_available():
            return []

        clean_num = str(base_number).strip().lstrip("0")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM catalogue_standards
                    WHERE base_number = ? AND prefix = ?
                      AND (part IS ? OR part = ?)
                      AND (section IS ? OR section = ?)
                    ORDER BY year DESC
                """, (clean_num, prefix, part, part, section, section))
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("Error retrieving editions for %s %s: %s", prefix, base_number, e)
            return []

    def get_catalogue_metadata(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """Direct primary key lookup for a canonical standard identifier."""
        if not self.is_available() or not canonical_id:
            return None

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM catalogue_standards WHERE canonical_id = ?", (canonical_id.strip(),))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error("Error getting catalogue metadata for %s: %s", canonical_id, e)
            return None

    def _row_to_match(
        self,
        row: Dict[str, Any],
        all_editions: List[Dict[str, Any]],
        is_ambiguous: bool,
        ambiguity_msg: Optional[str] = None
    ) -> CatalogueStandardMatch:
        """Constructs a CatalogueStandardMatch instance from a database row dict."""
        return CatalogueStandardMatch(
            canonical_id=row["canonical_id"],
            standard_number=row.get("standard_number") or row["canonical_id"],
            base_standard_number=row.get("base_standard_number") or row.get("standard_number", ""),
            prefix=row.get("prefix") or "IS",
            base_number=row.get("base_number") or "",
            part=row.get("part"),
            section=row.get("section"),
            year=row.get("year"),
            title=row.get("title") or "",
            technical_committee=row.get("technical_committee"),
            department=row.get("department"),
            status=row.get("status") or "UNKNOWN",
            is_active=bool(row.get("is_active")) if row.get("is_active") is not None else None,
            amendment_count=row.get("amendment_count") or 0,
            source_url=row.get("source_url"),
            iso_equivalence=row.get("iso_equivalence"),
            source=row.get("source") or "BIS Know Your Standards",
            all_editions=all_editions,
            is_ambiguous_edition=is_ambiguous,
            ambiguity_message=ambiguity_msg,
        )


# Singleton instance helper
_CATALOGUE_DB_INSTANCE: Optional[NationalCatalogueDatabase] = None

def get_national_catalogue() -> NationalCatalogueDatabase:
    """Returns the singleton instance of NationalCatalogueDatabase."""
    global _CATALOGUE_DB_INSTANCE
    if _CATALOGUE_DB_INSTANCE is None:
        _CATALOGUE_DB_INSTANCE = NationalCatalogueDatabase()
    return _CATALOGUE_DB_INSTANCE

get_national_catalogue_db = get_national_catalogue
