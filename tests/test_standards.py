"""
Unit tests for Milestone 1: BIS Standards Data Model, Relationship Graph, Search Engine & Evidence Layer.
"""

import unittest
import os
import shutil
from src.standards import StandardsDatabase
from src.search import StandardsSearchEngine
from src.evidence import EvidenceVerifier


class TestBISStandardsPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "data/standards/test_standards.db"
        cls.db = StandardsDatabase(cls.test_db_path)
        cls.v_count = cls.db.load_verified_json("data/standards/verified_standards.json")
        cls.c_count = cls.db.load_curated_excel("data/standards/standards.xlsx")
        cls.engine = StandardsSearchEngine(cls.db)
        cls.verifier = EvidenceVerifier(cls.db)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)

    def test_01_ingestion_and_provenance(self):
        """Verify that 8 verified standards and curated standards are ingested with distinct provenance."""
        self.assertEqual(self.v_count, 8, "Expected exactly 8 verified records.")
        self.assertGreater(self.c_count, 40, "Expected curated standards from Excel.")

        # Test IS 778 provenance
        std_778 = self.db.get_standard("IS-778-1984")
        self.assertIsNotNone(std_778)
        self.assertEqual(std_778["verification_status"], "VERIFIED")
        self.assertEqual(std_778["source"], "BSB_EDGE_MANUALLY_VERIFIED")
        self.assertIn("standardsbis.bsbedge.com", std_778["source_url"])
        self.assertEqual(std_778["technical_committee"], "CED 3")
        self.assertEqual(std_778["reaffirmed_year"], 2020)

    def test_02_explicit_relationships_only(self):
        """Verify that only relationships supported by source evidence exist."""
        # 1. IS 15000:2024 -> REFERENCES -> IS 2491:2024
        rels_15000 = self.db.get_relationships("IS-15000-2024")
        self.assertTrue(any(r["relationship_type"] == "REFERENCES" and "IS 2491" in r["target_standard"] for r in rels_15000))

        # 2. IS/ISO 10434:2020 -> SUPERSEDES -> IS 10611:1983
        rels_10434 = self.db.get_relationships("IS-ISO-10434-2020")
        self.assertTrue(any(r["relationship_type"] == "SUPERSEDES" and "IS 10611" in r["target_standard"] for r in rels_10434))

        # 3. IS 783:1985 -> CODE_OF_PRACTICE_FOR -> IS 458
        rels_783 = self.db.get_relationships("IS-783-1985")
        self.assertTrue(any(r["relationship_type"] == "CODE_OF_PRACTICE_FOR" and "IS 458" in r["target_standard"] for r in rels_783))

    def test_03_query_is15000(self):
        """Query 'IS 15000' must return Active 2024 HACCP standard with cited IS 2491."""
        results = self.engine.search("IS 15000", top_k=1)
        self.assertTrue(len(results) > 0)
        res = results[0]
        self.assertEqual(res.standard_number, "IS 15000")
        self.assertEqual(res.year, 2024)
        self.assertEqual(res.status, "Active")
        self.assertEqual(res.version_role, "CURRENT_ACTIVE")
        self.assertIn("IS 2491 (2024)", res.referenced_standards)

    def test_04_query_food_hygiene(self):
        """Query 'food hygiene' must return IS 2491 : 2024 with FAD 15 committee."""
        results = self.engine.search("food hygiene", top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].standard_number, "IS 2491")
        self.assertEqual(results[0].year, 2024)
        self.assertIn("food hygiene", results[0].full_title.lower())

    def test_05_query_polyethylene_pipes(self):
        """Query 'requirements for polyethylene pipes' must return IS 14333 : 2022."""
        results = self.engine.search("requirements for polyethylene pipes", top_k=1)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].standard_number, "IS 14333")
        self.assertEqual(results[0].year, 2022)
        self.assertIn("polyethylene pipes", results[0].scope_summary.lower())

    def test_06_query_laying_concrete_pipes(self):
        """Query 'standard for laying concrete pipes' must return IS 783 : 1985."""
        results = self.engine.search("standard for laying concrete pipes", top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].standard_number, "IS 783")
        self.assertEqual(results[0].year, 1985)
        self.assertIn("laying of concrete pipes", results[0].full_title.lower())

    def test_07_supersession_query(self):
        """Querying superseded standard 'IS 10611' must return IS/ISO 10434 as authoritative replacement."""
        results = self.engine.search("IS 10611", top_k=1)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].standard_number, "IS/ISO 10434")
        self.assertIn("supersedes IS 10611", results[0].relevance_reason)

    def test_08_evidence_grounding_constraint(self):
        """Test that factual claims map to evidence, and missing evidence returns the required fallback."""
        # Grounded claim
        claim = self.verifier.verify_claim("copper alloy gate globe check valves waterworks", "IS-778-1984", "Scope")
        self.assertTrue(claim.is_grounded)
        self.assertEqual(claim.evidence_type, "VERIFIED_PORTAL_VIEWER")
        self.assertIn("copper alloy gate", claim.source_text.lower())

        # Ungrounded / missing standard claim
        missing = self.verifier.verify_claim("non-existent standard requirement", "NON-EXISTENT-9999", "Scope")
        self.assertFalse(missing.is_grounded)
        self.assertEqual(missing.source_text, "Insufficient evidence from the retrieved BIS standard.")


if __name__ == "__main__":
    unittest.main()
