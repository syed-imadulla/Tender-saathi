"""
Module: tests/test_milestone10_dependencies.py
Purpose: Test suite for Milestone 10 Priority 1: Standards Dependency Intelligence.

Verifies:
1. Verified reference is preserved.
2. Supersession is preserved.
3. Code-of-practice relationship is preserved.
4. Unsupported relationship is not created (no title/domain/keyword hallucinations).
5. Provenance is preserved (cannot be upgraded by semantic similarity).
6. RELATED does not equal APPLICABLE.
7. Graph traversal is deterministic.
8. Depth limit is strictly enforced.
"""

import unittest
from src.graph import StandardsGraph, StandardRelationship
from src.dependencies import StandardsDependencyEngine, DependencyItem
from src.recommend import StandardsRecommender
from src.extract import Requirement


class TestMilestone10Dependencies(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.graph = StandardsGraph()
        cls.dep_engine = StandardsDependencyEngine(cls.graph)
        cls.recommender = StandardsRecommender(retrieval_mode="hybrid")

    # 1. Verified reference is preserved
    def test_01_verified_reference_preservation(self):
        """IS 15000:2024 must have verified normative reference to IS 2491:2024."""
        rels = self.graph.get_direct_relationships("IS 15000")
        target_stds = [r.target_standard for r in rels]
        self.assertTrue(any("2491" in t for t in target_stds), f"IS 2491 not found in {target_stds}")
        
        # Check provenance
        matching = [r for r in rels if "2491" in r.target_standard]
        self.assertEqual(matching[0].provenance, "VERIFIED")
        self.assertIn(matching[0].relationship_type, ["REFERENCES", "NORMATIVE_REFERENCE"])

    # 2. Supersession is preserved
    def test_02_supersession_preservation(self):
        """IS/ISO 10434:2020 must explicitly supersede IS 10611:1983."""
        rels = self.graph.get_direct_relationships("IS/ISO 10434")
        supersedes_rels = [r for r in rels if r.relationship_type == "SUPERSEDES"]
        self.assertTrue(len(supersedes_rels) > 0)
        self.assertTrue(any("10611" in r.target_standard for r in supersedes_rels))
        self.assertEqual(supersedes_rels[0].provenance, "VERIFIED")

    # 3. Code-of-practice relationship is preserved
    def test_03_code_of_practice_preservation(self):
        """IS 783:1985 must be identified as code of practice for IS 458."""
        rels = self.graph.get_direct_relationships("IS 783")
        cop_rels = [r for r in rels if r.relationship_type in ["CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"]]
        self.assertTrue(len(cop_rels) > 0)
        self.assertTrue(any("458" in r.target_standard for r in cop_rels))
        self.assertEqual(cop_rels[0].provenance, "VERIFIED")

    # 4. Unsupported relationship is not created
    def test_04_unsupported_relationship_not_created(self):
        """
        Two standards with similar keywords or same domain (e.g. valve vs crane or random valve)
        MUST NOT have an edge if no authoritative evidence exists.
        """
        # Test IS 778 (valves) against IS 15778 (CPVC pipes)
        rels_778 = self.graph.get_direct_relationships("IS 778")
        target_nums_778 = [r.target_standard for r in rels_778]
        self.assertFalse(any("15778" in t for t in target_nums_778), "Fake edge created between unrelated standards!")

        # Crane query / nonsense standard
        rels_crane = self.graph.get_direct_relationships("IS 99999")
        self.assertEqual(len(rels_crane), 0)

    # 5. Provenance is preserved (cannot be upgraded by semantic similarity)
    def test_05_provenance_preserved(self):
        """Curated relationships remain CURATED, Inferred remain INFERRED; cannot be upgraded."""
        rels_cpvc = self.graph.get_direct_relationships("IS 15778")
        test_rels = [r for r in rels_cpvc if "12235" in r.target_standard]
        if test_rels:
            self.assertIn(test_rels[0].provenance, ["CURATED", "VERIFIED"])
            self.assertNotEqual(test_rels[0].provenance, "FABRICATED")

    # 6. RELATED does not equal APPLICABLE
    def test_06_related_does_not_equal_applicable(self):
        """
        A dependency discovered in the graph must NOT be automatically declared
        the primary applicable standard for the tender.
        """
        req = Requirement(
            requirement_id="REQ-TEST",
            requirement_text="Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for potable water supply",
            category="plumbing"
        )
        rec_res = self.recommender.recommend_for_requirement(req)
        
        # Primary candidate standard must be the product standard IS 15778
        self.assertIn("15778", rec_res.candidate_standard)
        # Dependencies must be placed into dependencies list, NOT overriding candidate_standard
        self.assertIsNotNone(rec_res.dependencies)
        dep_numbers = [d["standard_number"] for d in rec_res.dependencies]
        self.assertNotIn(rec_res.candidate_standard, dep_numbers)

    # 7. Graph traversal is deterministic
    def test_07_graph_traversal_deterministic(self):
        """Repeated graph traversal must return identical relationships in identical order."""
        run1 = self.graph.get_direct_relationships("IS 15778")
        run2 = self.graph.get_direct_relationships("IS 15778")
        self.assertEqual(len(run1), len(run2))
        for r1, r2 in zip(run1, run2):
            self.assertEqual(r1.source_standard, r2.source_standard)
            self.assertEqual(r1.target_standard, r2.target_standard)
            self.assertEqual(r1.relationship_type, r2.relationship_type)

    # 8. Depth limit is strictly enforced
    def test_08_depth_limit_enforced(self):
        """Depth != 1 must raise ValueError to prevent runaway recursive traversal."""
        with self.assertRaises(ValueError):
            self.graph.get_direct_relationships("IS 15778", depth=3)


if __name__ == "__main__":
    unittest.main()
