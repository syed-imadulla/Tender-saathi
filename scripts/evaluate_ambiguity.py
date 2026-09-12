#!/usr/bin/env python3
"""
Controlled Ambiguity Benchmark Evaluation and Separation Threshold Sweep.

Evaluates TenderSaathi's 6-state ambiguity engine against:
1. The 40-case Controlled Ambiguity Benchmark (dataset/ground_truth/ambiguity_benchmark.json)
2. Threshold sweep across delta in {0.03, 0.05, 0.08, 0.10}
3. The 50-query Catalogue Benchmark (dataset/ground_truth/catalogue_benchmark_50.json) to confirm valid recommendation preservation >= 98%.
"""

import os
import sys
import json
import time
from typing import Dict, List, Any

# Add workspace root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.ambiguity import AmbiguityState


def run_ambiguity_benchmark(
    recommender: StandardsRecommender,
    benchmark_path: str,
    threshold: float
) -> Dict[str, Any]:
    """Runs the 40-case ambiguity benchmark for a given candidate separation threshold."""
    with open(benchmark_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # Set threshold on ambiguity engine
    recommender.ambiguity_engine.separation_threshold = threshold

    results = []
    state_confusion = {
        s.value: {target.value: 0 for target in AmbiguityState}
        for s in AmbiguityState
    }
    invariant_violations = 0
    clean_abstention_violations = 0

    for case in cases:
        c_id = case["id"]
        text = case["requirement_text"]
        expected_state = case["expected_state"]
        expected_review = case.get("expected_review_required", True)

        req = extract_from_text(text, requirement_id=c_id)
        res = recommender.recommend_for_requirement(req)

        pred_state = res.ambiguity_state
        state_match = (pred_state == expected_state)

        # Invariant checks
        # 1. candidate_standard == evidence_standard for every non-null recommendation
        if res.candidate_standard is not None:
            if res.candidate_standard != res.evidence_standard:
                invariant_violations += 1

        # 2. For abstentions (INCOMPLETE, AMBIGUOUS, CONFLICTING, NO_RELIABLE_MATCH):
        # candidate_standard must be None, human_review_required must be True
        if pred_state in ["INCOMPLETE", "AMBIGUOUS", "CONFLICTING", "NO_RELIABLE_MATCH"]:
            if res.candidate_standard is not None or not res.human_review_required:
                clean_abstention_violations += 1

        state_confusion[expected_state][pred_state] = state_confusion[expected_state].get(pred_state, 0) + 1

        results.append({
            "id": c_id,
            "category": case.get("category", ""),
            "text": text[:80] + "...",
            "expected_state": expected_state,
            "predicted_state": pred_state,
            "state_match": state_match,
            "candidate_standard": res.candidate_standard,
            "evidence_standard": res.evidence_standard,
            "human_review_required": res.human_review_required,
            "expected_review_required": expected_review,
            "review_match": (res.human_review_required == expected_review),
            "separation_margin": getattr(res, "separation_margin", None),
            "reason": res.reason[:100] if res.reason else ""
        })

    total_cases = len(cases)
    total_correct_state = sum(1 for r in results if r["state_match"])
    accuracy = (total_correct_state / total_cases) * 100.0

    # Per-state accuracy
    by_state = {}
    for state_name in ["CLEAR", "INCOMPLETE", "AMBIGUOUS", "CONFLICTING", "NO_RELIABLE_MATCH"]:
        cases_in_state = [r for r in results if r["expected_state"] == state_name]
        correct = [r for r in cases_in_state if r["state_match"]]
        cnt = len(cases_in_state)
        acc = (len(correct) / cnt * 100.0) if cnt > 0 else 0.0
        by_state[state_name] = {
            "total": cnt,
            "correct": len(correct),
            "accuracy": acc
        }

    return {
        "threshold": threshold,
        "total_cases": total_cases,
        "correct_state": total_correct_state,
        "accuracy": accuracy,
        "by_state": by_state,
        "invariant_violations": invariant_violations,
        "clean_abstention_violations": clean_abstention_violations,
        "results": results
    }


def evaluate_recommendation_preservation(
    recommender: StandardsRecommender,
    benchmark_path: str
) -> Dict[str, Any]:
    """
    Evaluates recommendation preservation on the existing 50-query catalogue benchmark.
    Verifies that valid recommendations are preserved (target >= 98%).
    """
    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items") or data.get("benchmark_queries") or data
    if isinstance(items, dict):
        items = list(items.values())

    total = len(items)
    preserved = 0
    abstentions = 0
    candidate_evidence_matches = 0
    records = []

    for item in items:
        q_id = item.get("id") or item.get("query_id")
        text = item.get("requirement_text") or item.get("query")
        expected_std = item.get("expected_standard") or item.get("standard_number")

        req = extract_from_text(text, requirement_id=q_id)
        res = recommender.recommend_for_requirement(req)

        cand = res.candidate_standard
        ev_std = res.evidence_standard

        # Check invariant
        if cand is not None:
            if cand == ev_std:
                candidate_evidence_matches += 1

        is_preserved = False
        if cand is not None and expected_std:
            exp_clean = expected_std.split(":")[0].strip().upper()
            cand_clean = cand.split(":")[0].strip().upper()
            if exp_clean in cand_clean or cand_clean in exp_clean:
                is_preserved = True
                preserved += 1
        elif cand is None:
            abstentions += 1

        records.append({
            "id": q_id,
            "text": text[:60] + "...",
            "expected_standard": expected_std,
            "candidate_standard": cand,
            "evidence_standard": ev_std,
            "ambiguity_state": res.ambiguity_state,
            "is_preserved": is_preserved
        })

    preservation_rate = (preserved / total) * 100.0 if total > 0 else 0.0

    return {
        "total_queries": total,
        "preserved_count": preserved,
        "preservation_rate": preservation_rate,
        "abstention_count": abstentions,
        "candidate_evidence_matches": candidate_evidence_matches,
        "records": records
    }


def main():
    print("==================================================================")
    print("  TenderSaathi Ambiguity Benchmark Evaluation & Threshold Sweep   ")
    print("==================================================================")

    ambiguity_bm_path = os.path.join(ROOT_DIR, "dataset", "ground_truth", "ambiguity_benchmark.json")
    catalogue_bm_path = os.path.join(ROOT_DIR, "dataset", "ground_truth", "catalogue_benchmark_50.json")

    if not os.path.exists(ambiguity_bm_path):
        print(f"Error: Ambiguity benchmark not found at {ambiguity_bm_path}")
        sys.exit(1)

    recommender = StandardsRecommender(retrieval_mode="hybrid")

    # Sweep thresholds: 0.03, 0.05, 0.08, 0.10, 0.15
    sweep_thresholds = [0.03, 0.05, 0.08, 0.10, 0.15]
    sweep_results = []

    print("\n--- Running Separation Threshold Sweep over Δ in {0.03, 0.05, 0.08, 0.10, 0.15} ---")
    for delta in sweep_thresholds:
        t0 = time.time()
        res = run_ambiguity_benchmark(recommender, ambiguity_bm_path, threshold=delta)
        elapsed = time.time() - t0
        res["elapsed_sec"] = round(elapsed, 2)
        sweep_results.append(res)

        print(f"\n[Threshold Δ = {delta:.2f}] (Evaluation time: {elapsed:.2f}s)")
        print(f"  Overall Accuracy: {res['accuracy']:.1f}% ({res['correct_state']}/{res['total_cases']})")
        print(f"  Invariant Violations (cand == evid): {res['invariant_violations']}")
        print(f"  Clean Abstention Violations: {res['clean_abstention_violations']}")
        for st, data in res["by_state"].items():
            print(f"    - {st:<18}: {data['correct']}/{data['total']} ({data['accuracy']:.1f}%)")

    # Select optimal threshold
    best_sweep = max(sweep_results, key=lambda x: (x["accuracy"], -x["invariant_violations"]))
    selected_delta = best_sweep["threshold"]
    print(f"\n>>> Selected Separation Threshold: Δ = {selected_delta:.2f} (Accuracy: {best_sweep['accuracy']:.1f}%)")

    # Display any mismatches for diagnostic transparency
    print("\n--- Diagnostic Details on Benchmark Cases ---")
    for r in best_sweep["results"]:
        if not r["state_match"]:
            print(f"  [MISMATCH {r['id']}] Expected: {r['expected_state']} | Predicted: {r['predicted_state']} | Cand: {r['candidate_standard']} | Reason: {r['reason']}")

    # Re-run at selected threshold and test 50-query catalogue preservation
    recommender.ambiguity_engine.separation_threshold = selected_delta
    cat_db_path = os.path.join(ROOT_DIR, "data", "catalogue", "catalogue.db")
    if os.path.exists(cat_db_path):
        from src.standards import StandardsDatabase
        cat_recommender = StandardsRecommender(db=StandardsDatabase(cat_db_path), retrieval_mode="hybrid")
        cat_recommender.ambiguity_engine.separation_threshold = selected_delta
        pres_results = evaluate_recommendation_preservation(cat_recommender, catalogue_bm_path)
    else:
        pres_results = evaluate_recommendation_preservation(recommender, catalogue_bm_path)
    print(f"  Total Queries: {pres_results['total_queries']}")
    print(f"  Preserved Valid Recommendations: {pres_results['preserved_count']}/{pres_results['total_queries']} ({pres_results['preservation_rate']:.1f}%)")
    print(f"  Clean Abstentions: {pres_results['abstention_count']}")
    print(f"  Candidate == Evidence Matches: {pres_results['candidate_evidence_matches']}")

    # Save evaluation report artifact
    report_data = {
        "selected_threshold": selected_delta,
        "sweep_results": [
            {
                "threshold": r["threshold"],
                "accuracy": r["accuracy"],
                "correct_state": r["correct_state"],
                "total_cases": r["total_cases"],
                "invariant_violations": r["invariant_violations"],
                "by_state": r["by_state"],
                "elapsed_sec": r["elapsed_sec"]
            }
            for r in sweep_results
        ],
        "ambiguity_benchmark": best_sweep,
        "catalogue_preservation": pres_results
    }

    report_path = os.path.join(ROOT_DIR, "reports", "ambiguity_evaluation_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\nFull evaluation report saved to {report_path}")
    print("==================================================================")


if __name__ == "__main__":
    main()
