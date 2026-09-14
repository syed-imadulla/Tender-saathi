import csv, json
from src.extract import extract_from_text
from src.recommend import StandardsRecommender
from src.catalogue.normalizer import StandardIdentifierNormalizer

recommender = StandardsRecommender(retrieval_mode='hybrid')
engine = recommender.search_engine
app_gate = recommender.applicability_gate

def find_rank(items, target_tokens):
    for idx, item in enumerate(items, 1):
        s = getattr(item, 'standard_number', '') or (item.get('standard_number') if isinstance(item, dict) else '')
        norm_s = StandardIdentifierNormalizer.parse(s)
        base_s = (norm_s.prefix + ' ' + norm_s.base_number).strip().lower() if norm_s else s.strip().lower()
        for t in target_tokens:
            norm_t = StandardIdentifierNormalizer.parse(t)
            base_t = (norm_t.prefix + ' ' + norm_t.base_number).strip().lower() if norm_t else t.strip().lower()
            if base_s == base_t:
                # Also check part if target has part
                if norm_t and norm_t.part is not None:
                    if norm_s and norm_s.part == norm_t.part:
                        return idx
                else:
                    return idx
    return None

def standards_match(cand_s, target_tokens):
    norm_s = StandardIdentifierNormalizer.parse(cand_s)
    base_s = (norm_s.prefix + ' ' + norm_s.base_number).strip().lower() if norm_s else cand_s.strip().lower()
    for t in target_tokens:
        norm_t = StandardIdentifierNormalizer.parse(t)
        base_t = (norm_t.prefix + ' ' + norm_t.base_number).strip().lower() if norm_t else t.strip().lower()
        if base_s == base_t:
            if norm_t and norm_t.part is not None:
                if norm_s and norm_s.part == norm_t.part:
                    return True
            else:
                return True
    return False

with open('dataset/ground_truth/ground_truth.csv') as f:
    evaluable = [r for r in csv.DictReader(f) if r['verification_outcome'] != 'NEEDS_EXPERT_VERIFICATION']

results = []

for idx, r in enumerate(evaluable, 1):
    req_id = r['requirement_id']
    text = r['requirement_text']
    exp_str = r['applicable_standard']
    exp_tokens = [t.strip() for t in exp_str.split(';') if t.strip()]
    
    # 1. Deterministic
    det_hits = engine.det_engine.search(text, top_k=100)
    det_rank = find_rank(det_hits, exp_tokens)
    
    # 2. BM25
    bm25_hits = engine.bm25_engine.search(text, top_k=100)
    bm25_rank = find_rank(bm25_hits, exp_tokens)
    
    # 3. Semantic
    sem_hits = engine.semantic_engine.search(text, top_k=100)
    sem_rank = find_rank(sem_hits, exp_tokens)
    
    # 4. Fused (top 100)
    fused_hits = engine.search(text, top_k=100, mode='hybrid')
    fused_rank = find_rank(fused_hits, exp_tokens)
    
    # 5. Full Recommender Workflow
    req_obj = extract_from_text(text, requirement_id=req_id)
    rec_res = recommender.recommend_for_requirement(req_obj)
    final_std = rec_res.candidate_standard or "NONE"
    final_is_correct = standards_match(final_std, exp_tokens)
    
    # Check dimensions
    retrieval_correct = (fused_rank is not None and fused_rank <= 100)
    
    # Check applicability
    app_eval = app_gate.evaluate_candidate(
        candidate=fused_hits[0] if fused_hits else None,
        requirement_text=text
    ) if fused_hits else None
    
    # Final recommendation applicability
    if rec_res.candidate_standard:
        final_app = rec_res.applicability.get("applicable", True) if rec_res.applicability else True
    else:
        final_app = True # Clean abstention
        
    identity_correct = (rec_res.candidate_standard == rec_res.evidence_standard) if rec_res.candidate_standard else True
    provenance_valid = bool(rec_res.provenance)
    lifecycle_valid = rec_res.status not in ["WITHDRAWN", "SUPERSEDED"]
    
    # Classify failure taxonomy
    if final_is_correct:
        fail_cat = "TOP1_CORRECT"
        fail_reason = "Final recommendation matches ground truth."
    elif fused_rank is None and det_rank is None and bm25_rank is None and sem_rank is None:
        fail_cat = "A"
        fail_reason = "Expected candidate was never retrieved in deterministic, BM25, or semantic pools."
    elif (bm25_rank is not None and bm25_rank <= 10) or (sem_rank is not None and sem_rank <= 10):
        if fused_rank is not None and fused_rank > 10:
            fail_cat = "B"
            fail_reason = f"Candidate retrieved in individual engine (BM25={bm25_rank}, Sem={sem_rank}) but pushed down to rank {fused_rank} during RRF fusion."
        else:
            fail_cat = "E"
            fail_reason = f"Candidate was in fused top-10 (rank {fused_rank}), but another candidate was selected or preferred by recommender."
    elif fused_rank is not None and fused_rank > 10:
        fail_cat = "B"
        fail_reason = f"Candidate retrieved at deep rank {fused_rank} (>10), not in top candidate consideration pool."
    elif fused_rank is not None and fused_rank <= 10:
        fail_cat = "E"
        fail_reason = f"Candidate in top-10 (rank {fused_rank}) but competing candidate outranked it."
    else:
        fail_cat = "A"
        fail_reason = "Zero retrieval across all engines."
        
    trace_entry = {
        "index": idx,
        "requirement_id": req_id,
        "query": text,
        "expected_standard": exp_str,
        "final_recommendation": final_std,
        "final_is_correct": final_is_correct,
        "retrieval_correct": retrieval_correct,
        "applicability_valid": final_app,
        "identity_correct": identity_correct,
        "provenance_valid": provenance_valid,
        "lifecycle_valid": lifecycle_valid,
        "det_rank": det_rank,
        "bm25_rank": bm25_rank,
        "sem_rank": sem_rank,
        "fused_rank": fused_rank,
        "failure_category": fail_cat,
        "failure_reason": fail_reason
    }
    results.append(trace_entry)
    print(f"[{idx:02d}/19] {req_id} | Cat: {fail_cat:12} | Rec: {final_std:22} | Exp: {exp_str[:35]}")

with open('reports/all_19_queries_trace.json', 'w') as f:
    json.dump(results, f, indent=2)

print('\nSaved traces to reports/all_19_queries_trace.json')
