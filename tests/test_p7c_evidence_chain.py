"""
tests/test_p7c_evidence_chain.py

Priority 7C — Evidence Chain, Audit Trail & Decision Traceability Test Suite.
Verifies the end-to-end audit chain from original tender text to:
- Candidate standard & evidence standard identity
- Genuine provenance and source traceability
- Safe abstention without fabricated evidence
- Preservation of competing interpretations and missing parameters
- Lifecycle status, successor standard, and explicit superseded warnings
- Dependency role separation and regulatory truthfulness
"""

import unittest
from api.server import app, are_standards_equivalent
from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender
from src.extract import extract_from_text


class TestPriority7CEvidenceChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.db = StandardsDatabase()
        cls.recommender = StandardsRecommender(db=cls.db, retrieval_mode="hybrid+rerank")

    def test_01_recommendation_evidence_identity(self):
        """1. Recommendation -> evidence identity: candidate_standard == evidence_standard."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Chlorinated polyvinyl chloride CPVC pipes for potable water distribution."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIsNotNone(r0["candidate_standard"])
        self.assertEqual(r0["candidate_standard"], r0["evidence_standard"])
        self.assertTrue(are_standards_equivalent(r0["candidate_standard"], r0["evidence_standard"]))

    def test_02_candidate_evidence_provenance(self):
        """2. Candidate -> evidence provenance: Valid, non-blank provenance level is tracked."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply of XLPE insulated power cables for 11kV distribution."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIn(r0["provenance"], ["CURATED", "VERIFIED", "OFFICIAL_PRIMARY", "OFFICIAL_SECONDARY"])

    def test_03_null_recommendation_no_fabricated_evidence(self):
        """3. Null recommendation -> no fabricated evidence or fake candidate standard."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Laying of sewerage pipeline without pipe specification."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIsNone(r0["candidate_standard"])
        self.assertIsNone(r0["evidence_standard"])
        self.assertIn("no reliable", r0["why_it_matches"].lower())

    def test_04_ambiguous_competing_interpretations_preserved(self):
        """4. AMBIGUOUS -> competing interpretations preserved with distinguishing details."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Overhaul, maintenance and replacement of valves in cooling water line."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertEqual(r0["ambiguity_state"], "AMBIGUOUS")
        self.assertIsNone(r0["candidate_standard"])
        self.assertTrue(len(r0.get("competing_interpretations", [])) >= 2)
        for comp in r0["competing_interpretations"]:
            self.assertIn("standard_number", comp)
            self.assertTrue(bool(comp.get("title")))

    def test_05_incomplete_clarification_preserved(self):
        """5. INCOMPLETE -> clarification question and missing technical parameters preserved."""
        # Test real tender PDF known to lack specific technical parameters
        with open("tenders/raw/eProcurement System Government of India3.pdf", "rb") as f:
            resp = self.client.post(
                "/api/analyze/pdf",
                data={"file": (f, "eProcurement System Government of India3.pdf")},
                content_type="multipart/form-data"
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertEqual(r0["ambiguity_state"], "INCOMPLETE")
        self.assertTrue(r0["human_review_required"])
        self.assertIsNone(r0["candidate_standard"])

    def test_06_no_reliable_match_no_fake_standard(self):
        """6. NO_RELIABLE_MATCH -> no fake standard manufactured for out-of-scope tenders."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Procurement of office stationary, printer cartridges, and executive chairs."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        r0 = data["requirements"][0]
        self.assertIsNone(r0["candidate_standard"])
        self.assertIsNone(r0["evidence_standard"])

    def test_07_lifecycle_status_preserved(self):
        """7. Lifecycle status preserved: Active standards marked active, superseded marked superseded."""
        resp_active = self.client.post("/api/analyze/text", json={
            "text": "Supply and laying of CPVC pipes conforming to IS 15778."
        })
        self.assertEqual(resp_active.status_code, 200)
        r_act = resp_active.get_json()["requirements"][0]
        self.assertEqual(r_act["lifecycle_status"].lower(), "active")

        resp_super = self.client.post("/api/analyze/text", json={
            "text": "Cast iron gate valves conforming to IS 10611."
        })
        self.assertEqual(resp_super.status_code, 200)
        r_sup = resp_super.get_json()["requirements"][0]
        self.assertTrue(
            r_sup.get("superseded_citation") == "IS 10611" or
            "superseded" in (r_sup.get("why_flagged") or "").lower() or
            r_sup["lifecycle_status"].lower() == "superseded"
        )

    def test_08_successor_preserved_on_superseded(self):
        """8. Successor preserved: When superseded standard cited, current active replacement is identified."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Cast iron gate valves conforming to IS 10611."
        })
        self.assertEqual(resp.status_code, 200)
        r0 = resp.get_json()["requirements"][0]
        self.assertTrue(bool(r0.get("successor_standard")))
        self.assertIn("10434", r0["successor_standard"])

    def test_09_dependency_role_preserved(self):
        """9. Dependency role preserved: Dependencies retain normative / testing / installation roles."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Submersible pump sets for clear cold water in 150mm borewell conforming to IS 8034."
        })
        self.assertEqual(resp.status_code, 200)
        r0 = resp.get_json()["requirements"][0]
        deps = r0.get("dependencies", [])
        if deps:
            for d in deps:
                self.assertIn("standard_number", d)
                self.assertIn("relationship_type", d)
                # Ensure dependency standard does not overwrite candidate standard
                self.assertNotEqual(d["standard_number"], r0["candidate_standard"])

    def test_10_regulatory_uncertainty_preserved(self):
        """10. Regulatory uncertainty preserved: UNKNOWN or NOT_IDENTIFIED is not converted to mandatory."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "General unclassified masonry plastering work."
        })
        self.assertEqual(resp.status_code, 200)
        r0 = resp.get_json()["requirements"][0]
        reg = r0.get("regulatory", {})
        if reg:
            for cat, item in reg.items():
                if isinstance(item, dict):
                    status = item.get("status")
                    if status in ["NOT_IDENTIFIED", "UNKNOWN", "NOT_APPLICABLE"]:
                        self.assertFalse(item.get("mandatory", False))

    def test_11_human_review_preserved(self):
        """11. Human review preserved: human_review_required boolean remains True when uncertainty exists."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Procurement of unspecified waterworks valves."
        })
        self.assertEqual(resp.status_code, 200)
        r0 = resp.get_json()["requirements"][0]
        self.assertTrue(r0["human_review_required"])

    def test_12_why_this_explanation_grounded(self):
        """12. Why-this explanation is present and grounded in requirement or catalogue scope."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Installation of electrical wiring and safety equipment in commercial building."
        })
        self.assertEqual(resp.status_code, 200)
        r0 = resp.get_json()["requirements"][0]
        self.assertIsNotNone(r0["candidate_standard"])
        self.assertTrue(bool(r0.get("why_it_matches")))
        self.assertIsInstance(r0.get("why_this", []), list)

    def test_13_source_metadata_preserved(self):
        """13. Source metadata preserved: API response contains source and provenance."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply and delivery of 25 mm CPVC pipe."
        })
        self.assertEqual(resp.status_code, 200)
        r0 = resp.get_json()["requirements"][0]
        self.assertIn("source", r0)
        self.assertIn("provenance", r0)
        self.assertTrue(bool(r0["source"]))

    def test_14_provenance_database_distribution_integrity(self):
        """14. Database provenance counts match the established 502-standard catalogue distribution."""
        import sqlite3
        conn = sqlite3.connect("data/catalogue/catalogue.db")
        cur = conn.cursor()
        counts = dict(cur.execute("SELECT provenance, count(*) FROM catalogue_standards GROUP BY provenance").fetchall())
        conn.close()

        self.assertEqual(counts.get("OFFICIAL_PRIMARY"), 173)
        self.assertEqual(counts.get("OFFICIAL_SECONDARY"), 271)
        self.assertEqual(counts.get("CURATED"), 52)
        self.assertEqual(counts.get("VERIFIED"), 6)
        self.assertEqual(sum(counts.values()), 502)

    def test_15_readiness_originates_from_backend_audit(self):
        """15. Readiness originates directly from TenderAuditEngine verdict."""
        resp = self.client.post("/api/analyze/text", json={
            "text": "Supply and installation of CPVC pipes."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn(data.get("readiness"), ["READY_FOR_REVIEW", "REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE"])
        self.assertIsInstance(data.get("readiness_reasons"), list)


if __name__ == "__main__":
    unittest.main()
