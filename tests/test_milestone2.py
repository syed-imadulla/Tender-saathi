"""
Unit tests for Milestone 2:
- Extraction (PDF and Text, category classification, explicit standard mentions)
- Standards Search Engine integration
- Status and Supersedence Validation
- Evidence Grounding
- Central StandardsRecommender Pipeline
- Benchmark Evaluation Harness
"""

import unittest
import os
from src.standards import StandardsDatabase
from src.search import StandardsSearchEngine
from src.validate import validate_standard_status
from src.evidence import EvidenceVerifier
from src.extract import extract_from_text, extract_from_pdf
from src.recommend import StandardsRecommender
from src.evaluate import evaluate_benchmark, extract_standard_tokens


class TestMilestone2Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = StandardsDatabase()
        cls.recommender = StandardsRecommender(cls.db)

    def test_01_extract_from_text_categories(self):
        """Test category classification and explicit standard detection on text."""
        # Material
        req_mat = extract_from_text("Supply of CPVC pipes for water supply")
        self.assertEqual(req_mat.category, "material")

        # Product / Equipment
        req_prod = extract_from_text("Supply and installation of Sluice Valves and pumps")
        self.assertEqual(req_prod.category, "product_equipment")

        # Installation / Execution
        req_exec = extract_from_text("Civil works for laying of concrete pipes and trenching")
        self.assertEqual(req_exec.category, "installation_execution")

        # Explicit standard detection
        req_explicit = extract_from_text("Work to be carried out as per IS 1239 : 2004 and IS 458")
        self.assertTrue(any("IS 1239" in s for s in req_explicit.explicit_standards))
        self.assertTrue(any("IS 458" in s for s in req_explicit.explicit_standards))

    def test_02_extract_from_pdf_t020(self):
        """Test extraction from real CPPP tender PDF for T020."""
        pdf_path = "data/tenders/eProcurement System Government of India.pdf"
        self.assertTrue(os.path.exists(pdf_path), "T020 PDF file must exist")
        reqs = extract_from_pdf(pdf_path, tender_id="T020")
        self.assertGreaterEqual(len(reqs), 1)
        r0 = reqs[0]
        self.assertEqual(r0.tender_id, "T020")
        self.assertEqual(r0.category, "material")
        self.assertIn("CPVC pipe", r0.requirement_text)

    def test_03_supersedence_validation(self):
        """Test status and supersedence validation for active and obsolete standards."""
        # Active standard
        val_active = validate_standard_status("IS 15000", self.db)
        self.assertTrue(val_active.is_known)
        self.assertTrue(val_active.is_active)
        self.assertIsNone(val_active.successor_standard)

        # Superseded standard IS 10611 -> IS/ISO 10434
        val_sup = validate_standard_status("IS 10611", self.db)
        self.assertTrue(val_sup.is_known)
        self.assertFalse(val_sup.is_active)
        self.assertEqual(val_sup.status, "Superseded")
        self.assertIsNotNone(val_sup.successor_standard)
        self.assertIn("10434", val_sup.successor_standard)

        # Superseded tile standard IS 13753 -> IS 15622
        val_tiles = validate_standard_status("IS 13753", self.db)
        self.assertTrue(val_tiles.is_known)
        self.assertFalse(val_tiles.is_active)
        self.assertIn("15622", val_tiles.successor_standard)

    def test_04_evidence_grounding(self):
        """Test evidence verifier grounds factual claims strictly against scope/metadata."""
        verifier = EvidenceVerifier(self.db)
        # Grounded claim against IS 778
        claim_grounded = verifier.verify_claim(
            claim="Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes",
            standard_id="IS-778-1984",
            expected_section="Scope"
        )
        self.assertTrue(claim_grounded.is_grounded)
        self.assertIn("nominal sizes 8 to 100 mm", claim_grounded.source_text)

        # Non-existent standard claim
        claim_missing = verifier.verify_claim("Fabricated standard", "NON-EXISTENT-ID")
        self.assertFalse(claim_missing.is_grounded)
        self.assertIn("Insufficient evidence", claim_missing.source_text)

    def test_05_recommender_pipeline_t020(self):
        """Test full recommendation pipeline on CPVC pipe requirement."""
        res = self.recommender.recommend_for_text("CPVC pipe replacement for water supply")
        self.assertIn("IS 15778", res.candidate_standard)
        self.assertEqual(res.confidence, "High")
        self.assertFalse(res.human_review_required)
        self.assertGreaterEqual(len(res.recommendations), 1)

    def test_06_recommender_ambiguity_gating(self):
        """Test that ambiguous requirement (unspecified valve replacement) triggers human review."""
        res = self.recommender.recommend_for_text("Replacement of damaged valves in pipeline")
        self.assertTrue(res.human_review_required)
        self.assertIn("Nominal Size", res.reason)

    def test_07_benchmark_evaluation_harness(self):
        """Test that evaluation harness runs over ground_truth.csv and computes expected metrics."""
        metrics = evaluate_benchmark()
        self.assertEqual(metrics["dataset_size"], 20)
        self.assertGreaterEqual(metrics["top1_accuracy"], 70.0)
        self.assertGreaterEqual(metrics["top3_recall"], 80.0)
        self.assertGreaterEqual(metrics["top3_with_alternatives_recall"], 85.0)
        self.assertGreaterEqual(metrics["mrr"], 0.75)
        self.assertEqual(metrics["supersedence_rate"], 100.0)
        self.assertTrue(os.path.exists(metrics["report_path"]))
        self.assertTrue(os.path.exists(metrics["csv_path"]))


if __name__ == "__main__":
    unittest.main()
