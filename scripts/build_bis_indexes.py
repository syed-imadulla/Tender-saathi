"""
scripts/build_bis_indexes.py — Build isolated BM25 and Semantic vector indexes for the BIS catalogue.

Usage:
    python3 -m scripts.build_bis_indexes [--force] [--batch-size 256]
"""

import os
import sys
import time
import argparse
import logging
import sqlite3
import numpy as np

# Ensure project root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider, BISCatalogueProvider
from src.bm25_search import BM25SearchEngine
from src.semantic_search import SemanticSearchEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_bis_indexes")


def main():
    parser = argparse.ArgumentParser(description="Build BIS search indexes for TenderSaathi")
    parser.add_argument("--db-path", default="data/catalogue/bis_catalogue.db", help="Path to BIS catalogue SQLite database")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if index exists")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size for sentence transformer encoding")
    args = parser.parse_args()

    # Invariant Check: Verify catalogue.db exists and has exactly 502 records
    legacy_db = os.path.join(ROOT_DIR, "data/catalogue/catalogue.db")
    if os.path.exists(legacy_db):
        con_leg = sqlite3.connect(legacy_db)
        cur_leg = con_leg.cursor()
        cur_leg.execute("SELECT count(*) FROM standards")
        legacy_count = cur_leg.fetchone()[0]
        con_leg.close()
        logger.info("Verified legacy catalogue (%s): %d records (UNTOUCHED)", legacy_db, legacy_count)
        assert legacy_count == 502, f"Expected 502 in catalogue.db, found {legacy_count}"

    t0 = time.perf_counter()
    logger.info("Initializing BISCatalogueProvider for %s...", args.db_path)
    provider = BISCatalogueProvider(db_path=args.db_path)
    total_records = provider.get_total_count()
    logger.info("Dynamic catalogue record count: %d standards", total_records)

    # 1. Build / Load BM25 Index
    bm25_cache_file = "bis_bm25_index.json"
    bm25_path = os.path.join(ROOT_DIR, "data/catalogue", bm25_cache_file)
    if args.force and os.path.exists(bm25_path):
        os.remove(bm25_path)
        logger.info("Removed existing BM25 cache for force rebuild: %s", bm25_path)

    t_bm25_start = time.perf_counter()
    logger.info("Building/Verifying BM25 index over %d standards...", total_records)
    bm25_engine = BM25SearchEngine(provider, cache_filename=bm25_cache_file)
    t_bm25_elapsed = time.perf_counter() - t_bm25_start
    bm25_size_mb = os.path.getsize(bm25_path) / (1024 * 1024) if os.path.exists(bm25_path) else 0.0
    logger.info(
        "BM25 index ready: %d docs indexed, cache size: %.2f MB, elapsed: %.2f s",
        bm25_engine.index.total_docs, bm25_size_mb, t_bm25_elapsed
    )

    # 2. Build / Load Semantic Vector Embeddings
    npy_path = os.path.join(ROOT_DIR, "data/catalogue/bis_semantic_embeddings.npy")
    if args.force and os.path.exists(npy_path):
        os.remove(npy_path)
        logger.info("Removed existing semantic embeddings for force rebuild: %s", npy_path)

    t_sem_start = time.perf_counter()
    logger.info("Building/Verifying Semantic vector embeddings (all-MiniLM-L6-v2) over %d standards...", total_records)
    sem_engine = SemanticSearchEngine(provider, cache_prefix="bis_")
    t_sem_elapsed = time.perf_counter() - t_sem_start
    sem_size_mb = os.path.getsize(npy_path) / (1024 * 1024) if os.path.exists(npy_path) else 0.0
    logger.info(
        "Semantic vector index ready: %d vectors (dim=%d), cache size: %.2f MB, elapsed: %.2f s",
        len(sem_engine.doc_ids),
        sem_engine.doc_embeddings.shape[1] if sem_engine.doc_embeddings is not None else 0,
        sem_size_mb,
        t_sem_elapsed
    )

    # 3. Test Spot Searches
    test_queries = ["CPVC pipe", "Sluice valve for water supply", "3.3 kV induction motor", "IS 15778"]
    logger.info("--- Verification Spot Checks ---")
    for q in test_queries:
        bm25_hits = bm25_engine.search(q, top_k=2)
        sem_hits = sem_engine.search(q, top_k=2)
        logger.info("Query: '%s'", q)
        if bm25_hits:
            logger.info("  BM25 Top-1: %s - %s (score: %.3f)", bm25_hits[0].standard_number, bm25_hits[0].full_title[:50], bm25_hits[0].score)
        if sem_hits:
            logger.info("  Semantic Top-1: %s - %s (sim: %.3f)", sem_hits[0].standard_number, sem_hits[0].full_title[:50], sem_hits[0].similarity_score)

    total_time = time.perf_counter() - t0
    logger.info("All BIS indexes successfully built and verified in %.2f s total.", total_time)

    # Final Invariant Check
    con_leg2 = sqlite3.connect(legacy_db)
    cur_leg2 = con_leg2.cursor()
    cur_leg2.execute("SELECT count(*) FROM standards")
    legacy_count_final = cur_leg2.fetchone()[0]
    con_leg2.close()
    assert legacy_count_final == 502, f"FATAL: catalogue.db altered during indexing! Found {legacy_count_final}"
    logger.info("Final verification: legacy catalogue.db remains exactly 502 records.")


if __name__ == "__main__":
    main()
