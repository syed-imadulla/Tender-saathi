"""
Module: src/catalogue/snapshot_builder.py
Purpose: Builds and validates complete, versioned catalogue snapshots in staging.

Key Responsibilities:
1. Assembles snapshot inside data/catalogue/staging/<snapshot_id>/.
2. Executes SQLite database integrity check (PRAGMA integrity_check).
3. Enforces canonical ID uniqueness and non-null constraints.
4. Builds BM25 and Semantic indexes for the snapshot.
5. Enforces Index Identity Invariants:
   - Every BM25 document maps to exactly one canonical standard ID.
   - Every semantic vector maps to exactly one canonical standard ID.
   - set(DB IDs) == set(BM25 IDs) == set(Semantic IDs).
   - Bi-directional reversibility (doc -> canonical ID -> DB row).
6. Computes SHA-256 cryptographic hashes for all snapshot artifacts.
7. Generates snapshot_manifest.json.
"""

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple

import numpy as np

from src.catalogue.normalizer import StandardIdentifierNormalizer

logger = logging.getLogger(__name__)


@dataclass
class SnapshotValidationReport:
    snapshot_id: str
    db_integrity_ok: bool
    total_db_records: int
    unique_canonical_ids: int
    null_canonical_ids: int
    quarantine_count: int
    bm25_doc_count: int
    semantic_doc_count: int
    bm25_id_set_matches_db: bool
    semantic_id_set_matches_db: bool
    index_bidirectional_reversible: bool
    artifact_hashes: Dict[str, str]
    is_valid: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SnapshotBuilder:
    """Constructs and validates immutable versioned snapshots."""

    def __init__(self, staging_base_dir: str = "data/catalogue/staging"):
        self.staging_base_dir = staging_base_dir
        os.makedirs(self.staging_base_dir, exist_ok=True)

    @staticmethod
    def compute_sha256(filepath: str) -> str:
        """Computes SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def create_staging_snapshot(
        self,
        snapshot_id: str,
        source_db_path: str,
        source_bm25_path: str,
        source_semantic_embeddings_path: str,
        source_semantic_doc_ids_path: str,
        source_semantic_doc_hashes_path: str,
        source_index_manifest_path: str
    ) -> Tuple[str, SnapshotValidationReport]:
        """
        Assembles a staging snapshot from source artifacts and rigorously validates it.
        """
        snapshot_dir = os.path.join(self.staging_base_dir, snapshot_id)
        if os.path.exists(snapshot_dir):
            shutil.rmtree(snapshot_dir)
        os.makedirs(snapshot_dir, exist_ok=True)

        target_db = os.path.join(snapshot_dir, "bis_catalogue.db")
        target_bm25 = os.path.join(snapshot_dir, "bis_bm25_index.json")
        target_embeddings = os.path.join(snapshot_dir, "bis_semantic_embeddings.npy")
        target_doc_ids = os.path.join(snapshot_dir, "bis_semantic_doc_ids.json")
        target_doc_hashes = os.path.join(snapshot_dir, "bis_semantic_doc_hashes.json")
        target_index_manifest = os.path.join(snapshot_dir, "bis_index_manifest.json")

        # Copy files into staging directory
        shutil.copy2(source_db_path, target_db)
        shutil.copy2(source_bm25_path, target_bm25)
        shutil.copy2(source_semantic_embeddings_path, target_embeddings)
        shutil.copy2(source_semantic_doc_ids_path, target_doc_ids)
        shutil.copy2(source_semantic_doc_hashes_path, target_doc_hashes)
        shutil.copy2(source_index_manifest_path, target_index_manifest)

        # Ensure fulltext and chunk provenance schema is present in database
        from src.catalogue.fulltext_fetcher import FullTextManager
        FullTextManager(db_path=target_db)

        # Validate staging snapshot
        report = self.validate_snapshot(snapshot_dir, snapshot_id)
        if not report.is_valid:
            logger.error("Staging snapshot %s validation failed: %s", snapshot_id, report.error_message)
            return snapshot_dir, report

        # Write validation report
        val_report_path = os.path.join(snapshot_dir, "validation_report.json")
        with open(val_report_path, "w", encoding="utf-8") as vf:
            json.dump(report.to_dict(), vf, indent=2)

        # Write snapshot manifest
        manifest_path = os.path.join(snapshot_dir, "snapshot_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "snapshot_id": snapshot_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "record_count": report.total_db_records,
                "validation_status": "VALIDATED",
                "files": report.artifact_hashes
            }, f, indent=2, ensure_ascii=False)

        # Re-hash manifest and update
        report.artifact_hashes["snapshot_manifest.json"] = self.compute_sha256(manifest_path)

        logger.info("Staging snapshot %s successfully built and validated.", snapshot_id)
        return snapshot_dir, report

    def validate_snapshot(self, snapshot_dir: str, snapshot_id: str) -> SnapshotValidationReport:
        """
        Rigorously validates database integrity, canonical ID constraints, and index invariants.
        """
        db_path = os.path.join(snapshot_dir, "bis_catalogue.db")
        bm25_path = os.path.join(snapshot_dir, "bis_bm25_index.json")
        embeddings_path = os.path.join(snapshot_dir, "bis_semantic_embeddings.npy")
        doc_ids_path = os.path.join(snapshot_dir, "bis_semantic_doc_ids.json")
        doc_hashes_path = os.path.join(snapshot_dir, "bis_semantic_doc_hashes.json")
        index_manifest_path = os.path.join(snapshot_dir, "bis_index_manifest.json")

        required_files = [
            ("bis_catalogue.db", db_path),
            ("bis_bm25_index.json", bm25_path),
            ("bis_semantic_embeddings.npy", embeddings_path),
            ("bis_semantic_doc_ids.json", doc_ids_path),
            ("bis_semantic_doc_hashes.json", doc_hashes_path),
            ("bis_index_manifest.json", index_manifest_path),
        ]

        for fname, fpath in required_files:
            if not os.path.exists(fpath):
                return SnapshotValidationReport(
                    snapshot_id=snapshot_id, db_integrity_ok=False, total_db_records=0,
                    unique_canonical_ids=0, null_canonical_ids=0, quarantine_count=0,
                    bm25_doc_count=0, semantic_doc_count=0, bm25_id_set_matches_db=False,
                    semantic_id_set_matches_db=False, index_bidirectional_reversible=False,
                    artifact_hashes={}, is_valid=False, error_message=f"Missing file {fname}"
                )

        # 1. Database Integrity Check
        db_integrity_ok = False
        total_db_records = 0
        unique_canonical_ids = 0
        null_canonical_ids = 0
        quarantine_count = 0
        db_canonical_ids: Set[str] = set()

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                res = cursor.fetchone()
                if res and res[0] == "ok":
                    db_integrity_ok = True

                # Determine primary standards table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('catalogue_standards', 'standards');")
                tables = [r[0] for r in cursor.fetchall()]
                std_table = "catalogue_standards" if "catalogue_standards" in tables else "standards"
                id_col = "canonical_id" if std_table == "catalogue_standards" else "standard_id"

                cursor.execute(f"SELECT count(*), count(DISTINCT {id_col}), sum(case when {id_col} is null or {id_col}='' then 1 else 0 end) FROM {std_table};")
                tot, uniq, nulls = cursor.fetchone()
                total_db_records = tot or 0
                unique_canonical_ids = uniq or 0
                null_canonical_ids = nulls or 0

                cursor.execute(f"SELECT {id_col} FROM {std_table};")
                db_canonical_ids = set(r[0] for r in cursor.fetchall())

                # Check quarantine table if exists
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('quarantine_records', 'standards_quarantine');")
                if cursor.fetchone()[0] > 0:
                    q_table = "quarantine_records" if "quarantine_records" in [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()] else "standards_quarantine"
                    cursor.execute(f"SELECT count(*) FROM {q_table};")
                    quarantine_count = cursor.fetchone()[0] or 0

        except Exception as e:
            return SnapshotValidationReport(
                snapshot_id=snapshot_id, db_integrity_ok=False, total_db_records=0,
                unique_canonical_ids=0, null_canonical_ids=0, quarantine_count=0,
                bm25_doc_count=0, semantic_doc_count=0, bm25_id_set_matches_db=False,
                semantic_id_set_matches_db=False, index_bidirectional_reversible=False,
                artifact_hashes={}, is_valid=False, error_message=f"DB integrity check exception: {e}"
            )

        if not db_integrity_ok:
            return SnapshotValidationReport(
                snapshot_id=snapshot_id, db_integrity_ok=False, total_db_records=total_db_records,
                unique_canonical_ids=unique_canonical_ids, null_canonical_ids=null_canonical_ids,
                quarantine_count=quarantine_count, bm25_doc_count=0, semantic_doc_count=0,
                bm25_id_set_matches_db=False, semantic_id_set_matches_db=False,
                index_bidirectional_reversible=False, artifact_hashes={}, is_valid=False,
                error_message="PRAGMA integrity_check failed"
            )

        if total_db_records == 0 or null_canonical_ids > 0 or total_db_records != unique_canonical_ids:
            return SnapshotValidationReport(
                snapshot_id=snapshot_id, db_integrity_ok=True, total_db_records=total_db_records,
                unique_canonical_ids=unique_canonical_ids, null_canonical_ids=null_canonical_ids,
                quarantine_count=quarantine_count, bm25_doc_count=0, semantic_doc_count=0,
                bm25_id_set_matches_db=False, semantic_id_set_matches_db=False,
                index_bidirectional_reversible=False, artifact_hashes={}, is_valid=False,
                error_message=f"DB records validation failed (tot={total_db_records}, uniq={unique_canonical_ids}, nulls={null_canonical_ids})"
            )

        # 2. BM25 Index Invariant Check
        with open(bm25_path, "r", encoding="utf-8") as f:
            bm25_data = json.load(f)
        bm25_doc_ids = bm25_data.get("doc_ids", [])
        bm25_canonical_set = set(doc_id.split("#")[0] for doc_id in bm25_doc_ids)

        bm25_id_set_matches_db = (bm25_canonical_set == db_canonical_ids)

        # 3. Semantic Index Invariant Check
        with open(doc_ids_path, "r", encoding="utf-8") as f:
            semantic_doc_ids = json.load(f)
        semantic_embeddings = np.load(embeddings_path)

        if len(semantic_doc_ids) != len(semantic_embeddings):
            return SnapshotValidationReport(
                snapshot_id=snapshot_id, db_integrity_ok=True, total_db_records=total_db_records,
                unique_canonical_ids=unique_canonical_ids, null_canonical_ids=null_canonical_ids,
                quarantine_count=quarantine_count, bm25_doc_count=len(bm25_doc_ids),
                semantic_doc_count=len(semantic_doc_ids), bm25_id_set_matches_db=bm25_id_set_matches_db,
                semantic_id_set_matches_db=False, index_bidirectional_reversible=False,
                artifact_hashes={}, is_valid=False,
                error_message=f"Semantic vectors ({len(semantic_embeddings)}) != doc_ids ({len(semantic_doc_ids)})"
            )

        semantic_canonical_set = set(doc_id.split("#")[0] for doc_id in semantic_doc_ids)
        semantic_id_set_matches_db = (semantic_canonical_set == db_canonical_ids)

        # 4. Bi-directional Reversibility Check
        # Every index doc ID resolves to a valid DB canonical ID
        bm25_valid = all(doc_id.split("#")[0] in db_canonical_ids for doc_id in bm25_doc_ids)
        semantic_valid = all(doc_id.split("#")[0] in db_canonical_ids for doc_id in semantic_doc_ids)
        index_reversible = bm25_valid and semantic_valid and bm25_id_set_matches_db and semantic_id_set_matches_db

        # 5. Cryptographic SHA-256 Hashes
        artifact_hashes = {
            fname: self.compute_sha256(fpath)
            for fname, fpath in required_files
        }

        is_valid = (
            db_integrity_ok and
            null_canonical_ids == 0 and
            total_db_records == unique_canonical_ids and
            bm25_id_set_matches_db and
            semantic_id_set_matches_db and
            index_reversible
        )

        error_msg = None if is_valid else (
            f"Index invariant failure: bm25_match={bm25_id_set_matches_db}, "
            f"sem_match={semantic_id_set_matches_db}, reversible={index_reversible}"
        )

        return SnapshotValidationReport(
            snapshot_id=snapshot_id,
            db_integrity_ok=db_integrity_ok,
            total_db_records=total_db_records,
            unique_canonical_ids=unique_canonical_ids,
            null_canonical_ids=null_canonical_ids,
            quarantine_count=quarantine_count,
            bm25_doc_count=len(bm25_doc_ids),
            semantic_doc_count=len(semantic_doc_ids),
            bm25_id_set_matches_db=bm25_id_set_matches_db,
            semantic_id_set_matches_db=semantic_id_set_matches_db,
            index_bidirectional_reversible=index_reversible,
            artifact_hashes=artifact_hashes,
            is_valid=is_valid,
            error_message=error_msg
        )
