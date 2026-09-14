"""
scripts/experiment_pool_sizes.py — Empirical Evaluation of Candidate Pool Sizing & Cross-Encoder Depth.

Tests parameter grids across:
1. FIRST_STAGE_RETRIEVAL_K: [100, 150, 200, 300]
2. RRF_RETENTION_K: [30, 50, 75, 100, 150, 200]
3. CROSS_ENCODER_POOL_K: [30, 50, 75, 100]

Uses STRICT identifier integrity checking (StandardIdentifierNormalizer) without substring bleed.
Measures:
- Per-stage recall
- Union recall
- Candidate preservation across stages
- RRF Recall@10, @30, @50, @100
- Cross-Encoder Recall@10, Hit@1, Hit@3, MRR
- Warm latency profile
"""

import os
import sys
import time
import json
import re
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider
from src.retrieval import HybridRetrievalEngine
from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.evaluate import extract_standard_tokens


def matches_standard(cand_str: str, exp_str: str) -> bool:
    """Rigorous standard matching ensuring zero identifier cross-talk."""
    if not cand_str or not exp_str:
        return False
    c = StandardIdentifierNormalizer.parse(cand_str)
    e = StandardIdentifierNormalizer.parse(exp_str)
    if not c.is_valid or not e.is_valid:
        return False
    # Normalize prefixes
    c_p = c.prefix.upper().replace(' ', '').replace('-', '')
    e_p = e.prefix.upper().replace(' ', '').replace('-', '')
    if c_p != e_p:
        return False
    if c.base_number != e.base_number:
        return False
    if e.part is not None and c.part != e.part:
        return False
    if e.section is not None and c.section != e.section:
        return False
    return True


def find_match_rank(candidates, expected_tokens, key_func=lambda x: x.standard_number):
    """Finds 1-based rank of the first candidate matching any expected token."""
    for idx, cand in enumerate(candidates):
        cand_str = key_func(cand)
        for exp in expected_tokens:
            if matches_standard(cand_str, exp):
                return idx + 1
    return None


def run_experiment():
    provider = get_default_catalogue_provider()
    engine = HybridRetrievalEngine(db=provider, fusion_strategy="rrf")
    reranker = engine.reranker

    df = pd.read_csv(os.path.join(ROOT_DIR, "dataset", "ground_truth", "ground_truth.csv"))
    evaluable = []
    for _, row in df.iterrows():
        raw = row["applicable_standard"]
        if pd.notna(raw):
            toks = extract_standard_tokens(raw)
            if toks:
                evaluable.append({
                    "req_id": row["requirement_id"],
                    "text": row["requirement_text"],
                    "expected_tokens": toks
                })

    print(f"Loaded {len(evaluable)} ground-truth benchmark queries.")
    print("Warming up models...")
    _ = engine.search("power cable", top_k=5)
    _ = reranker.score_pairs("power cable", ["IS 7098 Part 1 XLPE Cable"])

    depths = [100, 150, 200, 300]
    first_stage_results = {}

    print("\n" + "=" * 80)
    print("EXPERIMENT 1: FIRST_STAGE_RETRIEVAL_K & UNION RECALL")
    print("=" * 80)

    for depth in depths:
        t_start = time.perf_counter()
        det_ranks = []
        bm25_ranks = []
        sem_ranks = []
        union_ranks = []

        for q in evaluable:
            req_text = q["text"]
            exp_toks = q["expected_tokens"]

            # Deterministic
            det_hits = engine.det_engine.search(req_text, top_k=depth)
            d_rk = find_match_rank(det_hits, exp_toks)
            det_ranks.append(d_rk)

            # BM25
            exp_query = engine.terminology_normalizer.build_expanded_query(req_text)
            bm25_hits = engine.bm25_engine.search(exp_query, top_k=depth)
            b_rk = find_match_rank(bm25_hits, exp_toks)
            bm25_ranks.append(b_rk)

            # Semantic
            sem_hits = engine.semantic_engine.search(exp_query, top_k=depth)
            s_rk = find_match_rank(sem_hits, exp_toks)
            sem_ranks.append(s_rk)

            # Deduplicated Union
            seen = set()
            union_list = []
            for h in det_hits:
                if h.standard_id not in seen:
                    seen.add(h.standard_id)
                    union_list.append(h)
            for h in bm25_hits:
                if h.standard_id not in seen:
                    seen.add(h.standard_id)
                    union_list.append(h)
            for h in sem_hits:
                if h.standard_id not in seen:
                    seen.add(h.standard_id)
                    union_list.append(h)

            u_rk = find_match_rank(union_list, exp_toks)
            union_ranks.append(u_rk)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0 / len(evaluable)

        def r_at_k(ranks, k):
            return sum(1 for r in ranks if r is not None and r <= k)

        total = len(evaluable)
        det_found = sum(1 for r in det_ranks if r is not None)
        bm25_found = sum(1 for r in bm25_ranks if r is not None)
        sem_found = sum(1 for r in sem_ranks if r is not None)
        union_found = sum(1 for r in union_ranks if r is not None)

        first_stage_results[depth] = {
            "det_found": det_found,
            "bm25_found": bm25_found,
            "sem_found": sem_found,
            "union_found": union_found,
            "union_r10": r_at_k(union_ranks, 10),
            "union_r30": r_at_k(union_ranks, 30),
            "union_r50": r_at_k(union_ranks, 50),
            "union_r100": r_at_k(union_ranks, 100),
            "union_r150": r_at_k(union_ranks, 150),
            "union_r200": r_at_k(union_ranks, 200),
            "union_r300": r_at_k(union_ranks, 300),
            "latency_ms": round(elapsed_ms, 1)
        }

        print(f"FIRST_STAGE_RETRIEVAL_K={depth:3d} (avg {elapsed_ms:.1f} ms/query):")
        print(f"  Single Retrievers: DET={det_found}/{total}, BM25={bm25_found}/{total}, SEM={sem_found}/{total}")
        print(f"  Union Total Found: {union_found}/{total} ({union_found/total*100:.1f}%)")
        print(f"  Union Recall: @10={r_at_k(union_ranks, 10)}/{total}, @30={r_at_k(union_ranks, 30)}/{total}, @50={r_at_k(union_ranks, 50)}/{total}, @100={r_at_k(union_ranks, 100)}/{total}, @150={r_at_k(union_ranks, 150)}/{total}, @200={r_at_k(union_ranks, 200)}/{total}, @300={r_at_k(union_ranks, 300)}/{total}")

    print("\n" + "=" * 80)
    print("EXPERIMENT 2: RRF_RETENTION_K (using FIRST_STAGE_RETRIEVAL_K=150)")
    print("=" * 80)

    rrf_depths = [30, 50, 75, 100, 150, 200]
    rrf_results = {}

    for rrf_k_val in rrf_depths:
        t_start = time.perf_counter()
        rrf_ranks = []

        for q in evaluable:
            req_text = q["text"]
            exp_toks = q["expected_tokens"]

            det_hits = engine.det_engine.search(req_text, top_k=150)
            exp_query = engine.terminology_normalizer.build_expanded_query(req_text)
            bm25_hits = engine.bm25_engine.search(exp_query, top_k=150)
            sem_hits = engine.semantic_engine.search(exp_query, top_k=150)

            fused = engine._fuse_hybrid_results(
                query=req_text,
                components=[],
                det_results=det_hits,
                bm25_hits=bm25_hits,
                sem_hits=sem_hits,
                top_k=rrf_k_val,
                mode="hybrid",
                fusion_strategy="rrf"
            )

            r_rk = find_match_rank(fused, exp_toks)
            rrf_ranks.append(r_rk)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0 / len(evaluable)
        total_found = sum(1 for r in rrf_ranks if r is not None)
        r10 = sum(1 for r in rrf_ranks if r is not None and r <= 10)
        r30 = sum(1 for r in rrf_ranks if r is not None and r <= 30)
        r50 = sum(1 for r in rrf_ranks if r is not None and r <= 50)
        r100 = sum(1 for r in rrf_ranks if r is not None and r <= 100)
        hit1 = sum(1 for r in rrf_ranks if r == 1)
        hit3 = sum(1 for r in rrf_ranks if r is not None and r <= 3)
        mrr = sum(1.0 / r for r in rrf_ranks if r is not None) / len(evaluable)

        rrf_results[rrf_k_val] = {
            "total_found": total_found,
            "r10": r10, "r30": r30, "r50": r50, "r100": r100,
            "hit1": hit1, "hit3": hit3, "mrr": round(mrr, 3),
            "latency_ms": round(elapsed_ms, 1)
        }

        print(f"RRF_RETENTION_K={rrf_k_val:3d} (avg {elapsed_ms:.1f} ms/query): Found={total_found}/{len(evaluable)} | R@10={r10}/{len(evaluable)}, R@30={r30}/{len(evaluable)}, R@50={r50}/{len(evaluable)}, R@100={r100}/{len(evaluable)} | Hit@1={hit1}, Hit@3={hit3}, MRR={mrr:.3f}")

    print("\n" + "=" * 80)
    print("EXPERIMENT 3: CROSS_ENCODER_POOL_K (using FIRST_STAGE_K=150, RRF_RETENTION_K=150)")
    print("=" * 80)

    ce_pools = [30, 50, 75, 100]
    ce_results = {}

    for ce_k in ce_pools:
        t_start = time.perf_counter()
        ce_ranks = []

        for q in evaluable:
            req_text = q["text"]
            exp_toks = q["expected_tokens"]

            det_hits = engine.det_engine.search(req_text, top_k=150)
            exp_query = engine.terminology_normalizer.build_expanded_query(req_text)
            bm25_hits = engine.bm25_engine.search(exp_query, top_k=150)
            sem_hits = engine.semantic_engine.search(exp_query, top_k=150)

            fused = engine._fuse_hybrid_results(
                query=req_text,
                components=[],
                det_results=det_hits,
                bm25_hits=bm25_hits,
                sem_hits=sem_hits,
                top_k=150,
                mode="hybrid",
                fusion_strategy="rrf"
            )

            ce_pool = list(fused[:ce_k])
            reranked = reranker.rerank_candidates(req_text, ce_pool, top_k=ce_k)
            c_rk = find_match_rank(reranked, exp_toks)
            ce_ranks.append(c_rk)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0 / len(evaluable)
        total_found = sum(1 for r in ce_ranks if r is not None)
        r10 = sum(1 for r in ce_ranks if r is not None and r <= 10)
        hit1 = sum(1 for r in ce_ranks if r == 1)
        hit3 = sum(1 for r in ce_ranks if r is not None and r <= 3)
        mrr = sum(1.0 / r for r in ce_ranks if r is not None) / len(evaluable)

        ce_results[ce_k] = {
            "total_found": total_found,
            "r10": r10, "hit1": hit1, "hit3": hit3,
            "mrr": round(mrr, 3), "latency_ms": round(elapsed_ms, 1)
        }

        print(f"CROSS_ENCODER_POOL_K={ce_k:3d} (avg {elapsed_ms:.1f} ms/query): Found={total_found}/{len(evaluable)} | R@10={r10}/{len(evaluable)} | Hit@1={hit1}, Hit@3={hit3}, MRR={mrr:.3f}")

    # Output experiment summary JSON
    exp_out = {
        "first_stage": first_stage_results,
        "rrf_retention": rrf_results,
        "cross_encoder_pool": ce_results
    }
    with open(os.path.join(ROOT_DIR, "reports", "phase4_pool_sizing_experiment.json"), "w", encoding="utf-8") as f:
        json.dump(exp_out, f, indent=2)
    print("\nSaved experiment results to reports/phase4_pool_sizing_experiment.json")


if __name__ == "__main__":
    run_experiment()
