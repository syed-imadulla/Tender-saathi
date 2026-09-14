import csv
import json
import os
import sys
import subprocess
from datetime import datetime

from src.recommend import StandardsRecommender
from src.retrieval import HybridRetrievalEngine
from src.catalogue.provider import get_default_catalogue_provider
from src.extract import extract_from_text

def get_git_info():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
        return commit, branch
    except Exception:
        return "Unknown", "Unknown"

def trace_baseline():
    db = get_default_catalogue_provider()
    recommender = StandardsRecommender(db=db, candidate_pool_size=15)
    
    ground_truth = []
    with open("dataset/ground_truth/ground_truth.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("requirement_id") != "T002-R002":
                ground_truth.append(row)
                
    results = []
    correct = 0
    hit_1 = 0
    recall_100 = 0
    candidate_survival = 0
    applicability_survival = 0
    
    for row in ground_truth:
        req_text = row["requirement_text"]
        expected_str = row["applicable_standard"]
        expected_standards = [s.strip() for s in expected_str.split(";")]
        primary_expected = expected_standards[0]
        
        # 1. First stage retrieval rank
        search_res = recommender.search_engine.search(req_text, top_k=100)
        first_stage_rank = ">100"
        for i, cand in enumerate(search_res):
            if any(s.startswith(cand.standard_number) or cand.standard_number.startswith(s) for s in expected_standards):
                first_stage_rank = i + 1
                if i == 0:
                    hit_1 += 1
                if i < 100:
                    recall_100 += 1
                break
                
        first_stage_top1 = search_res[0].standard_number if search_res else "None"
        
        # Determine candidate survival
        survived_pool = False
        if isinstance(first_stage_rank, int) and first_stage_rank <= recommender.candidate_pool_size:
            candidate_survival += 1
            survived_pool = True
            
        # Recommendation
        res = recommender.recommend_for_text(req_text, req_id=row["requirement_id"])
        
        # Determine Applicability Survival
        survived_app = False
        if res.applicability and "VIABLE_CANDIDATE" in res.applicability_status: # or similar
             pass
        # Better: check if expected standard is in the recommendations
        if any(any(s.startswith(r.standard_number) or r.standard_number.startswith(s) for s in expected_standards) for r in res.recommendations):
            applicability_survival += 1
            survived_app = True
            
        final_cand = res.candidate_standard
        is_correct = False
        if final_cand and any(s.startswith(final_cand) or final_cand.startswith(s) for s in expected_standards):
            if not res.human_review_required or final_cand: 
                # Wait, the rule is if candidate is candidate_for_review but final=null, it's not correct.
                # Currently the code sets candidate_standard=None for review_required in ambiguous cases.
                # So if candidate_standard is set, it's the final recommendation.
                is_correct = True
                correct += 1
                
        # candidate role & arbitration reason
        top_rec_role = res.standard_role
        
        trace = {
            "requirement_id": row["requirement_id"],
            "expected_standard": primary_expected,
            "first_stage_rank": first_stage_rank,
            "first_stage_top1": first_stage_top1,
            "candidate_pool_size": 15,
            "candidate_survived_pool": survived_pool,
            "applicability_decision": res.applicability_status,
            "ambiguity_decision": res.ambiguity_state,
            "candidate_role": top_rec_role,
            "final_arbitration_reason": res.reason,
            "final_recommendation": final_cand,
            "final_recommendation_correct": is_correct
        }
        results.append(trace)
        
    commit, branch = get_git_info()
    baseline = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "git_commit": commit,
            "git_branch": branch,
            "candidate_pool_size": 15,
            "total_evaluable": len(ground_truth)
        },
        "metrics": {
            "final_recommendation_accuracy": f"{correct}/{len(ground_truth)}",
            "hit_at_1": f"{hit_1}/{len(ground_truth)}",
            "recall_at_100": f"{recall_100}/{len(ground_truth)}",
            "candidate_survival": f"{candidate_survival}/{len(ground_truth)}",
            "applicability_survival": f"{applicability_survival}/{len(ground_truth)}"
        },
        "traces": results
    }
    
    os.makedirs("reports", exist_ok=True)
    with open("reports/phase4r8_r7_baseline.json", "w") as f:
        json.dump(baseline, f, indent=4)
        
    print("Baseline trace saved to reports/phase4r8_r7_baseline.json")
    print(json.dumps(baseline["metrics"], indent=4))

if __name__ == '__main__':
    trace_baseline()
