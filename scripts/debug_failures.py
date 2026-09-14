import json

with open("reports/phase4r8_accuracy_improvement.json", "r") as f:
    data = json.load(f)

for trace in data["Combined"]["traces"]:
    if not trace.get("recommendation_correct"):
        print(f"ID: {trace['requirement_id']}")
        print(f"  Exp: {trace['expected_standard']}")
        print(f"  Rank: {trace['first_stage_rank']}")
        print(f"  Applicability: {trace['applicability_decision']}")
        print(f"  Ambiguity: {trace.get('ambiguity_state')}")
        print(f"  Reason: {trace.get('taxonomy_reason')}")
        print(f"  Final: {trace.get('final_recommended_standard')}")
        print(f"  Review Candidate: {trace.get('candidate_for_review')}")
        print("-" * 40)
