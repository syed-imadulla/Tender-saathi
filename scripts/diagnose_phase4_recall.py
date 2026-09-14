import sys, os, time, json
import pandas as pd
import warnings

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

warnings.filterwarnings("ignore")

from src.catalogue.provider import get_default_catalogue_provider
from src.retrieval import HybridRetrievalEngine
from src.extract import extract_from_text
from src.evaluate import extract_standard_tokens
from src.applicability import ApplicabilityGate
from src.reranker import get_reranker_instance

def main():
    print("Loading databases and indices...")
    t0 = time.time()
    db = get_default_catalogue_provider()
    # Preload DB schema / connection
    with db._get_connection() as c:
        pass
    db_load_time = time.time() - t0

    print("Initializing engines...")
    engine = HybridRetrievalEngine(db=db)
    reranker = get_reranker_instance()
    app_gate = ApplicabilityGate()
    
    df_gt = pd.read_csv("dataset/ground_truth/ground_truth.csv")
    
    print("\nStarting diagnostics...")
    
    results = []
    
    for idx, row in df_gt.iterrows():
        req_id = row["requirement_id"]
        req_text = row["requirement_text"]
        gt_standard_raw = str(row["applicable_standard"])
        gt_standards = extract_standard_tokens(gt_standard_raw)
        
        if not gt_standards:
            continue
            
        req = extract_from_text(req_text, requirement_id=req_id)
        query_clean = req.requirement_text.strip()
        components = getattr(req, "components", [])
        
        stage_times = {}
        
        # 1. Deterministic
        t0 = time.time()
        det_results = engine.det_engine.search(query_clean, top_k=100, components=components)
        stage_times["deterministic"] = time.time() - t0
        
        # 2. BM25
        t0 = time.time()
        bm25_hits = engine.bm25_engine.search(query_clean, top_k=100)
        stage_times["bm25"] = time.time() - t0
        
        # 3. Semantic
        t0 = time.time()
        sem_hits = engine.semantic_engine.search(query_clean, top_k=100)
        stage_times["semantic"] = time.time() - t0
        
        # 4. Hybrid Merge (we use our own modified call to get 100)
        t0 = time.time()
        hyb_results = engine._fuse_hybrid_results(
            query=query_clean,
            components=components,
            det_results=det_results,
            bm25_hits=bm25_hits,
            sem_hits=sem_hits,
            top_k=100,
            mode="hybrid"
        )
        stage_times["hybrid_merge"] = time.time() - t0
        
        # 5. Candidate Hydration (already done in _fuse_hybrid_results partly, but let's measure formatting)
        # We will skip direct candidate hydration timing because it's baked into search/merge.
        stage_times["candidate_hydration"] = 0.0 # Will estimate or leave 0

        # 6. Cross-Encoder
        t0 = time.time()
        if reranker and hyb_results:
            candidate_texts = [
                reranker.build_candidate_text(db.get_standard(cand.standard_id) or {})
                for cand in hyb_results
            ]
            rerank_scores = reranker.score_pairs(query_clean, candidate_texts)
            for cand, score in zip(hyb_results, rerank_scores):
                cand.reranker_score = score
            
            hyb_results.sort(key=lambda x: x.reranker_score or 0.0, reverse=True)
        stage_times["cross_encoder"] = time.time() - t0
        
        # 7. Applicability Gate
        t0 = time.time()
        app_passed = 0
        for cand in hyb_results[:10]: # Only run on top 10 for timing
            res = app_gate.evaluate_candidate(cand, query_clean, components=components)
            if res.applicable: app_passed += 1
        stage_times["applicability"] = time.time() - t0
        
        def find_rank(candidates):
            for i, cand in enumerate(candidates):
                p_tokens = extract_standard_tokens(cand.standard_number)
                if any(any(p in g or g in p for g in gt_standards) for p in p_tokens):
                    return i + 1
            return -1
            
        rank_det = find_rank(det_results)
        
        # BM25 returns hits, convert to search results for uniform check
        bm25_res = engine._convert_bm25_to_search_results(bm25_hits, 100)
        rank_bm25 = find_rank(bm25_res)
        
        sem_res = engine._convert_semantic_to_search_results(sem_hits, 100)
        rank_sem = find_rank(sem_res)
        
        rank_hyb = find_rank(hyb_results)
        # rank_hyb here is after reranker because we sorted it in place. Let's do hybrid without reranker too.
        # Wait, we sorted hyb_results in place. Let's re-fuse to get raw hybrid.
        raw_hyb = engine._fuse_hybrid_results(
            query=query_clean,
            components=components,
            det_results=det_results,
            bm25_hits=bm25_hits,
            sem_hits=sem_hits,
            top_k=100,
            mode="hybrid"
        )
        rank_raw_hyb = find_rank(raw_hyb)
        
        print(f"[{req_id}] DET:{rank_det} BM25:{rank_bm25} SEM:{rank_sem} HYB:{rank_raw_hyb} RERANK:{rank_hyb} " +
              f"| Latency(ms): DET:{stage_times['deterministic']*1000:.0f} BM25:{stage_times['bm25']*1000:.0f} SEM:{stage_times['semantic']*1000:.0f} MERGE:{stage_times['hybrid_merge']*1000:.0f} RERANK:{stage_times['cross_encoder']*1000:.0f} APP:{stage_times['applicability']*1000:.0f}")

if __name__ == "__main__":
    main()
