"""
Module: tests/test_milestone10_gap_detection.py
Purpose: Test suite for Milestone 10 Priority 2: Missing-Standard & Coverage Detection.

Verifies:
9. Existing dependency is detected as present.
10. Absent dependency becomes POTENTIALLY_MISSING when evidence supports it.
11. Unsupported dependency is not flagged.
12. Explicitly cited dependency is not reported as missing.
13. Verified missing case gets stronger severity.
14. Ambiguous requirement becomes REVIEW_REQUIRED.
15. Missing specification parameter remains separate from missing standard.
16. Nonsense input does not generate fake dependencies.
17. Cross-domain candidate does not generate a dependency.
18. Lifecycle-invalid dependency is flagged separately.
19. Provenance cannot be upgraded by semantic similarity.
20. Human review remains required where evidence is insufficient.
"""

import unittest
from src.dependencies import StandardsDependencyEngine
from src.gap_detection import StandardsGapDetector, GapItem
from src.recommend import StandardsRecommender
from src.extract import Requirement


class TestMilestone10GapDetection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dep_engine = StandardsDependencyEngine()
        cls.gap_detector = StandardsGapDetector()
        cls.recommender = StandardsRecommender(retrieval_mode="hybrid")

    # 9. Existing dependency is detected as present
    def test_09_existing_dependency_detected_as_present(self):
        """When a dependency (e.g. IS 12235) is cited in the tender, it is marked COVERED_IN_TENDER."""
        dep_rep = self.dep_engine.analyze_dependencies(
            "Providing and fixing CPVC pipes per IS 15778 and IS 12235",
            "IS 15778 : 2007"
        )
        cov_map = self.gap_detector.detect_gaps(
            requirement="Providing and fixing CPVC pipes per IS 15778 and IS 12235",
            primary_standard="IS 15778 : 2007",
            primary_title="CPVC Pipes Specification",
            dependency_report=dep_rep,
            tender_cited_standards=["IS 12235"]
        )
        covered_stds = [
            d["standard"] for d in cov_map.dependencies_coverage
            if d["coverage_status"] == "COVERED_IN_TENDER"
        ]
        self.assertTrue(any("12235" in c for c in covered_stds))

    # 10. Absent dependency becomes POTENTIALLY_MISSING when evidence supports it
    def test_10_absent_dependency_becomes_potentially_missing(self):
        """When an evidence-backed dependency is not cited, it is classified as POTENTIALLY_MISSING."""
        dep_rep = self.dep_engine.analyze_dependencies(
            "Providing and fixing CPVC pipes for hot and cold water",
            "IS 15778 : 2007"
        )
        cov_map = self.gap_detector.detect_gaps(
            requirement="Providing and fixing CPVC pipes for hot and cold water",
            primary_standard="IS 15778 : 2007",
            primary_title="CPVC Pipes Specification",
            dependency_report=dep_rep,
            tender_cited_standards=[]  # Nothing cited
        )
        gap_severities = [g.gap_severity for g in cov_map.standard_gaps]
        self.assertIn("POTENTIALLY_MISSING", gap_severities)

    # 11. Unsupported dependency is not flagged
    def test_11_unsupported_dependency_not_flagged(self):
        """Standards without evidence-backed relationships in the graph are never flagged as missing."""
        dep_rep = self.dep_engine.analyze_dependencies(
            "Supply of valves",
            "IS 778 : 1984"
        )
        cov_map = self.gap_detector.detect_gaps(
            requirement="Supply of valves",
            primary_standard="IS 778 : 1984",
            primary_title="Copper alloy gate valves",
            dependency_report=dep_rep,
            tender_cited_standards=[]
        )
        # Check that no random standards (e.g. paints IS 101 or cables IS 694) appear as gaps
        import re
        gap_numbers = [g.standard_number for g in cov_map.standard_gaps if g.standard_number]
        self.assertFalse(any(re.search(r'\b(101|694)\b', g) for g in gap_numbers))

    # 12. Explicitly cited dependency is not reported as missing
    def test_12_cited_dependency_not_reported_as_missing(self):
        """If a tender explicitly cites IS 783, it must not be reported as missing for concrete pipes."""
        dep_rep = self.dep_engine.analyze_dependencies(
            "Supply and laying of concrete pipes per IS 458 and IS 783",
            "IS 458 : 2021"
        )
        cov_map = self.gap_detector.detect_gaps(
            requirement="Supply and laying of concrete pipes per IS 458 and IS 783",
            primary_standard="IS 458 : 2021",
            primary_title="Precast concrete pipes",
            dependency_report=dep_rep,
            tender_cited_standards=["IS 783"]
        )
        missing_std_nums = [g.standard_number for g in cov_map.standard_gaps]
        self.assertFalse(any("783" in m for m in missing_std_nums if m))

    # 13. Verified missing case gets stronger severity
    def test_13_verified_missing_stronger_severity(self):
        """
        When requirement explicitly calls for laying/jointing operations and
        the authoritative laying code (IS 783) is omitted, it escalates to VERIFIED_MISSING.
        """
        dep_rep = self.dep_engine.analyze_dependencies(
            "Providing, laying and jointing of precast concrete pipes in trenches",
            "IS 458 : 2021"
        )
        cov_map = self.gap_detector.detect_gaps(
            requirement="Providing, laying and jointing of precast concrete pipes in trenches",
            primary_standard="IS 458 : 2021",
            primary_title="Precast concrete pipes",
            dependency_report=dep_rep,
            tender_cited_standards=[]
        )
        ver_missing = [g for g in cov_map.standard_gaps if g.gap_severity == "VERIFIED_MISSING"]
        self.assertTrue(len(ver_missing) > 0)
        self.assertTrue(any("783" in g.standard_number for g in ver_missing))

    # 14. Ambiguous requirement becomes REVIEW_REQUIRED
    def test_14_ambiguous_requirement_review_required(self):
        """Vague requirement without technical parameters requires human review."""
        req = Requirement(
            requirement_id="REQ-AMBIG",
            requirement_text="Supply of standard commercial piping materials as per site engineer direction",
            category="plumbing"
        )
        res = self.recommender.recommend_for_requirement(req)
        self.assertTrue(res.human_review_required)
        self.assertIn(res.critic_result.get("decision", ""), ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE", "NO_RELIABLE_MATCH"])

    # 15. Missing specification parameter remains separate from missing standard
    def test_15_parameter_gap_separated_from_standard_gap(self):
        """SPECIFICATION_GAP (parameters) and STANDARD_GAP (standards) must remain in distinct categories."""
        dep_rep = self.dep_engine.analyze_dependencies(
            "Supply of CPVC pipes",
            "IS 15778 : 2007"
        )
        cov_map = self.gap_detector.detect_gaps(
            requirement="Supply of CPVC pipes",
            primary_standard="IS 15778 : 2007",
            primary_title="CPVC Pipes",
            dependency_report=dep_rep,
            completeness_report={"missing_parameters": ["diameter_nominal_bore", "pressure_class"]}
        )
        self.assertEqual(len(cov_map.specification_gaps), 2)
        for sg in cov_map.specification_gaps:
            self.assertEqual(sg.gap_type, "SPECIFICATION_GAP")
            self.assertIsNone(sg.standard_number)

        for std_g in cov_map.standard_gaps:
            self.assertEqual(std_g.gap_type, "STANDARD_GAP")
            self.assertIsNotNone(std_g.standard_number)

    # 16. Nonsense input does not generate fake dependencies
    def test_16_nonsense_input_zero_dependencies(self):
        """Nonsense input ('xyz abc 123') must not produce any standards dependencies or coverage maps."""
        req = Requirement(
            requirement_id="REQ-NONSENSE",
            requirement_text="xyz abc 123 random nonsense text",
            category="general"
        )
        res = self.recommender.recommend_for_requirement(req)
        self.assertIsNone(res.candidate_standard)
        self.assertEqual(len(res.dependencies), 0)
        cov = res.standards_coverage
        if cov:
            self.assertEqual(cov.get("coverage_summary", {}).get("total_dependencies", 0), 0)

    # 17. Cross-domain candidate does not generate a dependency
    def test_17_cross_domain_candidate_zero_dependencies(self):
        """Crane rail track requirement must abstain and produce zero valve dependencies."""
        req = Requirement(
            requirement_id="REQ-CRANE",
            requirement_text="REPLACEMENT OF CRANE RAIL TRACK FOR RMQC (RAIL MOUNTED QUAY CRANE) INCLUDING ALLIED WORKS AT BERTH NO. 11 and 12 IN DOCK AREA, H.D.C, HALDIA",
            category="mechanical"
        )
        res = self.recommender.recommend_for_requirement(req)
        self.assertIsNone(res.candidate_standard)
        # Must not have any valve dependencies attached
        dep_nums = [d.get("standard_number", "") for d in (res.dependencies or [])]
        self.assertFalse(any("10434" in d or "778" in d for d in dep_nums))

    # 18. Lifecycle-invalid dependency is flagged separately
    def test_18_lifecycle_invalid_dependency_flagged(self):
        """If a dependency standard is superseded (e.g. IS 10611 for IS/ISO 10434), it is flagged in lifecycle."""
        dep_rep = self.dep_engine.analyze_dependencies(
            "Supply of bolted bonnet steel gate valves",
            "IS/ISO 10434 : 2020"
        )
        dep_10611 = [d for d in dep_rep.all_dependencies if "10611" in d.standard_number]
        self.assertTrue(len(dep_10611) > 0)
        self.assertEqual(dep_10611[0].relationship_type, "SUPERSEDES")

    # 19. Provenance cannot be upgraded by semantic similarity
    def test_19_provenance_cannot_be_upgraded(self):
        """Curated dependency items retain CURATED provenance regardless of similarity score."""
        dep_rep = self.dep_engine.analyze_dependencies(
            "Supply of CPVC pipes for potable water",
            "IS 15778 : 2007"
        )
        for dep in dep_rep.all_dependencies:
            self.assertIn(dep.provenance, ["VERIFIED", "CURATED"])
            self.assertNotEqual(dep.provenance, "UNKNOWN")

    # 20. Human review remains required where evidence is insufficient
    def test_20_human_review_required_where_evidence_insufficient(self):
        """When gaps are detected or candidate is unverified, human_review_required must be True."""
        req = Requirement(
            requirement_id="REQ-REVIEW",
            requirement_text="Providing, laying and jointing of concrete pipes in deep trenches",
            category="civil"
        )
        res = self.recommender.recommend_for_requirement(req)
        self.assertTrue(res.human_review_required)


if __name__ == "__main__":
    unittest.main()
