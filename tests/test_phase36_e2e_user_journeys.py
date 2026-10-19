"""
tests/test_phase36_e2e_user_journeys.py — Phase 36: 10 Canonical User Journeys & SIH Demo Hardening

Verifies end-to-end user journeys through the API and backend engines:
1. Valid engineering tender with supported requirements (IS 15778 CPVC pipe).
2. Multi-requirement tender (pipes, cables, transformers cleanly decomposed).
3. Catalogue-discovered standard lacking normative passages (IS 10245 breathing apparatus).
4. Withdrawn or superseded standard (IS 10611 superseded by IS 14846).
5. Underspecified technical requirement (water pumps without flow/head).
6. Conflicting specification (HDPE pipe for 250°C superheated steam).
7. Commercial / non-standardized requirement (EMD, bank guarantee, copier paper).
8. Requirement referencing another standard via normative clause (IS 456 referencing IS 1786).
9. Digital PDF tender upload via /api/analyze/pdf (PyMuPDF extraction with HTTP 200).
10. Mixed tender containing supported engineering clauses and unsupported commercial terms.
And export sanity across Markdown, JSON, and CSV.
"""

import io
import json
import unittest
from pathlib import Path

from api.server import app
from src.recommend import StandardsRecommender
from src.graph import StandardsGraph
from src.corpus.storage import CorpusStorage


class TestPhase36EndToEndUserJourneys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.recommender = StandardsRecommender()
        cls.graph = StandardsGraph()
        cls.corpus = CorpusStorage()

    # -------------------------------------------------------------------------
    # Journey 1: Valid engineering tender with supported requirements
    # -------------------------------------------------------------------------
    def test_journey_1_valid_engineering_tender(self):
        """Journey 1: Valid engineering tender with supported requirements."""
        payload = {
            "text": "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for domestic hot and cold water distribution conforming to IS 15778."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("requirements", data)
        self.assertGreaterEqual(len(data["requirements"]), 1)
        r0 = data["requirements"][0]

        # Validated candidate standard
        self.assertIsNotNone(r0["candidate_standard"])
        self.assertIn("15778", r0["candidate_standard"])
        self.assertEqual(r0["candidate_standard"], r0["evidence_standard"])
        self.assertIn(r0["ambiguity_state"], ("CLEAR", "REVIEW_REQUIRED"))

        # Invariant: Evidence tier is properly set
        self.assertIn(r0["evidence_tier"], ("CLAUSE_VERIFIED", "CORPUS_SUPPORTED", "CATALOGUE_DISCOVERED", "BSB_CURATED", "BSB_VERIFIED"))

    # -------------------------------------------------------------------------
    # Journey 2: Multi-requirement tender
    # -------------------------------------------------------------------------
    def test_journey_2_multi_requirement_tender(self):
        """Journey 2: Multi-requirement tender cleanly decomposed into separate requirements."""
        payload = {
            "text": (
                "Package A: Supply of Chlorinated Polyvinyl Chloride (CPVC) pipes for plumbing installations.\n"
                "Package B: Supply of PVC insulated copper electrical cables for internal electrical wiring.\n"
                "Package C: Supply of outdoor oil immersed distribution transformers 11kV."
            )
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 2, "Multi-package tender must be decomposed into multiple requirements")

        # Each requirement must maintain separate candidate standards without mutual contamination
        candidates = [r["candidate_standard"] for r in reqs if r["candidate_standard"]]
        self.assertGreaterEqual(len(candidates), 2)
        # Distinct standards should be matched
        self.assertEqual(len(candidates), len(set(candidates)))

    # -------------------------------------------------------------------------
    # Journey 3: Catalogue-discovered standard lacking normative passages
    # -------------------------------------------------------------------------
    def test_journey_3_catalogue_discovered_lacking_normative_passages(self):
        """Journey 3: Catalogue-discovered standard lacking normative passages (IS 10245)."""
        payload = {
            "text": "Procurement of self-contained open-circuit compressed air breathing apparatus conforming to IS 10245."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 1)
        r0 = reqs[0]

        # Standard is found in national catalogue
        if r0["candidate_standard"]:
            self.assertIn("10245", r0["candidate_standard"])
            # Invariant: Must NOT be CLAUSE_VERIFIED because IS 10245 lacks statutory corpus passages
            self.assertNotEqual(r0["evidence_tier"], "CLAUSE_VERIFIED")
            # Must require human review or flag catalogue-discovered tier
            self.assertTrue(r0["human_review_required"] or r0["evidence_tier"] == "CATALOGUE_DISCOVERED")

    # -------------------------------------------------------------------------
    # Journey 4: Withdrawn or superseded standard
    # -------------------------------------------------------------------------
    def test_journey_4_withdrawn_or_superseded_standard(self):
        """Journey 4: Withdrawn or superseded standard (IS 10611 superseded by IS 14846)."""
        payload = {
            "text": "Procurement of sluice valves conforming to IS 10611 for underground water supply."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 1)
        r0 = reqs[0]

        # Either flagged as superseded / withdrawn or redirected to IS 14846 with review flag
        self.assertTrue(r0["human_review_required"])
        summary = data["summary"]
        has_lifecycle_signal = (
            summary.get("superseded_count", 0) >= 1
            or summary.get("withdrawn_count", 0) >= 1
            or summary.get("lifecycle_concern_count", 0) >= 1
            or len(r0.get("lifecycle_warnings", [])) >= 1
        )
        self.assertTrue(has_lifecycle_signal)

    # -------------------------------------------------------------------------
    # Journey 5: Underspecified technical requirement
    # -------------------------------------------------------------------------
    def test_journey_5_underspecified_technical_requirement(self):
        """Journey 5: Underspecified technical requirement (water pumps without flow/head)."""
        payload = {
            "text": "Procurement of water pumps for municipal civil work."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 1)
        r0 = reqs[0]

        # Ambiguous specification must trigger review and ambiguity state
        self.assertIn(r0["ambiguity_state"], ("AMBIGUOUS", "INCOMPLETE", "REVIEW_REQUIRED"))
        self.assertTrue(r0["human_review_required"])

    # -------------------------------------------------------------------------
    # Journey 6: Conflicting specification
    # -------------------------------------------------------------------------
    def test_journey_6_conflicting_specification(self):
        """Journey 6: Conflicting specification (HDPE pipe for 250°C superheated steam)."""
        payload = {
            "text": "Supply of High Density Polyethylene (HDPE) pipes for conveyance of 250°C superheated high-pressure steam."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 1)
        r0 = reqs[0]

        # High risk, conflicting ambiguity state, or human review required
        self.assertTrue(
            r0["ambiguity_state"] in ("CONFLICTING", "REVIEW_REQUIRED", "AMBIGUOUS")
            or r0["risk_level"] in ("HIGH", "CRITICAL")
            or r0["human_review_required"]
        )

    # -------------------------------------------------------------------------
    # Journey 7: Commercial or non-standardized requirement
    # -------------------------------------------------------------------------
    def test_journey_7_commercial_non_standardized_clause(self):
        """Journey 7: Commercial or non-standardized requirement (EMD, bank guarantee, copier paper)."""
        payload = {
            "text": (
                "The bidder must submit an Earnest Money Deposit (EMD) of INR 2,00,000 via RTGS. "
                "A mobilization advance of 10% shall be released against a bank guarantee. "
                "General office stationery including A4 copier paper must be delivered within 7 days."
            )
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        # Must not fabricate an engineering standard recommendation for pure commercial/financial terms
        for r in reqs:
            cand = r.get("candidate_standard")
            if cand:
                self.assertNotIn("EMD", cand)
                self.assertNotIn("Mobilization", cand)
                self.assertNotIn("Advance", cand)
                # If matched to paper or stationery, it must require review or have low confidence
                self.assertTrue(r["human_review_required"] or r.get("confidence") in ("Low", "Medium"))

    # -------------------------------------------------------------------------
    # Journey 8: Normative cross-reference traversal
    # -------------------------------------------------------------------------
    def test_journey_8_normative_cross_reference_traversal(self):
        """Journey 8: Requirement referencing another standard via normative clause (IS 456 referencing IS 1786)."""
        # Test traversal endpoint
        resp = self.client.get("/api/standards/IS%20456%20:%202000/traversal?depth=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertEqual(data["start_standard"], "IS 456 : 2000")
        self.assertGreater(data["count"], 0)
        targets = [r["target_standard"] for r in data["traversed_references"]]
        self.assertTrue(any("1786" in t for t in targets), f"IS 1786 should be referenced by IS 456, got {targets}")

        # Check non-elevation invariant: Traversal API items preserve provenance and hop depth
        for ref in data["traversed_references"]:
            self.assertIn(ref["provenance"], ("VERIFIED", "CURATED", "GRAPH_TRAVERSAL"))
            self.assertIn(ref["hop_depth"], (1, 2))
            self.assertIn("target_standard", ref)
            self.assertIn("originating_evidence", ref)

    # -------------------------------------------------------------------------
    # Journey 9: Digital PDF tender upload
    # -------------------------------------------------------------------------
    def test_journey_9_pdf_tender_upload(self):
        """Journey 9: Digital PDF tender upload via /api/analyze/pdf."""
        fixture_path = Path("tests/fixtures/sample_tender.pdf")
        self.assertTrue(fixture_path.exists(), "Sample tender PDF fixture missing")

        with open(fixture_path, "rb") as f:
            pdf_bytes = f.read()

        resp = self.client.post(
            "/api/analyze/pdf",
            data={"file": (io.BytesIO(pdf_bytes), "sample_tender.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("tender", data)
        self.assertEqual(data["tender"]["source"], "sample_tender.pdf")
        self.assertIn("requirements", data)
        self.assertGreaterEqual(len(data["requirements"]), 1)
        self.assertIn("summary", data)

    # -------------------------------------------------------------------------
    # Journey 10: Mixed tender
    # -------------------------------------------------------------------------
    def test_journey_10_mixed_tender(self):
        """Journey 10: Mixed tender with supported engineering and unsupported commercial clauses."""
        payload = {
            "text": (
                "Section 1: Technical Specifications\n"
                "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for hot and cold water plumbing conforming to IS 15778.\n\n"
                "Section 2: Commercial Terms\n"
                "20% advance payment against bank guarantee. Penalty of 0.5% per week of delay up to a maximum of 10%."
            )
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 2)

        # Technical requirement mapped to IS 15778
        cpvc_matches = [r for r in reqs if r.get("candidate_standard") and "15778" in r["candidate_standard"]]
        self.assertGreaterEqual(len(cpvc_matches), 1)

        # Commercial requirement has safe abstention / review required
        commercial_reqs = [r for r in reqs if "bank guarantee" in r["text"].lower() or "commercial" in r.get("package_name", "").lower()]
        if commercial_reqs:
            comm = commercial_reqs[0]
            self.assertTrue(comm.get("candidate_standard") is None or comm.get("human_review_required"))


class TestPhase36ExportSanity(unittest.TestCase):
    """Verify Markdown, JSON, and CSV report export endpoints."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_export_all_formats(self):
        # 1. Analyze text first to seed the cache
        payload = {
            "text": "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes conforming to IS 15778."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        tender_id = data["tender"]["id"]

        # 2. Markdown export
        resp_md = self.client.get(f"/api/report/{tender_id}/markdown")
        self.assertEqual(resp_md.status_code, 200)
        self.assertIn("text/markdown", resp_md.content_type)
        md_text = resp_md.data.decode("utf-8")
        self.assertIn("# TenderSaathi", md_text)
        self.assertIn("IS 15778", md_text)

        # 3. JSON export
        resp_json = self.client.get(f"/api/report/{tender_id}/json")
        self.assertEqual(resp_json.status_code, 200)
        self.assertIn("application/json", resp_json.content_type)
        json_data = json.loads(resp_json.data.decode("utf-8"))
        self.assertIn("requirements", json_data)
        self.assertIn("executive_summary", json_data)

        # 4. CSV export
        resp_csv = self.client.get(f"/api/report/{tender_id}/csv")
        self.assertEqual(resp_csv.status_code, 200)
        self.assertIn("text/csv", resp_csv.content_type)
        csv_text = resp_csv.data.decode("utf-8")
        self.assertIn("Requirement ID", csv_text)
        self.assertIn("IS 15778", csv_text)
