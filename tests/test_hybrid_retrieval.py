"""
Unit tests for Milestone 2: Hybrid Retrieval Engine.

Covers:
1. Okapi BM25 retrieval for CPVC pipes (IS 15778)
2. Okapi BM25 retrieval for food hygiene (IS 2491 / IS 15000)
3. Semantic retrieval for paraphrased query without exact keywords
4. Hybrid retrieval candidate merging and deduplication
5. Compound requirement resolution for T013: VFD water pump panel (IS/IEC 61800-2)
6. Compound requirement resolution for T014: Process water pump with 3.3 kV motor (IS/IEC 60034-1)
7. Lifecycle / supersedence validation preserved in hybrid mode
8. Evidence grounding preserved in hybrid mode
9. Graceful fallback when semantic model is unavailable
"""

import unittest
from typing import Optional

from src.standards import StandardsDatabase
from src.bm25_search import BM25SearchEngine
from src.semantic_search import SemanticSearchEngine
from src.retrieval import HybridRetrievalEngine
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.validate import validate_standard_status
from src.evidence import EvidenceVerifier


class TestHybridRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = StandardsDatabase()
        cls.bm25 = BM25SearchEngine(cls.db)
        cls.semantic = SemanticSearchEngine(cls.db)
        cls.hybrid_engine = HybridRetrievalEngine(cls.db)
        cls.recommender = StandardsRecommender(cls.db, retrieval_mode="hybrid")

    def test_01_bm25_returns_cpvc_pipes(self):
        """BM25 returns relevant candidate for CPVC pipes."""
        hits = self.bm25.search("CPVC pipes for potable water distribution", top_k=3)
        self.assertGreater(len(hits), 0, "BM25 should return results for CPVC query")
        std_numbers = [h.standard_number for h in hits]
        self.assertTrue(
            any("15778" in s for s in std_numbers),
            f"Expected IS 15778 in top BM25 results, got {std_numbers}"
        )
        self.assertGreater(hits[0].score, 0.0, "BM25 score must be strictly positive")

    def test_02_bm25_returns_food_hygiene(self):
        """BM25 returns relevant candidate for food hygiene."""
        hits = self.bm25.search("food hygiene and safety management practices", top_k=3)
        self.assertGreater(len(hits), 0, "BM25 should return results for food hygiene")
        std_numbers = [h.standard_number for h in hits]
        self.assertTrue(
            any("2491" in s or "15000" in s for s in std_numbers),
            f"Expected IS 2491 or IS 15000 in top BM25 results, got {std_numbers}"
        )

    def test_03_semantic_returns_paraphrased_query(self):
        """Semantic search returns relevant candidate for a paraphrased query."""
        # Query with conceptual paraphrase: "cafeteria sanitary preparation guidelines"
        hits = self.semantic.search("cafeteria sanitary preparation guidelines", top_k=3)
        self.assertGreater(len(hits), 0, "Semantic search should return results")
        std_numbers = [h.standard_number for h in hits]
        # Should associate with IS 2491 (Food hygiene) or IS 15000 (HACCP)
        self.assertTrue(
            any("2491" in s or "15000" in s for s in std_numbers),
            f"Expected IS 2491 or IS 15000 in top semantic results for paraphrase, got {std_numbers}"
        )
        self.assertGreater(hits[0].similarity_score, 0.30, "Cosine similarity should be significant")

    def test_04_hybrid_merges_and_deduplicates_candidates(self):
        """Hybrid retrieval merges and deduplicates candidates across all three sources."""
        query = "potable water distribution pipeline and valves"
        results = self.hybrid_engine.search(query, top_k=5, mode="hybrid")
        self.assertGreater(len(results), 0)
        # Check standard_numbers are unique
        std_nums = [r.standard_number for r in results]
        self.assertEqual(
            len(std_nums), len(set(std_nums)),
            f"Candidate standards must be deduplicated: {std_nums}"
        )
        # Verify explainability reasons contain component attributions
        top_res = results[0]
        self.assertTrue(len(top_res.relevance_reason) > 0, "Result must contain explainability reason")

    def test_05_t013_vfd_water_pump_panel(self):
        """T013: VFD water pump panel resolves to IS/IEC 61800-2."""
        text = "Supply, Installation, Testing & Commissioning of VFD water pump control panel for booster pumping station"
        req = extract_from_text(text, requirement_id="T013-R002")
        rec = self.recommender.recommend_for_requirement(req)
        
        self.assertIn(
            "61800", rec.candidate_standard,
            f"T013 must resolve to IS/IEC 61800, got: {rec.candidate_standard}"
        )
        self.assertNotIn(
            "9694", rec.candidate_standard,
            "Agricultural pump code IS 9694 must NOT be recommended for industrial VFD panel"
        )

    def test_06_t014_process_water_pump_3_3kv_motor(self):
        """T014: Process water pump with 3.3 kV motor resolves to IS/IEC 60034-1."""
        text = "Design, manufacture, supply and testing of process water pump sets coupled with 3.3 kV medium voltage induction motor"
        req = extract_from_text(text, requirement_id="T014-R002")
        rec = self.recommender.recommend_for_requirement(req)

        self.assertIn(
            "60034", rec.candidate_standard,
            f"T014 must resolve to IS/IEC 60034, got: {rec.candidate_standard}"
        )
        self.assertNotIn(
            "9694", rec.candidate_standard,
            "Agricultural pump code IS 9694 must NOT be recommended for 3.3 kV process water pump motor"
        )

    def test_07_lifecycle_validation_still_works(self):
        """Lifecycle / supersedence validation still operates as a strict guardrail."""
        # Querying an obsolete standard in recommendation text
        rec = self.recommender.recommend_for_text("Procurement of valves conforming to IS 10611")
        self.assertIn(
            "10434", rec.candidate_standard,
            f"Superseded IS 10611 must return active successor IS/ISO 10434, got {rec.candidate_standard}"
        )
        self.assertIn("Tender cited superseded standard", rec.recommendations[0].superseded_warning)

    def test_08_evidence_grounding_still_works(self):
        """Evidence grounding against Scope/Metadata remains active in hybrid recommendations."""
        req = extract_from_text("Supply of CPVC pipes for hot and cold water", requirement_id="TEST-CPVC")
        rec = self.recommender.recommend_for_requirement(req)
        
        self.assertTrue(len(rec.evidence) > 0, "Recommendation must have evidence")
        self.assertIn(rec.provenance, ["VERIFIED", "CURATED"], "IS 15778 provenance must be VERIFIED or CURATED")

        # Test evidence verifier explicitly on verified standard IS 778
        verifier = EvidenceVerifier(self.db)
        claim = verifier.verify_claim("Copper alloy gate, globe and check valves", "IS-778-1984", expected_section="Scope")
        self.assertTrue(claim.is_grounded, "Scope claim must ground to authoritative text")

    def test_09_fallback_works_when_semantic_unavailable(self):
        """Hybrid retrieval gracefully falls back to BM25 + Deterministic when semantic engine is disabled."""
        # Create an engine with an unavailable semantic model
        fallback_hybrid = HybridRetrievalEngine(self.db)
        fallback_hybrid.semantic_engine.is_available = False

        hits = fallback_hybrid.search("Supply of CPVC pipes", top_k=3, mode="hybrid")
        self.assertGreater(len(hits), 0, "Fallback must return hits even without semantic model")
        std_nums = [h.standard_number for h in hits]
        self.assertTrue(
            any("15778" in s for s in std_nums),
            f"Fallback must still retrieve IS 15778 via BM25 + deterministic, got {std_nums}"
        )


if __name__ == "__main__":
    unittest.main()
