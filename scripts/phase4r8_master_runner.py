import os
import subprocess
import json
from datetime import datetime

REPORT_MD = "reports/phase4r8_accuracy_improvement.md"
REPORT_JSON = "reports/phase4r8_accuracy_improvement.json"

def run_eval(env_vars, run_name):
    print(f"\n--- Running: {run_name} ---")
    env = os.environ.copy()
    env.update(env_vars)
    env["PYTHONPATH"] = "."
    # Suppress output to keep logs clean
    subprocess.run([".venv/bin/python", "scripts/evaluate_phase4r6_retrieval_and_applicability.py"], env=env, check=True, stdout=subprocess.DEVNULL)
    
    with open("reports/phase4r6_retrieval_correctness_audit.json", "r") as f:
        audit = json.load(f)
    with open("reports/all_19_queries_trace.json", "r") as f:
        traces = json.load(f)
        
    return {"audit": audit, "traces": traces}

def extract_metric(audit, metric_key):
    metrics = audit.get("quantitative_retrieval_metrics", {})
    return metrics.get(metric_key, "UNKNOWN")

def main():
    print("Starting Phase 4R8 Master Runner...")
    
    results = {}
    
    # 1. R7 Baseline
    results["R7_Baseline"] = run_eval({"R8_ABLATE_K": "15", "R8_ABLATE_ARBITRATION": "false", "R8_ABLATE_AMBIGUITY": "false"}, "R7 Baseline")
    
    # 2. K Ablation
    for k in [10, 15, 20, 30, 50, 75, 100]:
        results[f"K_{k}"] = run_eval({"R8_ABLATE_K": str(k), "R8_ABLATE_ARBITRATION": "false", "R8_ABLATE_AMBIGUITY": "false"}, f"K={k}")
        
    # 3. Arbitration Only
    results["Arbitration_Only"] = run_eval({"R8_ABLATE_K": "15", "R8_ABLATE_ARBITRATION": "true", "R8_ABLATE_AMBIGUITY": "false"}, "Arbitration Only")
    
    # 4. Ambiguity Only
    results["Ambiguity_Only"] = run_eval({"R8_ABLATE_K": "15", "R8_ABLATE_ARBITRATION": "false", "R8_ABLATE_AMBIGUITY": "true"}, "Ambiguity Only")
    
    # 5. Combined (K=30, Arbitration=True, Ambiguity=True)
    results["Combined"] = run_eval({"R8_ABLATE_K": "30", "R8_ABLATE_ARBITRATION": "true", "R8_ABLATE_AMBIGUITY": "true"}, "Combined")

    # Build Report
    md = []
    md.append("# PHASE 4R8.0 FINAL RECOMMENDATION ACCURACY REPORT\n")
    md.append("## 1. K Ablation Results")
    md.append("| Candidate Pool (K) | Final Rec Accuracy | Hit@1 | Recall@100 | Identity Lineage |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    
    k_res = {}
    for k in [10, 15, 20, 30, 50, 75, 100]:
        audit = results[f"K_{k}"]["audit"]
        acc = extract_metric(audit, "Final_Recommendation_Accuracy")
        hit1 = extract_metric(audit, "Hit@1")
        rec100 = extract_metric(audit, "Recall@100")
        ident = extract_metric(audit, "Identity_Correctness")
        md.append(f"| {k} | {acc} | {hit1} | {rec100} | {ident} |")
        k_res[str(k)] = {"accuracy": acc, "hit1": hit1, "recall100": rec100}
        
    md.append("\n## 2. Component Ablation")
    md.append("| Configuration | Final Rec Accuracy | Hit@1 | Recall@100 | Identity Lineage |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    for name in ["R7_Baseline", "Arbitration_Only", "Ambiguity_Only", "Combined"]:
        audit = results[name]["audit"]
        acc = extract_metric(audit, "Final_Recommendation_Accuracy")
        hit1 = extract_metric(audit, "Hit@1")
        rec100 = extract_metric(audit, "Recall@100")
        ident = extract_metric(audit, "Identity_Correctness")
        md.append(f"| {name} | {acc} | {hit1} | {rec100} | {ident} |")
        
    md.append("\n## 3. Per-Query Improvement Table (12 Lost Recommendations in R7)")
    md.append("| Req ID | Expected Standard | R7 Final | R8 Combined Final | R7 Stage Rank | R8 Result | Change Responsible | Human Review |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    r7_traces = {t["requirement_id"]: t for t in results["R7_Baseline"]["traces"]}
    r8_traces = {t["requirement_id"]: t for t in results["Combined"]["traces"]}
    
    # The 12 lost recommendations are those where R7 Final != Expected
    # In evaluate script, they match if final_std is in expected_str (which might be ; separated)
    def is_match(final_std, expected_str):
        if not final_std or final_std == "NONE" or final_std == "None": return False
        return any(final_std.startswith(s.strip()) or s.strip().startswith(final_std) for s in expected_str.split(";"))

    lost_count = 0
    recovered_count = 0
    for req_id, r7_t in r7_traces.items():
        exp = r7_t.get("expected_standard", "UNKNOWN")
        r7_final = r7_t.get("final_recommendation", "NONE")
        if not is_match(r7_final, exp):
            lost_count += 1
            r8_t = r8_traces[req_id]
            r8_final = r8_t.get("final_recommendation", "NONE")
            
            status = "STILL LOST"
            if is_match(r8_final, exp):
                status = "RECOVERED"
                recovered_count += 1
            elif r8_t.get("candidate_for_review"):
                if is_match(r8_t.get("candidate_for_review"), exp):
                    status = "PRESERVED FOR REVIEW"
                    
            hr = r8_t.get("human_review_required", False)
            rank = r7_t.get("first_stage_rank", ">100")
            md.append(f"| {req_id} | {exp} | {r7_final} | {r8_final} | {rank} | {status} | Combined Fix | {hr} |")

    md.append(f"\nTotal Recovered: {recovered_count}/{lost_count}")
    
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(md))
        
    with open(REPORT_JSON, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"Master Runner complete! Generated {REPORT_MD}")

if __name__ == "__main__":
    main()
