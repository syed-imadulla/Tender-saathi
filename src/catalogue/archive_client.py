"""
Module: src/catalogue/archive_client.py
Purpose: Public.Resource.Org / Internet Archive client for acquiring full-text
standards documents with strict identity verification and TLS security.

Key Architectural Guarantees:
- Strict TLS certificate verification (verify=True).
- Parsing and extraction of RTI disclosure headers (Nehru epigraph stripping).
- SHA-256 cryptographic text hashing for tamper-evidence and change tracking.
- Rate limiting and exponential backoff retries.
- Strictly isolated from database writes.
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)


@dataclass
class ArchiveClientConfig:
    base_url: str = "https://archive.org/download"
    timeout_sec: float = 30.0
    delay_sec: float = 0.5
    max_retries: int = 3
    backoff_factor: float = 2.0
    user_agent: str = "TenderSaathi-Standards-Auditor/1.0 (Compliance; Research)"


@dataclass
class ArchiveDocumentResult:
    archive_identifier: str
    source_url: str
    retrieved_at: str
    clean_text: str
    text_hash: str
    char_count: int
    http_status: int
    is_success: bool
    error_message: Optional[str] = None


class ArchiveClient:
    """Client for fetching and cleaning pre-OCR full text from Internet Archive."""

    RTI_HEADER_TERMINATORS = [
        re.compile(r"Step\s+Out\s+From\s+the\s+Old\s+to\s+the\s+New", re.IGNORECASE),
        re.compile(r"Jawaharlal\s+Nehru", re.IGNORECASE),
        re.compile(r"INVENTOR\s+OF\s+THE\s+MODERN\s+WORLD", re.IGNORECASE),
        re.compile(r"NATIONAL\s+BUILDING\s+CODE\s+OF\s+INDIA", re.IGNORECASE),
        re.compile(r"BUREAU\s+OF\s+INDIAN\s+STANDARDS\s+MANAK\s+BHAVAN", re.IGNORECASE),
    ]

    def __init__(self, config: Optional[ArchiveClientConfig] = None, session: Optional[requests.Session] = None):
        self.config = config or ArchiveClientConfig()
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})
        self._last_request_time = 0.0

    def _polite_delay(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.delay_sec:
            time.sleep(self.config.delay_sec - elapsed)

    @classmethod
    def strip_rti_header(cls, raw_text: str) -> str:
        """
        Strips the standard Public.Resource.Org Right to Information disclosure header
        terminating at the Nehru epigraph or standard header.
        """
        if not raw_text:
            return ""

        text = raw_text
        # Search first 3000 chars for disclosure boundary
        search_window = text[:4000]
        match_end = -1

        for pattern in cls.RTI_HEADER_TERMINATORS:
            m = pattern.search(search_window)
            if m:
                # Find end of line following the match
                line_end = text.find("\n", m.end())
                if line_end != -1 and line_end > match_end:
                    match_end = line_end

        if match_end != -1:
            text = text[match_end:].strip()

        # Clean noise lines (e.g. standalone OCR artifacts)
        lines = [line.rstrip() for line in text.splitlines()]
        # Remove consecutive blank lines
        cleaned_lines = []
        consecutive_blanks = 0
        for line in lines:
            if not line:
                consecutive_blanks += 1
                if consecutive_blanks <= 2:
                    cleaned_lines.append("")
            else:
                consecutive_blanks = 0
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def fetch_fulltext_document(self, archive_identifier: str) -> ArchiveDocumentResult:
        """
        Fetches {identifier}_djvu.txt from archive.org with strict TLS verification.
        """
        # Sanitization
        clean_id = archive_identifier.strip().lower()
        short_id = clean_id.replace("gov.in.", "") if clean_id.startswith("gov.in.") else clean_id
        candidate_filenames = [
            f"{short_id}_djvu.txt",
            f"{clean_id}_djvu.txt",
            f"{short_id}.txt",
            f"{clean_id}.txt"
        ]
        retrieved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for fn in candidate_filenames:
            url = f"{self.config.base_url}/{clean_id}/{fn}"
            retries = 0
            while retries <= self.config.max_retries:
                self._polite_delay()
                try:
                    # Normal TLS certificate verification strictly enabled (verify=True)
                    resp = self.session.get(url, timeout=self.config.timeout_sec, verify=True)
                    self._last_request_time = time.time()

                    if resp.status_code == 200:
                        raw_text = resp.text
                        clean_text = self.strip_rti_header(raw_text)
                        text_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

                        return ArchiveDocumentResult(
                            archive_identifier=clean_id,
                            source_url=url,
                            retrieved_at=retrieved_at,
                            clean_text=clean_text,
                            text_hash=text_hash,
                            char_count=len(clean_text),
                            http_status=200,
                            is_success=True
                        )

                    if resp.status_code == 404:
                        break  # Try next filename candidate

                    if resp.status_code in (429, 500, 502, 503, 504):
                        retries += 1
                        time.sleep(self.config.backoff_factor ** retries)
                        continue

                    # Other unhandled HTTP error
                    break
                except requests.RequestException as e:
                    retries += 1
                    if retries > self.config.max_retries:
                        break
                    time.sleep(self.config.backoff_factor ** retries)

        return ArchiveDocumentResult(
            archive_identifier=clean_id,
            source_url=f"{self.config.base_url}/{clean_id}/",
            retrieved_at=retrieved_at,
            clean_text="",
            text_hash="",
            char_count=0,
            http_status=404,
            is_success=False,
            error_message="Document not found on archive.org (HTTP 404)"
        )
