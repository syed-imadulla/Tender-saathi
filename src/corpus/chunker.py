"""
src/corpus/chunker.py — Clause-Aware Passage Segmentation & Canonical Hashing

Divides extracted standards document pages into clause-grounded passages.
Enforces that passages never cross page or edition boundaries, assigns
stable deterministic chunk identifiers, and tags unidentified clauses explicitly
as 'CLAUSE_UNKNOWN'.
"""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from src.corpus.manifest import CorpusDocumentRecord
from src.corpus.extractor import ExtractedDocument, ExtractedPage
from src.corpus.semantics import VerificationState


@dataclass
class ClausePassage:
    """Represents a discrete, auditable text passage tied to a standard edition and page."""
    passage_id: str                          # Stable ID: {doc_id}_p{page}_c{clause_slug}_{index}
    doc_id: str                              # Source document record ID
    standard_number: str                     # e.g. "IS 1180 (Part 1)"
    edition_year: Optional[int]              # e.g. 2014
    source_file_sha256: str                  # Hash of the raw PDF file
    page_start: int                          # Starting page number (1-indexed)
    page_end: int                            # Ending page number (1-indexed)
    clause_identifier: str                   # e.g. "4.2", "1.1", "Foreword", or "CLAUSE_UNKNOWN"
    passage_text: str                        # Extracted raw text
    content_hash: str                        # SHA-256 of canonicalized text
    verification_state: str                  # Current verification state string
    extraction_quality_status: str           # Status from extractor (e.g. "EXTRACTED")
    has_table: bool = False                  # Whether passage contains tabular structure
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClausePassage:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class ClauseAwareChunker:
    """
    Splits extracted PDF pages into clause-scoped passages.
    Preserves strict boundary isolation across pages and editions.
    """

    # Clause heading patterns:
    # 1. Standard numbers: "1.2", "4.2.1", "12" followed by uppercase title
    # 2. Explicit "Clause 4.2"
    # 3. Structural sections: "Foreword", "Scope", "Table 1", "Annexure A", "Appendix B"
    CLAUSE_PATTERN = re.compile(
        r'^(?:(?:Clause|Section)\s+)?(\d+(?:\.\d+)*)\s+([A-Z0-9].*)$',
        re.MULTILINE
    )
    NAMED_SECTION_PATTERN = re.compile(
        r'^(Foreword|Scope|References|Annexure\s+[A-Z0-9]+|Appendix\s+[A-Z0-9]+|Table\s+\d+(?:\.\d+)?)\b',
        re.IGNORECASE | re.MULTILINE
    )

    @staticmethod
    def canonical_hash(text: str) -> str:
        """Computes SHA-256 over whitespace-normalized text."""
        normalized = re.sub(r'\s+', ' ', text.strip())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def _slugify(clause_str: str) -> str:
        """Converts clause string into a clean, filesystem/ID safe slug."""
        clean = re.sub(r'[^a-zA-Z0-9_\.]', '_', clause_str.strip())
        clean = re.sub(r'_+', '_', clean).strip('_')
        return clean or "unknown"

    def chunk_document(
        self,
        extracted_doc: ExtractedDocument,
        doc_record: CorpusDocumentRecord
    ) -> List[ClausePassage]:
        """
        Segments all pages of an ExtractedDocument into ClausePassage instances.
        Passages strictly do not cross page or document boundaries.
        """
        passages: List[ClausePassage] = []

        # If document extraction failed or requires OCR, do not generate valid passages
        if extracted_doc.ingestion_status in ["OCR_REQUIRED", "CORRUPT", "FAILED"]:
            return passages

        for page in extracted_doc.pages:
            if page.is_empty or not page.text.strip():
                continue

            page_passages = self._chunk_page(page, extracted_doc, doc_record)
            passages.extend(page_passages)

        return passages

    def _chunk_page(
        self,
        page: ExtractedPage,
        extracted_doc: ExtractedDocument,
        doc_record: CorpusDocumentRecord
    ) -> List[ClausePassage]:
        """Chunks a single page into one or more clause-grounded passages."""
        lines = page.text.split("\n")
        chunks: List[Dict[str, Any]] = []

        current_clause = "CLAUSE_UNKNOWN"
        current_lines: List[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if current_lines:
                    current_lines.append("")
                continue

            # Check for clause identifier at beginning of line
            match_num = self.CLAUSE_PATTERN.match(line_str)
            match_named = self.NAMED_SECTION_PATTERN.match(line_str)

            detected_clause = None
            if match_num:
                # E.g. "4.2 Loss Levels" -> clause "4.2"
                detected_clause = match_num.group(1)
            elif match_named:
                # E.g. "Foreword", "Table 1"
                detected_clause = match_named.group(1).title()

            if detected_clause:
                # Flush previous chunk if non-empty
                text_block = "\n".join(current_lines).strip()
                if text_block:
                    chunks.append({
                        "clause": current_clause,
                        "text": text_block
                    })
                current_clause = detected_clause
                current_lines = [line]
            else:
                current_lines.append(line)

        # Flush final block
        text_block = "\n".join(current_lines).strip()
        if text_block:
            chunks.append({
                "clause": current_clause,
                "text": text_block
            })

        # Convert to ClausePassage objects with stable IDs
        result: List[ClausePassage] = []
        for idx, item in enumerate(chunks):
            clause_id = item["clause"]
            passage_text = item["text"]
            if not passage_text.strip():
                continue

            clause_slug = self._slugify(clause_id)
            passage_id = f"{doc_record.doc_id}_p{page.page_number}_c{clause_slug}_{idx}"
            content_hash = self.canonical_hash(passage_text)

            # Verification state semantics:
            # If clause is reliably detected, it can advance to CLAUSE_IDENTIFIER_VERIFIED
            # If clause is unknown, it remains at EXTRACTION_QUALITY_CHECKED
            ver_state = (
                VerificationState.CLAUSE_IDENTIFIER_VERIFIED.value
                if clause_id != "CLAUSE_UNKNOWN"
                else VerificationState.EXTRACTION_QUALITY_CHECKED.value
            )

            result.append(ClausePassage(
                passage_id=passage_id,
                doc_id=doc_record.doc_id,
                standard_number=doc_record.standard_number,
                edition_year=doc_record.edition_year,
                source_file_sha256=doc_record.file_sha256,
                page_start=page.page_number,
                page_end=page.page_number,
                clause_identifier=clause_id,
                passage_text=passage_text,
                content_hash=content_hash,
                verification_state=ver_state,
                extraction_quality_status=extracted_doc.ingestion_status,
                has_table=page.has_table,
                warnings=page.warnings
            ))

        return result
