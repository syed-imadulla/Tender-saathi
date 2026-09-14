"""
Script: scripts/diagnose_phase4_r2_comprehensive.py
Purpose: Complete, objective Phase 4R2 diagnostic evaluation across all 20 benchmark requirements.

Computes:
1. Candidate Recall@10, 30, 50, 100 for DET, BM25, SEM, and HYB.
2. Explicit Citation Resolution vs General Relevance Retrieval separation.
3. Deep-dive root-cause analysis for failed queries (absent from Top-100).
4. Mathematical analysis of Hybrid Fusion on concrete cases (T003-R001, T004-R002, T005-R001, T012-R002, T014-R002).
5. Candidate Pool Size sweep (K=10, 20, 30, 50, 100).
6. Lifecycle composition in Top-10 results.
7. Stage-level warm latency measurements.
"""

import os
import sys
import time
import json
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider
from src.retrieval import HybridRetrievalEngine
from src.evaluate import extract_standard_tokens
from src.citation_resolver import ExactCitationResolver
from src.reranker import get_reranker_instance
from src.extract import extract_from_text


def run_diagnostics():
    print("=== Phase 4R2 Comprehensive Diagnostic Evaluation ===")
    db = get_default_catalogue_provider()
    engine = HybridRetrievalEngine(db=db)
    resolver = ExactCitationResolver(db=db)
    reranker = get_reranker_instance()
    df_gt = pd.read_csv("dataset/ground_truth/ground_truth.csv")

    # Warm-up models
    print("Warming up models...")
    _ = engine.search("test warm query", top_k=5, mode="hybrid+rerank")

    recall_counts = {k: {"DET": 0, "BM25": 0, "SEM": 0, "HYB": 0} for k in [10, 30, 50, 100]}
    citation_metrics = {"total_with_citation": 0, "resolved_correctly": 0}
    relevance_recall = {k: 0 for k in [10, 30, 50, 100]}
    failed_queries = []
    lifecycle_top10 = {"ACTIVE": 0, "WITHDRAWN": 0, "SUPERSEDED": 0, "UNKNOWN": 0}
    total_valid_queries = 0

    query_diagnostics = []

    for idx, row in df_gt.iterrows():
        req_id = row["requirement_id"]
        req_text = str(row["requirement_text"])
        gt_raw = str(row["applicable_standard"])
        gt_standards = extract_standard_tokens(gt_raw)

        if not gt_standards:
            continue

        total_valid_queries += 1
        req = extract_from_text(req_text, requirement_id=req_id)
        q = req_text
        components = req.components

        # Check explicit citation in requirement text
        extracted_citations = resolver.extract_citations(q)
        has_citation = len(extracted_citations) > 0
        resolved_cits = resolver.resolve_from_text(q) if has_citation else []

        if has_citation:
            citation_metrics["total_with_citation"] += 1
            cit_resolved_match = False
            for rc in resolved_cits:
                p_tokens = extract_standard_tokens(rc.standard_number)
                if any(any(p in g or g in p for g in gt_standards) for p in p_tokens):
                    cit_resolved_match = True
                    break
            if cit_resolved_match:
                citation_metrics["resolved_correctly"] += 1

        # Run first-stage retrieval engines for K=100
        det_res = engine.det_engine.search(q, top_k=100, components=components)
        bm25_hits = engine.bm25_engine.search(q, top_k=100)
        sem_hits = engine.semantic_engine.search(q, top_k=100)
        hyb_res = engine._fuse_hybrid_results(
            query=q, components=components or [], det_results=det_res,
            bm25_hits=bm25_hits, sem_hits=sem_hits, top_k=100, mode="hybrid"
        )

        def get_rank(cands, is_hit_obj=False):
            for i, c in enumerate(cands):
                std_num = c.standard_number if not is_hit_obj else getattr(c, "standard_number", "")
                p_tokens = extract_standard_tokens(std_num)
                if any(any(p in g or g in p for g in gt_standards) for p in p_tokens):
                    return i + 1
            return -1

        ranks = {
            "DET": get_rank(det_res),
            "BM25": get_rank(bm25_hits, is_hit_obj=True),
            "SEM": get_rank(sem_hits, is_hit_obj=True),
            "HYB": get_rank(hyb_res)
        }

        for k in [10, 30, 50, 100]:
            for m in ["DET", "BM25", "SEM", "HYB"]:
                if 0 < ranks[m] <= k:
                    recall_counts[k][m] += 1
            if not has_citation and 0 < ranks["HYB"] <= k:
                relevance_recall[k] += 1

        # Lifecycle counts in Top-10 Hybrid
        for c in hyb_res[:10]:
            st = str(c.status).upper()
            if st in lifecycle_top10:
                lifecycle_top10[st] += 1
            else:
                lifecycle_top10["UNKNOWN"] += 1

        q_info = {
            "requirement_id": req_id,
            "query": q,
            "expected_standard": gt_raw,
            "has_citation": has_citation,
            "extracted_citations": extracted_citations,
            "resolved_citations": [rc.to_dict() for rc in resolved_cits],
            "ranks": ranks,
            "top10_hybrid_lifecycle": [str(c.status).upper() for c in hyb_res[:10]],
            "top5_det": [c.standard_number for c in det_res[:5]],
            "top5_bm25": [h.standard_number for h in bm25_hits[:5]],
            "top5_sem": [h.standard_number for h in sem_hits[:5]],
            "top5_hyb": [c.standard_number for c in hyb_res[:5]],
        }
        query_diagnostics.append(q_info)

        # Failed query deep-dive: absent from Top-100 in Hybrid
        if ranks["HYB"] < 0:
            db_records = []
            with db._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                for gt in gt_standards:
                    cur.execute("SELECT * FROM catalogue_standards WHERE standard_number LIKE ? OR canonical_id LIKE ? LIMIT 1", (f"%{gt}%", f"%{gt}%"))
                    row = cur.fetchone()
                    if row:
                        db_records.append(dict(row))

            failed_queries.append({
                "requirement_id": req_id,
                "query": q,
                "expected_standard": gt_raw,
                "has_citation": has_citation,
                "ranks": ranks,
                "exists_in_db": len(db_records) > 0,
                "db_records": db_records,
                "top10_det": [{"std": c.standard_number, "score": c.relevance_score} for c in det_res[:10]],
                "top10_bm25": [{"std": h.standard_number, "score": round(h.normalized_score, 3)} for h in bm25_hits[:10]],
                "top10_sem": [{"std": h.standard_number, "score": round(h.similarity_score, 3)} for h in sem_hits[:10]],
                "top10_hyb": [{"std": c.standard_number, "score": round(getattr(c, "final_score", c.relevance_score), 3), "status": c.status} for c in hyb_res[:10]],
            })

    # Concrete Mathematical Fusion Analysis
    fusion_cases = ["T003-R001", "T004-R002", "T005-R001", "T012-R002", "T014-R002"]
    fusion_analysis = []
    for fc in query_diagnostics:
        if fc["requirement_id"] in fusion_cases:
            fusion_analysis.append({
                "requirement_id": fc["requirement_id"],
                "query": fc["query"],
                "expected": fc["expected_standard"],
                "ranks": fc["ranks"]
            })

    # Candidate Pool Size & Latency Sweep (K=10, 20, 30, 50, 100)
    pool_sweep = {}
    print("\nRunning Candidate Pool Size & Latency Sweep...")
    sample_query = df_gt.iloc[0]["requirement_text"]
    for k_val in [10, 20, 30, 50, 100]:
        t_start = time.perf_counter()
        _ = engine.search(sample_query, top_k=k_val, mode="hybrid+rerank")
        t_total = (time.perf_counter() - t_start) * 1000

        # Profile reranker specifically for k_val candidates
        t_rerank = 0.0
        if engine.reranker and hyb_res:
            c_pool = hyb_res[:k_val]
            t0 = time.perf_counter()
            c_texts = [engine.reranker.build_candidate_text(db.get_standard(c.standard_id) or {}) for c in c_pool]
            _ = engine.reranker.score_pairs(sample_query, c_texts)
            t_rerank = (time.perf_counter() - t0) * 1000

        pool_sweep[k_val] = {
            "total_latency_ms": round(t_total, 2),
            "reranker_latency_ms": round(t_rerank, 2)
        }

    # Warm Stage-Level Latency
    print("Measuring warm stage-level latency...")
    t_det_start = time.perf_counter()
    _ = engine.det_engine.search(sample_query, top_k=30)
    t_det = (time.perf_counter() - t_det_start) * 1000

    t_bm25_start = time.perf_counter()
    _ = engine.bm25_engine.search(sample_query, top_k=30)
    t_bm25 = (time.perf_counter() - t_bm25_start) * 1000

    t_sem_start = time.perf_counter()
    _ = engine.semantic_engine.search(sample_query, top_k=30)
    t_sem = (time.perf_counter() - t_sem_start) * 1000

    t_hyb_start = time.perf_counter()
    _ = engine.search(sample_query, top_k=30, mode="hybrid")
    t_hyb = (time.perf_counter() - t_hyb_start) * 1000

    stage_latencies = {
        "warm_deterministic_ms": round(t_det, 2),
        "warm_bm25_ms": round(t_bm25, 2),
        "warm_semantic_ms": round(t_sem, 2),
        "warm_hybrid_ms": round(t_hyb, 2)
    }

    report = {
        "total_queries_evaluated": total_valid_queries,
        "recall_at_k": {
            k: {
                "DET": f"{recall_counts[k]['DET']}/{total_valid_queries} ({recall_counts[k]['DET']/total_valid_queries*100:.1f}%)",
                "BM25": f"{recall_counts[k]['BM25']}/{total_valid_queries} ({recall_counts[k]['BM25']/total_valid_queries*100:.1f}%)",
                "SEM": f"{recall_counts[k]['SEM']}/{total_valid_queries} ({recall_counts[k]['SEM']/total_valid_queries*100:.1f}%)",
                "HYB": f"{recall_counts[k]['HYB']}/{total_valid_queries} ({recall_counts[k]['HYB']/total_valid_queries*100:.1f}%)",
            }
            for k in [10, 30, 50, 100]
        },
        "citation_metrics": citation_metrics,
        "general_relevance_recall": {
            k: f"{relevance_recall[k]}/{total_valid_queries - citation_metrics['total_with_citation']} ({relevance_recall[k]/(total_valid_queries - citation_metrics['total_with_citation'])*100:.1f}%)"
            for k in [10, 30, 50, 100]
        },
        "lifecycle_composition_top10": lifecycle_top10,
        "fusion_concrete_cases": fusion_analysis,
        "pool_size_sweep": pool_sweep,
        "warm_stage_latencies": stage_latencies,
        "failed_queries_count": len(failed_queries),
        "failed_queries": failed_queries,
        "all_queries": query_diagnostics
    }

    os.makedirs("reports", exist_ok=True)
    out_path = "reports/phase4_r2_diagnostics.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nDiagnostics successfully saved to {out_path}!")
    print("\n--- Summary Recall @ K ---")
    for k in [10, 30, 50, 100]:
        print(f"K={k:3d}: DET={report['recall_at_k'][k]['DET']} | BM25={report['recall_at_k'][k]['BM25']} | SEM={report['recall_at_k'][k]['SEM']} | HYB={report['recall_at_k'][k]['HYB']}")
    print(f"\nLifecycle Top-10: {lifecycle_top10}")
    print(f"Failed Queries (absent from Top-100): {len(failed_queries)}")


if __name__ == "__main__":
    run_diagnostics()
