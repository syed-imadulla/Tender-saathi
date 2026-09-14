import sys, os, time, sqlite3, json, numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider
from src.evaluate import extract_standard_tokens

print("=== 4. CHECK INDEX CORRECTNESS ===")
provider = get_default_catalogue_provider()
with open("data/catalogue/bis_index_manifest.json") as f:
    manifest = json.load(f)
print("Manifest:", manifest)

with open("data/catalogue/bis_semantic_doc_ids.json") as f:
    sem_ids = json.load(f)
sem_emb = np.load("data/catalogue/bis_semantic_embeddings.npy")
print("Semantic doc_ids len:", len(sem_ids))
print("Semantic embeddings shape:", sem_emb.shape)

with open("data/catalogue/bis_bm25_index.json") as f:
    bm25_idx = json.load(f)
print("BM25 doc_ids len:", len(bm25_idx["doc_ids"]))

print("\n=== 6. CHECK DATA DISTRIBUTION ===")
with provider._get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT count(*) FROM catalogue_standards")
    print("Total standards:", c.fetchone()[0])
    c.execute("SELECT status, count(*) FROM catalogue_standards GROUP BY status")
    for row in c.fetchall(): print("Status", row[0], ":", row[1])
    c.execute("SELECT count(*) FROM catalogue_standards WHERE title IS NULL OR title = ''")
    print("Missing title:", c.fetchone()[0])
    c.execute("SELECT count(*) FROM catalogue_standards WHERE aspect IS NULL OR aspect = ''")
    print("Missing aspect:", c.fetchone()[0])
    c.execute("SELECT count(*) FROM catalogue_standards WHERE technical_committee IS NULL OR technical_committee = ''")
    print("Missing technical_committee:", c.fetchone()[0])
    
    c.execute("SELECT AVG(length(title)) FROM catalogue_standards")
    print("Avg title length:", c.fetchone()[0])
    
    # Let's see some prefixes
    c.execute("SELECT prefix, count(*) as cnt FROM catalogue_standards GROUP BY prefix ORDER BY cnt DESC LIMIT 10")
    for row in c.fetchall(): print("Prefix", row[0], ":", row[1])
    
    # Check missing standard identifiers
    c.execute("SELECT count(*) FROM catalogue_standards WHERE standard_number IS NULL OR standard_number = ''")
    print("Missing standard_number:", c.fetchone()[0])

print("\n=== 7. DIAGNOSE THE 3.8 SECOND LATENCY ===")
from src.recommend import StandardsRecommender
from src.extract import extract_from_text

# measure DB load
t0 = time.time()
provider = get_default_catalogue_provider()
t1 = time.time()
print(f"DB Load: {t1-t0:.4f} s")

req = extract_from_text("Supply and installation of Chlorinated Polyvinyl Chloride (CPVC) pipes and fittings for domestic hot and cold water distribution conforming to IS 15778.", requirement_id="test")

# deterministic
rec_det = StandardsRecommender(db=provider, retrieval_mode="deterministic")
t_start = time.time()
res_det = rec_det.recommend_for_requirement(req)
t_end = time.time()
print(f"Deterministic query latency: {t_end - t_start:.4f} s")

# BM25
t_start = time.time()
rec_bm25 = StandardsRecommender(db=provider, retrieval_mode="bm25")
print(f"BM25 initialization: {time.time() - t_start:.4f} s")
t_start = time.time()
res_bm25 = rec_bm25.recommend_for_requirement(req)
print(f"BM25 query latency: {time.time() - t_start:.4f} s")

# Semantic
t_start = time.time()
rec_sem = StandardsRecommender(db=provider, retrieval_mode="semantic")
print(f"Semantic initialization: {time.time() - t_start:.4f} s")
t_start = time.time()
res_sem = rec_sem.recommend_for_requirement(req)
print(f"Semantic query latency: {time.time() - t_start:.4f} s")

print("\n=== 8. CHECK LEGACY PATH LEAKAGE ===")
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), 'r') as f:
                content = f.read()
                if "data/catalogue/catalogue.db" in content:
                    print(f"Legacy catalogue.db found in {file}")
                if "bm25_index.json" in content:
                    if not "bis_" in content:
                        print(f"bm25_index.json found in {file}")

