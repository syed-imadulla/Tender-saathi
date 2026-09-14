import csv
import json
import os
import sys

from src.recommend import StandardsRecommender
from src.retrieval import HybridRetrievalEngine
from src.catalogue.provider import get_default_catalogue_provider
from src.extract import extract_from_text

def run_ablation():
    db = get_default_catalogue_provider()
    
    # Load ground truth
    ground_truth = []
    with open("dataset/ground_truth/ground_truth.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("requirement_id") != "T002-R002":
                ground_truth.append(row)
                
    print(f"Evaluatable queries: {len(ground_truth)}")
    
    for k in [10, 15, 20, 30, 50]:
        print(f"\n--- Testing K={k} ---")
        recommender = StandardsRecommender(db=db, candidate_pool_size=k)
        
        correct_recommendations = 0
        hit_at_k_in_recs = 0
        
        for row in ground_truth:
            req_text = row["requirement_text"]
            expected_str = row["applicable_standard"]
            expected_standards = [s.strip() for s in expected_str.split(";")]
            
            res = recommender.recommend_for_text(req_text, req_id=row["requirement_id"])
            
            final_cand = res.candidate_standard
            if final_cand and any(s.startswith(final_cand) or final_cand.startswith(s) for s in expected_standards):
                correct_recommendations += 1
                
            # Check if expected standard is anywhere in the recommendations
            if any(any(r.standard_number.startswith(s) or s.startswith(r.standard_number) for s in expected_standards) for r in res.recommendations):
                hit_at_k_in_recs += 1
                
        print(f"K={k} -> Final Recommendation Accuracy: {correct_recommendations}/{len(ground_truth)} ({correct_recommendations/len(ground_truth)*100:.2f}%)")
        print(f"K={k} -> Expected in Applicability Gate pass pool: {hit_at_k_in_recs}/{len(ground_truth)}")

if __name__ == '__main__':
    run_ablation()
