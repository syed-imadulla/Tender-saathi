"""
scripts/experiment_depth_and_terminology.py — Test retrieval depth and terminology expansion.
"""

import os
import sys
import time
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider
from src.retrieval import HybridRetrievalEngine
from src.decompose import decompose_requirement
from src.evaluate import extract_standard_tokens
from src.terminology import TechnicalTerminologyNormalizer
from scripts.evaluate_phase4_r2_1_fusion import match_standard


def run_experiment():
    provider = get_default_catalogue_provider()
    engine = HybridRetrievalEngine(db=provider, fusion_strategy="rrf")
    normalizer = TechnicalTerminologyNormalizer()

    gt_path = os.path.join(ROOT_DIR, "dataset", "ground_truth", "ground_truth.csv")
    df_gt = pd.read_csv(gt_path)
    df_bench = df_gt[df_gt["applicable_standard"].notna() & (df_gt["applicable_standard"].astype(str).str.strip() != "")].copy()
    num_q = len(df_bench)

    print(f"Evaluating {num_q} benchmark queries across depth boundaries and terminology expansion...\n")

    for use_term in [False, True]:
        label = "WITH Controlled Terminology Expansion" if use_term else "WITHOUT Terminology Expansion (Raw Query)"
        print(f"================================================================================")
        print(f"CONFIGURATION: {label}")
        print(f"================================================================================")

        for depth_k in [100, 150, 200, 300]:
            union_hits = {30: 0, 50: 0, 100: 0, 150: 0, 200: 0, 300: 0}
            det_hits = 0
            bm25_hits_count = 0
            sem_hits_count = 0
            rrf_r10 = 0
            rrf_r30 = 0
            rrf_r100 = 0
            ce_hit1 = 0
            ce_hit3 = 0
            ce_r10 = 0
            latencies = []

            for idx, row in df_bench.iterrows():
                req_text = str(row["requirement_text"]).strip()
                gt_raw = str(row["applicable_standard"]).strip()
                expected_tokens = extract_standard_tokens(gt_raw)

                query_to_use = normalizer.build_expanded_query(req_text) if use_term else req_text
                decomp = decompose_requirement(query_to_use)

                t0 = time.perf_counter()
                det_res = engine.det_engine.search(query_to_use, top_k=depth_k, components=decomp.components)
                bm25_res = engine.bm25_engine.search(query_to_use, top_k=depth_k)
                sem_res = engine.semantic_engine.search(query_to_use, top_k=depth_k)

                # Union tracking
                for k_bound in [30, 50, 100, 150, 200, 300]:
                    if k_bound <= depth_k:
                        found = any(match_standard(expected_tokens, r.standard_number, r.standard_id) for r in det_res[:k_bound]) or \
                                any(match_standard(expected_tokens, h.standard_number, h.standard_id) for h in bm25_res[:k_bound]) or \
                                any(match_standard(expected_tokens, s.standard_number, s.standard_id) for s in sem_res[:k_bound])
                        if found:
                            union_hits[k_bound] += 1

                # Individual retrievers at depth_k
                if any(match_standard(expected_tokens, r.standard_number, r.standard_id) for r in det_res):
                    det_hits += 1
                if any(match_standard(expected_tokens, h.standard_number, h.standard_id) for h in bm25_res):
                    bm25_hits_count += 1
                if any(match_standard(expected_tokens, s.standard_number, s.standard_id) for s in sem_res):
                    sem_hits_count += 1

                # RRF Fusion
                fused = engine._fuse_hybrid_results(
                    query=query_to_use,
                    components=decomp.components,
                    det_results=det_res,
                    bm25_hits=bm25_res,
                    sem_hits=sem_res,
                    top_k=depth_k,
                    mode="hybrid",
                    fusion_strategy="rrf"
                )

                fused_rank = None
                for r_idx, res in enumerate(fused):
                    if match_standard(expected_tokens, res.standard_number, res.standard_id):
                        fused_rank = r_idx + 1
                        break

                if fused_rank:
                    if fused_rank <= 10:
                        rrf_r10 += 1
                    if fused_rank <= 30:
                        rrf_r30 += 1
                    if fused_rank <= 100:
                        rrf_r100 += 1

                # Cross encoder top 30
                ce_res = engine._fuse_hybrid_results(
                    query=query_to_use,
                    components=decomp.components,
                    det_results=det_res,
                    bm25_hits=bm25_res,
                    sem_hits=sem_res,
                    top_k=10,
                    mode="hybrid+rerank",
                    fusion_strategy="rrf",
                    rerank_pool_size=30
                )
                ce_rank = None
                for r_idx, res in enumerate(ce_res):
                    if match_standard(expected_tokens, res.standard_number, res.standard_id):
                        ce_rank = r_idx + 1
                        break
                if ce_rank:
                    if ce_rank == 1:
                        ce_hit1 += 1
                    if ce_rank <= 3:
                        ce_hit3 += 1
                    if ce_rank <= 10:
                        ce_r10 += 1

                t_total = (time.perf_counter() - t0) * 1000.0
                latencies.append(t_total)

            avg_lat = np.mean(latencies)
            print(f"Depth K={depth_k}:")
            print(f"  Single Retrievers: DET={det_hits}/{num_q}, BM25={bm25_hits_count}/{num_q}, SEM={sem_hits_count}/{num_q}")
            print(f"  Union Recall: @30={union_hits[30]}/{num_q}, @50={union_hits[50]}/{num_q}, @100={union_hits[100]}/{num_q}, @150={union_hits[150]}/{num_q}, @{depth_k}={union_hits[depth_k]}/{num_q}")
            print(f"  RRF Fusion:   R@10={rrf_r10}/{num_q}, R@30={rrf_r30}/{num_q}, R@100={rrf_r100}/{num_q}")
            print(f"  CrossEncoder: Hit@1={ce_hit1}/{num_q}, Hit@3={ce_hit3}/{num_q}, R@10={ce_r10}/{num_q}")
            print(f"  Avg Latency:  {avg_lat:.1f} ms\n")


if __name__ == "__main__":
    run_experiment()
