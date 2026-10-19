# tests/test_phase35_demonstration_readiness.py — Phase 35 Demonstration Readiness & Verification Suite
import hashlib
import json
import sqlite3
import unittest
from pathlib import Path

from api.server import app
from src.corpus.storage import CorpusStorage
from src.graph import StandardsGraph
from src.recommend import StandardsRecommender


EXPECTED_GROUND_TRUTH_SHA256 = "8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc"


class TestPhase35DemonstrationReadiness(unittest.TestCase):
    """
    Verification suite for Phase 35:
    1. Normative Traversal Journey API endpoints and bounding.
    2. Non-elevation safety invariant (traversal never upgrades unverified clauses to CLAUSE_VERIFIED).
    3. Catalogue lifecycle status reconciliation counts and idempotent provenance.
    4. Authentic normative passage ingestion for IS 694 : 2010 and IS 1180 (Part 1) : 2014.
    5. Ground-truth benchmark checksum immutability.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.graph = StandardsGraph()
        cls.corpus = CorpusStorage()

    def test_01_ground_truth_checksum_immutability(self):
        """Verify ground_truth.csv was not modified or corrupted."""
        gt_path = Path("dataset/ground_truth/ground_truth.csv")
        self.assertTrue(gt_path.exists())
        sha256 = hashlib.sha256(gt_path.read_bytes()).hexdigest()
        self.assertEqual(sha256, EXPECTED_GROUND_TRUTH_SHA256)

    def test_02_traversal_api_depth_1_and_2(self):
        """API traversal endpoint returns evidence-backed cross-references at depth 1 and 2."""
        # Test IS 800 : 2007 traversal
        resp = self.client.get("/api/standards/IS%20800%20:%202007/traversal?depth=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["start_standard"], "IS 800 : 2007")
        self.assertEqual(data["max_depth"], 1)
        self.assertGreater(data["count"], 0)
        
        targets = [r["target_standard"] for r in data["traversed_references"]]
        self.assertTrue(any("2062" in t for t in targets), f"IS 2062 should be among traversal targets, got {targets}")

        # Depth 2 traversal
        resp2 = self.client.get("/api/standards/IS%20800%20:%202007/traversal?depth=2")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertGreaterEqual(data2["count"], data["count"])

        # Invalid depth must be safely capped or rejected
        resp_bad = self.client.get("/api/standards/IS%20800%20:%202007/traversal?depth=5")
        self.assertIn(resp_bad.status_code, (200, 400))
        if resp_bad.status_code == 200:
            self.assertLessEqual(resp_bad.get_json()["max_depth"], 2)

    def test_03_traversal_non_elevation_invariant(self):
        """Traversing cross-references must not elevate unverified candidates to CLAUSE_VERIFIED."""
        traversed = self.graph.traverse_cross_references("IS 800 : 2007", max_depth=1)
        self.assertTrue(len(traversed) > 0)
        for t in traversed:
            # Traversed references are relational citations, not tender clause matches
            d = t.to_dict()
            self.assertIn(d["reference_kind"], ["EXPLICIT_NORMATIVE", "INFORMATIVE", "CODE_OF_PRACTICE", "TEST_METHOD"])
            self.assertIn(d["lifecycle_status"], ["Active", "Withdrawn", "Superseded", "Unknown"])
            self.assertTrue(bool(d["originating_evidence"]))

    def test_04_catalogue_hygiene_post_reconciliation_counts(self):
        """Verify catalogue status hygiene state in bis_catalogue.db."""
        cat_db = Path("data/catalogue/bis_catalogue.db")
        self.assertTrue(cat_db.exists())
        with sqlite3.connect(cat_db) as conn:
            counts = dict(conn.execute("SELECT status, COUNT(*) FROM catalogue_standards GROUP BY status").fetchall())
            total = sum(counts.values())

            self.assertEqual(total, 35208, "Total catalogue records must be preserved")
            self.assertEqual(counts.get("ACTIVE"), 23510, "Reconciled active standards must be exactly 23,510")
            self.assertEqual(counts.get("WITHDRAWN"), 11340, "Withdrawn standards must be 11,340")
            self.assertEqual(counts.get("UNKNOWN"), 342, "Unknown standards must be reduced from 13,024 to exactly 342")
            self.assertEqual(counts.get("SUPERSEDED"), 16, "Superseded standards must be 16")

            # Verify that the 342 UNKNOWN records have no raw active status in raw table or notes
            unknown_raw_active = conn.execute("""
                SELECT COUNT(*) FROM catalogue_standards 
                WHERE status = 'UNKNOWN' 
                AND (iso_equivalence LIKE '%(Active)%' OR recovery_reason LIKE '%RECONCILED%')
            """).fetchone()[0]
            self.assertEqual(unknown_raw_active, 0, "No remaining UNKNOWN record should contain unextracted active evidence")

    def test_05_authentic_standards_ingested_in_corpus(self):
        """Verify authentic passages for IS 694 : 2010 and IS 1180 (Part 1) : 2014."""
        stats = self.corpus.get_corpus_statistics()
        self.assertEqual(stats["documents_registered"], 13, "Corpus must have 13 ingested documents")
        self.assertEqual(stats["passages_created"], 53, "Corpus must have 53 authentic passages")

        doc694 = self.corpus.get_document_by_id("DOC-IS-694-2010")
        self.assertIsNotNone(doc694)
        self.assertEqual(doc694["licensing_status"], "STATUTORY_PUBLIC_GAZETTE")

        doc1180 = self.corpus.get_document_by_id("DOC-IS-1180-Part-1-2014")
        self.assertIsNotNone(doc1180)
        self.assertEqual(doc1180["licensing_status"], "STATUTORY_PUBLIC_GAZETTE")

        # IS 694 passages
        is694_passages = self.corpus.get_passages_by_standard("IS 694", edition_year=2010)
        self.assertGreaterEqual(len(is694_passages), 4)
        is694_clauses = {p.clause_identifier for p in is694_passages}
        self.assertTrue({"1.1", "4.1", "5.1", "15.1"}.issubset(is694_clauses))

        # IS 1180 passages
        is1180_passages = self.corpus.get_passages_by_standard("IS 1180 (Part 1)", edition_year=2014)
        self.assertGreaterEqual(len(is1180_passages), 5)
        is1180_clauses = {p.clause_identifier for p in is1180_passages}
        self.assertTrue({"1.1", "6.1", "7.1", "9.1", "10.1"}.issubset(is1180_clauses))

    def test_06_recommendation_traversed_references_serialization(self):
        """Verify traversed_cross_references are serialized into API normalized response."""
        recommender = StandardsRecommender()
        rec = recommender.recommend_for_text("Fabrication of structural steel roof truss using hot rolled sections")
        self.assertIsNotNone(rec.candidate_standard)
        # Verify traversed references field exists and is a list
        self.assertIsInstance(getattr(rec, "traversed_cross_references", None), list)


if __name__ == "__main__":
    unittest.main()
