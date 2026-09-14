"""
Module: src/catalogue/bis_client.py
Purpose: Dedicated HTTP client responsible strictly for acquiring raw BIS standards
data from the official "Know Your Standards" portal (services.bis.gov.in).

Key Responsibilities:
- Acquire and manage BIS session cookies (BISID) via the official isdetails page.
- Base64 encode query parameters ('seachby' and 'txt_search') as required by BIS backend.
- Format DataTables server-side pagination parameters (draw, start, length).
- Parse DataTables response JSON (iTotalRecords, aaData).
- Configurable rate-limiting delay, timeout, and exponential backoff retries.
- Strictly decoupled from database persistence or higher-level business logic.
"""

import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class BISError(Exception):
    """Base exception for BIS client operations."""
    pass


class BISSessionError(BISError):
    """Raised when session cookie acquisition fails."""
    pass


class BISRequestError(BISError):
    """Raised when request to BIS fails or returns invalid response."""
    pass


@dataclass
class BISClientConfig:
    """Configuration options for BISClient."""
    session_url: str = (
        "https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/Indian_standards/isdetails/"
    )
    search_url: str = (
        "https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards/Indian_standards/searchIS"
    )
    page_size: int = 500
    delay_sec: float = 0.5
    timeout_sec: float = 60.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )


@dataclass
class BISPageResult:
    """Represents a single raw paginated response from the BIS searchIS endpoint."""
    seed: str
    search_by: str
    draw: int
    start: int
    length: int
    total_records: int
    total_display_records: int
    rows: List[Dict[str, Any]]
    raw_response: Dict[str, Any]
    retrieved_at: str


class BISClient:
    """HTTP Client for acquiring raw catalogue data from BIS Know Your Standards."""

    def __init__(self, config: Optional[BISClientConfig] = None, session: Optional[requests.Session] = None):
        self.config = config or BISClientConfig()
        self.session = session or requests.Session()
        self._session_initialized = False
        self._last_request_time = 0.0

        # Set standard headers
        self.session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.config.session_url,
            "Origin": "https://www.services.bis.gov.in",
        })

    @staticmethod
    def encode_param(value: str) -> str:
        """Encodes a string parameter to Base64 ASCII as required by the BIS endpoint."""
        if value is None:
            value = ""
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    def initialize_session(self, force: bool = False) -> str:
        """
        Visits the session landing page to establish the BISID cookie.
        Returns the BISID cookie value.
        """
        if self._session_initialized and not force:
            bisid = self.session.cookies.get("BISID")
            if bisid:
                return bisid

        self._polite_delay()
        logger.info("Initializing BIS session via %s", self.config.session_url)

        try:
            resp = self.session.get(
                self.config.session_url,
                timeout=self.config.timeout_sec
            )
            self._last_request_time = time.time()
        except requests.RequestException as exc:
            raise BISSessionError(f"Failed to connect to BIS session URL: {exc}") from exc

        if resp.status_code != 200:
            raise BISSessionError(
                f"BIS session URL returned status HTTP {resp.status_code}: {resp.text[:200]}"
            )

        bisid = self.session.cookies.get("BISID")
        if not bisid:
            # Check other casings
            for cookie in self.session.cookies:
                if cookie.name.upper() == "BISID":
                    bisid = cookie.value
                    break

        if not bisid:
            logger.warning("No explicit BISID cookie found in session response headers, proceeding with session cookies.")
        else:
            logger.debug("Acquired BISID cookie: %s...", bisid[:8] if len(bisid) > 8 else bisid)

        self._session_initialized = True
        return bisid or "SESSION_ACTIVE"

    def _polite_delay(self):
        """Enforces a courteous delay between outbound requests to prevent hammering the server."""
        if self.config.delay_sec <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.delay_sec:
            time.sleep(self.config.delay_sec - elapsed)

    def fetch_page(
        self,
        seed: str,
        start: int = 0,
        length: Optional[int] = None,
        search_by: str = "isnumber",
        draw: int = 1
    ) -> BISPageResult:
        """
        Fetches a single page of results for a given seed and offset.
        
        Args:
            seed: Substring/search token (e.g. '0', '1', ..., '9').
            start: Offset row index for pagination (0, 500, 1000, ...).
            length: Number of records to request per page (defaults to config.page_size).
            search_by: Mode parameter ('isnumber' by default).
            draw: Sequence counter for DataTables.
        """
        if not self._session_initialized:
            self.initialize_session()

        page_length = length if length is not None else self.config.page_size

        seachby_b64 = self.encode_param(search_by)
        txt_search_b64 = self.encode_param(seed)

        # Note: the parameter in BIS is 'seachby' (spelled without the 'r')
        url = f"{self.config.search_url}?seachby={seachby_b64}&txt_search={txt_search_b64}"

        post_data = {
            "draw": str(draw),
            "start": str(start),
            "length": str(page_length),
        }

        retries = 0
        last_error = None

        while retries <= self.config.max_retries:
            self._polite_delay()
            retrieved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            try:
                logger.debug(
                    "POST %s (seed=%s, start=%d, length=%d, attempt=%d)",
                    self.config.search_url, seed, start, page_length, retries + 1
                )
                resp = self.session.post(
                    url,
                    data=post_data,
                    timeout=self.config.timeout_sec
                )
                self._last_request_time = time.time()

                if resp.status_code == 200:
                    try:
                        raw_data = resp.json()
                    except json.JSONDecodeError as jde:
                        raise BISRequestError(
                            f"BIS response is not valid JSON (HTTP 200): {resp.text[:200]}"
                        ) from jde

                    if not isinstance(raw_data, dict):
                        raise BISRequestError(
                            f"Expected JSON object from BIS, received {type(raw_data).__name__}"
                        )

                    # Extract DataTables fields
                    i_total_records = int(raw_data.get("iTotalRecords") or 0)
                    i_display_records = int(raw_data.get("iTotalDisplayRecords") or i_total_records)
                    aa_data = raw_data.get("aaData") or []

                    if not isinstance(aa_data, list):
                        logger.warning("aaData is not a list; coercing to empty list.")
                        aa_data = []

                    return BISPageResult(
                        seed=seed,
                        search_by=search_by,
                        draw=draw,
                        start=start,
                        length=page_length,
                        total_records=i_total_records,
                        total_display_records=i_display_records,
                        rows=aa_data,
                        raw_response=raw_data,
                        retrieved_at=retrieved_at,
                    )

                # If status is retryable (429, 500, 502, 503, 504)
                if resp.status_code in (429, 500, 502, 503, 504):
                    retries += 1
                    last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    if retries <= self.config.max_retries:
                        backoff = self.config.backoff_factor ** retries
                        logger.warning(
                            "BIS request error (%s). Retrying in %.1fs (attempt %d/%d)...",
                            last_error, backoff, retries, self.config.max_retries
                        )
                        time.sleep(backoff)
                        continue
                else:
                    raise BISRequestError(
                        f"BIS endpoint rejected request with HTTP {resp.status_code}: {resp.text[:200]}"
                    )

            except (requests.RequestException, BISRequestError) as exc:
                retries += 1
                last_error = str(exc)
                if retries <= self.config.max_retries:
                    backoff = self.config.backoff_factor ** retries
                    logger.warning(
                        "BIS network error (%s). Retrying in %.1fs (attempt %d/%d)...",
                        last_error, backoff, retries, self.config.max_retries
                    )
                    time.sleep(backoff)
                    continue
                raise BISRequestError(
                    f"Failed to fetch page for seed '{seed}' (start={start}) after {self.config.max_retries} retries: {last_error}"
                ) from exc

        raise BISRequestError(
            f"Failed to fetch page for seed '{seed}' (start={start}) after {self.config.max_retries} retries: {last_error}"
        )
