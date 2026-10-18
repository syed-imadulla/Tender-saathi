"""
src/corpus/extractor.py — Deterministic Text & Quality Extraction for Standards PDFs

Extracts page-by-page text from PDF standards documents using PyMuPDF (with pypdf
fallback), detects scanned/image-only PDFs, flags table structures, and computes
extraction quality statistics.
"""

from __future__ import annotations

import os
import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.corpus.manifest import IngestionStatus

# Try importing PyMuPDF (fitz) or pypdf
try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


@dataclass
class ExtractedPage:
    """Represents text and diagnostic metrics extracted from a single PDF page."""
    page_number: int                 # 1-indexed
    text: str
    char_count: int
    text_density: float              # characters per page
    replacement_char_count: int
    is_empty: bool
    has_table: bool
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExtractedDocument:
    """Complete extraction payload for a PDF standards document."""
    doc_id: str
    file_sha256: str
    file_size_bytes: int
    page_count: int
    pages: List[ExtractedPage] = field(default_factory=list)
    total_characters: int = 0
    empty_page_count: int = 0
    replacement_char_ratio: float = 0.0
    ingestion_status: str = IngestionStatus.REGISTERED.value
    failure_reasons: List[str] = field(default_factory=list)
    table_warnings: List[str] = field(default_factory=list)
    extraction_method: str = "PYMUPDF_V1"

    def get_full_text(self) -> str:
        return "\n\n".join([p.text for p in self.pages if p.text.strip()])


class PDFExtractor:
    """
    Deterministic text extraction engine for technical standards PDFs.
    Preserves page boundaries, detects scanned pages, and checks character quality.
    """

    def __init__(self, min_char_density: int = 50, max_empty_page_ratio: float = 0.8):
        self.min_char_density = min_char_density
        self.max_empty_page_ratio = max_empty_page_ratio

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Computes the SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def extract(self, file_path: str, doc_id: str = "") -> ExtractedDocument:
        """
        Extracts text and quality statistics from the given PDF file.
        Returns an ExtractedDocument with complete provenance and status.
        """
        # Validate file existence
        if not os.path.exists(file_path):
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256="",
                file_size_bytes=0,
                page_count=0,
                ingestion_status=IngestionStatus.FAILED.value,
                failure_reasons=[f"File not found: {file_path}"]
            )

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256=hashlib.sha256(b"").hexdigest(),
                file_size_bytes=0,
                page_count=0,
                ingestion_status=IngestionStatus.FAILED.value,
                failure_reasons=["Empty file: 0 bytes"]
            )

        # Check for corrupt header
        with open(file_path, "rb") as f:
            header = f.read(1024)
        if b"%PDF-" not in header:
            file_hash = self.compute_sha256(file_path)
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256=file_hash,
                file_size_bytes=file_size,
                page_count=0,
                ingestion_status=IngestionStatus.CORRUPT.value,
                failure_reasons=["Invalid PDF header: corrupt or non-PDF file"]
            )

        file_hash = self.compute_sha256(file_path)

        # Attempt extraction via PyMuPDF first
        if PYMUPDF_AVAILABLE:
            try:
                return self._extract_with_fitz(file_path, doc_id, file_hash, file_size)
            except Exception as e:
                # If fitz fails, try pypdf fallback
                if PYPDF_AVAILABLE:
                    try:
                        return self._extract_with_pypdf(file_path, doc_id, file_hash, file_size)
                    except Exception as e_pypdf:
                        return ExtractedDocument(
                            doc_id=doc_id,
                            file_sha256=file_hash,
                            file_size_bytes=file_size,
                            page_count=0,
                            ingestion_status=IngestionStatus.CORRUPT.value,
                            failure_reasons=[f"PyMuPDF error: {str(e)}", f"pypdf fallback error: {str(e_pypdf)}"]
                        )
                return ExtractedDocument(
                    doc_id=doc_id,
                    file_sha256=file_hash,
                    file_size_bytes=file_size,
                    page_count=0,
                    ingestion_status=IngestionStatus.CORRUPT.value,
                    failure_reasons=[f"PyMuPDF error: {str(e)}"]
                )
        elif PYPDF_AVAILABLE:
            try:
                return self._extract_with_pypdf(file_path, doc_id, file_hash, file_size)
            except Exception as e:
                return ExtractedDocument(
                    doc_id=doc_id,
                    file_sha256=file_hash,
                    file_size_bytes=file_size,
                    page_count=0,
                    ingestion_status=IngestionStatus.CORRUPT.value,
                    failure_reasons=[f"pypdf error: {str(e)}"]
                )
        else:
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256=file_hash,
                file_size_bytes=file_size,
                page_count=0,
                ingestion_status=IngestionStatus.FAILED.value,
                failure_reasons=["No PDF parsing library available (fitz or pypdf required)"]
            )

    def _extract_with_fitz(self, file_path: str, doc_id: str, file_hash: str, file_size: int) -> ExtractedDocument:
        doc = fitz.open(file_path)
        page_count = len(doc)
        if page_count == 0:
            doc.close()
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256=file_hash,
                file_size_bytes=file_size,
                page_count=0,
                ingestion_status=IngestionStatus.CORRUPT.value,
                failure_reasons=["PDF document has 0 pages"]
            )

        extracted_pages: List[ExtractedPage] = []
        total_chars = 0
        total_replacements = 0
        empty_pages = 0
        table_warnings: List[str] = []

        for p_idx in range(page_count):
            page = doc[p_idx]
            page_num = p_idx + 1
            raw_text = page.get_text("text") or ""
            
            # Clean non-printable control characters except standard whitespace
            char_count = len(raw_text)
            total_chars += char_count
            
            # Count replacement characters like \ufffd, middle-dot glyph fallbacks, or unprintable controls
            replacements = len(re.findall(r'[\ufffd\x00·\x01-\x08\x0b\x0c\x0e-\x1f]', raw_text))
            total_replacements += replacements
            
            is_empty = len(raw_text.strip()) == 0
            if is_empty:
                empty_pages += 1

            # Detect tables or tabular patterns
            has_table = self._detect_table_structure(raw_text)
            page_warnings = []
            if has_table:
                warn_msg = f"Table structure detected on page {page_num}: tabular data may require structured parsing"
                page_warnings.append(warn_msg)
                table_warnings.append(warn_msg)

            extracted_pages.append(ExtractedPage(
                page_number=page_num,
                text=raw_text,
                char_count=char_count,
                text_density=float(char_count),
                replacement_char_count=replacements,
                is_empty=is_empty,
                has_table=has_table,
                warnings=page_warnings
            ))

        doc.close()

        # Quality diagnostics
        return self._assess_quality(
            doc_id=doc_id,
            file_hash=file_hash,
            file_size=file_size,
            page_count=page_count,
            pages=extracted_pages,
            total_chars=total_chars,
            total_replacements=total_replacements,
            empty_pages=empty_pages,
            table_warnings=table_warnings,
            method="PYMUPDF_V1"
        )

    def _extract_with_pypdf(self, file_path: str, doc_id: str, file_hash: str, file_size: int) -> ExtractedDocument:
        reader = pypdf.PdfReader(file_path)
        page_count = len(reader.pages)
        if page_count == 0:
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256=file_hash,
                file_size_bytes=file_size,
                page_count=0,
                ingestion_status=IngestionStatus.CORRUPT.value,
                failure_reasons=["PDF document has 0 pages"]
            )

        extracted_pages: List[ExtractedPage] = []
        total_chars = 0
        total_replacements = 0
        empty_pages = 0
        table_warnings: List[str] = []

        for p_idx, page in enumerate(reader.pages):
            page_num = p_idx + 1
            raw_text = page.extract_text() or ""
            char_count = len(raw_text)
            total_chars += char_count
            replacements = len(re.findall(r'[\ufffd\x00·\x01-\x08\x0b\x0c\x0e-\x1f]', raw_text))
            total_replacements += replacements
            is_empty = len(raw_text.strip()) == 0
            if is_empty:
                empty_pages += 1

            has_table = self._detect_table_structure(raw_text)
            page_warnings = []
            if has_table:
                warn_msg = f"Table structure detected on page {page_num}: tabular data may require structured parsing"
                page_warnings.append(warn_msg)
                table_warnings.append(warn_msg)

            extracted_pages.append(ExtractedPage(
                page_number=page_num,
                text=raw_text,
                char_count=char_count,
                text_density=float(char_count),
                replacement_char_count=replacements,
                is_empty=is_empty,
                has_table=has_table,
                warnings=page_warnings
            ))

        return self._assess_quality(
            doc_id=doc_id,
            file_hash=file_hash,
            file_size=file_size,
            page_count=page_count,
            pages=extracted_pages,
            total_chars=total_chars,
            total_replacements=total_replacements,
            empty_pages=empty_pages,
            table_warnings=table_warnings,
            method="PYPDF_FALLBACK"
        )

    def _detect_table_structure(self, text: str) -> bool:
        """Detects whether page content contains explicit table keywords or tabular grid formatting."""
        # Keyword indicators
        if re.search(r'\bTable\s+\d+(\.\d+)?\b', text, re.IGNORECASE):
            return True
        # Delimiter indicators (e.g. pipe tables or consecutive tabbed/spaced numerical columns)
        lines = text.split("\n")
        pipe_lines = sum(1 for line in lines if line.count("|") >= 2)
        if pipe_lines >= 2:
            return True
        # Check for multiple lines with repeated multi-column tab or wide space alignments
        col_lines = 0
        for line in lines:
            if len(re.findall(r'\s{3,}\S+', line)) >= 3:
                col_lines += 1
        if col_lines >= 4:
            return True
        return False

    def _assess_quality(
        self,
        doc_id: str,
        file_hash: str,
        file_size: int,
        page_count: int,
        pages: List[ExtractedPage],
        total_chars: int,
        total_replacements: int,
        empty_pages: int,
        table_warnings: List[str],
        method: str
    ) -> ExtractedDocument:
        """Evaluates quality metrics to determine final IngestionStatus."""
        failure_reasons = []
        empty_ratio = (empty_pages / page_count) if page_count > 0 else 1.0
        replacement_ratio = (total_replacements / total_chars) if total_chars > 0 else 0.0

        # Scanned PDF check: too few characters or vast majority empty pages
        if total_chars < self.min_char_density or empty_ratio >= self.max_empty_page_ratio:
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256=file_hash,
                file_size_bytes=file_size,
                page_count=page_count,
                pages=pages,
                total_characters=total_chars,
                empty_page_count=empty_pages,
                replacement_char_ratio=replacement_ratio,
                ingestion_status=IngestionStatus.OCR_REQUIRED.value,
                failure_reasons=["Scanned PDF or insufficient text density detected: OCR required"],
                table_warnings=table_warnings,
                extraction_method=method
            )

        # High corrupt/replacement characters check
        if replacement_ratio > 0.05:
            return ExtractedDocument(
                doc_id=doc_id,
                file_sha256=file_hash,
                file_size_bytes=file_size,
                page_count=page_count,
                pages=pages,
                total_characters=total_chars,
                empty_page_count=empty_pages,
                replacement_char_ratio=replacement_ratio,
                ingestion_status=IngestionStatus.QUALITY_FAILED.value,
                failure_reasons=[f"Suspiciously high replacement character ratio: {replacement_ratio:.2%}"],
                table_warnings=table_warnings,
                extraction_method=method
            )

        return ExtractedDocument(
            doc_id=doc_id,
            file_sha256=file_hash,
            file_size_bytes=file_size,
            page_count=page_count,
            pages=pages,
            total_characters=total_chars,
            empty_page_count=empty_pages,
            replacement_char_ratio=replacement_ratio,
            ingestion_status=IngestionStatus.EXTRACTED.value,
            failure_reasons=[],
            table_warnings=table_warnings,
            extraction_method=method
        )
