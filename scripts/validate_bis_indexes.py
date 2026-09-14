"""
scripts/validate_bis_indexes.py — Strict Index and Catalogue Consistency Validator for TenderSaathi.

Verifies:
1. Catalogue record count from bis_catalogue.db
2. BM25 index document count
3. Semantic embedding matrix row count
4. Semantic doc IDs count and uniqueness
5. Semantic doc hashes count
6. Exact 1-to-1 correspondence between doc IDs and catalogue canonical IDs
7. Embedding dimensions (e.g. 384 for all-MiniLM-L6-v2)
8. Manifest consistency against database and physical index artifacts

Fails with exit code 1 if ANY mismatch exists.
"""

import os
import sys
import json
import sqlite3
import numpy as np
import logging

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.catalogue.provider import get_default_catalogue_provider, BISCatalogueProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_bis_indexes")


def validate_indexes(db_path: str = "data/catalogue/bis_catalogue.db") -> bool:
    logger.info("================================================================================")
    logger.info("VALIDATING BIS CATALOGUE & RETRIEVAL INDEX INTEGRITY")
    logger.info("================================================================================")

    # 1. Connect to Catalogue and get true record count
    full_db_path = os.path.join(ROOT_DIR, db_path)
    if not os.path.exists(full_db_path):
        logger.error("FATAL: Authoritative catalogue not found at %s", full_db_path)
        return False

    provider = BISCatalogueProvider(db_path=full_db_path)
    catalogue_count = provider.get_total_count()
    logger.info("Authoritative catalogue record count: %d standards", catalogue_count)

    # Check for canonical ID uniqueness
    with provider._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT standard_id FROM standards")
        db_std_ids = [r[0] for r in cur.fetchall()]
        unique_db_ids = set(db_std_ids)
        if len(db_std_ids) != len(unique_db_ids):
            logger.error("FATAL: Duplicate canonical IDs detected in database: %d total vs %d unique", len(db_std_ids), len(unique_db_ids))
            return False
        logger.info("Canonical ID uniqueness verified: %d unique standards", len(unique_db_ids))

    # 2. Check Manifest
    manifest_path = os.path.join(ROOT_DIR, "data/catalogue/bis_index_manifest.json")
    if not os.path.exists(manifest_path):
        logger.error("FATAL: Index manifest missing at %s", manifest_path)
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    logger.info("Manifest loaded: %s (version: %s, timestamp: %s)", manifest_path, manifest.get("index_version"), manifest.get("updated_at"))

    if manifest.get("total_standards") != catalogue_count:
        logger.error("FATAL: Manifest record count mismatch: %d in manifest vs %d in catalogue", manifest.get("total_standards"), catalogue_count)
        return False

    # 3. Check BM25 Index
    bm25_path = os.path.join(ROOT_DIR, "data/catalogue/bis_bm25_index.json")
    if not os.path.exists(bm25_path):
        logger.error("FATAL: BM25 index missing at %s", bm25_path)
        return False

    with open(bm25_path, "r", encoding="utf-8") as f:
        bm25_data = json.load(f)

    bm25_total_docs = bm25_data.get("total_docs", 0)
    bm25_doc_ids = bm25_data.get("doc_ids", [])
    logger.info("BM25 index loaded: %d total docs, %d doc IDs in list", bm25_total_docs, len(bm25_doc_ids))

    if bm25_total_docs != catalogue_count or len(bm25_doc_ids) != catalogue_count:
        logger.error("FATAL: BM25 index count mismatch: total_docs=%d, doc_ids=%d, catalogue=%d", bm25_total_docs, len(bm25_doc_ids), catalogue_count)
        return False

    if set(bm25_doc_ids) != unique_db_ids:
        missing_in_bm25 = unique_db_ids - set(bm25_doc_ids)
        logger.error("FATAL: BM25 doc IDs do not match catalogue IDs. Missing: %d", len(missing_in_bm25))
        return False

    # 4. Check Semantic Embeddings & Metadata
    npy_path = os.path.join(ROOT_DIR, "data/catalogue/bis_semantic_embeddings.npy")
    doc_ids_path = os.path.join(ROOT_DIR, "data/catalogue/bis_semantic_doc_ids.json")
    hashes_path = os.path.join(ROOT_DIR, "data/catalogue/bis_semantic_doc_hashes.json")

    for p in [npy_path, doc_ids_path, hashes_path]:
        if not os.path.exists(p):
            logger.error("FATAL: Semantic index component missing at %s", p)
            return False

    embeddings = np.load(npy_path)
    with open(doc_ids_path, "r", encoding="utf-8") as f:
        sem_doc_ids = json.load(f)
    with open(hashes_path, "r", encoding="utf-8") as f:
        sem_hashes = json.load(f)

    num_vectors, dim = embeddings.shape
    expected_dim = manifest.get("embedding_dimension", 384)
    logger.info("Semantic index loaded: %d vectors (dim=%d), %d doc IDs, %d hashes", num_vectors, dim, len(sem_doc_ids), len(sem_hashes))

    if num_vectors != catalogue_count:
        logger.error("FATAL: Embedding vector rows (%d) != catalogue count (%d)", num_vectors, catalogue_count)
        return False

    if dim != expected_dim:
        logger.error("FATAL: Embedding dimension (%d) != expected (%d)", dim, expected_dim)
        return False

    if len(sem_doc_ids) != catalogue_count:
        logger.error("FATAL: Semantic doc IDs count (%d) != catalogue count (%d)", len(sem_doc_ids), catalogue_count)
        return False

    if len(set(sem_doc_ids)) != catalogue_count:
        logger.error("FATAL: Duplicate doc IDs found in semantic index doc IDs")
        return False

    if len(sem_hashes) != catalogue_count:
        logger.error("FATAL: Semantic hashes count (%d) != catalogue count (%d)", len(sem_hashes), catalogue_count)
        return False

    if set(sem_doc_ids) != unique_db_ids:
        missing_in_sem = unique_db_ids - set(sem_doc_ids)
        logger.error("FATAL: Semantic doc IDs do not match catalogue IDs. Missing: %d", len(missing_in_sem))
        return False

    # 5. Invariant Check: Legacy catalogue.db must remain untouched at exactly 502 records
    legacy_db = os.path.join(ROOT_DIR, "data/catalogue/catalogue.db")
    if os.path.exists(legacy_db):
        with sqlite3.connect(legacy_db) as conn_leg:
            cur_leg = conn_leg.cursor()
            cur_leg.execute("SELECT count(*) FROM standards")
            legacy_count = cur_leg.fetchone()[0]
        if legacy_count != 502:
            logger.error("FATAL: Legacy catalogue count modified: %d != 502", legacy_count)
            return False
        logger.info("Legacy catalogue verified: exactly 502 records (ISOLATED)")

    logger.info("================================================================================")
    logger.info("INDEX & CATALOGUE INTEGRITY: ALL CHECKS PASSED (100%% IN SYNC)")
    logger.info("================================================================================")
    return True


if __name__ == "__main__":
    success = validate_indexes()
    if not success:
        sys.exit(1)
    sys.exit(0)
