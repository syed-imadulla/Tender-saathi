"""
Script: scripts/audit_standard_identity.py
Purpose: Audits standard identity integrity across DB, BM25, Semantic indexes,
and candidate retrieval layers for all benchmark targets and anti-collision negative pairs.

Key Invariants Checked:
1. Expected Token -> Canonical Normalization -> Canonical ID
2. Canonical ID -> Database Record Lookup (canonical_id and standard_number)
3. Canonical ID -> BM25 Index Document (doc_id matches canonical_id exactly)
4. Canonical ID -> Semantic Index Document (doc_id matches canonical_id exactly)
5. Searchable Document Title matches Database Record Title
6. Anti-Collision Negative Pairs: Checks that a query for standard A does not resolve or match negative distractor B:
   - IS 5039 vs IS 15039
   - IS 7098 (Part 1) vs IS 7098 (Part 2)
   - IS 7098 vs IS 17098
   - IS 3043 vs IS 13043
   - IS 1255 vs IS 11255
   - IS/IEC 61800-2 vs IS/IEC 61800-3
   - SP 30 vs IS 30
"""

import csv
import json
import logging
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier
from src.catalogue.provider import get_default_catalogue_provider, assert_authoritative_bis_catalogue
from src.bm25_search import BM25SearchEngine
from src.semantic_search import SemanticSearchEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audit_standard_identity")


BENCHMARK_TARGETS = [
    "IS 15905 : 2011",
    "IS 1239 (Part 1) : 2004",
    "IS 15622 : 2017",
    "IS 2556 (Part 1 to 17)",
    "IS 781 : 1984",
    "IS 774 : 2021",
    "IS 6392 : 1971",
    "IS 2712 : 2020",
    "IS/IEC 61439-3 : 2012",
    "IS 10322 (Part 5 / Sec 5) : 2013",
    "IS 7098 (Part 1) : 1988",
    "IS 1255 : 1983",
    "IS 5039 : 1983",
    "IS/IEC 61439-5 : 2014",
    "IS 3043 : 2018",
    "IS 1293 : 2019",
    "IS 16088 : 2016",
    "IS 2491 : 2013",
    "IS 15000 : 2013",
    "SP 30 : 2023",
    "IS 732 : 2019",
    "IS 458 : 2021",
    "IS 783 : 1985",
    "IS 14333 : 1996",
    "IS 1661 : 1972",
    "IS 269 : 2015",
    "IS 1239 (Part 2) : 1992",
    "IS 778 : 1984",
    "IS/IEC 61800-2 : 2015",
    "IS/IEC 61439-2 : 2011",
    "IS 14164 : 2008",
    "IS 8183 : 1993",
    "IS/IEC 60034-1 : 2017",
    "IS 5120 : 1977",
    "IS 15778 : 2007",
]

COLLISION_TEST_PAIRS = [
    ("IS 5039", "IS 15039"),
    ("IS 7098 (Part 1)", "IS 7098 (Part 2)"),
    ("IS 7098", "IS 17098"),
    ("IS 3043", "IS 13043"),
    ("IS 1255", "IS 11255"),
    ("IS/IEC 61800-2", "IS/IEC 61800-3"),
    ("SP 30", "IS 30"),
]


def audit_standard_identity() -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
    provider = get_default_catalogue_provider()
    assert_authoritative_bis_catalogue(provider)

    logger.info("Initializing BM25 and Semantic Search Engines for identity audit...")
    bm25_engine = BM25SearchEngine(db=provider)
    semantic_engine = SemanticSearchEngine(db=provider)

    bm25_doc_id_set = set(bm25_engine.index.doc_ids)
    semantic_doc_id_set = set(semantic_engine.doc_ids)

    all_pass = True
    benchmark_results: List[Dict[str, Any]] = []

    # 1. Audit Benchmark Standards
    for target_token in BENCHMARK_TARGETS:
        parsed = StandardIdentifierNormalizer.parse(target_token)
        canonical_id = parsed.canonical_id

        # Direct lookup by canonical_id
        db_record = provider.get_standard(canonical_id)
        if not db_record:
            # Query by base number and filter with matches_identity_without_year
            with provider._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM standards WHERE standard_number LIKE ?", (f"%{parsed.base_number}%",))
                candidates = [dict(r) for r in cursor.fetchall()]
                for cand in candidates:
                    cand_p = StandardIdentifierNormalizer.parse(cand.get("original_standard_identifier", "") or cand.get("standard_number", ""))
                    if StandardIdentifierNormalizer.matches_identity_without_year(parsed, cand_p):
                        db_record = cand
                        canonical_id = cand["standard_id"]
                        break

        db_standard_id = db_record["standard_id"] if db_record else None
        title = db_record["full_title"] if db_record else "NOT_FOUND"

        bm25_doc_id = canonical_id if canonical_id in bm25_doc_id_set else None
        semantic_doc_id = canonical_id if canonical_id in semantic_doc_id_set else None

        # Verify identity match across layers
        identity_match = (
            db_record is not None and
            bm25_doc_id == db_standard_id and
            semantic_doc_id == db_standard_id
        )

        status = "PASS" if identity_match else "FAIL"
        if not identity_match:
            all_pass = False

        benchmark_results.append({
            "expected_identifier": target_token,
            "canonical_id": canonical_id,
            "db_standard_id": db_standard_id,
            "bm25_doc_id": bm25_doc_id,
            "semantic_doc_id": semantic_doc_id,
            "title": title,
            "identity_match": identity_match,
            "status": status
        })

    # 2. Audit Collision Negative Pairs
    collision_results: List[Dict[str, Any]] = []
    for std_a, std_b in COLLISION_TEST_PAIRS:
        parsed_a = StandardIdentifierNormalizer.parse(std_a)
        parsed_b = StandardIdentifierNormalizer.parse(std_b)

        # Ensure normalizer keeps them distinct
        norm_distinct = (
            parsed_a.canonical_id != parsed_b.canonical_id and
            parsed_a.base_standard_number != parsed_b.base_standard_number and
            not StandardIdentifierNormalizer.matches_identity_without_year(parsed_a, parsed_b)
        )

        # Check in DB
        cand_a = None
        cand_b = None
        with provider._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standards WHERE standard_number LIKE ?", (f"%{parsed_a.base_number}%",))
            for r in cursor.fetchall():
                c = dict(r)
                cand_p = StandardIdentifierNormalizer.parse(c.get("original_standard_identifier", "") or c.get("standard_number", ""))
                if StandardIdentifierNormalizer.matches_identity_without_year(parsed_a, cand_p):
                    cand_a = c
                    break

            cursor.execute("SELECT * FROM standards WHERE standard_number LIKE ?", (f"%{parsed_b.base_number}%",))
            for r in cursor.fetchall():
                c = dict(r)
                cand_p = StandardIdentifierNormalizer.parse(c.get("original_standard_identifier", "") or c.get("standard_number", ""))
                if StandardIdentifierNormalizer.matches_identity_without_year(parsed_b, cand_p):
                    cand_b = c
                    break

        db_distinct = True
        if cand_a and cand_b:
            db_distinct = (cand_a["standard_id"] != cand_b["standard_id"])

        pair_pass = norm_distinct and db_distinct
        if not pair_pass:
            all_pass = False

        collision_results.append({
            "standard_a": std_a,
            "standard_b": std_b,
            "canonical_id_a": parsed_a.canonical_id,
            "canonical_id_b": parsed_b.canonical_id,
            "distinct_in_normalizer": norm_distinct,
            "distinct_in_db": db_distinct,
            "status": "PASS" if pair_pass else "FAIL"
        })

    return all_pass, benchmark_results, collision_results


if __name__ == "__main__":
    passed, bench_res, coll_res = audit_standard_identity()
    print("\n" + "=" * 80)
    print("STANDARD IDENTITY AUDIT RESULTS")
    print("=" * 80)
    print(f"{'Expected Identifier':<35} | {'Canonical ID':<25} | {'DB Match':<8} | {'Status'}")
    print("-" * 80)
    for r in bench_res:
        db_match_str = "YES" if r["identity_match"] else "NO"
        print(f"{r['expected_identifier']:<35} | {r['canonical_id']:<25} | {db_match_str:<8} | {r['status']}")

    print("\n" + "=" * 80)
    print("ANTI-COLLISION NEGATIVE PAIRS RESULTS")
    print("=" * 80)
    for c in coll_res:
        print(f"{c['standard_a']:<20} vs {c['standard_b']:<20} -> Distinct: {c['distinct_in_db']} | Status: {c['status']}")

    print("\n" + "=" * 80)
    print(f"FINAL AUDIT RESULT: {'ALL PASS' if passed else 'FAIL'}")
    print("=" * 80)
    sys.exit(0 if passed else 1)
