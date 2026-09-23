"""
Module: tests/test_tender_audit.py
Purpose: Comprehensive test suite for Phase 4: Tender Audit & Standards Gap Intelligence.

Validates:
1. Fully covered tender (all requirements meet COVERED criteria).
2. Safe abstention (routes to AMBIGUOUS_REQUIREMENT / CLARIFICATION_REQUIRED).
3. Potential coverage gap (technical domain without standard, disclaimers attached).
4. Withdrawn cited standard (flags LIFECYCLE_CONCERN without automated substitution).
5. UNKNOWN lifecycle (honestly preserves UNKNOWN without guessing).
6. Ambiguous requirement (retains missing parameters & clarification question).
7. Multi-standard requirement (composite coverage across distinct standards).
8. Partial component coverage (marks PARTIAL, isolates uncovered component).
9. Traceability of audit findings to Phase 3 structured evidence.
10. Missing evidence handled gracefully without crashing or fabricating.
11. Categorized human review queue generation and sorting.
12. No false conversion of UNKNOWN -> GAP for administrative/non-technical text.
13. No false automated replacement of WITHDRAWN standard without verified relationship.
14. No benchmark-specific hardcoding in audit logic.
15. End-to-end synthetic tender audit verification.
"""

import unittest
import inspect
from typing import List, Dict, Any, Optional

from src.audit import (
    TenderAuditEngine,
    TenderAuditResult,
    CoverageState,
    AuditFindingType,
    ReviewQueueCategory,
    AuditFinding,
    RequirementCoverageItem,
    StructuredTenderAuditReport,
    ReviewQueueItem
)
from src.recommend import (
    RequirementRecommendationResult,
    StandardRecommendation
)


class TestPhase4TenderAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_engine = TenderAuditEngine()

    def _create_mock_result(
        self,
        req_id: str,
        text: str,
        candidate_std: Optional[str] = "IS 15778",
        status: str = "Active",
        version_role: str = "CURRENT_ACTIVE",
        category: str = "PRODUCT",
        decision: str = "RECOMMEND",
        human_review: bool = False,
        evidence_strength: str = "STRONG",
        risk_level: str = "LOW",
        risk_reasons: Optional[List[str]] = None,
        explicit_standards: Optional[List[str]] = None,
        ambiguity_state: str = "CLEAR",
        ambiguity_reason: str = "",
        missing_information: Optional[List[str]] = None,
        suggested_clarification: Optional[str] = None,
        decomposed_components: Optional[List[Dict[str, Any]]] = None,
        structured_evidence: Optional[Dict[str, Any]] = None,
        applicability_decision: str = "APPLICABLE"
    ) -> RequirementRecommendationResult:
        """Helper to create synthetic RequirementRecommendationResult for generic audit testing."""
        rec = None
        recommendations = []
        if candidate_std and candidate_std not in ["INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"]:
            rec = StandardRecommendation(
                standard_number=candidate_std,
                title=f"Specification for {candidate_std}",
                status=status,
                version_role=version_role,
                relevance_score=0.90,
                confidence="High",
                evidence="Verified test evidence",
                provenance="VERIFIED" if evidence_strength == "STRONG" else "CURATED",
                applicability={"decision": applicability_decision, "is_applicable": (applicability_decision == "APPLICABLE")}
            )
            recommendations.append(rec)

        default_struct_ev = {
            "standard_number": candidate_std,
            "official_title": f"Specification for {candidate_std}" if candidate_std else None,
            "evidence_strength": evidence_strength,
            "scope_status": "AUTHORITATIVE_VERIFIED" if evidence_strength == "STRONG" else "CURATED",
            "lifecycle": {
                "status": status.upper() if status in ["Active", "Withdrawn", "Unknown"] else "UNKNOWN",
                "is_active": (status.upper() == "ACTIVE"),
                "is_withdrawn": (status.upper() == "WITHDRAWN"),
                "is_unknown": (status.upper() not in ["ACTIVE", "WITHDRAWN"])
            },
            "relationships": {
                "supersedes": [],
                "superseded_by": [],
                "international_equivalent": [],
                "normative_references": []
            },
            "provenance": {
                "source": "BIS Catalogue",
                "source_type": "OFFICIAL_DATABASE",
                "verification_status": "VERIFIED" if evidence_strength == "STRONG" else "CURATED"
            },
            "applicability": {
                "decision": applicability_decision
            },
            "explanation": {
                "why_selected": "Grounded match",
                "supporting_facts": ["Technical parameters match scope"],
                "human_review_required": human_review
            },
            "uncertainty_and_gaps": {}
        }

        return RequirementRecommendationResult(
            requirement_id=req_id,
            requirement_text=text,
            category=category,
            explicit_standards_found=explicit_standards or [],
            candidate_standard=candidate_std,
            title=f"Specification for {candidate_std}" if candidate_std else "No Standard",
            status=status,
            version_role=version_role,
            relevance_score=0.90 if candidate_std else 0.0,
            confidence="High" if candidate_std else "Low",
            evidence="Verified test evidence" if candidate_std else "No evidence",
            provenance="VERIFIED" if evidence_strength == "STRONG" else "CURATED",
            human_review_required=human_review,
            reason="Applicable" if candidate_std else "No match",
            recommendations=recommendations,
            decomposed_components=decomposed_components or [],
            critic_result={
                "decision": decision,
                "risk_level": risk_level,
                "evidence": {"evidence_strength": evidence_strength, "grounded": True}
            },
            risk_level=risk_level,
            risk_reasons=risk_reasons or [],
            applicability={"decision": applicability_decision, "is_applicable": (applicability_decision == "APPLICABLE")},
            ambiguity_state=ambiguity_state,
            ambiguity_reason=ambiguity_reason,
            missing_information=missing_information or [],
            suggested_clarification_question=suggested_clarification,
            structured_evidence=structured_evidence or default_struct_ev
        )

    # -----------------------------------------------------------------------
    # 1. Fully Covered Tender
    # -----------------------------------------------------------------------
    def test_01_fully_covered_tender(self):
        """Tender with fully covered requirements produces COVERED states and zero gaps."""
        r1 = self._create_mock_result("REQ-1", "Supply of CPVC pipes for domestic water", "IS 15778")
        r2 = self._create_mock_result("REQ-2", "Supply of centrifugal water pumps", "IS 1520")

        audit = self.audit_engine.audit_tender([r1, r2])

        self.assertEqual(audit.requirements_analyzed, 2)
        self.assertEqual(audit.supported_standards_count, 2)
        self.assertEqual(audit.potential_gap_count, 0)
        self.assertEqual(audit.coverage_distribution[CoverageState.COVERED], 2)
        self.assertEqual(audit.publication_readiness, "READY_FOR_REVIEW")

        cov_states = [item["coverage_state"] for item in audit.coverage_matrix]
        self.assertEqual(cov_states, [CoverageState.COVERED, CoverageState.COVERED])

    # -----------------------------------------------------------------------
    # 2. Tender with Safe Abstention
    # -----------------------------------------------------------------------
    def test_02_tender_with_safe_abstention(self):
        """Safe abstentions are tracked and routed to review without converting to fake gaps."""
        r_clean = self._create_mock_result("REQ-1", "Supply of CPVC pipes", "IS 15778")
        r_abstain = self._create_mock_result(
            "REQ-2",
            "Laying of pipeline without technical specifications",
            candidate_std=None,
            decision="INSUFFICIENT_EVIDENCE",
            human_review=True,
            ambiguity_state="SAFE_ABSTENTION_GENUINE_AMBIGUITY",
            ambiguity_reason="Underspecified pipeline type and material",
            missing_information=["pipe material", "pressure class"]
        )

        audit = self.audit_engine.audit_tender([r_clean, r_abstain])

        self.assertEqual(audit.safe_abstention_count, 1)
        self.assertEqual(audit.coverage_distribution[CoverageState.COVERED], 1)
        self.assertEqual(audit.coverage_distribution[CoverageState.REVIEW_REQUIRED], 1)
        # Safe abstention with missing information must NOT be classified as POTENTIAL_GAP
        self.assertEqual(audit.potential_gap_count, 0)
        self.assertTrue(any(f["finding_type"] in [AuditFindingType.AMBIGUOUS_REQUIREMENT, AuditFindingType.CLARIFICATION_REQUIRED] for f in audit.audit_findings))

    # -----------------------------------------------------------------------
    # 3. Tender with Potential Coverage Gap
    # -----------------------------------------------------------------------
    def test_03_tender_with_potential_coverage_gap(self):
        """Technical procurement specification without standards coverage becomes POTENTIAL_GAP with disclaimers."""
        r_gap = self._create_mock_result(
            "REQ-GAP",
            "Supply of specialized cryogenic fluid propellant containment vessel",
            candidate_std=None,
            decision="INSUFFICIENT_EVIDENCE",
            human_review=True,
            evidence_strength="NONE",
            applicability_decision="INCOMPATIBLE"
        )

        audit = self.audit_engine.audit_tender([r_gap])

        self.assertEqual(audit.potential_gap_count, 1)
        self.assertEqual(audit.coverage_distribution[CoverageState.POTENTIAL_GAP], 1)

        # Verify gap finding attributes and mandatory disclaimer
        gap_finding = audit.gap_findings[0]
        self.assertEqual(gap_finding["finding_type"], AuditFindingType.POTENTIAL_STANDARD_GAP)
        self.assertIn("does NOT indicate that no Indian Standard exists", gap_finding["uncertainty"])
        self.assertTrue(gap_finding["human_review_required"])

    # -----------------------------------------------------------------------
    # 4. Tender with Withdrawn Cited Standard
    # -----------------------------------------------------------------------
    def test_04_tender_with_withdrawn_cited_standard(self):
        """Tender citing a withdrawn standard produces LIFECYCLE_CONCERN without automated substitution."""
        r_withdrawn = self._create_mock_result(
            "REQ-WITHDRAWN",
            "Supply of pumps conforming to IS 8034 : 2002",
            candidate_std="IS 8034 : 2002",
            status="Withdrawn",
            human_review=True,
            explicit_standards=["IS 8034 : 2002"],
            risk_reasons=["Standard is marked WITHDRAWN in official catalogue"]
        )

        audit = self.audit_engine.audit_tender([r_withdrawn])

        self.assertEqual(audit.lifecycle_concern_count, 1)
        life_finding = audit.lifecycle_findings[0]
        self.assertEqual(life_finding["finding_type"], AuditFindingType.LIFECYCLE_CONCERN)
        self.assertEqual(life_finding["lifecycle_status"], "WITHDRAWN")
        # Must not automatically replace without authoritative relationship
        self.assertIn("Do NOT automatically substitute", life_finding["lifecycle_note"])

    # -----------------------------------------------------------------------
    # 5. Tender with UNKNOWN Lifecycle
    # -----------------------------------------------------------------------
    def test_05_tender_with_unknown_lifecycle(self):
        """Unknown lifecycle status is preserved honestly and not converted to active or withdrawn."""
        r_unknown_life = self._create_mock_result(
            "REQ-UNK",
            "Supply of specialty valves",
            candidate_std="IS 99999",
            status="Unknown",
            version_role="REFERENCE_ONLY",
            human_review=True
        )

        audit = self.audit_engine.audit_tender([r_unknown_life])

        self.assertEqual(audit.unknown_lifecycle_count, 1)
        self.assertEqual(audit.lifecycle_distribution["Unknown"], 1)

    # -----------------------------------------------------------------------
    # 6. Tender with Ambiguous Requirement
    # -----------------------------------------------------------------------
    def test_06_tender_with_ambiguous_requirement(self):
        """Ambiguous requirement aggregates into ambiguity findings and retains clarification question."""
        r_amb = self._create_mock_result(
            "REQ-AMB",
            "Supply of fire extinguishers for building safety",
            candidate_std="IS 15683",
            human_review=True,
            ambiguity_state="AMBIGUOUS_PARAMETER_GAP",
            ambiguity_reason="Missing extinguishing medium (CO2, Dry Powder, Water) and capacity rating",
            missing_information=["extinguishing medium", "capacity"],
            suggested_clarification="Please specify the extinguishing medium (CO2, Dry Powder, Foam) and required capacity."
        )

        audit = self.audit_engine.audit_tender([r_amb])

        self.assertEqual(audit.clarification_required_count, 1)
        self.assertEqual(len(audit.ambiguity_findings), 1)
        amb_f = audit.ambiguity_findings[0]
        self.assertEqual(amb_f["finding_type"], AuditFindingType.CLARIFICATION_REQUIRED)
        self.assertIn("extinguishing medium", amb_f["review_action"])

    # -----------------------------------------------------------------------
    # 7. Tender with Multi-Standard Requirement
    # -----------------------------------------------------------------------
    def test_07_tender_with_multi_standard_requirement(self):
        """Composite requirement across multiple standards is recognized and aggregated."""
        decomposed = [
            {"component_id": "C1", "component_text": "Submersible pump unit", "assigned_standard": "IS 8034 : 2018"},
            {"component_id": "C2", "component_text": "Submersible induction motor", "assigned_standard": "IS 9283 : 2024"}
        ]
        r_multi = self._create_mock_result(
            "REQ-MULTI",
            "Supply of submersible pump set with electric motor",
            candidate_std="IS 8034 : 2018",
            category="COMPOSITE",
            decomposed_components=decomposed
        )

        audit = self.audit_engine.audit_tender([r_multi])

        self.assertEqual(audit.multi_standard_count, 1)
        self.assertEqual(len(audit.multi_standard_items), 1)
        item = audit.multi_standard_items[0]
        self.assertEqual(len(item["component_breakdown"]), 2)
        self.assertEqual(item["coverage_state"], CoverageState.COVERED)

    # -----------------------------------------------------------------------
    # 8. Tender with Partial Component Coverage
    # -----------------------------------------------------------------------
    def test_08_tender_with_partial_component_coverage(self):
        """When some components have standards and others do not, requirement state is PARTIAL."""
        decomposed = [
            {"component_id": "C1", "component_text": "CPVC pipes for plumbing", "assigned_standard": "IS 15778"},
            {"component_id": "C2", "component_text": "Specialty imported solvent adhesive", "assigned_standard": None}
        ]
        r_part = self._create_mock_result(
            "REQ-PART",
            "Supply of CPVC pipes and specialty imported solvent adhesive",
            candidate_std="IS 15778",
            category="COMPOSITE",
            decomposed_components=decomposed
        )

        audit = self.audit_engine.audit_tender([r_part])

        self.assertEqual(audit.coverage_distribution[CoverageState.PARTIAL], 1)
        item = audit.coverage_matrix[0]
        self.assertEqual(item["coverage_state"], CoverageState.PARTIAL)
        self.assertTrue(any(f["finding_type"] == AuditFindingType.PARTIAL_STANDARD_COVERAGE for f in audit.audit_findings))

    # -----------------------------------------------------------------------
    # 9. Evidence Traceability
    # -----------------------------------------------------------------------
    def test_09_evidence_traceability(self):
        """Every audit finding traces to Phase 3 structured evidence fields."""
        struct_ev = {
            "standard_number": "IS 15778 : 2007",
            "evidence_strength": "STRONG",
            "scope_status": "AUTHORITATIVE_VERIFIED",
            "provenance": {
                "source": "BIS Production DB",
                "verification_status": "VERIFIED",
                "raw_record_ref": "RECORD-001"
            }
        }
        r = self._create_mock_result("REQ-TRACE", "CPVC pipes", "IS 15778", structured_evidence=struct_ev)

        audit = self.audit_engine.audit_tender([r])

        finding = audit.audit_findings[0]
        self.assertEqual(finding["evidence_strength"], "STRONG")
        self.assertEqual(finding["provenance"]["source"], "BIS Production DB")
        self.assertEqual(finding["provenance"]["verification_status"], "VERIFIED")

    # -----------------------------------------------------------------------
    # 10. Missing Evidence Handled Gracefully
    # -----------------------------------------------------------------------
    def test_10_missing_evidence_handled_gracefully(self):
        """Results missing structured_evidence dictionary fallback safely without errors."""
        r = self._create_mock_result("REQ-NO-EV", "Uncertain product", candidate_std="IS 999", structured_evidence={})

        audit = self.audit_engine.audit_tender([r])

        self.assertEqual(audit.requirements_analyzed, 1)
        self.assertIsNotNone(audit.audit_summary)
        self.assertIsNotNone(audit.structured_audit_report)

    # -----------------------------------------------------------------------
    # 11. Categorized Human Review Queue
    # -----------------------------------------------------------------------
    def test_11_human_review_queue_categories_and_sorting(self):
        """Review queue properly assigns categories and sorts by priority."""
        r_crit = self._create_mock_result("REQ-CRIT", "High voltage switchgear", "IS 123", risk_level="CRITICAL", human_review=True)
        r_life = self._create_mock_result("REQ-LIFE", "Withdrawn pipe", "IS 456", status="Withdrawn", human_review=True)
        r_gap = self._create_mock_result("REQ-GAP", "Cryo unit", candidate_std=None, human_review=True)
        r_clean = self._create_mock_result("REQ-CLEAN", "Standard pipe", "IS 15778", human_review=False)

        audit = self.audit_engine.audit_tender([r_clean, r_life, r_gap, r_crit])

        # Clean item is excluded from review queue
        queue_ids = [item.requirement_id for item in audit.review_queue]
        self.assertNotIn("REQ-CLEAN", queue_ids)

        # Critical item is first in review queue
        self.assertEqual(audit.review_queue[0].requirement_id, "REQ-CRIT")
        self.assertEqual(audit.review_queue[0].category, ReviewQueueCategory.HIGH_PRIORITY_REVIEW)

        # Check queue categories are populated
        categories = {item.category for item in audit.review_queue}
        self.assertIn(ReviewQueueCategory.HIGH_PRIORITY_REVIEW, categories)

    # -----------------------------------------------------------------------
    # 12. UNKNOWN Must Not Become GAP
    # -----------------------------------------------------------------------
    def test_12_unknown_does_not_become_gap(self):
        """Administrative clauses must be classified as UNKNOWN and never converted to POTENTIAL_GAP."""
        admin_reqs = [
            self._create_mock_result("REQ-ADM1", "Earnest money deposit (EMD) of Rs. 50,000 to be submitted.", candidate_std=None, category="ADMINISTRATIVE"),
            self._create_mock_result("REQ-ADM2", "Bid submission deadline is 25th October 2026, 15:00 hrs IST.", candidate_std=None, category="SUBMISSION"),
            self._create_mock_result("REQ-ADM3", "Payment terms: 90% against delivery and 10% after commissioning.", candidate_std=None, category="COMMERCIAL")
        ]

        audit = self.audit_engine.audit_tender(admin_reqs)

        self.assertEqual(audit.potential_gap_count, 0, "Administrative clauses must NEVER be flagged as standards gaps.")
        self.assertEqual(audit.coverage_distribution[CoverageState.UNKNOWN], 3)
        for item in audit.coverage_matrix:
            self.assertEqual(item["coverage_state"], CoverageState.UNKNOWN)

    # -----------------------------------------------------------------------
    # 13. Withdrawn Must Not Automatically Become Replacement
    # -----------------------------------------------------------------------
    def test_13_withdrawn_must_not_auto_replace(self):
        """Withdrawn standard without verified relationship does NOT get automatically replaced."""
        r = self._create_mock_result(
            "REQ-WITHDRAWN-NO-REP",
            "Tender requirement citing old IS 1234 : 1980",
            candidate_std="IS 1234 : 1980",
            status="Withdrawn",
            human_review=True,
            explicit_standards=["IS 1234 : 1980"]
        )

        audit = self.audit_engine.audit_tender([r])

        finding = audit.lifecycle_findings[0]
        self.assertIn("Do NOT automatically substitute", finding["lifecycle_note"])

    # -----------------------------------------------------------------------
    # 14. No Benchmark-Specific Hardcoding
    # -----------------------------------------------------------------------
    def test_14_no_benchmark_specific_hardcoding(self):
        """Verify that audit engine methods do not hardcode benchmark standard numbers."""
        src = inspect.getsource(self.audit_engine.audit_tender)
        src += inspect.getsource(self.audit_engine._evaluate_requirement_coverage)
        src += inspect.getsource(self.audit_engine._is_potential_gap)
        src += inspect.getsource(self.audit_engine._check_lifecycle_concern)

        forbidden = ["10611", "15778", "10434", "778", "458", "15000", "2491", "8034", "9283", "4984"]
        for num in forbidden:
            self.assertNotIn(num, src, f"Audit engine logic must not hardcode standard number '{num}'.")

    # -----------------------------------------------------------------------
    # 15. End-to-End Synthetic Tender Audit
    # -----------------------------------------------------------------------
    def test_15_end_to_end_synthetic_tender_report(self):
        """Complete synthetic tender generates full StructuredTenderAuditReport model."""
        r1 = self._create_mock_result("REQ-1", "Supply of CPVC pipes", "IS 15778")
        r2 = self._create_mock_result("REQ-2", "Supply of pumpsets with motor", "IS 8034", category="COMPOSITE", decomposed_components=[
            {"component_id": "C1", "component_text": "Pump", "assigned_standard": "IS 8034"},
            {"component_id": "C2", "component_text": "Motor", "assigned_standard": "IS 9283"}
        ])
        r3 = self._create_mock_result("REQ-3", "Underspecified fire equipment", candidate_std=None, ambiguity_state="AMBIGUOUS", missing_information=["type"], human_review=True)
        r4 = self._create_mock_result("REQ-4", "Pipes per withdrawn IS 4984 : 1995", candidate_std="IS 4984 : 1995", status="Withdrawn", explicit_standards=["IS 4984 : 1995"], human_review=True)
        r5 = self._create_mock_result("REQ-5", "Specialized custom alloy", candidate_std=None, human_review=True, applicability_decision="INCOMPATIBLE")

        report = self.audit_engine.generate_audit_report([r1, r2, r3, r4, r5], tender_id="SYNTH-TENDER-01")

        self.assertIsInstance(report, StructuredTenderAuditReport)
        self.assertEqual(report.tender_id, "SYNTH-TENDER-01")
        self.assertEqual(report.summary.requirements_analyzed, 5)
        self.assertEqual(report.summary.supported_standards_count, 2)  # r1 and r2
        self.assertEqual(report.summary.clarification_required_count, 1)  # r3
        self.assertEqual(report.summary.lifecycle_concern_count, 1)  # r4
        self.assertEqual(report.summary.potential_gap_count, 1)  # r5
        self.assertEqual(len(report.coverage_matrix), 5)
        self.assertGreater(len(report.disclaimers_and_notes), 0)


if __name__ == "__main__":
    unittest.main()
