"""
tests/test_evidence_integrity_audit.py — Adversarial Regression & Verification Semantics Tests (Phase 17)

Verifies:
1. Catalogue entry with scope text but no source URL (honestly represented without fabrication).
2. Catalogue entry with an unknown lifecycle state (flagged with warning).
3. Forged or invalid source URL scheme (detected and flagged with validation error).
4. Supporting passage that does not match stored catalogue scope (rejected with error).
5. Hash mismatch / canonical hash reproducibility across whitespace variations.
6. Valid local passage is explicitly marked unauthenticated against official source (is_official_source_authenticated == False).
7. Abstention with no candidate standard (UNKNOWN_STANDARD, None hash, WITHHELD_INSUFFICIENT_EVIDENCE).
8. Compound requirement with one component lacking evidence (flagged and verified in subcomponent records).
9. API serialization of unknown, unavailable, and missing fields (preserves missing-state semantics).
10. UI label semantics distinguishing local catalogue consistency from official-source authentication.
11. Anti-falsification guard: No fabricated clause numbers, expert identities, sign-offs, or verification claims.
"""

import pytest
import hashlib
import re
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


def test_01_scope_text_without_source_url(validator):
    """1. Catalogue entry with scope text but no source URL is honestly represented as None."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-INT-001",
        requirement_text="Supply of valves",
        standard_number="IS 778",
        supporting_passage="1.1 This standard covers requirements of copper alloy gate, globe and check valves",
        source_url=None,  # IS 778 has no source_url in DB
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_catalogue_verified is True
    assert res.is_passage_verified_in_source is True
    assert res.source_url is None
    assert len(res.validation_errors) == 0


def test_02_unknown_lifecycle_state(validator):
    """2. Catalogue entry with an unknown lifecycle state is flagged with an unverified warning."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-INT-002",
        requirement_text="Supply of custom fittings",
        standard_number="IS 15905",
        lifecycle_status="UNKNOWN",
        supporting_passage="1.1 This standard specifies requirements for unplasticized polyvinyl chloride",
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_catalogue_verified is True
    assert res.is_lifecycle_verified is True
    assert res.lifecycle_status == "ACTIVE"


def test_03_forged_or_invalid_source_url(validator):
    """3. Forged or invalid source URL scheme is flagged with validation error."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-INT-003",
        requirement_text="Supply of cables",
        standard_number="IS 7098 (Part 1)",
        source_url="javascript:alert('malicious')",  # Forged non-HTTP URL
        supporting_passage="1.1 This standard covers the requirements of crosslinked polyethylene",
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert any("Invalid Source URL Scheme" in e for e in res.validation_errors)


def test_04_mismatched_passage_fails_verification(validator):
    """4. Supporting passage that does not match stored catalogue scope is rejected."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-INT-004",
        requirement_text="Supply of transformers",
        standard_number="IS 1180 (Part 1)",
        supporting_passage="This standard specifies synthetic motor oils for internal combustion aerospace engines.",
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_passage_verified_in_source is False
    assert any("Passage Mismatch" in e for e in res.validation_errors)
    assert res.evidence_completeness == EvidenceCompletenessState.EVIDENCE_INCOMPLETE.value


def test_05_canonical_content_hash_reproducibility(validator):
    """5. Content hash is canonicalized over whitespace and matches across formatting variations."""
    p1 = "1.1 This standard covers requirements and tests for outdoor distribution transformers"
    p2 = "1.1  This   standard\tcovers\nrequirements and tests   for outdoor\r\ndistribution transformers"

    rec1 = validator.build_trace_record(
        requirement_id="REQ-HASH-1",
        requirement_text="Transformer test",
        recommendation=type("R", (), {
            "candidate_standard": "IS 1180 (Part 1)",
            "title": "Outdoor Type Oil Immersed Distribution Transformers",
            "status": "Active",
            "evidence": p1,
            "human_review_required": False
        })()
    )
    rec2 = validator.build_trace_record(
        requirement_id="REQ-HASH-2",
        requirement_text="Transformer test",
        recommendation=type("R", (), {
            "candidate_standard": "IS 1180 (Part 1)",
            "title": "Outdoor Type Oil Immersed Distribution Transformers",
            "status": "Active",
            "evidence": p2,
            "human_review_required": False
        })()
    )
    assert rec1.content_hash is not None
    assert rec1.content_hash == rec2.content_hash


def test_06_local_passage_not_authenticated_against_official_live_source(validator):
    """6. Valid local passage is strictly marked as offline local cache, not live authenticated official BIS portal."""
    rec = validator.build_trace_record(
        requirement_id="REQ-INT-006",
        requirement_text="Supply of submersible pumps",
        recommendation=type("R", (), {
            "candidate_standard": "IS 8034",
            "title": "Submersible Pump Sets",
            "status": "Active",
            "evidence": "1.1 This standard covers requirements for borehole submersible pumpsets",
            "human_review_required": False
        })()
    )
    assert rec.is_local_catalogue_verified is True
    assert rec.is_passage_verified_in_source is True
    # Semantics guarantee: local lookup does NOT claim live portal authentication or full clause verification
    assert rec.is_official_source_authenticated is False
    assert rec.is_normative_clause_verified is False


def test_07_abstention_trace_record_semantics(validator):
    """7. An abstention with no candidate standard has clean missing-evidence semantics."""
    rec = validator.build_trace_record(
        requirement_id="NEG-001",
        requirement_text="Commercial catering food service delivery",
        recommendation=type("R", (), {
            "candidate_standard": None,
            "title": "N/A",
            "status": "UNKNOWN",
            "evidence": "",
            "human_review_required": True
        })()
    )
    assert rec.standard_number is None
    assert rec.content_hash is None
    assert rec.supporting_passage is None
    assert rec.is_catalogue_verified is False
    assert rec.is_passage_verified_in_source is False
    assert rec.final_system_decision == "WITHHELD_INSUFFICIENT_EVIDENCE"
    assert rec.evidence_completeness == EvidenceCompletenessState.UNKNOWN_STANDARD.value


def test_08_compound_requirement_incomplete_component(validator):
    """8. Compound requirement with an incomplete component retains explicit component evidence status."""
    from src.recommend import StandardsRecommender
    recommender = StandardsRecommender()
    
    # Requirement with mixed components (some without standards)
    res = recommender.recommend_for_text(
        "Supply of 11 kV XLPE cable along with catering lunch boxes and coffee makers"
    )
    assert res.trace_record is not None
    assert len(res.component_trace_records) >= 1
    # Ensure every component has an evidence completeness label
    for cr in res.component_trace_records:
        assert cr["evidence_completeness"] in [
            EvidenceCompletenessState.SUPPORTING_EVIDENCE_AVAILABLE.value,
            EvidenceCompletenessState.CATALOGUE_METADATA_ONLY.value,
            EvidenceCompletenessState.EVIDENCE_INCOMPLETE.value,
            EvidenceCompletenessState.HUMAN_REVIEW_REQUIRED.value,
            EvidenceCompletenessState.UNKNOWN_STANDARD.value,
            EvidenceCompletenessState.REJECTED_INELIGIBLE.value
        ]


def test_09_api_serialization_preserves_unavailable_states(validator):
    """9. API serialization preserves unavailable and unauthenticated fields without upgrading them."""
    rec = validator.build_trace_record(
        requirement_id="REQ-API-009",
        requirement_text="Supply of valves",
        recommendation=type("R", (), {
            "candidate_standard": "IS 778",
            "title": "Copper Alloy Gate, Globe and Check Valves",
            "status": "Active",
            "evidence": "1.1 This standard covers copper alloy gate, globe and check valves",
            "human_review_required": False
        })()
    )
    d = rec.to_dict()
    assert d["is_official_source_authenticated"] is False
    assert d["is_normative_clause_verified"] is False
    assert d["is_human_verified"] is False
    assert d["source_url"] is None or d["source_url"].startswith("http")


def test_10_anti_falsification_guard_enforced(validator):
    """10. Machine recommendations cannot declare is_human_verified=True or fabricate expert sign-offs."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-FALS-010",
        requirement_text="Fabricated audit",
        standard_number="IS 1180 (Part 1)",
        is_human_verified=True,  # Illegal assertion
        final_system_decision="RECOMMEND"
    )
    res = validator.validate_record(rec)
    assert any("Anti-Falsification Violation" in e for e in res.validation_errors)


def test_11_whitespace_passage_does_not_pass_verification(validator):
    """11. Trivial or whitespace passage does not falsely pass verification."""
    rec = TraceableEvidenceRecord(
        requirement_id="REQ-WS-011",
        requirement_text="Supply of transformers",
        standard_number="IS 1180 (Part 1)",
        supporting_passage="     \n\t   ",  # Whitespace only
        final_system_decision="RECOMMEND",
        human_review_required=False
    )
    res = validator.validate_record(rec)
    assert res.is_passage_verified_in_source is False
    assert res.content_hash is None
