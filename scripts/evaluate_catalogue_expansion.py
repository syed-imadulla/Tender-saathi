"""
scripts/evaluate_catalogue_expansion.py
Purpose: Comparative benchmark evaluation between the 85-standard baseline
         and the 501-standard expanded catalogue on the 50-requirement benchmark.

Measures all 7 required metrics per Requirement 14:
1. Top-1 Accuracy
2. Top-3 Accuracy
3. MRR (Mean Reciprocal Rank)
4. Catalogue Coverage
5. False Positive Rate
6. Abstention Precision
7. Latency (ms per query)
"""

import json
import os
import time
from typing import Dict, Any, List

from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender
from src.critic import are_standards_equivalent


def run_benchmark_on_engine(recommender: StandardsRecommender, benchmark_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    top1_correct = 0
    top3_correct = 0
    reciprocal_ranks = []
    total_latency_ms = 0.0
    covered_in_catalogue = 0
    standard_requirements_count = 0
    
    # Abstention metrics
    abstention_true_positive = 0
    abstention_false_positive = 0
    false_positives = 0

    for item in benchmark_items:
        qid = item["id"]
        query = item["query"]
        expected = item["expected_standard"]
        is_abstention = (expected == "ABSTAIN")

        if not is_abstention:
            standard_requirements_count += 1

        t0 = time.perf_counter()
        res = recommender.recommend_for_text(query, req_id=qid)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        total_latency_ms += elapsed_ms

        candidate = res.candidate_standard
        recs = [r.standard_number for r in (res.recommendations or [])]

        if is_abstention:
            if candidate is None or candidate in ["INSUFFICIENT_INFORMATION", "", "UNKNOWN", "NONE"]:
                abstention_true_positive += 1
            else:
                abstention_false_positive += 1
                false_positives += 1
        else:
            # Check if expected standard is in the underlying database
            with recommender.db._get_connection() as conn:
                norm_exp = expected.split(" : ")[0].strip()
                row = conn.cursor().execute(
                    "SELECT standard_id FROM standards WHERE standard_number LIKE ? OR standard_id LIKE ?",
                    (f"{norm_exp}%", f"%{norm_exp}%")
                ).fetchone()
                if row:
                    covered_in_catalogue += 1

            if candidate and are_standards_equivalent(candidate, expected):
                top1_correct += 1
                top3_correct += 1
                reciprocal_ranks.append(1.0)
            elif any(are_standards_equivalent(r, expected) for r in recs[:3]):
                top3_correct += 1
                # Find rank
                rank = next(idx + 1 for idx, r in enumerate(recs[:3]) if are_standards_equivalent(r, expected))
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)
                if candidate and candidate not in ["INSUFFICIENT_INFORMATION", "", "UNKNOWN", "NONE"]:
                    # Candidate was recommended, but it didn't match expected standard
                    # Check if candidate was a false positive
                    if not row: # Expected was not in db, but system recommended something else
                        false_positives += 1

    total_items = len(benchmark_items)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    avg_latency = total_latency_ms / total_items if total_items else 0.0
    catalogue_cov_pct = (covered_in_catalogue / standard_requirements_count * 100.0) if standard_requirements_count else 0.0
    
    abstention_total_flagged = abstention_true_positive + abstention_false_positive
    abstention_precision = (abstention_true_positive / abstention_total_flagged * 100.0) if abstention_total_flagged else 100.0
    fp_rate = (false_positives / total_items * 100.0) if total_items else 0.0

    return {
        "total_queries": total_items,
        "standard_requirements": standard_requirements_count,
        "catalogue_coverage_pct": round(catalogue_cov_pct, 1),
        "covered_standards_count": covered_in_catalogue,
        "top_1_accuracy": round((top1_correct / standard_requirements_count) * 100.0, 1),
        "top_3_accuracy": round((top3_correct / standard_requirements_count) * 100.0, 1),
        "mrr": round(mrr, 3),
        "false_positive_rate": round(fp_rate, 1),
        "abstention_precision": round(abstention_precision, 1),
        "avg_latency_ms": round(avg_latency, 1)
    }


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bench_path = os.path.join(root_dir, "dataset", "ground_truth", "catalogue_benchmark_50.json")

    with open(bench_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    items = bench_data["items"]

    print("==================================================================")
    print("      TENDERSAATHI CATALOGUE EXPANSION BENCHMARK (85 vs 501)      ")
    print("==================================================================")
    print(f"Total benchmark requirements: {len(items)}\n")

    # 1. Evaluate Baseline 85 Catalogue (standards.db)
    print("--- 1. Evaluating Baseline Catalogue (85 Standards) ---")
    baseline_db = StandardsDatabase(db_path=os.path.join(root_dir, "data", "standards", "standards.db"))
    baseline_rec = StandardsRecommender(db=baseline_db)
    baseline_metrics = run_benchmark_on_engine(baseline_rec, items)
    print("Baseline Metrics:")
    for k, v in baseline_metrics.items():
        print(f"  {k:26}: {v}")

    # 2. Evaluate Expanded 501 Catalogue (catalogue.db)
    print("\n--- 2. Evaluating Expanded Catalogue (501 Standards) ---")
    expanded_db = StandardsDatabase(db_path=os.path.join(root_dir, "data", "catalogue", "catalogue.db"))
    expanded_rec = StandardsRecommender(db=expanded_db)
    expanded_metrics = run_benchmark_on_engine(expanded_rec, items)
    print("Expanded Metrics:")
    for k, v in expanded_metrics.items():
        print(f"  {k:26}: {v}")

    # Comparative Summary Table
    print("\n==================================================================")
    print(f"{'Metric':<28} | {'Baseline (85)':<15} | {'Expanded (501)':<15} | {'Delta':<10}")
    print("------------------------------------------------------------------")
    print(f"{'Catalogue Coverage':<28} | {str(baseline_metrics['catalogue_coverage_pct'])+'%':<15} | {str(expanded_metrics['catalogue_coverage_pct'])+'%':<15} | {round(expanded_metrics['catalogue_coverage_pct'] - baseline_metrics['catalogue_coverage_pct'], 1):+}%")
    print(f"{'Top-1 Accuracy':<28} | {str(baseline_metrics['top_1_accuracy'])+'%':<15} | {str(expanded_metrics['top_1_accuracy'])+'%':<15} | {round(expanded_metrics['top_1_accuracy'] - baseline_metrics['top_1_accuracy'], 1):+}%")
    print(f"{'Top-3 Accuracy':<28} | {str(baseline_metrics['top_3_accuracy'])+'%':<15} | {str(expanded_metrics['top_3_accuracy'])+'%':<15} | {round(expanded_metrics['top_3_accuracy'] - baseline_metrics['top_3_accuracy'], 1):+}%")
    print(f"{'MRR':<28} | {str(baseline_metrics['mrr']):<15} | {str(expanded_metrics['mrr']):<15} | {round(expanded_metrics['mrr'] - baseline_metrics['mrr'], 3):+}")
    print(f"{'False Positive Rate':<28} | {str(baseline_metrics['false_positive_rate'])+'%':<15} | {str(expanded_metrics['false_positive_rate'])+'%':<15} | {round(expanded_metrics['false_positive_rate'] - baseline_metrics['false_positive_rate'], 1):+}%")
    print(f"{'Abstention Precision':<28} | {str(baseline_metrics['abstention_precision'])+'%':<15} | {str(expanded_metrics['abstention_precision'])+'%':<15} | {round(expanded_metrics['abstention_precision'] - baseline_metrics['abstention_precision'], 1):+}%")
    print(f"{'Latency per Query':<28} | {str(baseline_metrics['avg_latency_ms'])+' ms':<15} | {str(expanded_metrics['avg_latency_ms'])+' ms':<15} | {round(expanded_metrics['avg_latency_ms'] - baseline_metrics['avg_latency_ms'], 1):+} ms")
    print("==================================================================")


if __name__ == "__main__":
    main()
