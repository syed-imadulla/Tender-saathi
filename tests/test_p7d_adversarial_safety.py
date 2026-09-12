"""
Priority 7D — Adversarial Safety, False-Positive Resistance & Trust Boundary Audit Test Suite
TenderSaathi (SIH26108)

Tests system resilience under adversarial stress, false-positive resistance,
and adherence to the golden principle:
ABSTENTION > UNSUPPORTED CONFIDENCE
"""

import unittest
import sqlite3
import json
from api.server import app, are_standards_equivalent
from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender
from src.extract import Requirement
from src.audit import TenderAuditEngine


class TestPriority7DAdversarialSafety(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.db = StandardsDatabase()
        cls.rec = StandardsRecommender(db=cls.db, retrieval_mode="hybrid+rerank")
        cls.auditor = TenderAuditEngine()

    # 1. Substring collision safety
    def test_01_substring_collision_safety(self):
        """1. Substring collisions: IS 778 vs IS 15778, IS 694 vs IS 9694 must NOT be treated as equivalent."""
        self.assertFalse(are_standards_equivalent("IS 778", "IS 15778"))
        self.assertFalse(are_standards_equivalent("IS 15778", "IS 778"))
        self.assertFalse(are_standards_equivalent("IS 694", "IS 9694"))
        self.assertFalse(are_standards_equivalent("IS 9694", "IS 694"))
        self.assertFalse(are_standards_equivalent("IS 1180", "IS 1180 Part 1"))
        self.assertFalse(are_standards_equivalent("IS 7098 Part 1", "IS 7098 Part 2"))

    # 2. Canonical identity exactness
    def test_02_canonical_identity_exactness(self):
        """2. Exact canonical matches with differing format must equate; non-canonical must not."""
        self.assertTrue(are_standards_equivalent("IS 15778 : 2007", "IS 15778"))
        self.assertTrue(are_standards_equivalent("IS 1786 : 2008", "IS 1786"))
        self.assertTrue(are_standards_equivalent("IS 7098 (Part 2) : 2011", "IS 7098-Part-2"))
        self.assertFalse(are_standards_equivalent("IS 10611", "IS/ISO 10434"))

    # 3. Provenance separation
    def test_03_provenance_separation(self):
        """3. Provenance must not conflate CURATED with OFFICIAL_PRIMARY."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply of chlorinated polyvinyl chloride (CPVC) pipes for potable water."
        })
        self.assertEqual(resp.status_code, 200)
        req = resp.get_json()["requirements"][0]
        # CPVC is CURATED, source is BIS Standards Catalogue
        self.assertIn(req["provenance"], ["CURATED", "VERIFIED"])
        # Source must be clearly identified
        self.assertTrue(bool(req.get("source")))
        # Provenance must never be artificially inflated to OFFICIAL_PRIMARY
        self.assertNotEqual(req["provenance"], "OFFICIAL_PRIMARY")

    # 4. Evidence strength semantics
    def test_04_evidence_strength_semantics(self):
        """4. Evidence strength must be STRONG only for explicit citations; MODERATE for scope matches; NONE for abstentions."""
        # A. Explicit citation -> STRONG
        resp_cite = self.client.post("/api/analyze/text", json={
            "text": "Supply and installation of CPVC pipes conforming to IS 15778."
        })
        req_cite = resp_cite.get_json()["requirements"][0]
        self.assertEqual(req_cite["evidence_strength"], "STRONG")

        # B. Uncited scope match -> MODERATE
        resp_scope = self.client.post("/api/analyze/text", json={
            "text": "Supply of CPVC pipes for domestic water plumbing."
        })
        req_scope = resp_scope.get_json()["requirements"][0]
        self.assertEqual(req_scope["evidence_strength"], "MODERATE")

        # C. Abstention -> NONE
        resp_none = self.client.post("/api/analyze/text", json={
            "text": "Procurement of office stationery, staplers, ballpoint pens, and paper pads."
        })
        req_none = resp_none.get_json()["requirements"][0]
        self.assertEqual(req_none["evidence_strength"], "NONE")

    # 5. Fabricated evidence prevention
    def test_05_fabricated_evidence_prevention(self):
        """5. When candidate is null or abstained, evidence quote must NEVER be fabricated or mismatched."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Procurement of fresh organic vegetables and cafeteria catering services."
        })
        req = resp.get_json()["requirements"][0]
        self.assertIsNone(req["candidate_standard"])
        self.assertIsNone(req["evidence_standard"])
        self.assertNotIn("IS ", req["evidence"])
        self.assertIn("could not establish a sufficiently supported Indian Standard", req["evidence"])
        self.assertIn("No reliable Indian Standard match found", req["why_it_matches"])

    # 6. Ambiguity abstention safety
    def test_06_ambiguity_abstention_safety(self):
        """6. When requirement is ambiguous across viable standards, it must abstain rather than guess."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Installation of high-voltage transmission cable connection."
        })
        req = resp.get_json()["requirements"][0]
        if req["ambiguity_state"] == "AMBIGUOUS":
            self.assertIsNone(req["candidate_standard"])
            self.assertIsNone(req["evidence_standard"])
            self.assertTrue(req["human_review_required"])

    # 7. Incomplete requirement abstention
    def test_07_incomplete_requirement_abstention(self):
        """7. Vague engineering scopes must trigger INCOMPLETE or REVIEW_REQUIRED with missing parameters."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Annual maintenance of water supply pumps and motors."
        })
        req = resp.get_json()["requirements"][0]
        self.assertIn(req["ambiguity_state"], ["INCOMPLETE", "REVIEW_REQUIRED", "AMBIGUOUS"])
        self.assertTrue(req["human_review_required"])
        # Missing parameters must be identified
        self.assertTrue(len(req.get("missing_parameters", [])) > 0)

    # 8. No-match truthful wording
    def test_08_no_match_truthful_wording(self):
        """8. Irrelevant inputs must state no match found in catalogue, not that no standard exists."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply of ergonomic executive conference chairs."
        })
        req = resp.get_json()["requirements"][0]
        self.assertEqual(req["ambiguity_state"], "NO_RELIABLE_MATCH")
        self.assertIsNone(req["candidate_standard"])
        self.assertNotIn("No Indian Standard exists", req["why_it_matches"])
        self.assertIn("No reliable Indian Standard match found in the available catalogue", req["why_it_matches"])

    # 9. Lifecycle status preservation
    def test_09_lifecycle_status_preservation(self):
        """9. Superseded standard must retain original citation as superseded, never silently upgraded."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Procurement of bolted bonnet steel gate valves conforming to IS 10611 : 1983."
        })
        req = resp.get_json()["requirements"][0]
        # Old citation is preserved in superseded_citation
        self.assertIn("IS 10611", req.get("superseded_citation", ""))
        self.assertIsNotNone(req.get("successor_standard"))
        self.assertEqual(req["successor_standard"], "IS/ISO 10434 : 2020")

    # 10. Successor standard preservation
    def test_10_successor_standard_preservation(self):
        """10. Superseded standard successor must identify modern active replacement standard."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Procurement of bolted bonnet steel gate valves conforming to IS 10611 : 1983."
        })
        req = resp.get_json()["requirements"][0]
        self.assertEqual(req["candidate_standard"], "IS/ISO 10434 : 2020")
        self.assertEqual(req["successor_standard"], "IS/ISO 10434 : 2020")
        self.assertIn("IS 10611", req["superseded_citation"])

    # 11. Regulatory uncertainty preservation
    def test_11_regulatory_uncertainty_preservation(self):
        """11. Standard existence alone must not infer mandatory statutory status."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Installation of ceramic glazed tiles conforming to IS 15622."
        })
        req = resp.get_json()["requirements"][0]
        reg = req.get("regulatory", {})
        # Tiles do not have mandatory QCO in core registry
        cert = reg.get("certification", {}) if isinstance(reg, dict) else {}
        self.assertIn(cert.get("status"), ["NOT_IDENTIFIED", "NOT_APPLICABLE", "UNKNOWN"])
        self.assertNotEqual(cert.get("status"), "APPLICABLE")

    # 12. Human review preservation under uncertainty
    def test_12_human_review_preservation(self):
        """12. Human review flag must stay True whenever ambiguity, missing parameters, or supersedence exists."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply and replacement of valves in cooling water line."
        })
        req = resp.get_json()["requirements"][0]
        self.assertTrue(req["human_review_required"])
        self.assertTrue(len(req.get("why_flagged", "")) > 0)

    # 13. Product vs installation separation
    def test_13_product_vs_installation_separation(self):
        """13. Requirement with product + installation must select product as candidate, not installation code."""
        r = Requirement(
            requirement_id="REQ-P7D-PROD",
            requirement_text="Supply and laying of CPVC pipes for internal water distribution network.",
            category="civil"
        )
        res = self.rec.recommend_for_requirement(r)
        self.assertEqual(res.candidate_standard, "IS 15778 : 2007")
        self.assertIn("Chlorinated Polyvinyl Chloride", res.title)
        # Installation code IS 7634 / IS 783 should appear in dependencies, not as primary candidate
        dep_numbers = [d.get("standard_number") for d in res.dependencies]
        self.assertNotIn("IS 15778", dep_numbers)

    # 14. Dependency role distinction
    def test_14_dependency_role_distinction(self):
        """14. Dependencies must preserve explicit relationship roles (INSTALLATION, CODE_OF_PRACTICE, TEST_METHOD)."""
        r = Requirement(
            requirement_id="REQ-P7D-DEP",
            requirement_text="Supply and installation of CPVC pipes for internal plumbing.",
            category="civil"
        )
        res = self.rec.recommend_for_requirement(r)
        roles = {d.get("relationship_type") for d in res.dependencies}
        self.assertTrue(len(roles) > 0)
        for d in res.dependencies:
            self.assertIn(d.get("relationship_type"), [
                "INSTALLATION_STANDARD", "CODE_OF_PRACTICE", "TEST_METHOD",
                "NORMATIVE_REFERENCE", "ALLIED_STANDARD"
            ])

    # 15. Readiness verdict integrity
    def test_15_readiness_verdict_integrity(self):
        """15. Overall publication readiness must honestly reflect requirement-level risk."""
        # Tender with missing parameters should be REVIEW_REQUIRED or INSUFFICIENT_EVIDENCE
        resp = self.client.post("/api/analyze/text", json={
            "text": "Annual maintenance of water supply pumps and electrical connections."
        })
        data = resp.get_json()
        self.assertIn(data["readiness"], ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE"])
        self.assertTrue(len(data.get("readiness_reasons", [])) > 0)


if __name__ == "__main__":
    unittest.main()
