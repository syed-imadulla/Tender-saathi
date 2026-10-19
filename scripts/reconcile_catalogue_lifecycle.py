"""
scripts/reconcile_catalogue_lifecycle.py — Phase 35 National BIS Catalogue Lifecycle Hygiene

Reconciles the 13,024 UNKNOWN records in data/catalogue/bis_catalogue.db:
- Investigates raw portal column shifting where '(Active)' was ingested into 'iso_equivalence'.
- Reconciles records deterministically where evidence is explicit in the raw data.
- Updates status to 'ACTIVE', is_active to 1, records provenance in recovery_reason.
- Retains records as 'UNKNOWN' when explicit status evidence is absent (e.g. true ISO adoptions with missing status).
- Cleans parenthetical status strings from iso_equivalence.
- Rebuilds data/catalogue/catalogue_search_index.db FTS5 index.
- Fully idempotent and deterministic.
"""

from __future__ import annotations

import os
import sys
import sqlite3
import argparse
import logging
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.build_catalogue_search_index import build_catalogue_search_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconcile_catalogue_lifecycle")

DEFAULT_CATALOGUE_DB = "data/catalogue/bis_catalogue.db"


def reconcile_catalogue_lifecycle(db_path: str = DEFAULT_CATALOGUE_DB, dry_run: bool = False) -> Dict[str, Any]:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Catalogue database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Pre-audit counts
    cur.execute("SELECT COUNT(*) FROM catalogue_standards")
    total_records = cur.fetchone()[0]

    cur.execute("SELECT status, COUNT(*) FROM catalogue_standards GROUP BY status")
    pre_status_counts = dict(cur.fetchall())

    cur.execute("""
        SELECT COUNT(*) FROM catalogue_standards
        WHERE status = 'UNKNOWN' AND (
            iso_equivalence = '(Active)' OR
            iso_equivalence = '(Active,Concurrent Running )' OR
            iso_equivalence = '(Concurrent Running )'
        )
    """)
    eligible_active_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM catalogue_standards
        WHERE status = 'UNKNOWN' AND (
            iso_equivalence IS NULL OR
            iso_equivalence NOT IN ('(Active)', '(Active,Concurrent Running )', '(Concurrent Running )')
        )
    """)
    unresolved_unknown_count = cur.fetchone()[0]

    logger.info("Pre-reconciliation counts for %s:", db_path)
    logger.info("  Total records: %d", total_records)
    logger.info("  Status breakdown: %s", pre_status_counts)
    logger.info("  Eligible for ACTIVE reconciliation: %d", eligible_active_count)
    logger.info("  Retained as UNKNOWN (insufficient evidence): %d", unresolved_unknown_count)

    if dry_run:
        conn.close()
        return {
            "dry_run": True,
            "total_records": total_records,
            "pre_status_counts": pre_status_counts,
            "eligible_active_count": eligible_active_count,
            "unresolved_unknown_count": unresolved_unknown_count,
        }

    # 1. Reconcile UNKNOWN standards that contain explicit raw Active status in iso_equivalence
    cur.execute("""
        UPDATE catalogue_standards
        SET
            status = 'ACTIVE',
            is_active = 1,
            is_recovered = 1,
            recovery_reason = 'RECONCILED_FROM_RAW_PORTAL_STATUS_COLUMN:iso_equivalence=' || COALESCE(iso_equivalence, '')
        WHERE status = 'UNKNOWN' AND (
            iso_equivalence = '(Active)' OR
            iso_equivalence = '(Active,Concurrent Running )' OR
            iso_equivalence = '(Concurrent Running )'
        )
    """)
    reconciled_active = cur.rowcount

    # 2. Clean parenthetical status strings from iso_equivalence across all records
    cur.execute("""
        UPDATE catalogue_standards
        SET iso_equivalence = NULL
        WHERE iso_equivalence LIKE '(Active%' OR iso_equivalence LIKE '(Withdrawn%' OR iso_equivalence LIKE '(Concurrent%'
    """)
    cleaned_iso_strings = cur.rowcount

    conn.commit()

    # Post-audit counts
    cur.execute("SELECT status, COUNT(*) FROM catalogue_standards GROUP BY status")
    post_status_counts = dict(cur.fetchall())

    conn.close()

    logger.info("Post-reconciliation counts for %s:", db_path)
    logger.info("  Status breakdown: %s", post_status_counts)
    logger.info("  Reconciled ACTIVE count: %d", reconciled_active)
    logger.info("  Cleaned parenthetical ISO strings: %d", cleaned_iso_strings)

    # 3. Rebuild catalogue search index
    logger.info("Rebuilding catalogue full-text search index (catalogue_search_index.db)...")
    index_res = build_catalogue_search_index()
    logger.info("Index rebuild complete: %s", index_res)

    return {
        "dry_run": False,
        "total_records": total_records,
        "pre_status_counts": pre_status_counts,
        "post_status_counts": post_status_counts,
        "reconciled_active": reconciled_active,
        "retained_unknown": post_status_counts.get("UNKNOWN", 0),
        "cleaned_iso_strings": cleaned_iso_strings,
        "index_record_count": index_res.get("record_count", 0),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile catalogue lifecycle statuses")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without modifying")
    args = parser.parse_args()

    res = reconcile_catalogue_lifecycle(dry_run=args.dry_run)
    print("\nResult Summary:")
    for k, v in res.items():
        print(f"  {k}: {v}")
