"""
tests/test_evaluation_metrics.py

Synthetic, deterministic unit tests for Tender Saathi's multi-metric evaluation harness.
Verifies hand-calculated metric formulas, selective classification, non-conflation of abstentions,
negative control safety, permutation invariance, and empty denominator resilience.
Part of Phase 12 (Plan 12-02).
"""

import copy
import json
import random
import unittest
from src.evaluate import compute_deconflated_metrics


class TestEvaluationMetrics(unittest.TestCase):
    """Deterministic tests for decoupled evaluation metrics calculation."""

    def test_01_hand_calculated_retrieval_ranking(self):
        """
        1. Verify Top-1, Top-3, and MRR calculations with known, hand-calculated values.
        
        Setup: 4 Answerable Cases:
        - Case 1: Top-1 match (rank 1, rr = 1.0)
        - Case 2: Top-2 match (rank 2, rr = 0.5)
        - Case 3: Top-3 match (rank 3, rr = 0.333333...)
        - Case 4: Miss (rank 0, rr = 0.0)
        
        Hand calculations:
        - Total Answerable = 4
        - Top-1 Hits = 1 -> 1/4 = 25.0%
        - Top-3 Hits = 3 -> 3/4 = 75.0%
        - MRR = (1.0 + 0.5 + 1/3 + 0.0) / 4 = 1.833333... / 4 = 0.458333... -> 0.458
        """
        cases = [
            {
                "requirement_id": "C1",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": True,
                "is_top3_hit": True,
                "reciprocal_rank": 1.0,
                "system_decision": "RECOMMEND",
                "predicted_top1": "IS 15905",
                "procurement_sector": "PROVISIONAL:CIVIL"
            },
            {
                "requirement_id": "C2",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": False,
                "is_top3_hit": True,
                "reciprocal_rank": 0.5,
                "system_decision": "RECOMMEND",
                "predicted_top1": "IS 456",
                "procurement_sector": "PROVISIONAL:CIVIL"
            },
            {
                "requirement_id": "C3",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": False,
                "is_top3_hit": True,
                "reciprocal_rank": 1.0 / 3.0,
                "system_decision": "RECOMMEND",
                "predicted_top1": "IS 1239",
                "procurement_sector": "PROVISIONAL:CIVIL"
            },
            {
                "requirement_id": "C4",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": False,
                "is_top3_hit": False,
                "reciprocal_rank": 0.0,
                "system_decision": "RECOMMEND",
                "predicted_top1": "IS 778",
                "procurement_sector": "PROVISIONAL:CIVIL"
            },
        ]

        metrics = compute_deconflated_metrics(cases)
        ret = metrics["retrieval_answerable"]

        self.assertEqual(ret["total_answerable"], 4)
        self.assertEqual(ret["top1_hits"], 1)
        self.assertEqual(ret["top1_accuracy_percent"], 25.0)
        self.assertEqual(ret["top3_hits"], 3)
        self.assertEqual(ret["top3_accuracy_percent"], 75.0)
        self.assertAlmostEqual(ret["mrr"], 0.458, places=3)

    def test_02_critical_abstention_never_counted_as_retrieval_hit(self):
        """
        2. CRITICAL ANTI-CONFLATION TEST:
        An abstention on an under-specified case MUST NOT be counted as a retrieval hit!
        
        Setup:
        - 2 Answerable cases: 1 Top-1 Hit, 1 Miss (pred=None, abstained).
        - 1 Under-specified case: Correctly abstained (safe_abstention=True).
        
        Decoupled metric expected:
        - Answerable total = 2
        - Answerable Top-1 accuracy = 1 / 2 = 50.0%
        - Under-spec abstention recall = 1 / 1 = 100.0%
        
        If conflated (legacy bug):
        - Answerable would erroneously include the under-specified case (1 + 1) / 3 = 66.7%!
        """
        cases = [
            {
                "requirement_id": "ANS-01",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": True,
                "is_top3_hit": True,
                "reciprocal_rank": 1.0,
                "system_decision": "RECOMMEND",
                "predicted_top1": "IS 15905"
            },
            {
                "requirement_id": "ANS-02",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": False,
                "is_top3_hit": False,
                "reciprocal_rank": 0.0,
                "system_decision": "REVIEW_REQUIRED",
                "predicted_top1": None,
                "is_safe_abstention": True
            },
            {
                "requirement_id": "UNDER-01",
                "expected_decision": "ABSTAIN_UNDER_SPECIFIED",
                "is_top1_hit": False,  # MUST NOT BE MARKED AS HIT
                "is_top3_hit": False,
                "reciprocal_rank": 0.0,
                "system_decision": "REVIEW_REQUIRED",
                "predicted_top1": None,
                "is_safe_abstention": True
            }
        ]

        metrics = compute_deconflated_metrics(cases)
        ret = metrics["retrieval_answerable"]
        abs_q = metrics["abstention_quality"]

        # Verification of strict de-conflation
        self.assertEqual(ret["total_answerable"], 2, "Under-specified case must not enter answerable denominator!")
        self.assertEqual(ret["top1_hits"], 1, "Under-specified abstention must not count as a retrieval hit!")
        self.assertEqual(ret["top1_accuracy_percent"], 50.0)
        self.assertNotEqual(ret["top1_accuracy_percent"], 66.67, "FATAL: Abstention was conflated as Top-1 hit!")

        self.assertEqual(abs_q["under_specified_count"], 1)
        self.assertEqual(abs_q["safe_abstained_count"], 1)
        self.assertEqual(abs_q["under_specified_abstention_recall_percent"], 100.0)

    def test_03_selective_classification_coverage_and_risk(self):
        """
        3. Verify Coverage and Selective Risk formulas with hand-calculated values.
        
        Setup: 5 Queries total
        - Case 1: Answerable, Covered (decision=RECOMMEND), Top-1 Hit.
        - Case 2: Answerable, Covered (decision=RECOMMEND), Top-1 Hit.
        - Case 3: Answerable, Covered (decision=RECOMMEND), Top-1 Miss (INCORRECT!).
        - Case 4: Answerable, Abstained (decision=REVIEW_REQUIRED, pred=None).
        - Case 5: Under-specified, Abstained (decision=REVIEW_REQUIRED, pred=None).
        
        Hand calculations:
        - Total eligible = 5
        - Covered cases = 3 (Cases 1, 2, 3)
        - Coverage = 3 / 5 = 60.0%
        - Incorrect among covered = 1 (Case 3)
        - Selective Risk = 1 / 3 = 33.33%
        """
        cases = [
            {"requirement_id": "Q1", "expected_decision": "RECOMMEND", "system_decision": "RECOMMEND", "predicted_top1": "IS 100", "is_top1_hit": True},
            {"requirement_id": "Q2", "expected_decision": "RECOMMEND", "system_decision": "RECOMMEND", "predicted_top1": "IS 200", "is_top1_hit": True},
            {"requirement_id": "Q3", "expected_decision": "RECOMMEND", "system_decision": "RECOMMEND", "predicted_top1": "IS 999", "is_top1_hit": False},
            {"requirement_id": "Q4", "expected_decision": "RECOMMEND", "system_decision": "REVIEW_REQUIRED", "predicted_top1": None, "is_top1_hit": False},
            {"requirement_id": "Q5", "expected_decision": "ABSTAIN_UNDER_SPECIFIED", "system_decision": "REVIEW_REQUIRED", "predicted_top1": None, "is_top1_hit": False},
        ]

        metrics = compute_deconflated_metrics(cases)
        sel = metrics["selective_classification"]

        self.assertEqual(sel["total_eligible"], 5)
        self.assertEqual(sel["covered_count"], 3)
        self.assertEqual(sel["coverage_percent"], 60.0)
        self.assertEqual(sel["incorrect_covered_count"], 1)
        self.assertAlmostEqual(sel["selective_risk_percent"], 33.33, places=2)

    def test_04_negative_control_false_recommendation_rate(self):
        """
        4. Verify Negative Control False Recommendation Rate and Safe Rejection Rate.
        
        Setup: 4 Negative control queries:
        - Neg 1: Safe rejection (abstained, pred=None)
        - Neg 2: Safe rejection (abstained, pred=None)
        - Neg 3: Safe rejection (abstained, pred=None)
        - Neg 4: Hallucinated recommendation! (system_decision=RECOMMEND, pred="IS 778")
        
        Hand calculations:
        - Total negative queries = 4
        - False recommendations = 1
        - False Recommendation Rate = 1 / 4 = 25.0%
        - Negative Rejection Rate = 3 / 4 = 75.0%
        """
        cases = [
            {"requirement_id": "NEG-1", "expected_decision": "REJECT_INELIGIBLE", "system_decision": "INSUFFICIENT_EVIDENCE", "predicted_top1": None},
            {"requirement_id": "NEG-2", "expected_decision": "REJECT_INELIGIBLE", "system_decision": "INSUFFICIENT_EVIDENCE", "predicted_top1": None},
            {"requirement_id": "NEG-3", "expected_decision": "REJECT_INELIGIBLE", "system_decision": "REVIEW_REQUIRED", "predicted_top1": None},
            {"requirement_id": "NEG-4", "expected_decision": "REJECT_INELIGIBLE", "system_decision": "RECOMMEND", "predicted_top1": "IS 778"},
        ]

        metrics = compute_deconflated_metrics(cases)
        neg = metrics["negative_control"]

        self.assertEqual(neg["total_negative_cases"], 4)
        self.assertEqual(neg["false_recommendation_count"], 1)
        self.assertEqual(neg["false_recommendation_rate_percent"], 25.0)
        self.assertEqual(neg["negative_rejection_rate_percent"], 75.0)

    def test_05_empty_denominators_resilience(self):
        """5. Verify zero division handling and graceful defaults for empty datasets or subgroups."""
        # A. Completely empty dataset
        empty_metrics = compute_deconflated_metrics([])
        self.assertEqual(empty_metrics["retrieval_answerable"]["total_answerable"], 0)
        self.assertEqual(empty_metrics["retrieval_answerable"]["top1_accuracy_percent"], 0.0)
        self.assertEqual(empty_metrics["selective_classification"]["coverage_percent"], 0.0)
        self.assertEqual(empty_metrics["selective_classification"]["selective_risk_percent"], 0.0)
        self.assertEqual(empty_metrics["abstention_quality"]["under_specified_count"], 0)
        self.assertEqual(empty_metrics["negative_control"]["total_negative_cases"], 0)

        # B. Dataset with only under-specified cases (0 answerable queries)
        only_under = [
            {"requirement_id": "U1", "expected_decision": "ABSTAIN_UNDER_SPECIFIED", "is_safe_abstention": True, "system_decision": "REVIEW_REQUIRED", "predicted_top1": None}
        ]
        u_metrics = compute_deconflated_metrics(only_under)
        self.assertEqual(u_metrics["retrieval_answerable"]["total_answerable"], 0)
        self.assertEqual(u_metrics["retrieval_answerable"]["top1_accuracy_percent"], 0.0)
        self.assertEqual(u_metrics["abstention_quality"]["under_specified_count"], 1)
        self.assertEqual(u_metrics["abstention_quality"]["under_specified_abstention_recall_percent"], 100.0)

    def test_06_evidence_grounding_status_and_limitations_disclosure(self):
        """6. Verify evidence limitations disclosure and catalogue consistency calculations."""
        cases = [
            {
                "requirement_id": "A1",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": True,
                "status_consistent": True,
                "evidence_proxy_score": 80.0
            },
            {
                "requirement_id": "A2",
                "expected_decision": "RECOMMEND",
                "is_top1_hit": True,
                "status_consistent": False,
                "evidence_proxy_score": 40.0
            },
        ]
        metrics = compute_deconflated_metrics(cases)
        ev = metrics["evidence_grounding"]

        self.assertEqual(ev["top1_evaluated_count"], 2)
        self.assertEqual(ev["catalogue_status_consistency_rate_percent"], 50.0)
        self.assertEqual(ev["clause_grounding_status"], "NOT_EVALUABLE_NO_FULL_TEXT_CORPUS")
        self.assertIn("Tender Saathi's catalogue database stores standard numbers", ev["limitations_disclosure"])
        self.assertEqual(ev["proxy_evidence_reference_overlap_percent"], 60.0)

    def test_07_sector_stratification_preserves_provisional_tagging(self):
        """7. Verify per-sector aggregation preserves PROVISIONAL: prefix and accurately tallies subgroups."""
        cases = [
            {"requirement_id": "S1", "procurement_sector": "PROVISIONAL:CIVIL_WORKS", "expected_decision": "RECOMMEND", "is_top1_hit": True, "is_top3_hit": True, "reciprocal_rank": 1.0},
            {"requirement_id": "S2", "procurement_sector": "PROVISIONAL:CIVIL_WORKS", "expected_decision": "RECOMMEND", "is_top1_hit": False, "is_top3_hit": True, "reciprocal_rank": 0.5},
            {"requirement_id": "S3", "procurement_sector": "PROVISIONAL:ELECTRICAL", "expected_decision": "RECOMMEND", "is_top1_hit": True, "is_top3_hit": True, "reciprocal_rank": 1.0},
            {"requirement_id": "S4", "procurement_sector": "PROVISIONAL:ELECTRICAL", "expected_decision": "ABSTAIN_UNDER_SPECIFIED", "is_top1_hit": False, "is_top3_hit": False, "reciprocal_rank": 0.0},
            {"requirement_id": "S5", "procurement_sector": "UNKNOWN", "expected_decision": "RECOMMEND", "is_top1_hit": False, "is_top3_hit": False, "reciprocal_rank": 0.0},
        ]

        metrics = compute_deconflated_metrics(cases)
        sec = metrics["sector_stratification"]

        self.assertIn("PROVISIONAL:CIVIL_WORKS", sec)
        self.assertIn("PROVISIONAL:ELECTRICAL", sec)
        self.assertIn("UNKNOWN", sec)

        # Civil: 2 sample, 2 answerable, 1 top1 (50%), 2 top3 (100%), MRR = 0.75
        self.assertEqual(sec["PROVISIONAL:CIVIL_WORKS"]["sample_size"], 2)
        self.assertEqual(sec["PROVISIONAL:CIVIL_WORKS"]["answerable_count"], 2)
        self.assertEqual(sec["PROVISIONAL:CIVIL_WORKS"]["top1_accuracy"], 50.0)
        self.assertEqual(sec["PROVISIONAL:CIVIL_WORKS"]["top3_accuracy"], 100.0)
        self.assertEqual(sec["PROVISIONAL:CIVIL_WORKS"]["mrr"], 0.75)

        # Electrical: 2 sample, 1 answerable, 1 top1 (100%), MRR = 1.0
        self.assertEqual(sec["PROVISIONAL:ELECTRICAL"]["sample_size"], 2)
        self.assertEqual(sec["PROVISIONAL:ELECTRICAL"]["answerable_count"], 1)
        self.assertEqual(sec["PROVISIONAL:ELECTRICAL"]["top1_accuracy"], 100.0)
        self.assertEqual(sec["PROVISIONAL:ELECTRICAL"]["mrr"], 1.0)

    def test_08_permutation_invariance(self):
        """8. Verify metric calculations are strictly invariant to row permutation / ordering."""
        cases = [
            {"requirement_id": "R1", "expected_decision": "RECOMMEND", "is_top1_hit": True, "is_top3_hit": True, "reciprocal_rank": 1.0, "system_decision": "RECOMMEND", "predicted_top1": "IS 1"},
            {"requirement_id": "R2", "expected_decision": "RECOMMEND", "is_top1_hit": False, "is_top3_hit": True, "reciprocal_rank": 0.5, "system_decision": "RECOMMEND", "predicted_top1": "IS 2"},
            {"requirement_id": "R3", "expected_decision": "RECOMMEND", "is_top1_hit": False, "is_top3_hit": False, "reciprocal_rank": 0.0, "system_decision": "REVIEW_REQUIRED", "predicted_top1": None},
            {"requirement_id": "R4", "expected_decision": "ABSTAIN_UNDER_SPECIFIED", "is_safe_abstention": True, "system_decision": "REVIEW_REQUIRED", "predicted_top1": None},
            {"requirement_id": "R5", "expected_decision": "REJECT_INELIGIBLE", "system_decision": "INSUFFICIENT_EVIDENCE", "predicted_top1": None},
            {"requirement_id": "R6", "expected_decision": "REJECT_INELIGIBLE", "system_decision": "RECOMMEND", "predicted_top1": "IS 999"},
        ]

        metrics_orig = compute_deconflated_metrics(cases)

        # Reverse
        cases_reversed = list(reversed(cases))
        metrics_rev = compute_deconflated_metrics(cases_reversed)

        # Shuffle with fixed seed
        cases_shuffled = copy.deepcopy(cases)
        random.seed(42)
        random.shuffle(cases_shuffled)
        metrics_shuf = compute_deconflated_metrics(cases_shuffled)

        # Assert equivalence
        for m in [metrics_rev, metrics_shuf]:
            self.assertEqual(metrics_orig["retrieval_answerable"], m["retrieval_answerable"])
            self.assertEqual(metrics_orig["selective_classification"], m["selective_classification"])
            self.assertEqual(metrics_orig["abstention_quality"], m["abstention_quality"])
            self.assertEqual(metrics_orig["negative_control"], m["negative_control"])


if __name__ == "__main__":
    unittest.main()
