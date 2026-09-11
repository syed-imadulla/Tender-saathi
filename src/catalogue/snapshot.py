"""
Module: src/catalogue/snapshot.py
Purpose: Point-in-time snapshot manager for catalogue versioning and auditability.
"""

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from src.catalogue.validator import StandardMasterRecord
from src.catalogue.manifest import IngestionManifest


class CatalogueSnapshotManager:
    """Manages versioned, point-in-time snapshots of the standards catalogue."""

    def __init__(
        self,
        snapshots_dir: str = "data/catalogue/snapshots",
        manifests_dir: str = "data/catalogue/manifests"
    ):
        self.snapshots_dir = snapshots_dir
        self.manifests_dir = manifests_dir
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.manifests_dir, exist_ok=True)

    def create_snapshot_id(self) -> str:
        """Generates a timestamped unique snapshot ID."""
        now = datetime.now(timezone.utc)
        return f"snapshot_{now.strftime('%Y%m%d_%H%M%S')}"

    def save_snapshot(
        self,
        records: List[StandardMasterRecord],
        snapshot_id: Optional[str] = None,
        source: str = "AUTHORITATIVE_CATALOGUE_INGESTION"
    ) -> Tuple[str, IngestionManifest]:
        """Saves records to a snapshot file and creates a corresponding manifest."""
        sid = snapshot_id or self.create_snapshot_id()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Load previous snapshot if any to compute diffs
        prev_records_map = self.get_latest_snapshot_records_map()

        curr_records_map = {r.canonical_id: r.to_dict() for r in records}

        new_count = 0
        updated_count = 0
        unchanged_count = 0

        for cid, r_dict in curr_records_map.items():
            if cid not in prev_records_map:
                new_count += 1
            else:
                prev_d = prev_records_map[cid]
                # Compare title, status, publication_year
                if (
                    prev_d.get("title") != r_dict.get("title") or
                    prev_d.get("status") != r_dict.get("status") or
                    prev_d.get("publication_year") != r_dict.get("publication_year")
                ):
                    updated_count += 1
                else:
                    unchanged_count += 1

        removed_count = sum(1 for cid in prev_records_map if cid not in curr_records_map)

        manifest = IngestionManifest(
            snapshot_id=sid,
            source=source,
            retrieved_at=now_iso,
            record_count=len(records),
            new_records=new_count,
            updated_records=updated_count,
            unchanged_records=unchanged_count,
            removed_records=removed_count,
            validation_errors=0,
            metadata={"record_ids": list(curr_records_map.keys())}
        )

        # Save snapshot file
        snapshot_file = os.path.join(self.snapshots_dir, f"{sid}.json")
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in records], f, indent=2, ensure_ascii=False)

        # Save manifest
        manifest.save(self.manifests_dir)

        return snapshot_file, manifest

    def get_latest_snapshot_path(self) -> Optional[str]:
        """Returns filepath of the most recent snapshot."""
        files = [
            f for f in os.listdir(self.snapshots_dir)
            if f.startswith("snapshot_") and f.endswith(".json")
        ]
        if not files:
            return None
        files.sort()
        return os.path.join(self.snapshots_dir, files[-1])

    def get_latest_snapshot_records_map(self) -> Dict[str, Dict[str, Any]]:
        """Returns a dict of canonical_id -> record for the latest snapshot."""
        latest_path = self.get_latest_snapshot_path()
        if not latest_path:
            return {}
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {item["canonical_id"]: item for item in data}
        except Exception:
            return {}

    def list_snapshots(self) -> List[str]:
        """Lists all available snapshot IDs."""
        files = [
            f[:-5] for f in os.listdir(self.snapshots_dir)
            if f.startswith("snapshot_") and f.endswith(".json")
        ]
        files.sort()
        return files
