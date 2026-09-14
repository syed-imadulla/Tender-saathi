"""
Module: src/catalogue/bis_normalizer.py
Purpose: Phase 2 BIS Catalogue Normalization, Validation, Deduplication, and Database Persistence.

Transforms raw BIS acquisition records from Phase 1 into a clean, validated,
provenance-aware standards catalogue stored in an isolated SQLite database.

Strict Scope Boundaries:
- Zero fabrication of missing identifiers.
- Complete audit trail and provenance for every record.
- Withdrawn standards are preserved.
- Different parts and sections are never collapsed.
- Production catalogue (data/catalogue/catalogue.db) remains untouched.
"""

import os
import re
import json
import sqlite3
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
import glob

from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bis_normalizer")


class ValidationCategory:
    VALID = "VALID"
    RECOVERABLE = "RECOVERABLE"
    DUPLICATE = "DUPLICATE"
    MALFORMED_SOURCE = "MALFORMED_SOURCE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"


@dataclass
class NormalizedBISStandard:
    """Normalized master standard record with multi-seed provenance."""
    canonical_id: str
    standard_number: str
    base_standard_number: str
    prefix: str
    base_number: str
    part: Optional[int]
    section: Optional[int]
    year: Optional[int]
    amendment: Optional[int]
    title: str
    technical_committee: Optional[str]
    department: Optional[str]
    aspect: Optional[str]
    amendments: str
    amendment_count: int
    status: str
    is_active: Optional[int]
    iso_equivalence: Optional[str]
    iso_equivalence_degree: Optional[str]
    source: str = "BIS"
    source_type: str = "BIS_KNOW_YOUR_STANDARD"
    source_url: Optional[str] = None
    retrieved_at: str = ""
    ingestion_run_id: str = ""
    seeds_observed: List[str] = field(default_factory=list)
    times_observed: int = 1
    first_seen: str = ""
    last_seen: str = ""
    raw_record_ref: str = ""
    is_recovered: bool = False
    recovery_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QuarantineRecord:
    """Record placed in quarantine with full diagnostic provenance."""
    raw_identifier: str
    raw_title: str
    reason: str
    validation_category: str
    source: str = "BIS"
    ingestion_run_id: str = ""
    raw_record_ref: str = ""
    raw_json: str = ""
    seed: str = ""
    retrieved_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BISCatalogueNormalizer:
    """Orchestrates Phase 2 normalization, validation, deduplication, and persistence."""

    DOWNLOAD_URL_PATTERN = re.compile(r"href=['\"]([^'\"]+)['\"]", re.IGNORECASE)

    def __init__(
        self,
        input_dir: str = "data/raw/bis/run_20260914_042545",
        output_db_path: str = "data/catalogue/bis_catalogue.db",
        report_dir: str = "reports"
    ):
        self.input_dir = input_dir
        self.output_db_path = output_db_path
        self.report_dir = report_dir
        os.makedirs(os.path.dirname(os.path.abspath(output_db_path)), exist_ok=True)
        os.makedirs(report_dir, exist_ok=True)

    @classmethod
    def extract_download_url(cls, download_action: Any) -> Optional[str]:
        """Extracts official standards URL from DownloadAction HTML snippet."""
        if not download_action or not isinstance(download_action, str):
            return None
        m = cls.DOWNLOAD_URL_PATTERN.search(download_action)
        return m.group(1).strip() if m else None

    @classmethod
    def determine_status(cls, raw_row: Dict[str, Any]) -> Tuple[str, Optional[int]]:
        """
        Determines lifecycle status strictly from BIS raw fields without fabricating facts.
        Returns: (status_str, is_active_int)
        """
        ws = raw_row.get("withdrawn_status")
        ws_w = str(ws).strip().upper() == "W"

        is_no = raw_row.get("is_no", "")
        parts = re.split(r"<br\s*/?>", is_no, flags=re.IGNORECASE) if is_no else []
        status_text = parts[2].strip().upper() if len(parts) > 2 else ""

        title = raw_row.get("is_title", "").upper()

        # Explicit withdrawn signal
        if ws_w or "WITHDRAWN" in status_text:
            return "WITHDRAWN", 0

        # Superseded mentions
        if "SUPERSED" in status_text or "SUPERSED" in title:
            return "SUPERSEDED", 0

        # Active indications
        if "ACTIVE" in status_text or "CONCURRENT RUNNING" in status_text:
            return "ACTIVE", 1

        # Unknown / unstated status
        return "UNKNOWN", None

    @classmethod
    def extract_department(cls, tc_code: Optional[str]) -> Optional[str]:
        """
        Extracts department code prefix from technical committee (e.g. 'CED' from 'CED 50').
        Does not invent synthetic definitions.
        """
        if not tc_code or not tc_code.strip():
            return None
        clean_tc = tc_code.strip()
        m = re.match(r"^([A-Za-z]+)", clean_tc)
        return m.group(1).upper() if m else None

    @classmethod
    def extract_iso_equivalence(cls, is_no_raw: Any) -> Optional[str]:
        """Extracts international equivalent standard identifier from HTML segment 2."""
        if not is_no_raw or not isinstance(is_no_raw, str):
            return None
        parts = re.split(r"<br\s*/?>", is_no_raw, flags=re.IGNORECASE)
        if len(parts) > 1:
            eq = re.sub(r"<[^>]+>", "", parts[1]).strip()
            # If it's just 'Identical' or empty, not a distinct standard identifier
            if eq and not eq.lower().startswith("identical") and not eq.lower().startswith("indigenous"):
                return eq
        return None

    def init_database(self, conn: sqlite3.Connection):
        """Initializes SQLite schema for the isolated BIS catalogue."""
        with conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS catalogue_standards (
                canonical_id TEXT PRIMARY KEY,
                standard_number TEXT NOT NULL,
                base_standard_number TEXT NOT NULL,
                prefix TEXT NOT NULL,
                base_number TEXT NOT NULL,
                part INTEGER,
                section INTEGER,
                year INTEGER,
                amendment INTEGER,
                title TEXT NOT NULL,
                technical_committee TEXT,
                department TEXT,
                aspect TEXT,
                amendments TEXT,
                amendment_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                is_active INTEGER,
                iso_equivalence TEXT,
                iso_equivalence_degree TEXT,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT,
                retrieved_at TEXT NOT NULL,
                ingestion_run_id TEXT NOT NULL,
                seeds_observed_json TEXT NOT NULL,
                times_observed INTEGER NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                raw_record_ref TEXT NOT NULL,
                is_recovered INTEGER NOT NULL DEFAULT 0,
                recovery_reason TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_bis_std_num ON catalogue_standards(standard_number);
            CREATE INDEX IF NOT EXISTS idx_bis_base_num ON catalogue_standards(base_standard_number);
            CREATE INDEX IF NOT EXISTS idx_bis_status ON catalogue_standards(status);
            CREATE INDEX IF NOT EXISTS idx_bis_prefix ON catalogue_standards(prefix);
            CREATE INDEX IF NOT EXISTS idx_bis_dept ON catalogue_standards(department);

            -- Compatibility table matching StandardsDatabase interface
            CREATE TABLE IF NOT EXISTS standards (
                standard_id TEXT PRIMARY KEY,
                standard_number TEXT NOT NULL,
                year INTEGER,
                full_title TEXT NOT NULL,
                status TEXT NOT NULL,
                reaffirmed_year INTEGER,
                amendments_count INTEGER,
                technical_committee TEXT,
                ics TEXT,
                udc TEXT,
                scope TEXT,
                notes TEXT,
                source TEXT NOT NULL,
                source_url TEXT,
                retrieved_at TEXT,
                original_standard_identifier TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                evidence TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_compat_std_num ON standards(standard_number);
            CREATE INDEX IF NOT EXISTS idx_compat_status ON standards(status);

            -- Quarantine / Rejection Audit Table
            CREATE TABLE IF NOT EXISTS quarantine_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_identifier TEXT,
                raw_title TEXT,
                reason TEXT NOT NULL,
                validation_category TEXT NOT NULL,
                source TEXT NOT NULL,
                ingestion_run_id TEXT NOT NULL,
                raw_record_ref TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                seed TEXT,
                retrieved_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_quarantine_cat ON quarantine_records(validation_category);

            -- Ingestion Run Summary
            CREATE TABLE IF NOT EXISTS ingestion_summary (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                total_raw_rows INTEGER NOT NULL,
                accepted_standards INTEGER NOT NULL,
                duplicate_rows INTEGER NOT NULL,
                quarantined_rows INTEGER NOT NULL,
                recovered_standards INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            );
            """)

    def process(self) -> Dict[str, Any]:
        """Executes full normalization, validation, deduplication, and database persistence."""
        started_at = datetime.now(timezone.utc).isoformat()
        run_id = os.path.basename(os.path.normpath(self.input_dir))
        logger.info("Starting Phase 2 normalization on %s...", self.input_dir)

        # Ensure production DB is untouched
        prod_db_path = "data/catalogue/catalogue.db"
        prod_count_before = self._get_db_count(prod_db_path)
        logger.info("Verified production database %s has %d standards before run.", prod_db_path, prod_count_before)

        # Locate page files
        pages_pattern = os.path.join(self.input_dir, "pages", "*.json")
        page_files = sorted(glob.glob(pages_pattern))
        if not page_files:
            raise FileNotFoundError(f"No page files found matching {pages_pattern}")

        logger.info("Discovered %d raw page files to process.", len(page_files))

        # Metrics collectors
        total_raw_rows = 0
        canonical_map: Dict[str, NormalizedBISStandard] = {}
        quarantine_list: List[QuarantineRecord] = []
        duplicate_rows_count = 0
        recovered_rows_count = 0

        # Breakdown stats
        prefix_distribution: Dict[str, int] = {}
        status_distribution: Dict[str, int] = {}
        department_distribution: Dict[str, int] = {}
        category_distribution: Dict[str, int] = {
            ValidationCategory.VALID: 0,
            ValidationCategory.RECOVERABLE: 0,
            ValidationCategory.DUPLICATE: 0,
            ValidationCategory.MALFORMED_SOURCE: 0,
            ValidationCategory.UNSUPPORTED_FORMAT: 0,
        }

        # Track Phase 1 rejections explicitly
        phase1_rejection_pattern = re.compile(
            r"^(IS\s*/\s*ISO\s*/\s*IEC|IS\s*/\s*IEC|IS\s*/\s*ISO|IS\s*/\s*QC|IS\s*/\s*CISPR|IS|SP)\s*(\d+)",
            re.IGNORECASE
        )
        phase1_rejected_instances = 0
        phase1_recovered_instances = 0
        phase1_quarantined_instances = 0

        now_iso = datetime.now(timezone.utc).isoformat()

        for page_file in page_files:
            page_basename = os.path.basename(page_file)
            # Parse seed from filename: seed_X_page_YYYY.json
            seed_match = re.search(r"seed_([^_]+)_page_(\d+)", page_basename)
            seed_val = seed_match.group(1) if seed_match else "UNKNOWN"

            with open(page_file, "r", encoding="utf-8") as pf:
                try:
                    data = json.load(pf)
                except Exception as err:
                    logger.error("Failed to read JSON from %s: %s", page_file, err)
                    continue

                rows = data.get("aaData", [])
                for row_idx, r in enumerate(rows):
                    total_raw_rows += 1
                    raw_ref = f"{page_basename}:{row_idx}"

                    raw_is_no = r.get("is_no", "")
                    clean_id_str = StandardIdentifierNormalizer.clean_html(raw_is_no)
                    raw_title = r.get("is_title", "") or ""

                    # Check if Phase 1 regex rejected this row
                    was_p1_rejected = not bool(phase1_rejection_pattern.search(clean_id_str))
                    if was_p1_rejected:
                        phase1_rejected_instances += 1

                    # 1. Non-standard publications (e.g. SI B Standards India magazine)
                    if clean_id_str.startswith("SI B") or clean_id_str.startswith("SI/B"):
                        category_distribution[ValidationCategory.UNSUPPORTED_FORMAT] += 1
                        q_rec = QuarantineRecord(
                            raw_identifier=clean_id_str,
                            raw_title=raw_title,
                            reason="Unsupported format: Periodical / Standards India magazine (not a technical standard)",
                            validation_category=ValidationCategory.UNSUPPORTED_FORMAT,
                            source="BIS",
                            ingestion_run_id=run_id,
                            raw_record_ref=raw_ref,
                            raw_json=json.dumps(r, ensure_ascii=False),
                            seed=seed_val,
                            retrieved_at=now_iso
                        )
                        quarantine_list.append(q_rec)
                        if was_p1_rejected:
                            phase1_quarantined_instances += 1
                        continue

                    # 2. Parse identifier
                    parsed_id = StandardIdentifierNormalizer.parse(raw_is_no)

                    # Check if recoverable
                    is_recovered = False
                    recovery_reason = None
                    if parsed_id.is_valid:
                        if clean_id_str.startswith("ÍS") or clean_id_str.startswith("Ís"):
                            is_recovered = True
                            recovery_reason = "Diacritic typo in prefix normalized from ÍS to IS"
                        elif re.match(r"^(\d+)(?:\s+\1)?(?:\s*:\s*|\s*-\s*)(19\d\d|20\d\d)", clean_id_str):
                            is_recovered = True
                            recovery_reason = "Missing IS prefix recovered from unambiguous standard digits and year"

                    if not parsed_id.is_valid:
                        # Malformed upstream source
                        category_distribution[ValidationCategory.MALFORMED_SOURCE] += 1
                        reason = "Malformed identifier: missing base standard number or invalid format"
                        if not parsed_id.base_number:
                            reason = "Malformed identifier: standard number is missing in source"
                        q_rec = QuarantineRecord(
                            raw_identifier=clean_id_str,
                            raw_title=raw_title,
                            reason=reason,
                            validation_category=ValidationCategory.MALFORMED_SOURCE,
                            source="BIS",
                            ingestion_run_id=run_id,
                            raw_record_ref=raw_ref,
                            raw_json=json.dumps(r, ensure_ascii=False),
                            seed=seed_val,
                            retrieved_at=now_iso
                        )
                        quarantine_list.append(q_rec)
                        if was_p1_rejected:
                            phase1_quarantined_instances += 1
                        continue

                    # Identifier is valid or recovered
                    if was_p1_rejected:
                        phase1_recovered_instances += 1

                    cid = parsed_id.canonical_id

                    # 3. Deduplication Check
                    if cid in canonical_map:
                        duplicate_rows_count += 1
                        category_distribution[ValidationCategory.DUPLICATE] += 1
                        existing = canonical_map[cid]
                        existing.times_observed += 1
                        if seed_val not in existing.seeds_observed:
                            existing.seeds_observed.append(seed_val)
                        existing.last_seen = now_iso
                        continue

                    # First time seeing this canonical standard
                    if is_recovered:
                        recovered_rows_count += 1
                        category_distribution[ValidationCategory.RECOVERABLE] += 1
                    else:
                        category_distribution[ValidationCategory.VALID] += 1

                    # Extract metadata fields
                    status_str, is_act = self.determine_status(r)
                    status_distribution[status_str] = status_distribution.get(status_str, 0) + 1

                    tc_val = r.get("technical_committee")
                    clean_tc = re.sub(r"\s+", " ", tc_val.strip()) if tc_val else None
                    dept_val = self.extract_department(clean_tc)
                    if dept_val:
                        department_distribution[dept_val] = department_distribution.get(dept_val, 0) + 1

                    prefix_distribution[parsed_id.prefix] = prefix_distribution.get(parsed_id.prefix, 0) + 1

                    amd_str = str(r.get("amendments", "0")).strip()
                    amd_cnt = int(amd_str) if amd_str.isdigit() else 0

                    iso_eq = self.extract_iso_equivalence(raw_is_no)
                    iso_deg = r.get("referirmatin_year")  # Equivalence degree in BIS source
                    src_url = self.extract_download_url(r.get("DownloadAction"))

                    norm_std = NormalizedBISStandard(
                        canonical_id=cid,
                        standard_number=parsed_id.canonical_number,
                        base_standard_number=parsed_id.base_standard_number,
                        prefix=parsed_id.prefix,
                        base_number=parsed_id.base_number,
                        part=parsed_id.part,
                        section=parsed_id.section,
                        year=parsed_id.year,
                        amendment=parsed_id.amendment,
                        title=raw_title.strip(),
                        technical_committee=clean_tc,
                        department=dept_val,
                        aspect=r.get("aspect"),
                        amendments=amd_str,
                        amendment_count=amd_cnt,
                        status=status_str,
                        is_active=is_act,
                        iso_equivalence=iso_eq,
                        iso_equivalence_degree=iso_deg,
                        source="BIS",
                        source_type="BIS_KNOW_YOUR_STANDARD",
                        source_url=src_url,
                        retrieved_at=now_iso,
                        ingestion_run_id=run_id,
                        seeds_observed=[seed_val],
                        times_observed=1,
                        first_seen=now_iso,
                        last_seen=now_iso,
                        raw_record_ref=raw_ref,
                        is_recovered=is_recovered,
                        recovery_reason=recovery_reason
                    )
                    canonical_map[cid] = norm_std

        finished_at = datetime.now(timezone.utc).isoformat()
        logger.info("Processed %d raw rows into %d unique standards.", total_raw_rows, len(canonical_map))
        logger.info("Quarantined: %d rows (%d unique IDs).", len(quarantine_list), len(set(q.raw_identifier for q in quarantine_list)))

        # 4. Database Persistence
        conn = sqlite3.connect(self.output_db_path)
        self.init_database(conn)

        with conn:
            # Insert into catalogue_standards
            cat_rows = [
                (
                    s.canonical_id,
                    s.standard_number,
                    s.base_standard_number,
                    s.prefix,
                    s.base_number,
                    s.part,
                    s.section,
                    s.year,
                    s.amendment,
                    s.title,
                    s.technical_committee,
                    s.department,
                    s.aspect,
                    s.amendments,
                    s.amendment_count,
                    s.status,
                    s.is_active,
                    s.iso_equivalence,
                    s.iso_equivalence_degree,
                    s.source,
                    s.source_type,
                    s.source_url,
                    s.retrieved_at,
                    s.ingestion_run_id,
                    json.dumps(s.seeds_observed),
                    s.times_observed,
                    s.first_seen,
                    s.last_seen,
                    s.raw_record_ref,
                    1 if s.is_recovered else 0,
                    s.recovery_reason
                )
                for s in canonical_map.values()
            ]
            conn.executemany("""
                INSERT OR REPLACE INTO catalogue_standards VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, cat_rows)

            # Insert into compatibility table standards
            compat_rows = [
                (
                    s.canonical_id,
                    s.standard_number,
                    s.year,
                    s.title,
                    s.status,
                    None,  # reaffirmed_year not in BIS raw
                    s.amendment_count,
                    s.technical_committee,
                    None,  # ics
                    None,  # udc
                    None,  # scope
                    s.iso_equivalence_degree,  # notes
                    s.source,
                    s.source_url,
                    s.retrieved_at,
                    s.standard_number,
                    "VERIFIED",
                    f"Acquired from BIS Know Your Standards (seed: {','.join(s.seeds_observed)})"
                )
                for s in canonical_map.values()
            ]
            conn.executemany("""
                INSERT OR REPLACE INTO standards VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, compat_rows)

            # Insert quarantine records
            q_rows = [
                (
                    q.raw_identifier,
                    q.raw_title,
                    q.reason,
                    q.validation_category,
                    q.source,
                    q.ingestion_run_id,
                    q.raw_record_ref,
                    q.raw_json,
                    q.seed,
                    q.retrieved_at
                )
                for q in quarantine_list
            ]
            conn.executemany("""
                INSERT INTO quarantine_records (
                    raw_identifier, raw_title, reason, validation_category, source,
                    ingestion_run_id, raw_record_ref, raw_json, seed, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, q_rows)

        # Verify production DB remained untouched
        prod_count_after = self._get_db_count(prod_db_path)
        if prod_count_after != prod_count_before:
            raise RuntimeError(f"PRODUCTION DATABASE WAS MODIFIED! Before: {prod_count_before}, After: {prod_count_after}")
        logger.info("VERIFIED: Production database %s remains untouched at %d records.", prod_db_path, prod_count_after)

        # Build Summary Report
        summary: Dict[str, Any] = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "database_path": self.output_db_path,
            "total_raw_rows_processed": total_raw_rows,
            "unique_canonical_standards": len(canonical_map),
            "duplicate_row_instances": duplicate_rows_count,
            "quarantined_row_instances": len(quarantine_list),
            "unique_quarantined_identifiers": len(set(q.raw_identifier for q in quarantine_list)),
            "recovered_standards_count": recovered_rows_count,
            "category_breakdown": category_distribution,
            "phase1_rejections_analysis": {
                "phase1_rejected_row_instances": phase1_rejected_instances,
                "recovered_by_phase2": phase1_recovered_instances,
                "still_quarantined": phase1_quarantined_instances,
                "recovery_rate_pct": round((phase1_recovered_instances / phase1_rejected_instances) * 100, 2) if phase1_rejected_instances else 0.0
            },
            "status_distribution": status_distribution,
            "prefix_distribution": dict(sorted(prefix_distribution.items(), key=lambda x: x[1], reverse=True)),
            "department_distribution": dict(sorted(department_distribution.items(), key=lambda x: x[1], reverse=True)),
            "production_db_verified": {
                "path": prod_db_path,
                "count": prod_count_after,
                "untouched": True
            }
        }

        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO ingestion_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                started_at,
                finished_at,
                total_raw_rows,
                len(canonical_map),
                duplicate_rows_count,
                len(quarantine_list),
                recovered_rows_count,
                json.dumps(summary, indent=2)
            ))
        conn.close()

        # Write reports
        self._write_reports(summary)
        return summary

    def _get_db_count(self, db_path: str) -> int:
        """Helper to get record count in a database."""
        if not os.path.exists(db_path):
            return 0
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM standards")
            count = cur.fetchone()[0]
            return count
        except sqlite3.OperationalError:
            return 0
        finally:
            conn.close()

    def _write_reports(self, summary: Dict[str, Any]):
        """Writes JSON and Markdown quality reports."""
        json_path = os.path.join(self.report_dir, "phase2_bis_catalogue_report.json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(summary, jf, indent=2, ensure_ascii=False)
        logger.info("Saved JSON quality report to %s", json_path)

        md_path = os.path.join(self.report_dir, "phase2_bis_catalogue_report.md")
        lines = [
            "# PHASE 2 BIS CATALOGUE REPORT",
            "",
            f"**Run ID**: `{summary['run_id']}`  ",
            f"**Database Output**: `{summary['database_path']}`  ",
            f"**Started At**: `{summary['started_at']}`  ",
            f"**Finished At**: `{summary['finished_at']}`  ",
            "",
            "## 1. Executive Summary",
            "",
            f"- **Raw Rows Processed**: {summary['total_raw_rows_processed']:,}",
            f"- **Unique Canonical Standards**: {summary['unique_canonical_standards']:,}",
            f"- **Duplicate Row Instances**: {summary['duplicate_row_instances']:,}",
            f"- **Quarantined Row Instances**: {summary['quarantined_row_instances']:,}",
            f"- **Unique Quarantined Identifiers**: {summary['unique_quarantined_identifiers']:,}",
            f"- **Recovered Standards**: {summary['recovered_standards_count']:,}",
            f"- **Production DB Verified (`data/catalogue/catalogue.db`)**: {summary['production_db_verified']['count']} records (UNTOUCHED)",
            "",
            "## 2. Phase 1 Rejection Resolution",
            "",
            f"- **Phase 1 Rejected Row Instances**: {summary['phase1_rejections_analysis']['phase1_rejected_row_instances']:,}",
            f"- **Successfully Recovered / Normalized**: {summary['phase1_rejections_analysis']['recovered_by_phase2']:,} ({summary['phase1_rejections_analysis']['recovery_rate_pct']}%)",
            f"- **Still Quarantined (Malformed / Unsupported)**: {summary['phase1_rejections_analysis']['still_quarantined']:,}",
            "",
            "## 3. Classification Breakdown",
            "",
            "| Category | Count | Percentage |",
            "| :--- | :--- | :--- |",
        ]
        for cat, cnt in summary["category_breakdown"].items():
            pct = (cnt / summary["total_raw_rows_processed"]) * 100
            lines.append(f"| `{cat}` | {cnt:,} | {pct:.2f}% |")

        lines.extend([
            "",
            "## 4. Status Distribution",
            "",
            "| Status | Standards Count | Percentage |",
            "| :--- | :--- | :--- |",
        ])
        for st, cnt in summary["status_distribution"].items():
            pct = (cnt / summary["unique_canonical_standards"]) * 100
            lines.append(f"| `{st}` | {cnt:,} | {pct:.2f}% |")

        lines.extend([
            "",
            "## 5. Top Identifier Prefixes",
            "",
            "| Prefix | Count |",
            "| :--- | :--- |",
        ])
        for pfx, cnt in list(summary["prefix_distribution"].items())[:25]:
            lines.append(f"| `{pfx}` | {cnt:,} |")

        lines.extend([
            "",
            "## 6. Top Technical Departments",
            "",
            "| Department Code | Standards Count |",
            "| :--- | :--- |",
        ])
        for dept, cnt in list(summary["department_distribution"].items())[:20]:
            lines.append(f"| `{dept}` | {cnt:,} |")

        lines.extend([
            "",
            "---",
            "*Report generated by TenderSaathi Phase 2 BIS Normalizer.*"
        ])

        with open(md_path, "w", encoding="utf-8") as mf:
            mf.write("\n".join(lines))
        logger.info("Saved Markdown quality report to %s", md_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2 BIS Catalogue Normalizer")
    parser.add_argument("--input-dir", default="data/raw/bis/run_20260914_042545", help="Path to Phase 1 raw data directory")
    parser.add_argument("--output-db", default="data/catalogue/bis_catalogue.db", help="Path to output SQLite database")
    parser.add_argument("--report-dir", default="reports", help="Directory to save quality reports")

    args = parser.parse_args()
    normalizer = BISCatalogueNormalizer(
        input_dir=args.input_dir,
        output_db_path=args.output_db,
        report_dir=args.report_dir
    )
    res = normalizer.process()
    print("\nPhase 2 Complete. Final Summary:")
    print(json.dumps(res, indent=2))
