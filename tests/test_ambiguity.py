"""
Unit and Integration Tests for TenderSaathi 6-State Ambiguity Engine.

Validates:
- Exactly 6 ambiguity states (CLEAR, AMBIGUOUS, INCOMPLETE, CONFLICTING, NO_RELIABLE_MATCH, REVIEW_REQUIRED)
- Invariant 1: candidate_standard == evidence_standard for all non-null recommendations
- Invariant 2: For INCOMPLETE, AMBIGUOUS, CONFLICTING, NO_RELIABLE_MATCH:
  candidate_standard = None, evidence_standard = None, human_review_required = True
- Evidence NONE / Grounding failure maps to REVIEW_REQUIRED with separate evidence_status
- Authoritative conflict rules (CONF-01, CONF-02, CONF-03)
- Zero retrieval != proof of non-existence
"""

import unittest
from src.ambiguity import (
    AmbiguityState,
    AmbiguityEngine,
    AmbiguityReport,
    ConflictRegistry
)
from src.recommend import StandardsRecommender
from src.extract import extract_from_text


class TestAmbiguityEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.recommender = StandardsRecommender(retrieval_mode="hybrid")

    def test_01_ambiguity_states_enumeration(self):
        """Verify strictly 6 ambiguity states are defined with no extra states."""
        expected_states = {
            "CLEAR",
            "AMBIGUOUS",
            "INCOMPLETE",
            "CONFLICTING",
            "NO_RELIABLE_MATCH",
            "REVIEW_REQUIRED"
        }
        actual_states = {s.value for s in AmbiguityState}
        self.assertEqual(actual_states, expected_states, "Must have exactly the 6 approved ambiguity states.")
        self.assertEqual(len(AmbiguityState), 6, "Must define exactly 6 enum values.")

    def test_02_clear_state_single_recommendation(self):
        """CLEAR: One primary applicable standard is clearly identifiable and sufficiently supported."""
        text = "Supply and installation of chlorinated polyvinyl chloride (CPVC) pipes and fittings for domestic hot and cold water distribution system conforming to IS 15778."
        req = extract_from_text(text, requirement_id="TEST-CLEAR-01")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "CLEAR")
        self.assertIsNotNone(res.candidate_standard)
        self.assertIn("15778", res.candidate_standard)
        self.assertEqual(res.candidate_standard, res.evidence_standard)
        self.assertFalse(res.human_review_required)
        self.assertEqual(res.evidence_status, "VALID")

    def test_03_incomplete_state_abstention(self):
        """INCOMPLETE: Specification lacks critical parameters needed to identify standard."""
        text = "Procurement and supply of industrial valves for water utility distribution network."
        req = extract_from_text(text, requirement_id="TEST-INC-01")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "INCOMPLETE")
        self.assertIsNone(res.candidate_standard)
        self.assertIsNone(res.evidence_standard)
        self.assertTrue(res.human_review_required)
        self.assertTrue("valve" in res.reason.lower() or "missing" in res.reason.lower())
        self.assertIsNotNone(res.suggested_clarification_question)

    def test_04_ambiguous_state_competing_candidates(self):
        """AMBIGUOUS: Multiple viable standards with close scores and no distinguishing specification."""
        text = "Operation and management of staff canteen and food outlet on BOT concession revenue share model."
        req = extract_from_text(text, requirement_id="TEST-AMB-01")
        res = self.recommender.recommend_for_requirement(req)

        # Commercial BOT food concession has competing viable standards (IS 2491 vs IS 15000)
        self.assertEqual(res.ambiguity_state, "AMBIGUOUS")
        self.assertIsNone(res.candidate_standard)
        self.assertIsNone(res.evidence_standard)
        self.assertTrue(res.human_review_required)
        self.assertTrue(len(res.competing_interpretations) >= 2)

    def test_05_conflicting_state_conf04_voltage(self):
        """CONFLICTING: Low-voltage code (IS 694) cited for medium/high-voltage application."""
        text = "Installation of 33 kV medium voltage electrical substation cabling conforming to IS 694."
        req = extract_from_text(text, requirement_id="TEST-CONF-01")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "CONFLICTING")
        self.assertIsNone(res.candidate_standard)
        self.assertIsNone(res.evidence_standard)
        self.assertTrue(res.human_review_required)
        self.assertIn("CONF-04", res.reason)

    def test_06_conflicting_state_conf01_agri_industrial(self):
        """CONFLICTING: Agricultural pump code (IS 9079) cited for industrial process."""
        text = "Supply of centrifugal pumps for heavy industrial process water treatment plant with variable frequency drive conforming to IS 9079."
        req = extract_from_text(text, requirement_id="TEST-CONF-02")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "CONFLICTING")
        self.assertIsNone(res.candidate_standard)
        self.assertIsNone(res.evidence_standard)
        self.assertTrue(res.human_review_required)
        self.assertIn("CONF-01", res.reason)

    def test_07_conflicting_state_conf05_tile_crane(self):
        """CONFLICTING: Ceramic tile standard (IS 15622) cited for heavy crane rail track."""
        text = "REPLACEMENT OF CRANE RAIL TRACK FOR RMQC (RAIL MOUNTED QUAY CRANE) conforming to IS 15622."
        req = extract_from_text(text, requirement_id="TEST-CONF-03")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "CONFLICTING")
        self.assertIsNone(res.candidate_standard)
        self.assertIsNone(res.evidence_standard)
        self.assertTrue(res.human_review_required)
        self.assertIn("CONF-05", res.reason)

    def test_08_no_reliable_match_unsupported(self):
        """NO_RELIABLE_MATCH: Technology or product outside the catalogue."""
        text = "Procurement of carbon fiber reinforced polymer matrix prepreg sheets for supersonic aerospace fuselage structures."
        req = extract_from_text(text, requirement_id="TEST-NOM-01")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "NO_RELIABLE_MATCH")
        self.assertIsNone(res.candidate_standard)
        self.assertIsNone(res.evidence_standard)
        self.assertTrue(res.human_review_required)
        self.assertEqual(res.title, "No Reliable Indian Standard Match Found")

    def test_09_review_required_waterworks_valves(self):
        """REVIEW_REQUIRED: Valid candidate recommended but review needed for unstated metallurgy."""
        text = "Supply and installation of waterworks valves for potable water pipelines, including sluice/gate valves and check valves."
        req = extract_from_text(text, requirement_id="TEST-REV-01")
        res = self.recommender.recommend_for_requirement(req)

        self.assertEqual(res.ambiguity_state, "REVIEW_REQUIRED")
        self.assertIsNotNone(res.candidate_standard)
        self.assertEqual(res.candidate_standard, res.evidence_standard)
        self.assertTrue(res.human_review_required)

    def test_10_candidate_evidence_identity_invariant(self):
        """Strict Invariant Check: candidate_standard == evidence_standard for ALL non-null recommendations."""
        test_queries = [
            "Supply of 43 Grade Ordinary Portland Cement conforming to IS 269",
            "1100V grade PVC insulated copper cables conforming to IS 694",
            "Supply of precast concrete pipes for culvert works",
            "Supply of chlorinated polyvinyl chloride pipes conforming to IS 15778",
            "Supply of copper alloy gate valves conforming to IS 778"
        ]
        for query in test_queries:
            res = self.recommender.recommend_for_text(query)
            if res.candidate_standard is not None:
                self.assertEqual(
                    res.candidate_standard,
                    res.evidence_standard,
                    f"Candidate standard '{res.candidate_standard}' must identically match evidence standard '{res.evidence_standard}'."
                )


    def test_11_api_ambiguity_contract(self):
        """API Contract: Ensure API responses include 6 ambiguity states, reasons, and ambiguity_summary."""
        from api.server import app
        client = app.test_client()
        resp = client.post("/api/analyze/text", json={
            "text": "Supply and installation of chlorinated polyvinyl chloride (CPVC) pipes conforming to IS 15778."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("summary", data)
        self.assertIn("ambiguity_summary", data["summary"])
        amb_sum = data["summary"]["ambiguity_summary"]
        self.assertIn("clear", amb_sum)
        self.assertIn("incomplete", amb_sum)
        self.assertIn("ambiguous", amb_sum)
        self.assertIn("conflicting", amb_sum)
        self.assertIn("no_reliable_match", amb_sum)
        self.assertIn("review_required", amb_sum)

        all_reqs = data.get("requirements", [])
        self.assertTrue(len(all_reqs) >= 1)
        r0 = all_reqs[0]
        self.assertIn("ambiguity_state", r0)
        self.assertIn("ambiguity_reason", r0)
        self.assertIn("retrieval_status", r0)
        self.assertIn("applicability_status", r0)
        self.assertIn("evidence_status", r0)
        self.assertIn("competing_interpretations", r0)
        self.assertEqual(r0["ambiguity_state"], "CLEAR")


if __name__ == "__main__":
    unittest.main()
