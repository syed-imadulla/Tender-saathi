"""
Tests for Milestone 6: Tender Audit & Publication Readiness Engine.

Verifies:
1. Correct requirement count.
2. Correct recommendation count.
3. Correct review-required count.
4. Correct superseded count.
5. Correct withdrawn count.
6. Evidence distribution aggregation.
7. Completeness distribution aggregation.
8. Risk distribution aggregation.
9. Related-standard count.
10. Critical item appears before High in review queue.
11. High appears before Medium in review queue.
12. Readiness changes dynamically based on actual results.
13. Superseded standard affects readiness.
14. Weak evidence affects readiness appropriately.
15. Empty tender handled safely.
16. Single requirement handled correctly.
17. No legal-compliance wording generated.
18. No fake percentage score.
19. No hardcoded standard-number-specific outcomes in audit engine.
20. Existing critic Trust Gate remains intact.
21. Existing graph applicability separation remains intact.
22. Ground truth remains untouched.
"""

import unittest
import csv
import inspect
from typing import List

from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender, RequirementRecommendationResult, StandardRecommendation
from src.audit import TenderAuditEngine, TenderAuditResult, ReviewQueueItem
from src.extract import extract_from_text


class TestMilestone6Audit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = StandardsDatabase()
        cls.recommender = StandardsRecommender(cls.db)
        cls.audit_engine = TenderAuditEngine()

    def _create_mock_result(
        self,
        req_id: str,
        text: str,
        candidate_std: str = "IS 15778",
        status: str = "Active",
        version_role: str = "CURRENT_ACTIVE",
        risk_level: str = "LOW",
        decision: str = "RECOMMEND",
        human_review: bool = False,
        evidence_strength: str = "STRONG",
        completeness_label: str = "KNOWN",
        related_count: int = 0,
        risk_reasons: List[str] = None
    ) -> RequirementRecommendationResult:
        """Helper to create synthetic RequirementRecommendationResult for generic audit testing."""
        return RequirementRecommendationResult(
            requirement_id=req_id,
            requirement_text=text,
            category="PRODUCT",
            explicit_standards_found=[],
            candidate_standard=candidate_std,
            title="Mock Standard Title",
            status=status,
            version_role=version_role,
            relevance_score=0.90,
            confidence="High",
            evidence="Mock evidence text",
            provenance="VERIFIED" if evidence_strength == "STRONG" else "CURATED",
            human_review_required=human_review,
            reason="Mock reason",
            recommendations=[StandardRecommendation(
                standard_number=candidate_std,
                title="Mock Standard Title",
                status=status,
                version_role=version_role,
                relevance_score=0.90,
                confidence="High",
                evidence="Mock evidence text",
                provenance="VERIFIED"
            )],
            alternatives=[],
            decomposed_components=[],
            critic_result={
                "decision": decision,
                "risk_level": risk_level,
                "evidence": {"evidence_strength": evidence_strength, "grounded": True}
            },
            why_this=["Mock why this"],
            why_not=[],
            risk_level=risk_level,
            risk_reasons=risk_reasons or [],
            specification_completeness={
                "completeness_label": completeness_label,
                "known_count": 2 if completeness_label == "KNOWN" else 0,
                "potentially_missing_count": 2 if completeness_label == "POTENTIALLY_MISSING" else 0
            },
            related_standards=[{"standard_number": f"IS {i}", "relationship_type": "REFERENCES"} for i in range(related_count)]
        )

    # 1. Correct requirement count
    def test_01_requirement_count(self):
        results = [
            self._create_mock_result(f"REQ-{i}", f"Requirement {i}")
            for i in range(5)
        ]
        audit = self.audit_engine.audit_tender(results, tender_id="T001")
        self.assertEqual(audit.requirements_analyzed, 5)

    # 2. Correct recommendation count
    def test_02_recommendation_count(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", human_review=False, decision="RECOMMEND"),
            self._create_mock_result("REQ-2", "Req 2", human_review=False, decision="RECOMMEND"),
            self._create_mock_result("REQ-3", "Req 3", human_review=True, decision="REVIEW_REQUIRED")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.recommendations_count, 2)
        self.assertEqual(audit.review_required_count, 1)

    # 3. Correct review-required count
    def test_03_review_required_count(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", human_review=True, decision="REVIEW_REQUIRED"),
            self._create_mock_result("REQ-2", "Req 2", human_review=True, decision="RECOMMEND_WITH_REVIEW"),
            self._create_mock_result("REQ-3", "Req 3", human_review=False, decision="RECOMMEND")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.review_required_count, 2)

    # 4. Correct superseded count
    def test_04_superseded_count(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", status="Superseded", version_role="REPLACED_OR_SUPERSEDED"),
            self._create_mock_result("REQ-2", "Req 2", status="Active", version_role="CURRENT_ACTIVE")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.superseded_count, 1)
        self.assertEqual(audit.lifecycle_distribution["Superseded"], 1)

    # 5. Correct withdrawn count
    def test_05_withdrawn_count(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", status="Withdrawn"),
            self._create_mock_result("REQ-2", "Req 2", status="Active")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.withdrawn_count, 1)
        self.assertEqual(audit.lifecycle_distribution["Withdrawn"], 1)

    # 6. Evidence distribution aggregation
    def test_06_evidence_distribution(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", evidence_strength="STRONG"),
            self._create_mock_result("REQ-2", "Req 2", evidence_strength="MODERATE"),
            self._create_mock_result("REQ-3", "Req 3", evidence_strength="WEAK"),
            self._create_mock_result("REQ-4", "Req 4", evidence_strength="NONE")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.evidence_distribution["STRONG"], 1)
        self.assertEqual(audit.evidence_distribution["MODERATE"], 1)
        self.assertEqual(audit.evidence_distribution["WEAK"], 1)
        self.assertEqual(audit.evidence_distribution["NONE"], 1)
        self.assertEqual(sum(audit.evidence_distribution.values()), 4)

    # 7. Completeness distribution aggregation
    def test_07_completeness_distribution(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", completeness_label="KNOWN"),
            self._create_mock_result("REQ-2", "Req 2", completeness_label="POTENTIALLY_MISSING"),
            self._create_mock_result("REQ-3", "Req 3", completeness_label="UNKNOWN"),
            self._create_mock_result("REQ-4", "Req 4", completeness_label="NOT_APPLICABLE")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.completeness_distribution["KNOWN"], 1)
        self.assertEqual(audit.completeness_distribution["POTENTIALLY_MISSING"], 1)
        self.assertEqual(audit.completeness_distribution["UNKNOWN"], 1)
        self.assertEqual(audit.completeness_distribution["NOT_APPLICABLE"], 1)
        self.assertEqual(sum(audit.completeness_distribution.values()), 4)

    # 8. Risk distribution aggregation
    def test_08_risk_distribution(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", risk_level="LOW"),
            self._create_mock_result("REQ-2", "Req 2", risk_level="MEDIUM"),
            self._create_mock_result("REQ-3", "Req 3", risk_level="HIGH"),
            self._create_mock_result("REQ-4", "Req 4", risk_level="CRITICAL")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.risk_distribution["LOW"], 1)
        self.assertEqual(audit.risk_distribution["MEDIUM"], 1)
        self.assertEqual(audit.risk_distribution["HIGH"], 1)
        self.assertEqual(audit.risk_distribution["CRITICAL"], 1)
        self.assertEqual(sum(audit.risk_distribution.values()), 4)

    # 9. Related-standard count
    def test_09_related_standards_count(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", related_count=2),
            self._create_mock_result("REQ-2", "Req 2", related_count=3)
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.related_standards_count, 5)

    # 10. Critical item appears before High
    def test_10_critical_before_high_in_queue(self):
        results = [
            self._create_mock_result("REQ-HIGH", "High risk item", risk_level="HIGH", human_review=True),
            self._create_mock_result("REQ-CRIT", "Critical risk item", risk_level="CRITICAL", human_review=True)
        ]
        audit = self.audit_engine.audit_tender(results)
        queue_ids = [item.requirement_id for item in audit.review_queue]
        self.assertEqual(queue_ids[0], "REQ-CRIT")
        self.assertEqual(queue_ids[1], "REQ-HIGH")

    # 11. High appears before Medium
    def test_11_high_before_medium_in_queue(self):
        results = [
            self._create_mock_result("REQ-MED", "Medium item", risk_level="MEDIUM", human_review=True),
            self._create_mock_result("REQ-HIGH", "High item", risk_level="HIGH", human_review=True)
        ]
        audit = self.audit_engine.audit_tender(results)
        queue_ids = [item.requirement_id for item in audit.review_queue]
        self.assertEqual(queue_ids[0], "REQ-HIGH")
        self.assertEqual(queue_ids[1], "REQ-MED")

    # 12. Readiness changes based on actual results
    def test_12_readiness_changes_based_on_results(self):
        clean_results = [
            self._create_mock_result("REQ-1", "Req 1", risk_level="LOW", human_review=False, decision="RECOMMEND"),
            self._create_mock_result("REQ-2", "Req 2", risk_level="LOW", human_review=False, decision="RECOMMEND")
        ]
        clean_audit = self.audit_engine.audit_tender(clean_results)
        self.assertEqual(clean_audit.publication_readiness, "READY_FOR_REVIEW")

        flagged_results = clean_results + [
            self._create_mock_result("REQ-3", "Req 3", risk_level="HIGH", human_review=True, decision="REVIEW_REQUIRED")
        ]
        flagged_audit = self.audit_engine.audit_tender(flagged_results)
        self.assertEqual(flagged_audit.publication_readiness, "REVIEW_REQUIRED")

    # 13. Superseded standard affects readiness
    def test_13_superseded_affects_readiness(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", status="Superseded", risk_level="CRITICAL", human_review=True)
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.publication_readiness, "REVIEW_REQUIRED")
        self.assertTrue(any("superseded" in r.lower() for r in audit.readiness_reasons))

    # 14. Weak evidence affects readiness appropriately
    def test_14_weak_evidence_affects_readiness(self):
        results = [
            self._create_mock_result("REQ-1", "Req 1", evidence_strength="NONE", decision="INSUFFICIENT_EVIDENCE"),
            self._create_mock_result("REQ-2", "Req 2", evidence_strength="NONE", decision="INSUFFICIENT_EVIDENCE")
        ]
        audit = self.audit_engine.audit_tender(results)
        self.assertEqual(audit.publication_readiness, "INSUFFICIENT_EVIDENCE")

    # 15. Empty tender handled safely
    def test_15_empty_tender_handled_safely(self):
        audit = self.audit_engine.audit_tender([])
        self.assertEqual(audit.requirements_analyzed, 0)
        self.assertEqual(audit.publication_readiness, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(len(audit.review_queue), 0)
        self.assertGreater(len(audit.readiness_reasons), 0)

    # 16. Single requirement handled correctly
    def test_16_single_requirement_handled_correctly(self):
        single = [self._create_mock_result("REQ-1", "Single item")]
        audit = self.audit_engine.audit_tender(single)
        self.assertEqual(audit.requirements_analyzed, 1)
        self.assertEqual(audit.publication_readiness, "READY_FOR_REVIEW")

    # 17. No legal-compliance wording generated
    def test_17_no_legal_compliance_wording(self):
        results = [
            self._create_mock_result("REQ-1", "Supply of pipes", risk_level="CRITICAL", human_review=True),
            self._create_mock_result("REQ-2", "Valves", risk_level="LOW", human_review=False)
        ]
        audit = self.audit_engine.audit_tender(results)
        audit_dict_str = str(audit.to_dict()).lower()

        forbidden_phrases = [
            "legally valid",
            "legally invalid",
            "legally complete",
            "legally incomplete",
            "non-compliant",
            "compliance check"
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, audit_dict_str, f"Forbidden legal terminology found: '{phrase}'")

    # 18. No fake percentage score
    def test_18_no_fake_percentage_score(self):
        results = [self._create_mock_result("REQ-1", "Req 1")]
        audit = self.audit_engine.audit_tender(results)
        d = audit.to_dict()

        self.assertNotIn("score", d)
        self.assertNotIn("percentage", d)
        self.assertNotIn("compliance_percentage", d)
        self.assertNotIn("readiness_score", d)

    # 19. No hardcoded standard-number-specific outcomes
    def test_19_no_hardcoded_standard_numbers(self):
        src = inspect.getsource(self.audit_engine.audit_tender)
        src += inspect.getsource(self.audit_engine._determine_publication_readiness)
        forbidden_standards = ["10611", "15778", "10434", "778", "458", "15000", "2491"]
        for std in forbidden_standards:
            self.assertNotIn(std, src, f"Audit engine logic must not hardcode standard number '{std}'.")

    # 20. Existing critic Trust Gate remains intact
    def test_20_critic_trust_gate_intact(self):
        from src.search import SearchResult
        from src.completeness import DomainCompletenessAnalyzer
        dummy_cand = SearchResult(
            standard_id="IS-302-1994",
            standard_number="IS 302",
            year=1994,
            full_title="General and Safety Requirements for Household and Similar Electrical Appliances",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.95,
            relevance_reason="Simulated high retrieval score",
            scope_summary="Electrical appliance safety requirements",
            verification_status="CURATED",
            source_provenance="SIMULATED"
        )
        comp = DomainCompletenessAnalyzer().analyze("High-pressure gas line pipe")
        crit = self.recommender.critic.critique_candidate(
            candidate=dummy_cand,
            requirement_text="High-pressure gas line pipe",
            components=[],
            completeness=comp
        )
        self.assertIn(crit.decision, ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE", "REJECT"])
        self.assertTrue(crit.review_required)

    # 21. Existing graph applicability separation remains intact
    def test_21_graph_applicability_separation_intact(self):
        req = extract_from_text("Supply of CPVC pipes for potable water distribution", requirement_id="T-GRAPH")
        rec_res = self.recommender.recommend_for_requirement(req)
        audit = self.audit_engine.audit_tender([rec_res])
        # Related standards count is tracked separately and does not inflate recommendations count
        self.assertEqual(audit.requirements_analyzed, 1)
        self.assertLessEqual(audit.recommendations_count, 1)

    # 22. Ground truth remains untouched
    def test_22_ground_truth_untouched(self):
        with open("dataset/ground_truth/ground_truth.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), 20, "Ground truth benchmark must remain exactly 20 rows.")

    # 23. Exact conservation law: recommendations + review_required + insufficient == analyzed
    def test_23_exact_conservation_law(self):
        """Verify recommendations_count + review_required_count + insufficient_evidence_count == requirements_analyzed."""
        test_cases = [
            [],  # 0 requirements
            [self._create_mock_result("R1", "Clean", human_review=False, decision="RECOMMEND")],
            [
                self._create_mock_result("R1", "Clean", human_review=False, decision="RECOMMEND"),
                self._create_mock_result("R2", "Review req", human_review=True, decision="REVIEW_REQUIRED"),
                self._create_mock_result("R3", "No info", candidate_std="INSUFFICIENT_INFORMATION", decision="INSUFFICIENT_EVIDENCE")
            ],
            [
                self._create_mock_result("R1", "Req 1", human_review=True, decision="RECOMMEND_WITH_REVIEW"),
                self._create_mock_result("R2", "Req 2", human_review=True, decision="REVIEW_REQUIRED"),
                self._create_mock_result("R3", "Req 3", human_review=False, decision="RECOMMEND"),
                self._create_mock_result("R4", "Req 4", human_review=False, decision="RECOMMEND"),
                self._create_mock_result("R5", "Req 5", candidate_std="UNKNOWN", decision="INSUFFICIENT_EVIDENCE")
            ]
        ]
        for case in test_cases:
            audit = self.audit_engine.audit_tender(case)
            total = audit.requirements_analyzed
            sub_sum = audit.recommendations_count + audit.review_required_count + audit.insufficient_evidence_count
            self.assertEqual(sub_sum, total, f"Conservation failed: {sub_sum} != {total} for case len {len(case)}")

    # 24. Curated-only tender reaches READY_FOR_REVIEW
    def test_24_curated_only_tender_ready_for_review(self):
        """Verify that well-supported CURATED requirements (MODERATE evidence) do NOT fail readiness."""
        curated_results = [
            self._create_mock_result("R1", "Curated 1", evidence_strength="MODERATE", human_review=False, decision="RECOMMEND"),
            self._create_mock_result("R2", "Curated 2", evidence_strength="MODERATE", human_review=False, decision="RECOMMEND")
        ]
        audit = self.audit_engine.audit_tender(curated_results)
        self.assertEqual(audit.publication_readiness, "READY_FOR_REVIEW")
        self.assertEqual(audit.evidence_distribution["MODERATE"], 2)
        self.assertEqual(audit.evidence_distribution["STRONG"], 0)

    # 25. Clean LOW-risk requirement without review condition is excluded from review queue
    def test_25_low_risk_no_review_excluded_from_queue(self):
        """Verify clean low-risk recommendations without review conditions do not clutter review queue."""
        clean_results = [
            self._create_mock_result("R1", "Clean low risk", risk_level="LOW", human_review=False, decision="RECOMMEND")
        ]
        audit = self.audit_engine.audit_tender(clean_results)
        self.assertEqual(len(audit.review_queue), 0, "Clean LOW-risk requirement must not be in review queue")


if __name__ == "__main__":
    unittest.main()
