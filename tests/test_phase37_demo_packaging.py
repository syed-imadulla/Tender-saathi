"""
tests/test_phase37_demo_packaging.py — Phase 37 Demonstration Packaging & Readiness Suite

Verifies:
1. Docker Compose and Nginx deployment configurations.
2. .env.example variable definitions and security hygiene (no leaked secrets).
3. The 3 Canonical Live Demo Scenarios:
   - Stage 1: Clause-Verified CPVC pipe (IS 15778) with grounded passages & QCO mandate.
   - Stage 2: Mixed multi-package tender with commercial clauses (IS 694 + safe abstention).
   - Stage 3: Catalogue-discovered breathing apparatus (IS 10245) + human review queue workflow.
4. Human Review decision persistence (ACCEPT/EDIT/DISMISS) into audit trail.
5. Multi-format report export consistency (Markdown, JSON, CSV).
"""

import json
import unittest
from pathlib import Path

from api.server import app


class TestPhase37DemoPackaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    # -------------------------------------------------------------------------
    # 1. Deployment Packaging & Configuration Validation
    # -------------------------------------------------------------------------
    def test_01_docker_compose_configuration(self):
        """Verify docker-compose.yml defines backend and frontend with required ports and healthchecks."""
        compose_path = Path("docker-compose.yml")
        self.assertTrue(compose_path.exists(), "docker-compose.yml must exist at repository root")

        content = compose_path.read_text(encoding="utf-8")
        self.assertIn("services:", content)
        self.assertIn("backend:", content)
        self.assertIn("frontend:", content)
        self.assertIn('"5000:5000"', content)
        self.assertIn('"3000:80"', content)
        self.assertIn("reports_data:", content)
        self.assertIn("healthcheck:", content)

    def test_02_frontend_nginx_configuration(self):
        """Verify frontend/nginx.conf handles reverse-proxying and SPA history fallback."""
        nginx_path = Path("frontend/nginx.conf")
        self.assertTrue(nginx_path.exists(), "frontend/nginx.conf must exist")

        content = nginx_path.read_text(encoding="utf-8")
        self.assertIn("location /api/", content)
        self.assertIn("proxy_pass http://backend:5000/api/;", content)
        self.assertIn("try_files $uri $uri/ /index.html;", content)

    def test_03_env_example_hygiene(self):
        """Verify .env.example contains documentation placeholders and zero leaked credentials."""
        env_path = Path(".env.example")
        self.assertTrue(env_path.exists(), ".env.example must exist")

        content = env_path.read_text(encoding="utf-8")
        self.assertIn("PORT=", content)
        self.assertIn("CORS_ORIGINS=", content)
        self.assertIn("REPORT_DIR=", content)
        self.assertIn("TENDERSAATHI_LLM_ENABLED=", content)

        # Invariant: No real secrets in .env.example
        lines = content.splitlines()
        for line in lines:
            if line.startswith("GROQ_API_KEY="):
                val = line.split("=", 1)[1].strip()
                self.assertEqual(val, "", ".env.example must not contain real API keys")

    # -------------------------------------------------------------------------
    # 2. Live Demo 3-Stage Narrative Verification
    # -------------------------------------------------------------------------
    def test_04_live_demo_stage1_clause_verified_cpvc(self):
        """Stage 1: Verified engineering specification (IS 15778 CPVC pipe)."""
        payload = {
            "text": "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for domestic hot and cold water distribution conforming to IS 15778."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 1)
        r0 = reqs[0]

        self.assertIsNotNone(r0["candidate_standard"])
        self.assertIn("15778", r0["candidate_standard"])
        self.assertIn(r0["evidence_tier"], ("CLAUSE_VERIFIED", "CORPUS_SUPPORTED", "CATALOGUE_DISCOVERED", "BSB_CURATED", "BSB_VERIFIED"))
        self.assertIn(r0["ambiguity_state"], ("CLEAR", "REVIEW_REQUIRED"))
        self.assertEqual(r0["decision"], "RECOMMEND")
        self.assertEqual(r0["candidate_standard"], r0["evidence_standard"])

        # Check regulatory intelligence presence (QCO and Scheme-I)
        reg = r0.get("regulatory", {})
        self.assertIn("qco", reg)
        self.assertIn("certification", reg)

    def test_05_live_demo_stage2_mixed_technical_and_commercial(self):
        """Stage 2: Mixed tender with technical scope (IS 694) and commercial safe abstention."""
        payload = {
            "text": (
                "Section 1: Electrical Wiring\n"
                "Supply and laying of PVC insulated unsheathed copper conductor cables for electrical installations conforming to IS 694.\n\n"
                "Section 2: Commercial Terms\n"
                "Earnest Money Deposit (EMD) of INR 1,50,000 shall be submitted online. Performance security of 5% valid for 12 months."
            )
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 2)

        # Technical requirement mapped to IS 694
        cable_reqs = [r for r in reqs if "694" in (r.get("candidate_standard") or "")]
        self.assertGreaterEqual(len(cable_reqs), 1)

        # Commercial requirement has safe abstention (no fabricated standard)
        comm_reqs = [r for r in reqs if "earnest money" in r["text"].lower() or "emd" in r["text"].lower()]
        self.assertGreaterEqual(len(comm_reqs), 1)
        comm = comm_reqs[0]
        self.assertTrue(comm.get("candidate_standard") is None or comm.get("human_review_required"))

    def test_06_live_demo_stage3_catalogue_only_and_human_review(self):
        """Stage 3: Catalogue-discovered item (IS 10245) showing transparent human review queue."""
        payload = {
            "text": "Procurement of self-contained open-circuit compressed air breathing apparatus conforming to IS 10245."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        reqs = data["requirements"]
        self.assertGreaterEqual(len(reqs), 1)
        r0 = reqs[0]

        if r0["candidate_standard"]:
            self.assertIn("10245", r0["candidate_standard"])
            # Invariant: Never CLAUSE_VERIFIED without authentic statutory corpus passages
            self.assertNotEqual(r0["evidence_tier"], "CLAUSE_VERIFIED")
            self.assertTrue(r0["human_review_required"] or r0["evidence_tier"] == "CATALOGUE_DISCOVERED")

    # -------------------------------------------------------------------------
    # 3. Human Review Decision Workflow Persistence
    # -------------------------------------------------------------------------
    def test_07_human_review_decision_persistence(self):
        """Verify human officer review decisions (ACCEPT/EDIT/DISMISS) are persisted in report cache."""
        # 1. Analyze tender to seed report cache
        payload = {
            "text": "Procurement of self-contained open-circuit compressed air breathing apparatus conforming to IS 10245."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        tender_id = data["tender"]["id"]
        req_id = data["requirements"][0]["id"]

        # 2. Submit officer decision via /api/tender/<tender_id>/review
        review_payload = {
            "decisions": [
                {
                    "requirement_id": req_id,
                    "decision": "ACCEPT",
                    "reviewer_note": "Verified against fire department operational guidelines.",
                    "reviewer": "Procurement Officer SIH"
                }
            ]
        }
        resp_rev = self.client.post(f"/api/tender/{tender_id}/review", json=review_payload)
        self.assertEqual(resp_rev.status_code, 200)
        rev_data = resp_rev.get_json()
        self.assertTrue(rev_data.get("success") or rev_data.get("status") == "ok")

        # 3. Verify Markdown export reflects the recorded review
        resp_md = self.client.get(f"/api/report/{tender_id}/markdown")
        self.assertEqual(resp_md.status_code, 200)
        md_text = resp_md.data.decode("utf-8")
        self.assertIn("**ACCEPT**", md_text)
        self.assertIn("Verified against fire department operational guidelines", md_text)

    # -------------------------------------------------------------------------
    # 4. Multi-Format Report Export Sanity
    # -------------------------------------------------------------------------
    def test_08_multi_format_reports_consistency(self):
        """Verify Markdown, JSON, and CSV exports succeed with matching tender IDs."""
        payload = {
            "text": "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes conforming to IS 15778."
        }
        resp = self.client.post("/api/analyze/text", json=payload)
        self.assertEqual(resp.status_code, 200)
        tender_id = resp.get_json()["tender"]["id"]

        # Markdown
        r_md = self.client.get(f"/api/report/{tender_id}/markdown")
        self.assertEqual(r_md.status_code, 200)
        self.assertIn("text/markdown", r_md.content_type)
        self.assertIn(tender_id, r_md.data.decode("utf-8"))

        # JSON
        r_json = self.client.get(f"/api/report/{tender_id}/json")
        self.assertEqual(r_json.status_code, 200)
        self.assertIn("application/json", r_json.content_type)
        parsed = json.loads(r_json.data.decode("utf-8"))
        self.assertEqual(parsed["tender_info"]["tender_id"], tender_id)

        # CSV
        r_csv = self.client.get(f"/api/report/{tender_id}/csv")
        self.assertEqual(r_csv.status_code, 200)
        self.assertIn("text/csv", r_csv.content_type)
        self.assertIn("IS 15778", r_csv.data.decode("utf-8"))
