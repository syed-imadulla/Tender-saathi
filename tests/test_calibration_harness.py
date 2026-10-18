"""
tests/test_calibration_harness.py — Unit tests for Phase 14 calibration infrastructure.

Verifies:
1. Split integrity and leakage freedom (strictly disjoint tenders across splits).
2. Small dataset splitting safeguards (graceful handling when tenders < 3).
3. Wilson confidence interval calculation with known hand-calculated bounds.
4. Threshold trial isolation without mutating production defaults.
5. Cohort categorization across the 7 calibration groups.
6. Safety gate verification and blocking rule when adjudicated under-specified cases < 5.
"""

import unittest
from typing import Dict, Any, List

from src.calibrate import (
    CalibrationConfig,
    TenderSplitter,
    RequirementCategorizer,
    calculate_wilson_interval,
    OfflineCalibrationRunner
)
from src.applicability import ApplicabilityGate
from src.standards import StandardsDatabase


class TestCalibrationHarness(unittest.TestCase):

    def test_01_wilson_confidence_interval_bounds(self):
        """1. Verify Wilson score intervals with known hand calculations and edge cases."""
        # A. 0 total cases
        lower, upper = calculate_wilson_interval(0, 0)
        self.assertIsNone(lower)
        self.assertIsNone(upper)

        # B. 10 successes out of 20 trials (50% empirical)
        # Wilson 95% CI for p=0.5, n=20 is approx [29.9%, 70.1%]
        lower, upper = calculate_wilson_interval(10, 20)
        self.assertAlmostEqual(lower, 29.9, delta=0.5)
        self.assertAlmostEqual(upper, 70.1, delta=0.5)

        # C. 17 successes out of 19 trials (89.5% empirical)
        lower, upper = calculate_wilson_interval(17, 19)
        self.assertAlmostEqual(lower, 68.6, delta=1.0)
        self.assertAlmostEqual(upper, 97.1, delta=1.0)

    def test_02_tender_splitter_leakage_safety(self):
        """2. Verify that TenderSplitter enforces strict disjointness across train, val, and test splits."""
        cases = [
            {"requirement_id": "T001-R01", "tender_id": "T001"},
            {"requirement_id": "T001-R02", "tender_id": "T001"},
            {"requirement_id": "T002-R01", "tender_id": "T002"},
            {"requirement_id": "T002-R02", "tender_id": "T002"},
            {"requirement_id": "T003-R01", "tender_id": "T003"},
            {"requirement_id": "T004-R01", "tender_id": "T004"},
            {"requirement_id": "T005-R01", "tender_id": "T005"},
            {"requirement_id": "T006-R01", "tender_id": "T006"},
        ]

        result = TenderSplitter.split(cases, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25, seed=42)
        audit = result["leakage_audit"]

        self.assertTrue(audit["is_leakage_free"], "Splits MUST be strictly disjoint!")

        train_t = set(audit["train_tenders"])
        val_t = set(audit["val_tenders"])
        test_t = set(audit["test_tenders"])

        self.assertTrue(train_t.isdisjoint(val_t))
        self.assertTrue(train_t.isdisjoint(test_t))
        self.assertTrue(val_t.isdisjoint(test_t))

        # Check case distribution
        for c in result["train"]:
            self.assertIn(c["tender_id"], train_t)
        for c in result["val"]:
            self.assertIn(c["tender_id"], val_t)
        for c in result["test"]:
            self.assertIn(c["tender_id"], test_t)

    def test_03_tender_splitter_too_few_tenders_warning(self):
        """3. Verify graceful handling and warning when dataset contains fewer than 3 tenders."""
        cases = [
            {"requirement_id": "T001-R01", "tender_id": "T001"},
            {"requirement_id": "T002-R01", "tender_id": "T002"}
        ]
        result = TenderSplitter.split(cases)
        self.assertEqual(len(result["val"]), 0)
        self.assertEqual(len(result["test"]), 0)
        self.assertIn("warning", result["metadata"])

    def test_04_cohort_categorization(self):
        """4. Verify that requirements are classified into the 7 distinct evaluation cohorts."""
        test_cases = [
            # 1. Distractor probe
            ({"requirement_id": "NEG-002", "test_type": "DISTRACTOR_PROBE"}, "RETRIEVAL_DISTRACTOR_PROBE"),
            # 2. Open set ineligible
            ({"requirement_id": "NEG-004", "expected_decision": "REJECT_INELIGIBLE"}, "OPEN_SET_INELIGIBLE"),
            # 3. Under specified
            ({"requirement_id": "T002-R002", "expected_decision": "ABSTAIN_UNDER_SPECIFIED"}, "UNDER_SPECIFIED"),
            # 4. Ambiguous competing
            ({"requirement_id": "T002-R001", "reasoning": "Multiple competing Indian Standards IS 14846 and IS/ISO 10434"}, "AMBIGUOUS_COMPETING"),
            # 5. Compound
            ({"requirement_id": "T001-R002", "applicable_standard": "IS 15905 : 2011; IS 1239 (Part 1) : 2004"}, "ANSWERABLE_IN_DOMAIN_COMPOUND"),
            # 6. Lifecycle
            ({"requirement_id": "T001-R003", "applicable_standard": "IS 15622 : 2017"}, "LIFECYCLE_EDITION_SENSITIVE"),
            # 7. Single standard
            ({"requirement_id": "T006-R001", "applicable_standard": "IS 16088 : 2016"}, "ANSWERABLE_IN_DOMAIN_SINGLE"),
        ]

        for case_data, expected_cohort in test_cases:
            cohort = RequirementCategorizer.classify(case_data)
            self.assertEqual(cohort, expected_cohort, f"Failed for {case_data}")

    def test_05_threshold_isolation_does_not_mutate_defaults(self):
        """5. Candidate threshold configurations must NOT mutate production defaults."""
        default_gate = ApplicabilityGate()
        self.assertEqual(default_gate.applicability_threshold, 0.60)
        self.assertEqual(default_gate.review_threshold, 0.35)

        # Run an experiment with candidate thresholds
        candidate_config = CalibrationConfig(
            experiment_id="candidate_sweep_01",
            applicability_threshold=0.75,
            review_threshold=0.45,
            separation_threshold=0.18
        )

        runner = OfflineCalibrationRunner()
        recommender = runner.build_candidate_recommender(candidate_config)


        # Candidate recommender has custom thresholds
        self.assertEqual(recommender.applicability_gate.applicability_threshold, 0.75)
        self.assertEqual(recommender.applicability_gate.review_threshold, 0.45)
        self.assertEqual(recommender.ambiguity_engine.separation_threshold, 0.18)

        # Fresh default gate still has pristine production defaults
        pristine_gate = ApplicabilityGate()
        self.assertEqual(pristine_gate.applicability_threshold, 0.60)
        self.assertEqual(pristine_gate.review_threshold, 0.35)

    def test_06_safety_gates_and_readiness_verdict(self):
        """6. Calibration verdict MUST be NOT READY when adjudicated under-specified cases < 5."""
        runner = OfflineCalibrationRunner()
        config = CalibrationConfig()

        # Synthetic dataset with 0 adjudicated cases
        mock_cases = [
            {
                "requirement_id": "T001-R001",
                "tender_id": "T001",
                "requirement_text": "Supply and laying of CPVC pipes conforming to IS 15778.",
                "applicable_standard": "IS 15778 : 2007",
                "expected_decision": "RECOMMEND",
                "human_verified": "FALSE"
            },
            {
                "requirement_id": "T002-R002",
                "tender_id": "T002",
                "requirement_text": "Valve Replacement",
                "applicable_standard": "",
                "expected_decision": "ABSTAIN_UNDER_SPECIFIED",
                "human_verified": "FALSE"  # Unverified!
            }
        ]

        result = runner.evaluate_configuration(config, mock_cases)
        safety_gates = result["safety_gates"]

        # Prerequisite gate must fail
        self.assertFalse(safety_gates["gate_adjudicated_under_spec_prerequisite"]["passed"])
        self.assertEqual(safety_gates["calibration_readiness_verdict"], "NOT READY FOR CALIBRATION")


if __name__ == "__main__":
    unittest.main()
