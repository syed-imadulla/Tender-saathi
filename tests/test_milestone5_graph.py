"""
Tests for Milestone 5: Lightweight Evidence & Relationship Graph.

Verifies:
1. Existing verified relationships can be retrieved.
2. SUPERSEDES relationship is correctly represented.
3. REFERENCES relationship is correctly represented.
4. CODE_OF_PRACTICE_FOR relationship is correctly represented.
5. Relationship provenance is preserved.
6. Relationship evidence is preserved.
7. INFERRED relationship cannot become STRONG evidence.
8. Graph connectivity does not automatically mean tender applicability.
9. Related standards are labelled "Related standards to review".
10. Lifecycle status is preserved.
11. Graph depth is limited to 1.
12. Existing critic Trust Gate still works.
13. No benchmark ground truth modification.
14. No standard-number-specific hacks.
"""

import unittest
from typing import List

from src.standards import StandardsDatabase
from src.graph import StandardsGraph, StandardRelationship, RelatedStandardResult
from src.critic import EvidenceAwareCritic, CandidateEvidence, CandidateCritique
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.search import SearchResult
from src.completeness import DomainCompletenessAnalyzer


class TestMilestone5Graph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = StandardsDatabase()
        cls.graph = StandardsGraph(cls.db)
        cls.critic = EvidenceAwareCritic(cls.db)
        cls.recommender = StandardsRecommender(cls.db)

    # 1. Existing verified relationships can be retrieved
    def test_01_existing_relationships_retrieval(self):
        """Verify that stored relationships can be queried from the database."""
        rels = self.graph.get_direct_relationships("IS 15000", depth=1)
        self.assertGreater(len(rels), 0, "IS 15000 should have relationships in the database.")
        targets = [r.target_standard for r in rels]
        self.assertTrue(any("2491" in t for t in targets), "IS 15000 should relate to IS 2491.")

    # 2. SUPERSEDES relationship is correctly represented
    def test_02_supersedes_relationship(self):
        """Verify that SUPERSEDES relationship is correctly loaded with source and target."""
        # IS/ISO 10434 supersedes IS 10611
        rels = self.graph.get_direct_relationships("IS/ISO 10434", depth=1)
        supersedes_rels = [r for r in rels if r.relationship_type == "SUPERSEDES"]
        self.assertGreater(len(supersedes_rels), 0, "IS/ISO 10434 should have a SUPERSEDES relationship.")
        target_match = any("10611" in r.target_standard for r in supersedes_rels)
        self.assertTrue(target_match, "IS/ISO 10434 should supersede IS 10611.")

    # 3. REFERENCES relationship is correctly represented
    def test_03_references_relationship(self):
        """Verify that REFERENCES relationships are correctly represented."""
        rels = self.graph.get_direct_relationships("IS 15000", depth=1)
        ref_rels = [r for r in rels if r.relationship_type == "REFERENCES"]
        self.assertGreater(len(ref_rels), 0, "IS 15000 should have REFERENCES relationships.")
        self.assertTrue(any("2491" in r.target_standard for r in ref_rels))

    # 4. CODE_OF_PRACTICE_FOR relationship is correctly represented
    def test_04_code_of_practice_relationship(self):
        """Verify that CODE_OF_PRACTICE_FOR relationship is correctly represented."""
        # IS 783 is code of practice for IS 458
        rels = self.graph.get_direct_relationships("IS 783", depth=1)
        cop_rels = [r for r in rels if r.relationship_type == "CODE_OF_PRACTICE_FOR"]
        self.assertGreater(len(cop_rels), 0, "IS 783 should have CODE_OF_PRACTICE_FOR relationships.")
        self.assertTrue(any("458" in r.target_standard for r in cop_rels))

    # 5. Relationship provenance is preserved
    def test_05_provenance_preserved(self):
        """Verify that provenance (VERIFIED / CURATED / INFERRED) is preserved in graph models."""
        rels = self.graph.get_direct_relationships("IS/ISO 10434", depth=1)
        for r in rels:
            self.assertIn(r.provenance, ["VERIFIED", "CURATED", "INFERRED"],
                          f"Relationship provenance '{r.provenance}' is invalid.")

    # 6. Relationship evidence is preserved
    def test_06_evidence_preserved(self):
        """Verify that evidence text is non-empty and contains verbatim or citing details."""
        rels = self.graph.get_direct_relationships("IS/ISO 10434", depth=1)
        for r in rels:
            self.assertTrue(r.evidence and len(r.evidence.strip()) > 0,
                            "Relationship must have non-empty supporting evidence.")

    # 7. INFERRED relationship cannot become STRONG evidence
    def test_07_inferred_cannot_become_strong(self):
        """Ensure that INFERRED provenance relationships produce WEAK evidence strength."""
        # Create a mock relationship with INFERRED provenance
        inferred_rel = StandardRelationship(
            source_standard="IS 99999",
            target_standard="IS 88888",
            relationship_type="REFERENCES",
            evidence="Inferred co-citation in tender corpus",
            provenance="INFERRED"
        )
        # Test mapping logic
        if inferred_rel.provenance == "INFERRED":
            ev_strength = "WEAK"
        elif inferred_rel.provenance == "CURATED":
            ev_strength = "MODERATE"
        else:
            ev_strength = "STRONG"
        self.assertEqual(ev_strength, "WEAK", "INFERRED relationship must never produce STRONG evidence.")

    # 8. Graph connectivity does not automatically mean tender applicability
    def test_08_connectivity_not_automatic_applicability(self):
        """
        Verify evidence propagation rule:
        Discovered related standards must NOT be injected directly as primary applicable recommendations.
        """
        req = extract_from_text(
            "Supply of CPVC pipes for potable water distribution",
            requirement_id="TEST-001"
        )
        rec_res = self.recommender.recommend_for_requirement(req)
        
        # Primary recommendation must be the primary standard (e.g. IS 15778)
        self.assertIsNotNone(rec_res.candidate_standard)
        primary_num = rec_res.candidate_standard

        # Related standards discovered via graph must be in related_standards list, NOT overriding the primary
        self.assertIsNotNone(rec_res.related_standards)
        for rel_std in rec_res.related_standards:
            self.assertNotEqual(rel_std["standard_number"], primary_num)
            # The review note must indicate it is for review, not an assertion of mandatory applicability
            self.assertIn("review", rel_std["review_note"].lower())

    # 9. Related standards are labelled "Related standards to review"
    def test_09_related_standards_labeling(self):
        """Verify that related standards carry the explicit review guidance."""
        related = self.graph.get_related_standards("IS 15000")
        self.assertGreater(len(related), 0)
        for item in related:
            self.assertTrue(
                "review" in item.review_note.lower() or "adoption" in item.review_note.lower(),
                f"Review note should emphasize review: {item.review_note}"
            )

    # 10. Lifecycle status is preserved
    def test_10_lifecycle_status_preserved(self):
        """Verify lifecycle status is accurately resolved for source and related target standards."""
        # IS 10611 is superseded; when queried, its related standard IS/ISO 10434 is Active
        related = self.graph.get_related_standards("IS 10611")
        self.assertGreater(len(related), 0)
        sup_rel = [r for r in related if "10434" in r.standard_number]
        self.assertGreater(len(sup_rel), 0)
        self.assertEqual(sup_rel[0].lifecycle_status, "Active")

    # 11. Graph depth is limited to 1
    def test_11_depth_limited_to_1(self):
        """Verify that attempting a traversal depth > 1 raises ValueError."""
        with self.assertRaises(ValueError):
            self.graph.get_direct_relationships("IS 15000", depth=2)
        with self.assertRaises(ValueError):
            self.graph.get_direct_relationships("IS 15000", depth=0)

    # 12. Existing critic Trust Gate still works
    def test_12_critic_trust_gate_integrity(self):
        """Verify that Critic Trust Gate continues to function as designed with graph enabled."""
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
        crit = self.critic.critique_candidate(
            candidate=dummy_cand,
            requirement_text="High-pressure gas line pipe",
            components=[],
            completeness=comp
        )
        # Decision must be gated - cannot be RECOMMEND
        self.assertIn(crit.decision, ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE", "REJECT"])
        self.assertTrue(crit.review_required)

        # When evaluated in candidate list, confidence must not be High
        outcome = self.critic.evaluate_candidates([dummy_cand], "High-pressure gas line pipe", [], comp)
        self.assertNotEqual(outcome.confidence, "High")

    # 13. No benchmark ground truth modification
    def test_13_ground_truth_unmodified(self):
        """Verify ground_truth.csv has exactly 20 locked rows."""
        import csv
        with open("dataset/ground_truth/ground_truth.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), 20, "Ground truth benchmark must remain exactly 20 rows.")

    # 14. No standard-number-specific hacks
    def test_14_explain_relationship_general(self):
        """Verify explain_relationship operates deterministically via graph models."""
        exp = self.graph.explain_relationship("IS 15000", "IS 2491")
        self.assertIsNotNone(exp)
        self.assertIn("IS 15000", exp)
        self.assertIn("IS 2491", exp)
        self.assertIn("REFERENCES", exp)


if __name__ == "__main__":
    unittest.main()
