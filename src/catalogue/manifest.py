"""
Module: src/catalogue/manifest.py
Purpose: Audit manifest tracking catalogue ingestion runs, versioning,
and changes over time.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime, timezone


@dataclass
class IngestionManifest:
    """Audit manifest produced on every ingestion run."""
    snapshot_id: str                          # Unique identifier e.g. "snapshot_20260911_172500"
    source: str                               # e.g. "BIS_STANDARDS_EXPANDED_CATALOGUE"
    retrieved_at: str                         # ISO timestamp
    record_count: int = 0
    new_records: int = 0
    updated_records: int = 0
    unchanged_records: int = 0
    removed_records: int = 0
    validation_errors: int = 0
    error_details: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, manifests_dir: str = "data/catalogue/manifests") -> str:
        """Saves manifest to disk."""
        os.makedirs(manifests_dir, exist_ok=True)
        manifest_path = os.path.join(manifests_dir, f"manifest_{self.snapshot_id}.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return manifest_path

    @classmethod
    def load(cls, manifest_path: str) -> "IngestionManifest":
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
