"""
Script: scripts/build_catalogue_search_index.py
Purpose: Builds a high-performance SQLite FTS5 full-text search index over all
active standards in the National BIS Catalogue (data/catalogue/bis_catalogue.db).

Phase 25 Architecture:
- Indexes all ACTIVE standards (10,828 records).
- Compounds searchable fields: standard_number, title, technical_committee, department, iso_equivalence.
- Employs 'porter unicode61' tokenizer for English morphological stemming (e.g. 'transformers' -> 'transform').
- Output database: data/catalogue/catalogue_search_index.db (completely separate from bis_catalogue.db to preserve read-only integrity).
- Reproducible, deterministic, and fast (builds in < 2 seconds).
"""

import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_catalogue_search_index")

SOURCE_DB_PATH = "data/catalogue/bis_catalogue.db"
TARGET_INDEX_DB_PATH = "data/catalogue/catalogue_search_index.db"


def build_catalogue_search_index(
    source_db_path: str = SOURCE_DB_PATH,
    target_index_path: str = TARGET_INDEX_DB_PATH,
    active_only: bool = True
) -> dict:
    start_time = time.time()

    if not os.path.exists(source_db_path):
        raise FileNotFoundError(f"Source catalogue database not found at '{source_db_path}'")

    # Ensure target directory exists
    os.makedirs(os.path.dirname(os.path.abspath(target_index_path)), exist_ok=True)

    # Remove previous index database if it exists for a clean build
    if os.path.exists(target_index_path):
        os.remove(target_index_path)
        logger.info(f"Removed existing index database: {target_index_path}")

    # Connect to source read-only
    source_uri = f"file:{os.path.abspath(source_db_path)}?mode=ro"
    source_conn = sqlite3.connect(source_uri, uri=True)
    source_conn.row_factory = sqlite3.Row
    source_cur = source_conn.cursor()

    # Query active catalogue records
    query = """
        SELECT
            canonical_id,
            standard_number,
            title,
            technical_committee,
            department,
            iso_equivalence,
            year,
            status,
            source_url
        FROM catalogue_standards
    """
    if active_only:
        query += " WHERE status = 'ACTIVE'"
    query += " ORDER BY canonical_id ASC"

    source_cur.execute(query)
    rows = source_cur.fetchall()
    total_records = len(rows)
    logger.info(f"Fetched {total_records} records from {source_db_path} (active_only={active_only})")

    # Connect to target index database
    target_conn = sqlite3.connect(target_index_path)
    target_cur = target_conn.cursor()

    # Enable WAL mode for high read concurrency
    target_cur.execute("PRAGMA journal_mode = WAL;")
    target_cur.execute("PRAGMA synchronous = NORMAL;")

    # Create FTS5 virtual table
    # Columns marked UNINDEXED are stored for direct retrieval without polluting the token inverted index
    create_table_sql = """
        CREATE VIRTUAL TABLE catalogue_fts USING fts5(
            canonical_id UNINDEXED,
            standard_number,
            title,
            technical_committee,
            department,
            iso_equivalence,
            year UNINDEXED,
            status UNINDEXED,
            source_url UNINDEXED,
            tokenize = 'porter unicode61'
        );
    """
    target_cur.execute(create_table_sql)

    # Also create a metadata table to record provenance and build timestamps
    target_cur.execute("""
        CREATE TABLE index_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    # Insert records into FTS5 table
    insert_sql = """
        INSERT INTO catalogue_fts (
            canonical_id,
            standard_number,
            title,
            technical_committee,
            department,
            iso_equivalence,
            year,
            status,
            source_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    batch = []
    for r in rows:
        batch.append((
            r["canonical_id"],
            r["standard_number"] or "",
            r["title"] or "",
            r["technical_committee"] or "",
            r["department"] or "",
            r["iso_equivalence"] or "",
            str(r["year"]) if r["year"] is not None else "",
            r["status"] or "UNKNOWN",
            r["source_url"] or ""
        ))

    target_cur.executemany(insert_sql, batch)

    # Record metadata
    elapsed_time = time.time() - start_time
    target_cur.execute("INSERT INTO index_metadata (key, value) VALUES (?, ?);", ("record_count", str(total_records)))
    target_cur.execute("INSERT INTO index_metadata (key, value) VALUES (?, ?);", ("build_time_seconds", f"{elapsed_time:.4f}"))
    target_cur.execute("INSERT INTO index_metadata (key, value) VALUES (?, ?);", ("built_at_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    target_cur.execute("INSERT INTO index_metadata (key, value) VALUES (?, ?);", ("source_db", source_db_path))

    # Commit and optimize FTS index
    target_cur.execute("INSERT INTO catalogue_fts(catalogue_fts) VALUES('optimize');")
    target_conn.commit()

    target_conn.close()
    source_conn.close()

    file_size_bytes = os.path.getsize(target_index_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    logger.info(
        f"Successfully built {target_index_path}: {total_records} records indexed in {elapsed_time:.2f}s "
        f"({file_size_mb:.2f} MB)"
    )

    return {
        "status": "SUCCESS",
        "records_indexed": total_records,
        "elapsed_seconds": elapsed_time,
        "index_file_path": target_index_path,
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(file_size_mb, 2)
    }


if __name__ == "__main__":
    result = build_catalogue_search_index()
    print("Build Result:", result)
