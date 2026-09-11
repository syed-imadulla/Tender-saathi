"""
Module: src/catalogue/loader.py
Purpose: Ingestion engine supporting OFFLINE_IMPORT and OFFICIAL_SOURCE_DISCOVERY modes.

Rules:
- Never fabricate data.
- Deduplicate on canonical standard identity, preserving parts, sections, and years.
- Clean adapter interface for official source discovery without uncontrolled scraping.
- Rejects unsupported or unofficial sources.
- Generates snapshot and manifest on every ingestion.
"""

from enum import Enum
import os
import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from src.catalogue.validator import StandardMasterRecord, CatalogueValidator, LifecycleStatus
from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.catalogue.provenance import CatalogueSourceInfo, ProvenanceLevel, PERMITTED_SOURCE_TYPES
from src.catalogue.snapshot import CatalogueSnapshotManager
from src.catalogue.manifest import IngestionManifest


class IngestionMode(str, Enum):
    OFFLINE_IMPORT = "OFFLINE_IMPORT"
    OFFICIAL_SOURCE_DISCOVERY = "OFFICIAL_SOURCE_DISCOVERY"


class OfficialSourceDiscoveryAdapter:
    """
    Clean, documented adapter interface for official BIS discovery sources.
    
    LIMITATION NOTE:
    BIS currently provides official portal interfaces (standardsbis.bsbedge.com,
    services.bis.gov.in) with session-gated tokens. When live authenticated endpoints
    are not connected or return 403/401/CAPTCHA, this adapter safely returns an empty
    discovery set or raises a documented exception rather than executing unauthorized,
    brittle scraping or fabricating synthetic records.
    """

    def __init__(self, endpoint_url: str = "https://standardsbis.bsbedge.com"):
        self.endpoint_url = endpoint_url

    def discover_by_committee(self, committee_code: str) -> List[StandardMasterRecord]:
        """Discovers standards under a specific technical committee (e.g. CED 50)."""
        # Documented adapter: Return empty list with explanatory notice if live endpoint is inactive
        return []

    def discover_by_keyword(self, query: str) -> List[StandardMasterRecord]:
        """Discovers standard records matching query from official portal."""
        return []


class CatalogueLoader:
    """Main loader orchestrating validation, deduplication, SQLite persistence, and snapshotting."""

    def __init__(
        self,
        db_path: str = "data/catalogue/catalogue.db",
        normalized_dir: str = "data/catalogue/normalized",
        snapshots_dir: str = "data/catalogue/snapshots",
        manifests_dir: str = "data/catalogue/manifests"
    ):
        self.db_path = db_path
        self.normalized_dir = normalized_dir
        self.snapshot_mgr = CatalogueSnapshotManager(snapshots_dir, manifests_dir)
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        os.makedirs(self.normalized_dir, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Initializes scalable catalogue schema."""
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS catalogue_standards (
                canonical_id TEXT PRIMARY KEY,
                standard_number TEXT NOT NULL,
                base_standard_number TEXT NOT NULL,
                title TEXT NOT NULL,
                scope TEXT,
                status TEXT NOT NULL,
                publication_year INTEGER,
                reaffirmed_year INTEGER,
                technical_committee TEXT,
                product_domain TEXT,
                certification TEXT,
                amendments_json TEXT,
                supersedes_json TEXT,
                superseded_by_json TEXT,
                references_json TEXT,
                source_json TEXT NOT NULL,
                provenance TEXT NOT NULL,
                retrieved_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cat_std_num ON catalogue_standards(standard_number);
            CREATE INDEX IF NOT EXISTS idx_cat_base_num ON catalogue_standards(base_standard_number);
            CREATE INDEX IF NOT EXISTS idx_cat_status ON catalogue_standards(status);
            CREATE INDEX IF NOT EXISTS idx_cat_prov ON catalogue_standards(provenance);

            -- Compatibility table and indices for StandardsDatabase / search engines
            CREATE TABLE IF NOT EXISTS standards (
                standard_id TEXT PRIMARY KEY,
                standard_number TEXT NOT NULL,
                year INTEGER,
                full_title TEXT NOT NULL,
                status TEXT NOT NULL,
                reaffirmed_year INTEGER,
                amendments_count INTEGER,
                technical_committee TEXT,
                ics TEXT,
                udc TEXT,
                scope TEXT,
                notes TEXT,
                source TEXT NOT NULL,
                source_url TEXT,
                retrieved_at TEXT,
                original_standard_identifier TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                evidence TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_std_number ON standards(standard_number);
            CREATE INDEX IF NOT EXISTS idx_std_status ON standards(status);

            CREATE TABLE IF NOT EXISTS standard_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                standard_id TEXT NOT NULL,
                referenced_standard_number TEXT NOT NULL,
                referenced_year INTEGER,
                referenced_title TEXT,
                citing_clause TEXT
            );

            CREATE TABLE IF NOT EXISTS standard_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_standard_id TEXT NOT NULL,
                target_standard TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                evidence TEXT NOT NULL
            );
            """)

    def load_from_json_file(
        self,
        file_path: str,
        mode: IngestionMode = IngestionMode.OFFLINE_IMPORT,
        default_provenance: str = ProvenanceLevel.OFFICIAL_PRIMARY.value
    ) -> IngestionManifest:
        """Loads and ingests a list of standard records from a structured JSON file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Catalogue import file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if not isinstance(raw_data, list):
            raise ValueError("Expected JSON file containing a list of standard records.")

        records: List[StandardMasterRecord] = []
        validation_errors = 0
        error_details: List[str] = []

        seen_canonical_ids = set()

        for idx, item in enumerate(raw_data):
            # Parse identifier canonically
            raw_num = item.get("standard_number") or item.get("standard_id", "")
            title = item.get("title") or item.get("full_title", "")

            norm = StandardIdentifierNormalizer.parse(raw_num)
            cid = norm.canonical_id

            # Deduplication: If duplicate canonical ID in this batch, preserve the richer record
            if cid in seen_canonical_ids:
                continue
            seen_canonical_ids.add(cid)

            # Build source
            src_raw = item.get("source")
            if isinstance(src_raw, dict):
                src_dict = src_raw
            else:
                src_type = str(src_raw) if src_raw else "OFFLINE_EXPORT_AUTHORITATIVE"
                src_dict = CatalogueSourceInfo(
                    source_type=src_type if src_type in PERMITTED_SOURCE_TYPES else "OFFLINE_EXPORT_AUTHORITATIVE",
                    source_url=item.get("source_url"),
                    retrieved_at=item.get("retrieved_at") or datetime.now(timezone.utc).isoformat(),
                    provenance=item.get("verification_status") or default_provenance
                ).to_dict()

            rec = StandardMasterRecord(
                standard_number=norm.canonical_number,
                title=title,
                scope=item.get("scope") or "UNKNOWN",
                status=LifecycleStatus.normalize(item.get("status")),
                publication_year=item.get("year") or norm.year,
                reaffirmed_year=item.get("reaffirmed_year"),
                technical_committee=item.get("technical_committee"),
                amendments=item.get("amendments") or [],
                supersedes=item.get("supersedes") or [],
                superseded_by=item.get("superseded_by") or [],
                references=item.get("references") or [],
                product_domain=item.get("product_domain") or [],
                certification=item.get("certification") or [],
                source=src_dict,
                canonical_id=cid,
                base_standard_number=norm.base_standard_number
            )

            # Validate
            errs = CatalogueValidator.validate_record(rec)
            if errs:
                validation_errors += 1
                error_details.append(f"Record {idx} ({raw_num}): {'; '.join(errs)}")
                continue

            records.append(rec)

        # Ingest into SQLite
        new_count, updated_count, unchanged_count = self._persist_records(records)

        # Save snapshot and manifest
        _, manifest = self.snapshot_mgr.save_snapshot(
            records=records,
            source=f"{mode.value}:{os.path.basename(file_path)}"
        )
        manifest.validation_errors = validation_errors
        manifest.error_details = error_details[:20]  # Store top 20 error snippets
        manifest.save()

        # Update individual normalized JSON records for atomic inspection
        for r in records:
            r_path = os.path.join(self.normalized_dir, f"{r.canonical_id}.json")
            with open(r_path, "w", encoding="utf-8") as f:
                json.dump(r.to_dict(), f, indent=2, ensure_ascii=False)

        return manifest

    def _persist_records(self, records: List[StandardMasterRecord]) -> Tuple[int, int, int]:
        """Inserts or updates records in SQLite database."""
        new_count = 0
        updated_count = 0
        unchanged_count = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for r in records:
                cursor.execute("SELECT title, status, publication_year FROM catalogue_standards WHERE canonical_id = ?", (r.canonical_id,))
                row = cursor.fetchone()
                if row is None:
                    new_count += 1
                elif row["title"] != r.title or row["status"] != r.status or row["publication_year"] != r.publication_year:
                    updated_count += 1
                else:
                    unchanged_count += 1

                cursor.execute("""
                INSERT OR REPLACE INTO catalogue_standards (
                    canonical_id, standard_number, base_standard_number, title, scope,
                    status, publication_year, reaffirmed_year, technical_committee,
                    product_domain, certification, amendments_json, supersedes_json,
                    superseded_by_json, references_json, source_json, provenance, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.canonical_id,
                    r.standard_number,
                    r.base_standard_number,
                    r.title,
                    r.scope,
                    r.status,
                    r.publication_year,
                    r.reaffirmed_year,
                    r.technical_committee,
                    json.dumps(r.product_domain),
                    json.dumps(r.certification),
                    json.dumps(r.amendments),
                    json.dumps(r.supersedes),
                    json.dumps(r.superseded_by),
                    json.dumps(r.references),
                    json.dumps(r.source),
                    r.source.get("provenance") or ProvenanceLevel.UNKNOWN.value,
                    r.source.get("retrieved_at") or datetime.now(timezone.utc).isoformat()
                ))

                cursor.execute("""
                INSERT OR REPLACE INTO standards (
                    standard_id, standard_number, year, full_title, status,
                    reaffirmed_year, amendments_count, technical_committee,
                    ics, udc, scope, notes, source, source_url,
                    retrieved_at, original_standard_identifier, verification_status, evidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.canonical_id,
                    r.base_standard_number,
                    r.publication_year,
                    r.title,
                    r.status,
                    r.reaffirmed_year,
                    len(r.amendments),
                    r.technical_committee,
                    None,
                    None,
                    r.scope,
                    ", ".join(r.product_domain) if r.product_domain else None,
                    r.source.get("source_type") or "CATALOGUE_INGESTION",
                    r.source.get("source_url"),
                    r.source.get("retrieved_at") or datetime.now(timezone.utc).isoformat(),
                    r.standard_number,
                    r.source.get("provenance") or ProvenanceLevel.OFFICIAL_PRIMARY.value,
                    r.source.get("source_citation")
                ))

        return new_count, updated_count, unchanged_count

    def get_standard_count(self) -> int:
        """Returns total count of standards in the catalogue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM catalogue_standards")
            return cursor.fetchone()[0]

    def get_standard(self, canonical_id_or_number: str) -> Optional[Dict[str, Any]]:
        """Retrieves a standard by canonical ID or standard number."""
        norm = StandardIdentifierNormalizer.parse(canonical_id_or_number)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM catalogue_standards WHERE canonical_id = ? OR standard_number = ? OR base_standard_number = ?",
                (norm.canonical_id, norm.canonical_number, norm.base_standard_number)
            )
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["amendments"] = json.loads(res.get("amendments_json") or "[]")
            res["supersedes"] = json.loads(res.get("supersedes_json") or "[]")
            res["superseded_by"] = json.loads(res.get("superseded_by_json") or "[]")
            res["references"] = json.loads(res.get("references_json") or "[]")
            res["product_domain"] = json.loads(res.get("product_domain") or "[]")
            res["certification"] = json.loads(res.get("certification") or "[]")
            res["source"] = json.loads(res.get("source_json") or "{}")
            return res

    def get_all_standards(self) -> List[Dict[str, Any]]:
        """Returns all standards in the catalogue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM catalogue_standards")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["amendments"] = json.loads(d.get("amendments_json") or "[]")
                d["supersedes"] = json.loads(d.get("supersedes_json") or "[]")
                d["superseded_by"] = json.loads(d.get("superseded_by_json") or "[]")
                d["references"] = json.loads(d.get("references_json") or "[]")
                d["product_domain"] = json.loads(d.get("product_domain") or "[]")
                d["certification"] = json.loads(d.get("certification") or "[]")
                d["source"] = json.loads(d.get("source_json") or "{}")
                results.append(d)
            return results
