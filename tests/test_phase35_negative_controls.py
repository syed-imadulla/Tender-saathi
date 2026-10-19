# tests/test_phase35_negative_controls.py — Phase 35 Negative-Control Evaluation Suite
import json
import hashlib
import os
import unittest
from pathlib import Path

from src.recommend import StandardsRecommender
from src.standards import StandardsDatabase


EXPECTED_GROUND_TRUTH_SHA256 = "8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc"


class TestPhase35NegativeControls(unittest.TestCase):
    """
    Evaluates Tender Saathi against 12 negative-control probes covering commercial terms,
    vague commodities, missing essential parameters, conflicting specifications,
    withdrawn standards, and IT services.

    Safety Invariant:
    1. Zero false recommendations (0 RECOMMEND decisions on negative controls).
    2. Safe abstention or explicit human review required.
    3. Ground truth checksum is strictly preserved.
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture_path = Path("dataset/evaluation/phase35_negative_controls.json")
        with open(cls.fixture_path, "r", encoding="utf-8") as f:
            cls.fixture = json.load(f)
        cls.recommender = StandardsRecommender()

    def test_01_ground_truth_checksum_immutability(self):
        """Verify ground_truth.csv was not modified or adulterated by test fixtures."""
        gt_path = Path("dataset/ground_truth/ground_truth.csv")
        self.assertTrue(gt_path.exists(), "ground_truth.csv must exist")
        sha256 = hashlib.sha256(gt_path.read_bytes()).hexdigest()
        self.assertEqual(
            sha256,
            EXPECTED_GROUND_TRUTH_SHA256,
            f"Ground truth checksum changed! Expected {EXPECTED_GROUND_TRUTH_SHA256}, got {sha256}"
        )

    def test_02_negative_controls_zero_false_recommendations(self):
        """All 12 negative control probes must result in safe abstention or review required."""
        probes = self.fixture["probes"]
        self.assertGreaterEqual(len(probes), 10, "Phase 35 requires >= 10 negative control probes")

        false_recommendations = []
        abstention_counts = 0
        review_required_counts = 0

        for probe in probes:
            case_id = probe["case_id"]
            text = probe["requirement_text"]
            forbidden = probe.get("forbidden_candidate_standards", [])

            rec = self.recommender.recommend_for_text(text)

            crit = getattr(rec, "critic_result", None) or {}
            decision = crit.get("decision") or "REVIEW_REQUIRED"

            # Check for false recommendation:
            # A false recommendation is when decision == 'RECOMMEND' and human_review_required is False
            is_recommend = (decision == "RECOMMEND" and not rec.human_review_required)
            candidate = rec.candidate_standard

            if is_recommend:
                false_recommendations.append({
                    "case_id": case_id,
                    "candidate": candidate,
                    "decision": decision,
                    "confidence": rec.confidence,
                })

            # Check forbidden candidates
            if candidate and forbidden:
                for f_std in forbidden:
                    self.assertNotIn(
                        f_std.lower().replace(" ", ""),
                        candidate.lower().replace(" ", ""),
                        f"Probe {case_id} recommended forbidden standard {f_std} (got {candidate})"
                    )

            # Safe outcome check: candidate is None, or human_review_required is True, or non-RECOMMEND decision
            is_safe = (
                rec.candidate_standard is None or
                rec.human_review_required or
                decision in ("REVIEW_REQUIRED", "NO_RELIABLE_MATCH", "INSUFFICIENT_EVIDENCE", "ABSTAIN_UNDER_SPECIFIED", "CONFLICTING")
            )

            self.assertTrue(
                is_safe,
                f"Probe {case_id} failed safe abstention invariant! Decision={decision}, Candidate={candidate}, ReviewReq={rec.human_review_required}"
            )

            if rec.candidate_standard is None:
                abstention_counts += 1
            if rec.human_review_required:
                review_required_counts += 1

        self.assertEqual(
            len(false_recommendations),
            0,
            f"Found {len(false_recommendations)} false recommendations on negative controls: {false_recommendations}"
        )

    def test_03_commercial_clauses_abstain(self):
        """Commercial advance, liquidated damages, and EMD must safely abstain or flag review."""
        comm_probes = [p for p in self.fixture["probes"] if p["category"] == "COMMERCIAL_TERMS"]
        self.assertEqual(len(comm_probes), 3)

        for p in comm_probes:
            rec = self.recommender.recommend_for_text(p["requirement_text"])
            crit = getattr(rec, "critic_result", None) or {}
            decision = crit.get("decision") or "REVIEW_REQUIRED"
            self.assertTrue(
                rec.candidate_standard is None or rec.human_review_required or decision != "RECOMMEND",
                f"Commercial clause {p['case_id']} did not safely abstain or flag review: {decision}"
            )

    def test_04_under_specified_clauses_require_review(self):
        """Missing essential parameters must not yield an unqualified RECOMMEND."""
        param_probes = [p for p in self.fixture["probes"] if p["category"] == "MISSING_ESSENTIAL_PARAMETERS"]
        self.assertGreaterEqual(len(param_probes), 2)

        for p in param_probes:
            rec = self.recommender.recommend_for_text(p["requirement_text"])
            crit = getattr(rec, "critic_result", None) or {}
            decision = crit.get("decision") or "REVIEW_REQUIRED"
            self.assertTrue(
                rec.human_review_required or rec.candidate_standard is None or decision != "RECOMMEND",
                f"Under-specified probe {p['case_id']} produced unflagged recommendation: {decision}"
            )


if __name__ == "__main__":
    unittest.main()
