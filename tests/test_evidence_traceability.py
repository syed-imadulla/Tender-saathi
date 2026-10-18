"""
tests/test_evidence_traceability.py — Unit Tests for Evidence Traceability & Recommendation Verification (Phase 16)

Tests:
1. Recommendation with valid stored evidence passes passage verification.
2. Recommendation with missing/unrecorded passage falls back to metadata only.
3. Recommendation with fabricated/mismatched passage fails passage verification with validation errors.
4. Recommendation referencing an unknown standard is flagged as UNKNOWN_STANDARD with errors.
5. Missing or unverified lifecycle/edition claims are flagged as warnings/unverified.
6. Compound requirements maintain individual component trace records.
7. Recommendation requiring human review cannot be presented as autonomous RECOMMEND.
8. Rejected candidate (NOT_APPLICABLE) cannot be presented as RECOMMEND.
9. Missing source metadata / unverified source files are handled cleanly.
10. Backward compatibility with existing API response consumers.
11. Anti-falsification guard: Rejects illegal machine-to-human verification upgrades.
"""

import pytest
from src.traceability import (
    TraceableEvidenceValidator,
    TraceableEvidenceRecord,
    EvidenceCompletenessState,
    EvidenceType
)
from src.standards import StandardsDatabase


@pytest.fixture
def db():
    return StandardsDatabase()


@pytest.fixture
def validator(db):
    return TraceableEvidenceValidator(db)


def test_01_valid_stored_evidence_passage_verified(validator):
    """1. Recommendation with valid stored evidence passes passage verification."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-001",
        requirement_text="Supply of 11 kV XLPE insulated power cables",
        standard_number="IS 7098 (Part 2)",
        official_title="Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
        supporting_passage="1.1 This standard covers requirements of crosslinked polyethylene",
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_catalogue_verified is True
    assert res.is_passage_verified_in_source is True
    assert res.evidence_completeness == EvidenceCompletenessState.SUPPORTING_EVIDENCE_AVAILABLE.value
    assert len(res.validation_errors) == 0


def test_02_recommendation_with_no_supporting_passage(validator):
    """2. Recommendation with no supporting passage falls back to metadata only."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-002",
        requirement_text="Supply of distribution transformers",
        standard_number="IS 1180 (Part 1)",
        official_title="Outdoor Type Oil Immersed Distribution Transformers",
        supporting_passage=None,
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_catalogue_verified is True
    assert res.is_passage_verified_in_source is False
    assert res.evidence_completeness == EvidenceCompletenessState.CATALOGUE_METADATA_ONLY.value
    assert any("Missing Supporting Passage" in w for w in res.validation_warnings)
    assert len(res.validation_errors) == 0


def test_03_fabricated_or_mismatched_passage_fails(validator):
    """3. Recommendation with fabricated/mismatched passage fails passage verification with errors."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-003",
        requirement_text="Supply of steel bars",
        standard_number="IS 1786",
        official_title="High Strength Deformed Steel Bars",
        supporting_passage="This standard covers optical fiber telecommunication laser cables.",
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_catalogue_verified is True
    assert res.is_passage_verified_in_source is False
    assert any("Passage Mismatch" in e for e in res.validation_errors)
    assert res.evidence_completeness == EvidenceCompletenessState.EVIDENCE_INCOMPLETE.value


def test_04_unknown_standard_identifier_flagged(validator):
    """4. Recommendation referencing an unknown standard is flagged as UNKNOWN_STANDARD with errors."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-004",
        requirement_text="Supply of quantum teleportation conduits",
        standard_number="IS 999999",
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_catalogue_verified is False
    assert res.evidence_completeness == EvidenceCompletenessState.UNKNOWN_STANDARD.value
    assert any("does not exist in active catalogue" in e for e in res.validation_errors)


def test_05_missing_or_contradictory_lifecycle(validator):
    """5. Contradictory lifecycle claims are detected and flagged."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-005",
        requirement_text="Supply of cast iron sluice valves",
        standard_number="IS 14846",
        lifecycle_status="WITHDRAWN", # Actual catalogue status is Active
        supporting_passage="1.1 This standard covers requirements for sluice valves",
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_catalogue_verified is True
    assert any("Lifecycle Contradiction" in e for e in res.validation_errors)


def test_06_compound_requirement_subcomponent_traces(validator):
    """6. Compound requirements maintain individual component trace records."""
    from src.recommend import StandardsRecommender
    rec = StandardsRecommender()
    res = rec.recommend_for_text(
        "Replacement of damaged pipelines by Hubless CI pipes and replacement of wall tiles and sanitary fittings"
    )
    assert res.trace_record is not None
    assert isinstance(res.component_trace_records, list)
    if res.component_recommendations:
        assert len(res.component_trace_records) == len(res.component_recommendations)
        for cr in res.component_trace_records:
            assert "requirement_id" in cr
            assert "sub_requirement_id" in cr
            assert "evidence_completeness" in cr


def test_07_review_required_cannot_be_presented_as_recommend(validator):
    """7. Recommendation requiring human review cannot be presented as fully autonomous RECOMMEND."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-007",
        requirement_text="Valve replacement in chemical plant",
        standard_number="IS 778",
        human_review_required=True,
        final_system_decision="RECOMMEND" # Contradiction: review required but marked RECOMMEND
    )
    res = validator.validate_record(rec)
    assert any("Safety Gate Violation" in e for e in res.validation_errors)
    assert res.evidence_completeness == EvidenceCompletenessState.HUMAN_REVIEW_REQUIRED.value


def test_08_rejected_candidate_cannot_be_selected(validator):
    """8. A rejected candidate (NOT_APPLICABLE) cannot be presented as selected RECOMMEND."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-008",
        requirement_text="Heavy crane rail",
        standard_number="IS 7098 (Part 1)",
        is_rejected_candidate=True,
        final_system_decision="RECOMMEND" # Contradiction
    )
    res = validator.validate_record(rec)
    assert any("Safety Gate Violation: Rejected candidate" in e for e in res.validation_errors)
    assert res.evidence_completeness == EvidenceCompletenessState.REJECTED_INELIGIBLE.value


def test_09_anti_falsification_guard_blocks_human_verified_upgrade(validator):
    """9. Anti-falsification guard rejects illegal machine-to-human verification upgrades."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-009",
        requirement_text="Supply of cables",
        standard_number="IS 7098 (Part 1)",
        is_human_verified=True, # Illegal machine assertion
        final_system_decision="RECOMMEND"
    )
    res = validator.validate_record(rec)
    assert any("Anti-Falsification Violation" in e for e in res.validation_errors)


def test_10_api_backward_compatibility(db):
    """10. Backward compatibility with existing API response consumers."""
    from src.recommend import StandardsRecommender
    rec = StandardsRecommender(db=db)
    res = rec.recommend_for_text("Supply of 11 kV XLPE insulated power cables")
    
    # Check that RequirementRecommendationResult to_dict() contains trace_record
    d = res.to_dict()
    assert "trace_record" in d
    assert "component_trace_records" in d
    assert d["trace_record"] is not None
    assert d["trace_record"]["is_catalogue_verified"] is True
    assert "evidence_completeness" in d["trace_record"]

    # Check that legacy consumer keys are 100% intact
    legacy_keys = [
        "requirement_id", "requirement_text", "category", "candidate_standard",
        "title", "status", "relevance_score", "confidence", "evidence", "provenance",
        "human_review_required", "reason", "critic_result", "applicability", "regulatory"
    ]
    for k in legacy_keys:
        assert k in d, f"Missing legacy key: {k}"
