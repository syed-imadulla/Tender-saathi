"""
Test Suite: tests/test_phase4r6_applicability_and_bookkeeping.py
Purpose: Machine-verifiable tests for Phase 4R6 Acceptance:
1. Canonical ID bookkeeping and DB row attachment
2. Exact separation of known collision pairs:
   - IS 5039 vs IS 15039
   - IS 7098 Part 1 vs Part 2
   - IS 7098 vs IS 17098
   - IS 3043 vs IS 13043
   - IS 1255 vs IS 11255
   - IS/IEC 61800-2 vs IS/IEC 61800-3
   - SP 30 vs IS 30
3. Deterministic applicability gate rules based strictly on authoritative catalogue evidence
4. Candidate pool continuation behavior
5. Clear separation of Identity, Retrieval, and Applicability correctness
"""

import pytest
from src.catalogue.provider import get_default_catalogue_provider
from src.citation_resolver import ExactCitationResolver
from src.validate import validate_standard_status
from src.applicability import ApplicabilityGate
from src.search import SearchResult


@pytest.fixture(scope="module")
def catalogue_db():
    return get_default_catalogue_provider()


@pytest.fixture(scope="module")
def citation_resolver(catalogue_db):
    return ExactCitationResolver(catalogue_db)


@pytest.fixture(scope="module")
def applicability_gate():
    return ApplicabilityGate()


# ===========================================================================
# 1. Canonical ID & Collision Pair Proofs (Constraint 12)
# ===========================================================================

COLLISION_PAIRS = [
    ("IS 5039", "IS 5039", "IS 15039", "IS 15039"),
    ("IS 7098 (Part 1)", "IS 7098 (Part 1)", "IS 7098 (Part 2)", "IS 7098 (Part 2)"),
    ("IS 7098", "IS 7098 (Part 1)", "IS 17098", "IS 17098"),
    ("IS 3043", "IS 3043", "IS 13043", "IS 13043"),
    ("IS 1255", "IS 1255", "IS 11255 (Part 1)", "IS 11255 (Part 1)"),
    ("IS/IEC 61800-2", "IS/IEC 61800 (Part 2)", "IS/IEC 61800-3", "IS/IEC 61800 (Part 3)"),
    ("SP 30", "SP 30", "IS 30", "IS 30"),
]


@pytest.mark.parametrize("query_a,base_a,query_b,base_b", COLLISION_PAIRS)
def test_collision_pairs_do_not_cross_resolve(citation_resolver, query_a, base_a, query_b, base_b):
    """Proves each side of known collision pairs resolves uniquely to its own canonical identity."""
    res_a = citation_resolver.resolve_citation(query_a)
    res_b = citation_resolver.resolve_citation(query_b)

    assert res_a is not None, f"Failed to resolve {query_a}"
    assert res_b is not None, f"Failed to resolve {query_b}"

    # Verify canonical IDs and base numbers are strictly distinct
    assert res_a.canonical_id != res_b.canonical_id, f"Collision detected: {res_a.canonical_id} == {res_b.canonical_id}"
    assert res_a.base_standard_number == base_a, f"Expected base {base_a}, got {res_a.base_standard_number}"
    assert res_b.base_standard_number == base_b, f"Expected base {base_b}, got {res_b.base_standard_number}"

    # Verify each resolved record links to a valid DB row with matching canonical_id
    assert res_a.raw_record is not None
    assert res_b.raw_record is not None
    assert res_a.raw_record.get("canonical_id") == res_a.canonical_id
    assert res_b.raw_record.get("canonical_id") == res_b.canonical_id


def test_validate_standard_status_no_digit_substring_collision(catalogue_db):
    """Proves validate_standard_status does NOT conflate IS 732 with IS 10732 or IS 5039 with IS 15039."""
    val_732 = validate_standard_status("IS 732 : 2019", catalogue_db)
    assert val_732.is_known is True
    assert val_732.status == "ACTIVE"
    assert val_732.is_active is True
    assert val_732.standard_metadata["standard_number"] == "IS 732 : 2019"

    val_5039 = validate_standard_status("IS 5039", catalogue_db)
    val_15039 = validate_standard_status("IS 15039", catalogue_db)
    assert val_5039.standard_metadata["standard_number"].startswith("IS 5039")
    assert val_15039.standard_metadata["standard_number"].startswith("IS 15039")
    assert val_5039.standard_metadata["standard_number"] != val_15039.standard_metadata["standard_number"]


# ===========================================================================
# 2. Applicability Correctness vs Retrieval Correctness (Constraints 2, 3, 5, 6)
# ===========================================================================

def test_voltage_gate_is7098_part1_vs_part2(applicability_gate):
    """
    Constraint 5: HT XLPE insulated power cables 11 kV grade.
    IS 7098 (Part 1) title states 'up to and including 1 100 V'.
    Must be rejected with VOLTAGE_CONFLICT, while Part 2 must be accepted.
    """
    req_text = "HT XLPE insulated power cables 11 kV grade"

    cand_part1 = SearchResult(
        standard_id="IS-7098-Part-1-2025",
        standard_number="IS 7098 (Part 1) : 2025",
        year=2025,
        full_title="Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables - Specification Part 1 For Working Voltages up to and Including 1 100 Volts",
        scope_summary="",
        status="ACTIVE",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.92,
        relevance_reason="Top semantic match"
    )

    cand_part2 = SearchResult(
        standard_id="IS-7098-Part-2-2011",
        standard_number="IS 7098 (Part 2) : 2011",
        year=2011,
        full_title="Crosslinked polyethylene insulated thermoplastic sheathed cables - Specification: Part 2 for working voltages from 3.3 kV up to and including 33 kV",
        scope_summary="",
        status="ACTIVE",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.88,
        relevance_reason="Second semantic match"
    )

    res_part1 = applicability_gate.evaluate_candidate(cand_part1, req_text)
    assert res_part1.applicable is False
    assert res_part1.decision == "NOT_APPLICABLE"
    assert any("VOLTAGE_CONFLICT" in f for f in res_part1.conflict_flags)

    res_part2 = applicability_gate.evaluate_candidate(cand_part2, req_text)
    assert res_part2.applicable is True
    assert res_part2.decision == "APPLICABLE"
    assert len(res_part2.conflict_flags) == 0


def test_equipment_mismatch_is16667_vs_cables(applicability_gate):
    """
    Constraint 6: High voltage underground electric cable for power transmission distribution.
    IS 16667 concerns HVDC voltage sourced converters (valves/stations), NOT cables.
    Must be marked EQUIPMENT_MISMATCH and rejected.
    """
    req_text = "High voltage underground electric cable for power transmission distribution"

    cand_16667 = SearchResult(
        standard_id="IS-16667-2018",
        standard_number="IS 16667 : 2018",
        year=2018,
        full_title="High - Voltage direct current (Hvdc) power transmission using voltage sourced converters (Vsc)",
        scope_summary="",
        status="WITHDRAWN",
        version_role="WITHDRAWN",
        relevance_score=0.91,
        relevance_reason="Semantic overlap with HVDC transmission"
    )

    res_16667 = applicability_gate.evaluate_candidate(cand_16667, req_text)
    assert res_16667.applicable is False
    assert res_16667.decision == "NOT_APPLICABLE"
    assert any("EQUIPMENT_MISMATCH" in f for f in res_16667.conflict_flags)


def test_openwell_vs_borewell_pump_gate(applicability_gate):
    """Openwell pumpset IS 14220 must be rejected for narrow 100 mm borewell requirements."""
    req_text = "Submersible pump set for 100 mm borewell with 5 HP motor"

    cand_openwell = SearchResult(
        standard_id="IS-14220-2018",
        standard_number="IS 14220 : 2018",
        year=2018,
        full_title="Openwell submersible pumpsets - Specification",
        scope_summary="",
        status="ACTIVE",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.90,
        relevance_reason="Submersible pump match"
    )

    cand_borewell = SearchResult(
        standard_id="IS-8034-2018",
        standard_number="IS 8034 : 2018",
        year=2018,
        full_title="Submersible pumpsets - Specification",
        scope_summary="",
        status="ACTIVE",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.88,
        relevance_reason="Submersible pumpset match"
    )

    res_open = applicability_gate.evaluate_candidate(cand_openwell, req_text)
    assert res_open.applicable is False
    assert any("openwell" in r.lower() for r in res_open.rejection_reasons)

    res_bore = applicability_gate.evaluate_candidate(cand_borewell, req_text)
    assert res_bore.applicable is True


# ===========================================================================
# 3. Candidate Pool Continuation (Constraint 7)
# ===========================================================================

def test_candidate_pool_continuation_skips_incompatible_top1():
    """
    Constraint 7: When Top-1 candidate is rejected by applicability or lifecycle,
    pipeline inspects downstream candidates in pool and returns the best validated candidate.
    """
    from src.recommend import StandardsRecommender
    recommender = StandardsRecommender()

    # Query 4: HT XLPE 11 kV cable
    # Top-1 retrieved is IS 7098 (Part 1) : 2025 (incompatible voltage)
    # Next candidate in pool is IS 7098 (Part 2) : 2011 (compatible voltage)
    rec = recommender.recommend_for_text("HT XLPE insulated power cables 11 kV grade")
    assert rec.candidate_standard is not None
    assert "IS 7098 (Part 2)" in rec.candidate_standard
    assert rec.applicability is not None
    assert rec.applicability["applicable"] is True
