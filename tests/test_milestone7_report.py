"""
tests/test_milestone7_report.py
Unit tests for Milestone 7: Evidence-Backed Standards Review Report Generator.

Verifies:
1. Report generated from valid TenderAuditResult.
2. Tender metadata is preserved.
3. Readiness state is preserved.
4. Readiness reasons are preserved.
5. Aggregate counts match TenderAuditResult.
6. Every requirement appears exactly once.
7. Recommendation information is preserved.
8. Evidence strength is preserved.
9. Provenance is preserved.
10. Lifecycle information is preserved.
11. Superseded standards are clearly represented.
12. Completeness findings are preserved.
13. Related standards are preserved.
14. Human review queue is preserved.
15. Risk ordering works.
16. No unsupported claims are invented (no compliance certification, honest provenance).
17. JSON serialization works.
18. Markdown generation works.
19. Empty/missing optional metadata does not crash.
20. Integration with demo and existing pipelines.
"""

import unittest
import json
import os
import tempfile

from src.audit import (
    TenderAuditResult,
    ReviewQueueItem
)
from src.recommend import (
    RequirementRecommendationResult,
    StandardRecommendation
)
from src.report import (
    TenderInformation,
    RequirementReviewSection,
    EvidenceSummary,
    TenderReviewReport,
    ReportGenerator
)


class TestMilestone7Report(unittest.TestCase):
    def setUp(self):
        self.generator = ReportGenerator()

        # Build mock RequirementRecommendationResults
        self.req1 = RequirementRecommendationResult(
            requirement_id="REQ-001",
            requirement_text="Supply of CPVC pipes for domestic water distribution",
            category="material",
            explicit_standards_found=[],
            candidate_standard="IS 15778 : 2007",
            title="Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Supplies",
            status="Active",
            confidence="High",
            reason="Exact specification match for CPVC potable water pipes.",
            evidence="Authoritative standard for Chlorinated Polyvinyl Chloride pipes.",
            provenance="VERIFIED",
            relevance_score=0.92,
            alternatives=["IS 4985 : 2021"],
            version_role="Current Primary",
            human_review_required=False,
            decomposed_components=[{"aspect": "material", "text": "CPVC", "subcategory": "polymer"}],
            critic_result={
                "decision": "RECOMMEND",
                "risk_level": "LOW",
                "evidence": {
                    "evidence_strength": "STRONG",
                    "evidence_text": "Authoritative standard for Chlorinated Polyvinyl Chloride pipes.",
                    "evidence_source": "BSB Edge Portal"
                },
                "why_this": ["Exact match for CPVC pipes", "Active BIS standard"],
                "why_not": ["IS 4985 applies to uPVC, not CPVC"]
            },
            specification_completeness={
                "completeness_label": "KNOWN",
                "domain": "piping",
                "known_parameters": {"material": "CPVC", "application": "potable water"},
                "potentially_missing_parameters": []
            },
            related_standards=[
                {
                    "standard_number": "IS 4985",
                    "title": "Unplasticized PVC Pipes",
                    "relationship_type": "RELATED_TO",
                    "direction": "OUTGOING",
                    "lifecycle_status": "Active",
                    "review_note": "Related standard identified for review"
                }
            ],
            risk_level="LOW",
            risk_reasons=[]
        )

        self.req2 = RequirementRecommendationResult(
            requirement_id="REQ-002",
            requirement_text="Replacement of valves conforming to IS 10611",
            category="product",
            explicit_standards_found=["IS 10611"],
            candidate_standard="IS/ISO 10434 : 2020",
            title="Steel Globe Valves",
            status="Active",
            confidence="Medium",
            reason="Superseded standard cited in tender.",
            evidence="Curated catalog mapping IS 10611 -> IS/ISO 10434.",
            provenance="CURATED",
            relevance_score=0.85,
            alternatives=[],
            version_role="Superseded Citation",
            human_review_required=True,
            decomposed_components=[{"aspect": "product", "text": "valves"}],
            critic_result={
                "decision": "REVIEW_REQUIRED",
                "risk_level": "CRITICAL",
                "evidence": {
                    "evidence_strength": "MODERATE",
                    "evidence_text": "Curated catalog mapping IS 10611 -> IS/ISO 10434.",
                    "evidence_source": "BIS Standards Catalogue"
                },
                "why_this": ["Active successor standard to IS 10611"],
                "why_not": []
            },
            specification_completeness={
                "completeness_label": "POTENTIALLY_MISSING",
                "domain": "valves",
                "known_parameters": {"standard_cited": "IS 10611"},
                "potentially_missing_parameters": ["DN", "PN", "body_material"]
            },
            related_standards=[
                {
                    "standard_number": "IS 10611",
                    "title": "Steel Globe Valves",
                    "relationship_type": "SUPERSEDES",
                    "direction": "OUTGOING",
                    "lifecycle_status": "Superseded",
                    "review_note": "Legacy standard cited; verify replacement"
                }
            ],
            recommendations=[
                StandardRecommendation(
                    standard_number="IS/ISO 10434",
                    title="Steel Globe Valves",
                    status="Active",
                    version_role="CURRENT_ACTIVE",
                    relevance_score=0.85,
                    confidence="Medium",
                    evidence="Curated catalog",
                    provenance="CURATED",
                    superseded_warning="Cites superseded IS 10611"
                )
            ],
            risk_level="CRITICAL",
            risk_reasons=["Tender cites superseded standard IS 10611"]
        )

        self.req3 = RequirementRecommendationResult(
            requirement_id="REQ-003",
            requirement_text="Generic civil excavation work",
            category="general",
            explicit_standards_found=[],
            candidate_standard="NONE",
            title="No standard matched",
            status="Unknown",
            confidence="Low",
            reason="No clear Indian Standard match found.",
            evidence="",
            provenance="INFERRED",
            relevance_score=0.2,
            alternatives=[],
            version_role="None",
            human_review_required=True,
            critic_result={
                "decision": "INSUFFICIENT_EVIDENCE",
                "risk_level": "HIGH",
                "evidence": {
                    "evidence_strength": "WEAK",
                    "evidence_text": "",
                    "evidence_source": None
                }
            },
            specification_completeness={
                "completeness_label": "UNKNOWN",
                "domain": "generic",
                "known_parameters": {},
                "potentially_missing_parameters": []
            },
            risk_level="HIGH",
            risk_reasons=["No matching standards in scope"]
        )

        self.requirements_list = [self.req1, self.req2, self.req3]

        # Build mock TenderAuditResult
        self.audit_result = TenderAuditResult(
            tender_id="T-DEMO-2026",
            requirements_analyzed=3,
            recommendations_count=1,
            review_required_count=2,
            insufficient_evidence_count=0,
            active_count=2,
            superseded_count=1,
            withdrawn_count=0,
            unknown_lifecycle_count=0,
            evidence_distribution={"STRONG": 1, "MODERATE": 1, "WEAK": 1, "NONE": 0},
            completeness_distribution={"KNOWN": 1, "POTENTIALLY_MISSING": 1, "UNKNOWN": 1, "NOT_APPLICABLE": 0},
            risk_distribution={"CRITICAL": 1, "HIGH": 1, "MEDIUM": 0, "LOW": 1},
            lifecycle_distribution={"Active": 2, "Superseded": 1, "Withdrawn": 0, "Unknown": 0},
            related_standards_count=2,
            publication_readiness="REVIEW_REQUIRED",
            readiness_reasons=[
                "1 requirement(s) cite or match superseded standard(s).",
                "1 requirement(s) flagged with CRITICAL risk.",
                "2 requirement(s) require technical engineer review."
            ],
            review_queue=[
                ReviewQueueItem(
                    requirement_id="REQ-002",
                    requirement_text="Replacement of valves conforming to IS 10611",
                    risk_level="CRITICAL",
                    decision="REVIEW_REQUIRED",
                    candidate_standard="IS/ISO 10434 : 2020",
                    evidence_strength="MODERATE",
                    primary_reason="Tender explicitly cited a superseded standard requiring replacement verification.",
                    priority=1
                ),
                ReviewQueueItem(
                    requirement_id="REQ-003",
                    requirement_text="Generic civil excavation work",
                    risk_level="HIGH",
                    decision="INSUFFICIENT_EVIDENCE",
                    candidate_standard="NONE",
                    evidence_strength="WEAK",
                    primary_reason="No matching standards in scope.",
                    priority=2
                )
            ]
        )

        self.metadata = {
            "tender_title": "Water Works and Civil Renovation",
            "organisation": "Municipal Engineering Dept",
            "source_file": "tender_spec_2026.pdf",
            "date": "2026-09-10"
        }

    # 1. Report generated from valid TenderAuditResult
    def test_report_generation_from_valid_audit_result(self):
        report = self.generator.generate_report(
            self.audit_result,
            self.requirements_list,
            tender_metadata=self.metadata
        )
        self.assertIsInstance(report, TenderReviewReport)
        self.assertEqual(report.tender_info.tender_id, "T-DEMO-2026")

    # 2. Tender metadata is preserved
    def test_tender_metadata_preserved(self):
        report = self.generator.generate_report(
            self.audit_result,
            self.requirements_list,
            tender_metadata=self.metadata
        )
        self.assertEqual(report.tender_info.tender_title, "Water Works and Civil Renovation")
        self.assertEqual(report.tender_info.organisation, "Municipal Engineering Dept")
        self.assertEqual(report.tender_info.source_file, "tender_spec_2026.pdf")
        self.assertEqual(report.tender_info.date, "2026-09-10")
        self.assertEqual(report.tender_info.requirements_analyzed, 3)

    # 3. Readiness state is preserved
    def test_readiness_state_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        self.assertEqual(report.publication_readiness, "REVIEW_REQUIRED")
        # Ensure disallowed terms are NOT used
        self.assertNotIn(report.publication_readiness, ["COMPLIANT", "NON-COMPLIANT", "LEGALLY COMPLIANT"])

    # 4. Readiness reasons are preserved
    def test_readiness_reasons_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        self.assertEqual(len(report.readiness_reasons), 3)
        self.assertIn("1 requirement(s) cite or match superseded standard(s).", report.readiness_reasons)

    # 5. Aggregate counts match TenderAuditResult
    def test_aggregate_counts_match(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        es = report.executive_summary
        self.assertEqual(es["requirements_analyzed"], 3)
        self.assertEqual(es["recommendations_count"], 1)
        self.assertEqual(es["review_required_count"], 2)
        self.assertEqual(es["insufficient_evidence_count"], 0)
        self.assertEqual(es["active_count"], 2)
        self.assertEqual(es["superseded_count"], 1)
        self.assertEqual(es["related_standards_count"], 2)

    # 6. Every requirement appears exactly once
    def test_every_requirement_appears_once(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        self.assertEqual(len(report.requirements), 3)
        req_ids = [r.requirement_id for r in report.requirements]
        self.assertEqual(req_ids, ["REQ-001", "REQ-002", "REQ-003"])
        self.assertEqual(len(set(req_ids)), 3)

    # 7. Recommendation information is preserved
    def test_recommendation_info_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        sec1 = report.requirements[0]
        self.assertEqual(sec1.recommended_standard, "IS 15778 : 2007")
        self.assertEqual(sec1.relevance_score, 0.92)
        self.assertEqual(sec1.components, [{"aspect": "material", "text": "CPVC", "subcategory": "polymer"}])

    # 8. Evidence strength is preserved
    def test_evidence_strength_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        self.assertEqual(report.requirements[0].evidence_strength, "STRONG")
        self.assertEqual(report.requirements[1].evidence_strength, "MODERATE")
        self.assertEqual(report.requirements[2].evidence_strength, "WEAK")

    # 9. Provenance is preserved
    def test_provenance_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        self.assertEqual(report.requirements[0].provenance, "VERIFIED")
        self.assertEqual(report.requirements[1].provenance, "CURATED")
        self.assertEqual(report.requirements[2].provenance, "INFERRED")

    # 10. Lifecycle information is preserved
    def test_lifecycle_information_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        self.assertEqual(report.requirements[0].lifecycle_status, "Active")
        self.assertEqual(report.requirements[1].lifecycle_status, "Active")
        self.assertEqual(report.requirements[2].lifecycle_status, "Unknown")

    # 11. Superseded standards are clearly represented
    def test_superseded_standards_represented(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        sec2 = report.requirements[1]
        self.assertEqual(sec2.successor_standard, "IS/ISO 10434")
        md = report.to_markdown()
        self.assertIn("Superseded by `IS/ISO 10434`", md)

    # 12. Completeness findings are preserved
    def test_completeness_findings_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        sec1 = report.requirements[0]
        sec2 = report.requirements[1]
        self.assertEqual(sec1.completeness_label, "KNOWN")
        self.assertEqual(sec1.potentially_missing_parameters, [])
        self.assertEqual(sec2.completeness_label, "POTENTIALLY_MISSING")
        self.assertIn("DN", sec2.potentially_missing_parameters)
        self.assertIn("PN", sec2.potentially_missing_parameters)

    # 13. Related standards are preserved
    def test_related_standards_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        sec1 = report.requirements[0]
        self.assertEqual(len(sec1.related_standards), 1)
        self.assertEqual(sec1.related_standards[0]["standard_number"], "IS 4985")
        md = report.to_markdown()
        self.assertIn("Related standard identified for review", sec1.related_standards[0]["review_note"])
        # Important boundary rule: related standard is review notice, not automatic applicability
        self.assertIn("Related Standards Identified for Review", md)

    # 14. Human review queue is preserved
    def test_human_review_queue_preserved(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        self.assertEqual(len(report.review_queue), 2)
        self.assertEqual(report.review_queue[0].requirement_id, "REQ-002")
        self.assertEqual(report.review_queue[1].requirement_id, "REQ-003")

    # 15. Risk ordering in review queue works (CRITICAL before HIGH before MEDIUM before LOW)
    def test_risk_ordering(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        priorities = [q.risk_level for q in report.review_queue]
        self.assertEqual(priorities, ["CRITICAL", "HIGH"])

    # 16. No unsupported claims are invented (non-legalistic disclaimers present)
    def test_no_unsupported_claims_invented(self):
        report = self.generator.generate_report(self.audit_result, self.requirements_list)
        md = report.to_markdown()
        # Ensure mandatory disclaimer appears
        self.assertIn("does not constitute legal compliance certification", md)
        self.assertIn("Final applicability, specification, procurement, regulatory and legal decisions", md)
        # Ensure AI limitation statement is included
        self.assertIn("AI/retrieval results are not treated as authoritative evidence", md)
        # Never claim legal compliance
        self.assertNotIn("LEGALLY COMPLIANT", md)
        self.assertNotIn("NON-COMPLIANT", md)

    # 17. JSON serialization works
    def test_json_serialization(self):
        report = self.generator.generate_report(
            self.audit_result,
            self.requirements_list,
            tender_metadata=self.metadata
        )
        json_str = report.to_json()
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["tender_info"]["tender_id"], "T-DEMO-2026")
        self.assertEqual(len(parsed["requirements"]), 3)
        self.assertEqual(len(parsed["review_queue"]), 2)

    # 18. Markdown generation works
    def test_markdown_generation(self):
        report = self.generator.generate_report(
            self.audit_result,
            self.requirements_list,
            tender_metadata=self.metadata
        )
        md = report.to_markdown()
        self.assertIsInstance(md, str)
        self.assertIn("# TenderSaathi Evidence-Backed Indian Standards Review Report", md)
        self.assertIn("## 1. Tender Information", md)
        self.assertIn("## 2. Publication Readiness", md)
        self.assertIn("## 3. Executive Summary", md)
        self.assertIn("## 4. Prioritized Human Review Queue", md)
        self.assertIn("## 5. Requirement-by-Requirement Review", md)
        self.assertIn("## 6. Evidence & Provenance Governance Summary", md)
        self.assertIn("## 7. Officer Notice & Disclaimer", md)

    # 19. Empty/missing optional metadata does not crash
    def test_empty_metadata_safe(self):
        # Empty audit result & empty metadata
        empty_audit = TenderAuditResult(
            tender_id="EMPTY-TENDER",
            requirements_analyzed=0,
            recommendations_count=0,
            review_required_count=0,
            insufficient_evidence_count=0,
            active_count=0,
            superseded_count=0,
            withdrawn_count=0,
            unknown_lifecycle_count=0,
            evidence_distribution={},
            completeness_distribution={},
            risk_distribution={},
            lifecycle_distribution={},
            related_standards_count=0,
            publication_readiness="INSUFFICIENT_EVIDENCE",
            readiness_reasons=[],
            review_queue=[]
        )
        report = self.generator.generate_report(empty_audit, [], tender_metadata=None)
        self.assertEqual(report.tender_info.tender_id, "EMPTY-TENDER")
        self.assertIsNone(report.tender_info.tender_title)
        md = report.to_markdown()
        self.assertIn("EMPTY-TENDER", md)
        json_dict = json.loads(report.to_json())
        self.assertEqual(json_dict["tender_info"]["tender_id"], "EMPTY-TENDER")

    # 20. File saving generates valid files on disk
    def test_generate_and_save_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            md_path, json_path = self.generator.generate_and_save(
                self.audit_result,
                self.requirements_list,
                output_dir=tmp_dir,
                tender_metadata=self.metadata
            )
            self.assertTrue(os.path.exists(md_path))
            self.assertTrue(os.path.exists(json_path))
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("T-DEMO-2026", content)
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(data["tender_info"]["tender_id"], "T-DEMO-2026")


if __name__ == "__main__":
    unittest.main()
