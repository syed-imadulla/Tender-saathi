"""
tests/test_p7b_api_ui_contract.py

Priority 7B — API/UI Contract, Evidence Display & Decision-Safety Automated Test Suite.
Validates that:
1. All API endpoints (/api/health, /api/analyze/text, /api/analyze/pdf, /api/analyze/sample, /api/report)
   preserve backend decision truth without omission or modification.
2. Invariants 1-8 hold unconditionally across serialization.
3. Representative cases (Clear Product, Clear Installation, Ambiguous, Incomplete, No Reliable Match, Lifecycle)
   behave predictably and safely.
4. Error and null states fail safely without exposing unhandled exceptions or manufacturing false evidence.
5. Standard equivalence avoids substring matching defects (e.g. IS 15778 vs IS 778).
"""

import os
import unittest
import json
from api.server import app, are_standards_equivalent


class TestPriority7BApiUiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    # -----------------------------------------------------------------------
    # Endpoint Inventory & Schema Validation
    # -----------------------------------------------------------------------

    def test_01_health_endpoint(self):
        """GET /api/health returns 200 with status ok and active service name."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "TenderSaathi API")
        self.assertIn("timestamp", data)

    def test_02_analyze_text_schema_integrity(self):
        """POST /api/analyze/text returns complete schema matching TypeScript AnalysisResult."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply and installation of chlorinated polyvinyl chloride (CPVC) pipes conforming to IS 15778."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        # Top-level required keys
        self.assertIn("tender", data)
        self.assertIn("summary", data)
        self.assertIn("readiness", data)
        self.assertIn("readiness_reasons", data)
        self.assertIn("sections", data)
        self.assertIn("requirements", data)
        self.assertIn("metadata", data)

        # Tender block
        tender = data["tender"]
        self.assertIn("id", tender)
        self.assertIn("source", tender)
        self.assertIn("timestamp", tender)

        # Summary block
        summary = data["summary"]
        self.assertIn("requirements_analyzed", summary)
        self.assertIn("ambiguity_summary", summary)
        self.assertIn("evidence_distribution", summary)
        self.assertIn("risk_distribution", summary)

        # Requirements block
        reqs = data["requirements"]
        self.assertTrue(len(reqs) >= 1)
        r0 = reqs[0]
        self.assertIn("id", r0)
        self.assertIn("text", r0)
        self.assertIn("candidate_standard", r0)
        self.assertIn("evidence_standard", r0)
        self.assertIn("why_it_matches", r0)
        self.assertIn("ambiguity_state", r0)
        self.assertIn("human_review_required", r0)
        self.assertIn("risk_level", r0)
        self.assertIn("scores", r0)

    # -----------------------------------------------------------------------
    # Invariant Tests (Invariants 1-8)
    # -----------------------------------------------------------------------

    def test_03_invariant_1_candidate_equals_evidence_when_present(self):
        """INVARIANT 1: If candidate_standard != null -> candidate_standard == evidence_standard."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "25 mm nominal diameter CPVC plumbing pipe for domestic hot and cold water distribution."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        reqs = data["requirements"]
        self.assertTrue(len(reqs) >= 1)
        for r in reqs:
            if r["candidate_standard"] is not None:
                self.assertEqual(r["candidate_standard"], r["evidence_standard"])

    def test_04_invariant_2_evidence_null_when_candidate_null(self):
        """INVARIANT 2: If candidate_standard == null -> evidence_standard == null."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "General maintenance of municipal premises and cleaning."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        reqs = data["requirements"]
        for r in reqs:
            if r["candidate_standard"] is None:
                self.assertIsNone(r["evidence_standard"])

    def test_05_invariant_3_ambiguous_state_contract(self):
        """INVARIANT 3: If ambiguity_state == AMBIGUOUS -> candidate=None, evidence=None, human_review=True."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Overhaul, maintenance and replacement of valves in cooling water line."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        reqs = data["requirements"]
        ambiguous_reqs = [r for r in reqs if r.get("ambiguity_state") == "AMBIGUOUS"]
        self.assertTrue(len(ambiguous_reqs) >= 1)
        for r in ambiguous_reqs:
            self.assertIsNone(r["candidate_standard"])
            self.assertIsNone(r["evidence_standard"])
            self.assertTrue(r["human_review_required"])
            self.assertTrue(len(r.get("competing_interpretations", [])) >= 2)

    def test_06_invariant_4_incomplete_state_contract(self):
        """INVARIANT 4: If ambiguity_state == INCOMPLETE -> human_review_required == True."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Annual Rate Contract for Execution of Mechanical Maintenance Works including Pumps."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        reqs = data["requirements"]
        for r in reqs:
            if r.get("ambiguity_state") == "INCOMPLETE":
                self.assertTrue(r["human_review_required"])

    def test_07_invariant_5_no_reliable_match_contract(self):
        """INVARIANT 5: If ambiguity_state == NO_RELIABLE_MATCH -> candidate_standard == null."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply of catering lunch boxes and mineral water for office staff meeting."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        reqs = data["requirements"]
        for r in reqs:
            if r.get("ambiguity_state") == "NO_RELIABLE_MATCH":
                self.assertIsNone(r["candidate_standard"])
                self.assertIsNone(r["evidence_standard"])

    def test_08_invariant_6_no_manufactured_evidence(self):
        """INVARIANT 6: Abstaining requirements must not display candidate-specific evidence."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Laying of sewerage pipeline without pipe specification."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        reqs = data["requirements"]
        for r in reqs:
            if r["candidate_standard"] is None:
                self.assertIsNone(r["evidence_standard"])
                self.assertIn("no reliable", r["why_it_matches"].lower())

    def test_09_invariant_7_human_review_state_preservation(self):
        """INVARIANT 7: human_review_required boolean is preserved across serialization."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Procurement of valves without pressure rating or body material."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIsInstance(r0["human_review_required"], bool)
        self.assertTrue(r0["human_review_required"])

    def test_10_invariant_8_readiness_state_integrity(self):
        """INVARIANT 8: Overall publication readiness is one of the 3 canonical states and includes reasons."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply and laying of CPVC pipes."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        readiness = data["readiness"]
        self.assertIn(readiness, ["READY_FOR_REVIEW", "REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE"])
        self.assertIsInstance(data["readiness_reasons"], list)

    # -----------------------------------------------------------------------
    # Representative Cases (Cases A - F)
    # -----------------------------------------------------------------------

    def test_11_case_a_clear_product(self):
        """CASE A: Clear Product (CPVC pipe -> IS 15778)."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Chlorinated polyvinyl chloride CPVC pipes for potable water distribution in building."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIsNotNone(r0["candidate_standard"])
        self.assertIn("15778", r0["candidate_standard"])
        self.assertEqual(r0["candidate_standard"], r0["evidence_standard"])
        self.assertIn(r0["ambiguity_state"], ["CLEAR", "REVIEW_REQUIRED"])

    def test_12_case_b_clear_installation(self):
        """CASE B: Clear Installation (Electrical wiring installation -> IS 732)."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Installation of electrical wiring and safety equipment in office building."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIsNotNone(r0["candidate_standard"])
        self.assertIn("732", r0["candidate_standard"])
        self.assertEqual(r0["candidate_standard"], r0["evidence_standard"])

    def test_13_case_c_ambiguous(self):
        """CASE C: Ambiguous (Sewerage pipeline without material specification)."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Electromechanical Works and Sewerage Pipeline works from Collection Chamber to STP."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertEqual(r0["ambiguity_state"], "AMBIGUOUS")
        self.assertIsNone(r0["candidate_standard"])
        self.assertIsNone(r0["evidence_standard"])
        self.assertTrue(r0["human_review_required"])

    def test_14_case_d_incomplete(self):
        """CASE D: Incomplete (Real tender PDF upload where parameters are missing -> INCOMPLETE)."""
        pdf_path = "tenders/raw/eProcurement System Government of India3.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post(
                "/api/analyze/pdf",
                data={"file": (f, "eProcurement System Government of India3.pdf")},
                content_type="multipart/form-data"
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertEqual(r0["ambiguity_state"], "INCOMPLETE")
        self.assertIsNone(r0["candidate_standard"])
        self.assertIsNone(r0["evidence_standard"])
        self.assertTrue(r0["human_review_required"])

    def test_15_case_e_no_reliable_match(self):
        """CASE E: No Reliable Match (Nonsense text)."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supercalifragilisticexpialidocious lorem ipsum dolor sit amet."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIsNone(r0["candidate_standard"])
        self.assertIsNone(r0["evidence_standard"])

    def test_16_case_f_lifecycle_review_superseded(self):
        """CASE F: Lifecycle Review (Superseded IS 10611 cited in text)."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Procurement of cast iron gate valves conforming to IS 10611."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIn("standards_to_update", data["sections"])
        self.assertTrue(
            r0.get("superseded_citation") == "IS 10611" or
            "superseded" in (r0.get("why_flagged") or "").lower() or
            r0.get("successor_standard") is not None
        )

    # -----------------------------------------------------------------------
    # Error Handling & Null States
    # -----------------------------------------------------------------------

    def test_17_error_handling_empty_text(self):
        """Empty text payload returns 400 with user-friendly error message."""
        resp = self.client.post("/api/analyze/text", json={"text": ""})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)

    def test_18_error_handling_unknown_sample(self):
        """Request for nonexistent sample returns 400."""
        resp = self.client.get("/api/analyze/sample/unknown_xyz")
        self.assertEqual(resp.status_code, 400)

    def test_19_error_handling_nonexistent_report(self):
        """Request for nonexistent report returns 404."""
        resp = self.client.get("/api/report/NONEXISTENT_TENDER_ID/json")
        self.assertEqual(resp.status_code, 404)

    # -----------------------------------------------------------------------
    # Evidence Display Safety & Substring Bug Prevention
    # -----------------------------------------------------------------------

    def test_20_substring_matching_bug_prevention(self):
        """are_standards_equivalent avoids substring false positives (e.g. IS 15778 vs IS 778)."""
        # Exact prefix match without year:
        self.assertTrue(are_standards_equivalent("IS 15778 : 2007", "IS 15778 : 2007"))
        self.assertTrue(are_standards_equivalent("IS 15778 : 2007", "IS 15778"))
        self.assertTrue(are_standards_equivalent("IS 778 : 1984", "IS 778"))

        # Substring false positives MUST be False:
        self.assertFalse(are_standards_equivalent("IS 15778 : 2007", "IS 778 : 1984"))
        self.assertFalse(are_standards_equivalent("IS 778 : 1984", "IS 15778 : 2007"))
        self.assertFalse(are_standards_equivalent("IS 1180 (Part 1) : 2014", "IS 1180"))
        self.assertFalse(are_standards_equivalent("IS 7098 (Part 2)", "IS 7098 (Part 1)"))


if __name__ == "__main__":
    unittest.main()
