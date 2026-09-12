import pytest
from src.ambiguity import AmbiguityEngine, AmbiguityState
from src.search import SearchResult
from src.decompose import RequirementComponent
from src.completeness import SpecificationCompletenessReport

def _mock_search_result(std_number: str, title: str, scope: str, score: float) -> SearchResult:
    return SearchResult(
        standard_id=std_number,
        standard_number=std_number,
        year=2020,
        full_title=title,
        status="active",
        version_role="CURRENT_ACTIVE",
        relevance_score=score,
        relevance_reason="Mock testing",
        scope_summary=scope,
        final_score=score,
        verification_status="VERIFIED"
    )

def test_far_scores_genuine_competitors_ambiguous():
    """Test that two genuine competitors with a large score delta still result in AMBIGUOUS, bypassing the 0.12 threshold."""
    engine = AmbiguityEngine(separation_threshold=0.12)
    
    # 694 and 7098 are competitors (PVC vs XLPE cable)
    c1 = _mock_search_result("IS 694", "PVC Insulated Cables for working voltages up to 1100 V", "PVC cables", 0.90)
    c2 = _mock_search_result("IS 7098 (Part 1)", "Crosslinked Polyethylene (XLPE) Insulated PVC Sheathed Cables", "XLPE cables", 0.70)
    
    report = engine.evaluate(
        requirement_text="Provide electrical power cable for lighting",
        decomposed_components=[],
        completeness_report=None,
        retrieved_candidates=[c1, c2],
        applicable_candidates=[c1, c2],
        rejected_candidates=[],
        candidate_applicability_map={},
        critic_outcome=None,
        explicit_standards=[]
    )
    
    assert report.ambiguity_state == AmbiguityState.AMBIGUOUS
    assert len(report.competing_interpretations) == 2
    assert report.separation_margin == 0.20

def test_explicit_discriminator_resolves_ambiguity():
    """Test that if the tender explicitly states the discriminator (e.g. XLPE), it resolves ambiguity (CLEAR)."""
    engine = AmbiguityEngine(separation_threshold=0.12)
    
    c1 = _mock_search_result("IS 694", "PVC Insulated Cables for working voltages up to 1100 V", "PVC cables", 0.90)
    c2 = _mock_search_result("IS 7098 (Part 1)", "Crosslinked Polyethylene (XLPE) Insulated PVC Sheathed Cables", "XLPE cables", 0.70)
    
    report = engine.evaluate(
        requirement_text="Provide XLPE electrical power cable for lighting",
        decomposed_components=[],
        completeness_report=None,
        retrieved_candidates=[c1, c2],
        applicable_candidates=[c1, c2],
        rejected_candidates=[],
        candidate_applicability_map={},
        critic_outcome=None,
        explicit_standards=[]
    )
    
    # Since XLPE is specified, they no longer compete on 'material' because the tender clearly specifies XLPE.
    # Therefore, ambiguity engine will not flag AMBIGUOUS.
    assert report.ambiguity_state != AmbiguityState.AMBIGUOUS

def test_non_competing_roles():
    """Test that complementary parts like a flange and gasket are not competing."""
    engine = AmbiguityEngine()
    
    c1 = _mock_search_result("IS 6392", "Steel Pipe Flanges", "Pipe flanges", 0.90)
    c2 = _mock_search_result("IS 2712", "Compressed Asbestos Fibre Jointing (Gasket)", "Jointing", 0.85)
    
    report = engine.evaluate(
        requirement_text="Supply steel pipe flange with jointing sheet",
        decomposed_components=[],
        completeness_report=None,
        retrieved_candidates=[c1, c2],
        applicable_candidates=[c1, c2],
        rejected_candidates=[],
        candidate_applicability_map={},
        critic_outcome=None,
        explicit_standards=[]
    )
    
    assert report.ambiguity_state != AmbiguityState.AMBIGUOUS

def test_unseen_domain_competition():
    """Test standard numbers not in the old hardcoded list still compete using attribute generalization."""
    engine = AmbiguityEngine()
    
    # HDPE vs uPVC for sewerage pipes (IS 14333 vs IS 4985)
    c1 = _mock_search_result("IS 14333", "High Density Polyethylene Pipes for Sewerage", "HDPE pipes", 0.90)
    c2 = _mock_search_result("IS 4985", "Unplasticized PVC Pipes for Potable Water Supplies", "uPVC pipes", 0.88)
    
    report = engine.evaluate(
        requirement_text="Supply sewerage pipes",
        decomposed_components=[],
        completeness_report=None,
        retrieved_candidates=[c1, c2],
        applicable_candidates=[c1, c2],
        rejected_candidates=[],
        candidate_applicability_map={},
        critic_outcome=None,
        explicit_standards=[]
    )
    
    # They should compete on material
    assert report.ambiguity_state == AmbiguityState.AMBIGUOUS
    assert any("material" in missing for missing in report.missing_information)
