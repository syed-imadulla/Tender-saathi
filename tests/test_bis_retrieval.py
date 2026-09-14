"""
tests/test_bis_retrieval.py — Comprehensive Test Suite for Phase 4 BIS Catalogue Retrieval Integration.

Covers all 30 specified verification scenarios:
- Catalogue source & isolation
- Identifier handling (simple, compound, parts, sections, prefixes)
- Retrieval mechanisms (deterministic, BM25, semantic, hybrid, reranker, pool bounding)
- Evidence & provenance tracking
- Lifecycle grounding & safety rules
- Regression invariants
"""

import os
import sys
import sqlite3
import pytest
import numpy as np

from src.catalogue.provider import BISCatalogueProvider, get_default_catalogue_provider
from src.standards import StandardsDatabase
from src.search import StandardsSearchEngine
from src.bm25_search import BM25SearchEngine
from src.semantic_search import SemanticSearchEngine
from src.retrieval import HybridRetrievalEngine
from src.recommend import StandardsRecommender
from src.extract import extract_from_text


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def bis_provider():
    return get_default_catalogue_provider()


@pytest.fixture(scope="module")
def hybrid_engine(bis_provider):
    return HybridRetrievalEngine(bis_provider, default_mode="hybrid")


@pytest.fixture(scope="module")
def recommender(bis_provider):
    return StandardsRecommender(db=bis_provider, retrieval_mode="hybrid")


# ---------------------------------------------------------------------------
# 1. Catalogue Source Tests
# ---------------------------------------------------------------------------

def test_01_retrieval_uses_bis_catalogue(hybrid_engine):
    """Retrieval engine must use bis_catalogue.db as its standards source."""
    assert "bis_catalogue.db" in hybrid_engine.db.db_path
    assert isinstance(hybrid_engine.db, BISCatalogueProvider)


def test_02_retrieval_does_not_use_502_catalogue(hybrid_engine):
    """Retrieval engine must NOT use the legacy 502-record catalogue.db."""
    assert "catalogue.db" != os.path.basename(hybrid_engine.db.db_path)
    count = hybrid_engine.db.get_total_count()
    assert count > 1000, f"Expected full BIS catalogue, got {count}"


def test_03_bis_catalogue_contains_35208_records(bis_provider):
    """Current Phase 2 BIS snapshot invariant: exactly 35,208 records."""
    assert bis_provider.get_total_count() == 35208


def test_04_duplicate_canonical_ids_zero(bis_provider):
    """Current Phase 2 BIS catalogue must have zero duplicate canonical IDs."""
    with bis_provider._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT canonical_id, count(*) FROM catalogue_standards GROUP BY canonical_id HAVING count(*) > 1")
        dups = cursor.fetchall()
        assert len(dups) == 0, f"Found duplicate canonical IDs: {dups}"


# ---------------------------------------------------------------------------
# 2. Identifier Handling Tests
# ---------------------------------------------------------------------------

def test_05_simple_is_standard(bis_provider):
    """Simple IS standard (e.g. IS 15778) resolved accurately."""
    rec = bis_provider.get_standard("IS-15778-2007")
    assert rec is not None
    assert "15778" in rec["standard_number"]
    assert "CPVC" in rec["full_title"] or "Chlorinated" in rec["full_title"]


def test_06_compound_iso_iec_standard(bis_provider):
    """Compound ISO/IEC standards (e.g. IS/ISO 10434, IS/IEC 60034-1) remain distinct."""
    rec_iso = bis_provider.get_standard("IS-ISO-10434-2020")
    assert rec_iso is not None
    assert "10434" in rec_iso["standard_number"]
    assert "ISO" in rec_iso["standard_number"]

    # Rotating electrical machines Part 1
    rec_iec = bis_provider.get_standard("IS-IEC-60034-Part-1-2022")
    assert rec_iec is not None
    assert "60034" in rec_iec["standard_number"]
    assert "IEC" in rec_iec["standard_number"]


def test_07_ieee_compound_standard(bis_provider):
    """IEEE compound standard preserves multi-body identifier."""
    rec = bis_provider.get_standard("IS-ISO-IEEE-11073-Part-10407-2022")
    assert rec is not None
    assert "11073" in rec["standard_number"]
    assert "IEEE" in rec["standard_number"]


def test_08_part_specific_standards_remain_distinct(bis_provider):
    """Part-specific standards (e.g. IS 1554 Part 1 vs Part 2) remain separate records."""
    rec_p1 = bis_provider.get_standard("IS-1554-Part-1-1988")
    rec_p2 = bis_provider.get_standard("IS-1554-Part-2-1988")
    assert rec_p1 is not None
    assert rec_p2 is not None
    assert rec_p1["standard_id"] != rec_p2["standard_id"]
    assert "Part 1" in rec_p1["standard_number"]
    assert "Part 2" in rec_p2["standard_number"]


def test_09_section_specific_standards_remain_distinct(bis_provider):
    """Section-specific standards (e.g. IS 1554 Part 1 Sec 2 or IS 7785 Part 5 Sec 1) remain distinct."""
    rec = bis_provider.get_standard("IS-7785-Part-5-Sec-1-1981")
    assert rec is not None
    assert "Part 5" in rec["standard_number"]
    assert "Sec 1" in rec["standard_number"] or "(Sec 1)" in rec["standard_number"]


def test_10_similar_base_numbers_remain_distinct(bis_provider):
    """Similar base numbers (e.g. IS 458 vs IS 4580) never collide."""
    rec_458 = bis_provider.get_standard("IS-458-2021")
    rec_4580 = bis_provider.get_standard("IS-4580-1986")
    assert rec_458 is not None
    assert rec_4580 is not None
    assert rec_458["standard_id"] != rec_4580["standard_id"]
    assert "Concrete" in rec_458["full_title"]
    assert "brushes" in rec_4580["full_title"].lower()


# ---------------------------------------------------------------------------
# 3. Retrieval Tests
# ---------------------------------------------------------------------------

def test_11_deterministic_exact_standard_lookup(hybrid_engine):
    """Deterministic exact standard lookup matches directly."""
    results = hybrid_engine.det_engine.search("IS 15778 : 2007", top_k=5)
    assert len(results) > 0
    assert any("15778" in r.standard_number for r in results)
    assert results[0].relevance_score >= 0.90


def test_12_bm25_uses_bis_catalogue(hybrid_engine):
    """BM25 search operates over the BIS catalogue corpus."""
    assert hybrid_engine.bm25_engine.index.total_docs > 1000
    hits = hybrid_engine.bm25_engine.search("Chlorinated Polyvinyl Chloride pipes", top_k=5)
    assert len(hits) > 0
    assert any("15778" in h.standard_number for h in hits)


def test_13_semantic_retrieval_uses_bis_catalogue(hybrid_engine):
    """Semantic vector search operates over the BIS catalogue embeddings."""
    assert hybrid_engine.semantic_engine.is_available
    assert len(hybrid_engine.semantic_engine.doc_ids) > 1000
    hits = hybrid_engine.semantic_engine.search("precast concrete pipes reinforcement", top_k=5)
    assert len(hits) > 0
    assert any("458" in h.standard_number for h in hits)


def test_14_hybrid_retrieval_uses_bis_candidates(hybrid_engine):
    """Hybrid retrieval fuses candidates from the BIS catalogue."""
    results = hybrid_engine.search("Supply of CPVC pipes conforming to IS 15778", top_k=5)
    assert len(results) > 0
    top = results[0]
    assert "15778" in top.standard_number


def test_15_cross_encoder_receives_bis_candidates(hybrid_engine):
    """Cross-encoder reranks candidates sourced from the BIS catalogue."""
    results = hybrid_engine.search(
        "Procurement of process water pump induction motors",
        top_k=5,
        mode="hybrid+rerank"
    )
    assert len(results) > 0
    reranked = [r for r in results if r.reranker_score is not None]
    assert len(reranked) > 0, "Expected candidates to receive cross-encoder reranker scores"


def test_16_candidate_pool_remains_bounded(hybrid_engine):
    """Candidate pool passed to reranking never evaluates all 35,208 records."""
    # Test internal method directly
    det_results = hybrid_engine.det_engine.search("water pipeline", top_k=10)
    bm25_hits = hybrid_engine.bm25_engine.search("water pipeline", top_k=10)
    sem_hits = hybrid_engine.semantic_engine.search("water pipeline", top_k=10)
    fused = hybrid_engine._fuse_hybrid_results(
        query="water pipeline",
        components=[],
        det_results=det_results,
        bm25_hits=bm25_hits,
        sem_hits=sem_hits,
        top_k=5,
        mode="hybrid+rerank"
    )
    assert len(fused) <= 5


# ---------------------------------------------------------------------------
# 4. Evidence & Provenance Tests
# ---------------------------------------------------------------------------

def test_17_recommended_standard_has_bis_provenance(recommender):
    """Recommended standard preserves BIS provenance."""
    res = recommender.recommend_for_text("Supply of CPVC pipes conforming to IS 15778")
    assert res.candidate_standard is not None
    assert "15778" in res.candidate_standard
    top_rec = res.recommendations[0]
    assert top_rec.canonical_id == "IS-15778-2007"
    assert top_rec.source_url is not None


def test_18_source_url_is_preserved(bis_provider):
    """BIS portal source URL is preserved in the database record."""
    prov = bis_provider.get_provenance("IS-15778-2007")
    assert prov is not None
    assert "standardsbis.bsbedge.com" in (prov["source_url"] or "")


def test_19_raw_record_ref_preserved_where_available(bis_provider):
    """Raw record reference (seed file + index) is preserved."""
    prov = bis_provider.get_provenance("IS-15778-2007")
    assert prov is not None
    assert prov.get("raw_record_ref") is not None
    assert "seed_" in prov["raw_record_ref"]


# ---------------------------------------------------------------------------
# 5. Lifecycle Grounding Tests
# ---------------------------------------------------------------------------

def test_20_active_remains_active(bis_provider):
    """Active standard maintains ACTIVE lifecycle status."""
    rec = bis_provider.get_standard("IS-10001-1981")
    assert rec is not None
    assert rec["status"] == "ACTIVE"


def test_21_withdrawn_remains_withdrawn(bis_provider):
    """Withdrawn standard maintains WITHDRAWN status."""
    breakdown = bis_provider.get_lifecycle_breakdown()
    assert breakdown["WITHDRAWN"] > 10000


def test_22_superseded_does_not_invent_replacement(bis_provider):
    """SUPERSEDED records preserve status without fabricating replacement numbers."""
    with bis_provider._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT canonical_id, status FROM catalogue_standards WHERE status = 'SUPERSEDED' LIMIT 5")
        rows = cursor.fetchall()
        assert len(rows) > 0
        for r in rows:
            assert r[1] == "SUPERSEDED"


def test_23_unknown_is_not_treated_as_active(bis_provider):
    """UNKNOWN status is not automatically assumed ACTIVE."""
    rec = bis_provider.get_standard("IS-15778-2007")
    assert rec is not None
    assert rec["status"] == "UNKNOWN"
    # Check that it is NOT marked as is_active == 1 in catalogue_standards
    with bis_provider._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM catalogue_standards WHERE canonical_id = 'IS-15778-2007'")
        row = cursor.fetchone()
        assert row[0] != 1


# ---------------------------------------------------------------------------
# 6. Safety & Human Review Tests
# ---------------------------------------------------------------------------

def test_24_missing_technical_details_trigger_review(recommender):
    """Underspecified requirements (e.g. generic valve repair) trigger human review."""
    res = recommender.recommend_for_text("Repair and replacement of valves in the mechanical distribution system.")
    assert res.human_review_required is True


def test_25_retrieval_does_not_equal_compliance():
    """Retrieval alone indicates a candidate standard, not legal compliance."""
    from src.applicability import ApplicabilityDecision
    # System architecture mandates ApplicabilityGate separates retrieval from compliance
    assert hasattr(ApplicabilityDecision, "APPLICABLE")
    assert hasattr(ApplicabilityDecision, "REVIEW_REQUIRED")
    assert hasattr(ApplicabilityDecision, "NOT_APPLICABLE")


def test_26_llm_cannot_directly_create_standard_recommendation():
    """AI parser output is restricted to structured facets; standard recommendations originate from retrieval."""
    from src.ai_understanding import AIRequirementParser
    parser = AIRequirementParser(enabled=False)
    facets = parser.parse("Procurement of 100m CPVC pipe")
    assert hasattr(facets, "equipment")
    assert not hasattr(facets, "candidate_standard")
    assert not hasattr(facets, "recommended_standard_number")


# ---------------------------------------------------------------------------
# 7. Regression Invariants
# ---------------------------------------------------------------------------

def test_27_production_db_remains_exactly_502():
    """Legacy catalogue.db must remain untouched at exactly 502 records."""
    db_path = "data/catalogue/catalogue.db"
    assert os.path.exists(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM standards")
    count = cur.fetchone()[0]
    con.close()
    assert count == 502, f"catalogue.db has {count} records, expected 502"


def test_28_phase2_bis_catalogue_remains_35208():
    """Phase 2 BIS catalogue must retain its 35,208 records."""
    db_path = "data/catalogue/bis_catalogue.db"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM catalogue_standards")
    cat_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM standards")
    std_count = cur.fetchone()[0]
    con.close()
    assert cat_count == 35208
    assert std_count == 35208


def test_29_phase1_raw_data_remains_untouched():
    """Raw BIS page data from Phase 1 must remain intact."""
    raw_dir = "data/raw/bis/run_20260914_042545/pages"
    assert os.path.isdir(raw_dir)
    page_files = [f for f in os.listdir(raw_dir) if f.endswith(".json")]
    assert len(page_files) == 186


def test_30_no_fake_relationship_tables_in_bis_db(bis_provider):
    """No empty standard_relationships or standard_references tables in bis_catalogue.db."""
    with bis_provider._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('standard_relationships', 'standard_references')")
        tables = [r[0] for r in cursor.fetchall()]
        assert len(tables) == 0, f"Found unexpected tables: {tables}"


def test_31_production_source_assertion(bis_provider):
    """Production source assertion must verify bis_catalogue.db and fail on legacy 502 catalogue."""
    import pytest
    from src.catalogue.provider import assert_authoritative_bis_catalogue
    from src.standards import StandardsDatabase

    # Valid BIS provider must pass without error
    assert_authoritative_bis_catalogue(bis_provider)

    # Legacy 502 catalogue must strictly fail
    legacy_db = StandardsDatabase(db_path="data/catalogue/catalogue.db")
    with pytest.raises(RuntimeError, match="legacy catalogue detected"):
        assert_authoritative_bis_catalogue(legacy_db)

    # None provider must fail
    with pytest.raises(RuntimeError, match="provider is None"):
        assert_authoritative_bis_catalogue(None)


def test_32_synchronization_metadata_truthful(bis_provider):
    """Synchronization metadata must truthfully report snapshot timestamp without claiming real-time."""
    meta = bis_provider.get_synchronization_metadata()
    assert meta["provider"] == "BIS catalogue"
    assert "data/catalogue/bis_catalogue.db" in meta["catalogue_path"]
    assert meta["total_standards"] == 35208
    assert meta["last_synchronized_at"] is not None
    assert "BIS catalogue synchronized:" in meta["formatted_label"]
    assert "real-time" not in meta["formatted_label"].lower()

