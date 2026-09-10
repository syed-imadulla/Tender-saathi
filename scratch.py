import sys
sys.path.append(".")
from src.recommend import StandardsRecommender
from src.standards import StandardsDatabase

from src.extract import extract_from_text
db = StandardsDatabase()
req = extract_from_text("Procurement of valves conforming to IS 10611")
print(req)

res = db.get_standard("IS 10611")
print(f"DB result for IS 10611: {res}")

