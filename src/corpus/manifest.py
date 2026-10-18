"""
src/corpus/manifest.py — Versioned Corpus Manifest & Document Metadata

Defines data models, licensing categories, and ingestion statuses for full-text
standards documents, separating source URLs from documentary citations.
"""

from __future__ import annotations

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple


class LicensingStatus(str, Enum):
    """Licensing and permitted usage status for standards documents."""
    STATUTORY_PUBLIC_GAZETTE = "STATUTORY_PUBLIC_GAZETTE"  # Government gazette / statutory orders (public domain)
    PERMITTED_TEST_FIXTURE = "PERMITTED_TEST_FIXTURE"        # Synthetic or authorized fixtures for testing
    RESTRICTED_BIS_COPYRIGHT = "RESTRICTED_BIS_COPYRIGHT"    # Standard under proprietary copyright; no distribution
    ACADEMIC_RESEARCH_USE = "ACADEMIC_RESEARCH_USE"          # Lawful research copy under fair dealing
    UNKNOWN = "UNKNOWN"                                      # Unspecified licensing status


class IngestionStatus(str, Enum):
    """Lifecycle status of a document in the ingestion pipeline."""
    REGISTERED = "REGISTERED"          # Recorded in manifest, file not yet extracted
    EXTRACTED = "EXTRACTED"            # Text successfully extracted and quality checked
    OCR_REQUIRED = "OCR_REQUIRED"      # Scanned PDF; image-based; needs OCR
    QUALITY_FAILED = "QUALITY_FAILED"  # Text density or character encoding failed checks
    CORRUPT = "CORRUPT"                # File header invalid or unparseable
    FAILED = "FAILED"                  # Extraction crashed or encountered unrecoverable error


@dataclass
class CorpusDocumentRecord:
    """Versioned provenance and extraction record for a standards document."""
    doc_id: str                              # Unique internal document ID, e.g. "DOC-IS-1180-P1-2014"
    standard_number: str                     # e.g. "IS 1180 (Part 1)"
    edition_year: Optional[int] = None       # e.g. 2014
    document_title: str = ""                 # Official title
    source_url: Optional[str] = None         # Official web URL if available (http/https only)
    source_citation: Optional[str] = None    # Documentary or gazette citation (e.g. "Gazette Notification S.O. 4467(E)")
    acquisition_date: str = ""               # ISO-8601 date, e.g. "2026-10-18"
    source_name: str = "OFFICIAL_REPOSITORY" # Acquisition source name
    file_sha256: str = ""                    # SHA-256 of the raw PDF file
    file_size_bytes: int = 0                 # File size in bytes
    file_format: str = "PDF"                 # File extension / format
    licensing_status: str = LicensingStatus.UNKNOWN.value
    usage_restrictions: str = ""             # e.g. "Internal test fixture only"
    extraction_method: str = "PYMUPDF_TEXT"  # e.g. "PYMUPDF_V1", "PYPDF_FALLBACK"
    software_version: str = "1.0.0"          # Subsystem software version
    ingestion_status: str = IngestionStatus.REGISTERED.value
    failure_reasons: List[str] = field(default_factory=list)
    page_count: int = 0
    extracted_at: Optional[str] = None
    table_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CorpusDocumentRecord:
        # Filter unexpected keys for forward compatibility
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class CorpusManifest:
    """
    Manages the persistent, versioned registry of corpus documents.
    Enforces hash uniqueness, edition segregation, and licensing tracking.
    """

    def __init__(self, manifest_path: Optional[str] = None):
        self.manifest_path = manifest_path or "data/standards/corpus_manifest.json"
        self.documents: Dict[str, CorpusDocumentRecord] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("documents", []):
                        rec = CorpusDocumentRecord.from_dict(item)
                        self.documents[rec.doc_id] = rec
            except Exception:
                self.documents = {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.manifest_path)), exist_ok=True)
        payload = {
            "version": "1.0.0",
            "manifest_schema": "tender_saathi_corpus_manifest_v1",
            "total_documents": len(self.documents),
            "documents": [doc.to_dict() for doc in self.documents.values()]
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def register_document(self, record: CorpusDocumentRecord) -> Tuple[bool, Optional[str]]:
        """
        Registers a document record in the manifest.
        Rejects duplicate file hashes unless it's the exact same document ID.
        """
        # Validate licensing status
        if record.licensing_status not in [e.value for e in LicensingStatus]:
            record.licensing_status = LicensingStatus.UNKNOWN.value

        # Check for duplicate file hash across different doc_ids
        for existing in self.documents.values():
            if existing.file_sha256 and existing.file_sha256 == record.file_sha256:
                if existing.doc_id != record.doc_id:
                    return False, f"Duplicate file hash: matches existing doc_id '{existing.doc_id}'"

        self.documents[record.doc_id] = record
        self.save()
        return True, None

    def get_document(self, doc_id: str) -> Optional[CorpusDocumentRecord]:
        return self.documents.get(doc_id)

    def get_documents_by_standard(self, standard_number: str, edition_year: Optional[int] = None) -> List[CorpusDocumentRecord]:
        matches = []
        for doc in self.documents.values():
            if doc.standard_number.strip().upper() == standard_number.strip().upper():
                if edition_year is None or doc.edition_year == edition_year:
                    matches.append(doc)
        return matches
