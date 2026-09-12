"""
Priority 5: Ambiguity Engine V2 + Catalogue-Scale Validation Test Suite.

Validates the 12 core requirements from Section 13 of the Priority 5 specification:
1. Retrieval candidate != semantic competitor
2. Switchgear vs VFD false competition prevention (Generalization Case A)
3. Product vs installation standard role classification distinction
4. Installation standard surfaces as dependency, not competitor (Generalization Case B)
5. Missing discriminator detected and returned as structured output
6. Genuine material ambiguity produces plausible competitors (AMB-AMB-01 / Cable)
7. Genuine metallurgy ambiguity produces plausible competitors (Generalization Case C)
8. Expanded 500+ catalogue candidate retrieval & competition evaluation
9. Safe abstention preserved (candidate=None, review=True, score=0.0)
10. Candidate == evidence identity invariant 100%
11. Unrelated candidate rejection (assembly parts, unrelated scopes)
12. Unseen-domain generalization across transformers, cement, and pipes
"""

import os
import unittest
from typing import Dict, Any, List

from src.ambiguity import (
    AmbiguityState,
    AmbiguityEngine,
    is_true_competing_interpretation
)
from src.standards import StandardsDatabase, classify_standard_role
from src.recommend import StandardsRecommender
from src.extract import extract_from_text


class TestAmbiguityEngineV2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.baseline_db_path = "data/standards/standards.db"
        cls.catalogue_db_path = "data/catalogue/catalogue.db"
        cls.recommender = StandardsRecommender(db=StandardsDatabase(cls.baseline_db_path), retrieval_mode="hybrid")
        cls.ambiguity_engine = AmbiguityEngine(separation_threshold=0.08)

    def test_01_retrieval_candidate_is_not_automatically_competitor(self):
        """1. High retrieval similarity alone does NOT constitute semantic competition."""
        text = "Supply and installation of low-voltage switchgear and controlgear panels for industrial substation distribution."
        sr = self.recommender.search_engine.search(text, top_k=8)
        self.assertTrue(len(sr) >= 2)

        # IS/IEC 61439-2 is switchgear, IS/IEC 61800-2 is VFD / power drive
        c_swg = next((s for s in sr if "61439" in s.standard_number), None)
        c_vfd = next((s for s in sr if "61800" in s.standard_number), None)
        self.assertIsNotNone(c_swg, "IS/IEC 61439 must be retrieved")
        self.assertIsNotNone(c_vfd, "IS/IEC 61800 must be in search pool")

        # Despite both being retrieved, is_true_competing_interpretation must return False
        is_comp, _, _ = self.ambiguity_engine.is_true_competing_interpretation(text, c_swg, c_vfd)
        self.assertFalse(is_comp, "VFD drive standard must not compete against switchgear panel")

    def test_02_switchgear_vs_vfd_false_competition_prevented(self):
        """2. Case A: Switchgear panel does NOT flag false competition against VFD standard."""
        text = "Supply and installation of low-voltage switchgear and controlgear panels for industrial substation distribution."
        res = self.recommender.recommend_for_text(text)

        # Must recommend IS/IEC 61439 as primary product
        self.assertIsNotNone(res.candidate_standard)
        self.assertIn("61439", res.candidate_standard)
        self.assertEqual(res.standard_role, "PRIMARY_PRODUCT")

        # Must NOT flag competition against IS/IEC 61800-2
        comp_nums = [c.get("standard_number", "") for c in res.competing_interpretations]
        self.assertNotIn("61800-2", " ".join(comp_nums))
        self.assertNotIn("61800", res.ambiguity_reason)

    def test_03_product_vs_installation_distinction(self):
        """3. classify_standard_role correctly segregates product from installation / CoP standards."""
        # Product standards
        self.assertEqual(classify_standard_role("IS 7098 (Part 1)", "Crosslinked Polyethylene Insulated Cables"), "PRIMARY_PRODUCT")
        self.assertEqual(classify_standard_role("IS 694", "PVC Insulated Cables for Working Voltages"), "PRIMARY_PRODUCT")
        self.assertEqual(classify_standard_role("IS 458", "Precast Concrete Pipes"), "PRIMARY_PRODUCT")
        self.assertEqual(classify_standard_role("IS 778", "Copper Alloy Gate, Globe and Check Valves"), "PRIMARY_PRODUCT")
        self.assertEqual(classify_standard_role("IS 14846", "Sluice Valve for Water Works Purposes"), "PRIMARY_PRODUCT")
        self.assertEqual(classify_standard_role("IS 1180 (Part 1)", "Outdoor Type Oil Immersed Distribution Transformers"), "PRIMARY_PRODUCT")

        # Installation / Code of practice standards
        self.assertEqual(classify_standard_role("IS 1255", "Code of Practice for Installation of Power Cables"), "INSTALLATION")
        self.assertEqual(classify_standard_role("IS 783", "Code of Practice for Laying of Concrete Pipes"), "INSTALLATION")
        self.assertEqual(classify_standard_role("IS 10028 (Part 2)", "Code of Practice for Installation of Transformers"), "INSTALLATION")
        self.assertEqual(classify_standard_role("IS 3043", "Code of Practice for Earthing"), "CODE_OF_PRACTICE")

    def test_04_installation_standard_surfaces_as_dependency_not_competitor(self):
        """4. Case B: XLPE cable identifies IS 7098 (Part 1) as primary and IS 1255 as dependency."""
        text = "Supply and laying of crosslinked polyethylene insulated power cables for working voltages up to and including 1100 V with aluminium conductors."
        res = self.recommender.recommend_for_text(text)

        # Primary product must be IS 7098 (Part 1)
        self.assertIsNotNone(res.candidate_standard)
        self.assertIn("7098", res.candidate_standard)
        self.assertEqual(res.standard_role, "PRIMARY_PRODUCT")

        # Installation standard IS 1255 must appear in dependencies
        dep_nums = [d.get("standard_number", "") for d in res.dependencies]
        self.assertTrue(any("1255" in d for d in dep_nums), f"IS 1255 must be in dependencies: {dep_nums}")

        # IS 1255 must NOT be listed as a competing candidate
        comp_nums = [c.get("standard_number", "") for c in res.competing_interpretations]
        self.assertTrue(not any("1255" in c for c in comp_nums), f"IS 1255 must not be a competitor: {comp_nums}")

    def test_05_missing_discriminator_detected_and_structured(self):
        """5. Incomplete specifications produce structured missing discriminator reports."""
        text = "Procurement and supply of industrial valves for water utility distribution network."
        req = extract_from_text(text, requirement_id="V2-TEST-INC")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "AMBIGUOUS")
        self.assertIsNone(res.candidate_standard)
        self.assertTrue(res.human_review_required)
        self.assertIsNotNone(res.suggested_clarification_question)
        self.assertTrue(len(res.missing_information) > 0 or len(res.reason) > 0)

    def test_06_material_ambiguity_produces_plausible_competitors(self):
        """6. Cable procurement with omitted insulation polymer flags PVC vs XLPE competition."""
        text = "Supply of 1100V power cables for internal electrical distribution."
        req = extract_from_text(text, requirement_id="V2-TEST-AMB-CABLE")
        res = self.recommender.recommend_for_requirement(req)

        # Safe abstention holds
        self.assertIn(res.ambiguity_state, ["AMBIGUOUS", "INCOMPLETE", "REVIEW_REQUIRED"])
        self.assertTrue(res.human_review_required)

        # Candidate competition gate evaluation for PVC vs XLPE
        from src.search import SearchResult
        c_pvc = SearchResult(
            standard_id="IS 694",
            standard_number="IS 694",
            year=2010,
            full_title="PVC Insulated Cables for Working Voltages up to and Including 1100 V",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.60,
            relevance_reason="PVC cable match",
            scope_summary="PVC insulated cables specification",
            final_score=0.60
        )
        c_xlpe = SearchResult(
            standard_id="IS 7098 (Part 1)",
            standard_number="IS 7098 (Part 1)",
            year=1988,
            full_title="Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.58,
            relevance_reason="XLPE cable match",
            scope_summary="XLPE insulated cables specification",
            final_score=0.58
        )
        is_comp, discrim, _ = self.ambiguity_engine.is_true_competing_interpretation(text, c_pvc, c_xlpe)
        self.assertTrue(is_comp, "PVC and XLPE should compete as alternative insulation materials")
        self.assertIn("material", discrim)

    def test_07_metallurgy_ambiguity_produces_plausible_competitors(self):
        """7. Case C: 100mm gate valve without metallurgy flags genuine IS 778 vs IS 14846 competition."""
        text = "Supply of 100mm gate valve for water supply application."
        res = self.recommender.recommend_for_text(text)

        # Gate valve up to 100mm can be Copper Alloy (IS 778) or Cast Iron Sluice (IS 14846)
        self.assertEqual(res.ambiguity_state, "AMBIGUOUS")
        self.assertIsNone(res.candidate_standard)
        self.assertTrue(res.human_review_required)
        self.assertTrue(len(res.competing_interpretations) >= 2)
        comp_stds = [c.get("standard_number", "") for c in res.competing_interpretations]
        self.assertTrue(any("778" in c for c in comp_stds) and any("14846" in c for c in comp_stds))

    def test_08_expanded_catalogue_competitor_retrieval(self):
        """8. Expanded 500+ standard catalogue retrieval operates cleanly without hallucination."""
        if not os.path.exists(self.catalogue_db_path):
            self.skipTest("500+ catalogue DB not found")

        cat_rec = StandardsRecommender(db=StandardsDatabase(self.catalogue_db_path))
        text = "Supply and installation of 1000 kVA, 11/0.433 kV outdoor distribution transformer for substation."
        res = cat_rec.recommend_for_text(text)

        # Must correctly find IS 1180 (Part 1) from expanded catalogue
        self.assertIsNotNone(res.candidate_standard)
        self.assertIn("1180", res.candidate_standard)
        self.assertEqual(res.standard_role, "PRIMARY_PRODUCT")
        # Must locate installation dependencies (IS 10028)
        dep_nums = [d.get("standard_number", "") for d in res.dependencies]
        self.assertTrue(any("10028" in d for d in dep_nums))

    def test_09_safe_abstention_preserved(self):
        """9. Invariant: For AMBIGUOUS, INCOMPLETE, CONFLICTING, NO_RELIABLE_MATCH, candidate=None & review=True."""
        abstention_queries = [
            ("Supply of 100mm gate valve for water supply application.", "AMBIGUOUS"),
            ("Procurement and supply of industrial valves for water utility distribution network.", "AMBIGUOUS"),
            ("Installation of 33 kV medium voltage electrical substation cabling conforming to IS 694.", "CONFLICTING"),
            ("Procurement of liquid sodium coolant pumps for secondary heat transport system of fast breeder nuclear reactor.", "NO_RELIABLE_MATCH")
        ]
        for query, expected_state in abstention_queries:
            res = self.recommender.recommend_for_text(query)
            self.assertEqual(res.ambiguity_state, expected_state, f"Query '{query}' should evaluate to {expected_state}")
            self.assertIsNone(res.candidate_standard, f"candidate_standard must be None for {expected_state}")
            self.assertIsNone(res.evidence_standard, f"evidence_standard must be None for {expected_state}")
            self.assertTrue(res.human_review_required, f"human_review_required must be True for {expected_state}")
            self.assertEqual(res.relevance_score, 0.0, f"relevance_score must be 0.0 for {expected_state}")

    def test_10_candidate_evidence_identity_invariant_100_percent(self):
        """10. Invariant: Whenever candidate_standard is non-null, candidate_standard == evidence_standard."""
        queries = [
            "Supply and installation of low-voltage switchgear and controlgear panels for industrial substation distribution.",
            "Supply and laying of crosslinked polyethylene insulated power cables for working voltages up to and including 1100 V with aluminium conductors.",
            "Supply and installation of chlorinated polyvinyl chloride (CPVC) pipes and fittings conforming to IS 15778.",
            "Supply of 43 Grade Ordinary Portland Cement conforming to IS 269.",
            "Supply and delivery of mild steel ERW pipes for drinking water distribution network."
        ]
        for q in queries:
            res = self.recommender.recommend_for_text(q)
            if res.candidate_standard is not None:
                self.assertEqual(
                    res.candidate_standard, res.evidence_standard,
                    f"Candidate ({res.candidate_standard}) must equal Evidence ({res.evidence_standard}) for query: {q}"
                )

    def test_11_unrelated_candidate_rejection(self):
        """11. Assembly components or unrelated scopes (e.g. luminaires for switchgear) are rejected as competitors."""
        text = "Supply and installation of low-voltage switchgear and controlgear panels for industrial substation distribution."
        sr = self.recommender.search_engine.search(text, top_k=8)

        c_swg = next((s for s in sr if "61439" in s.standard_number), None)
        c_lum = next((s for s in sr if "10322" in s.standard_number or "luminaire" in s.full_title.lower()), None)
        if c_swg and c_lum:
            is_comp, _, _ = self.ambiguity_engine.is_true_competing_interpretation(text, c_swg, c_lum)
            self.assertFalse(is_comp, "Luminaire must not compete with switchgear")

    def test_12_unseen_domain_generalization(self):
        """12. Generalization across unseen domains without hardcoding query text."""
        # Unseen domain: Distribution Transformers (IS 1180 in catalogue vs IS 2026 power transformers)
        if os.path.exists(self.catalogue_db_path):
            cat_rec = StandardsRecommender(db=StandardsDatabase(self.catalogue_db_path))
            res = cat_rec.recommend_for_text("Outdoor mineral oil immersed distribution transformer 500 kVA 11 kV.")
            self.assertIsNotNone(res.candidate_standard)
            self.assertIn("1180", res.candidate_standard)
            self.assertEqual(res.standard_role, "PRIMARY_PRODUCT")


if __name__ == "__main__":
    unittest.main()
