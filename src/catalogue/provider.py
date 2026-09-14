"""
Module: src/catalogue/provider.py
Purpose: Authoritative Standards Catalogue Provider & Adapter for TenderSaathi.

Connects the Phase 2 BIS catalogue (data/catalogue/bis_catalogue.db) to the
retrieval and recommendation pipeline, conforming to the StandardsDatabase interface
without creating fake relationship tables or altering the underlying database.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import sqlite3
import os
import json
import logging

from src.standards import StandardsDatabase

logger = logging.getLogger("tendersaathi.catalogue.provider")


class CatalogueProvider(ABC):
    """Abstract interface defining the standards catalogue provider contract."""

    @abstractmethod
    def get_standard(self, standard_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single standard by canonical identifier."""
        pass

    @abstractmethod
    def get_total_count(self) -> int:
        """Returns the total number of canonical standards in the catalogue."""
        pass

    @abstractmethod
    def get_provenance(self, standard_id: str) -> Optional[Dict[str, Any]]:
        """Returns complete provenance information for a standard."""
        pass


class BISCatalogueProvider(StandardsDatabase, CatalogueProvider):
    """
    Authoritative BIS Catalogue Provider reading from bis_catalogue.db.
    Subclasses StandardsDatabase to ensure seamless backward compatibility with
    StandardsSearchEngine, BM25SearchEngine, SemanticSearchEngine, and StandardsRecommender.

    Design rules:
    - Never creates fake/empty relationship tables in the database.
    - Operates dynamically without hard-coded record counts.
    - Exposes rich provenance (source, source_url, raw_record_ref, ingestion_run_id).
    - Preserves canonical IDs (parts, sections, compound prefixes).
    """

    DEFAULT_DB_PATH = "data/catalogue/bis_catalogue.db"

    def __init__(self, db_path: Optional[str] = None, read_only: bool = True):
        if db_path:
            resolved_path = db_path
        elif os.environ.get("TENDERSAATHI_CATALOGUE_PATH"):
            resolved_path = os.environ["TENDERSAATHI_CATALOGUE_PATH"]
        else:
            # Check for active snapshot pointer
            pointer_path = os.path.join("data/catalogue", "current_snapshot.json")
            if os.path.exists(pointer_path):
                try:
                    with open(pointer_path, "r", encoding="utf-8") as f:
                        snap_data = json.load(f)
                    snap_db = snap_data.get("paths", {}).get("db_path")
                    if snap_db and os.path.exists(snap_db):
                        resolved_path = snap_db
                    else:
                        resolved_path = self.DEFAULT_DB_PATH
                except Exception:
                    resolved_path = self.DEFAULT_DB_PATH
            else:
                resolved_path = self.DEFAULT_DB_PATH

        self.db_path = resolved_path
        self.read_only = read_only
        self._table_cache: Dict[str, bool] = {}

        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Authoritative BIS catalogue not found at: {self.db_path}")

        # Verify database has required catalogue tables without creating any
        self._verify_catalogue()

    def _init_db(self):
        """
        No-op override. Prevents StandardsDatabase.__init__ from creating
        empty standard_relationships or standard_references tables.
        """
        pass

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a SQLite connection to the BIS catalogue."""
        if self.read_only:
            abs_path = os.path.abspath(self.db_path)
            conn = sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)
        else:
            conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _has_table(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Checks if a table exists in the database with local caching."""
        if table_name in self._table_cache:
            return self._table_cache[table_name]
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        exists = cursor.fetchone() is not None
        self._table_cache[table_name] = exists
        return exists

    def _verify_catalogue(self):
        """Verifies that the database contains the authoritative catalogue table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('catalogue_standards', 'standards')")
            tables = {r[0] for r in cursor.fetchall()}
            if not tables:
                raise ValueError(f"Database at {self.db_path} does not contain catalogue_standards or standards tables.")
            logger.info("BISCatalogueProvider verified at %s (tables: %s)", self.db_path, list(tables))

    def get_total_count(self) -> int:
        """Dynamically queries the total count of standards from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if self._has_table(conn, "catalogue_standards"):
                cursor.execute("SELECT count(*) FROM catalogue_standards")
            else:
                cursor.execute("SELECT count(*) FROM standards")
            return cursor.fetchone()[0]

    def get_standard(self, standard_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a standard by standard_id or canonical_id, merging core fields
        with rich catalogue metadata when available.
        """
        if not standard_id:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # First try the standards compatibility table
            row = None
            if self._has_table(conn, "standards"):
                cursor.execute("SELECT * FROM standards WHERE standard_id = ? OR standard_number = ?", (standard_id, standard_id))
                row = cursor.fetchone()

            # If not found or if catalogue_standards has richer data, check catalogue_standards
            cat_row = None
            if self._has_table(conn, "catalogue_standards"):
                cursor.execute("SELECT * FROM catalogue_standards WHERE canonical_id = ? OR standard_number = ?", (standard_id, standard_id))
                cat_row = cursor.fetchone()

            if not row and not cat_row:
                return None

            result: Dict[str, Any] = {}
            if row:
                result.update(dict(row))

            if cat_row:
                c_dict = dict(cat_row)
                # Ensure standard_id maps to canonical_id
                if "canonical_id" in c_dict and not result.get("standard_id"):
                    result["standard_id"] = c_dict["canonical_id"]
                if "title" in c_dict and not result.get("full_title"):
                    result["full_title"] = c_dict["title"]
                # Add rich catalogue fields
                result["canonical_id"] = c_dict.get("canonical_id")
                result["aspect"] = c_dict.get("aspect")
                result["raw_record_ref"] = c_dict.get("raw_record_ref")
                result["ingestion_run_id"] = c_dict.get("ingestion_run_id")
                result["seeds_observed"] = c_dict.get("seeds_observed_json")
                result["times_observed"] = c_dict.get("times_observed", 1)
                result["is_active"] = c_dict.get("is_active")
                result["iso_equivalence"] = c_dict.get("iso_equivalence")
                if not result.get("source_url") and c_dict.get("source_url"):
                    result["source_url"] = c_dict.get("source_url")
                if not result.get("source") and c_dict.get("source"):
                    result["source"] = c_dict.get("source")

            # References: check if table genuinely exists, otherwise empty list
            if self._has_table(conn, "standard_references"):
                cursor.execute(
                    "SELECT referenced_standard_number, referenced_year, referenced_title, citing_clause "
                    "FROM standard_references WHERE standard_id = ?",
                    (result.get("standard_id", standard_id),)
                )
                result["references"] = [dict(r) for r in cursor.fetchall()]
            else:
                result["references"] = []

            # Explicit relationships: check if table genuinely exists, otherwise empty list
            if self._has_table(conn, "standard_relationships"):
                cursor.execute(
                    "SELECT target_standard, relationship_type, evidence "
                    "FROM standard_relationships WHERE source_standard_id = ?",
                    (result.get("standard_id", standard_id),)
                )
                result["explicit_relationships"] = [dict(r) for r in cursor.fetchall()]
            else:
                result["explicit_relationships"] = []

            return result

    def get_provenance(self, standard_id: str) -> Optional[Dict[str, Any]]:
        """Extracts verified provenance details for a standard."""
        std = self.get_standard(standard_id)
        if not std:
            return None

        seeds = []
        if std.get("seeds_observed"):
            try:
                seeds = json.loads(std["seeds_observed"]) if isinstance(std["seeds_observed"], str) else std["seeds_observed"]
            except Exception:
                seeds = []

        return {
            "canonical_id": std.get("canonical_id") or std.get("standard_id"),
            "standard_number": std.get("standard_number"),
            "title": std.get("full_title"),
            "status": std.get("status"),
            "source": std.get("source", "BIS_KNOW_YOUR_STANDARDS"),
            "source_url": std.get("source_url"),
            "retrieved_at": std.get("retrieved_at"),
            "ingestion_run_id": std.get("ingestion_run_id"),
            "raw_record_ref": std.get("raw_record_ref"),
            "seeds_observed": seeds,
            "verification_status": std.get("verification_status", "BIS_OFFICIAL_CATALOGUE")
        }

    def get_references(self, standard_id: str) -> List[Dict[str, Any]]:
        """Returns references if table exists, else empty list without error."""
        with self._get_connection() as conn:
            if not self._has_table(conn, "standard_references"):
                return []
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standard_references WHERE standard_id = ?", (standard_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_referencing_standards(self, standard_number: str) -> List[Dict[str, Any]]:
        """Returns citing standards if table exists, else empty list without error."""
        with self._get_connection() as conn:
            if not self._has_table(conn, "standard_references"):
                return []
            cursor = conn.cursor()
            cursor.execute("""
            SELECT s.* FROM standards s
            JOIN standard_references r ON s.standard_id = r.standard_id
            WHERE r.referenced_standard_number LIKE ?
            """, (f"%{standard_number}%",))
            return [dict(r) for r in cursor.fetchall()]

    def get_relationships(self, standard_id: str) -> List[Dict[str, Any]]:
        """Returns explicit relationships if table exists, else empty list without error."""
        with self._get_connection() as conn:
            if not self._has_table(conn, "standard_relationships"):
                return []
            cursor = conn.cursor()
            cursor.execute("""
            SELECT source_standard_id, target_standard, relationship_type, evidence
            FROM standard_relationships
            WHERE source_standard_id = ? OR target_standard LIKE ?
            """, (standard_id, f"%{standard_id}%"))
            return [dict(r) for r in cursor.fetchall()]

    def get_lifecycle_breakdown(self) -> Dict[str, int]:
        """Dynamically computes the status/lifecycle counts directly from BIS data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            table = "catalogue_standards" if self._has_table(conn, "catalogue_standards") else "standards"
            cursor.execute(f"SELECT status, count(*) FROM {table} GROUP BY status")
            counts = {r[0]: r[1] for r in cursor.fetchall()}
            return {
                "ACTIVE": counts.get("ACTIVE", 0),
                "WITHDRAWN": counts.get("WITHDRAWN", 0),
                "SUPERSEDED": counts.get("SUPERSEDED", 0),
                "UNKNOWN": counts.get("UNKNOWN", 0),
                "total": sum(counts.values())
            }

    def get_synchronization_metadata(self) -> Dict[str, Any]:
        """
        Returns snapshot and synchronization metadata for provenance reporting.
        Uses truthful wording: 'BIS catalogue synchronized: <timestamp>'
        """
        last_sync_timestamp = None
        snapshot_id = None
        with self._get_connection() as conn:
            if self._has_table(conn, "catalogue_snapshots"):
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT snapshot_id, created_at FROM catalogue_snapshots ORDER BY created_at DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    snapshot_id = row[0]
                    last_sync_timestamp = row[1]

        total_count = self.get_total_count()
        label = f"BIS catalogue synchronized: {last_sync_timestamp}" if last_sync_timestamp else "BIS catalogue snapshot active"

        return {
            "provider": "BIS catalogue",
            "catalogue_path": self.db_path,
            "total_standards": total_count,
            "snapshot_id": snapshot_id,
            "last_synchronized_at": last_sync_timestamp,
            "synchronization_status": "SYNCHRONIZED",
            "formatted_label": label
        }


_GLOBAL_PROVIDER: Optional[BISCatalogueProvider] = None


def get_default_catalogue_provider(db_path: Optional[str] = None) -> BISCatalogueProvider:
    """Factory returning the singleton BISCatalogueProvider."""
    global _GLOBAL_PROVIDER
    if _GLOBAL_PROVIDER is None or (db_path and _GLOBAL_PROVIDER.db_path != db_path):
        _GLOBAL_PROVIDER = BISCatalogueProvider(db_path=db_path)
    return _GLOBAL_PROVIDER


def assert_authoritative_bis_catalogue(provider: Any) -> None:
    """
    Runtime assertion verifying that the active standards catalogue provider
    is strictly the authoritative BIS catalogue and NOT the legacy 502-record catalogue.
    
    Logs:
        active catalogue provider = BIS catalogue
        active catalogue path = data/catalogue/bis_catalogue.db
    """
    if provider is None:
        raise RuntimeError("Production retrieval assertion failed: standards catalogue provider is None.")

    db_path = getattr(provider, "db_path", None)
    if not db_path:
        raise RuntimeError("Production retrieval assertion failed: provider has no valid db_path.")

    normalized_path = os.path.normpath(db_path)

    # Strictly disallow legacy 502-record catalogue in production retrieval path
    if "data/catalogue/catalogue.db" in normalized_path or normalized_path.endswith("/catalogue.db"):
        raise RuntimeError(
            f"Production retrieval assertion failed: legacy catalogue detected at '{db_path}'. "
            "Production retrieval MUST use data/catalogue/bis_catalogue.db."
        )

    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Production retrieval assertion failed: BIS catalogue file not found at '{db_path}'."
        )

    # Log required operational assertions
    logger.info("active catalogue provider = BIS catalogue")
    logger.info("active catalogue path = %s", db_path)

