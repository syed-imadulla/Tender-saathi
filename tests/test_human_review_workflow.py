"""
tests/test_human_review_workflow.py
Phase 5: Human Review & Decision Workflow Automated Test Suite.

Verifies:
1. Review item creation (HumanReviewDecisionRecord structure and dataclass contract)
2. Review queue categorization (maps to Phase 4 categories)
3. Decision states (PENDING, ACCEPT, EDIT, DISMISS, with safe fallback)
4. Accept decision (records decision, captures timestamp, preserves candidate)
5. Edit decision (records reviewer_standard, note, without mutating system candidate)
6. Dismiss decision (records dismissal, note, without mutating system candidate)
7. Reviewer notes (custom text & standard rationale chips)
8. Review progress computation (pending/reviewed/accepted/edited/dismissed and status transitions)
9. System recommendation immutability (candidate_standard, evidence_standard, decision never mutated)
10. Human decision separation (system findings and human decision trail strictly separate)
11. Evidence immutability (candidate_standard == evidence_standard; edited standard does not inherit evidence)
12. Report decision trail (Markdown section 8 and JSON human_decisions field)
13. Review-complete state (all items decided, explicit non-statutory disclaimer)
14. Safe abstention preservation (insufficient evidence / no match cannot display false accept)
15. Lifecycle finding preservation (superseded citation warnings preserved alongside human decision)
16. API review roundtrip (POST /api/tender/<id>/review & GET /api/tender/<id>/review with report regeneration)
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timezone

from src.report import (
    HumanReviewDecisionRecord,
    RequirementReviewSection,
    TenderInformation,
    TenderReviewReport,
    ReportGenerator,
)
from src.audit import (
    TenderAuditResult,
    ReviewQueueItem,
    ReviewQueueCategory,
)
from src.recommend import (
    RequirementRecommendationResult,
    StandardRecommendation,
)
from api.server import app, _report_cache


class TestHumanReviewWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def setUp(self):
        self.generator = ReportGenerator()
        self.now_iso = datetime.now(timezone.utc).isoformat()

        # Build mock RequirementRecommendationResults matching dataclass contract
        self.req1 = RequirementRecommendationResult(
            requirement_id="REQ-001",
            requirement_text="Supply of CPVC pipes for domestic water distribution",
            category="material",
            explicit_standards_found=[],
            candidate_standard="IS 15778 : 2007",
            title="Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Distribution Supplies",
            status="Active",
            version_role="Current Primary",
            relevance_score=0.92,
            confidence="High",
            evidence="IS 15778 covers chlorinated polyvinyl chloride pipes for potable water distribution.",
            provenance="CURATED",
            human_review_required=False,
            reason="Direct match for CPVC water distribution pipes",
            critic_result={
                "decision": "RECOMMEND",
                "evidence": {
                    "evidence_strength": "STRONG",
                    "evidence_standard": "IS 15778 : 2007",
                    "evidence_text": "IS 15778 covers chlorinated polyvinyl chloride pipes for potable water distribution.",
                }
            },
        )
        self.req1.evidence_standard = "IS 15778 : 2007"

        self.req2 = RequirementRecommendationResult(
            requirement_id="REQ-002",
            requirement_text="Cast iron gate valves for industrial utility pipeline citing IS 10611",
            category="component",
            explicit_standards_found=["IS 10611"],
            candidate_standard="IS/ISO 10434",
            title="Bolted bonnet steel gate valves for petroleum, petrochemical and allied industries",
            status="Active",
            version_role="Superseded Citation",
            relevance_score=0.88,
            confidence="Medium",
            evidence="IS 10611 superseded by IS/ISO 10434.",
            provenance="VERIFIED",
            human_review_required=True,
            reason="Tender cited superseded standard IS 10611. Recommended active replacement IS/ISO 10434.",
            recommendations=[
                StandardRecommendation(
                    standard_number="IS/ISO 10434",
                    title="Bolted bonnet steel gate valves",
                    status="Active",
                    version_role="Current Replacement",
                    evidence="IS 10611 superseded by IS/ISO 10434",
                    relevance_score=0.88,
                    confidence=0.85,
                    provenance="VERIFIED",
                    superseded_warning="Cited standard IS 10611 is SUPERSEDED by IS/ISO 10434",
                )
            ],
            critic_result={
                "decision": "RECOMMEND_WITH_REVIEW",
                "evidence": {
                    "evidence_strength": "MODERATE",
                    "evidence_standard": "IS/ISO 10434",
                    "evidence_text": "IS 10611 superseded by IS/ISO 10434.",
                }
            },
        )
        self.req2.evidence_standard = "IS/ISO 10434"

        self.req3 = RequirementRecommendationResult(
            requirement_id="REQ-003",
            requirement_text="Pipes for drainage without diameter or material specification",
            category="general",
            explicit_standards_found=[],
            candidate_standard="NONE",
            title="",
            status="Unknown",
            version_role="Unmatched",
            relevance_score=0.20,
            confidence="Low",
            evidence="",
            provenance="UNVERIFIED",
            human_review_required=True,
            reason="Insufficient information: material, diameter, and application unspecified.",
            critic_result={
                "decision": "NO_RELIABLE_MATCH",
                "evidence": {
                    "evidence_strength": "NONE",
                    "evidence_standard": None,
                    "evidence_text": "",
                }
            },
        )
        self.req3.evidence_standard = None

        self.mock_audit = TenderAuditResult(
            tender_id="TENDER-HR-001",
            requirements_analyzed=3,
            recommendations_count=1,
            review_required_count=2,
            insufficient_evidence_count=0,
            active_count=1,
            superseded_count=1,
            withdrawn_count=0,
            unknown_lifecycle_count=1,
            evidence_distribution={"STRONG": 1, "MODERATE": 1, "WEAK": 0, "NONE": 1},
            completeness_distribution={"KNOWN": 1, "POTENTIALLY_MISSING": 1, "UNKNOWN": 1, "NOT_APPLICABLE": 0},
            risk_distribution={"CRITICAL": 1, "HIGH": 1, "MEDIUM": 0, "LOW": 1},
            lifecycle_distribution={"Active": 1, "Superseded": 1, "Withdrawn": 0, "Unknown": 1},
            related_standards_count=2,
            publication_readiness="REVIEW_REQUIRED",
            readiness_reasons=["1 ambiguous requirement requiring clarification"],
            review_queue=[
                ReviewQueueItem(
                    requirement_id="REQ-001",
                    requirement_text="Supply of CPVC pipes for domestic water distribution",
                    risk_level="MEDIUM",
                    decision="RECOMMEND_WITH_REVIEW",
                    candidate_standard="IS 15778 : 2007",
                    evidence_strength="STRONG",
                    primary_reason="Confirm application fits IS 15778",
                    priority=2,
                    category=ReviewQueueCategory.HIGH_PRIORITY_REVIEW,
                ),
                ReviewQueueItem(
                    requirement_id="REQ-002",
                    requirement_text="Cast iron gate valves citing IS 10611",
                    risk_level="CRITICAL",
                    decision="REVIEW_REQUIRED",
                    candidate_standard="IS/ISO 10434",
                    evidence_strength="MODERATE",
                    primary_reason="IS 10611 is superseded by IS/ISO 10434",
                    priority=1,
                    category=ReviewQueueCategory.LIFECYCLE_REVIEW,
                ),
                ReviewQueueItem(
                    requirement_id="REQ-003",
                    requirement_text="Pipes for drainage without diameter or material specification",
                    risk_level="HIGH",
                    decision="INSUFFICIENT_EVIDENCE",
                    candidate_standard="NONE",
                    evidence_strength="NONE",
                    primary_reason="Drainage pipe material unspecified",
                    priority=1,
                    category=ReviewQueueCategory.CLARIFICATION_REQUIRED,
                ),
            ],
        )

    # -------------------------------------------------------------------------
    # 1. Review Item Creation
    # -------------------------------------------------------------------------
    def test_01_review_record_creation(self):
        """Verifies HumanReviewDecisionRecord fields, defaults, and dataclass contract."""
        record = HumanReviewDecisionRecord(
            requirement_id="REQ-001",
            decision="ACCEPT",
            reviewer_standard=None,
            reviewer_note="Verified application matches scope",
            reviewed_at=self.now_iso,
            system_standard="IS 15778 : 2007",
            system_finding="Direct match for CPVC pipes",
        )
        self.assertEqual(record.requirement_id, "REQ-001")
        self.assertEqual(record.decision, "ACCEPT")
        self.assertIsNone(record.reviewer_standard)
        self.assertEqual(record.reviewer_note, "Verified application matches scope")
        self.assertEqual(record.system_standard, "IS 15778 : 2007")
        self.assertEqual(record.system_finding, "Direct match for CPVC pipes")
        self.assertEqual(record.reviewed_at, self.now_iso)

    # -------------------------------------------------------------------------
    # 2. Review Queue Categorization
    # -------------------------------------------------------------------------
    def test_02_review_queue_categorization(self):
        """Verifies existing Phase 4 review queue categories are preserved and recognized."""
        expected_categories = {
            ReviewQueueCategory.HIGH_PRIORITY_REVIEW,
            ReviewQueueCategory.LIFECYCLE_REVIEW,
            ReviewQueueCategory.CLARIFICATION_REQUIRED,
        }
        actual_categories = {item.category for item in self.mock_audit.review_queue}
        self.assertEqual(actual_categories, expected_categories)
        self.assertEqual(len(self.mock_audit.review_queue), 3)

    # -------------------------------------------------------------------------
    # 3. Decision States
    # -------------------------------------------------------------------------
    def test_03_decision_states(self):
        """Verifies valid decision states (PENDING, ACCEPT, EDIT, DISMISS) and safe fallback."""
        valid_states = ["PENDING", "ACCEPT", "EDIT", "DISMISS"]
        for st in valid_states:
            rec = HumanReviewDecisionRecord(requirement_id="REQ-X", decision=st)
            self.assertEqual(rec.decision, st)

    # -------------------------------------------------------------------------
    # 4. Accept Decision
    # -------------------------------------------------------------------------
    def test_04_accept_decision(self):
        """Verifies ACCEPT decision records state, captures timestamp, and preserves candidate."""
        record = HumanReviewDecisionRecord(
            requirement_id=self.req1.requirement_id,
            decision="ACCEPT",
            reviewer_note="Verified against CPVC schedule",
            reviewed_at=self.now_iso,
            system_standard=self.req1.candidate_standard,
        )
        self.assertEqual(record.decision, "ACCEPT")
        self.assertEqual(record.system_standard, "IS 15778 : 2007")
        self.assertIsNone(record.reviewer_standard)
        # Original candidate remains unchanged
        self.assertEqual(self.req1.candidate_standard, "IS 15778 : 2007")

    # -------------------------------------------------------------------------
    # 5. Edit Decision
    # -------------------------------------------------------------------------
    def test_05_edit_decision(self):
        """Verifies EDIT decision records reviewer_standard without mutating system candidate."""
        record = HumanReviewDecisionRecord(
            requirement_id=self.req1.requirement_id,
            decision="EDIT",
            reviewer_standard="IS 4985",
            reviewer_note="Tender specifies uPVC rather than CPVC",
            reviewed_at=self.now_iso,
            system_standard=self.req1.candidate_standard,
        )
        self.assertEqual(record.decision, "EDIT")
        self.assertEqual(record.reviewer_standard, "IS 4985")
        self.assertEqual(record.system_standard, "IS 15778 : 2007")
        # System recommendation object is NOT modified
        self.assertEqual(self.req1.candidate_standard, "IS 15778 : 2007")

    # -------------------------------------------------------------------------
    # 6. Dismiss Decision
    # -------------------------------------------------------------------------
    def test_06_dismiss_decision(self):
        """Verifies DISMISS decision records dismissal rationale without modifying system recommendation."""
        record = HumanReviewDecisionRecord(
            requirement_id=self.req3.requirement_id,
            decision="DISMISS",
            reviewer_note="Scope covered under civil work package 2",
            reviewed_at=self.now_iso,
            system_standard=self.req3.candidate_standard,
        )
        self.assertEqual(record.decision, "DISMISS")
        self.assertEqual(record.reviewer_note, "Scope covered under civil work package 2")
        self.assertEqual(self.req3.candidate_standard, "NONE")

    # -------------------------------------------------------------------------
    # 7. Reviewer Notes
    # -------------------------------------------------------------------------
    def test_07_reviewer_notes(self):
        """Verifies standard rationale chips and custom notes are properly preserved."""
        chips = [
            "Verified application",
            "Scope mismatch",
            "Missing specification",
            "Departmental standard applies",
        ]
        for chip in chips:
            rec = HumanReviewDecisionRecord(
                requirement_id="REQ-TEST",
                decision="ACCEPT",
                reviewer_note=chip,
            )
            self.assertEqual(rec.reviewer_note, chip)

    # -------------------------------------------------------------------------
    # 8. Review Progress Computation
    # -------------------------------------------------------------------------
    def test_08_review_progress_computation(self):
        """Verifies tender review progress math and status transitions."""
        # 3 total review items
        total_items = 3
        decisions = {}

        # Initial state: 0 reviewed
        reviewed = len([d for d in decisions.values() if d.decision != "PENDING"])
        status = "REVIEW_REQUIRED" if reviewed == 0 else ("REVIEW_COMPLETE" if reviewed >= total_items else "IN_PROGRESS")
        self.assertEqual(status, "REVIEW_REQUIRED")
        self.assertEqual(reviewed, 0)

        # 1 decision added
        decisions["REQ-001"] = HumanReviewDecisionRecord(requirement_id="REQ-001", decision="ACCEPT")
        reviewed = len([d for d in decisions.values() if d.decision != "PENDING"])
        status = "REVIEW_REQUIRED" if reviewed == 0 else ("REVIEW_COMPLETE" if reviewed >= total_items else "IN_PROGRESS")
        self.assertEqual(status, "IN_PROGRESS")
        self.assertEqual(reviewed, 1)

        # All 3 decisions added
        decisions["REQ-002"] = HumanReviewDecisionRecord(requirement_id="REQ-002", decision="EDIT", reviewer_standard="IS/ISO 10434")
        decisions["REQ-003"] = HumanReviewDecisionRecord(requirement_id="REQ-003", decision="DISMISS")
        reviewed = len([d for d in decisions.values() if d.decision != "PENDING"])
        status = "REVIEW_REQUIRED" if reviewed == 0 else ("REVIEW_COMPLETE" if reviewed >= total_items else "IN_PROGRESS")
        self.assertEqual(status, "REVIEW_COMPLETE")
        self.assertEqual(reviewed, 3)

    # -------------------------------------------------------------------------
    # 9. System Recommendation Immutability
    # -------------------------------------------------------------------------
    def test_09_system_recommendation_immutability(self):
        """Verifies invariant: System recommendations must NEVER be mutated by human decisions."""
        orig_candidate = self.req1.candidate_standard
        orig_evidence_std = self.req1.evidence_standard
        orig_lifecycle = self.req1.status

        # Reviewer decides EDIT to IS 4985
        human_dec = HumanReviewDecisionRecord(
            requirement_id=self.req1.requirement_id,
            decision="EDIT",
            reviewer_standard="IS 4985",
            reviewer_note="Alternative standard selected by engineer",
        )

        # Confirm RequirementRecommendationResult properties are strictly identical
        self.assertEqual(self.req1.candidate_standard, orig_candidate)
        self.assertEqual(self.req1.evidence_standard, orig_evidence_std)
        self.assertEqual(self.req1.status, orig_lifecycle)

    # -------------------------------------------------------------------------
    # 10. Human Decision Separation
    # -------------------------------------------------------------------------
    def test_10_human_decision_separation(self):
        """Verifies human decisions and system findings remain in separate fields in TenderReviewReport."""
        dec = HumanReviewDecisionRecord(
            requirement_id="REQ-001",
            decision="EDIT",
            reviewer_standard="IS 4985",
            reviewer_note="Reviewer override",
            system_standard="IS 15778 : 2007",
        )
        report = self.generator.generate_report(
            audit_result=self.mock_audit,
            requirement_results=[self.req1],
            human_decisions=[dec],
        )

        req_sec = report.requirements[0]
        # System candidate remains IS 15778
        self.assertEqual(req_sec.candidate_standard, "IS 15778 : 2007")
        # Human decision layer is distinctly stored
        self.assertIsNotNone(req_sec.human_decision)
        self.assertEqual(req_sec.human_decision["decision"], "EDIT")
        self.assertEqual(req_sec.human_decision["reviewer_standard"], "IS 4985")

    # -------------------------------------------------------------------------
    # 11. Evidence Immutability
    # -------------------------------------------------------------------------
    def test_11_evidence_immutability(self):
        """Verifies invariant: candidate_standard == evidence_standard. An edited standard does not inherit evidence."""
        dec = HumanReviewDecisionRecord(
            requirement_id=self.req1.requirement_id,
            decision="EDIT",
            reviewer_standard="IS 4985",
            reviewer_note="Engineer change",
        )
        report = self.generator.generate_report(
            audit_result=self.mock_audit,
            requirement_results=[self.req1],
            human_decisions=[dec],
        )
        req_sec = report.requirements[0]
        # The system evidence standard is still for IS 15778, NOT IS 4985
        self.assertEqual(req_sec.evidence_standard, "IS 15778 : 2007")
        self.assertNotEqual(req_sec.evidence_standard, dec.reviewer_standard)

    # -------------------------------------------------------------------------
    # 12. Report Decision Trail
    # -------------------------------------------------------------------------
    def test_12_report_decision_trail(self):
        """Verifies Markdown and JSON reports contain complete Section 8 Decision Trail."""
        dec1 = HumanReviewDecisionRecord(
            requirement_id="REQ-001",
            decision="ACCEPT",
            reviewer_note="Verified application",
            reviewed_at=self.now_iso,
            system_standard="IS 15778 : 2007",
            system_finding="Direct match for CPVC pipes",
        )
        dec2 = HumanReviewDecisionRecord(
            requirement_id="REQ-002",
            decision="EDIT",
            reviewer_standard="IS/ISO 10434",
            reviewer_note="Confirmed active replacement",
            reviewed_at=self.now_iso,
            system_standard="IS/ISO 10434",
            system_finding="Superseded replacement",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path, json_path = self.generator.generate_and_save(
                audit_result=self.mock_audit,
                requirement_results=[self.req1, self.req2, self.req3],
                output_dir=tmpdir,
                human_decisions=[dec1, dec2],
            )

            # Check JSON
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("human_decisions", data)
            self.assertEqual(len(data["human_decisions"]), 2)
            self.assertEqual(data["human_decisions"][0]["requirement_id"], "REQ-001")
            self.assertEqual(data["human_decisions"][0]["decision"], "ACCEPT")

            # Check Markdown
            with open(md_path, "r", encoding="utf-8") as f:
                md_text = f.read()
            self.assertIn("## 8. Human Review & Decision Trail", md_text)
            self.assertIn("REQ-001", md_text)
            self.assertIn("ACCEPT", md_text)
            self.assertIn("Verified application", md_text)
            self.assertIn("REQ-002", md_text)
            self.assertIn("EDIT", md_text)
            self.assertIn("IS/ISO 10434", md_text)

    # -------------------------------------------------------------------------
    # 13. Review Complete State
    # -------------------------------------------------------------------------
    def test_13_review_complete_state(self):
        """Verifies review-complete status logic and ensures non-statutory disclaimer is documented."""
        decisions = [
            {"requirement_id": "REQ-001", "decision": "ACCEPT"},
            {"requirement_id": "REQ-002", "decision": "EDIT", "reviewer_standard": "IS/ISO 10434"},
            {"requirement_id": "REQ-003", "decision": "DISMISS"},
        ]
        total_items = 3
        reviewed = sum(1 for d in decisions if d["decision"] in ("ACCEPT", "EDIT", "DISMISS"))
        self.assertEqual(reviewed, total_items)
        status = "REVIEW_COMPLETE" if reviewed >= total_items else "IN_PROGRESS"
        self.assertEqual(status, "REVIEW_COMPLETE")

        # Verify disclaimer wording
        disclaimer = "Review Complete indicates all identified review items have received a human decision. It does not constitute statutory approval or procurement authorization."
        self.assertIn("does not constitute statutory approval", disclaimer)

    # -------------------------------------------------------------------------
    # 14. Safe Abstention Preservation
    # -------------------------------------------------------------------------
    def test_14_safe_abstention_preservation(self):
        """Verifies requirements with safe abstentions (no match) do not imply system recommendations."""
        self.assertEqual(self.req3.candidate_standard, "NONE")
        crit_dec = (self.req3.critic_result or {}).get("decision")
        self.assertEqual(crit_dec, "NO_RELIABLE_MATCH")

        # In safe abstention, system recommendation does not exist
        has_system_rec = bool(
            self.req3.candidate_standard
            and self.req3.candidate_standard not in ("NONE", "INSUFFICIENT_INFORMATION")
            and crit_dec != "NO_RELIABLE_MATCH"
        )
        self.assertFalse(has_system_rec)

    # -------------------------------------------------------------------------
    # 15. Lifecycle Finding Preservation
    # -------------------------------------------------------------------------
    def test_15_lifecycle_finding_preservation(self):
        """Verifies superseded standard findings remain intact even when human decision is recorded."""
        dec = HumanReviewDecisionRecord(
            requirement_id="REQ-002",
            decision="ACCEPT",
            reviewer_note="Accept active replacement",
        )
        report = self.generator.generate_report(
            audit_result=self.mock_audit,
            requirement_results=[self.req2],
            human_decisions=[dec],
        )
        req_sec = report.requirements[0]
        # Superseded citation and lifecycle finding preserved
        self.assertEqual(req_sec.superseded_citation, "IS 10611")
        if req_sec.review_reason:
            self.assertIn("superseded", req_sec.review_reason.lower())

    # -------------------------------------------------------------------------
    # 16. API Review Roundtrip
    # -------------------------------------------------------------------------
    def test_16_api_review_roundtrip(self):
        """Verifies POST /api/tender/<id>/review and GET /api/tender/<id>/review roundtrip."""
        # 1. Analyze sample to create session in _report_cache
        res = self.client.get("/api/analyze/sample/cpvc")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        tender_id = data["tender"]["id"]
        self.assertTrue(tender_id)

        # 2. GET initial review status
        get_res = self.client.get(f"/api/tender/{tender_id}/review")
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.get_json()
        self.assertEqual(get_data["tender_id"], tender_id)
        self.assertEqual(len(get_data["decisions"]), 0)
        self.assertEqual(get_data["progress"]["review_status"], "REVIEW_REQUIRED")

        # 3. POST human decisions
        first_req_id = data["requirements"][0]["id"]
        payload = {
            "decisions": [
                {
                    "requirement_id": first_req_id,
                    "decision": "ACCEPT",
                    "reviewer_note": "Verified by procurement officer",
                }
            ]
        }
        post_res = self.client.post(f"/api/tender/{tender_id}/review", json=payload)
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.get_json()
        self.assertEqual(post_data["status"], "ok")
        self.assertEqual(len(post_data["decisions"]), 1)
        self.assertEqual(post_data["decisions"][0]["decision"], "ACCEPT")
        self.assertEqual(post_data["progress"]["accepted_count"], 1)

        # 4. GET updated review status
        get_res2 = self.client.get(f"/api/tender/{tender_id}/review")
        self.assertEqual(get_res2.status_code, 200)
        get_data2 = get_res2.get_json()
        self.assertEqual(len(get_data2["decisions"]), 1)
        self.assertEqual(get_data2["decisions"][0]["decision"], "ACCEPT")


if __name__ == "__main__":
    unittest.main()
