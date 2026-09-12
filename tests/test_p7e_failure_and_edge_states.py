"""
tests/test_p7e_failure_and_edge_states.py
Priority 7E: Comprehensive Failure, Edge State & Decision-Safety Contract Tests.

Validates:
1. Empty text input handling (400 Bad Request).
2. Very short text input handling (safe evaluation, no crash).
3. Oversized text input handling (>10,000 chars rejected).
4. Invalid file extension upload (rejected with clean message).
5. Empty / corrupt PDF upload (fails safely, no unhandled traceback).
6. Text-only input workflow (returns complete normalized audit schema).
7. Zero extracted requirements (TenderAuditEngine handles empty list gracefully).
8. All requirements abstained (all candidate=None -> INSUFFICIENT_EVIDENCE).
9. All requirements review-required (REVIEW_REQUIRED verdict & populated review queue).
10. Mixed clear, ambiguous, and abstained requirements (strict invariant preservation).
11. Missing evidence / source URL / metadata resilience.
12. Missing regulatory data resilience.
13. Report download endpoint error states (404 on unknown ID).
14. Unknown sample demo endpoint (400 Bad Request with valid error message).
15. Absolute invariant: candidate_standard == evidence_standard for all non-null,
    and candidate=None, evidence=None for all abstentions.
"""

import io
import json
import pytest
from api.server import app, _report_cache
from src.audit import TenderAuditEngine, TenderAuditResult
from src.recommend import RequirementRecommendationResult
from src.report import ReportGenerator


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestPriority7EFailureAndEdgeStates:
    """Rigorous failure, edge-case, and safety-contract test suite for P7E."""

    # 1. Empty tender text
    def test_01_empty_text_input(self, client):
        res = client.post("/api/analyze/text", json={"text": ""})
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        assert "Missing 'text' field" in data["error"]

        res_spaces = client.post("/api/analyze/text", json={"text": "    \n\t   "})
        assert res_spaces.status_code == 400
        assert "Missing 'text' field" in res_spaces.get_json()["error"]

    # 2. Very short text input
    def test_02_very_short_text_input(self, client):
        res = client.post("/api/analyze/text", json={"text": "abc"})
        assert res.status_code == 200
        data = res.get_json()
        assert "tender" in data
        assert "readiness" in data
        assert "requirements" in data
        assert len(data["requirements"]) >= 1

        req = data["requirements"][0]
        # Extremely short ambiguous text must not produce a false positive strong recommendation
        if req["candidate_standard"]:
            assert req["candidate_standard"] == req["evidence_standard"]
        else:
            assert req["candidate_standard"] is None
            assert req["evidence_standard"] is None

    # 3. Oversized text input
    def test_03_oversized_text_input(self, client):
        huge_text = "CPVC pipe " * 2000  # >10,000 characters
        res = client.post("/api/analyze/text", json={"text": huge_text})
        assert res.status_code == 400
        data = res.get_json()
        assert "Text too long" in data["error"]

    # 4. Invalid file extension upload
    def test_04_invalid_file_extension(self, client):
        fake_file = (io.BytesIO(b"malicious executable"), "tender.exe")
        res = client.post("/api/analyze/pdf", data={"file": fake_file}, content_type="multipart/form-data")
        assert res.status_code == 400
        data = res.get_json()
        assert "Unsupported file type" in data["error"]

    # 5. Empty / non-PDF upload
    def test_05_corrupt_pdf_upload(self, client):
        empty_pdf = (io.BytesIO(b""), "empty.pdf")
        res = client.post("/api/analyze/pdf", data={"file": empty_pdf}, content_type="multipart/form-data")
        # Empty file causes fitz/pdf processing to fail safely with JSON error, not crash
        assert res.status_code in (400, 500)
        data = res.get_json()
        assert "error" in data

    # 6. Text-only input workflow produces complete, valid response
    def test_06_text_only_valid_specification(self, client):
        valid_spec = "Supply and installation of Chlorinated Polyvinyl Chloride (CPVC) pipes conforming to IS 15778 for internal water distribution"
        res = client.post("/api/analyze/text", json={"text": valid_spec})
        assert res.status_code == 200
        data = res.get_json()

        # Check all required top-level contract keys
        assert data["tender"]["id"].startswith("TS-")
        assert data["readiness"] in ("READY_FOR_REVIEW", "REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE")
        assert isinstance(data["readiness_reasons"], list)
        assert len(data["requirements"]) == 1

        req = data["requirements"][0]
        assert req["candidate_standard"] is not None
        assert req["evidence_standard"] is not None
        assert req["candidate_standard"] == req["evidence_standard"]
        assert req["evidence_strength"] in ("STRONG", "MODERATE", "WEAK", "NONE")
        assert req["provenance"] in ("VERIFIED", "CURATED", "INFERRED", "OFFICIAL_PRIMARY", "OFFICIAL_SECONDARY")

    # 7. Zero extracted requirements handling
    def test_07_zero_requirements_audit(self):
        audit_eng = TenderAuditEngine()
        res = audit_eng.audit_tender([], tender_id="ZERO_REQ_TENDER")
        assert res.requirements_analyzed == 0
        assert res.publication_readiness == "INSUFFICIENT_EVIDENCE"
        assert len(res.readiness_reasons) > 0
        assert "No requirements identified" in res.readiness_reasons[0]
        assert res.recommendations_count == 0
        assert len(res.review_queue) == 0

        # Test report generator with 0 requirements
        gen = ReportGenerator()
        report = gen.generate_report(res, [])
        assert report.publication_readiness == "INSUFFICIENT_EVIDENCE"
        assert len(report.requirements) == 0
        md = report.to_markdown()
        assert "No requirements identified in tender" in md

    # 8. All requirements abstained
    def test_08_all_requirements_abstained(self):
        audit_eng = TenderAuditEngine()
        r1 = RequirementRecommendationResult(
            requirement_id="REQ-A1",
            requirement_text="Overhaul of heavy earthmoving plant",
            category="service",
            explicit_standards_found=[],
            candidate_standard=None,
            evidence_standard=None,
            title="No standard matched",
            status="Unknown",
            version_role="None",
            relevance_score=0.0,
            confidence="Low",
            evidence="",
            provenance="INFERRED",
            human_review_required=True,
            reason="Catalogue unsupported",
            ambiguity_state="NO_RELIABLE_MATCH"
        )
        r2 = RequirementRecommendationResult(
            requirement_id="REQ-A2",
            requirement_text="Routine catering and housekeeping services",
            category="service",
            explicit_standards_found=[],
            candidate_standard=None,
            evidence_standard=None,
            title="No standard matched",
            status="Unknown",
            version_role="None",
            relevance_score=0.0,
            confidence="Low",
            evidence="",
            provenance="INFERRED",
            human_review_required=True,
            reason="Catalogue unsupported",
            ambiguity_state="NO_RELIABLE_MATCH"
        )
        res = audit_eng.audit_tender([r1, r2], tender_id="ALL_ABSTAINED")
        assert res.publication_readiness == "INSUFFICIENT_EVIDENCE"
        assert res.recommendations_count == 0

        gen = ReportGenerator()
        rep = gen.generate_report(res, [r1, r2])
        d = rep.to_dict()
        for sec in d["requirements"]:
            assert sec["candidate_standard"] is None
            assert sec["evidence_standard"] is None
            assert sec["evidence_strength"] == "NONE"

    # 9. All requirements review-required
    def test_09_all_requirements_review_required(self):
        audit_eng = TenderAuditEngine()
        r1 = RequirementRecommendationResult(
            requirement_id="REQ-R1",
            requirement_text="High tensile steel rebar Fe 500D",
            category="material",
            explicit_standards_found=[],
            candidate_standard="IS 1786 : 2008",
            evidence_standard="IS 1786 : 2008",
            title="High Strength Deformed Steel Bars and Wires for Concrete Reinforcement",
            status="Active",
            version_role="Current Primary",
            relevance_score=0.88,
            confidence="Medium",
            evidence="Authoritative standard for concrete reinforcement bars.",
            provenance="VERIFIED",
            human_review_required=True,
            reason="Mandatory Steel QCO verification required",
            critic_result={"decision": "REVIEW_REQUIRED", "evidence": {"evidence_strength": "STRONG"}}
        )
        res = audit_eng.audit_tender([r1], tender_id="ALL_REVIEW")
        assert res.publication_readiness == "REVIEW_REQUIRED"
        assert len(res.review_queue) >= 1
        assert res.review_queue[0].requirement_id == "REQ-R1"

    # 10. Mixed clear + ambiguous + abstained requirements
    def test_10_mixed_requirements_invariant(self):
        r_clear = RequirementRecommendationResult(
            requirement_id="REQ-CLEAR",
            requirement_text="Supply of CPVC pipes for domestic water distribution",
            category="material",
            explicit_standards_found=[],
            candidate_standard="IS 15778 : 2007",
            evidence_standard="IS 15778 : 2007",
            title="Chlorinated Polyvinyl Chloride Pipes",
            status="Active",
            version_role="Current Primary",
            relevance_score=0.92,
            confidence="High",
            evidence="Authoritative CPVC pipe standard",
            provenance="VERIFIED",
            human_review_required=False,
            reason="Exact match",
            critic_result={"decision": "RECOMMEND", "evidence": {"evidence_strength": "STRONG"}}
        )
        r_amb = RequirementRecommendationResult(
            requirement_id="REQ-AMB",
            requirement_text="Submersible pumpset for water supply",
            category="product_equipment",
            explicit_standards_found=[],
            candidate_standard=None,
            evidence_standard=None,
            title="No standard matched",
            status="Unknown",
            version_role="None",
            relevance_score=0.0,
            confidence="Low",
            evidence="",
            provenance="INFERRED",
            human_review_required=True,
            reason="Ambiguous borewell vs openwell",
            ambiguity_state="AMBIGUOUS",
            competing_interpretations=[
                {"standard_number": "IS 8034", "score": 0.82},
                {"standard_number": "IS 14220", "score": 0.79}
            ]
        )
        r_abst = RequirementRecommendationResult(
            requirement_id="REQ-ABST",
            requirement_text="Routine grass cutting and gardening",
            category="service",
            explicit_standards_found=[],
            candidate_standard=None,
            evidence_standard=None,
            title="No standard matched",
            status="Unknown",
            version_role="None",
            relevance_score=0.0,
            confidence="Low",
            evidence="",
            provenance="INFERRED",
            human_review_required=True,
            reason="Catalogue unsupported",
            ambiguity_state="NO_RELIABLE_MATCH"
        )

        results = [r_clear, r_amb, r_abst]
        audit_eng = TenderAuditEngine()
        audit_res = audit_eng.audit_tender(results, tender_id="MIXED_AUDIT")

        gen = ReportGenerator()
        rep = gen.generate_report(audit_res, results)
        d = rep.to_dict()

        for sec in d["requirements"]:
            if sec["candidate_standard"]:
                assert sec["candidate_standard"] == sec["evidence_standard"]
            else:
                assert sec["candidate_standard"] is None
                assert sec["evidence_standard"] is None

    # 11. Missing optional metadata resilience
    def test_11_missing_metadata_resilience(self):
        r = RequirementRecommendationResult(
            requirement_id="REQ-SPARSE",
            requirement_text="Unspecified work clause",
            category="general",
            explicit_standards_found=[],
            candidate_standard=None,
            evidence_standard=None,
            title="",
            status="",
            version_role="",
            relevance_score=0.0,
            confidence="",
            evidence="",
            provenance="",
            human_review_required=False,
            reason=""
        )
        audit_eng = TenderAuditEngine()
        audit_res = audit_eng.audit_tender([r], tender_id="SPARSE")

        gen = ReportGenerator()
        rep = gen.generate_report(audit_res, [r], tender_metadata=None)
        assert rep.tender_info.tender_title is None
        assert rep.tender_info.organisation is None

        # Must generate valid markdown and json without throwing KeyError or AttributeError
        md = rep.to_markdown()
        assert isinstance(md, str)
        js = rep.to_json()
        assert isinstance(js, str)

    # 12. Missing regulatory data resilience
    def test_12_missing_regulatory_data(self):
        r = RequirementRecommendationResult(
            requirement_id="REQ-NO-REG",
            requirement_text="Standard without regulatory metadata",
            category="product",
            explicit_standards_found=[],
            candidate_standard="IS 15778 : 2007",
            evidence_standard="IS 15778 : 2007",
            title="CPVC Pipes",
            status="Active",
            version_role="Current Primary",
            relevance_score=0.9,
            confidence="High",
            evidence="Evidence text",
            provenance="VERIFIED",
            human_review_required=False,
            reason="Matched",
            regulatory=None  # Explicitly None
        )
        gen = ReportGenerator()
        audit_eng = TenderAuditEngine()
        audit_res = audit_eng.audit_tender([r], tender_id="NO_REG")
        rep = gen.generate_report(audit_res, [r])
        d = rep.to_dict()
        assert d["requirements"][0]["regulatory"] is not None or d["requirements"][0]["regulatory"] == {}
        md = rep.to_markdown()
        assert "IS 15778 : 2007" in md

    # 13. Unknown report download returns 404
    def test_13_unknown_report_download_404(self, client):
        res_json = client.get("/api/report/NONEXISTENT_TENDER_12345/json")
        assert res_json.status_code == 404
        assert "Report not found" in res_json.get_json()["error"]

        res_md = client.get("/api/report/NONEXISTENT_TENDER_12345/markdown")
        assert res_md.status_code == 404
        assert "Report not found" in res_md.get_json()["error"]

    # 14. Unknown sample demo returns 400
    def test_14_unknown_sample_demo_400(self, client):
        res = client.get("/api/analyze/sample/unknown_xyz")
        assert res.status_code == 400
        data = res.get_json()
        assert "Unknown sample" in data["error"]
        assert "cpvc" in data["error"]
