import sys
sys.path.append(".")
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.validate import validate_standard_status
from src.standards import StandardsDatabase
db = StandardsDatabase()
req = extract_from_text("Procurement of valves conforming to IS 10611")
print(req)

recommender = StandardsRecommender(db, retrieval_mode="hybrid")

rec = recommender.recommend_for_text("Procurement of valves conforming to IS 10611")

print(f"Top recommendation: {rec.candidate_standard}")
print(f"Critic Result: {rec.critic_result}")
print(f"Risk Reasons: {rec.risk_reasons}")
print(f"Why this: {rec.why_this}")
print(f"Why not: {rec.why_not}")
if rec.recommendations:
    print(f"Warning: {rec.recommendations[0].superseded_warning}")
for i, r in enumerate(rec.recommendations):
    print(f"{i}: {r.standard_number} - score: {r.final_score} - {r.superseded_warning}")

