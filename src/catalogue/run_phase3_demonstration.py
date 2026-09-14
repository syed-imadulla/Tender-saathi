"""
Module: src/catalogue/run_phase3_demonstration.py
Purpose: Registers the Phase 2 baseline snapshot and executes a controlled comparison demonstration.
"""

import os
import json
import sqlite3
import copy
from datetime import datetime, timezone
import logging

from src.catalogue.change_detector import (
    CatalogueChangeDetector,
    SnapshotMetadata,
    ComparableStandardRecord,
    ChangeType
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phase3_demo")


def run_phase3_demonstration(
    db_path: str = "data/catalogue/bis_catalogue.db",
    report_dir: str = "reports"
):
    detector = CatalogueChangeDetector(db_path=db_path, report_dir=report_dir)
    conn = sqlite3.connect(db_path)
    detector.init_database_tables(conn)

    # 1. Register the Phase 2 catalogue as baseline snapshot
    baseline_records = detector.load_snapshot_from_db(conn, table_name="catalogue_standards")
    baseline_count = len(baseline_records)
    logger.info("Loaded baseline snapshot from %s: %d records.", db_path, baseline_count)
    if baseline_count != 35208:
        raise ValueError(f"Expected 35,208 baseline records, found {baseline_count}!")

    baseline_snap_id = "snapshot_phase2_baseline_20260914"
    baseline_meta = SnapshotMetadata(
        snapshot_id=baseline_snap_id,
        created_at="2026-09-14T05:45:25Z",
        source="BIS",
        source_type="BIS_KNOW_YOUR_STANDARD",
        record_count=baseline_count,
        run_id="run_20260914_042545",
        input_reference="data/raw/bis/run_20260914_042545",
        metadata_json=json.dumps({"description": "Official Phase 2 normalized baseline snapshot", "unique_standards": baseline_count})
    )
    detector.register_snapshot(conn, baseline_meta)
    logger.info("Registered baseline snapshot: %s", baseline_snap_id)

    # 2. Build controlled fresh snapshot (simulating a subsequent acquisition cycle)
    # Deep copy baseline records
    fresh_records: dict[str, ComparableStandardRecord] = {
        cid: copy.deepcopy(rec) for cid, rec in baseline_records.items()
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    fresh_snap_id = f"snapshot_phase3_fresh_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # A. 5 NEW Standards
    for i in range(1, 6):
        new_cid = f"IS-9900{i}-2026"
        fresh_records[new_cid] = ComparableStandardRecord(
            canonical_id=new_cid,
            standard_number=f"IS 9900{i} : 2026",
            base_standard_number=f"IS 9900{i}",
            part=None,
            section=None,
            year=2026,
            title=f"Advanced Smart Grid Specification Part {i}",
            technical_committee="ETD 50",
            aspect="Product Specification",
            amendments="0",
            amendment_count=0,
            status="ACTIVE",
            is_active=1,
            iso_equivalence=None,
            iso_equivalence_degree="Indigenous",
            source="BIS",
            source_url=f"https://standardsbis.bsbedge.com/search_redirect.aspx?id=9900{i}",
            raw_record_ref=f"fresh_run_page_0001.json:{i}"
        )

    # B. 10 Explicit WITHDRAWN Transitions
    # Pick 10 active records and transition them to WITHDRAWN
    active_keys = [cid for cid, r in fresh_records.items() if r.status == "ACTIVE" and not cid.startswith("IS-9900")][:10]
    for cid in active_keys:
        rec = fresh_records[cid]
        rec.status = "WITHDRAWN"
        rec.is_active = 0

    # C. 2 Explicit SUPERSEDED Transitions
    # Pick 2 active records and mark them explicitly as SUPERSEDED
    super_keys = [cid for cid, r in fresh_records.items() if r.status == "ACTIVE" and cid not in active_keys and not cid.startswith("IS-9900")][:2]
    for cid in super_keys:
        rec = fresh_records[cid]
        rec.status = "SUPERSEDED"
        rec.is_active = 0

    # D. 15 STATUS_CHANGED Transitions (UNKNOWN -> ACTIVE)
    unknown_keys = [cid for cid, r in fresh_records.items() if r.status == "UNKNOWN"][:15]
    for cid in unknown_keys:
        rec = fresh_records[cid]
        rec.status = "ACTIVE"
        rec.is_active = 1

    # E. 20 UPDATED Metadata Transitions (title, amendment, TC updates)
    candidate_keys = [cid for cid, r in fresh_records.items() if r.status == "ACTIVE" and cid not in active_keys and cid not in super_keys][:20]
    for idx, cid in enumerate(candidate_keys):
        rec = fresh_records[cid]
        if idx % 3 == 0:
            rec.title = rec.title + " (Second Revision)"
        elif idx % 3 == 1:
            rec.amendment_count += 1
            rec.amendments = str(rec.amendment_count)
        else:
            rec.aspect = "Revised Performance Standard"

    # F. 5 MISSING_FROM_SOURCE Standards (absent in fresh search, must be preserved)
    missing_keys = [cid for cid, r in fresh_records.items() if r.status == "UNKNOWN" and cid not in unknown_keys][:5]
    for cid in missing_keys:
        del fresh_records[cid]

    # Register the fresh snapshot
    fresh_meta = SnapshotMetadata(
        snapshot_id=fresh_snap_id,
        created_at=now_iso,
        source="BIS",
        source_type="BIS_KNOW_YOUR_STANDARD",
        record_count=len(fresh_records),
        run_id="run_phase3_controlled_demo",
        input_reference="controlled_bis_snapshot_comparison",
        metadata_json=json.dumps({"description": "Controlled fresh snapshot for Phase 3 change detection verification"})
    )
    detector.register_snapshot(conn, fresh_meta)

    # 3. Execute Comparison
    result = detector.compare_snapshots(
        previous_records=baseline_records,
        current_records=fresh_records,
        snapshot_id_previous=baseline_snap_id,
        snapshot_id_current=fresh_snap_id,
        detected_at=now_iso
    )

    # 4. Persist change history
    detector.persist_change_history(conn, result, include_unchanged=False)

    # 5. Write reports
    detector.write_reports(result)

    conn.close()
    return result


if __name__ == "__main__":
    res = run_phase3_demonstration()
    print("\nPhase 3 Demonstration Complete. Result Summary:")
    print(f"Previous Records: {res.previous_record_count}")
    print(f"Current Records:  {res.current_record_count}")
    print(f"Counts by Type:   {res.counts_by_type}")
    print(f"Field Changes:    {res.field_change_counts}")
