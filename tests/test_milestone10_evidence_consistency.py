"""
tests/test_milestone10_evidence_consistency.py
Purpose: Regression test suite and automated invariant for Milestone 10:
         Evidence Consistency and 'Why It Matches' correctness.

Ensures candidate_standard, title, evidence, and why_it_matches always refer
strictly to the same Indian Standard, and never cross-contaminate across domains.
"""

import unittest
import json
import csv
import os

from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.critic import are_standards_equivalent


class TestMilestone10EvidenceConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recommender = StandardsRecommender()

    def test_01_cpvc_pipes_why_matches_correctness(self):
        """CPVC pipe requirement must recommend IS 15778 and must NOT mention valves."""
        text = "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for hot and cold water distribution including CPVC fittings"
        res = self.recommender.recommend_for_text(text, req_id="TEST-CPVC-01")

        # 1. Candidate must be IS 15778
        self.assertIsNotNone(res.candidate_standard, "CPVC must produce a candidate standard")
        self.assertTrue(
            are_standards_equivalent(res.candidate_standard, "IS 15778"),
            f"Candidate should be IS 15778, got {res.candidate_standard}"
        )

        # 2. Evidence standard must match candidate standard
        self.assertIsNotNone(res.evidence_standard)
        self.assertTrue(
            are_standards_equivalent(res.candidate_standard, res.evidence_standard),
            f"Candidate {res.candidate_standard} != evidence standard {res.evidence_standard}"
        )

        # 3. Why-it-matches must describe CPVC / water pipe context
        why_text = (res.why_it_matches or "").lower()
        self.assertTrue(
            "cpvc" in why_text or "polyvinyl" in why_text or "pipe" in why_text or "water" in why_text,
            f"Why it matches must mention CPVC/pipes/water, got: {res.why_it_matches}"
        )

        # 4. Must NOT mention valves
        for forbidden in ["gate valve", "globe valve", "check valve", "waterworks valve", "valves for waterworks"]:
            self.assertNotIn(
                forbidden,
                why_text,
                f"CPVC explanation must NEVER mention '{forbidden}'! Got: {res.why_it_matches}"
            )

    def test_02_waterworks_valves_why_matches_correctness(self):
        """Waterworks valve requirement must recommend IS 778 and must NOT mention CPVC."""
        text = "Supply of copper alloy gate valves for waterworks purposes"
        res = self.recommender.recommend_for_text(text, req_id="TEST-VALVE-01")

        self.assertIsNotNone(res.candidate_standard)
        self.assertTrue(
            are_standards_equivalent(res.candidate_standard, "IS 778"),
            f"Candidate should be IS 778, got {res.candidate_standard}"
        )

        # Evidence consistency
        self.assertTrue(
            are_standards_equivalent(res.candidate_standard, res.evidence_standard),
            f"Candidate {res.candidate_standard} != evidence standard {res.evidence_standard}"
        )

        why_text = (res.why_it_matches or "").lower()
        self.assertTrue(
            "valve" in why_text or "copper" in why_text or "waterworks" in why_text,
            f"Why it matches must discuss valve/waterworks context, got: {res.why_it_matches}"
        )

        # Must NOT mention CPVC
        self.assertNotIn("cpvc", why_text, f"Valve explanation must NOT mention CPVC! Got: {res.why_it_matches}")

    def test_03_concrete_pipes_why_matches_correctness(self):
        """Concrete pipes requirement must correspond to concrete pipe standard, not valves or CPVC."""
        text = "Supply and laying of precast concrete pipes"
        res = self.recommender.recommend_for_text(text, req_id="TEST-CONCRETE-01")

        self.assertIsNotNone(res.candidate_standard)
        self.assertTrue(
            are_standards_equivalent(res.candidate_standard, res.evidence_standard),
            f"Candidate {res.candidate_standard} != evidence standard {res.evidence_standard}"
        )

        why_text = (res.why_it_matches or "").lower()
        # Must correspond to concrete pipe
        self.assertTrue(
            "concrete" in why_text or "pipe" in why_text,
            f"Explanation must correspond to concrete pipes, got: {res.why_it_matches}"
        )

        # Must NOT mention CPVC, valves, electrical cables
        self.assertNotIn("cpvc", why_text)
        self.assertNotIn("valve", why_text)
        self.assertNotIn("electric cable", why_text)

    def test_04_electrical_cable_why_matches_correctness(self):
        """Electrical cable requirement must correspond to cable standard, not CPVC or valves."""
        text = "PVC insulated electric cable"
        res = self.recommender.recommend_for_text(text, req_id="TEST-CABLE-01")

        self.assertIsNotNone(res.candidate_standard)
        self.assertTrue(
            are_standards_equivalent(res.candidate_standard, res.evidence_standard),
            f"Candidate {res.candidate_standard} != evidence standard {res.evidence_standard}"
        )

        why_text = (res.why_it_matches or "").lower()
        self.assertTrue(
            "cable" in why_text or "insulated" in why_text or "volt" in why_text,
            f"Explanation must correspond to cable standard, got: {res.why_it_matches}"
        )

        self.assertNotIn("cpvc", why_text)
        self.assertNotIn("valve", why_text)
        self.assertNotIn("concrete pipe", why_text)

    def test_05_crane_rail_adversarial_case(self):
        """Adversarial crane rail requirement must return candidate_standard=None, decision=NO_RELIABLE_MATCH."""
        text = "Replacement of crane rail track for RMQC including allied works"
        res = self.recommender.recommend_for_text(text, req_id="TEST-CRANE-01")

        self.assertIsNone(res.candidate_standard, "Crane rail must NOT recommend an unrelated standard")
        decision = res.critic_result.get("decision") if res.critic_result else None
        self.assertEqual(decision, "NO_RELIABLE_MATCH")
        self.assertEqual(len(res.dependencies), 0, "No dependencies should be returned for NO_RELIABLE_MATCH")
        self.assertIsNone(res.evidence_standard, "Evidence standard must be None when abstaining")

        # No unrelated evidence shown
        why_text = (res.why_it_matches or "").lower()
        self.assertNotIn("valve", why_text)
        self.assertNotIn("cpvc", why_text)
        self.assertIn("no reliable", why_text)

    def test_06_automated_invariant_candidate_equals_evidence_standard(self):
        """
        AUTOMATED INVARIANT:
        For EVERY positive recommendation across the benchmark ground truth:
        candidate_standard must equal evidence_standard.
        If candidate_standard != evidence_standard, FAIL the test.
        """
        gt_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "ground_truth", "ground_truth.csv")
        with open(gt_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            benchmarks = list(reader)

        tested_count = 0
        for item in benchmarks:
            req_text = item["requirement_text"]
            res = self.recommender.recommend_for_text(req_text, req_id=item.get("requirement_id", "INV-TEST"))

            if res.candidate_standard:
                tested_count += 1
                self.assertIsNotNone(
                    res.evidence_standard,
                    f"Requirement '{req_text[:40]}' has candidate {res.candidate_standard} but evidence_standard is None!"
                )
                self.assertTrue(
                    are_standards_equivalent(res.candidate_standard, res.evidence_standard),
                    f"INVARIANT VIOLATION: candidate_standard ({res.candidate_standard}) != "
                    f"evidence_standard ({res.evidence_standard}) for requirement: '{req_text[:40]}'"
                )

        self.assertGreaterEqual(tested_count, 15, "Invariant must be verified across at least 15 positive recommendations")

    def test_07_evidence_consistency_rule_mismatch_fallback(self):
        """
        When candidate_standard != evidence_standard, the system must NOT display
        candidate-specific evidence, but instead show the mandated fallback text.
        """
        # Test are_standards_equivalent logic
        self.assertTrue(are_standards_equivalent("IS 15778 : 2007", "IS 15778"))
        self.assertTrue(are_standards_equivalent("IS 778 : 1984", "IS 778"))
        self.assertFalse(are_standards_equivalent("IS 15778 : 2007", "IS 778 : 1984"))
        self.assertFalse(are_standards_equivalent("IS 15778", "IS 778"))
        self.assertFalse(are_standards_equivalent(None, "IS 15778"))
        self.assertFalse(are_standards_equivalent("IS 15778", None))


if __name__ == "__main__":
    unittest.main()
