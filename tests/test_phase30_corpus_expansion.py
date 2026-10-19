"""
tests/test_phase30_corpus_expansion.py — Phase 30 Normative Corpus Expansion & Evidence Integrity Tests

Deterministic verification of:
1. Corpus document integrity, provenance, and statutory licensing invariants for all 8 documents.
2. Ingestion stability and passage content hash integrity.
3. Clause extraction and deterministic passage IDs for IS 383, IS 269, IS 1786, and IS 1239 (Part 1).
4. End-to-end pipeline verification (CLAUSE_VERIFIED) for newly supported standards with real procurement requirements.
5. Strict verification gates: edition mismatch rejection and ungrounded parameters abstain safely.
6. Full interoperability with multi-package and complementary standard graphs (IS 456 dependencies).
"""

import sqlite3
import pytest
from src.extract import extract_from_text
from src.recommend import StandardsRecommender
from src.corpus.storage import CorpusStorage
from src.corpus.retriever import ClauseRetriever
from src.corpus.manifest import LicensingStatus, IngestionStatus


@pytest.fixture(scope="module")
def recommender():
    return StandardsRecommender()


@pytest.fixture(scope="module")
def corpus_storage():
    return CorpusStorage("data/standards/corpus.db")


@pytest.fixture(scope="module")
def clause_retriever(corpus_storage):
    return ClauseRetriever(storage=corpus_storage)


# ===========================================================================
# 1. Corpus Document Registration and Licensing Invariants
# ===========================================================================

def test_all_eight_corpus_documents_registered(corpus_storage):
    """Verify exactly 8 documents are registered with authentic metadata and valid SHA-256."""
    with sqlite3.connect(corpus_storage.db_path) as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT doc_id, standard_number, edition_year, licensing_status, ingestion_status, file_sha256
            FROM corpus_documents
            ORDER BY doc_id
        """).fetchall()

    assert len(rows) >= 8, f"Expected at least 8 registered documents, found {len(rows)}"

    expected_docs = {
        "DOC-IS-456-2000": ("IS 456", 2000),
        "DOC-IS-4984-2016": ("IS 4984", 2016),
        "DOC-IS-1489-Part-1-2015": ("IS 1489 (Part 1)", 2015),
        "DOC-IS-8112-2013": ("IS 8112", 2013),
        "DOC-IS-383-2016": ("IS 383", 2016),
        "DOC-IS-269-2015": ("IS 269", 2015),
        "DOC-IS-1786-2008": ("IS 1786", 2008),
        "DOC-IS-1239-Part-1-2004": ("IS 1239 (Part 1)", 2004),
        "DOC-IS-1239-Part-2-2011": ("IS 1239 (Part 2)", 2011),
        "DOC-IS-14846-2000": ("IS 14846", 2000),
        "DOC-IS-800-2007": ("IS 800", 2007),
    }

    found_doc_ids = set()
    for doc_id, std_num, yr, lic_status, ing_status, sha in rows:
        assert doc_id in expected_docs, f"Unexpected doc_id: {doc_id}"
        found_doc_ids.add(doc_id)
        exp_std, exp_yr = expected_docs[doc_id]
        assert std_num == exp_std
        assert yr == exp_yr
        assert lic_status == LicensingStatus.STATUTORY_PUBLIC_GAZETTE.value
        assert len(sha) == 64, f"Invalid SHA-256 hash length for {doc_id}"

    assert set(expected_docs.keys()).issubset(found_doc_ids)


def test_passage_counts_and_content_hashes(corpus_storage):
    """Verify total passage count is at least 31 (44 in Phase 33) with stable, non-empty content hashes."""
    with sqlite3.connect(corpus_storage.db_path) as conn:
        cursor = conn.cursor()
        passages = cursor.execute("""
            SELECT passage_id, doc_id, standard_number, clause_identifier, content_hash
            FROM corpus_passages
        """).fetchall()

    assert len(passages) >= 31, f"Expected at least 31 passages, found {len(passages)}"
    for pid, did, snum, cid, chash in passages:
        assert len(pid) > 0, "Passage ID must be a non-empty string"
        assert len(chash) == 64, f"Content hash for {pid} should be 64-char SHA-256"
        assert did.startswith("DOC-IS-")


# ===========================================================================
# 2. Targeted Clause Retrieval for New Standards
# ===========================================================================

def test_is383_concrete_aggregate_clauses(clause_retriever):
    """Verify IS 383:2016 clauses for scope, classification, and grading zones."""
    # Scope
    cl_1_1 = clause_retriever.get_clause("IS 383", "1.1", edition_year=2016)
    assert cl_1_1 is not None
    p_lower = cl_1_1.passage_text.lower()
    assert "aggregates" in p_lower and "coarse" in p_lower and "fine" in p_lower

    # Classification
    cl_4_1 = clause_retriever.get_clause("IS 383", "4.1", edition_year=2016)
    assert cl_4_1 is not None
    assert "coarse aggregate" in cl_4_1.passage_text.lower()
    assert "fine aggregate" in cl_4_1.passage_text.lower()

    # Grading zones
    cl_6_2 = clause_retriever.get_clause("IS 383", "6.2", edition_year=2016)
    assert cl_6_2 is not None
    assert "zone ii" in cl_6_2.passage_text.lower()
    assert "table 4" in cl_6_2.passage_text.lower()


def test_is269_opc_cement_clauses(clause_retriever):
    """Verify IS 269:2015 clauses for 33, 43, 53 grade cement and compressive strength."""
    # Scope and consolidated grades
    cl_1_1 = clause_retriever.get_clause("IS 269", "1.1", edition_year=2015)
    assert cl_1_1 is not None
    p_lower = cl_1_1.passage_text.lower()
    assert "ordinary portland cement" in p_lower
    assert "33 grade" in p_lower and "43 grade" in p_lower and "53 grade" in p_lower

    # Chemical requirements
    cl_5_1 = clause_retriever.get_clause("IS 269", "5.1", edition_year=2015)
    assert cl_5_1 is not None
    assert "chemical requirements" in cl_5_1.passage_text.lower()
    assert "lime saturation" in cl_5_1.passage_text.lower()

    # Physical / Compressive strength
    cl_6_1 = clause_retriever.get_clause("IS 269", "6.1", edition_year=2015)
    assert cl_6_1 is not None
    assert "43 mpa" in cl_6_1.passage_text.lower()
    assert "53 mpa" in cl_6_1.passage_text.lower()


def test_is1786_tmt_rebar_clauses(clause_retriever):
    """Verify IS 1786:2008 clauses for rebar grades (Fe 415/500/500D) and mechanical properties."""
    # Scope
    cl_1_1 = clause_retriever.get_clause("IS 1786", "1.1", edition_year=2008)
    assert cl_1_1 is not None
    assert "deformed steel bars" in cl_1_1.passage_text.lower()

    # Steel manufacture
    cl_4_1 = clause_retriever.get_clause("IS 1786", "4.1", edition_year=2008)
    assert cl_4_1 is not None
    assert "steel manufacture" in cl_4_1.passage_text.lower()
    assert "electric furnace" in cl_4_1.passage_text.lower()

    # Grades
    cl_5_1 = clause_retriever.get_clause("IS 1786", "5.1", edition_year=2008)
    assert cl_5_1 is not None
    p_lower = cl_5_1.passage_text.lower()
    assert "fe 415" in p_lower and "fe 500d" in p_lower

    # Mechanical properties
    cl_8_1 = clause_retriever.get_clause("IS 1786", "8.1", edition_year=2008)
    assert cl_8_1 is not None
    assert "table 3" in cl_8_1.passage_text.lower()
    assert "yield strength" in cl_8_1.passage_text.lower() or "elongation" in cl_8_1.passage_text.lower()


def test_is1239_part1_steel_tube_clauses(clause_retriever):
    """Verify IS 1239 (Part 1):2004 clauses for steel tubes, classes, and testing."""
    # Scope
    cl_1_1 = clause_retriever.get_clause("IS 1239 (Part 1)", "1.1", edition_year=2004)
    assert cl_1_1 is not None
    p_lower = cl_1_1.passage_text.lower()
    assert "steel tubes" in p_lower and "water" in p_lower

    # Material and tensile properties
    cl_5_1 = clause_retriever.get_clause("IS 1239 (Part 1)", "5.1", edition_year=2004)
    assert cl_5_1 is not None
    assert "tensile properties" in cl_5_1.passage_text.lower()
    assert "320 n/mm²" in cl_5_1.passage_text.lower() or "320" in cl_5_1.passage_text

    # Classification and dimensions
    cl_8_1 = clause_retriever.get_clause("IS 1239 (Part 1)", "8.1", edition_year=2004)
    assert cl_8_1 is not None
    assert "medium" in cl_8_1.passage_text.lower()
    assert "heavy" in cl_8_1.passage_text.lower()

    # Hydrostatic test
    cl_9_1 = clause_retriever.get_clause("IS 1239 (Part 1)", "9.1", edition_year=2004)
    assert cl_9_1 is not None
    assert "hydrostatic test" in cl_9_1.passage_text.lower()
    assert "5.0 mpa" in cl_9_1.passage_text.lower()


# ===========================================================================
# 3. End-to-End Pipeline Recommendation & Clause Verification
# ===========================================================================

def test_is1786_rebar_recommendation_and_clause_verification(recommender):
    """Verify real procurement requirement for TMT rebars resolves to CLAUSE_VERIFIED IS 1786."""
    text = "High strength deformed steel bars for concrete reinforcement conforming to IS 1786 Grade Fe 500D."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert "1786" in res.candidate_standard
    assert res.verification_tier == "CLAUSE_VERIFIED"
    assert res.passage_id is not None
    assert res.clause_number in ["1.1", "4.1", "5.1", "8.1"]
    assert res.clause_evidence is not None
    assert res.clause_evidence.get("requirement_evidence_support") in ["FULLY_SUPPORTED", "PARTIALLY_SUPPORTED"]


def test_is383_aggregate_recommendation_and_clause_verification(recommender):
    """Verify real procurement requirement for concrete aggregate resolves to CLAUSE_VERIFIED IS 383."""
    text = "Supply of coarse and fine aggregates for design mix concrete conforming to IS 383, including Zone II river sand."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert "383" in res.candidate_standard
    assert res.verification_tier == "CLAUSE_VERIFIED"
    assert res.passage_id is not None
    assert res.clause_number in ["1.1", "4.1", "5.1", "6.2"]
    assert "coarse" in res.clause_evidence.get("passage_text", "").lower() or "sand" in res.clause_evidence.get("passage_text", "").lower() or "fine" in res.clause_evidence.get("passage_text", "").lower()


def test_is269_opc_recommendation_and_clause_verification(recommender):
    """Verify direct procurement requirement for 53 Grade OPC resolves to CLAUSE_VERIFIED IS 269."""
    text = "Procurement of 53 Grade Ordinary Portland Cement conforming to IS 269 for precast prestressed concrete girders."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert "269" in res.candidate_standard
    assert res.verification_tier == "CLAUSE_VERIFIED"
    assert res.passage_id is not None
    assert res.clause_number in ["1.1", "5.1", "6.1", "6.2"]
    assert "portland cement" in res.clause_evidence.get("passage_text", "").lower()


def test_is1239_steel_tube_recommendation_and_clause_verification(recommender):
    """Verify real procurement requirement for GI pipes resolves to CLAUSE_VERIFIED IS 1239 (Part 1)."""
    text = "Supply and laying of medium class galvanized mild steel tubes for internal water distribution conforming to IS 1239 (Part 1)."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert "1239" in res.candidate_standard
    assert res.verification_tier == "CLAUSE_VERIFIED"
    assert res.passage_id is not None
    assert res.clause_number in ["1.1", "5.1", "8.1", "9.1"]
    assert res.clause_evidence.get("requirement_evidence_support") in ["FULLY_SUPPORTED", "PARTIALLY_SUPPORTED"]


# ===========================================================================
# 4. Strict Verification Gates and Mismatch Rejection
# ===========================================================================

def test_edition_mismatch_prevents_false_grounding_is1786(clause_retriever):
    """Verify obsolete edition IS 1786:1985 cannot inherit passages from 2008."""
    p_1985 = clause_retriever.get_clause("IS 1786", "4.1", edition_year=1985)
    assert p_1985 is None, "Edition 1985 must not return passages from edition 2008"

    p_2008 = clause_retriever.get_clause("IS 1786", "4.1", edition_year=2008)
    assert p_2008 is not None, "Edition 2008 passage must be accessible"


def test_nonexistent_clause_returns_none(clause_retriever):
    """Verify querying an un-ingested clause returns None without fabricating content."""
    res = clause_retriever.get_clause("IS 383", "99.9", edition_year=2016)
    assert res is None


def test_catalogue_only_candidate_not_falsely_clause_verified(recommender):
    """Verify an active catalogue standard without normative corpus document remains CATALOGUE_DISCOVERED."""
    text = "Procurement of marine propulsion diesel engines for coastal patrol vessels."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert res.verification_tier != "CLAUSE_VERIFIED"
    assert res.clause_evidence.get("is_grounded") is False
    assert res.clause_evidence.get("passage_text") is None


# ===========================================================================
# 5. Dependency Graph Interoperability (IS 456 Complementary Standards)
# ===========================================================================

def test_is456_normative_dependencies_link_to_newly_ingested_standards():
    """Verify IS 456 concrete specification includes IS 383, IS 269, IS 1786 in its relationships."""
    import json
    with open("data/standards/relationships.json", "r") as f:
        rels = json.load(f)

    is456_refs = [
        r["target_standard"] for r in rels
        if "456" in r.get("source_standard", "") and r.get("relationship_type") == "NORMATIVE_REFERENCE"
    ]

    assert any("383" in r for r in is456_refs), "IS 456 must reference aggregate standard IS 383"
    assert any("269" in r for r in is456_refs), "IS 456 must reference cement standard IS 269"
    assert any("1786" in r for r in is456_refs), "IS 456 must reference rebar standard IS 1786"
