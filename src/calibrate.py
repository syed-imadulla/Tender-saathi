"""
src/calibrate.py — Tender Saathi Offline Calibration & Validation Infrastructure

Enables reproducible, leakage-safe threshold calibration experiments without mutating
production defaults or global environment variables.

Core Capabilities:
1. CalibrationConfig: Immutable specification of candidate operational thresholds.
2. TenderSplitter: Leakage-safe grouped dataset partitioning strictly by tender_id.
3. CategoryAnalyzer: Fine-grained categorization of requirements into 7 distinct evaluation cohorts.
4. WilsonConfidenceInterval: Exact Wilson score confidence intervals for small-sample proportions.
5. OfflineCalibrationRunner: Isolated candidate evaluation, metric diffing, and safety gate checking.

Safety & Governance Invariants:
- Production thresholds are NEVER mutated by running experiments.
- Experiments run 100% offline without live LLM calls.
- Negative-control false positive rate must strictly remain 0.0%.
- Abstention threshold sweeps are BLOCKED unless at least 5 adjudicated under-specified cases exist.
"""

import os
import math
import copy
import json
import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Set

from src.standards import StandardsDatabase
from src.applicability import ApplicabilityGate
from src.ambiguity import AmbiguityEngine
from src.critic import EvidenceAwareCritic
from src.recommend import StandardsRecommender
from src.evaluate import (
    ComprehensiveEvaluationHarness,
    compute_deconflated_metrics,
    compute_dataset_sha256,
    extract_standard_tokens,
    NEGATIVE_BENCHMARK_CASES
)


# ---------------------------------------------------------------------------
# 1. Configuration Data Model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CalibrationConfig:
    """Immutable operational threshold parameters for an offline calibration trial."""
    experiment_id: str = "baseline"
    description: str = "Production baseline configuration"
    # Applicability Gate Thresholds
    applicability_threshold: float = 0.60
    review_threshold: float = 0.35
    # Ambiguity Engine Separation Threshold
    separation_threshold: float = 0.12
    # Critic & Trust Gate Thresholds
    min_relevance_threshold: float = 0.35
    min_evidence_score_recommend: float = 0.65
    critic_recommend_score: float = 0.70
    critic_assisted_score: float = 0.55
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 2. Wilson Score Confidence Interval Calculator
# ---------------------------------------------------------------------------

def calculate_wilson_interval(
    successes: int,
    total: int,
    confidence: float = 0.95
) -> Tuple[Optional[float], Optional[float]]:
    """
    Computes the Wilson score interval for a binomial proportion.
    Essential for small sample sizes ($N < 30$) where normal approximation fails.
    Returns (lower_bound_pct, upper_bound_pct) rounded to 1 decimal place.
    """
    if total <= 0:
        return (None, None)
    
    # z-value for confidence level
    z = 1.95996 if abs(confidence - 0.95) < 0.01 else 2.57583
    p = successes / total
    
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    margin = (z * math.sqrt((p * (1.0 - p) / total) + (z * z) / (4.0 * total * total))) / denom
    
    lower = max(0.0, (center - margin) * 100.0)
    upper = min(100.0, (center + margin) * 100.0)
    return (round(lower, 1), round(upper, 1))


# ---------------------------------------------------------------------------
# 3. Leakage-Safe Tender-Grouped Splitter
# ---------------------------------------------------------------------------

class TenderSplitter:
    """
    Splits procurement requirement cases into Train, Validation, and Test sets
    strictly grouped by tender_id to prevent intra-tender specification leakage.
    """

    @staticmethod
    def split(
        cases: List[Dict[str, Any]],
        train_ratio: float = 0.60,
        val_ratio: float = 0.20,
        test_ratio: float = 0.20,
        seed: int = 42
    ) -> Dict[str, Any]:
        import random
        
        # 1. Identify distinct tender IDs
        tender_to_cases: Dict[str, List[Dict[str, Any]]] = {}
        for c in cases:
            tid = c.get("tender_id") or "UNASSIGNED_TENDER"
            tender_to_cases.setdefault(tid, []).append(c)

        unique_tenders = sorted(list(tender_to_cases.keys()))
        rng = random.Random(seed)
        shuffled_tenders = list(unique_tenders)
        rng.shuffle(shuffled_tenders)

        n_tenders = len(shuffled_tenders)
        if n_tenders < 3:
            # Cannot safely form 3 disjoint non-empty splits with fewer than 3 tenders
            return {
                "train": cases,
                "val": [],
                "test": [],
                "metadata": {
                    "total_tenders": n_tenders,
                    "warning": "Dataset contains fewer than 3 unique tenders. 3-way disjoint splitting is statistically impossible."
                },
                "leakage_audit": {
                    "is_leakage_free": True,
                    "train_tenders": unique_tenders,
                    "val_tenders": [],
                    "test_tenders": []
                }
            }

        n_train = max(1, int(round(n_tenders * train_ratio)))
        n_val = max(1, int(round(n_tenders * val_ratio)))
        
        train_tenders = set(shuffled_tenders[:n_train])
        val_tenders = set(shuffled_tenders[n_train:n_train + n_val])
        test_tenders = set(shuffled_tenders[n_train + n_val:])
        
        # Ensure test set is non-empty if ratios dictate
        if not test_tenders and len(train_tenders) > 1:
            pop_t = sorted(list(train_tenders))[-1]
            train_tenders.remove(pop_t)
            test_tenders.add(pop_t)

        train_cases = [c for c in cases if (c.get("tender_id") or "UNASSIGNED_TENDER") in train_tenders]
        val_cases = [c for c in cases if (c.get("tender_id") or "UNASSIGNED_TENDER") in val_tenders]
        test_cases = [c for c in cases if (c.get("tender_id") or "UNASSIGNED_TENDER") in test_tenders]

        # Audit disjointness
        is_leakage_free = (
            train_tenders.isdisjoint(val_tenders) and
            train_tenders.isdisjoint(test_tenders) and
            val_tenders.isdisjoint(test_tenders)
        )

        return {
            "train": train_cases,
            "val": val_cases,
            "test": test_cases,
            "metadata": {
                "total_cases": len(cases),
                "total_tenders": n_tenders,
                "train_tenders_count": len(train_tenders),
                "val_tenders_count": len(val_tenders),
                "test_tenders_count": len(test_tenders),
                "train_cases_count": len(train_cases),
                "val_cases_count": len(val_cases),
                "test_cases_count": len(test_cases)
            },
            "leakage_audit": {
                "is_leakage_free": is_leakage_free,
                "train_tenders": sorted(list(train_tenders)),
                "val_tenders": sorted(list(val_tenders)),
                "test_tenders": sorted(list(test_tenders))
            }
        }


# ---------------------------------------------------------------------------
# 4. Evaluation Cohort Categorizer
# ---------------------------------------------------------------------------

class RequirementCategorizer:
    """Categorizes requirements into the 7 formal calibration cohorts."""

    @staticmethod
    def classify(case: Dict[str, Any]) -> str:
        req_id = case.get("requirement_id", "")
        req_text = (case.get("requirement_text") or "").lower()
        exp_dec = case.get("expected_decision", "RECOMMEND")
        gt_std = case.get("applicable_standard", "") or ""
        test_type = case.get("test_type", "")

        # 1. Distractor Probe
        if test_type == "DISTRACTOR_PROBE" or "NEG-002" in req_id:
            return "RETRIEVAL_DISTRACTOR_PROBE"

        # 2. Genuine Open-Set Negative
        if exp_dec in ("REJECT_INELIGIBLE", "NEGATIVE_CONTROL") or "NEG-001" in req_id or "NEG-004" in req_id or "NEG-005" in req_id:
            return "OPEN_SET_INELIGIBLE"

        # 3. Under-Specified
        if exp_dec == "ABSTAIN_UNDER_SPECIFIED" or "NEG-003" in req_id or (not gt_std and exp_dec != "RECOMMEND"):
            return "UNDER_SPECIFIED"

        # 4. Ambiguous / Competing
        if "competing" in str(case.get("reasoning", "")).lower() or "multiple competing" in str(case.get("standard_title", "")).lower():
            return "AMBIGUOUS_COMPETING"

        # 5. Compound Requirements
        if ";" in str(gt_std):
            return "ANSWERABLE_IN_DOMAIN_COMPOUND"

        # 6. Lifecycle / Edition-Sensitive
        if any(tok in str(gt_std) for tok in ["IS 15622", "IS 15000 : 2024", "IS 732 : 2019", "IS 3043 : 2018"]):
            return "LIFECYCLE_EDITION_SENSITIVE"

        # 7. Answerable Single Standard
        return "ANSWERABLE_IN_DOMAIN_SINGLE"


# ---------------------------------------------------------------------------
# 5. Offline Calibration Experiment Runner
# ---------------------------------------------------------------------------

class OfflineCalibrationRunner:
    """
    Executes threshold calibration trials deterministically offline.
    Isolates candidate parameters using dependency injection.
    """

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db or StandardsDatabase()

    def build_candidate_recommender(self, config: CalibrationConfig) -> StandardsRecommender:
        """Constructs a StandardsRecommender with candidate thresholds via dependency injection."""
        gate = ApplicabilityGate(
            applicability_threshold=config.applicability_threshold,
            review_threshold=config.review_threshold
        )
        amb_engine = AmbiguityEngine(
            separation_threshold=config.separation_threshold
        )
        return StandardsRecommender(
            db=self.db,
            applicability_gate=gate,
            ambiguity_engine=amb_engine
        )


    def evaluate_configuration(
        self,
        config: CalibrationConfig,
        cases: List[Dict[str, Any]],
        dataset_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Runs a complete evaluation trial under candidate configuration without modifying global state."""
        recommender = self.build_candidate_recommender(config)
        harness = ComprehensiveEvaluationHarness(recommender=recommender)

        evaluated_cases = []
        for c in cases:
            res = harness.evaluate_case(c)
            # Annotate with calibration cohort
            res["calibration_cohort"] = RequirementCategorizer.classify(c)
            evaluated_cases.append(res)

        meta = dataset_meta or {}
        meta["calibration_config"] = config.to_dict()
        meta["evaluated_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        metrics = compute_deconflated_metrics(evaluated_cases, meta)

        # Compute confidence intervals
        m_ret = metrics["retrieval_answerable"]
        m_sel = metrics["selective_classification"]
        top1_ci = calculate_wilson_interval(m_ret["top1_hits"], m_ret["total_answerable"])
        cov_ci = calculate_wilson_interval(m_sel["covered_count"], m_sel["total_eligible"])
        risk_ci = calculate_wilson_interval(m_sel["incorrect_covered_count"], m_sel["covered_count"])

        # Cohort-stratified breakdown
        cohorts: Dict[str, Dict[str, Any]] = {}
        for ec in evaluated_cases:
            coh = ec.get("calibration_cohort", "UNKNOWN")
            if coh not in cohorts:
                cohorts[coh] = {"total": 0, "covered": 0, "hits": 0, "abstained": 0, "failures": []}
            cohorts[coh]["total"] += 1
            if ec.get("system_decision") in ("RECOMMEND", "RECOMMEND_WITH_REVIEW") and ec.get("predicted_top1"):
                cohorts[coh]["covered"] += 1
            if ec.get("is_top1_hit", False):
                cohorts[coh]["hits"] += 1
            if ec.get("is_safe_abstention", False):
                cohorts[coh]["abstained"] += 1
            
            # Failure detection
            if coh == "OPEN_SET_INELIGIBLE" and ec.get("predicted_top1") is not None:
                cohorts[coh]["failures"].append({"id": ec["requirement_id"], "error": "False recommendation on negative control", "pred": ec["predicted_top1"]})
            elif coh == "UNDER_SPECIFIED" and not ec.get("is_safe_abstention", False):
                cohorts[coh]["failures"].append({"id": ec["requirement_id"], "error": "Failed safe abstention on under-specified query"})

        # Safety Gates Verification
        m_neg = metrics["negative_control"]
        in_dom_risk = metrics.get("in_domain_selective_classification", {}).get("selective_risk_percent", 0.0)
        
        gate_negative_safety = (m_neg["false_recommendation_rate_percent"] == 0.0)
        gate_selective_risk = (in_dom_risk == 0.0)
        
        # Check prerequisite: at least 5 adjudicated under-specified requirements
        adjudicated_under_count = sum(
            1 for c in cases
            if c.get("expected_decision") == "ABSTAIN_UNDER_SPECIFIED"
            and str(c.get("human_verified", "FALSE")).upper() == "TRUE"
        )
        gate_under_spec_prerequisite = (adjudicated_under_count >= 5)

        is_calibration_ready = (
            gate_negative_safety and
            gate_selective_risk and
            gate_under_spec_prerequisite
        )

        return {
            "config": config.to_dict(),
            "metrics": metrics,
            "statistical_uncertainty": {
                "top1_accuracy_wilson_ci_95": top1_ci,
                "coverage_wilson_ci_95": cov_ci,
                "selective_risk_wilson_ci_95": risk_ci,
                "interpretation": f"Sample size (N={m_sel['total_eligible']}) results in wide confidence intervals (Top-1 95% CI: {top1_ci[0]}% - {top1_ci[1]}%)."
            },
            "cohort_stratification": cohorts,
            "safety_gates": {
                "gate_negative_control_safety": {
                    "passed": gate_negative_safety,
                    "target": "0.0% false recommendations",
                    "observed": f"{m_neg['false_recommendation_rate_percent']:.1f}%"
                },
                "gate_in_domain_selective_risk": {
                    "passed": gate_selective_risk,
                    "target": "0.0% error rate on in-domain recommendations",
                    "observed": f"{in_dom_risk:.1f}%"
                },
                "gate_adjudicated_under_spec_prerequisite": {
                    "passed": gate_under_spec_prerequisite,
                    "target": ">= 5 qualified expert-adjudicated under-specified cases",
                    "observed": f"{adjudicated_under_count} adjudicated cases"
                },
                "calibration_readiness_verdict": "READY FOR CALIBRATION" if is_calibration_ready else "NOT READY FOR CALIBRATION"
            }
        }
