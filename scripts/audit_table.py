import sys, os, time, sqlite3, json, numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.evaluate import extract_standard_tokens

provider = get_default_catalogue_provider()

# Check legacy
conn_legacy = sqlite3.connect("data/catalogue/catalogue.db")
cur_legacy = conn_legacy.cursor()
cur_legacy.execute("SELECT standard_number, standard_id FROM standards")
legacy_standards = {row[0]: row[1] for row in cur_legacy.fetchall()}

# Ground truth
df_gt = pd.read_csv("dataset/ground_truth/ground_truth.csv")

# Load bm25 doc_ids to check index
with open("data/catalogue/bis_bm25_index.json") as f:
    bm25_idx = json.load(f)
bm25_docs = set(bm25_idx["doc_ids"])

# Load semantic doc_ids
with open("data/catalogue/bis_semantic_doc_ids.json") as f:
    sem_docs = set(json.load(f))

def get_rank_from_res(rec_res, gt_standards):
    for rank, r in enumerate(rec_res.recommendations[:5], 1):
        p_tokens = extract_standard_tokens(r.standard_number)
        if any(any(p in g or g in p for g in gt_standards) for p in p_tokens):
            return rank, [x.standard_number for x in rec_res.recommendations[:3]]
    return -1, [x.standard_number for x in rec_res.recommendations[:3]]

print("Initializing recommenders...")
rec_det = StandardsRecommender(db=provider, retrieval_mode="deterministic")
rec_bm25 = StandardsRecommender(db=provider, retrieval_mode="bm25")
rec_sem = StandardsRecommender(db=provider, retrieval_mode="semantic")
rec_hyb = StandardsRecommender(db=provider, retrieval_mode="hybrid")

print("Processing 20 queries...")
for idx, row in df_gt.iterrows():
    req_id = row["requirement_id"]
    req_text = row["requirement_text"]
    gt_standard_raw = str(row["applicable_standard"])
    gt_standards = extract_standard_tokens(gt_standard_raw)
    
    if not gt_standards:
        continue # skip abstainers for the table since they don't have expected IDs
        
    req_obj = extract_from_text(req_text, requirement_id=req_id)
    
    rank_det, top3_det = get_rank_from_res(rec_det.recommend_for_requirement(req_obj), gt_standards)
    rank_bm25, top3_bm25 = get_rank_from_res(rec_bm25.recommend_for_requirement(req_obj), gt_standards)
    rank_sem, top3_sem = get_rank_from_res(rec_sem.recommend_for_requirement(req_obj), gt_standards)
    rank_hyb, top3_hyb = get_rank_from_res(rec_hyb.recommend_for_requirement(req_obj), gt_standards)
    
    in_bis = False
    in_legacy = False
    in_bm25_idx = False
    in_sem_idx = False
    
    expected_ids = []
    
    with provider._get_connection() as c:
        cursor = c.cursor()
        for g in gt_standards:
            cursor.execute("SELECT canonical_id FROM catalogue_standards WHERE standard_number LIKE ?", (f"%{g}%",))
            rows = cursor.fetchall()
            if rows:
                in_bis = True
                for r in rows:
                    cid = r[0]
                    expected_ids.append(cid)
                    if cid in bm25_docs: in_bm25_idx = True
                    if cid in sem_docs: in_sem_idx = True
            
            for k in legacy_standards:
                if g in k: in_legacy = True

    print(f"\n--- {req_id} ---")
    print(f"Query: {req_text[:80]}")
    print(f"Expected: {gt_standard_raw}")
    print(f"Expected IDs in DB: {expected_ids}")
    print(f"In BIS: {in_bis}, In Legacy: {in_legacy}, In BM25: {in_bm25_idx}, In Sem: {in_sem_idx}")
    print(f"Ranks -> Det: {rank_det}, BM25: {rank_bm25}, Sem: {rank_sem}, Hyb: {rank_hyb}")
    if rank_hyb == -1:
        print(f"Top 3 Hyb: {top3_hyb}")
