"""
api/ingestion/document_model.py — Normalized internal document representation.

All document types (text, PDF, image, multi-page) converge into a Document
before being passed to the analysis pipeline.  No analysis logic lives here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


# ---------------------------------------------------------------------------
# Page-level result
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    """Represents one page (or one image) worth of extracted content."""

    page_number: int
    """1-indexed page number within the document."""

    source_type: str
    """One of: 'text', 'pdf', 'image', 'ocr'."""

    extracted_text: str
    """The final extracted / OCR'd text for this page."""

    ocr_used: bool = False
    """True when an OCR engine was invoked for this page."""

    language: Optional[str] = None
    """BCP-47 language tag detected by OCR, e.g. 'en', 'hi'.  None if unknown."""

    confidence: Optional[float] = None
    """OCR confidence in [0.0, 1.0].  None when the engine cannot provide a
    reliable value — never invented."""

    ocr_quality_flag: Optional[str] = None
    """One of: None, 'LOW', 'MEDIUM', 'HIGH'.  Set when ocr_used=True."""

    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    """Engine-specific extras (word boxes, block counts, etc.)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "source_type": self.source_type,
            "extracted_text": self.extracted_text,
            "ocr_used": self.ocr_used,
            "language": self.language,
            "confidence": self.confidence,
            "ocr_quality_flag": self.ocr_quality_flag,
        }


# ---------------------------------------------------------------------------
# Document-level metadata
# ---------------------------------------------------------------------------

@dataclass
class IngestionMetadata:
    """Provenance and quality metadata for a document."""

    source_name: str = "unknown"
    """Original filename or source description."""

    source_type: str = "unknown"
    """Top-level type: 'text', 'pdf', 'image', 'multi_image'."""

    file_size_bytes: int = 0
    """Size of the original uploaded file(s) in bytes."""

    page_count: int = 0
    """Total number of pages/images processed."""

    ocr_pages: int = 0
    """Number of pages that required OCR."""

    any_ocr_low_quality: bool = False
    """True when at least one page has ocr_quality_flag='LOW'."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "ocr_pages": self.ocr_pages,
            "any_ocr_low_quality": self.any_ocr_low_quality,
        }


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

@dataclass
class Document:
    """
    Normalized document ready for the analysis pipeline.

    Future file types (DOCX, scanned PDF, multi-image) all produce a Document
    so that the downstream pipeline does not need to know the source type.
    """

    metadata: IngestionMetadata = field(default_factory=IngestionMetadata)
    pages: List[PageResult] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience factories
    # ------------------------------------------------------------------

    @classmethod
    def from_text(cls, text: str, source_name: str = "text input") -> "Document":
        """Wrap a plain text string into a single-page Document."""
        meta = IngestionMetadata(
            source_name=source_name,
            source_type="text",
            file_size_bytes=len(text.encode()),
            page_count=1,
            ocr_pages=0,
        )
        page = PageResult(
            page_number=1,
            source_type="text",
            extracted_text=text,
            ocr_used=False,
        )
        return cls(metadata=meta, pages=[page])

    @classmethod
    def from_pages(
        cls,
        pages: List[PageResult],
        source_name: str = "document",
        source_type: str = "pdf",
        file_size_bytes: int = 0,
    ) -> "Document":
        """Build a Document from an already-processed list of pages."""
        ocr_pages = sum(1 for p in pages if p.ocr_used)
        any_low = any(
            p.ocr_quality_flag == "LOW" for p in pages if p.ocr_used
        )
        meta = IngestionMetadata(
            source_name=source_name,
            source_type=source_type,
            file_size_bytes=file_size_bytes,
            page_count=len(pages),
            ocr_pages=ocr_pages,
            any_ocr_low_quality=any_low,
        )
        return cls(metadata=meta, pages=pages)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def combined_text(self) -> str:
        """
        Join all page texts with double newlines.

        Empty pages are skipped so callers get a clean string even when
        some pages failed OCR or produced no text.
        """
        parts = [p.extracted_text.strip() for p in self.pages if p.extracted_text.strip()]
        return "\n\n".join(parts)

    @property
    def is_empty(self) -> bool:
        """True when no page produced any text at all."""
        return not bool(self.combined_text)

    @property
    def ocr_summary(self) -> Dict[str, Any]:
        """Compact OCR quality summary for the API response."""
        return {
            "ocr_used": self.metadata.ocr_pages > 0,
            "ocr_pages": self.metadata.ocr_pages,
            "total_pages": self.metadata.page_count,
            "any_low_quality": self.metadata.any_ocr_low_quality,
            "pages": [p.to_dict() for p in self.pages],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "ocr_summary": self.ocr_summary,
        }
