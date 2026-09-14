"""
Tests for Phase 4R2.1 Candidate-Preserving Fusion strategies:
- Strategy A: Weighted fusion baseline
- Strategy B: Reciprocal Rank Fusion (RRF)
- Strategy C: Candidate-preserving union / CombMAX with consensus boost

Validates:
1. Candidate preservation across first-stage retrievers
2. Union behaviour before fusion
3. RRF formula correctness
4. Explicit citation precedence over fusion
5. Lifecycle visibility (UNKNOWN and WITHDRAWN records remain searchable)
"""

import pytest
from src.retrieval import HybridRetrievalEngine, HybridCandidate
from src.catalogue.provider import get_default_catalogue_provider
from src.search import SearchResult
from src.bm25_search import BM25Hit
from src.semantic_search import SemanticHit


@pytest.fixture(scope="module")
def hybrid_engine():
    provider = get_default_catalogue_provider()
    return HybridRetrievalEngine(db=provider)


def test_01_candidate_preservation_single_engine(hybrid_engine):
    """A candidate found exclusively by Semantic or Deterministic is preserved in Strategy C."""
    # Create mock hits where standard X is only in semantic (rank 5, score 0.45)
    sem_hits = [
        SemanticHit(
            standard_id="bis_std_001",
            standard_number="IS 9999",
            full_title="High precision semantic standard",
            similarity_score=0.45,
            raw_record={"standard_id": "bis_std_001", "standard_number": "IS 9999", "full_title": "High precision semantic standard", "status": "Active"}
        )
    ]
    # And 20 BM25 hits with mild scores (0.25)
    bm25_hits = [
        BM25Hit(
            standard_id=f"bis_bm_{i}",
            standard_number=f"IS {1000 + i}",
            full_title=f"Generic title {i}",
            score=5.0,
            normalized_score=0.25,
            matched_terms=["term"],
            doc_length=10,
            raw_record={"standard_id": f"bis_bm_{i}", "standard_number": f"IS {1000 + i}", "full_title": f"Generic title {i}", "status": "Active"}
        )
        for i in range(20)
    ]

    # Under Strategy C (candidate_preserving), IS 9999 must rank near the very top (rank 1)
    res_c = hybrid_engine._fuse_hybrid_results(
        query="precision requirement",
        components=[],
        det_results=[],
        bm25_hits=bm25_hits,
        sem_hits=sem_hits,
        top_k=5,
        mode="hybrid",
        fusion_strategy="candidate_preserving"
    )
    assert len(res_c) > 0
    top_ids = [r.standard_id for r in res_c]
    assert "bis_std_001" in top_ids, "Candidate-preserving fusion must preserve strong single-engine candidate"
    assert res_c[0].standard_id == "bis_std_001"


def test_02_rrf_formula_correctness(hybrid_engine):
    """RRF score matches 1 / (k + rank) formula exactly."""
    cand_1 = SearchResult(
        standard_id="std_1",
        standard_number="IS 1",
        year=2020,
        full_title="Standard 1",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.8,
        relevance_reason="test",
        scope_summary=""
    )
    cand_2 = SearchResult(
        standard_id="std_2",
        standard_number="IS 2",
        year=2020,
        full_title="Standard 2",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.7,
        relevance_reason="test",
        scope_summary=""
    )
    # std_1 is rank 1 in DET, std_2 is rank 2 in DET
    det_results = [cand_1, cand_2]
    # In BM25, std_2 is rank 1, std_1 is rank 2
    raw_1 = {"standard_id": "std_1", "standard_number": "IS 1", "full_title": "Standard 1", "status": "Active"}
    raw_2 = {"standard_id": "std_2", "standard_number": "IS 2", "full_title": "Standard 2", "status": "Active"}
    bm25_hits = [
        BM25Hit(standard_id="std_2", standard_number="IS 2", full_title="Standard 2", score=10.0, normalized_score=1.0, matched_terms=[], doc_length=5, raw_record=raw_2),
        BM25Hit(standard_id="std_1", standard_number="IS 1", full_title="Standard 1", score=9.0, normalized_score=0.9, matched_terms=[], doc_length=5, raw_record=raw_1)
    ]

    res_rrf = hybrid_engine._fuse_hybrid_results(
        query="test query",
        components=[],
        det_results=det_results,
        bm25_hits=bm25_hits,
        sem_hits=[],
        top_k=2,
        mode="hybrid",
        fusion_strategy="rrf"
    )
    assert len(res_rrf) == 2
    # Both have ranks 1 and 2 in the two engines:
    # RRF score = 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.016393 + 0.016129 = 0.032522
    assert abs(res_rrf[0].final_score - 0.032522) < 1e-4
    assert abs(res_rrf[1].final_score - 0.032522) < 1e-4


def test_03_union_behaviour_and_first_stage_boundary(hybrid_engine):
    """First-stage union correctly captures candidates from all retrievers."""
    # When searching, first_stage_k bounds all 3 engines
    results = hybrid_engine.search(
        "PVC insulated electric cables",
        top_k=10,
        first_stage_k=50,
        mode="hybrid"
    )
    assert len(results) > 0
    # Must contain IS 1554 or IS 694 cable standards
    std_numbers = [r.standard_number for r in results]
    assert any("1554" in s or "694" in s for s in std_numbers)


def test_04_explicit_citation_precedence_over_fusion(hybrid_engine):
    """Explicit citation always takes top priority regardless of fusion strategy."""
    for strategy in ["weighted", "rrf", "candidate_preserving"]:
        res = hybrid_engine.search(
            "Conforming to IS 15778:2007 for CPVC pipes in hot and cold water installations",
            top_k=3,
            fusion_strategy=strategy
        )
        assert len(res) > 0
        top = res[0]
        assert "15778" in top.standard_number
        assert top.final_score == 1.0
        assert "Authoritative BIS Citation" in top.relevance_reason


def test_05_lifecycle_visibility_preserved(hybrid_engine):
    """WITHDRAWN and UNKNOWN records remain fully searchable and discoverable."""
    # IS 15778:2007 has status UNKNOWN in source BIS data
    std = hybrid_engine.db.get_standard("IS-15778-2007")
    assert std is not None
    assert std.get("status") in ["UNKNOWN", "WITHDRAWN", "Active", "Superseded"]
    # Search for it explicitly
    res = hybrid_engine.search("CPVC pipes IS 15778", top_k=5)
    found = [r for r in res if "15778" in r.standard_number]
    assert len(found) > 0
    assert found[0].status == std.get("status")
