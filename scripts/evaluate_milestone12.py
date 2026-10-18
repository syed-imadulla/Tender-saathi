#!/usr/bin/env python3
"""
scripts/evaluate_milestone12.py

CLI executable for running Tender Saathi's multi-metric reproducible benchmark evaluation.
Generates structured JSON and Markdown evaluation artifacts.
Part of Phase 12 (Plan 12-02).
"""

import argparse
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.evaluate import evaluate_comprehensive_benchmark


def main():
    parser = argparse.ArgumentParser(
        description="Run Tender Saathi Comprehensive Multi-Metric Evaluation Benchmark (Phase 12)"
    )
    parser.add_argument(
        "--ground-truth",
        default="dataset/ground_truth/ground_truth.csv",
        help="Path to ground truth benchmark CSV file"
    )
    parser.add_argument(
        "--output-json",
        default="reports/evaluation/evaluation_benchmark_m12.json",
        help="Destination path for structured JSON metrics artifact"
    )
    parser.add_argument(
        "--output-report",
        default="reports/evaluation/evaluation_benchmark_m12.md",
        help="Destination path for Markdown evaluation report"
    )
    parser.add_argument(
        "--no-negative-controls",
        action="store_true",
        help="Exclude negative control queries from evaluation suite"
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("   TENDER SAATHI — COMPREHENSIVE MULTI-METRIC EVALUATION HARNESS   ")
    print("=" * 80)
    print(f"Dataset Target        : {args.ground_truth}")
    print(f"Include Negative Cases: {not args.no_negative_controls}")
    print("Starting evaluation pipeline...\n")

    metrics = evaluate_comprehensive_benchmark(
        ground_truth_path=args.ground_truth,
        output_json_path=args.output_json,
        output_report_path=args.output_report,
        include_negative_controls=not args.no_negative_controls
    )

    ret = metrics["retrieval_answerable"]
    sel = metrics["selective_classification"]
    abs_q = metrics["abstention_quality"]
    neg_q = metrics["negative_control"]
    ev_q = metrics["evidence_grounding"]
    sec_q = metrics["sector_stratification"]

    print("\n" + "=" * 80)
    print("                      DECOUPLED BENCHMARK RESULTS                      ")
    print("=" * 80)
    print(f"Dataset SHA-256             : {metrics['metadata']['dataset_sha256']}")
    print(f"Total Evaluated Cases       : {metrics['metadata']['total_evaluated_cases']}")
    print("-" * 80)
    print("1. RETRIEVAL ACCURACY (Answerable Cases Only):")
    print(f"   - Top-1 Accuracy         : {ret['top1_accuracy_percent']:.1f}% ({ret['top1_hits']} / {ret['total_answerable']})")
    print(f"   - Top-3 Accuracy         : {ret['top3_accuracy_percent']:.1f}% ({ret['top3_hits']} / {ret['total_answerable']})")
    print(f"   - Mean Reciprocal Rank   : {ret['mrr']:.3f}")
    print("-" * 80)
    print("2. SELECTIVE CLASSIFICATION:")
    print(f"   - Recommendation Coverage: {sel['coverage_percent']:.1f}% ({sel['covered_count']} / {sel['total_eligible']})")
    print(f"   - Selective Risk (Errors): {sel['selective_risk_percent']:.1f}% ({sel['incorrect_covered_count']} / {sel['covered_count']})")
    print("-" * 80)
    print("3. ABSTENTION & SAFETY QUALITY:")
    print(f"   - Under-Spec Abstain Rec : {abs_q['under_specified_abstention_recall_percent']:.1f}% ({abs_q['safe_abstained_count']} / {abs_q['under_specified_count']})")
    print(f"   - Negative False Rec Rate: {neg_q['false_recommendation_rate_percent']:.1f}% ({neg_q['false_recommendation_count']} / {neg_q['total_negative_cases']})")
    print(f"   - Negative Rejection Rate: {neg_q['negative_rejection_rate_percent']:.1f}%")
    print("-" * 80)
    print("4. EVIDENCE GROUNDING & CURRENCY:")
    print(f"   - Catalogue Status Match : {ev_q['catalogue_status_consistency_rate_percent']:.1f}%")
    print(f"   - Clause Grounding Status: {ev_q['clause_grounding_status']}")
    print(f"   - Proxy Overlap Score    : {ev_q['proxy_evidence_reference_overlap_percent']:.1f}%")
    print("-" * 80)
    print("5. SECTOR-STRATIFIED BREAKDOWN:")
    for sec, data in sec_q.items():
        print(f"   - {sec:<28}: n={data['sample_size']:<2} | ans={data['answerable_count']:<2} | Top-1: {data['top1_accuracy']:>5.1f}% | MRR: {data['mrr']:.3f}")
    print("=" * 80)
    print(f"\n[✓] Evaluation Report : {metrics['report_path']}")
    print(f"[✓] JSON Artifact     : {metrics['json_path']}\n")


if __name__ == "__main__":
    main()
