"""
tests/test_applicability_multidomain.py - Comprehensive Multi-Domain Applicability Test Suite

Validates TenderSaathi 2.0 Phase 1 Applicability Engine:
1. CPVC dual-use golden scenarios (potable water vs fire sprinkler).
2. CPVC ambiguous context -> UNKNOWN / MISSING_APPLICATION_CONTEXT.
3. Multi-domain generalization:
   - Drainage vs Potable piping (IS 15328 vs IS 4985).
   - Low-voltage vs Medium/High-voltage power cables (IS 7098 Pt 1 vs Pt 2).
   - Deformed / TMT reinforcement steel vs Mild steel (IS 1786 vs IS 432).
   - Terrestrial electrical switchgear vs Marine/Shipboard equipment.
4. Non-conflation of INCOMPATIBLE vs UNKNOWN.
5. Auditability: reason_code, human_reason, evidence_text, and evidence_source preserved.
"""

import pytest
from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.search import SearchResult
from src.applicability import (
    ApplicabilityGate,
    ApplicabilityState,
    ApplicabilityReasonCode,
    ApplicabilityDecision
)


@pytest.fixture(scope="module")
def shared_db():
    return StandardsDatabase()


@pytest.fixture(scope="module")
def recommender(shared_db):
    return StandardsRecommender(db=shared_db)


@pytest.fixture(scope="module")
def gate():
    return ApplicabilityGate()


# ---------------------------------------------------------------------------
# 1. CPVC Dual-Application Discrimination (Golden Scenarios)
# ---------------------------------------------------------------------------

def test_cpvc_potable_water_discrimination(gate):
    """
    CPVC pipes for domestic hot and cold water distribution:
    - IS 15778 must be APPLICABLE
    - Fire sprinkler pipe standard must be INCOMPATIBLE with INCOMPATIBLE_APPLICATION
    """
    cand_potable = SearchResult(
        standard_id="IS-15778-2007",
        standard_number="IS 15778 : 2007",
        year="2007",
        version_role="CURRENT_ACTIVE",
        full_title="Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Distribution Supplies - Specification",
        status="ACTIVE",
        relevance_score=0.92,
        relevance_reason="CPVC pipes for potable water",
        scope_summary="Specification for CPVC pipes for potable hot and cold water distribution supplies",
        final_score=0.92,
        verification_status="VERIFIED"
    )

    cand_sprinkler = SearchResult(
        standard_id="IS-16088-2012",
        standard_number="IS 16088 : 2012",
        year="2012",
        version_role="CURRENT_ACTIVE",
        full_title="Chlorinated polyvinyl chloride (CPVC) pipes for automatic sprinkler fire extinguishing system - Specification",
        status="ACTIVE",
        relevance_score=0.91,
        relevance_reason="CPVC pipes for fire sprinkler",
        scope_summary="Specification for CPVC pipes for automatic sprinkler fire extinguishing system",
        final_score=0.91,
        verification_status="VERIFIED"
    )

    req_text = "Supply of CPVC pipes for domestic hot and cold potable water distribution system"

    res_potable = gate.evaluate_candidate(cand_potable, req_text)
    assert res_potable.state == ApplicabilityState.APPLICABLE
    assert res_potable.reason_code == ApplicabilityReasonCode.APPLICABLE
    assert res_potable.applicable is True

    res_sprinkler = gate.evaluate_candidate(cand_sprinkler, req_text)
    assert res_sprinkler.state == ApplicabilityState.INCOMPATIBLE
    assert res_sprinkler.reason_code == ApplicabilityReasonCode.INCOMPATIBLE_APPLICATION
    assert res_sprinkler.applicable is False
    assert "fire extinguishing" in res_sprinkler.human_reason.lower() or "incompatible" in res_sprinkler.human_reason.lower()
    assert res_sprinkler.evidence_text is not None


def test_cpvc_fire_sprinkler_discrimination(gate):
    """
    CPVC pipes for automatic fire sprinkler systems:
    - Fire sprinkler standard must be APPLICABLE
    - IS 15778 (potable water) must be INCOMPATIBLE with INCOMPATIBLE_APPLICATION
    """
    cand_potable = SearchResult(
        standard_id="IS-15778-2007",
        standard_number="IS 15778 : 2007",
        year="2007",
        version_role="CURRENT_ACTIVE",
        full_title="Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Distribution Supplies - Specification",
        status="ACTIVE",
        relevance_score=0.91,
        relevance_reason="CPVC pipes for potable water",
        scope_summary="Specification for CPVC pipes for potable hot and cold water distribution supplies",
        final_score=0.91,
        verification_status="VERIFIED"
    )

    cand_sprinkler = SearchResult(
        standard_id="IS-16088-2012",
        standard_number="IS 16088 : 2012",
        year="2012",
        version_role="CURRENT_ACTIVE",
        full_title="Chlorinated polyvinyl chloride (CPVC) pipes for automatic sprinkler fire extinguishing system - Specification",
        status="ACTIVE",
        relevance_score=0.93,
        relevance_reason="CPVC pipes for fire sprinkler",
        scope_summary="Specification for CPVC pipes for automatic sprinkler fire extinguishing system",
        final_score=0.93,
        verification_status="VERIFIED"
    )

    req_text = "CPVC piping for wet pipe automatic fire sprinkler systems"

    res_sprinkler = gate.evaluate_candidate(cand_sprinkler, req_text)
    assert res_sprinkler.state == ApplicabilityState.APPLICABLE
    assert res_sprinkler.reason_code == ApplicabilityReasonCode.APPLICABLE
    assert res_sprinkler.applicable is True

    res_potable = gate.evaluate_candidate(cand_potable, req_text)
    assert res_potable.state == ApplicabilityState.INCOMPATIBLE
    assert res_potable.reason_code == ApplicabilityReasonCode.INCOMPATIBLE_APPLICATION
    assert res_potable.applicable is False
    assert "potable" in res_potable.human_reason.lower() or "incompatible" in res_potable.human_reason.lower()


def test_cpvc_ambiguous_context_returns_unknown(gate):
    """
    Ambiguous requirement without operating application context:
    "Procurement of 25mm CPVC pipes and fittings"
    Must evaluate candidate as UNKNOWN with MISSING_APPLICATION_CONTEXT and provide a clarification prompt.
    """
    cand_potable = SearchResult(
        standard_id="IS-15778-2007",
        standard_number="IS 15778 : 2007",
        year="2007",
        version_role="CURRENT_ACTIVE",
        full_title="Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Distribution Supplies - Specification",
        status="ACTIVE",
        relevance_score=0.88,
        relevance_reason="CPVC pipes",
        scope_summary="Specification for CPVC pipes for potable hot and cold water distribution supplies",
        final_score=0.88,
        verification_status="VERIFIED"
    )

    req_text = "Procurement of 25mm CPVC pipes and fittings"
    res = gate.evaluate_candidate(cand_potable, req_text)

    assert res.state == ApplicabilityState.UNKNOWN
    assert res.reason_code == ApplicabilityReasonCode.MISSING_APPLICATION_CONTEXT
    assert res.applicable is True  # Kept in pool for review/clarification
    assert res.missing_information is not None
    assert "service application" in res.missing_information.lower()
    assert res.clarification_prompt is not None


# ---------------------------------------------------------------------------
# 2. Multi-Domain Generalization Scenarios
# ---------------------------------------------------------------------------

def test_drainage_vs_potable_piping_generalization(gate):
    """
    Drainage vs Potable piping:
    Requirement: "uPVC pipes for gravity underground sewerage and drainage"
    Candidate: IS 4985 (potable water supply) -> INCOMPATIBLE_APPLICATION
    """
    cand_4985 = SearchResult(
        standard_id="IS-4985-2021",
        standard_number="IS 4985 : 2021",
        year="2021",
        version_role="CURRENT_ACTIVE",
        full_title="Unplasticized Polyvinyl Chloride (uPVC) Pipes for Potable Water Supplies - Specification",
        status="ACTIVE",
        relevance_score=0.85,
        relevance_reason="uPVC pipes",
        scope_summary="Unplasticized polyvinyl chloride pipes for potable water supplies",
        final_score=0.85,
        verification_status="VERIFIED"
    )

    req_text = "uPVC pipes for gravity underground sewerage and drainage systems"
    res = gate.evaluate_candidate(cand_4985, req_text)

    assert res.state == ApplicabilityState.INCOMPATIBLE
    assert res.reason_code == ApplicabilityReasonCode.INCOMPATIBLE_APPLICATION
    assert res.applicable is False
    assert "potable" in res.human_reason.lower() or "drainage" in res.human_reason.lower()


def test_cable_voltage_tier_boundary_generalization(gate):
    """
    Cable voltage tier boundary check:
    Requirement specifies 11 kV (Medium/High Voltage).
    Candidate IS 7098 (Part 1) title explicitly limits to <= 1100 V.
    Must reject with PARAMETER_OUT_OF_SCOPE.
    """
    cand_7098_p1 = SearchResult(
        standard_id="IS-7098-1-1988",
        standard_number="IS 7098 (Part 1) : 1988",
        year="1988",
        version_role="CURRENT_ACTIVE",
        full_title="Cross-linked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 1 For Working Voltages up to and Including 1100 V",
        status="ACTIVE",
        relevance_score=0.89,
        relevance_reason="XLPE cable",
        scope_summary="XLPE insulated cables for working voltages up to and including 1100 V",
        final_score=0.89,
        verification_status="VERIFIED"
    )

    req_text = "11 kV grade cross-linked polyethylene (XLPE) insulated power cables"
    res = gate.evaluate_candidate(cand_7098_p1, req_text)

    assert res.state == ApplicabilityState.INCOMPATIBLE
    assert res.reason_code == ApplicabilityReasonCode.PARAMETER_OUT_OF_SCOPE
    assert res.applicable is False
    assert "voltage" in res.human_reason.lower()


def test_steel_grade_process_generalization(gate):
    """
    Steel reinforcement process:
    Requirement specifies TMT / Fe 500D deformed bars.
    Candidate IS 432 covers mild steel (Fe 250).
    Must reject with INCOMPATIBLE_APPLICATION.
    """
    cand_432 = SearchResult(
        standard_id="IS-432-1-1982",
        standard_number="IS 432 (Part 1) : 1982",
        year="1982",
        version_role="CURRENT_ACTIVE",
        full_title="Specification for Mild Steel and Medium Tensile Steel Bars and Hard-Drawn Steel Wire for Concrete Reinforcement",
        status="ACTIVE",
        relevance_score=0.86,
        relevance_reason="Steel bars for concrete reinforcement",
        scope_summary="Mild steel and medium tensile steel bars for concrete reinforcement",
        final_score=0.86,
        verification_status="VERIFIED"
    )

    req_text = "Thermo-mechanically treated (TMT) Fe 500D steel bars for concrete reinforcement"
    res = gate.evaluate_candidate(cand_432, req_text)

    assert res.state == ApplicabilityState.INCOMPATIBLE
    assert res.reason_code == ApplicabilityReasonCode.INCOMPATIBLE_APPLICATION
    assert res.applicable is False
    assert "mild steel" in res.human_reason.lower() or "tmt" in res.human_reason.lower()


def test_marine_shipboard_environmental_exclusion(gate):
    """
    Marine/shipboard equipment applied to terrestrial requirement:
    Candidate specifies shipboard equipment; requirement specifies terrestrial commercial installation.
    Must reject with INCOMPATIBLE_APPLICATION.
    """
    cand_marine = SearchResult(
        standard_id="IS-10242-1982",
        standard_number="IS 10242 : 1982",
        year="1982",
        version_role="CURRENT_ACTIVE",
        full_title="Electrical installations in ships - System design - General",
        status="ACTIVE",
        relevance_score=0.84,
        relevance_reason="Electrical installation",
        scope_summary="Electrical installations and distribution in ships and marine vessels",
        final_score=0.84,
        verification_status="VERIFIED"
    )

    req_text = "Low voltage electrical distribution board for commercial building installation"
    res = gate.evaluate_candidate(cand_marine, req_text)

    assert res.state == ApplicabilityState.INCOMPATIBLE
    assert res.reason_code == ApplicabilityReasonCode.INCOMPATIBLE_APPLICATION
    assert res.applicable is False
    assert "marine" in res.human_reason.lower() or "ships" in res.human_reason.lower()


# ---------------------------------------------------------------------------
# 3. End-to-End Recommender Integration Tests
# ---------------------------------------------------------------------------

def test_e2e_recommender_cpvc_potable(recommender):
    """
    End-to-end integration:
    Requirement specifying CPVC for potable water must recommend IS 15778.
    """
    req_text = "Supply and installation of CPVC pipes for domestic hot and cold potable water distribution"
    req = extract_from_text(req_text, requirement_id="REQ-TEST-CPVC-POTABLE")
    result = recommender.recommend_for_requirement(req)

    assert result.candidate_standard is not None
    assert "15778" in result.candidate_standard
    assert result.applicability is not None
    assert result.applicability.get("reason_code") == "APPLICABLE"


def test_e2e_recommender_underground_drainage_pvc(recommender):
    """
    End-to-end integration:
    Requirement specifying underground drainage/sewerage piping must include IS 15328 among
    applicable candidate recommendations and strictly exclude potable water pressure pipe IS 4985.
    """
    req_text = "Supply and laying of uPVC pipes for gravity underground sewerage and drainage"
    req = extract_from_text(req_text, requirement_id="REQ-TEST-DRAINAGE")
    result = recommender.recommend_for_requirement(req)

    assert result.candidate_standard is not None
    all_recs = [r.standard_number for r in result.recommendations]
    assert any("15328" in s for s in all_recs)
    # Verify IS 4985 was NOT recommended
    assert not any("4985" in s for s in all_recs)
