"""
Module: src/catalogue/snapshot_manager.py
Purpose: Production snapshot manager providing atomic promotion, CURRENT manifest switching,
and fail-safe rollback guarantees.

Key Invariants:
1. Versioned Immutable Snapshots:
   Stored in data/catalogue/snapshots/<snapshot_id>/ containing all DB, index, and manifest files.
2. Single Atomic CURRENT Pointer:
   data/catalogue/current_snapshot.json points to exactly one active snapshot.
3. POSIX Atomic Replace:
   current_snapshot.json is updated via atomic rename (os.replace).
4. Rollback / Abort Safety:
   Any failed promotion aborts immediately and leaves current_snapshot.json untouched.
"""

import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages active production snapshot resolution, atomic promotion, and rollback."""

    def __init__(
        self,
        catalogue_dir: str = "data/catalogue",
        snapshots_dir: str = "data/catalogue/snapshots",
        pointer_filename: str = "current_snapshot.json"
    ):
        self.catalogue_dir = catalogue_dir
        self.snapshots_dir = snapshots_dir
        self.pointer_path = os.path.join(self.catalogue_dir, pointer_filename)
        os.makedirs(self.catalogue_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def get_current_snapshot(self) -> Optional[Dict[str, Any]]:
        """Returns metadata for the currently active production snapshot."""
        if not os.path.exists(self.pointer_path):
            return None
        try:
            with open(self.pointer_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read current_snapshot.json: %s", e)
            return None

    def promote_staging_snapshot(
        self,
        staging_dir: str,
        snapshot_id: str
    ) -> bool:
        """
        Atomically promotes a validated staging snapshot into production.
        If any validation or filesystem error occurs, the previous production snapshot
        remains completely unchanged.
        """
        manifest_path = os.path.join(staging_dir, "snapshot_manifest.json")
        if not os.path.exists(manifest_path):
            logger.error("Cannot promote %s: missing snapshot_manifest.json", staging_dir)
            return False

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        if manifest.get("validation_status") != "VALIDATED":
            logger.error("Cannot promote %s: status is not VALIDATED (%s)", staging_dir, manifest.get("validation_status"))
            return False

        target_dir = os.path.join(self.snapshots_dir, snapshot_id)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        try:
            # Copy validated snapshot into immutable production snapshots directory
            shutil.copytree(staging_dir, target_dir)

            # Query DB inside target directory to retrieve fulltext and metadata counts
            db_path = os.path.join(target_dir, "bis_catalogue.db")
            full_text_count = 0
            metadata_only_count = manifest.get("record_count", 0)
            historical_edition_count = 0

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='standards_fulltext';")
                if cursor.fetchone()[0] > 0:
                    cursor.execute("SELECT count(*) FROM standards_fulltext WHERE metadata_only = 0;")
                    full_text_count = cursor.fetchone()[0] or 0
                    cursor.execute("SELECT count(*) FROM standards_fulltext WHERE metadata_only = 1;")
                    metadata_only_count = cursor.fetchone()[0] or 0
                    cursor.execute("SELECT count(*) FROM standards_fulltext WHERE is_historical_edition = 1;")
                    historical_edition_count = cursor.fetchone()[0] or 0

            # Prepare new atomic CURRENT pointer
            new_current_data = {
                "snapshot_id": snapshot_id,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
                "snapshot_dir": target_dir,
                "paths": {
                    "db_path": db_path,
                    "bm25_path": os.path.join(target_dir, "bis_bm25_index.json"),
                    "semantic_embeddings_path": os.path.join(target_dir, "bis_semantic_embeddings.npy"),
                    "semantic_doc_ids_path": os.path.join(target_dir, "bis_semantic_doc_ids.json"),
                    "semantic_doc_hashes_path": os.path.join(target_dir, "bis_semantic_doc_hashes.json"),
                    "index_manifest_path": os.path.join(target_dir, "bis_index_manifest.json"),
                    "snapshot_manifest_path": os.path.join(target_dir, "snapshot_manifest.json"),
                },
                "record_count": manifest.get("record_count", 0),
                "full_text_count": full_text_count,
                "metadata_only_count": metadata_only_count,
                "historical_edition_count": historical_edition_count,
                "validation_status": "VALIDATED"
            }

            # Atomic file swap via tmp file and os.replace
            tmp_pointer = self.pointer_path + ".tmp"
            with open(tmp_pointer, "w", encoding="utf-8") as f:
                json.dump(new_current_data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_pointer, self.pointer_path)

            logger.info("Successfully and atomically promoted snapshot %s to production.", snapshot_id)
            return True

        except Exception as e:
            logger.error("Failed during promotion of snapshot %s: %s", snapshot_id, e)
            # Cleanup target dir if failed halfway
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            tmp_pointer = self.pointer_path + ".tmp"
            if os.path.exists(tmp_pointer):
                os.remove(tmp_pointer)
            return False
