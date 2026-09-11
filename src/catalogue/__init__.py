"""
Package: src.catalogue
Purpose: Ingestion, normalization, validation, snapshotting, and provenance
management for the large-scale real-world Indian Standards catalogue.
"""

from src.catalogue.provenance import (
    ProvenanceLevel,
    SourcePriority,
    CatalogueSourceInfo,
    assert_no_inferred_as_authoritative,
)
from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.catalogue.validator import (
    StandardMasterRecord,
    CatalogueValidator,
    LifecycleStatus,
)
from src.catalogue.snapshot import CatalogueSnapshotManager
from src.catalogue.manifest import IngestionManifest
from src.catalogue.loader import CatalogueLoader, IngestionMode

__all__ = [
    "ProvenanceLevel",
    "SourcePriority",
    "CatalogueSourceInfo",
    "assert_no_inferred_as_authoritative",
    "StandardIdentifierNormalizer",
    "StandardMasterRecord",
    "CatalogueValidator",
    "LifecycleStatus",
    "CatalogueSnapshotManager",
    "IngestionManifest",
    "CatalogueLoader",
    "IngestionMode",
]
