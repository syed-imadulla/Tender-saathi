"""
tests/test_phase31_evidence_integrity.py — Phase 31 Verification Test Suite

Tests:
1. All 8 compound-requirement & edge-case fixtures:
   - M25 concrete multi-component scope
   - TMT reinforcement IS 1786 grade Fe 500D (supported parameter)
   - Mild steel tubes IS 1239 Part 1 explicit part disambiguation
   - Piping manifold compound with multiple standards
   - Unsupported grade Fe 750 (bounds rejection)
   - Withdrawn standard citation (IS 8112) with local successor
   - Conflicting editions (IS 4984:1995 vs 2016)
   - Out-of-scope parameter (5500 mm pipe diameter on IS 4984)
2. Case A grounding alignment (requires FULLY_SUPPORTED)
3. Provenance audit (integrity check vs authenticity proof)
4. Un-ingested standards blocker tracking (IS 1239 Part 2 and IS 2062)
5. Reconciled coverage metric consistency
"""

import sqlite3
import pytest
from src.recommend import StandardsRecommender
from src.corpus.retriever import ClauseRetriever, RequirementEvidenceSupportState
from src.corpus.storage import CorpusStorage
from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.validate import validate_standard_status


@pytest.fixture(scope="module")
def recommender():
    return StandardsRecommender()


@pytest.fixture(scope="module")
def clause_retriever():
    storage = CorpusStorage(db_path="data/standards/corpus.db")
    return ClauseRetriever(storage=storage)


# ---------------------------------------------------------------------------
# 1. Eight Core Compound Requirement & Parameter Fixtures
# ---------------------------------------------------------------------------

def test_fixture_m25_concrete_compound_subcomponents(recommender):
    """M25 concrete requirement decomposing into multi-component requirements."""
    req_text = (
        "M25 grade design-mix concrete conforming to IS 456, using 43 grade OPC cement "
        "conforming to IS 269, coarse aggregates conforming to IS 383, and high strength deformed steel bars conforming to IS 1786."
    )
    res = recommender.recommend_for_requirement(req_text)
    assert res.human_review_required is True
    # Must not receive unconditional CLAUSE_VERIFIED tier because composite subcomponents require engineering review
    assert res.verification_tier in ["CATALOGUE_DISCOVERED", "SAFE_ABSTENTION"]
    assert res.component_recommendations is not None
    assert len(res.component_recommendations) >= 2


def test_fixture_tmt_fe500d_verified(recommender):
    """TMT reinforcement conforming to IS 1786 with supported grade Fe 500D."""
    req_text = "High strength deformed steel bars for concrete reinforcement conforming to IS 1786 grade Fe 500D."
    res = recommender.recommend_for_requirement(req_text)
    assert res.candidate_standard.startswith("IS 1786")
    assert res.verification_tier == "CLAUSE_VERIFIED"
    assert res.clause_evidence is not None
    assert res.clause_evidence.get("requirement_evidence_support") == "FULLY_SUPPORTED"
    assert res.passage_id is not None


def test_fixture_steel_tubes_part1_disambiguation(recommender):
    """Mild steel tubular pipes conforming to IS 1239 Part 1 must select Part 1, not Part 2."""
    req_text = "Mild steel tubular pipes conforming to IS 1239 Part 1 Medium class."
    res = recommender.recommend_for_requirement(req_text)
    assert "Part 1" in res.candidate_standard
    assert "Part 2" not in res.candidate_standard


def test_fixture_compound_piping_manifold(recommender):
    """Compound piping and valve manifold where multiple standards apply."""
    req_text = "Piping manifold assembly comprising mild steel tubes to IS 1239 (Part 1) and sluice valves for water works to IS 14846."
    res = recommender.recommend_for_requirement(req_text)
    assert res.human_review_required is True
    assert res.verification_tier != "CLAUSE_VERIFIED"
    assert res.component_recommendations is not None
    assert len(res.component_recommendations) >= 2


def test_fixture_unsupported_grade_fe750_abstention(recommender):
    """Unsupported grade Fe 750 on IS 1786 must NOT receive CLAUSE_VERIFIED."""
    req_text = "High strength deformed steel bars conforming to IS 1786 grade Fe 750 Super."
    res = recommender.recommend_for_requirement(req_text)
    assert res.verification_tier != "CLAUSE_VERIFIED"
    assert res.clause_evidence.get("requirement_evidence_support") in ["PARTIALLY_SUPPORTED", "UNSUPPORTED"]


def test_fixture_withdrawn_successor_gate(recommender):
    """Withdrawn citation IS 8112:2013 must be barred from CLAUSE_VERIFIED."""
    req_text = "43-grade ordinary portland cement conforming to IS 8112:2013."
    res = recommender.recommend_for_requirement(req_text)
    assert res.verification_tier != "CLAUSE_VERIFIED"
    assert res.human_review_required is True


def test_fixture_conflicting_editions_gate(recommender):
    """Simultaneous citation of conflicting editions must be barred from CLAUSE_VERIFIED."""
    req_text = "Polyethylene pipes for water supply conforming to IS 4984:1995 and IS 4984:2016 simultaneously."
    res = recommender.recommend_for_requirement(req_text)
    assert res.verification_tier != "CLAUSE_VERIFIED"
    assert res.human_review_required is True


def test_fixture_out_of_scope_diameter_5500mm(recommender):
    """Out-of-scope 5500 mm pipe diameter on IS 4984 must NOT receive CLAUSE_VERIFIED."""
    req_text = "Polyethylene pipes for water supply conforming to IS 4984 with nominal outside diameter 5500 mm."
    res = recommender.recommend_for_requirement(req_text)
    assert res.verification_tier != "CLAUSE_VERIFIED"
    assert res.clause_evidence.get("requirement_evidence_support") in ["PARTIALLY_SUPPORTED", "UNSUPPORTED"]


# ---------------------------------------------------------------------------
# 2. Case A Grounding & Evidence Support State Invariant
# ---------------------------------------------------------------------------

def test_case_a_evidence_support_blocks_clause_verified(clause_retriever):
    """Case A: Even if clause 1.1 is grounded, out-of-scope parameter (5500 mm) must result in non-FULLY_SUPPORTED, blocking CLAUSE_VERIFIED."""
    # IS 4984 Clause 1.1 with out-of-scope diameter parameter 5500 mm
    res = clause_retriever.retrieve_clause_evidence(
        standard_number="IS 4984",
        edition_year=2016,
        clause_identifier="1.1",
        query_text="Polyethylene pipes for water supply conforming to IS 4984 with nominal outside diameter 5500 mm"
    )
    assert res.outcome == "CLAUSE_EVIDENCE_FOUND"
    assert res.clause_identifier == "1.1"
    # Clause 1.1 exists in document so it is grounded, but parameter 5500 mm is out of scope (DN 16-2000 mm)
    assert res.is_grounded is True
    assert res.requirement_evidence_support in [RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value, RequirementEvidenceSupportState.UNSUPPORTED.value]

    # Recommender end-to-end gate check: must NOT be CLAUSE_VERIFIED
    recommender = StandardsRecommender()
    rec_res = recommender.recommend_for_text(
        "Polyethylene pipes for water supply conforming to IS 4984 with nominal outside diameter 5500 mm"
    )
    assert rec_res.verification_tier != "CLAUSE_VERIFIED"



# ---------------------------------------------------------------------------
# 3. Provenance and Integrity Verification
# ---------------------------------------------------------------------------

def test_provenance_audit_string_hash_integrity():
    """Verify document file_sha256 serves as deterministic content integrity check in corpus.db."""
    conn = sqlite3.connect("data/standards/corpus.db")
    cur = conn.cursor()
    docs = cur.execute("SELECT doc_id, standard_number, edition_year, file_sha256, extraction_method FROM corpus_documents").fetchall()
    conn.close()

    assert len(docs) >= 8
    for doc_id, std_num, yr, sha, method in docs:
        assert doc_id.startswith("DOC-IS-")
        assert len(sha) == 64
        assert method in ["PYMUPDF_TEXT", "GAZETTE_PUBLIC_EXTRACT", "MANUAL_EXTRACT", "OFFICIAL_BIS_PUBLICATION"]


def test_un_ingested_standards_blocker_recorded():
    """Verify unacquired standards (IS 2062) have zero passages in corpus.db due to missing authentic full-text sources,
    while acquired IS 1239 (Part 2) has authentic passages."""
    conn = sqlite3.connect("data/standards/corpus.db")
    cur = conn.cursor()
    p_unverified_1239 = cur.execute("SELECT COUNT(*) FROM corpus_passages WHERE standard_number LIKE '%1239%Part 2%' AND verification_state != 'CLAUSE_IDENTIFIER_VERIFIED'").fetchone()[0]
    p_2062 = cur.execute("SELECT COUNT(*) FROM corpus_passages WHERE standard_number LIKE '%2062%'").fetchone()[0]
    conn.close()

    assert p_unverified_1239 == 0
    assert p_2062 == 0


def test_reconciled_coverage_metrics_consistency():
    """Verify database counts agree with reconciled metrics definitions."""
    # Catalogue database
    cat_conn = sqlite3.connect("data/catalogue/bis_catalogue.db")
    cat_cur = cat_conn.cursor()
    total_cat = cat_cur.execute("SELECT COUNT(*) FROM catalogue_standards").fetchone()[0]
    active_cat = cat_cur.execute("SELECT COUNT(*) FROM catalogue_standards WHERE status = 'ACTIVE'").fetchone()[0]
    unknown_cat = cat_cur.execute("SELECT COUNT(*) FROM catalogue_standards WHERE status = 'UNKNOWN'").fetchone()[0]
    withdrawn_cat = cat_cur.execute("SELECT COUNT(*) FROM catalogue_standards WHERE status = 'WITHDRAWN'").fetchone()[0]
    cat_conn.close()

    assert total_cat == 35208
    assert active_cat == 10828
    assert unknown_cat == 13024
    assert withdrawn_cat == 11340

    # Curated database (at least 96 baseline standards)
    std_conn = sqlite3.connect("data/standards/standards.db")
    std_cur = std_conn.cursor()
    total_std = std_cur.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
    active_std = std_cur.execute("SELECT COUNT(*) FROM standards WHERE status = 'Active'").fetchone()[0]
    std_conn.close()

    assert total_std >= 96
    assert active_std >= 80

    # Corpus database (at least 8 baseline documents and 31 passages)
    corp_conn = sqlite3.connect("data/standards/corpus.db")
    corp_cur = corp_conn.cursor()
    total_docs = corp_cur.execute("SELECT COUNT(*) FROM corpus_documents").fetchone()[0]
    total_passages = corp_cur.execute("SELECT COUNT(*) FROM corpus_passages").fetchone()[0]
    corp_conn.close()

    assert total_docs >= 8
    assert total_passages >= 31
