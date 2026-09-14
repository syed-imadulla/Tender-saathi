"""
Module: src/catalogue/fulltext_fetcher.py
Purpose: Associates external full-text documents with authoritative BIS catalogue records.

Key Invariants Enforced:
1. Exact Identity Anchoring:
   Archive identifier parsed -> canonical identity compared to BIS record.
   - Sibling parts and sections are strictly prohibited (e.g. Part 2/Sec 21 cannot attach to Part 2/Sec 28 or Part 1).
   - Base number, prefix, part, and section MUST match exactly.
2. Edition Separation:
   - If archive year matches BIS catalogue year: current edition (edition_mismatch=False, is_historical_edition=False).
   - If archive year differs: historical edition (edition_mismatch=True, is_historical_edition=True).
     The historical document's own identity (e.g. IS 732:1989) is preserved in source_edition.
3. Provenance Tracking:
   - Every text record and chunk stores SHA256 hash, retrieval timestamp, char count, and source edition.
4. Database Isolation:
   - Stores full text in separate table `standards_fulltext` and chunks in `standards_fulltext_chunks`.
   - Never overwrites BIS-authoritative metadata with external full text.
"""

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple

from src.catalogue.archive_client import ArchiveClient, ArchiveDocumentResult
from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier

logger = logging.getLogger(__name__)


@dataclass
class VerifiedFullTextRecord:
    canonical_id: str
    archive_identifier: str
    source_edition: str            # e.g. "IS 732 : 1989"
    catalogue_year: Optional[int]  # e.g. 2019
    full_text_year: Optional[int]  # e.g. 1989
    source_url: str
    retrieved_at: str
    text_hash: str
    full_text_chars: int
    full_text: str
    metadata_only: int             # 0 if full text attached, 1 if metadata only
    identity_verified: int         # 1 if identity matches
    edition_mismatch: int          # 1 if catalogue_year != full_text_year
    is_historical_edition: int     # 1 if older/mismatched edition
    archive_checked: int           # 1 if archive.org was queried

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FullTextChunkRecord:
    chunk_id: str
    canonical_id: str
    chunk_index: int
    chunk_text: str
    chunk_chars: int
    chunk_hash: str
    source_edition: str
    full_text_year: Optional[int]
    catalogue_year: Optional[int]
    edition_mismatch: int
    is_historical_edition: int
    retrieved_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FullTextManager:
    """Manages association, chunking, and database persistence of verified full-text documents."""

    def __init__(self, db_path: str, archive_client: Optional[ArchiveClient] = None):
        self.db_path = db_path
        self.archive_client = archive_client or ArchiveClient()
        self._ensure_schema()

    def _ensure_schema(self):
        """Creates the full-text and chunk tables separate from BIS metadata."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS standards_fulltext (
                    canonical_id TEXT PRIMARY KEY,
                    archive_identifier TEXT NOT NULL,
                    source_edition TEXT NOT NULL,
                    catalogue_year INTEGER,
                    full_text_year INTEGER,
                    source_url TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    full_text_chars INTEGER NOT NULL,
                    full_text TEXT NOT NULL,
                    metadata_only INTEGER NOT NULL,
                    identity_verified INTEGER NOT NULL,
                    edition_mismatch INTEGER NOT NULL,
                    is_historical_edition INTEGER NOT NULL,
                    archive_checked INTEGER NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS standards_fulltext_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    canonical_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    chunk_chars INTEGER NOT NULL,
                    chunk_hash TEXT NOT NULL,
                    source_edition TEXT NOT NULL,
                    full_text_year INTEGER,
                    catalogue_year INTEGER,
                    edition_mismatch INTEGER NOT NULL,
                    is_historical_edition INTEGER NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    FOREIGN KEY(canonical_id) REFERENCES standards_fulltext(canonical_id)
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fulltext_chunks_canonical 
                ON standards_fulltext_chunks(canonical_id);
            """)
            conn.commit()

    @classmethod
    def evaluate_identity_attachment(
        cls,
        target_parsed: CanonicalStandardIdentifier,
        archive_identifier: str
    ) -> Tuple[bool, Optional[CanonicalStandardIdentifier], str]:
        """
        Evaluates whether an archive identifier can legitimately attach to a target standard.
        Returns: (can_attach, parsed_archive, rejection_reason)
        """
        parsed_archive = StandardIdentifierNormalizer.parse_archive_identifier(archive_identifier)
        if not parsed_archive or not parsed_archive.is_valid:
            return False, None, f"Invalid or unparseable archive identifier: '{archive_identifier}'"

        # Check prefix
        if parsed_archive.prefix.upper() != target_parsed.prefix.upper():
            return False, parsed_archive, (
                f"Prefix mismatch: archive={parsed_archive.prefix} vs target={target_parsed.prefix}"
            )

        # Check base number
        if parsed_archive.base_number != target_parsed.base_number:
            return False, parsed_archive, (
                f"Base number collision mismatch: archive={parsed_archive.base_number} vs target={target_parsed.base_number}"
            )

        # Check part number
        if parsed_archive.part != target_parsed.part:
            return False, parsed_archive, (
                f"Part mismatch (sibling bleed prohibited): archive Part {parsed_archive.part} vs target Part {target_parsed.part}"
            )

        # Check section number
        if parsed_archive.section != target_parsed.section:
            return False, parsed_archive, (
                f"Section mismatch (sibling bleed prohibited): archive Sec {parsed_archive.section} vs target Sec {target_parsed.section}"
            )

        return True, parsed_archive, "VALID"

    def attach_fulltext_document(
        self,
        target_standard_str: str,
        archive_identifier: str,
        raw_text_override: Optional[str] = None
    ) -> Tuple[bool, str, Optional[VerifiedFullTextRecord]]:
        """
        Attempts to verify and attach full text to a standard in the database.
        """
        target_parsed = StandardIdentifierNormalizer.parse(target_standard_str)
        if not target_parsed.is_valid:
            return False, f"Target standard is invalid: '{target_standard_str}'", None

        can_attach, parsed_archive, reason = self.evaluate_identity_attachment(
            target_parsed, archive_identifier
        )
        if not can_attach or not parsed_archive:
            logger.warning(
                "Rejected full-text attachment of %s to %s: %s",
                archive_identifier, target_standard_str, reason
            )
            # Record metadata_only record with rejection reason
            self._record_metadata_only(target_parsed.canonical_id)
            return False, reason, None

        # Determine edition correspondence
        catalogue_year = target_parsed.year
        full_text_year = parsed_archive.year
        edition_mismatch = int(catalogue_year is not None and full_text_year is not None and catalogue_year != full_text_year)
        is_historical = edition_mismatch

        # Fetch or use provided text
        if raw_text_override is not None:
            clean_text = ArchiveClient.strip_rti_header(raw_text_override)
            text_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
            doc_res = ArchiveDocumentResult(
                archive_identifier=archive_identifier,
                source_url=f"local://{archive_identifier}",
                retrieved_at="2026-09-14T00:00:00Z",
                clean_text=clean_text,
                text_hash=text_hash,
                char_count=len(clean_text),
                http_status=200,
                is_success=True
            )
        else:
            doc_res = self.archive_client.fetch_fulltext_document(archive_identifier)

        if not doc_res.is_success or not doc_res.clean_text:
            self._record_metadata_only(target_parsed.canonical_id)
            return False, f"Archive document fetch failed: {doc_res.error_message}", None

        # Build verified full-text record
        record = VerifiedFullTextRecord(
            canonical_id=target_parsed.canonical_id,
            archive_identifier=archive_identifier,
            source_edition=parsed_archive.canonical_number,
            catalogue_year=catalogue_year,
            full_text_year=full_text_year,
            source_url=doc_res.source_url,
            retrieved_at=doc_res.retrieved_at,
            text_hash=doc_res.text_hash,
            full_text_chars=doc_res.char_count,
            full_text=doc_res.clean_text,
            metadata_only=0,
            identity_verified=1,
            edition_mismatch=edition_mismatch,
            is_historical_edition=is_historical,
            archive_checked=1
        )

        # Chunk document (approx 1000 characters per chunk with paragraph boundaries)
        chunks = self._chunk_text(record)

        # Persist to database
        self._save_record_and_chunks(record, chunks)

        logger.info(
            "Successfully attached %s to %s (historical=%s, chars=%d, chunks=%d)",
            parsed_archive.canonical_number, target_parsed.canonical_id,
            bool(is_historical), record.full_text_chars, len(chunks)
        )
        return True, "SUCCESS", record

    def _record_metadata_only(self, canonical_id: str):
        """Records that archive.org was checked but no text is attached."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO standards_fulltext (
                    canonical_id, archive_identifier, source_edition, catalogue_year,
                    full_text_year, source_url, retrieved_at, text_hash, full_text_chars,
                    full_text, metadata_only, identity_verified, edition_mismatch,
                    is_historical_edition, archive_checked
                ) VALUES (?, '', 'METADATA_ONLY', NULL, NULL, '', datetime('now'), '', 0, '', 1, 1, 0, 0, 1)
            """, (canonical_id,))
            conn.commit()

    def _chunk_text(self, record: VerifiedFullTextRecord, chunk_size: int = 1000) -> List[FullTextChunkRecord]:
        """Splits full text into chunks while preserving paragraph boundaries and complete provenance."""
        text = record.full_text
        if not text:
            return []

        paragraphs = text.split("\n\n")
        chunks: List[FullTextChunkRecord] = []
        current_paras: List[str] = []
        current_len = 0
        chunk_idx = 0

        for para in paragraphs:
            p = para.strip()
            if not p:
                continue
            if current_len + len(p) > chunk_size and current_paras:
                chunk_body = "\n\n".join(current_paras)
                chunk_hash = hashlib.sha256(chunk_body.encode("utf-8")).hexdigest()
                chunk_id = f"{record.canonical_id}#chunk_{chunk_idx:04d}"
                chunks.append(FullTextChunkRecord(
                    chunk_id=chunk_id,
                    canonical_id=record.canonical_id,
                    chunk_index=chunk_idx,
                    chunk_text=chunk_body,
                    chunk_chars=len(chunk_body),
                    chunk_hash=chunk_hash,
                    source_edition=record.source_edition,
                    full_text_year=record.full_text_year,
                    catalogue_year=record.catalogue_year,
                    edition_mismatch=record.edition_mismatch,
                    is_historical_edition=record.is_historical_edition,
                    retrieved_at=record.retrieved_at
                ))
                chunk_idx += 1
                current_paras = [p]
                current_len = len(p)
            else:
                current_paras.append(p)
                current_len += len(p)

        if current_paras:
            chunk_body = "\n\n".join(current_paras)
            chunk_hash = hashlib.sha256(chunk_body.encode("utf-8")).hexdigest()
            chunk_id = f"{record.canonical_id}#chunk_{chunk_idx:04d}"
            chunks.append(FullTextChunkRecord(
                chunk_id=chunk_id,
                canonical_id=record.canonical_id,
                chunk_index=chunk_idx,
                chunk_text=chunk_body,
                chunk_chars=len(chunk_body),
                chunk_hash=chunk_hash,
                source_edition=record.source_edition,
                full_text_year=record.full_text_year,
                catalogue_year=record.catalogue_year,
                edition_mismatch=record.edition_mismatch,
                is_historical_edition=record.is_historical_edition,
                retrieved_at=record.retrieved_at
            ))

        return chunks

    def _save_record_and_chunks(self, record: VerifiedFullTextRecord, chunks: List[FullTextChunkRecord]):
        """Saves verified record and chunks to database in one atomic transaction."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO standards_fulltext (
                    canonical_id, archive_identifier, source_edition, catalogue_year,
                    full_text_year, source_url, retrieved_at, text_hash, full_text_chars,
                    full_text, metadata_only, identity_verified, edition_mismatch,
                    is_historical_edition, archive_checked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.canonical_id, record.archive_identifier, record.source_edition,
                record.catalogue_year, record.full_text_year, record.source_url,
                record.retrieved_at, record.text_hash, record.full_text_chars,
                record.full_text, record.metadata_only, record.identity_verified,
                record.edition_mismatch, record.is_historical_edition, record.archive_checked
            ))

            # Remove prior chunks for this canonical_id before inserting new ones
            cursor.execute("DELETE FROM standards_fulltext_chunks WHERE canonical_id = ?", (record.canonical_id,))

            cursor.executemany("""
                INSERT INTO standards_fulltext_chunks (
                    chunk_id, canonical_id, chunk_index, chunk_text, chunk_chars,
                    chunk_hash, source_edition, full_text_year, catalogue_year,
                    edition_mismatch, is_historical_edition, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    c.chunk_id, c.canonical_id, c.chunk_index, c.chunk_text, c.chunk_chars,
                    c.chunk_hash, c.source_edition, c.full_text_year, c.catalogue_year,
                    c.edition_mismatch, c.is_historical_edition, c.retrieved_at
                )
                for c in chunks
            ])
            conn.commit()

    def get_fulltext_provenance(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full-text provenance record for a given canonical standard ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standards_fulltext WHERE canonical_id = ?", (canonical_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_chunk_provenance(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves provenance for a single chunk."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standards_fulltext_chunks WHERE chunk_id = ?", (chunk_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
