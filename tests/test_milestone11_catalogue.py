"""
Module: tests/test_milestone11_catalogue.py
Purpose: Unit tests for Milestone 11 - Priority 3 Catalogue Pipeline.

Covers:
- Canonical standard identifier normalization
- Duplicate detection & deduplication
- Provenance preservation hierarchy
- Lifecycle preservation (ACTIVE, SUPERSEDED, WITHDRAWN, etc.)
- Amendment preservation
- Snapshot & manifest generation
- Incremental update tracking
- Explicit UNKNOWN fields representation
- Unsupported source rejection
- Copyright safety guardrail
"""

import unittest
import os
import json
import tempfile
import shutil

from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.catalogue.provenance import (
    ProvenanceLevel,
    CatalogueSourceInfo,
    assert_no_inferred_as_authoritative,
)
from src.catalogue.validator import (
    StandardMasterRecord,
    CatalogueValidator,
    LifecycleStatus,
)
from src.catalogue.snapshot import CatalogueSnapshotManager
from src.catalogue.manifest import IngestionManifest
from src.catalogue.loader import CatalogueLoader, IngestionMode


class TestMilestone11Catalogue(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_catalogue.db")
        self.norm_dir = os.path.join(self.temp_dir, "normalized")
        self.snap_dir = os.path.join(self.temp_dir, "snapshots")
        self.man_dir = os.path.join(self.temp_dir, "manifests")
        self.loader = CatalogueLoader(
            db_path=self.db_path,
            normalized_dir=self.norm_dir,
            snapshots_dir=self.snap_dir,
            manifests_dir=self.man_dir
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_canonical_normalization(self):
        """Test that different formatting variations resolve to identical canonical representation."""
        variations = [
            "IS 15778 : 2007",
            "IS 15778:2007",
            "IS 15778-2007",
            "is 15778 : 2007",
            "IS  15778 :  2007"
        ]
        parsed = [StandardIdentifierNormalizer.parse(v) for v in variations]
        first = parsed[0]

        for p in parsed[1:]:
            self.assertEqual(p.canonical_id, first.canonical_id)
            self.assertEqual(p.canonical_number, first.canonical_number)
            self.assertEqual(p.base_number, "15778")
            self.assertEqual(p.year, 2007)

    def test_02_preservation_of_parts_sections_amendments(self):
        """Test that technical distinctions (Part, Section, Amd, IEC) are preserved and not stripped."""
        parsed_part = StandardIdentifierNormalizer.parse("IS 7098 (Part 1) : 1988")
        self.assertEqual(parsed_part.part, 1)
        self.assertEqual(parsed_part.canonical_id, "IS-7098-Part-1-1988")
        self.assertEqual(parsed_part.canonical_number, "IS 7098 (Part 1) : 1988")

        parsed_iec = StandardIdentifierNormalizer.parse("IS/IEC 61439-3 : 2012")
        self.assertEqual(parsed_iec.prefix, "IS/IEC")
        self.assertEqual(parsed_iec.part, 3)
        self.assertEqual(parsed_iec.canonical_id, "IS-IEC-61439-Part-3-2012")

        parsed_sec = StandardIdentifierNormalizer.parse("IS 10322 (Part 5 / Sec 5) : 2013")
        self.assertEqual(parsed_sec.part, 5)
        self.assertEqual(parsed_sec.section, 5)

        # Amendment preservation
        parsed_amd = StandardIdentifierNormalizer.parse("IS 1239 (Part 1) : 2004 Amd 1")
        self.assertEqual(parsed_amd.amendment, 1)

    def test_03_deduplication_without_collapsing_distinct_standards(self):
        """Test deduplication merges identical standards but preserves distinct parts/standards."""
        self.assertTrue(StandardIdentifierNormalizer.are_equivalent("IS 15778:2007", "IS 15778 : 2007"))
        # Different parts are NOT equivalent
        self.assertFalse(StandardIdentifierNormalizer.are_equivalent("IS 7098 (Part 1) : 1988", "IS 7098 (Part 2) : 2011"))
        # Different standards are NOT equivalent even if titles or numbers look similar
        self.assertFalse(StandardIdentifierNormalizer.are_equivalent("IS 1239 (Part 1)", "IS 1239 (Part 2)"))
        self.assertFalse(StandardIdentifierNormalizer.are_equivalent("IS 4984", "IS 4985"))

    def test_04_provenance_preservation(self):
        """Test strict provenance tracking and non-authoritative INFERRED assertion."""
        primary_src = CatalogueSourceInfo(
            source_type="BIS_OFFICIAL_PORTAL",
            provenance=ProvenanceLevel.OFFICIAL_PRIMARY.value
        )
        self.assertEqual(primary_src.validate(), [])

        inferred_src = CatalogueSourceInfo(
            source_type="OFFLINE_EXPORT_AUTHORITATIVE",
            provenance=ProvenanceLevel.INFERRED.value,
            confidence=0.5
        )
        self.assertEqual(inferred_src.validate(), [])

        # Inferred data must never be presented as authoritative fact
        with self.assertRaises(ValueError):
            assert_no_inferred_as_authoritative(ProvenanceLevel.INFERRED.value, "Testing regulatory obligation")

    def test_05_lifecycle_preservation(self):
        """Test lifecycle states are normalized accurately without guessing."""
        self.assertEqual(LifecycleStatus.normalize("Active"), "ACTIVE")
        self.assertEqual(LifecycleStatus.normalize("Superseded by IS 15622"), "SUPERSEDED")
        self.assertEqual(LifecycleStatus.normalize("Withdrawn"), "WITHDRAWN")
        self.assertEqual(LifecycleStatus.normalize("Under Review"), "UNDER_REVIEW")
        self.assertEqual(LifecycleStatus.normalize(None), "UNKNOWN")
        self.assertEqual(LifecycleStatus.normalize(""), "UNKNOWN")

    def test_06_amendment_preservation(self):
        """Test amendments are stored distinctly and not silently collapsed into base text."""
        record = StandardMasterRecord(
            standard_number="IS 4985 : 2021",
            title="Unplasticized Polyvinyl Chloride (uPVC) Pipes for Potable Water Supplies",
            amendments=[
                {
                    "amendment_number": 1,
                    "amendment_date": "2023-01",
                    "source": "BIS Official Gazette",
                    "provenance": "OFFICIAL_PRIMARY"
                }
            ]
        )
        self.assertEqual(len(record.amendments), 1)
        self.assertEqual(record.amendments[0]["amendment_number"], 1)

    def test_07_snapshot_and_manifest_generation(self):
        """Test snapshot creation and manifest generation tracking record additions and diffs."""
        records_batch_1 = [
            StandardMasterRecord(
                standard_number="IS 15778 : 2007",
                title="CPVC Pipes for Potable Water",
                scope="Legitimate scope summary"
            ),
            StandardMasterRecord(
                standard_number="IS 4985 : 2021",
                title="uPVC Pipes",
                scope="Legitimate scope summary"
            )
        ]

        batch_file_1 = os.path.join(self.temp_dir, "batch_1.json")
        with open(batch_file_1, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in records_batch_1], f)

        manifest_1 = self.loader.load_from_json_file(batch_file_1)
        self.assertEqual(manifest_1.record_count, 2)
        self.assertEqual(manifest_1.new_records, 2)
        self.assertEqual(manifest_1.updated_records, 0)
        self.assertEqual(self.loader.get_standard_count(), 2)

        # Second batch with 1 unchanged, 1 updated, 1 new
        records_batch_2 = [
            StandardMasterRecord(
                standard_number="IS 15778 : 2007",
                title="CPVC Pipes for Potable Water (Updated Title)",
                scope="Legitimate scope summary"
            ),
            StandardMasterRecord(
                standard_number="IS 4985 : 2021",
                title="uPVC Pipes",
                scope="Legitimate scope summary"
            ),
            StandardMasterRecord(
                standard_number="IS 14846 : 2000",
                title="Sluice Valves for Water Works Purposes",
                scope="Legitimate scope summary"
            )
        ]

        batch_file_2 = os.path.join(self.temp_dir, "batch_2.json")
        with open(batch_file_2, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in records_batch_2], f)

        manifest_2 = self.loader.load_from_json_file(batch_file_2)
        self.assertEqual(manifest_2.record_count, 3)
        self.assertEqual(manifest_2.new_records, 1)
        self.assertEqual(manifest_2.updated_records, 1)
        self.assertEqual(manifest_2.unchanged_records, 1)
        self.assertEqual(self.loader.get_standard_count(), 3)

    def test_08_explicit_unknown_fields_not_fabricated(self):
        """Test that missing fields remain UNKNOWN and are never fabricated."""
        rec = StandardMasterRecord(
            standard_number="IS 99999 : 2020",
            title="Hypothetical Standard with Minimal Data"
        )
        self.assertEqual(rec.scope, "UNKNOWN")
        self.assertEqual(rec.reaffirmed_year, None)
        self.assertEqual(rec.amendments, [])

    def test_09_unsupported_source_rejection(self):
        """Test that Wikipedia, blogs, or commercial scrapers are rejected as authoritative sources."""
        bad_src = CatalogueSourceInfo(
            source_type="WIKIPEDIA",
            provenance=ProvenanceLevel.OFFICIAL_PRIMARY.value
        )
        errs = bad_src.validate()
        self.assertTrue(any("disallowed" in e.lower() for e in errs))

    def test_10_copyright_guardrail(self):
        """Test that attempting to dump full standard copyrighted text is rejected."""
        giant_fake_text = "Clause 1.1 Specification details... " * 2000  # > 50,000 chars
        rec = StandardMasterRecord(
            standard_number="IS 15778 : 2007",
            title="CPVC Pipes",
            scope=giant_fake_text
        )
        errs = CatalogueValidator.validate_record(rec)
        self.assertTrue(any("copyrighted" in e.lower() for e in errs))


if __name__ == "__main__":
    unittest.main()
