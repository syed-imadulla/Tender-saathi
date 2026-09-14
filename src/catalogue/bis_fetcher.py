"""
Module: src/catalogue/bis_fetcher.py
Purpose: Acquisition runner and CLI for BIS catalogue data enumeration.

Phase 1 Responsibilities:
- Orchestrates multi-seed catalogue acquisition (default seeds: 0-9).
- Paginates through DataTables endpoints using BISClient.
- Performs basic validation on raw rows (rejecting corrupt/identity-free rows).
- Deduplicates rows across seeds and pages without inventing data.
- Persists raw responses page-by-page into data/raw/bis/<run_id>/pages/.
- Writes consolidated raw records to data/raw/bis/<run_id>/raw_records.jsonl.
- Generates reproducible, auditable summaries in JSON and plain text.
- Strictly isolated: does NOT touch production database or existing catalogue.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from src.catalogue.bis_client import BISClient, BISClientConfig, BISError, BISPageResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bis_fetcher")


@dataclass
class SeedStat:
    """Audit statistics for a single seed run."""
    seed: str
    reported_total: int = 0
    fetched_rows: int = 0
    unique_rows: int = 0
    duplicate_rows: int = 0
    rejected_rows: int = 0
    pages_fetched: int = 0
    failed: bool = False
    error_message: Optional[str] = None


@dataclass
class IngestionRunSummary:
    """Comprehensive auditable summary of an acquisition run."""
    run_id: str
    started_at: str
    finished_at: str
    search_mode: str
    seeds: List[str]
    config: Dict[str, Any]
    seed_stats: Dict[str, Dict[str, Any]]
    total_reported: int
    total_raw_rows: int
    total_unique_rows: int
    total_duplicates: int
    total_rejected: int
    failed_seeds: List[str]
    status: str  # "SUCCESS", "PARTIAL", "FAILED"
    output_dir: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_formatted_text(self) -> str:
        """Returns human-readable text table matching Phase 1 spec."""
        lines = [
            "=" * 60,
            "BIS INGESTION RUN AUDIT SUMMARY",
            "=" * 60,
            f"run_id:        {self.run_id}",
            f"started_at:    {self.started_at}",
            f"finished_at:   {self.finished_at}",
            f"search_mode:   {self.search_mode}",
            f"seeds:         {', '.join(self.seeds)}",
            f"status:        {self.status}",
            f"output_dir:    {self.output_dir}",
            "-" * 60,
            "SEED BREAKDOWN:",
            f"{'Seed':<6} | {'Reported':<9} | {'Fetched':<8} | {'Unique':<8} | {'Dups':<6} | {'Rejected':<8} | {'Pages':<6} | {'Status'}",
            "-" * 60,
        ]
        for s, stat in self.seed_stats.items():
            st_text = "FAILED" if stat.get("failed") else "OK"
            lines.append(
                f"{s:<6} | {stat.get('reported_total', 0):<9} | {stat.get('fetched_rows', 0):<8} | "
                f"{stat.get('unique_rows', 0):<8} | {stat.get('duplicate_rows', 0):<6} | "
                f"{stat.get('rejected_rows', 0):<8} | {stat.get('pages_fetched', 0):<6} | {st_text}"
            )
        lines.extend([
            "-" * 60,
            "TOTAL AGGREGATES:",
            f"  Raw Rows Fetched:       {self.total_raw_rows}",
            f"  Unique Standards:       {self.total_unique_rows}",
            f"  Duplicate Instances:    {self.total_duplicates}",
            f"  Rejected / Malformed:   {self.total_rejected}",
            f"  Failed Seeds:           {', '.join(self.failed_seeds) if self.failed_seeds else 'None'}",
            f"  Final Status:           {self.status}",
            "=" * 60,
        ])
        return "\n".join(lines)


class RawRecordValidator:
    """
    Phase 1 Basic Validation.
    
    Verifies that a raw row is a valid object and possesses an authentic,
    extractable IS identifier. Rejects corrupt or identity-free rows without
    inventing identities.
    """

    # Matches basic IS standard prefix e.g. "IS 1239", "IS/IEC 60502", "SP 7"
    IS_IDENTIFIER_PATTERN = re.compile(
        r'^(IS\s*/\s*ISO\s*/\s*IEC|IS\s*/\s*IEC|IS\s*/\s*ISO|IS\s*/\s*QC|IS\s*/\s*CISPR|IS|SP)\s*(\d+)',
        re.IGNORECASE
    )

    @classmethod
    def clean_html_is_no(cls, raw_is_no: Any) -> str:
        """Extracts primary standard string from HTML-formatted is_no field."""
        if not raw_is_no or not isinstance(raw_is_no, str):
            return ""
        # The is_no is typically: "IS 1554 (Part 1):1988<br>IEC 60502<br> (Active)"
        # The primary identity is in the first segment before <br>
        first_segment = re.split(r'<br\s*/?>', raw_is_no, flags=re.IGNORECASE)[0]
        return first_segment.strip()

    @classmethod
    def validate_raw_row(cls, row: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates raw dictionary row.
        Returns: (is_valid, extracted_clean_id, rejection_reason)
        """
        if not isinstance(row, dict):
            return False, None, f"Row is not a dictionary ({type(row).__name__})"

        raw_is_no = row.get("is_no")
        if not raw_is_no:
            return False, None, "Missing 'is_no' field"

        clean_is_no = cls.clean_html_is_no(raw_is_no)
        if not clean_is_no:
            return False, None, "Empty standard identifier after cleaning HTML"

        # Check for corrupt source entries like "IS  (Part 1/Sec 1):1975" where number is missing
        match = cls.IS_IDENTIFIER_PATTERN.search(clean_is_no)
        if not match:
            return False, None, f"Corrupt or unparseable IS identity: '{clean_is_no}'"

        # Normalize spacing between prefix and base number (e.g. "IS/ISO3471" -> "IS/ISO 3471")
        clean_prefix = match.group(1).strip()
        clean_num = match.group(2).strip()
        normalized_str = cls.IS_IDENTIFIER_PATTERN.sub(f"{clean_prefix} {clean_num}", clean_is_no, count=1)

        # Canonical key for Phase 1 deduplication
        # Normalizes spaces and uppercase: "IS 778:1984" -> "IS 778:1984"
        canonical_key = re.sub(r'\s+', ' ', normalized_str.strip().upper())
        return True, canonical_key, None


class BISCatalogueFetcher:
    """Orchestrates acquisition runs, pagination, raw storage, and audit logs."""

    def __init__(
        self,
        client: Optional[BISClient] = None,
        output_base_dir: str = "data/raw/bis",
        page_size: int = 500,
        delay_sec: float = 0.5,
        timeout_sec: float = 60.0,
        max_retries: int = 3
    ):
        self.output_base_dir = output_base_dir
        self.config = BISClientConfig(
            page_size=page_size,
            delay_sec=delay_sec,
            timeout_sec=timeout_sec,
            max_retries=max_retries
        )
        self.client = client or BISClient(config=self.config)

    @classmethod
    def validate_seed_pagination(
        cls,
        seed: str,
        offsets: List[int],
        page_row_counts: List[int],
        reported_total: int,
        page_size: int,
        limit: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates pagination completeness:
        - Every expected offset (0, page_size, 2*page_size, ...) exists without gaps or duplicates.
        - Final page is allowed to contain fewer than page_size rows (valid short page).
        - Accumulated rows must equal reported_total (or limit).
        """
        if limit is not None:
            expected_total = min(reported_total, limit)
        else:
            expected_total = reported_total

        if expected_total == 0:
            if offsets and offsets != [0]:
                return False, f"Seed '{seed}': Expected 0 rows but received offsets {offsets}"
            return True, None

        expected_page_count = (expected_total + page_size - 1) // page_size
        expected_offsets = [i * page_size for i in range(expected_page_count)]

        if offsets != expected_offsets:
            return False, f"Seed '{seed}': Offset sequence mismatch. Expected {expected_offsets}, got {offsets}"

        accumulated = sum(page_row_counts)
        if accumulated != expected_total:
            return False, (
                f"Seed '{seed}': Accumulated rows ({accumulated}) != expected total ({expected_total}). "
                f"Page row counts: {page_row_counts}"
            )

        # Check intermediate page lengths are full page_size
        for idx, count in enumerate(page_row_counts[:-1]):
            if count != page_size:
                return False, f"Seed '{seed}': Intermediate page {idx} is short ({count} < {page_size})"

        # Final page length check
        final_expected = expected_total - (expected_page_count - 1) * page_size
        if page_row_counts and page_row_counts[-1] != final_expected:
            return False, f"Seed '{seed}': Final page has {page_row_counts[-1]} rows, expected {final_expected}"

        return True, None

    def run_acquisition(
        self,
        seeds: Optional[List[str]] = None,
        limit: Optional[int] = None,
        search_mode: str = "isnumber"
    ) -> IngestionRunSummary:
        """
        Executes an acquisition run across given seeds.
        
        Args:
            seeds: List of string seeds (e.g. ['0', '1', ..., '9']).
            limit: Maximum records to fetch per seed (useful for smoke tests).
            search_mode: 'isnumber' by default.
        """
        if seeds is None:
            seeds = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        run_dir = os.path.join(self.output_base_dir, run_id)
        pages_dir = os.path.join(run_dir, "pages")
        os.makedirs(pages_dir, exist_ok=True)

        started_at = datetime.now(timezone.utc).isoformat()
        logger.info("Starting BIS acquisition run %s (seeds: %s, limit per seed: %s)", run_id, seeds, limit)

        # Global deduplication across all seeds in this run
        seen_identities: Set[str] = set()
        rejected_identities: List[Dict[str, Any]] = []

        total_raw_rows = 0
        total_unique_rows = 0
        total_duplicates = 0
        total_rejected = 0
        total_reported = 0

        seed_stats: Dict[str, SeedStat] = {}
        failed_seeds: List[str] = []

        raw_records_path = os.path.join(run_dir, "raw_records.jsonl")

        with open(raw_records_path, "w", encoding="utf-8") as raw_f:
            for seed in seeds:
                logger.info("Processing seed: '%s'...", seed)
                stat = SeedStat(seed=seed)
                start_offset = 0
                page_index = 0
                seed_done = False
                offsets: List[int] = []
                page_row_counts: List[int] = []

                while not seed_done:
                    draw = page_index + 1
                    req_length = self.config.page_size
                    if limit is not None:
                        remaining = limit - stat.fetched_rows
                        if remaining <= 0:
                            logger.info("Reached limit of %d records for seed '%s'", limit, seed)
                            break
                        req_length = min(req_length, remaining)

                    try:
                        page_result = self.client.fetch_page(
                            seed=seed,
                            start=start_offset,
                            length=req_length,
                            search_by=search_mode,
                            draw=draw
                        )
                    except BISError as err:
                        logger.error("Error fetching seed '%s' at offset %d: %s", seed, start_offset, err)
                        stat.failed = True
                        stat.error_message = str(err)
                        failed_seeds.append(seed)
                        break

                    # Record reported total on first page
                    if page_index == 0:
                        stat.reported_total = page_result.total_records
                        total_reported += page_result.total_records
                        logger.info(
                            "Seed '%s' reports %d total records in BIS catalogue.",
                            seed, page_result.total_records
                        )

                    stat.pages_fetched += 1
                    offsets.append(start_offset)
                    page_row_counts.append(len(page_result.rows))

                    # Save raw page response to disk
                    page_filename = f"seed_{seed}_page_{page_index:04d}.json"
                    page_path = os.path.join(pages_dir, page_filename)
                    with open(page_path, "w", encoding="utf-8") as pf:
                        json.dump(page_result.raw_response, pf, ensure_ascii=False)

                    page_index += 1

                    rows = page_result.rows
                    if not rows:
                        logger.info("No more rows returned for seed '%s'. Pagination complete.", seed)
                        break

                    logger.info(
                        "Seed '%s' page %d: received %d rows (offset %d / %d)",
                        seed, page_index, len(rows), start_offset + len(rows), page_result.total_records
                    )

                    stat.fetched_rows += len(rows)
                    total_raw_rows += len(rows)

                    for r in rows:
                        is_valid, clean_id, reason = RawRecordValidator.validate_raw_row(r)
                        if not is_valid or not clean_id:
                            stat.rejected_rows += 1
                            total_rejected += 1
                            rejected_identities.append({
                                "seed": seed,
                                "row": r,
                                "reason": reason
                            })
                            continue

                        # Check for duplicates
                        if clean_id in seen_identities:
                            stat.duplicate_rows += 1
                            total_duplicates += 1
                            is_dup = True
                        else:
                            seen_identities.add(clean_id)
                            stat.unique_rows += 1
                            total_unique_rows += 1
                            is_dup = False

                        # Record in consolidated JSONL with provenance metadata
                        record_entry = {
                            "seed": seed,
                            "clean_id": clean_id,
                            "is_duplicate": is_dup,
                            "retrieved_at": page_result.retrieved_at,
                            "raw": r
                        }
                        raw_f.write(json.dumps(record_entry, ensure_ascii=False) + "\n")

                    start_offset += len(rows)

                    # Termination condition: fetched all reported or empty batch
                    if start_offset >= page_result.total_records or len(rows) < req_length:
                        seed_done = True

                # Validate pagination completeness if not already failed on transport
                if not stat.failed:
                    is_valid_pag, pag_err = self.validate_seed_pagination(
                        seed=seed,
                        offsets=offsets,
                        page_row_counts=page_row_counts,
                        reported_total=stat.reported_total,
                        page_size=self.config.page_size,
                        limit=limit
                    )
                    if not is_valid_pag:
                        logger.error("Pagination validation failed for seed '%s': %s", seed, pag_err)
                        stat.failed = True
                        stat.error_message = pag_err
                        if seed not in failed_seeds:
                            failed_seeds.append(seed)

                seed_stats[seed] = stat
                logger.info(
                    "Seed '%s' completed: fetched=%d, unique=%d, dups=%d, rejected=%d, failed=%s",
                    seed, stat.fetched_rows, stat.unique_rows, stat.duplicate_rows,
                    stat.rejected_rows, stat.failed
                )

        finished_at = datetime.now(timezone.utc).isoformat()

        # Determine overall run status
        if len(failed_seeds) == 0:
            overall_status = "SUCCESS"
        elif len(failed_seeds) == len(seeds):
            overall_status = "FAILED"
        else:
            overall_status = "PARTIAL"

        summary = IngestionRunSummary(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            search_mode=search_mode,
            seeds=seeds,
            config={
                "page_size": self.config.page_size,
                "delay_sec": self.config.delay_sec,
                "timeout_sec": self.config.timeout_sec,
                "max_retries": self.config.max_retries,
                "limit_per_seed": limit,
            },
            seed_stats={s: asdict(st) for s, st in seed_stats.items()},
            total_reported=total_reported,
            total_raw_rows=total_raw_rows,
            total_unique_rows=total_unique_rows,
            total_duplicates=total_duplicates,
            total_rejected=total_rejected,
            failed_seeds=failed_seeds,
            status=overall_status,
            output_dir=os.path.abspath(run_dir),
        )

        # Save metadata and summary
        summary_json_path = os.path.join(run_dir, "run_summary.json")
        with open(summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)

        summary_txt_path = os.path.join(run_dir, "run_summary.txt")
        with open(summary_txt_path, "w", encoding="utf-8") as f:
            f.write(summary.to_formatted_text() + "\n")

        metadata_path = os.path.join(run_dir, "run_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "seeds": seeds,
                "limit_per_seed": limit,
                "rejected_count": len(rejected_identities),
                "rejected_samples": rejected_identities[:50],
            }, f, indent=2, ensure_ascii=False)

        logger.info("\n%s", summary.to_formatted_text())
        return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Acquire raw BIS catalogue records via Know Your Standards portal.")
    parser.add_argument(
        "--seeds",
        type=str,
        default="0,1,2,3,4,5,6,7,8,9",
        help="Comma-separated digits/seeds to enumerate (default: 0,1,2,3,4,5,6,7,8,9)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum rows to fetch per seed (useful for smoke tests)"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Number of rows per DataTables request page (default: 500)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between requests (default: 0.5)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds (default: 60.0)"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Max retries per page on transient errors (default: 3)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/raw/bis",
        help="Base directory for storing raw run artifacts (default: data/raw/bis)"
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a quick smoke test with valid digit seeds (seeds: 7,8 with limit: 50)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.smoke_test:
        seeds = ["7", "8"]
        limit = args.limit or 50
    else:
        seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
        limit = args.limit

    fetcher = BISCatalogueFetcher(
        output_base_dir=args.output_dir,
        page_size=args.page_size,
        delay_sec=args.delay,
        timeout_sec=args.timeout,
        max_retries=args.retries
    )

    summary = fetcher.run_acquisition(seeds=seeds, limit=limit)
    print(f"\nCompleted run {summary.run_id} with status: {summary.status}")
    print(f"Audit summary written to: {summary.output_dir}/run_summary.txt")

    if summary.status == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
