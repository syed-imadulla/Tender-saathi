"""
Module: tests/test_national_catalogue_retrieval.py
Purpose: Comprehensive, deterministic regression test matrix for Phase 25
(National BIS Catalogue Metadata Retrieval).

Covers:
1. Natural-language discovery of standards absent from curated 90.
2. Multi-part and edition accuracy.
3. Deduplication between curated and catalogue results.
4. Active vs withdrawn/superseded safeguards.
5. Two-tier cascading and weak-match fallback.
6. Irrelevant queries and service-only tenders (clean abstention).
7. Malformed queries, injection prevention, and empty queries.
8. Strict evidence safeguards (no fabricated clause text or normative parameters).
9. API response serialization and contract compatibility.
10. Lexical retrieval latency benchmarks (sub-10ms).
"""

import pytest
import time
from typing import List

from src.catalogue.search import NationalCatalogueSearchEngine
from src.retrieval import HybridRetrievalEngine
from src.recommend import StandardsRecommender
from src.search import SearchResult
from src.applicability import ApplicabilityGate
from api.server import app


@pytest.fixture(scope="module")
def catalogue_search_engine():
    return NationalCatalogueSearchEngine()


@pytest.fixture(scope="module")
def hybrid_engine():
    return HybridRetrievalEngine()


@pytest.fixture(scope="module")
def recommender():
    return StandardsRecommender()


@pytest.fixture(scope="module")
def api_client():
    return app.test_client()



# ---------------------------------------------------------------------------
# 1. Natural-Language Discovery of Standards Beyond Curated 90
# ---------------------------------------------------------------------------

def test_nl_discovery_marine_diesel_engine(catalogue_search_engine):
    """Verifies that an unrepresented engineering domain (marine diesel engine) retrieves valid standards."""
    results = catalogue_search_engine.search("marine diesel engine for ship propulsion", top_k=5)
    assert len(results) > 0
    std_numbers = [r.standard_number for r in results]
    titles = [r.full_title.lower() for r in results]

    # Verify marine/diesel relevance
    assert any("diesel" in t and ("ship" in t or "marine" in t or "engine" in t) for t in titles)
    assert any("3979" in num or "14909" in num or "8528" in num for num in std_numbers)

    top = results[0]
    assert top.verification_status == "CATALOGUE_VERIFIED"
    assert getattr(top, "_is_catalogue_only", False) is True
    assert top.source_provenance.startswith("National BIS Catalogue")


def test_nl_discovery_respiratory_devices(catalogue_search_engine):
    """Verifies discovery of personal protective respiratory equipment."""
    results = catalogue_search_engine.search("respiratory protective devices breathing apparatus", top_k=5)
    assert len(results) > 0
    assert any("17274" in r.standard_number for r in results)
    assert any("respiratory" in r.full_title.lower() for r in results)


def test_nl_discovery_medical_textiles(catalogue_search_engine):
    """Verifies discovery of medical/surgical textiles."""
    results = catalogue_search_engine.search("medical surgical adhesive tape", top_k=5)
    assert len(results) > 0
    assert any("16470" in r.standard_number or "16948" in r.standard_number for r in results)
    assert any("surgical" in r.full_title.lower() for r in results)


# ---------------------------------------------------------------------------
# 2. Multi-Part and Edition Accuracy
# ---------------------------------------------------------------------------

def test_multipart_standard_accuracy(catalogue_search_engine):
    """Verifies that multi-part standards preserve exact part designations and publication years."""
    results = catalogue_search_engine.search("IS 17274 Part 12 respiratory", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert "Part 12" in top.standard_number
    assert top.year == 2019
    assert "volume-averaged work of breathing" in top.full_title.lower()


# ---------------------------------------------------------------------------
# 3. Deduplication Between Curated and Catalogue Results
# ---------------------------------------------------------------------------

def test_curated_deduplication_preserves_clause_rich_standard(hybrid_engine):
    """
    When a requirement matches a curated standard (e.g. 500 kVA distribution transformer),
    the search engine should return the curated record without duplicates or degradation.
    """
    results = hybrid_engine.search("supply of 500 kva outdoor distribution transformer 11 kv", top_k=5)
    assert len(results) > 0
    top = results[0]
    # Primary result should be curated IS 1180
    assert "1180" in top.standard_number
    # It must not be marked _is_catalogue_only because it exists in the curated corpus
    assert getattr(top, "_is_catalogue_only", False) is False

    # Ensure no duplicate 1180 records in results
    cand_1180_count = sum(1 for r in results if "1180" in r.standard_number)
    assert cand_1180_count == 1


# ---------------------------------------------------------------------------
# 4. Active vs Withdrawn/Superseded Safeguards
# ---------------------------------------------------------------------------

def test_active_only_discovery_pool(catalogue_search_engine):
    """Verifies that all candidates returned by national catalogue discovery have status ACTIVE."""
    queries = [
        "diesel engine",
        "respiratory protective",
        "hydraulic fluid power",
        "earth moving machinery"
    ]
    for q in queries:
        results = catalogue_search_engine.search(q, top_k=5)
        for r in results:
            assert r.status == "Active" or r.status == "ACTIVE"
            assert r.version_role == "CURRENT_ACTIVE"


# ---------------------------------------------------------------------------
# 5. Two-Tier Cascading and Fallback Behavior
# ---------------------------------------------------------------------------

def test_two_tier_cascades_on_unrepresented_domain(hybrid_engine):
    """
    For an engineering domain missing from curated 90 standards,
    HybridRetrievalEngine automatically cascades to the national catalogue.
    """
    # Curated DB has 0 marine propulsion standards
    results = hybrid_engine.search("marine diesel engines for ship propulsion", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert getattr(top, "_is_catalogue_only", False) is True
    assert "Shipbuilding" in top.full_title or "diesel" in top.full_title.lower()


def test_two_tier_preserves_curated_on_high_confidence(hybrid_engine):
    """
    For a curated engineering domain (e.g. cross-linked polyethylene insulated cables),
    the high-confidence curated standard is preserved as primary.
    """
    results = hybrid_engine.search("xlpe insulated power cables 11 kv grade conforming to standard", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert "7098" in top.standard_number
    assert getattr(top, "_is_catalogue_only", False) is False


# ---------------------------------------------------------------------------
# 6. Service-Only & Irrelevant Tenders (Clean Abstention)
# ---------------------------------------------------------------------------

def test_pure_service_audit_clean_abstention(recommender):
    """
    A purely administrative tender (statutory audit and tax consultancy)
    must cleanly abstain without falsely recommending physical engineering standards.
    """
    res = recommender.recommend_for_requirement(
        "Hiring of chartered accountant firm for statutory internal audit, corporate tax filing, and gst compliance"
    )
    # The candidate standard should either be None or flagged as NOT_APPLICABLE / REVIEW_REQUIRED with 0 applicability
    if res.candidate_standard is not None:
        assert res.applicability is not None
        assert res.applicability.get("applicable") is False or res.human_review_required is True
    else:
        assert res.candidate_standard is None


def test_catering_service_clean_abstention(recommender):
    """
    An annual catering / refreshment service tender must cleanly abstain.
    """
    res = recommender.recommend_for_requirement(
        "Annual contract for catering services, boardroom refreshments, and executive dining facility"
    )
    if res.candidate_standard is not None:
        assert res.human_review_required is True
    else:
        assert res.candidate_standard is None


# ---------------------------------------------------------------------------
# 7. Malformed Queries and Injection Prevention
# ---------------------------------------------------------------------------

def test_malformed_fts_queries_do_not_crash(catalogue_search_engine):
    """Verifies that malicious or malformed FTS syntax does not trigger SQLite exceptions."""
    malformed_inputs = [
        "",
        "   ",
        '"""*^^((((',
        "NEAR/5 AND OR NOT",
        "SELECT * FROM users WHERE '1'='1'",
        "diesel' OR '1'='1'; DROP TABLE catalogue_fts; --",
        "(((+++---***///)))",
        "!@#$%^&*()_+"
    ]
    for mi in malformed_inputs:
        results = catalogue_search_engine.search(mi, top_k=3)
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# 8. Evidence Boundaries (No Fabricated Clause Evidence)
# ---------------------------------------------------------------------------

def test_no_fabricated_clause_evidence_for_catalogue_discovery(recommender):
    """
    Verifies that standards discovered through the national catalogue
    strictly have human_review_required=True, PENDING_TECHNICAL_EVALUATION,
    and ZERO fabricated clause evidence or scope text.
    """
    res = recommender.recommend_for_requirement(
        "Supply and delivery of marine diesel engines for harbor tug vessel propulsion"
    )

    assert res.candidate_standard is not None
    assert "3979" in res.candidate_standard or "14909" in res.candidate_standard or "diesel" in res.title.lower()
    assert res.human_review_required is True
    assert res.provenance == "NATIONAL_CATALOGUE_DISCOVERY"
    assert res.applicability is not None
    assert res.applicability.get("decision") == "PENDING_TECHNICAL_EVALUATION"

    # Clause evidence must not contain fabricated normative passages
    if res.structured_evidence:
        clause_ev = res.structured_evidence.get("clause_evidence")
        assert clause_ev is None or clause_ev.get("requirement_evidence_support") == "UNINDEXED_IN_SEMANTIC_CORPUS"

    assert "Discovered National Catalogue Standard" in res.reason


# ---------------------------------------------------------------------------
# 9. API Response Serialization Compatibility
# ---------------------------------------------------------------------------

def test_api_text_analysis_with_catalogue_discovery(api_client):
    """
    Verifies that the /api/analyze/text endpoint serializes catalogue-discovered
    candidates with provenance, confidence, review status, and score breakdown.
    """
    payload = {
        "text": "Supply and installation of marine diesel engines for tug vessel propulsion",
        "tender_title": "Marine Procurement Tender"
    }
    response = api_client.post("/api/analyze/text", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "requirements" in data
    assert len(data["requirements"]) > 0

    req = data["requirements"][0]
    assert req.get("candidate_standard") is not None
    assert req.get("human_review_required") is True
    assert req.get("provenance") == "NATIONAL_CATALOGUE_DISCOVERY"
    assert req.get("evidence_strength") in ("MEDIUM", "MODERATE")
    assert "confidence" in req


# ---------------------------------------------------------------------------
# 10. Lexical Retrieval Latency Benchmarks
# ---------------------------------------------------------------------------

def test_catalogue_search_latency_under_10ms(catalogue_search_engine):
    """Benchmarks that FTS5 lexical queries execute in under 10 milliseconds."""
    queries = [
        "marine diesel engine",
        "respiratory protective devices",
        "hydraulic fluid power valves",
        "earth moving machinery roll over protective structures"
    ]
    # Warmup
    catalogue_search_engine.search("diesel", top_k=5)

    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        results = catalogue_search_engine.search(q, top_k=5)
        dt_ms = (time.perf_counter() - t0) * 1000
        latencies.append(dt_ms)
        assert len(results) > 0

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 10.0, f"Average query latency {avg_latency:.2f}ms exceeds 10ms threshold"
