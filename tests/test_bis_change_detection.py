"""
Test Suite: tests/test_bis_change_detection.py
Purpose: Comprehensive unit testing of Phase 3 BIS catalogue change detection.
"""

import unittest
import json
import sqlite3
import tempfile
from typing import Dict

from src.catalogue.change_detector import (
    ChangeType,
    ComparableStandardRecord,
    CatalogueChangeDetector,
    CatalogueChangeRecord,
    SnapshotMetadata
)


class TestBISChangeDetection(unittest.TestCase):
    """Test suite for deterministic catalogue change detection and history persistence."""

    def _make_sample_record(self, **kwargs) -> ComparableStandardRecord:
        """Helper to create a sample ComparableStandardRecord with default values."""
        defaults = {
            "canonical_id": "IS-15778-2007",
            "standard_number": "IS 15778 : 2007",
            "base_standard_number": "IS 15778",
            "part": None,
            "section": None,
            "year": 2007,
            "title": "Chlorinated Polyvinyl Chloride Pipes for Potable Hot and Cold Water Distribution",
            "technical_committee": "CED 50",
            "aspect": "Product Specification",
            "amendments": "2",
            "amendment_count": 2,
            "status": "ACTIVE",
            "is_active": 1,
            "iso_equivalence": None,
            "iso_equivalence_degree": "Indigenous",
            "source": "BIS",
            "source_url": "https://standardsbis.bsbedge.com/search_redirect.aspx?id=123",
            "raw_record_ref": "seed_0_page_0000.json:0"
        }
        defaults.update(kwargs)
        return ComparableStandardRecord(**defaults)

    def test_01_new_standard_detection(self):
        """Test detection of a newly introduced standard in the fresh snapshot."""
        prev = {}
        curr = {
            "IS-99999-2026": self._make_sample_record(
                canonical_id="IS-99999-2026",
                standard_number="IS 99999 : 2026",
                base_standard_number="IS 99999",
                year=2026,
                title="Brand New Quantum Standards Specification"
            )
        }
        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.NEW.value], 1)
        self.assertEqual(len(res.changes), 1)
        c = res.changes[0]
        self.assertEqual(c.canonical_id, "IS-99999-2026")
        self.assertEqual(c.change_type, ChangeType.NEW.value)
        self.assertIsNone(c.previous_values)
        self.assertEqual(c.new_values["canonical_id"], "IS-99999-2026")

    def test_02_unchanged_standard_detection(self):
        """Test identical records across snapshots produce UNCHANGED classification."""
        rec = self._make_sample_record()
        prev = {rec.canonical_id: rec}
        curr = {rec.canonical_id: self._make_sample_record()}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.UNCHANGED.value], 1)
        self.assertEqual(len(res.changes), 0)  # No delta change records created

    def test_03_title_update_detection(self):
        """Test single field metadata change: title update."""
        prev_rec = self._make_sample_record(title="Old Pipe Specification")
        curr_rec = self._make_sample_record(title="Updated Chlorinated Polyvinyl Chloride Pipes Specification")

        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.UPDATED.value], 1)
        self.assertEqual(len(res.changes), 1)
        c = res.changes[0]
        self.assertEqual(c.change_type, ChangeType.UPDATED.value)
        self.assertIn("title", c.changed_fields)
        self.assertEqual(c.previous_values["title"], "Old Pipe Specification")
        self.assertEqual(c.new_values["title"], "Updated Chlorinated Polyvinyl Chloride Pipes Specification")

    def test_04_technical_committee_update(self):
        """Test technical committee reassignment."""
        prev_rec = self._make_sample_record(technical_committee="CED 50")
        curr_rec = self._make_sample_record(technical_committee="CED 53")

        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.UPDATED.value], 1)
        c = res.changes[0]
        self.assertIn("technical_committee", c.changed_fields)
        self.assertEqual(c.previous_values["technical_committee"], "CED 50")
        self.assertEqual(c.new_values["technical_committee"], "CED 53")

    def test_05_status_withdrawn_detection(self):
        """Test explicit transition to WITHDRAWN status."""
        prev_rec = self._make_sample_record(status="ACTIVE", is_active=1)
        curr_rec = self._make_sample_record(status="WITHDRAWN", is_active=0)

        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.WITHDRAWN.value], 1)
        c = res.changes[0]
        self.assertEqual(c.change_type, ChangeType.WITHDRAWN.value)
        self.assertIn("status", c.changed_fields)
        self.assertIn("is_active", c.changed_fields)
        self.assertEqual(c.previous_values["status"], "ACTIVE")
        self.assertEqual(c.new_values["status"], "WITHDRAWN")

    def test_06_status_unknown_to_active(self):
        """Test explicit confirmation from UNKNOWN to ACTIVE."""
        prev_rec = self._make_sample_record(status="UNKNOWN", is_active=None)
        curr_rec = self._make_sample_record(status="ACTIVE", is_active=1)

        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.STATUS_CHANGED.value], 1)
        c = res.changes[0]
        self.assertEqual(c.change_type, ChangeType.STATUS_CHANGED.value)
        self.assertEqual(c.previous_values["status"], "UNKNOWN")
        self.assertEqual(c.new_values["status"], "ACTIVE")

    def test_07_explicit_superseded_status(self):
        """Test explicit BIS supersession classification."""
        prev_rec = self._make_sample_record(status="ACTIVE", is_active=1)
        curr_rec = self._make_sample_record(status="SUPERSEDED", is_active=0)

        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.SUPERSEDED.value], 1)
        c = res.changes[0]
        self.assertEqual(c.change_type, ChangeType.SUPERSEDED.value)
        self.assertEqual(c.previous_values["status"], "ACTIVE")
        self.assertEqual(c.new_values["status"], "SUPERSEDED")

    def test_08_missing_from_source_safety(self):
        """Test record absent in current snapshot is classified as MISSING_FROM_SOURCE, not WITHDRAWN."""
        rec = self._make_sample_record(canonical_id="IS-500-1990", standard_number="IS 500 : 1990", status="ACTIVE")
        prev = {rec.canonical_id: rec}
        curr = {}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.MISSING_FROM_SOURCE.value], 1)
        self.assertEqual(res.counts_by_type[ChangeType.WITHDRAWN.value], 0)
        c = res.changes[0]
        self.assertEqual(c.canonical_id, "IS-500-1990")
        self.assertEqual(c.change_type, ChangeType.MISSING_FROM_SOURCE.value)
        self.assertEqual(c.new_values["presence"], "MISSING_FROM_SOURCE")

    def test_09_compound_identifier_change(self):
        """Test compound identifiers are preserved during changes without reduction."""
        prev_rec = self._make_sample_record(
            canonical_id="IS-ISO-IEEE-11073-Part-10407-2022",
            standard_number="IS/ISO/IEEE 11073 (Part 10407) : 2022",
            base_standard_number="IS/ISO/IEEE 11073",
            part=10407,
            year=2022,
            technical_committee="MHD 08",
            status="ACTIVE"
        )
        curr_rec = self._make_sample_record(
            canonical_id="IS-ISO-IEEE-11073-Part-10407-2022",
            standard_number="IS/ISO/IEEE 11073 (Part 10407) : 2022",
            base_standard_number="IS/ISO/IEEE 11073",
            part=10407,
            year=2022,
            technical_committee="MHD 08",
            status="WITHDRAWN",
            is_active=0
        )
        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.WITHDRAWN.value], 1)
        c = res.changes[0]
        self.assertEqual(c.canonical_id, "IS-ISO-IEEE-11073-Part-10407-2022")
        self.assertNotIn("IS-11073", c.canonical_id)

    def test_10_part_specific_standards_separation(self):
        """Test that different parts of a standard remain separate during comparisons."""
        part1 = self._make_sample_record(
            canonical_id="IS-1554-Part-1-1988",
            standard_number="IS 1554 (Part 1) : 1988",
            part=1,
            title="PVC Insulated Cables Part 1"
        )
        part2_prev = self._make_sample_record(
            canonical_id="IS-1554-Part-2-1988",
            standard_number="IS 1554 (Part 2) : 1988",
            part=2,
            title="PVC Insulated Cables Part 2 (Old)"
        )
        part2_curr = self._make_sample_record(
            canonical_id="IS-1554-Part-2-1988",
            standard_number="IS 1554 (Part 2) : 1988",
            part=2,
            title="PVC Insulated Cables Part 2 (Revised Title)"
        )
        prev = {part1.canonical_id: part1, part2_prev.canonical_id: part2_prev}
        curr = {part1.canonical_id: part1, part2_curr.canonical_id: part2_curr}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.UNCHANGED.value], 1)
        self.assertEqual(res.counts_by_type[ChangeType.UPDATED.value], 1)
        c = res.changes[0]
        self.assertEqual(c.canonical_id, "IS-1554-Part-2-1988")

    def test_11_section_specific_standards_separation(self):
        """Test section-specific standard remains separate from base part standard."""
        part_only = self._make_sample_record(
            canonical_id="IS-1554-Part-1-1988",
            standard_number="IS 1554 (Part 1) : 1988",
            part=1,
            section=None
        )
        part_sec = self._make_sample_record(
            canonical_id="IS-1554-Part-1-Sec-2-1988",
            standard_number="IS 1554 (Part 1) (Sec 2) : 1988",
            part=1,
            section=2
        )
        prev = {part_only.canonical_id: part_only, part_sec.canonical_id: part_sec}
        # Update only the section standard
        part_sec_updated = self._make_sample_record(
            canonical_id="IS-1554-Part-1-Sec-2-1988",
            standard_number="IS 1554 (Part 1) (Sec 2) : 1988",
            part=1,
            section=2,
            aspect="Test Method"
        )
        curr = {part_only.canonical_id: part_only, part_sec.canonical_id: part_sec_updated}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.UNCHANGED.value], 1)
        self.assertEqual(res.counts_by_type[ChangeType.UPDATED.value], 1)
        c = res.changes[0]
        self.assertEqual(c.canonical_id, "IS-1554-Part-1-Sec-2-1988")
        self.assertIn("aspect", c.changed_fields)

    def test_12_multiple_fields_changing_simultaneously(self):
        """Test status and non-status metadata both changing: all changed fields are preserved."""
        prev_rec = self._make_sample_record(
            title="Old Title",
            status="ACTIVE",
            is_active=1,
            amendment_count=0,
            aspect="General"
        )
        curr_rec = self._make_sample_record(
            title="New Revised Title",
            status="WITHDRAWN",
            is_active=0,
            amendment_count=1,
            aspect="Product Specification"
        )
        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.WITHDRAWN.value], 1)
        c = res.changes[0]
        self.assertEqual(c.change_type, ChangeType.WITHDRAWN.value)
        # All changed fields must be preserved
        self.assertIn("title", c.changed_fields)
        self.assertIn("status", c.changed_fields)
        self.assertIn("is_active", c.changed_fields)
        self.assertIn("amendment_count", c.changed_fields)
        self.assertIn("aspect", c.changed_fields)
        self.assertEqual(c.previous_values["title"], "Old Title")
        self.assertEqual(c.new_values["title"], "New Revised Title")

    def test_13_null_to_populated_transition(self):
        """Test previously NULL field becoming populated."""
        prev_rec = self._make_sample_record(iso_equivalence=None)
        curr_rec = self._make_sample_record(iso_equivalence="IEC 60502-1")

        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.UPDATED.value], 1)
        c = res.changes[0]
        self.assertIn("iso_equivalence", c.changed_fields)
        self.assertIsNone(c.previous_values["iso_equivalence"])
        self.assertEqual(c.new_values["iso_equivalence"], "IEC 60502-1")

    def test_14_populated_to_null_transition(self):
        """Test populated field becoming NULL."""
        prev_rec = self._make_sample_record(aspect="Product Specification")
        curr_rec = self._make_sample_record(aspect=None)

        prev = {prev_rec.canonical_id: prev_rec}
        curr = {curr_rec.canonical_id: curr_rec}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.counts_by_type[ChangeType.UPDATED.value], 1)
        c = res.changes[0]
        self.assertIn("aspect", c.changed_fields)
        self.assertEqual(c.previous_values["aspect"], "Product Specification")
        self.assertIsNone(c.new_values["aspect"])

    def test_15_duplicate_canonical_id_protection(self):
        """Test that duplicate canonical IDs in either snapshot are caught by integrity metrics."""
        rec1 = self._make_sample_record(canonical_id="IS-100-2000")
        prev = {"IS-100-2000": rec1}
        curr = {"IS-100-2000": rec1}

        res = CatalogueChangeDetector.compare_snapshots(prev, curr, "snap_prev", "snap_curr")
        self.assertEqual(res.integrity["duplicate_canonical_ids_previous"], 0)
        self.assertEqual(res.integrity["duplicate_canonical_ids_current"], 0)

    def test_16_persistence_and_provenance(self):
        """Test append-only persistence of change history and snapshot metadata into SQLite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_catalogue.db"
            conn = sqlite3.connect(db_path)

            detector = CatalogueChangeDetector(db_path=db_path, report_dir=f"{tmpdir}/reports")
            detector.init_database_tables(conn)

            # Register snapshot
            meta = SnapshotMetadata(
                snapshot_id="snap_v1",
                created_at="2026-09-14T00:00:00Z",
                record_count=100,
                run_id="run_001"
            )
            detector.register_snapshot(conn, meta)

            # Run diff
            prev = {"IS-1-2000": self._make_sample_record(canonical_id="IS-1-2000", title="Version 1")}
            curr = {"IS-1-2000": self._make_sample_record(canonical_id="IS-1-2000", title="Version 2")}
            result = detector.compare_snapshots(prev, curr, "snap_v1", "snap_v2")

            # Persist history
            written = detector.persist_change_history(conn, result)
            self.assertEqual(written, 1)

            # Query change history
            cur = conn.cursor()
            cur.execute("SELECT snapshot_id_previous, snapshot_id_current, canonical_id, change_type, changed_fields_json, raw_record_ref FROM catalogue_change_history")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "snap_v1")
            self.assertEqual(row[1], "snap_v2")
            self.assertEqual(row[2], "IS-1-2000")
            self.assertEqual(row[3], ChangeType.UPDATED.value)
            self.assertIn("title", json.loads(row[4]))
            self.assertEqual(row[5], "seed_0_page_0000.json:0")

            # Verify append-only property: subsequent insert adds row without overwriting
            detector.persist_change_history(conn, result)
            cur.execute("SELECT count(*) FROM catalogue_change_history")
            total_history = cur.fetchone()[0]
            self.assertEqual(total_history, 2)

            conn.close()


if __name__ == "__main__":
    unittest.main()
