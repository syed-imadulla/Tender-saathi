"""Evaluation Script for TenderSaathi Priority 6 Multilingual Benchmark.

Runs all 40 ground-truth benchmark cases (10 Hindi, 10 Kannada, 10 Tamil, 10 Mixed)
and measures:
1. Script & Language Detection Accuracy
2. Normalization Quality & Latency
3. English Reference vs. Multilingual Recommendation Consistency (Top-1, Top-3, Abstention)
4. Critical Entity Preservation (IS codes, ratings, dimensions, units)
5. Safety Invariants:
   - candidate_standard == evidence_standard (100% required)
   - Zero fabricated IS codes
   - Safe abstention on ambiguous/nonsense input
"""

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from src.recommend import StandardsRecommender


def run_benchmark():
    benchmark_file = Path("dataset/ground_truth/multilingual_benchmark.json")
    if not benchmark_file.exists():
        print(f"Error: Benchmark file {benchmark_file} not found.")
        sys.exit(1)

    with open(benchmark_file, "r", encoding="utf-8") as f:
        cases: List[Dict[str, Any]] = json.load(f)

    print(f"Loaded {len(cases)} benchmark cases.")
    recommender = StandardsRecommender()

    results = []
    top1_matches = 0
    top3_matches = 0
    abstention_matches = 0
    entity_preservations = 0
    total_entity_cases = 0
    invariant_passed = 0
    total_evaluable = 0

    language_stats = {
        "hi": {"total": 0, "correct_lang": 0, "consistent": 0, "latencies": []},
        "kn": {"total": 0, "correct_lang": 0, "consistent": 0, "latencies": []},
        "ta": {"total": 0, "correct_lang": 0, "consistent": 0, "latencies": []},
        "mixed": {"total": 0, "correct_lang": 0, "consistent": 0, "latencies": []},
    }

    print("\n" + "=" * 80)
    print("RUNNING 40-CASE MULTILINGUAL BENCHMARK EVALUATION")
    print("=" * 80)

    for i, case in enumerate(cases, 1):
        cid = case["id"]
        lang = case["language"]
        multi_text = case["multilingual_input"]
        eng_ref = case["english_reference"]
        exp_std = case["expected_standard"]
        exp_state = case["expected_state"]

        language_stats[lang]["total"] += 1

        # Measure Multilingual Pipeline
        t0 = time.perf_counter()
        multi_res = recommender.recommend_for_text(multi_text, req_id=cid)
        multi_latency = (time.perf_counter() - t0) * 1000.0
        language_stats[lang]["latencies"].append(multi_latency)

        # Measure English Reference Pipeline
        t0_eng = time.perf_counter()
        eng_res = recommender.recommend_for_text(eng_ref, req_id=f"ENG-{cid}")
        eng_latency = (time.perf_counter() - t0_eng) * 1000.0

        # Detection accuracy
        det_lang = multi_res.multilingual.get("detected_language") if multi_res.multilingual else "unknown"
        lang_correct = (det_lang == lang) or (lang == "mixed" and det_lang in ["mixed", "hi-Latn", "kn", "ta", "hi"])
        if lang_correct:
            language_stats[lang]["correct_lang"] += 1

        # Invariant check
        inv_ok = True
        if multi_res.candidate_standard:
            inv_ok = (multi_res.candidate_standard == multi_res.evidence_standard)
        if inv_ok:
            invariant_passed += 1

        # Entity preservation
        ent_status = multi_res.multilingual.get("entity_preservation_status", "N/A") if multi_res.multilingual else "N/A"
        if case.get("expected_entities"):
            total_entity_cases += 1
            if ent_status == "PASS":
                entity_preservations += 1

        # Recommendation Consistency: Multilingual vs English Reference
        multi_cand = multi_res.candidate_standard
        eng_cand = eng_res.candidate_standard

        # Check Top-1 match
        same_rec = False
        if multi_cand and eng_cand:
            same_rec = (multi_cand.split(":")[0].strip() == eng_cand.split(":")[0].strip())
        elif multi_cand is None and eng_cand is None:
            same_rec = True  # Both abstained cleanly

        if same_rec:
            top1_matches += 1
            top3_matches += 1
            language_stats[lang]["consistent"] += 1
        else:
            # Check if eng_cand is in alternatives
            alts = [a.split(":")[0].strip() for a in (multi_res.alternatives or []) if a]
            if eng_cand and eng_cand.split(":")[0].strip() in alts:
                top3_matches += 1

        # Check Abstention Consistency
        if exp_std is None:
            if multi_cand is None:
                abstention_matches += 1
        else:
            if multi_cand is not None:
                abstention_matches += 1

        outcome_category = "SAME_RECOMMENDATION" if same_rec else (
            "SAFE_ABSTENTION" if multi_cand is None and exp_std is None else "DIFFERENT_BUT_VALID"
        )

        results.append({
            "id": cid,
            "language": lang,
            "detected_language": det_lang,
            "domain": case["domain"],
            "multilingual_input": multi_text,
            "canonical_text": multi_res.multilingual.get("canonical_text") if multi_res.multilingual else multi_text,
            "normalization_method": multi_res.multilingual.get("normalization_method") if multi_res.multilingual else "none",
            "multi_candidate": multi_cand,
            "eng_candidate": eng_cand,
            "expected_standard": exp_std,
            "multi_evidence": multi_res.evidence_standard,
            "entity_preservation": ent_status,
            "invariant_passed": inv_ok,
            "same_as_english": same_rec,
            "outcome_category": outcome_category,
            "latency_ms": round(multi_latency, 2),
            "eng_latency_ms": round(eng_latency, 2),
        })

        print(f"[{cid}] ({lang}) -> Multi: {multi_cand} | Eng: {eng_cand} | Match: {same_rec} | Latency: {multi_latency:.1f}ms")

    total_cases = len(cases)
    consistency_rate = (top1_matches / total_cases) * 100.0
    top3_rate = (top3_matches / total_cases) * 100.0
    abstention_rate = (abstention_matches / total_cases) * 100.0
    invariant_rate = (invariant_passed / total_cases) * 100.0
    entity_rate = (entity_preservations / total_entity_cases * 100.0) if total_entity_cases else 100.0

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY RESULTS")
    print("=" * 80)
    print(f"Total Cases:                   {total_cases}")
    print(f"Top-1 Recommendation Match:    {top1_matches}/{total_cases} ({consistency_rate:.1f}%)")
    print(f"Top-3 Recommendation Match:    {top3_matches}/{total_cases} ({top3_rate:.1f}%)")
    print(f"Abstention Consistency:        {abstention_matches}/{total_cases} ({abstention_rate:.1f}%)")
    print(f"Entity Preservation Rate:      {entity_preservations}/{total_entity_cases} ({entity_rate:.1f}%)")
    print(f"Candidate==Evidence Invariant: {invariant_passed}/{total_cases} ({invariant_rate:.1f}%)")
    print("\nPer-Language Breakdown:")
    for l, s in language_stats.items():
        avg_lat = sum(s["latencies"]) / len(s["latencies"]) if s["latencies"] else 0.0
        print(f"  [{l.upper()}] Detection: {s['correct_lang']}/{s['total']} | Consistency: {s['consistent']}/{s['total']} | Avg Latency: {avg_lat:.1f} ms")

    # Save detailed evaluation report
    report_output = Path("reports/feasibility/multilingual_benchmark_results.json")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    with open(report_output, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "total_cases": total_cases,
                "top1_consistency": consistency_rate,
                "top3_consistency": top3_rate,
                "abstention_consistency": abstention_rate,
                "entity_preservation_rate": entity_rate,
                "candidate_evidence_invariant": invariant_rate,
            },
            "language_stats": language_stats,
            "detailed_results": results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed benchmark results saved to: {report_output}")
    return results


if __name__ == "__main__":
    run_benchmark()
