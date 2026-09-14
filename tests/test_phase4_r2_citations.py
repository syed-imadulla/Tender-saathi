"""
Module: tests/test_phase4_r2_citations.py
Purpose: Regression test suite for Phase 4R2 Exact Citation Resolution and Retrieval Integrity.

Verifies:
1. Exact citation resolution across all compound formats:
   - IS 15778:2007
   - IS15778:2007 (unspaced prefix)
   - IS 15778 (base number without year)
   - IS 1554 (Part 1):1988 (part-specific standard)
   - IS/ISO 9001:2015 (compound international adoption)
   - IS/IEC 61439-5:2014 (compound IEC standard)
   - SP 30:2023 (special publication)
2. Withdrawn standard preservation (explicitly cited withdrawn standard returned with status=WITHDRAWN).
3. Precedence hierarchy (EXACT_EXPLICIT_CITATION > EXACT_NORMALIZED_IDENTIFIER > HIGH_CONFIDENCE_IDENTIFIER_MATCH).
4. Full provenance retention (canonical_id, standard_number, part, section, year, status).
5. Hybrid retrieval integration (exact citations are ranked at top).
"""

import pytest
from src.catalogue.provider import get_default_catalogue_provider
from src.citation_resolver import ExactCitationResolver, CitationPrecedence
from src.retrieval import HybridRetrievalEngine


@pytest.fixture(scope="module")
def bis_provider():
    return get_default_catalogue_provider()


@pytest.fixture(scope="module")
def resolver(bis_provider):
    return ExactCitationResolver(db=bis_provider)


@pytest.fixture(scope="module")
def retrieval_engine(bis_provider):
    return HybridRetrievalEngine(db=bis_provider)


def test_01_exact_citation_standard_spaced(resolver):
    """Test resolution of 'IS 15778:2007'."""
    resolved = resolver.resolve_citation("IS 15778:2007")
    assert resolved is not None
    assert resolved.canonical_id == "IS-15778-2007"
    assert resolved.standard_number == "IS 15778 : 2007"
    assert resolved.year == 2007
    assert resolved.precedence in [CitationPrecedence.EXACT_EXPLICIT_CITATION, CitationPrecedence.EXACT_NORMALIZED_IDENTIFIER]


def test_02_exact_citation_unspaced_prefix(resolver):
    """Test resolution of 'IS15778:2007' without space between prefix and digits."""
    resolved = resolver.resolve_citation("IS15778:2007")
    assert resolved is not None
    assert resolved.canonical_id == "IS-15778-2007"
    assert resolved.standard_number == "IS 15778 : 2007"
    assert resolved.year == 2007


def test_03_base_standard_number_without_year(resolver):
    """Test resolution of 'IS 15778' when year is omitted."""
    resolved = resolver.resolve_citation("IS 15778")
    assert resolved is not None
    assert resolved.base_standard_number == "IS 15778"
    assert resolved.precedence == CitationPrecedence.HIGH_CONFIDENCE_IDENTIFIER_MATCH


def test_04_part_specific_standard(resolver):
    """Test resolution of 'IS 1554 (Part 1):1988' preserving part specificity."""
    resolved = resolver.resolve_citation("IS 1554 (Part 1):1988")
    assert resolved is not None
    assert resolved.canonical_id == "IS-1554-Part-1-1988"
    assert resolved.part == 1
    assert resolved.year == 1988


def test_05_compound_iso_adoption(resolver):
    """Test resolution of 'IS/ISO 9001:2015'."""
    resolved = resolver.resolve_citation("IS/ISO 9001:2015")
    assert resolved is not None
    assert resolved.canonical_id == "IS-ISO-9001-2015"
    assert resolved.year == 2015
    assert resolved.status.upper() == "ACTIVE"


def test_06_withdrawn_standard_preserved_on_explicit_citation(resolver):
    """A withdrawn standard must still be returned if explicitly cited."""
    resolved = resolver.resolve_citation("IS/IEC 61439-5 : 2014")
    assert resolved is not None
    assert resolved.canonical_id == "IS-IEC-61439-Part-5-2014"
    assert resolved.status.upper() == "WITHDRAWN"
    assert resolved.year == 2014


def test_07_special_publication_citation(resolver):
    """Test resolution of special publication 'SP 30 : 2023'."""
    resolved = resolver.resolve_citation("SP 30 : 2023")
    assert resolved is not None
    assert resolved.canonical_id == "SP-30-2023"
    assert resolved.year == 2023


def test_08_extract_and_resolve_from_tender_text(resolver):
    """Test full extraction and resolution from natural language tender requirement text."""
    query = "Supply and laying of CPVC pipes conforming to IS 15778:2007 for hot water plumbing"
    results = resolver.resolve_from_text(query)
    assert len(results) == 1
    assert results[0].canonical_id == "IS-15778-2007"


def test_09_hybrid_retrieval_prioritizes_exact_citation(retrieval_engine):
    """Verify that hybrid retrieval places the explicitly cited standard at rank 1."""
    query = "Providing heavy duty electrical power cables conforming to IS 1554 (Part 1):1988"
    results = retrieval_engine.search(query, top_k=5, mode="hybrid")
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit.standard_id == "IS-1554-Part-1-1988"
    assert top_hit.relevance_score == 1.0
    assert "Authoritative BIS Citation" in top_hit.relevance_reason


def test_10_deterministic_retrieval_prioritizes_exact_citation(retrieval_engine):
    """Verify that deterministic retrieval places the explicitly cited standard at rank 1."""
    query = "Water fittings per IS 15778:2007"
    results = retrieval_engine.search(query, top_k=5, mode="deterministic")
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit.standard_id == "IS-15778-2007"
    assert top_hit.relevance_score == 1.0
