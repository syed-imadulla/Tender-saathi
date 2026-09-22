"""
Unit and Integration Tests for Ambiguity Engine Calibration & Multi-Standard Decision Quality.

Verifies:
1. Calibrated Competition Gate:
   - Distant alternatives (wide score gap / zero lexical match) do NOT trigger AMBIGUOUS.
   - Genuinely close competitors (close score, missing discriminator) DO trigger AMBIGUOUS.
2. Legitimate Safe Abstention Protection:
   - Generic "Valve Replacement" without fluid, pressure, or metallurgy strictly abstains.
3. Procurement-Object-Level Discrimination:
   - Facility / premise / establishment requirements (e.g., canteens, food outlets)
     prioritize facility/hygiene codes of practice over individual kitchen appliances.
4. Component-Level Ambiguity Isolation:
   - Ambiguity in a secondary component does not suppress a confident primary recommendation.
5. Invariant & Negative Control Preservation:
   - CPVC with continuous steam remains strictly rejected.
"""

import unittest
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.search import SearchResult
from src.ambiguity import AmbiguityEngine, AmbiguityState
from src.applicability import ApplicabilityGate
from src.standards import classify_standard_role


class TestAmbiguityCalibration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.recommender = StandardsRecommender(retrieval_mode="hybrid")
        cls.ambiguity_engine = AmbiguityEngine()
        cls.applicability_gate = ApplicabilityGate()

    # -----------------------------------------------------------------------
    # 1. Calibrated Candidate Competition
    # -----------------------------------------------------------------------

    def test_distant_candidate_does_not_trigger_ambiguity(self):
        """A distant alternative candidate with weak relevance must NOT trigger AMBIGUOUS."""
        # Synthetic SearchResult pair: Top candidate has dominant score (0.83), Alt has distant score (0.22)
        c_top = SearchResult(
            standard_id="STD_001",
            standard_number="IS 7098 (Part 1)",
            year=1988,
            full_title="Crosslinked Polyethylene Insulated Cables - Part 1: Up to 1100 V",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.829,
            relevance_reason="Matches underground cable requirement",
            scope_summary="Covers crosslinked polyethylene insulated cables up to 1100 V",
            bm25_score=0.98,
            semantic_score=0.56,
            deterministic_score=0.96,
            final_score=0.829
        )
        c_distant = SearchResult(
            standard_id="STD_002",
            standard_number="IS 7098 (Part 2)",
            year=2011,
            full_title="Crosslinked Polyethylene Insulated Cables - Part 2: 3.3 kV to 33 kV",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.220,
            relevance_reason="Distant semantic match on cable keyword",
            scope_summary="Covers medium and high voltage cables from 3.3 kV up to 33 kV",
            bm25_score=0.00,
            semantic_score=0.33,
            deterministic_score=0.41,
            final_score=0.220
        )

        text = "Providing and laying underground cable for main supply of electricity"
        report = self.ambiguity_engine.evaluate(
            requirement_text=text,
            decomposed_components=[],
            completeness_report=None,
            retrieved_candidates=[c_top, c_distant],
            applicable_candidates=[c_top, c_distant],
            rejected_candidates=[],
            candidate_applicability_map={},
            critic_outcome=None,
            explicit_standards=[]
        )

        # Distant candidate should not cause full AMBIGUOUS state
        self.assertNotEqual(
            report.ambiguity_state,
            AmbiguityState.AMBIGUOUS,
            "Distant candidate with score 0.22 should not trigger AMBIGUOUS against dominant candidate with score 0.83."
        )

    def test_genuinely_close_candidates_trigger_ambiguity(self):
        """Genuinely close candidates competing on missing parameters MUST trigger AMBIGUOUS."""
        # Synthetic SearchResult pair: Both candidates close in score (~0.65 vs ~0.62)
        c1 = SearchResult(
            standard_id="STD_001",
            standard_number="IS 7098 (Part 1)",
            year=1988,
            full_title="Crosslinked Polyethylene Insulated Cables - Part 1: Up to 1100 V",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.640,
            relevance_reason="Power cable match",
            scope_summary="Covers XLPE power cables up to 1100 V",
            bm25_score=0.85,
            semantic_score=0.50,
            deterministic_score=0.60,
            final_score=0.640
        )
        c2 = SearchResult(
            standard_id="STD_002",
            standard_number="IS 7098 (Part 2)",
            year=2011,
            full_title="Crosslinked Polyethylene Insulated Cables - Part 2: 3.3 kV to 33 kV",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.630,
            relevance_reason="Power cable match",
            scope_summary="Covers XLPE power cables 3.3 kV to 33 kV",
            bm25_score=0.83,
            semantic_score=0.49,
            deterministic_score=0.60,
            final_score=0.630
        )

        text = "Supply of power cables from electrical room to distribution point"
        report = self.ambiguity_engine.evaluate(
            requirement_text=text,
            decomposed_components=[],
            completeness_report=None,
            retrieved_candidates=[c1, c2],
            applicable_candidates=[c1, c2],
            rejected_candidates=[],
            candidate_applicability_map={},
            critic_outcome=None,
            explicit_standards=[]
        )

        self.assertEqual(
            report.ambiguity_state,
            AmbiguityState.AMBIGUOUS,
            "Close candidates with missing voltage specification must trigger AMBIGUOUS."
        )

    # -----------------------------------------------------------------------
    # 2. Legitimate Safe Abstention Protection
    # -----------------------------------------------------------------------

    def test_generic_valve_replacement_remains_safe_abstention(self):
        """Generic 'Valve Replacement' without fluid, pressure, or metallurgy must remain a safe abstention."""
        req = extract_from_text("Valve Replacement", requirement_id="VALVE-TEST-01")
        res = self.recommender.recommend_for_requirement(req)

        self.assertIsNone(
            res.candidate_standard,
            "Generic Valve Replacement must abstain without specification of service or material."
        )
        self.assertTrue(
            res.human_review_required,
            "Generic Valve Replacement must flag human review required."
        )
        self.assertIn(res.ambiguity_state, ["AMBIGUOUS", "INCOMPLETE"])

    def test_synthetic_unspecified_valve_abstains(self):
        """Synthetic unspecified valve replacement for plant water distribution must safely abstain."""
        req = extract_from_text("Replacement of utility line valves across plant water distribution network", requirement_id="VALVE-TEST-02")
        res = self.recommender.recommend_for_requirement(req)

        self.assertIsNone(res.candidate_standard)
        self.assertTrue(res.human_review_required)
        self.assertIn(res.ambiguity_state, ["AMBIGUOUS", "INCOMPLETE"])

    # -----------------------------------------------------------------------
    # 3. Procurement-Object-Level Discrimination (Facility/Premise vs Appliance)
    # -----------------------------------------------------------------------

    def test_food_premise_prioritizes_hygiene_code_over_appliance(self):
        """A commercial catering premise / food outlet must prioritize hygiene codes over individual appliances."""
        req = extract_from_text("Operation of Canteen and Food Outlet on Campus", requirement_id="PREMISE-TEST-01")
        res = self.recommender.recommend_for_requirement(req)

        # Standard recommended should be hygiene / food safety related (e.g. IS 2491, IS 15000), NOT an electrical appliance (IS 302)
        if res.candidate_standard:
            self.assertNotIn(
                "302",
                res.candidate_standard,
                "Food outlet / canteen requirement must NOT recommend appliance safety standard IS 302 as Top-1."
            )
            self.assertTrue(
                any(std in res.candidate_standard for std in ["2491", "15000", "FSSAI"]),
                f"Candidate standard should be a food hygiene/safety code, got: {res.candidate_standard}"
            )

    def test_appliance_role_classification(self):
        """Standards covering household/commercial appliances should be categorized with appliance role."""
        role = classify_standard_role(
            standard_number="IS 302 (Part 2/Sec 209)",
            title="Safety of Household and Similar Electrical Appliances - Section 209: Low Speed Food Grinding Machines",
            scope="Safety requirements for electric food grinders"
        )
        self.assertIn(role, ["APPLIANCE_TOOL", "SAFETY", "APPLIANCE_PRODUCT"])

    # -----------------------------------------------------------------------
    # 4. Component-Level Ambiguity Isolation
    # -----------------------------------------------------------------------

    def test_multi_component_partial_ambiguity_isolation(self):
        """A compound requirement with one clear component and one ambiguous component must isolate the ambiguity."""
        text = "Cable connection of DG Set in newly constructed building"
        req = extract_from_text(text, requirement_id="DG-TEST-01")
        res = self.recommender.recommend_for_requirement(req)

        # DG set earthing is supported by IS 3043 with high confidence.
        # Cable ambiguity should not completely blank the recommendation if earthing is clearly supported.
        self.assertIsNotNone(
            res.candidate_standard,
            "DG Set connection should yield a confident primary recommendation (e.g., IS 3043 for earthing) rather than collapsing to None."
        )
        self.assertIn("3043", res.candidate_standard)

    # -----------------------------------------------------------------------
    # 5. Invariant & Negative Control Preservation
    # -----------------------------------------------------------------------

    def test_cpvc_continuous_steam_remains_strictly_rejected(self):
        """Negative control: CPVC with continuous steam service must remain strictly rejected."""
        req = extract_from_text("Supply of CPVC pipes for continuous superheated steam service at 180 C", requirement_id="CPVC-STEAM-01")
        res = self.recommender.recommend_for_requirement(req)

        self.assertIsNone(
            res.candidate_standard,
            "CPVC specified for continuous superheated steam must strictly abstain."
        )
        self.assertTrue(res.human_review_required)
        self.assertIn(res.ambiguity_state, ["CONFLICTING", "NO_RELIABLE_MATCH"])


if __name__ == "__main__":
    unittest.main()
