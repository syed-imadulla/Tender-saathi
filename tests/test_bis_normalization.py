"""
Test Suite: tests/test_bis_normalization.py
Purpose: Phase 2 BIS Normalization, Validation, Deduplication, and Database Tests.
"""

import unittest
import os
import json
import sqlite3
import tempfile
from unittest.mock import patch

from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier
from src.catalogue.bis_normalizer import BISCatalogueNormalizer, ValidationCategory


class TestBISNormalization(unittest.TestCase):
    """Unit tests for Phase 2 BIS identifier normalization and classification."""

    def test_01_simple_is_standards(self):
        """Test simple IS numbers with year and base."""
        res = StandardIdentifierNormalizer.parse("IS 15778:2007")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.prefix, "IS")
        self.assertEqual(res.base_number, "15778")
        self.assertEqual(res.year, 2007)
        self.assertEqual(res.canonical_id, "IS-15778-2007")

        res2 = StandardIdentifierNormalizer.parse("IS 1239:2004")
        self.assertTrue(res2.is_valid)
        self.assertEqual(res2.prefix, "IS")
        self.assertEqual(res2.base_number, "1239")
        self.assertEqual(res2.year, 2004)
        self.assertEqual(res2.canonical_id, "IS-1239-2004")

    def test_02_parts_and_sections_preservation(self):
        """Test parts and sections are preserved without collision."""
        part1 = StandardIdentifierNormalizer.parse("IS 1554 (Part 1):1988")
        self.assertTrue(part1.is_valid)
        self.assertEqual(part1.prefix, "IS")
        self.assertEqual(part1.base_number, "1554")
        self.assertEqual(part1.part, 1)
        self.assertIsNone(part1.section)
        self.assertEqual(part1.year, 1988)
        self.assertEqual(part1.canonical_id, "IS-1554-Part-1-1988")

        part2 = StandardIdentifierNormalizer.parse("IS 1554 (Part 2):1988")
        self.assertTrue(part2.is_valid)
        self.assertEqual(part2.part, 2)
        self.assertEqual(part2.canonical_id, "IS-1554-Part-2-1988")

        # Crucial: Part 1 and Part 2 must NOT have identical canonical IDs
        self.assertNotEqual(part1.canonical_id, part2.canonical_id)

        # Combined Part and Section
        part_sec = StandardIdentifierNormalizer.parse("IS 1554 (Part 1/Sec 2):1988")
        self.assertTrue(part_sec.is_valid)
        self.assertEqual(part_sec.part, 1)
        self.assertEqual(part_sec.section, 2)
        self.assertEqual(part_sec.canonical_id, "IS-1554-Part-1-Sec-2-1988")
        self.assertNotEqual(part_sec.canonical_id, part1.canonical_id)

    def test_03_compound_qualifiers(self):
        """Test all compound BIS qualifiers are correctly parsed."""
        cases = [
            ("IS/ISO 9001:2015", "IS/ISO", "9001", None, None, 2015, "IS-ISO-9001-2015"),
            ("IS/IEC 60502:2020", "IS/IEC", "60502", None, None, 2020, "IS-IEC-60502-2020"),
            ("IS/ISO/TR 10013:2001", "IS/ISO/TR", "10013", None, None, 2001, "IS-ISO-TR-10013-2001"),
            ("IS/ISO/TS 10020:2022", "IS/ISO/TS", "10020", None, None, 2022, "IS-ISO-TS-10020-2022"),
            ("IS/IEC/TS 10993-19:2006", "IS/IEC/TS", "10993", 19, None, 2006, "IS-IEC-TS-10993-Part-19-2006"),
            ("IS/CISPR 16-1-1:2015", "IS/CISPR", "16", 1, 1, 2015, "IS-CISPR-16-Part-1-Sec-1-2015"),
            ("IS/QC 001002:1998", "IS/QC", "001002", None, None, 1998, "IS-QC-001002-1998"),
            ("SP 7:2016", "SP", "7", None, None, 2016, "SP-7-2016"),
            ("IS B 1234:2000", "IS B", "1234", None, None, 2000, "IS-B-1234-2000"),
        ]
        for raw, expected_prefix, expected_base, exp_part, exp_sec, exp_year, expected_cid in cases:
            res = StandardIdentifierNormalizer.parse(raw)
            self.assertTrue(res.is_valid, f"Failed to parse valid standard {raw}")
            self.assertEqual(res.prefix, expected_prefix)
            self.assertEqual(res.base_number, expected_base)
            self.assertEqual(res.part, exp_part)
            self.assertEqual(res.section, exp_sec)
            self.assertEqual(res.year, exp_year)
            self.assertEqual(res.canonical_id, expected_cid)

    def test_04_anti_reduction_guardrail(self):
        """Test IS/ISO/IEEE 11073-10407:2022 is NOT reduced to IS 11073:2022."""
        compound = StandardIdentifierNormalizer.parse("IS/ISO/IEEE 11073-10407:2022")
        indigenous = StandardIdentifierNormalizer.parse("IS 11073:1984")

        self.assertTrue(compound.is_valid)
        self.assertTrue(indigenous.is_valid)

        self.assertEqual(compound.prefix, "IS/ISO/IEEE")
        self.assertEqual(compound.base_number, "11073")
        self.assertEqual(compound.part, 10407)
        self.assertEqual(compound.year, 2022)
        self.assertEqual(compound.canonical_id, "IS-ISO-IEEE-11073-Part-10407-2022")

        self.assertEqual(indigenous.prefix, "IS")
        self.assertEqual(indigenous.base_number, "11073")
        self.assertIsNone(indigenous.part)
        self.assertEqual(indigenous.year, 1984)
        self.assertEqual(indigenous.canonical_id, "IS-11073-1984")

        # Must never collide
        self.assertNotEqual(compound.canonical_id, indigenous.canonical_id)
        self.assertNotIn("IS 11073", compound.canonical_number)

    def test_05_malformed_records_quarantine(self):
        """Test malformed BIS records missing numbers or bases are marked invalid without guessing."""
        malformed_inputs = [
            "IS/IEC :2023",
            "IS/ISO :2012",
            "IS/ISO -4:2008",
            "IS/ISO/IEC -1:2008",
            "IS (Part 1/Sec 1):1975",
            "IS ISO:2024",
            "IS/IEC TS TS:2016",
        ]
        for m in malformed_inputs:
            res = StandardIdentifierNormalizer.parse(m)
            self.assertFalse(res.is_valid, f"Expected {m} to be invalid/malformed, but was accepted!")
            self.assertEqual(res.canonical_id, "UNKNOWN")

    def test_06_recoverable_identifiers(self):
        """Test recoverable identifiers with unambiguous digits or accent typos."""
        # Bare digits
        r1 = StandardIdentifierNormalizer.parse("16324 16324:2014")
        self.assertTrue(r1.is_valid)
        self.assertEqual(r1.canonical_id, "IS-16324-2014")

        r2 = StandardIdentifierNormalizer.parse("13360:2025")
        self.assertTrue(r2.is_valid)
        self.assertEqual(r2.canonical_id, "IS-13360-2025")

        # Diacritic typo
        r3 = StandardIdentifierNormalizer.parse("ÍS 15381:2021")
        self.assertTrue(r3.is_valid)
        self.assertEqual(r3.prefix, "IS")
        self.assertEqual(r3.canonical_id, "IS-15381-2021")

    def test_07_status_normalization_and_preservation(self):
        """Test status determination preserves withdrawn standards and distinguishes active vs unknown."""
        # Explicit withdrawn status
        st_w, act_w = BISCatalogueNormalizer.determine_status({"withdrawn_status": "W", "is_no": "IS 100:1980"})
        self.assertEqual(st_w, "WITHDRAWN")
        self.assertEqual(act_w, 0)

        # Title/segment withdrawn
        st_tw, act_tw = BISCatalogueNormalizer.determine_status({
            "withdrawn_status": None,
            "is_no": "IS 100:1980<br>ISO 100<br> (Withdrawn )"
        })
        self.assertEqual(st_tw, "WITHDRAWN")
        self.assertEqual(act_tw, 0)

        # Active
        st_a, act_a = BISCatalogueNormalizer.determine_status({
            "withdrawn_status": None,
            "is_no": "IS 15778:2007<br><br> (Active)"
        })
        self.assertEqual(st_a, "ACTIVE")
        self.assertEqual(act_a, 1)

        # Unknown (neither active nor withdrawn)
        st_u, act_u = BISCatalogueNormalizer.determine_status({
            "withdrawn_status": None,
            "is_no": "IS 15778:2007<br><br>"
        })
        self.assertEqual(st_u, "UNKNOWN")
        self.assertIsNone(act_u)

    def test_08_field_mappings(self):
        """Test department and equivalence degree extraction."""
        dept = BISCatalogueNormalizer.extract_department("CED 50")
        self.assertEqual(dept, "CED")

        dept_etd = BISCatalogueNormalizer.extract_department("ETD  09")
        self.assertEqual(dept_etd, "ETD")

        self.assertIsNone(BISCatalogueNormalizer.extract_department(None))
        self.assertIsNone(BISCatalogueNormalizer.extract_department(""))

        # ISO Equivalence
        eq = BISCatalogueNormalizer.extract_iso_equivalence("IS 1554 (Part 1):1988<br>IEC 60502<br> (Active)")
        self.assertEqual(eq, "IEC 60502")

        eq_none = BISCatalogueNormalizer.extract_iso_equivalence("IS 15778:2007<br>Identical<br> (Active)")
        self.assertIsNone(eq_none)

    def test_09_database_isolation_and_persistence(self):
        """Test database persistence in an isolated database file with provenance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock raw data directory
            run_dir = os.path.join(tmpdir, "run_test")
            pages_dir = os.path.join(run_dir, "pages")
            os.makedirs(pages_dir, exist_ok=True)

            mock_page_0 = {
                "aaData": [
                    {
                        "is_no": "IS 15778:2007<br><br> (Active)",
                        "is_title": "Chlorinated Polyvinyl Chloride Pipes",
                        "technical_committee": "CED 50",
                        "aspect": "Product Specification",
                        "referirmatin_year": "Indigenous",
                        "amendments": "2",
                        "withdrawn_status": None,
                        "DownloadAction": "<a href='https://standardsbis.bsbedge.com/search_redirect.aspx?id=123'>Download</a>"
                    },
                    {
                        "is_no": "IS/ISO -4:2008<br><br>",
                        "is_title": "Malformed Earth-moving Machinery",
                        "technical_committee": "MED 07",
                        "aspect": "Specification",
                        "referirmatin_year": "Indigenous",
                        "amendments": "0",
                        "withdrawn_status": None
                    },
                    {
                        "is_no": "SI B2410:2011<br><br>",
                        "is_title": "Standards India Vol 24 No 10",
                        "technical_committee": "SSD 01",
                        "aspect": "General",
                        "referirmatin_year": "Indigenous",
                        "amendments": "0",
                        "withdrawn_status": None
                    }
                ]
            }
            # Page 1 has duplicate of IS 15778 under a different seed
            mock_page_1 = {
                "aaData": [
                    {
                        "is_no": "IS 15778:2007<br><br> (Active)",
                        "is_title": "Chlorinated Polyvinyl Chloride Pipes",
                        "technical_committee": "CED 50",
                        "aspect": "Product Specification",
                        "referirmatin_year": "Indigenous",
                        "amendments": "2",
                        "withdrawn_status": None
                    }
                ]
            }

            with open(os.path.join(pages_dir, "seed_0_page_0000.json"), "w") as f:
                json.dump(mock_page_0, f)
            with open(os.path.join(pages_dir, "seed_1_page_0000.json"), "w") as f:
                json.dump(mock_page_1, f)

            output_db = os.path.join(tmpdir, "test_catalogue.db")
            normalizer = BISCatalogueNormalizer(
                input_dir=run_dir,
                output_db_path=output_db,
                report_dir=os.path.join(tmpdir, "reports")
            )
            summary = normalizer.process()

            self.assertEqual(summary["total_raw_rows_processed"], 4)
            self.assertEqual(summary["unique_canonical_standards"], 1)
            self.assertEqual(summary["duplicate_row_instances"], 1)
            self.assertEqual(summary["quarantined_row_instances"], 2)

            # Query database
            conn = sqlite3.connect(output_db)
            cur = conn.cursor()

            # Check catalogue_standards
            cur.execute("SELECT canonical_id, standard_number, status, is_active, department, iso_equivalence_degree, times_observed, seeds_observed_json FROM catalogue_standards")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "IS-15778-2007")
            self.assertEqual(row[1], "IS 15778 : 2007")
            self.assertEqual(row[2], "ACTIVE")
            self.assertEqual(row[3], 1)
            self.assertEqual(row[4], "CED")
            self.assertEqual(row[5], "Indigenous")
            self.assertEqual(row[6], 2)  # Observed twice across seeds 0 and 1
            seeds = json.loads(row[7])
            self.assertIn("0", seeds)
            self.assertIn("1", seeds)

            # Check quarantine_records
            cur.execute("SELECT raw_identifier, validation_category, reason FROM quarantine_records ORDER BY id")
            q_rows = cur.fetchall()
            self.assertEqual(len(q_rows), 2)
            self.assertEqual(q_rows[0][0], "IS/ISO -4:2008")
            self.assertEqual(q_rows[0][1], ValidationCategory.MALFORMED_SOURCE)
            self.assertEqual(q_rows[1][0], "SI B2410:2011")
            self.assertEqual(q_rows[1][1], ValidationCategory.UNSUPPORTED_FORMAT)

            conn.close()


if __name__ == "__main__":
    unittest.main()
