"""
Module: src/catalogue/search.py
Purpose: Fast, deterministic lexical retrieval engine over the National BIS Catalogue
using SQLite FTS5 (catalogue_search_index.db).

Architecture:
- Connects read-only to data/catalogue/catalogue_search_index.db.
- Automatically builds the FTS5 index if it does not already exist.
- Sanitizes untrusted queries and builds multi-tier FTS5 queries (phrase + prefix conjunctions).
- Ranks candidates using SQLite FTS5 BM25 with calibrated field weights:
    standard_number: 5.0, title: 3.0, technical_committee: 1.0, department: 0.8, iso_equivalence: 2.0.
- Normalizes scores into a calibrated [0.0, 1.0] range.
- Returns standard SearchResult objects marked with verification_status="CATALOGUE_VERIFIED"
  and _is_catalogue_only=True.
- Never fabricates clause passages, technical thresholds, or normative evidence.
"""

from typing import List, Dict, Any, Optional
import os
import re
import sqlite3
import logging
from contextlib import contextmanager

from src.search import SearchResult

logger = logging.getLogger(__name__)

DEFAULT_INDEX_DB_PATH = "data/catalogue/catalogue_search_index.db"
DEFAULT_SOURCE_DB_PATH = "data/catalogue/bis_catalogue.db"

# Generic tender procurement stopwords that dilute product search
PROCUREMENT_STOPWORDS = {
    "supply", "installation", "testing", "commissioning", "procurement",
    "works", "system", "systems", "work", "tender", "item", "items",
    "specification", "specifications", "requirements", "shall", "conform",
    "conforming", "standard", "standards", "code", "practice", "general",
    "part", "section", "clause", "type", "types", "method", "methods",
    "for", "and", "the", "with", "including", "allied", "at", "in", "on",
    "of", "to", "by", "from", "an", "as", "is", "are", "was", "were", "be",
    "been", "has", "have", "had", "do", "does", "did", "can", "could",
    "should", "would", "may", "might", "must", "new", "nos", "no", "etc"
}


class NationalCatalogueSearchEngine:
    """Lexical retrieval engine operating over the National BIS Catalogue FTS5 index."""

    def __init__(
        self,
        index_db_path: str = DEFAULT_INDEX_DB_PATH,
        source_db_path: str = DEFAULT_SOURCE_DB_PATH,
        auto_build: bool = True
    ):
        self.index_db_path = index_db_path
        self.source_db_path = source_db_path
        self._ensure_index_available(auto_build=auto_build)

    def _ensure_index_available(self, auto_build: bool = True) -> bool:
        """Verifies index database existence; builds it if missing and source DB is available."""
        if os.path.exists(self.index_db_path):
            return True
        if auto_build and os.path.exists(self.source_db_path):
            try:
                from scripts.build_catalogue_search_index import build_catalogue_search_index
                logger.info(f"FTS5 index missing at '{self.index_db_path}'. Building from '{self.source_db_path}'...")
                build_catalogue_search_index(
                    source_db_path=self.source_db_path,
                    target_index_path=self.index_db_path,
                    active_only=True
                )
                return os.path.exists(self.index_db_path)
            except Exception as e:
                logger.error(f"Failed to auto-build catalogue search index: {e}")
                return False
        return False

    @contextmanager
    def _get_connection(self):
        """Yields a read-only thread-safe SQLite connection."""
        if not os.path.exists(self.index_db_path):
            yield None
            return

        uri = f"file:{os.path.abspath(self.index_db_path)}?mode=ro"
        conn = None
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def sanitize_and_build_fts_query(self, raw_query: str) -> Optional[str]:
        """
        Transforms untrusted natural-language query into a safe, multi-term FTS5 query.
        Strips dangerous FTS5 control operators and syntax tokens.
        """
        # Strip all punctuation and non-alphanumeric characters except whitespace
        clean_text = re.sub(r'[^\w\s]', ' ', raw_query)
        words = clean_text.split()

        # Tokenize and normalize
        tokens = [w.strip().lower() for w in words if len(w.strip()) >= 2]
        if not tokens:
            return None

        # Separate significant technical tokens from procurement noise
        sig_tokens = [t for t in tokens if t not in PROCUREMENT_STOPWORDS and not t.isdigit()]
        number_tokens = [t for t in tokens if t.isdigit() and len(t) >= 3]

        # If numbers present (e.g. 10000, 14846, 7098), prioritize them
        if number_tokens:
            num_clauses = [f'"{nt}"' for nt in number_tokens]
            if sig_tokens:
                sig_clauses = [f'"{st}*"' for st in sig_tokens[:4]]
                return f"({' OR '.join(num_clauses)}) OR ({' AND '.join(sig_clauses)})"
            return " OR ".join(num_clauses)

        if not sig_tokens:
            sig_tokens = tokens[:4]

        # Build compound FTS5 query:
        # Tier 1: exact phrase match if 2+ words
        # Tier 2: AND conjunction of prefix tokens
        # Tier 3: OR disjunction of prefix tokens for ranking
        parts = []
        if len(sig_tokens) >= 2:
            exact_phrase = " ".join(sig_tokens[:3])
            parts.append(f'"{exact_phrase}"')
            and_phrase = " AND ".join(f'{t}*' for t in sig_tokens[:4])
            parts.append(f"({and_phrase})")

        or_phrase = " OR ".join(f'{t}*' for t in sig_tokens[:5])
        parts.append(f"({or_phrase})")

        return " OR ".join(parts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.20
    ) -> List[SearchResult]:
        """
        Executes lexical FTS5 BM25 search over active catalogue records.
        Returns a bounded list of SearchResult candidates.
        """
        sanitized_fts_query = self.sanitize_and_build_fts_query(query)
        if not sanitized_fts_query:
            return []

        with self._get_connection() as conn:
            if not conn:
                return []

            cursor = conn.cursor()
            sql = """
                SELECT
                    canonical_id,
                    standard_number,
                    title,
                    technical_committee,
                    department,
                    iso_equivalence,
                    year,
                    status,
                    source_url,
                    bm25(catalogue_fts, 5.0, 3.0, 1.0, 0.8, 2.0) as rank_score
                FROM catalogue_fts
                WHERE catalogue_fts MATCH ?
                ORDER BY rank_score ASC
                LIMIT ?;
            """

            try:
                cursor.execute(sql, (sanitized_fts_query, top_k * 2))
                rows = cursor.fetchall()
            except sqlite3.OperationalError as e:
                logger.warning(f"FTS5 query failed for '{sanitized_fts_query}': {e}. Retrying with simple tokens...")
                # Fallback to simple unpunctuated tokens
                simple_tokens = " OR ".join(re.findall(r'[a-zA-Z0-9]+', query)[:4])
                if not simple_tokens:
                    return []
                try:
                    cursor.execute(sql, (simple_tokens, top_k * 2))
                    rows = cursor.fetchall()
                except Exception as e_fallback:
                    logger.error(f"Fallback FTS5 query failed: {e_fallback}")
                    return []

        results: List[SearchResult] = []
        for r in rows:
            bm25_raw = r["rank_score"]
            # BM25 is negative in SQLite; convert magnitude into normalized [0.0, 1.0] score
            abs_bm25 = abs(bm25_raw)
            norm_score = round(min(1.0, max(0.0, abs_bm25 / (abs_bm25 + 5.0))), 3)

            if norm_score < min_score:
                continue

            year_val = None
            if r["year"]:
                try:
                    year_val = int(r["year"])
                except (ValueError, TypeError):
                    year_val = None

            tech_comm = r["technical_committee"] or "Technical Committee"
            dept = r["department"] or "BIS Division Council"
            title_clean = r["title"] or "Indian Standard"

            res = SearchResult(
                standard_id=r["canonical_id"],
                standard_number=r["standard_number"] or r["canonical_id"],
                year=year_val,
                full_title=title_clean,
                status="Active" if r["status"] == "ACTIVE" else r["status"],
                version_role="CURRENT_ACTIVE" if r["status"] == "ACTIVE" else "REPLACED_OR_SUPERSEDED",
                relevance_score=norm_score,
                relevance_reason=(
                    f"National BIS Catalogue Lexical Match (FTS5 BM25: {abs_bm25:.2f}, "
                    f"Committee: {tech_comm}, Division: {dept})"
                ),
                scope_summary=(
                    f"[National BIS Catalogue metadata: Committee {tech_comm}, Department {dept}. "
                    f"Technical clauses unindexed in local semantic corpus]"
                ),
                referenced_standards=[],
                explicit_relationships=[],
                verification_status="CATALOGUE_VERIFIED",
                source_provenance="National BIS Catalogue (data/catalogue/bis_catalogue.db)",
                bm25_score=norm_score,
                final_score=norm_score
            )

            # Store explicit provenance flags for downstream guards
            setattr(res, "_is_catalogue_only", True)
            setattr(res, "_catalogue_record", {
                "canonical_id": r["canonical_id"],
                "standard_number": r["standard_number"],
                "title": title_clean,
                "technical_committee": tech_comm,
                "department": dept,
                "year": year_val,
                "status": r["status"],
                "source_url": r["source_url"],
                "iso_equivalence": r["iso_equivalence"],
                "source": "National BIS Catalogue"
            })

            results.append(res)
            if len(results) >= top_k:
                break

        return results
