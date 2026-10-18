"""
tests/test_milestone9_applicability.py — Milestone 9 Test Suite
Validates the Applicability + Abstention Gate:
1. Crane rail track does NOT recommend IS/ISO 10434 or any valve standard (abstains cleanly).
2. Positive regression: CPVC pipes conforming to IS 15778 -> IS 15778:2007.
3. Positive regression: Waterworks valves -> IS 778:1984 with review.
4. Positive regression: Superseded IS 10611 -> IS/ISO 10434:2020 successor.
5. Nonsense input abstains cleanly.
6. Retrieval score cannot override domain conflict.
7. Multi-candidate evaluation independence.
8. Negative benchmark False Positive Rate = 0.0% and Negative Rejection Rate = 100.0%.
"""

import pytest
from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.search import SearchResult
from src.applicability import ApplicabilityGate, ApplicabilityDecision
from src.evaluate import evaluate_negative_benchmark


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
# 1. Exact Failure Case: Crane Rail Track MUST NOT recommend IS/ISO 10434
# ---------------------------------------------------------------------------

def test_crane_rail_track_abstains_no_valve_recommendation(recommender):
    """
    CRITICAL FAILURE TEST:
    Tender: "REPLACEMENT OF CRANE RAIL TRACK FOR RMQC (RAIL MOUNTED QUAY CRANE)
            INCLUDING ALLIED WORKS AT BERTH NO. 11 and 12 IN DOCK AREA, H.D.C, HALDIA"
    The system MUST NOT recommend IS/ISO 10434 or any valve standard.
    Must abstain with candidate_standard=None, decision=NO_RELIABLE_MATCH, human_review_required=True.
    """
    tender_text = (
        "REPLACEMENT OF CRANE RAIL TRACK FOR RMQC (RAIL MOUNTED QUAY CRANE) "
        "INCLUDING ALLIED WORKS AT BERTH NO. 11 and 12 IN DOCK AREA, H.D.C, HALDIA"
    )
    req = extract_from_text(tender_text, requirement_id="REQ-CRANE-01")
    result = recommender.recommend_for_requirement(req)

    # 1. Must NOT recommend IS/ISO 10434 or any valve standard
    assert result.candidate_standard is None, (
        f"Expected candidate_standard to be None, got {result.candidate_standard}"
    )
    for rec in result.recommendations:
        assert "10434" not in rec.standard_number, "IS/ISO 10434 must not be in recommendations"
        assert "valve" not in rec.title.lower(), f"Unrelated valve standard recommended: {rec.title}"

    # 2. Decision must be clean abstention
    critic_res = result.critic_result or {}
    assert critic_res.get("decision") == "NO_RELIABLE_MATCH"
    assert result.human_review_required is True

    # 3. User-facing title and explanation
    assert result.title == "No Reliable Indian Standard Match Found"
    assert "No reliable Indian Standard match found" in result.reason
    assert "We could not establish a sufficiently supported Indian Standard" in result.reason

    # 4. Transparency: why_not must articulate why valve standard was rejected
    why_not_str = " ".join(result.why_not)
    assert "IS/ISO 10434" in why_not_str or "valves" in why_not_str.lower()
    assert "crane" in why_not_str.lower() or "mismatch" in why_not_str.lower() or "conflict" in why_not_str.lower()


# ---------------------------------------------------------------------------
# 2. Positive Regression Tests
# ---------------------------------------------------------------------------

def test_positive_regression_cpvc(recommender):
    """
    CPVC pipes requirement with explicit citation to IS 15778.
    Must recommend IS 15778:2007 with High confidence and active status.
    """
    tender_text = (
        "Supply and installation of CPVC pipes and fittings for domestic hot and cold "
        "water distribution system, conforming to IS 15778."
    )
    req = extract_from_text(tender_text, requirement_id="REQ-CPVC-01")
    result = recommender.recommend_for_requirement(req)

    assert result.candidate_standard is not None
    assert "15778" in result.candidate_standard
    assert "CPVC" in result.title or "Chlorinated Polyvinyl Chloride" in result.title
    assert result.critic_result.get("decision") == "RECOMMEND"
    assert result.human_review_required is False

    # Check applicability metadata
    assert result.applicability is not None
    assert result.applicability["applicable"] is True
    assert result.applicability["domain_match"] is True
    assert result.applicability["product_match"] is True
    assert result.applicability["scope_match"] is True


def test_positive_regression_waterworks_valves(recommender):
    """
    Waterworks valves requirement.
    IS 778:1984 should remain a recommendation with human review required (ambiguity on exact metallurgy/size).
    """
    tender_text = (
        "Supply and installation of waterworks valves for potable water pipelines, "
        "including sluice/gate valves and check valves."
    )
    req = extract_from_text(tender_text, requirement_id="REQ-VALVE-01")
    result = recommender.recommend_for_requirement(req)

    assert result.candidate_standard is not None
    # Waterworks valves can recommend IS 14846 or IS 778
    all_recs = [result.candidate_standard] + [r.standard_number for r in result.recommendations] + result.alternatives
    assert any("778" in s or "14846" in s for s in all_recs), f"Expected IS 778 or IS 14846 in candidates: {all_recs}"
    assert result.human_review_required is True
    assert result.applicability is not None
    assert result.applicability["applicable"] is True
    assert result.applicability["domain_match"] is True


def test_positive_regression_superseded_valve(recommender):
    """
    Procurement citing superseded standard IS 10611:1983.
    Must recommend current active replacement IS/ISO 10434:2020 and flag IS 10611 as superseded.
    """
    tender_text = "Procurement of bolted bonnet steel gate valves conforming to IS 10611 : 1983."
    req = extract_from_text(tender_text, requirement_id="REQ-SUPERSEDED-01")
    result = recommender.recommend_for_requirement(req)

    assert result.candidate_standard is not None
    assert "10434" in result.candidate_standard
    assert result.human_review_required is True
    assert "IS 10611" in result.reason or "superseded" in result.reason.lower()


def test_nonsense_input_abstains(recommender):
    """
    Nonsense input 'xyz abc 123' must abstain cleanly without inventing any IS standard.
    """
    req = extract_from_text("xyz abc 123", requirement_id="REQ-NONSENSE-01")
    result = recommender.recommend_for_requirement(req)

    assert result.candidate_standard is None
    assert result.critic_result.get("decision") == "NO_RELIABLE_MATCH"
    assert result.human_review_required is True
    assert result.title == "No Reliable Indian Standard Match Found"


# ---------------------------------------------------------------------------
# 3. Unit Tests on Applicability Gate Logic
# ---------------------------------------------------------------------------

def test_score_cannot_override_domain_conflict(gate):
    """
    CORE PRINCIPLE TEST:
    A high retrieval score (BM25=1.0, semantic=1.0, reranker=1.0) must NEVER
    override a domain conflict.
    """
    cand = SearchResult(
        standard_id="IS_10434",
        standard_number="IS/ISO 10434",
        full_title="Bolted Bonnet Steel Gate Valves for the Petroleum, Petrochemical and Allied Industries",
        year="2020",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_reason="High keyword score",
        scope_summary="Specification for bolted bonnet steel gate valves",
        relevance_score=1.0,
        bm25_score=1.0,
        semantic_score=1.0,
        deterministic_score=1.0,
        reranker_score=1.0,
        final_score=1.0
    )

    tender_req = "REPLACEMENT OF CRANE RAIL TRACK FOR RMQC (RAIL MOUNTED QUAY CRANE)"
    app_res = gate.evaluate_candidate(cand, tender_req)

    assert app_res.applicable is False
    assert app_res.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert app_res.applicability_score == 0.0
    assert len(app_res.conflict_flags) > 0
    assert any("DOMAIN_CONFLICT" in f for f in app_res.conflict_flags)
    assert any("valves" in r.lower() for r in app_res.rejection_reasons)


def test_multi_candidate_independence(gate):
    """
    Evaluates each candidate independently.
    In a mixed pool (matching standard vs conflicting standard),
    the matching standard must pass and the conflicting standard must be rejected.
    """
    tender_req = "Supply and installation of waterworks valves for potable water pipeline"

    valve_cand = SearchResult(
        standard_id="IS_778",
        standard_number="IS 778",
        full_title="Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes",
        year="1984",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_reason="valve match",
        scope_summary="Valves for waterworks purposes",
        relevance_score=0.85,
        bm25_score=0.85,
        semantic_score=0.80,
        deterministic_score=0.0,
        reranker_score=0.82,
        final_score=0.83
    )

    tile_cand = SearchResult(
        standard_id="IS_15622",
        standard_number="IS 15622",
        full_title="Pressed Ceramic Tiles - Specification",
        year="2017",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_reason="forced retrieval hit",
        scope_summary="Specification for ceramic tiles",
        relevance_score=0.50,
        bm25_score=0.50,
        semantic_score=0.30,
        deterministic_score=0.0,
        reranker_score=0.20,
        final_score=0.35
    )

    res_valve = gate.evaluate_candidate(valve_cand, tender_req)
    res_tile = gate.evaluate_candidate(tile_cand, tender_req)

    assert res_valve.applicable is True
    assert res_valve.decision in [ApplicabilityDecision.APPLICABLE.value, ApplicabilityDecision.REVIEW_REQUIRED.value]

    assert res_tile.applicable is False
    assert res_tile.decision == ApplicabilityDecision.NOT_APPLICABLE.value


# ---------------------------------------------------------------------------
# 4. Negative Benchmark Evaluation Test
# ---------------------------------------------------------------------------

def test_negative_benchmark_metrics(recommender):
    """
    Runs the negative benchmark dataset across all 5 test cases.
    Verifies:
    - False Positive Rate is 0.0%
    - Negative Rejection Rate is 100.0%
    """
    metrics = evaluate_negative_benchmark(recommender)

    assert metrics["total_cases"] == 5
    assert metrics["false_positive_count"] == 0, (
        f"False positives detected in negative benchmark: {metrics['case_results']}"
    )
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["negative_rejection_rate"] == 100.0


# ---------------------------------------------------------------------------
# 5. Non-Submersible Pump Boundary Tests (Blocker 3 Regression)
# ---------------------------------------------------------------------------

def test_non_submersible_pump_boundary(gate):
    """
    Verifies that 'non-submersible' or 'non submersible' pumps are NOT
    treated as submersible pumps, preventing incorrect IS 8034 applicability.
    """
    is8034_cand = SearchResult(
        standard_id="IS-8034-2018",
        standard_number="IS 8034",
        full_title="Submersible Pumpsets - Specification",
        year="2018",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.90,
        relevance_reason="Submersible pumpset",
        scope_summary="Submersible pumpsets for clear cold water",
        bm25_score=0.90,
        semantic_score=0.85,
        deterministic_score=0.0,
        reranker_score=0.88,
        final_score=0.89
    )

    # 1. Submersible pump -> should be applicable to IS 8034
    res1 = gate.evaluate_candidate(is8034_cand, "submersible pump")
    assert res1.applicable is True
    assert not any("submersible" in f.lower() for f in res1.conflict_flags)

    # 2. Non-submersible pump -> must NOT be applicable, must flag conflict
    res2 = gate.evaluate_candidate(is8034_cand, "non-submersible pump")
    assert res2.applicable is False
    assert res2.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert any("APPLICATION_CONFLICT" in f for f in res2.conflict_flags)

    # 3. Non submersible pump (space separated) -> must NOT be applicable
    res3 = gate.evaluate_candidate(is8034_cand, "non submersible pump")
    assert res3.applicable is False
    assert res3.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert any("APPLICATION_CONFLICT" in f for f in res3.conflict_flags)

    # 4. Non-submersible horizontal end suction centrifugal pump -> must NOT be applicable
    res4 = gate.evaluate_candidate(is8034_cand, "non-submersible horizontal end suction centrifugal pump")
    assert res4.applicable is False
    assert res4.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert any("APPLICATION_CONFLICT" in f for f in res4.conflict_flags)

    # 5. Borewell submersible pump -> should be applicable
    res5 = gate.evaluate_candidate(is8034_cand, "borewell submersible pump")
    assert res5.applicable is True
    assert not any("submersible" in f.lower() for f in res5.conflict_flags)

    # 6. Surface pump -> must NOT be applicable to IS 8034
    res6 = gate.evaluate_candidate(is8034_cand, "surface pump")
    assert res6.applicable is False
    assert any("APPLICATION_CONFLICT" in f for f in res6.conflict_flags)

    # 7. Non-submersible horizontal end suction centrifugal water process pump
    res7 = gate.evaluate_candidate(is8034_cand, "Non-submersible horizontal end suction centrifugal water process pump")
    assert res7.applicable is False
    assert res7.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert any("APPLICATION_CONFLICT" in f for f in res7.conflict_flags)


# ---------------------------------------------------------------------------
# 6. Negative-Control False-Positive Regression Tests (Phase 13 / M12 Investigation)
# ---------------------------------------------------------------------------

def test_neg004_structural_steel_framing_abstains_rejects_concrete_rebar(recommender, gate):
    """
    FAILURE MODE 1 (Unsafe Recommendation):
    Tender: "Design, fabrication and erection of structural steel roof trusses and purlins for industrial workshop shed."
    The system MUST NOT recommend IS 1786 (concrete reinforcement rebar) or IS 432.
    Must abstain with candidate_standard=None, decision=NO_RELIABLE_MATCH, human_review_required=True.
    """
    # 1. Direct Applicability Gate Check: IS 1786 must be rejected for structural steel framing
    is1786_cand = SearchResult(
        standard_id="IS-1786-2008",
        standard_number="IS 1786",
        full_title="High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - Specification",
        year="2008",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.85,
        relevance_reason="Steel bars specification",
        scope_summary="High strength deformed steel bars and wires for concrete reinforcement",
        bm25_score=0.85,
        semantic_score=0.80,
        deterministic_score=0.0,
        reranker_score=0.82,
        final_score=0.83
    )
    tender_text = "Design, fabrication and erection of structural steel roof trusses and purlins for industrial workshop shed."
    gate_res = gate.evaluate_candidate(is1786_cand, tender_text)
    assert gate_res.applicable is False
    assert gate_res.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert any("APPLICATION_CONFLICT" in f for f in gate_res.conflict_flags)
    assert any("structural steel framing" in r.lower() for r in gate_res.rejection_reasons)

    # 2. End-to-end recommender evaluation: clean abstention
    req = extract_from_text(tender_text, requirement_id="NEG-004")
    rec_res = recommender.recommend_for_requirement(req)

    assert rec_res.candidate_standard is None, (
        f"Expected candidate_standard to be None, got {rec_res.candidate_standard}"
    )
    assert rec_res.human_review_required is True
    critic_res = rec_res.critic_result or {}
    assert critic_res.get("decision") == "NO_RELIABLE_MATCH"
    assert rec_res.title == "No Reliable Indian Standard Match Found"

    # Verify IS 1786 was explicitly flagged in why_not
    why_not_str = " ".join(rec_res.why_not)
    assert "IS 1786" in why_not_str or "concrete reinforcement" in why_not_str.lower()
    assert "structural steel framing" in why_not_str.lower()

    # 3. Positive Control: Concrete reinforcement requirement must STILL accept IS 1786
    concrete_rebar_text = "Supply and laying of Fe 500D high strength deformed steel rebar for RCC column foundation reinforcement."
    pos_gate_res = gate.evaluate_candidate(is1786_cand, concrete_rebar_text)
    assert pos_gate_res.applicable is True
    assert not any("structural steel framing" in f.lower() for f in pos_gate_res.conflict_flags)


def test_d2_structural_steel_trusses_rejects_both_is1786_and_is432(gate):
    """
    Step 2 Test 1:
    Structural steel roof trusses and purlins must not be matched to concrete-reinforcement
    standards (IS 1786 rebar OR IS 432 mild steel wire/bars for concrete reinforcement)
    solely because both contain the word 'steel'.
    """
    is432_cand = SearchResult(
        standard_id="IS-432-1-1982",
        standard_number="IS 432 (Part 1)",
        full_title="Specification for Mild Steel and Medium Tensile Steel Bars and Hard-Drawn Steel Wire for Concrete Reinforcement",
        year="1982",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.82,
        relevance_reason="Steel bars for reinforcement",
        scope_summary="Mild steel bars and wires for concrete reinforcement",
        bm25_score=0.80,
        semantic_score=0.75,
        deterministic_score=0.0,
        reranker_score=0.78,
        final_score=0.80
    )
    is1786_cand = SearchResult(
        standard_id="IS-1786-2008",
        standard_number="IS 1786",
        full_title="High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - Specification",
        year="2008",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.85,
        relevance_reason="Steel bars specification",
        scope_summary="High strength deformed steel bars and wires for concrete reinforcement",
        bm25_score=0.85,
        semantic_score=0.80,
        deterministic_score=0.0,
        reranker_score=0.82,
        final_score=0.83
    )
    truss_req = "Design, fabrication and erection of structural steel roof trusses and purlins for industrial workshop shed."
    
    # Both concrete reinforcement standards must be rejected for structural steel roof trusses
    res_1786 = gate.evaluate_candidate(is1786_cand, truss_req)
    assert res_1786.applicable is False
    assert res_1786.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert any("APPLICATION_CONFLICT" in f for f in res_1786.conflict_flags)
    assert any("structural steel framing" in r.lower() for r in res_1786.rejection_reasons)

    res_432 = gate.evaluate_candidate(is432_cand, truss_req)
    assert res_432.applicable is False
    assert res_432.decision == ApplicabilityDecision.NOT_APPLICABLE.value
    assert any("APPLICATION_CONFLICT" in f for f in res_432.conflict_flags)
    assert any("structural steel framing" in r.lower() for r in res_432.rejection_reasons)


def test_d2_genuine_concrete_reinforcement_remains_eligible(gate):
    """
    Step 2 Test 2:
    Genuine concrete reinforcement requirements must still be eligible for IS 1786 and IS 432.
    """
    is1786_cand = SearchResult(
        standard_id="IS-1786-2008",
        standard_number="IS 1786",
        full_title="High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - Specification",
        year="2008",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.85,
        relevance_reason="Steel bars specification",
        scope_summary="High strength deformed steel bars and wires for concrete reinforcement",
        bm25_score=0.85,
        semantic_score=0.80,
        deterministic_score=0.0,
        reranker_score=0.82,
        final_score=0.83
    )
    rebar_req = "Supply and bending of Fe 500 TMT steel rebar for RCC column foundation reinforcement."
    res = gate.evaluate_candidate(is1786_cand, rebar_req)
    assert res.applicable is True
    assert not any("APPLICATION_CONFLICT" in f for f in res.conflict_flags)


def test_d2_structural_steelwork_not_rejected_by_generic_steel_terminology(gate):
    """
    Step 2 Test 3:
    Related structural steel requirements should not be rejected merely because they contain
    generic steel terminology when evaluated against general structural steel standards.
    """
    is800_cand = SearchResult(
        standard_id="IS-800-2007",
        standard_number="IS 800",
        full_title="General Construction in Steel - Code of Practice",
        year="2007",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.90,
        relevance_reason="General structural steel construction",
        scope_summary="Code of practice for general construction in steel",
        bm25_score=0.90,
        semantic_score=0.85,
        deterministic_score=0.0,
        reranker_score=0.88,
        final_score=0.89
    )
    is1161_cand = SearchResult(
        standard_id="IS-1161-2014",
        standard_number="IS 1161",
        full_title="Steel Tubes for Structural Purposes - Specification",
        year="2014",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.88,
        relevance_reason="Structural steel tubular sections",
        scope_summary="Specification for steel tubes for structural purposes",
        bm25_score=0.85,
        semantic_score=0.82,
        deterministic_score=0.0,
        reranker_score=0.84,
        final_score=0.86
    )
    structural_req = (
        "Design, fabrication and erection of mild steel tubular columns, rafters and base plates "
        "for warehouse structural steelwork framing."
    )
    # Neither standard should trigger the D2 APPLICATION_CONFLICT
    res_800 = gate.evaluate_candidate(is800_cand, structural_req)
    assert not any("APPLICATION_CONFLICT" in f for f in res_800.conflict_flags)
    assert not any("concrete reinforcement" in r.lower() for r in res_800.rejection_reasons)

    res_1161 = gate.evaluate_candidate(is1161_cand, structural_req)
    assert not any("APPLICATION_CONFLICT" in f for f in res_1161.conflict_flags)
    assert not any("concrete reinforcement" in r.lower() for r in res_1161.rejection_reasons)


def test_compound_and_ambiguous_steel_preserves_safeguards(recommender):
    """
    Step 2 Test 4:
    Compound requirements and ambiguous descriptions must not bypass existing review or
    abstention safeguards.
    """
    # 4A. Compound requirement: RCC foundation rebar + structural steel roof trusses
    compound_req_text = (
        "Construction of industrial shed including RCC column foundation reinforcement "
        "with Fe 500 rebar and structural steel roof trusses with tubular purlins."
    )
    req_comp = extract_from_text(compound_req_text, requirement_id="REQ-COMPOUND-01")
    rec_comp = recommender.recommend_for_requirement(req_comp)
    # Compound nature MUST trigger human_review_required
    assert rec_comp.human_review_required is True, (
        "Compound requirements with multiple structural scopes must mandate human review"
    )

    # 4B. Ambiguous requirement: Vague steel works without specification
    ambiguous_req_text = "Structural steel fabrication works as directed by site in-charge."
    req_amb = extract_from_text(ambiguous_req_text, requirement_id="REQ-AMBIGUOUS-01")
    rec_amb = recommender.recommend_for_requirement(req_amb)
    # Ambiguous scope must NOT autonomously recommend rebar, must preserve review/abstention safeguards
    assert rec_amb.human_review_required is True, (
        "Ambiguous steel requirement must preserve review/abstention safeguards"
    )
    assert rec_amb.candidate_standard is None, (
        f"Expected abstention (candidate_standard=None) for ambiguous steel works, got {rec_amb.candidate_standard}"
    )
    critic_dec = (rec_amb.critic_result or {}).get("decision")
    assert critic_dec in ["NO_RELIABLE_MATCH", "REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE"]


def test_neg002_power_cable_subcomponent_review_and_benchmark_classification(recommender):
    """
    FAILURE MODE 2 (Dataset Formulation / Evaluation Classification Defect):
    Tender: "Supply and laying of 1.1 kV grade copper conductor armored power and control cables for substation automation system."
    Demonstrates that NEG-002 is a valid in-domain electrical procurement requirement rather than an ineligible negative control.
    The system correctly recommends IS 7098 (Part 1) : 1988 with RECOMMEND_WITH_REVIEW (human_review_required=True)
    due to composite subcomponents (power cables vs control cables).
    """
    tender_text = (
        "Supply and laying of 1.1 kV grade copper conductor armored power and control cables "
        "for substation automation system."
    )
    req = extract_from_text(tender_text, requirement_id="NEG-002")
    rec_res = recommender.recommend_for_requirement(req)

    # Engine correctly identifies IS 7098 (Part 1) as valid 1.1 kV cable standard
    assert rec_res.candidate_standard is not None
    assert "7098" in rec_res.candidate_standard
    # Human review is flagged because of installation / component context
    assert rec_res.human_review_required is True
    assert rec_res.critic_result.get("decision") in ["RECOMMEND", "RECOMMEND_WITH_REVIEW"]



