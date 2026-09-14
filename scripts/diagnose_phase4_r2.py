import os
import sys
import time
import pandas as pd
from typing import List, Dict, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider
from src.retrieval import HybridRetrievalEngine
from src.evaluate import extract_standard_tokens
from src.reranker import get_reranker_instance
from src.extract import extract_from_text

def diagnose():
    print("Loading DB...")
    db = get_default_catalogue_provider()
    engine = HybridRetrievalEngine(db=db)
    reranker = get_reranker_instance()
    df_gt = pd.read_csv("dataset/ground_truth/ground_truth.csv")
    
    print("Running Diagnostics...")
    
    # Trackers
    recall_at = {k: {"DET": 0, "BM25": 0, "SEM": 0, "HYB": 0} for k in [10, 30, 50, 100]}
    failed_queries = []
    lifecycle_counts = {"ACTIVE": 0, "WITHDRAWN": 0, "SUPERSEDED": 0, "UNKNOWN": 0}
    total_valid_queries = 0
    
    # 1. Warm-up
    print("Warming up...")
    _ = engine.search("test query", top_k=5, mode="hybrid+rerank")
    
    for idx, row in df_gt.iterrows():
        req_id = row["requirement_id"]
        req_text = row["requirement_text"]
        gt_raw = str(row["applicable_standard"])
        gt_standards = extract_standard_tokens(gt_raw)
        
        if not gt_standards:
            continue
            
        total_valid_queries += 1
        req = extract_from_text(req_text, requirement_id=req_id)
        q = req_text
        components = req.components
        
        # Get raw candidates up to 100
        det_res = engine.det_engine.search(q, top_k=100, components=components)
        bm25_res = engine.bm25_engine.search(q, top_k=100)
        sem_res = engine.semantic_engine.search(q, top_k=100)
        hyb_res = engine._fuse_hybrid_results(q, components, det_res, bm25_res, sem_res, top_k=100, mode="hybrid")
        
        def get_rank(cands):
            for i, c in enumerate(cands):
                p_tokens = extract_standard_tokens(c.standard_number)
                if any(any(p in g or g in p for g in gt_standards) for p in p_tokens):
                    return i + 1
            return -1

        ranks = {
            "DET": get_rank(det_res),
            "BM25": get_rank(bm25_res),
            "SEM": get_rank(sem_res),
            "HYB": get_rank(hyb_res)
        }
        
        for k in [10, 30, 50, 100]:
            for model in ["DET", "BM25", "SEM", "HYB"]:
                if 0 < ranks[model] <= k:
                    recall_at[k][model] += 1
                    
        # Lifecycle checks on Top-10 HYB
        for c in hyb_res[:10]:
            lifecycle_counts[c.status] = lifecycle_counts.get(c.status, 0) + 1
            
        # Failed Query Analysis (not in top 100 in ANY or specifically HYB)
        if ranks["HYB"] < 0:
            # Check if expected standard exists in DB
            db_matches = []
            with db._get_connection() as conn:
                cur = conn.cursor()
                for gt in gt_standards:
                    cur.execute("SELECT * FROM catalogue_standards WHERE standard_number LIKE ? LIMIT 1", (f"%{gt}%",))
                    r = cur.fetchone()
                    if r: db_matches.append(dict(r))
                    
            failed_queries.append({
                "req_id": req_id,
                "query": q,
                "expected": gt_raw,
                "db_matches": db_matches,
                "ranks": ranks,
                "top_det": [{"std": c.standard_number, "score": c.relevance_score} for c in det_res[:3]],
                "top_bm25": [{"std": c.standard_number, "score": getattr(c, "normalized_score", getattr(c, "score", 0))} for c in bm25_res[:3]],
                "top_sem": [{"std": c.standard_number, "score": getattr(c, "score", 0)} for c in sem_res[:3]],
            })
            
    print("\n--- Recall @ K ---")
    for k in [10, 30, 50, 100]:
        print(f"K={k}: DET={recall_at[k]['DET']} BM25={recall_at[k]['BM25']} SEM={recall_at[k]['SEM']} HYB={recall_at[k]['HYB']}")
        
    print(f"\n--- Lifecycle in Top-10 (over {total_valid_queries} queries) ---")
    print(lifecycle_counts)
    
    print(f"\n--- Failed Queries (HYB Rank < 0) : {len(failed_queries)} ---")
    for fq in failed_queries[:3]:
        print(f"\n[{fq['req_id']}] Expected: {fq['expected']}")
        print(f"Ranks: {fq['ranks']}")
        if fq['db_matches']:
            db_m = fq['db_matches'][0]
            print(f"DB Exists: {db_m['standard_number']} | Title: {db_m['full_title']} | Status: {db_m['status']}")
        else:
            print("DB Exists: NO")
        print(f"DET Top: {fq['top_det']}")
        print(f"BM25 Top: {fq['top_bm25']}")
        print(f"SEM Top: {fq['top_sem']}")
        
    # Reranker Profiling
    print("\n--- Reranker Profiling ---")
    if hyb_res:
        t0 = time.time()
        cands = hyb_res[:30]
        prep_t0 = time.time()
        cand_texts = [reranker.build_candidate_text(db.get_standard(c.standard_id) or {}) for c in cands]
        prep_time = time.time() - prep_t0
        
        inf_t0 = time.time()
        scores = reranker.score_pairs("dummy query", cand_texts)
        inf_time = time.time() - inf_t0
        
        total_time = time.time() - t0
        print(f"Reranking 30 cands - Prep: {prep_time*1000:.1f}ms, Inference: {inf_time*1000:.1f}ms, Total: {total_time*1000:.1f}ms")

if __name__ == "__main__":
    diagnose()
