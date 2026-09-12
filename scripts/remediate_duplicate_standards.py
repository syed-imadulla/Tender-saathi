"""Script: scripts/remediate_duplicate_standards.py
Purpose: Audited, deterministic remediation of duplicate standard IDs in data/standards/standards.db.

Remediates Blocker 1 of Priority 6E:
- Identifies duplicate slug records for IS 1180 (Part 1) and IS 7098 (Part 2).
- Preserves the authoritative, verified records (IS-1180-Part-1-2014 and IS-7098-Part-2-2011).
- Removes the redundant unnormalized slug records (IS-1180-(Part-1)-2014 and IS-7098-(Part-2)-2011).
- Regenerates BM25 index and dense semantic vector embeddings.
- Validates index-to-database parity (exactly 90 records).
- Confirms catalogue.db (502 records) remains intact.
"""

import os
import json
import sqlite3
import numpy as np

from src.standards import StandardsDatabase
from src.bm25_search import BM25Index
from src.semantic_search import SemanticSearchEngine


def remediate_standards_db(db_path: str = "data/standards/standards.db"):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM standards;")
    initial_count = cur.fetchone()[0]
    print(f"Initial physical row count in {db_path}: {initial_count}")

    # Inspect the authoritative records
    cur.execute("SELECT standard_id, standard_number, full_title, source, verification_status FROM standards WHERE standard_id IN ('IS-1180-Part-1-2014', 'IS-7098-Part-2-2011');")
    authoritative = cur.fetchall()
    print("Authoritative records to retain:")
    for r in authoritative:
        print(f"  [RETAIN] {r[0]} | {r[1]} | {r[3]} | {r[4]}")

    if len(authoritative) != 2:
        raise RuntimeError(f"Expected 2 authoritative records, found {len(authoritative)}")

    # Inspect the redundant records
    cur.execute("SELECT standard_id, standard_number, full_title, source, verification_status FROM standards WHERE standard_id IN ('IS-1180-(Part-1)-2014', 'IS-7098-(Part-2)-2011');")
    redundant = cur.fetchall()
    print("Redundant records to remove:")
    for r in redundant:
        print(f"  [REMOVE] {r[0]} | {r[1]} | {r[3]} | {r[4]}")

    if len(redundant) != 2:
        print(f"Warning: Expected 2 redundant records, found {len(redundant)}. (May already be remediated)")
    else:
        # Delete redundant records
        cur.execute("DELETE FROM standards WHERE standard_id IN ('IS-1180-(Part-1)-2014', 'IS-7098-(Part-2)-2011');")
        conn.commit()
        print("Deleted redundant records successfully.")

    # Vacuum database
    cur.execute("VACUUM;")
    conn.commit()

    # Verify counts
    cur.execute("SELECT COUNT(*) FROM standards;")
    final_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT standard_id) FROM standards;")
    distinct_ids = cur.fetchone()[0]
    cur.execute("SELECT standard_id, COUNT(*) FROM standards GROUP BY standard_id HAVING COUNT(*) > 1;")
    dup_ids = cur.fetchall()

    conn.close()

    print(f"\nPost-remediation physical row count: {final_count}")
    print(f"Post-remediation distinct standard_ids: {distinct_ids}")
    print(f"Duplicate standard_ids: {dup_ids}")

    if final_count != 90 or distinct_ids != 90 or len(dup_ids) > 0:
        raise AssertionError(f"Integrity check failed! Expected 90 distinct rows, got {final_count} (distinct: {distinct_ids})")

    print("\n--- REGENERATING SEARCH INDEXES ---")
    db = StandardsDatabase(db_path)

    # 1. Rebuild BM25 Index
    bm25 = BM25Index()
    # Remove existing cache to force clean rebuild
    bm25_cache = os.path.join(os.path.dirname(db_path), "bm25_index.json")
    if os.path.exists(bm25_cache):
        os.remove(bm25_cache)
    bm25.build_from_db(db)
    print(f"BM25 index regenerated with {len(bm25.doc_ids)} documents.")

    # 2. Rebuild Semantic Embeddings
    sem_npy = os.path.join(os.path.dirname(db_path), "semantic_embeddings.npy")
    sem_ids_file = os.path.join(os.path.dirname(db_path), "semantic_doc_ids.json")
    sem_hash_file = os.path.join(os.path.dirname(db_path), "semantic_doc_hashes.json")
    for f in [sem_npy, sem_ids_file, sem_hash_file]:
        if os.path.exists(f):
            os.remove(f)

    sem = SemanticSearchEngine(db=db, cache_dir=os.path.dirname(db_path))
    print(f"Semantic search engine rebuilt with {len(sem.doc_ids)} vectors of shape {sem.doc_embeddings.shape}.")

    # 3. Verify Parity
    with open(bm25_cache, "r", encoding="utf-8") as f:
        bm25_data = json.load(f)
    bm25_ids = bm25_data.get("doc_ids", [])

    with open(sem_ids_file, "r", encoding="utf-8") as f:
        sem_ids = json.load(f)

    sem_emb = np.load(sem_npy)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT standard_id FROM standards ORDER BY rowid;")
    db_ids = [r[0] for r in cur.fetchall()]
    conn.close()

    assert len(db_ids) == 90, f"Expected 90 DB IDs, got {len(db_ids)}"
    assert bm25_ids == db_ids, "BM25 doc_ids do not match DB standard_ids exactly!"
    assert sem_ids == db_ids, "Semantic doc_ids do not match DB standard_ids exactly!"
    assert sem_emb.shape == (90, 384), f"Semantic embeddings shape mismatch: {sem_emb.shape}"

    print("\nPARITY VERIFIED:")
    print(f"  Database Rows:      {len(db_ids)}")
    print(f"  BM25 Documents:     {len(bm25_ids)}")
    print(f"  Semantic Vector IDs: {len(sem_ids)}")
    print(f"  Embedding Array:    {sem_emb.shape}")
    print("  All ID sets and orderings match 100%!")

    # Verify Catalogue DB
    cat_conn = sqlite3.connect("data/catalogue/catalogue.db")
    cat_cur = cat_conn.cursor()
    cat_cur.execute("SELECT COUNT(*) FROM standards;")
    cat_count = cat_cur.fetchone()[0]
    cat_conn.close()
    print(f"\nExpanded catalogue check: {cat_count} records in data/catalogue/catalogue.db (unchanged).")
    assert cat_count == 502, f"catalogue.db record count unexpected: {cat_count}"

    print("\nREMEDIATION OF DUPLICATE STANDARDS COMPLETE (PASS).")


if __name__ == "__main__":
    remediate_standards_db()
