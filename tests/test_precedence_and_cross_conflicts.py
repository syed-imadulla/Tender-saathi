"""
tests/test_precedence_and_cross_conflicts.py — Phase 22 Adversarial Cross-Requirement Test Suite

Validates the 8 deterministic scenarios for systemic tender-level interaction and conflict analysis:
1. Direct rating contradiction on shared equipment tag -> CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION
2. Operating envelope clash on shared apparatus -> CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION
3. Disjoint physical zones (false conflict avoided) -> NO_CROSS_REQUIREMENT_CONFLICT
4. Edition divergence across tender requirements -> LIFECYCLE_EDITION_DIVERGENCE
5. Product specification + Installation code co-applicability -> CO_APPLICABLE_COMPLEMENTARY_STANDARDS
6. Explicit tender specification override (buyer option) -> TENDER_SPECIFICATION_OVERRIDE
7. Overlapping product standards without statutory priority -> UNRESOLVED_NORMATIVE_PRECEDENCE
8. Missing or unverified evidence -> POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED
"""

import pytest
from typing import Dict, Any

from src.corpus.semantics import (
    CrossRequirementConflictState,
    RequirementEvidenceSupportState
)
from src.precedence.conflict_engine import (
    CrossRequirementConflictEngine,
    CrossRequirementAnalysisResult,
    CrossRequirementFinding
)


class MockRecommendationResult:
    """Lightweight deterministic test mock matching RequirementRecommendationResult interface."""
    def __init__(
        self,
        requirement_id: str,
        requirement_text: str,
        candidate_standard: str,
        standard_role: str = "PRIMARY_PRODUCT",
        clause_evidence: Dict[str, Any] = None
    ):
        self.requirement_id = requirement_id
        self.requirement_text = requirement_text
        self.candidate_standard = candidate_standard
        self.standard_role = standard_role
        self.clause_evidence = clause_evidence or {
            "requirement_evidence_support": RequirementEvidenceSupportState.FULLY_SUPPORTED.value
        }
        self.recommendations = [type("Rec", (), {
            "standard_number": candidate_standard,
            "provenance": "VERIFIED",
            "confidence": "High",
            "evidence": "Scope match"
        })()]
        self.explicit_standards_found = [candidate_standard]
        self.risk_level = "LOW"
        self.status = "Active"
        self.provenance = "VERIFIED"
        self.relevance_score = 0.95
        self.confidence = "High"
        self.human_review_required = False
        self.reason = "Standard recommended"
        self.critic_result = {"decision": "RECOMMEND"}
        self.applicability = {"decision": "ACCEPT"}
        self.dependencies = []
        self.potential_gaps = []
        self.verified_missing = []
        self.potentially_missing = []
        self.related_for_review = []
        self.ambiguity_state = "CLEAR"
        self.structured_evidence = {}
        self.evidence = "Valid scope evidence"
        self.title = "Synthetic Standard"
        self.version_role = "CURRENT_ACTIVE"
        self.why_this = []
        self.why_not = []
        self.risk_reasons = []
        self.decomposed_components = []
        self.specification_completeness = None
        self.related_standards = []
        self.category = "product_equipment"


@pytest.fixture
def conflict_engine():
    return CrossRequirementConflictEngine(db=None)


# 1. Direct rating contradiction on shared equipment tag (TR-01 100 kVA vs 200 kVA)
def test_case_01_shared_tag_rating_contradiction(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Supply of 100 kVA distribution transformer for unit TR-01.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Rating of transformer TR-01 shall be 200 kVA with copper winding.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-01")
    assert result.has_confirmed_contradictions is True
    assert result.human_review_required is True
    assert len(result.findings) >= 1
    f = result.findings[0]
    assert f.conflict_state == CrossRequirementConflictState.CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION.value
    assert "TR-01" in f.equipment_or_parameter
    assert f.escalation_action == "HUMAN_REVIEW_REQUIRED"


# 2. Operating envelope clash on shared apparatus (Indoor dry-type vs Outdoor pole-mounted)
def test_case_02_shared_apparatus_envelope_contradiction(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Distribution transformer shall be outdoor pole-mounted type.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Transformer apparatus designed strictly for indoor dry-type installation only.",
        candidate_standard="IS 11171 : 1985"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-02")
    assert result.has_confirmed_contradictions is True
    assert result.human_review_required is True
    contra_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION.value
    ]
    assert len(contra_findings) == 1
    assert "Operating Environment" in contra_findings[0].equipment_or_parameter


# 3. Disjoint physical zones (False conflict avoided)
def test_case_03_disjoint_physical_zones_no_conflict(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Outdoor switchyard cabling: 33 kV XLPE insulated armoured cables.",
        candidate_standard="IS 7098 (Part 2) : 2011"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Indoor control room wiring: 1.1 kV PVC insulated copper wire.",
        candidate_standard="IS 694 : 2010"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-03")
    assert result.has_confirmed_contradictions is False
    no_conflict_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.NO_CROSS_REQUIREMENT_CONFLICT.value
    ]
    assert len(no_conflict_findings) >= 1
    assert "disjoint" in no_conflict_findings[0].evidence_text.lower()


# 4. Edition divergence across tender requirements (IS 1180 1979 vs 2014)
def test_case_04_edition_divergence(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Transformer conforming to IS 1180 : 1979 specifications.",
        candidate_standard="IS 1180 : 1979"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Transformer testing conforming to IS 1180 (Part 1) : 2014.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-04")
    assert result.has_edition_divergence is True
    assert result.human_review_required is True
    div_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.LIFECYCLE_EDITION_DIVERGENCE.value
    ]
    assert len(div_findings) == 1
    assert div_findings[0].escalation_action == "HUMAN_REVIEW_REQUIRED"


# 5. Product specification + Installation code co-applicability (IS 1554 + IS 1255)
def test_case_05_co_applicable_complementary_standards(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Supply of 1.1 kV PVC insulated power cables.",
        candidate_standard="IS 1554 (Part 1) : 1988",
        standard_role="PRIMARY_PRODUCT"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Laying and jointing of power cables according to code of practice.",
        candidate_standard="IS 1255 : 1983",
        standard_role="INSTALLATION_CODE"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-05")
    assert result.has_confirmed_contradictions is False
    co_app_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.CO_APPLICABLE_COMPLEMENTARY_STANDARDS.value
    ]
    assert len(co_app_findings) == 1
    assert "Installation Code" in co_app_findings[0].evidence_text


# 6. Explicit tender specification override (Buyer option)
def test_case_06_tender_specification_override(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Power cables conforming to IS 1554 (Part 1).",
        candidate_standard="IS 1554 (Part 1) : 1988"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Buyer option: copper conductor mandatory, aluminium strictly prohibited.",
        candidate_standard="IS 1554 (Part 1) : 1988"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-06")
    override_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.TENDER_SPECIFICATION_OVERRIDE.value
    ]
    assert len(override_findings) == 1
    assert override_findings[0].escalation_action == "NONE"


# 7. Overlapping product standards without statutory priority (Unresolved Precedence)
def test_case_07_unresolved_normative_precedence(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Low voltage distribution panel switchgear apparatus.",
        candidate_standard="IS 13947 (Part 1) : 1993",
        standard_role="PRIMARY_PRODUCT"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Low voltage switchgear apparatus for control circuits.",
        candidate_standard="IS/IEC 60947-1 : 2007",
        standard_role="PRIMARY_PRODUCT"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-07")
    assert result.has_unresolved_precedence is True
    assert result.human_review_required is True
    prec_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.UNRESOLVED_NORMATIVE_PRECEDENCE.value
    ]
    assert len(prec_findings) == 1
    assert prec_findings[0].escalation_action == "HUMAN_REVIEW_REQUIRED"


# 8. Missing or unverified evidence preserves uncertainty
def test_case_08_evidence_insufficiency_preserves_uncertainty(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Specialized high-pressure chemical dosing pump.",
        candidate_standard="IS 1520 : 1980",
        clause_evidence={
            "requirement_evidence_support": RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value
        }
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Centrifugal pump for auxiliary cooling water loop.",
        candidate_standard="IS 6595 : 2002",
        clause_evidence={
            "requirement_evidence_support": RequirementEvidenceSupportState.FULLY_SUPPORTED.value
        }
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-08")
    insufficient_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED.value
    ]
    assert len(insufficient_findings) == 1
    assert insufficient_findings[0].escalation_action == "CLARIFICATION_REQUIRED"


# 9. Integration with TenderAuditEngine preserves safety escalation
def test_case_09_tender_audit_integration_escalation():
    from src.audit import TenderAuditEngine

    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Supply of 100 kVA distribution transformer for unit TR-01.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Rating of transformer TR-01 shall be 200 kVA with copper winding.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )

    audit_engine = TenderAuditEngine(db=None)
    audit_res = audit_engine.audit_tender([r1, r2], tender_id="TENDER-INTEG")

    assert audit_res.has_cross_requirement_contradictions is True
    assert len(audit_res.cross_requirement_conflicts) >= 1
    assert audit_res.publication_readiness == "REVIEW_REQUIRED"
    assert any("contradictions" in r.lower() for r in audit_res.readiness_reasons)


# 10. Anti-Falsification Boundaries: Never fabricate statutory portal authentication or automatic sign-off
def test_case_10_anti_falsification_invariants(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Transformer apparatus TR-01 100 kVA.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Transformer apparatus TR-01 200 kVA.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-AF")
    for f in result.findings:
        # Must not claim official live BIS portal authentication
        assert f.source_provenance in ("VERIFIED", "CURATED", "UNVERIFIED")
        assert f.source_provenance != "BIS_LIVE_STATUTORY_PORTAL"
        # Escalations must require human review, not claim automatic human verification
        if f.conflict_state == CrossRequirementConflictState.CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION.value:
            assert f.escalation_action == "HUMAN_REVIEW_REQUIRED"


# 11. Ambiguous Equipment Identity: Missing tag and no singular demonstrative preserves uncertainty
def test_case_11_ambiguous_equipment_identity_preserves_uncertainty(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Supply 100 kVA distribution transformer.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Supply 250 kVA distribution transformer.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-AMBIG-ID")
    # Must NOT claim a confirmed contradiction because they could be distinct tender items
    assert result.has_confirmed_contradictions is False
    potential_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED.value
    ]
    assert len(potential_findings) == 1
    assert potential_findings[0].escalation_action == "CLARIFICATION_REQUIRED"
    assert "unconfirmed" in potential_findings[0].evidence_text.lower()


# 12. Compatible Inequality Ratings: Minimum floor vs higher rating does NOT contradict
def test_case_12_compatible_inequality_ratings_no_contradiction(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Transformer TR-01 shall have minimum rating of 100 kVA.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Transformer TR-01 rating shall be 150 kVA.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-INEQ")
    # 150 kVA satisfies minimum 100 kVA; must NOT be a contradiction
    assert result.has_confirmed_contradictions is False


# 13. Disjoint Equipment Types: Distinct equipment cannot be co-applicable complementary standards
def test_case_13_disjoint_equipment_not_co_applicable(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Supply of 1.1 kV PVC power cables.",
        candidate_standard="IS 1554 (Part 1) : 1988",
        standard_role="PRIMARY_PRODUCT"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Laying and jointing of concrete pipes.",
        candidate_standard="IS 783 : 1985",
        standard_role="INSTALLATION_CODE"
    )

    result = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-DISJOINT-COAPP")
    coapp_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.CO_APPLICABLE_COMPLEMENTARY_STANDARDS.value
    ]
    # Cable and Concrete pipe must NOT be declared co-applicable complementary standards!
    assert len(coapp_findings) == 0
    disjoint_findings = [
        f for f in result.findings
        if f.conflict_state == CrossRequirementConflictState.NO_CROSS_REQUIREMENT_CONFLICT.value
    ]
    assert len(disjoint_findings) >= 1


# 14. Input Order Invariance / Determinism
def test_case_14_input_order_invariance_determinism(conflict_engine):
    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Transformer TR-01 shall be outdoor pole-mounted type 100 kVA.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Transformer TR-01 shall be indoor dry-type 200 kVA.",
        candidate_standard="IS 11171 : 1985"
    )

    forward = conflict_engine.analyze_tender_requirements([r1, r2], tender_id="TENDER-DET")
    reverse = conflict_engine.analyze_tender_requirements([r2, r1], tender_id="TENDER-DET")

    assert forward.has_confirmed_contradictions == reverse.has_confirmed_contradictions
    assert forward.has_unresolved_precedence == reverse.has_unresolved_precedence
    assert forward.has_edition_divergence == reverse.has_edition_divergence
    assert len(forward.findings) == len(reverse.findings)
    assert forward.summary == reverse.summary


# 15. Report Markdown Rendering & API Summary Propagation
def test_case_15_report_and_api_propagation():
    from src.audit import TenderAuditEngine
    from src.report import ReportGenerator

    r1 = MockRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Supply of 100 kVA distribution transformer for unit TR-01.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )
    r2 = MockRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Rating of transformer TR-01 shall be 200 kVA.",
        candidate_standard="IS 1180 (Part 1) : 2014"
    )

    audit_engine = TenderAuditEngine(db=None)
    audit_res = audit_engine.audit_tender([r1, r2], tender_id="TENDER-REPORT-PROP")

    rep_gen = ReportGenerator()
    rep = rep_gen.generate_report(audit_result=audit_res, requirement_results=[r1, r2])
    md_text = rep.to_markdown()

    assert "Cross-Requirement Conflict & Precedence Findings" in md_text
    assert "TR-01" in md_text
    assert "CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION" in md_text


