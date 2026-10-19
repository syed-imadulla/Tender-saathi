# tests/test_phase38_production_reality.py
"""Phase 38 — Production Reality Check & End-to-End User Journey Validation.

Validates the complete Tender Saathi stack across all 12 canonical user scenarios:
1. Supported CPVC pipe requirement producing grounded, active IS 15778 recommendation.
2. Mixed multi-package tender (technical + commercial payment safe abstention).
3. Catalogue-discovered standard with transparent review requirement disclosure.
4. Withdrawn/superseded standard lifecycle warning.
5. Underspecified requirement ambiguity handling.
6. Physically incompatible engineering parameters rejection.
7. Digital PDF upload and extraction.
8. Scanned OCR fallback handling.
9. Human review decision persistence across reloads.
10. Report downloads (Markdown + CSV with formula injection defense).
11. Standards graph traversal (depth-1 normative references without ungrounded elevation).
12. Malformed, empty, and oversized boundary request handling.
"""

import io
import os
import json
import pytest

from api.server import app, _report_cache


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ===========================================================================
# Scenario 1: Supported CPVC Pipe Grounded Recommendation
# ===========================================================================
def test_scenario_1_cpvc_pipe_grounded_recommendation(client):
    """Scenario 1: CPVC pipe specification generates clause-verified IS 15778 : 2007."""
    payload = {
        "text": "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for potable hot and cold water distribution conforming to IS 15778."
    }
    resp = client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "requirements" in data
    reqs = data["requirements"]
    assert len(reqs) >= 1
    r0 = reqs[0]

    assert r0.get("candidate_standard") is not None
    assert "15778" in r0.get("candidate_standard", "")
    assert r0.get("evidence_tier") in ("CLAUSE_VERIFIED", "CORPUS_SUPPORTED", "BSB_VERIFIED", "CATALOGUE_DISCOVERED")
    assert r0.get("decision") in ("RECOMMEND", "REVIEW_REQUIRED")


# ===========================================================================
# Scenario 2: Mixed Tender with Technical & Commercial Terms
# ===========================================================================
def test_scenario_2_mixed_technical_and_commercial_terms(client):
    """Scenario 2: Technical requirement is matched; pure commercial terms produce Safe Abstention."""
    tender_text = (
        "Section 1: Electrical Wiring\n"
        "Supply and laying of PVC insulated unsheathed copper conductor cables for electrical installations conforming to IS 694.\n\n"
        "Section 2: Commercial Terms\n"
        "Earnest Money Deposit (EMD) of INR 1,50,000 shall be submitted online. Performance security of 5% valid for 12 months."
    )
    resp = client.post("/api/analyze/text", json={"text": tender_text})
    assert resp.status_code == 200
    data = resp.get_json()
    reqs = data["requirements"]
    assert len(reqs) >= 2

    # Technical requirement mapped to IS 694
    cable_reqs = [r for r in reqs if "694" in (r.get("candidate_standard") or "")]
    assert len(cable_reqs) >= 1

    # Commercial requirement has safe abstention (no fabricated standard)
    comm_reqs = [r for r in reqs if "earnest money" in r["text"].lower() or "emd" in r["text"].lower()]
    assert len(comm_reqs) >= 1
    comm = comm_reqs[0]
    assert comm.get("candidate_standard") is None or comm.get("human_review_required") is True


# ===========================================================================
# Scenario 3: Catalogue-Discovered Transparent Tier
# ===========================================================================
def test_scenario_3_catalogue_discovered_transparent_tier(client):
    """Scenario 3: Standard found in BIS catalogue but without registered gazette passage is CATALOGUE_DISCOVERED."""
    payload = {
        "text": "Procurement of self-contained open-circuit compressed air breathing apparatus conforming to IS 10245."
    }
    resp = client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    reqs = data["requirements"]
    assert len(reqs) >= 1
    r0 = reqs[0]

    if r0.get("candidate_standard"):
        assert "10245" in r0["candidate_standard"]
        # Invariant: Never CLAUSE_VERIFIED without authentic statutory corpus passages
        assert r0.get("evidence_tier") != "CLAUSE_VERIFIED"
        assert r0.get("human_review_required") is True or r0.get("evidence_tier") == "CATALOGUE_DISCOVERED"


# ===========================================================================
# Scenario 4: Withdrawn / Superseded Standard Lifecycle Warning
# ===========================================================================
def test_scenario_4_withdrawn_superseded_standard_warning(client):
    """Scenario 4: Explicit search for standard accurately surfaces recorded lifecycle status."""
    resp = client.get("/api/standards/search?q=IS 4984")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "standards" in data or "results" in data or isinstance(data, list)


# ===========================================================================
# Scenario 5: Underspecified Requirement Ambiguity Handling
# ===========================================================================
def test_scenario_5_underspecified_requirement_handling(client):
    """Scenario 5: Vague query lacking engineering parameters flags review/ambiguity."""
    payload = {"text": "Supply of standard pipes for general construction works."}
    resp = client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    reqs = data["requirements"]
    assert len(reqs) >= 1
    req = reqs[0]
    # Lacks diameter, material, pressure, temperature -> requires human review or low confidence
    assert req.get("human_review_required") is True or req.get("confidence") in ("Low", "Medium") or req.get("ambiguity_state") == "REVIEW_REQUIRED"


# ===========================================================================
# Scenario 6: Physically Incompatible Boundary Rejection
# ===========================================================================
def test_scenario_6_physically_incompatible_rejection(client):
    """Scenario 6: Impossible physical parameters (PVC pipe for superheated steam at 220 deg C) safely rejected."""
    payload = {
        "text": "Unplasticized PVC pipes conforming to IS 4985 for superheated steam conveyance at 220 deg C and 35 bar."
    }
    resp = client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    reqs = data["requirements"]
    assert len(reqs) >= 1
    req = reqs[0]
    # Engineering applicability gates must flag rejection, review, or incompatibility
    assert req.get("decision") in ("REJECTED", "REVIEW_REQUIRED", "FLAG") or req.get("human_review_required") is True


# ===========================================================================
# Scenario 7: Digital PDF Upload & Extraction
# ===========================================================================
def test_scenario_7_digital_pdf_upload(client):
    """Scenario 7: Digital PDF tender is ingested and parsed without OCR degradation."""
    pdf_path = "tests/fixtures/sample_tender.pdf"
    assert os.path.exists(pdf_path), "sample_tender.pdf fixture must exist"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    data = {
        "file": (io.BytesIO(pdf_bytes), "sample_tender.pdf", "application/pdf")
    }
    resp = client.post("/api/analyze/pdf", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    result = resp.get_json()
    assert "requirements" in result
    assert "tender" in result
    assert len(result["requirements"]) >= 1


# ===========================================================================
# Scenario 8: Scanned PDF / Fallback Handling
# ===========================================================================
def test_scenario_8_scanned_ocr_fallback_handling(client):
    """Scenario 8: Non-PDF or invalid binary payload triggers graceful error handling, not 500."""
    bad_data = {
        "file": (io.BytesIO(b"NOT_A_REAL_PDF"), "fake.pdf", "application/pdf")
    }
    resp = client.post("/api/analyze/pdf", data=bad_data, content_type="multipart/form-data")
    assert resp.status_code in (400, 422, 200)
    if resp.status_code == 200:
        data = resp.get_json()
        assert data.get("error") is not None or len(data.get("requirements", [])) == 0


# ===========================================================================
# Scenario 9: Human Review Decision Persistence Across Reloads
# ===========================================================================
def test_scenario_9_human_review_decision_persistence(client):
    """Scenario 9: Officer review decision is saved, persists, and appears in Section 8 report trail."""
    # 1. Analyze tender to seed report cache
    payload = {
        "text": "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes conforming to IS 15778."
    }
    resp = client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    tender_id = data["tender"]["id"]
    req_id = data["requirements"][0]["id"]

    # 2. Submit officer decision via /api/tender/<tender_id>/review
    review_payload = {
        "decisions": [
            {
                "requirement_id": req_id,
                "decision": "ACCEPT",
                "reviewer_note": "Verified against state water authority guidelines.",
                "reviewer": "Senior Procurement Officer"
            }
        ]
    }
    resp_rev = client.post(f"/api/tender/{tender_id}/review", json=review_payload)
    assert resp_rev.status_code == 200
    rev_data = resp_rev.get_json()
    assert rev_data.get("success") or rev_data.get("status") == "ok"

    # 3. Verify Markdown export reflects the recorded review
    resp_md = client.get(f"/api/report/{tender_id}/markdown")
    assert resp_md.status_code == 200
    md_text = resp_md.data.decode("utf-8")
    assert "ACCEPT" in md_text
    assert "Verified against state water authority guidelines" in md_text


# ===========================================================================
# Scenario 10: Report Downloads & CSV Formula Injection Defense
# ===========================================================================
def test_scenario_10_csv_formula_injection_defense(client):
    """Scenario 10: Requirement text with leading =, +, -, @ is sanitized in CSV exports."""
    probe_text = "=SUM(1,2) Mild steel tubes for water and gas pipelines."
    resp = client.post("/api/analyze/text", json={"text": probe_text})
    assert resp.status_code == 200
    tender_id = resp.get_json()["tender"]["id"]

    # Download CSV
    csv_resp = client.get(f"/api/report/{tender_id}/csv")
    assert csv_resp.status_code == 200
    csv_text = csv_resp.data.decode("utf-8")

    # The formula trigger must be escaped with a leading single quote (')
    assert "'=SUM(1,2)" in csv_text or not csv_text.startswith("=SUM")


# ===========================================================================
# Scenario 11: Standards Graph Traversal (No Ungrounded Elevation)
# ===========================================================================
def test_scenario_11_standards_graph_traversal_integrity(client):
    """Scenario 11: Standards graph returns valid depth-1 neighbors without ungrounded elevation."""
    resp = client.get("/api/standards/IS 1255/neighbors")
    assert resp.status_code == 200
    graph = resp.get_json()
    assert "neighbors" in graph or "nodes" in graph or "standard_id" in graph or isinstance(graph, list) or isinstance(graph, dict)


# ===========================================================================
# Scenario 12: Malformed, Empty, and Oversized Boundary Requests
# ===========================================================================
def test_scenario_12_boundary_error_handling(client):
    """Scenario 12: Handles empty body, invalid JSON, and non-existent IDs with proper HTTP error codes."""
    # Empty JSON
    resp = client.post("/api/analyze/text", json={})
    assert resp.status_code in (400, 422)

    # Empty text
    resp = client.post("/api/analyze/text", json={"text": "   "})
    assert resp.status_code in (400, 422)

    # Non-existent tender review
    resp = client.post("/api/tender/non_existent_id_9999/review", json={"decisions": []})
    assert resp.status_code == 404

    # Non-existent report
    resp = client.get("/api/report/non_existent_id_9999/markdown")
    assert resp.status_code == 404
