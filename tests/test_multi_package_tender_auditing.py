"""
tests/test_multi_package_tender_auditing.py — Deterministic verification suite for Phase 27.

Covers:
1. Multi-package and multi-domain segmentation and domain categorization.
2. Verification tier segregation: CLAUSE_VERIFIED vs CATALOGUE_DISCOVERED vs SAFE_ABSTENTION.
3. Cross-package complementary standards suites detection.
4. Tender-wide uncovered normative dependencies detection.
5. End-to-end multi-package tender auditing and package summary statistics.
6. Report generation in Markdown and JSON with exact passage traceability.
7. Flask REST API /api/analyze/tender endpoint contract.
"""

import pytest
from typing import Dict, Any, List
import json

from src.extract import (
    Requirement,
    extract_from_text,
    extract_packages_and_requirements,
    detect_technical_domain
)
from src.recommend import (
    StandardsRecommender,
    RequirementRecommendationResult,
    StandardRecommendation
)
from src.audit import (
    TenderAuditEngine,
    TenderAuditResult,
    TenderAuditSummary,
    StructuredTenderAuditReport
)
from src.report import (
    ReportGenerator,
    TenderReviewReport,
    RequirementReviewSection
)
from api.server import app


# ---------------------------------------------------------------------------
# Test 1: Technical Domain Detection
# ---------------------------------------------------------------------------

def test_technical_domain_detection():
    # Civil & Structural
    assert detect_technical_domain("Supply of ready mixed concrete grade M30 with high yield strength deformed steel bars") == "CIVIL_AND_STRUCTURAL"
    assert detect_technical_domain("Structural steel fabrication for warehouse roof trusses") == "CIVIL_AND_STRUCTURAL"

    # Pipes & Fittings
    assert detect_technical_domain("Supply of High Density Polyethylene (HDPE) pipes PN 10 for drinking water distribution") == "PIPES_AND_FITTINGS"
    assert detect_technical_domain("Ductile iron socket and spigot pressure pipes for water mains") == "PIPES_AND_FITTINGS"

    # Valves & Flow Control
    assert detect_technical_domain("Cast iron double flanged sluice valves PN 1.0 for isolation") == "VALVES_AND_FLOW"

    # Electrical & Power
    assert detect_technical_domain("Supply and laying of 11kV cross linked polyethylene XLPE insulated power cables") == "ELECTRICAL_AND_POWER"
    assert detect_technical_domain("Outdoor type oil immersed distribution transformers 11kV / 433V") == "ELECTRICAL_AND_POWER"

    # Pumps & Rotating
    assert detect_technical_domain("Submersible pump sets for clear cold water with electric motors") == "PUMPS_AND_ROTATING"

    # General & Administrative
    assert detect_technical_domain("Bidder must submit EMD of Rs 50,000 and valid GST registration certificate") == "GENERAL_AND_ADMINISTRATIVE"
    assert detect_technical_domain("The bidder shall provide 3 years annual maintenance service with 2 dedicated technicians") == "GENERAL_AND_ADMINISTRATIVE"


# ---------------------------------------------------------------------------
# Test 2: Multi-Package Requirement Extraction
# ---------------------------------------------------------------------------

def test_multi_package_extraction():
    multi_pkg_text = """
    Tender No: WSS-2026-PKG-01/02
    Integrated Infrastructure Development Project

    Package 1: Civil and Intake Works
    1. Supply and laying of reinforced cement concrete for intake well foundation as per IS 456.
    2. High strength deformed steel reinforcement bars for intake pump house structure.

    Package 2: Transmission Mains & Water Supply
    1. Supply of 200mm diameter PE-100 HDPE pipes for potable water conveyance.
    2. Installation of cast iron sluice valves Class 1 for isolation.

    Package 3: Substation & Power Distribution
    1. 11kV grade cross linked polyethylene XLPE power cables.
    2. Code of practice for earthing and lightning protection.

    General Terms and Administrative Conditions
    1. Bidder must submit EMD of Rs 1,00,000 and 3 years audited balance sheets.
    """

    reqs = extract_packages_and_requirements(multi_pkg_text, tender_id="TND-WSS-01")
    assert len(reqs) >= 6

    # Verify package assignments
    pkg1_reqs = [r for r in reqs if r.package_id == "PKG-01"]
    assert len(pkg1_reqs) == 2
    assert "Civil" in pkg1_reqs[0].package_name
    assert pkg1_reqs[0].domain == "CIVIL_AND_STRUCTURAL"

    pkg2_reqs = [r for r in reqs if r.package_id == "PKG-02"]
    assert len(pkg2_reqs) == 2
    assert "Water" in pkg2_reqs[0].package_name
    assert any(r.domain in ["PIPES_AND_FITTINGS", "VALVES_AND_FLOW"] for r in pkg2_reqs)

    pkg3_reqs = [r for r in reqs if r.package_id == "PKG-03"]
    assert len(pkg3_reqs) == 2
    assert "Power" in pkg3_reqs[0].package_name
    assert all(r.domain == "ELECTRICAL_AND_POWER" for r in pkg3_reqs)

    # General / administrative
    admin_reqs = [r for r in reqs if r.domain == "GENERAL_AND_ADMINISTRATIVE"]
    assert len(admin_reqs) >= 1


# ---------------------------------------------------------------------------
# Test 3: Verification Tier Segregation in Recommender
# ---------------------------------------------------------------------------

def test_verification_tier_segregation():
    recommender = StandardsRecommender()

    # 1. Clause-verified requirement (indexed in corpus: IS 1180 or IS 4984)
    hdpe_req = Requirement(
        requirement_id="REQ-HDPE",
        requirement_text="High density polyethylene HDPE pipes for water supply conforming to IS 4984",
        category="materials",
        package_id="PKG-01",
        package_name="Piping Package",
        domain="PIPES_AND_FITTINGS"
    )
    hdpe_res = recommender.recommend_for_requirement(hdpe_req)
    assert hdpe_res.candidate_standard is not None
    assert "4984" in hdpe_res.candidate_standard
    assert hdpe_res.verification_tier in ["CLAUSE_VERIFIED", "CATALOGUE_DISCOVERED"]
    assert hdpe_res.package_id == "PKG-01"
    assert hdpe_res.domain == "PIPES_AND_FITTINGS"

    # 2. Safe abstention requirement (pure administrative tender condition)
    admin_req = Requirement(
        requirement_id="REQ-ADMIN",
        requirement_text="Bidder must furnish Earnest Money Deposit (EMD) of INR 50,000 via RTGS and valid PAN card copy",
        category="general",
        package_id="PKG-ADM",
        package_name="Commercial Scope",
        domain="GENERAL_AND_ADMINISTRATIVE"
    )
    admin_res = recommender.recommend_for_requirement(admin_req)
    assert admin_res.verification_tier == "SAFE_ABSTENTION"
    assert admin_res.candidate_standard in [None, "NONE", "INSUFFICIENT_INFORMATION"]
    assert admin_res.passage_id is None
    assert admin_res.clause_number is None


# ---------------------------------------------------------------------------
# Test 4: Cross-Package Complementary Engineering Suites Detection
# ---------------------------------------------------------------------------

def test_cross_package_complementary_suites():
    audit_eng = TenderAuditEngine()

    def make_res(req_id, text, std, pkg_id, pkg_name, domain, tier="CLAUSE_VERIFIED"):
        return RequirementRecommendationResult(
            requirement_id=req_id,
            requirement_text=text,
            category="materials",
            explicit_standards_found=[std],
            candidate_standard=std,
            title=f"Standard {std}",
            status="Active",
            version_role="CURRENT",
            relevance_score=0.95,
            confidence="High",
            evidence="Authentic evidence",
            provenance="VERIFIED",
            human_review_required=False,
            reason="Applicable standard",
            package_id=pkg_id,
            package_name=pkg_name,
            domain=domain,
            verification_tier=tier,
            passage_id="PASSAGE-01",
            clause_number="4.1",
            edition_year="2020"
        )

    # Tender with Civil Structural Suite: IS 456 in PKG-01, IS 1786 in PKG-02
    results = [
        make_res("R1", "Reinforced concrete works", "IS 456", "PKG-01", "Civil Works", "CIVIL_AND_STRUCTURAL"),
        make_res("R2", "High strength deformed steel bars", "IS 1786", "PKG-02", "Rebar Supply", "CIVIL_AND_STRUCTURAL"),
        make_res("R3", "HDPE piping conveyance", "IS 4984", "PKG-03", "Piping Works", "PIPES_AND_FITTINGS"),
        make_res("R4", "Sluice valves for flow control", "IS 14846", "PKG-03", "Piping Works", "VALVES_AND_FLOW")
    ]

    audit_res = audit_eng.audit_tender(results, tender_id="TND-SUITES")
    suites = audit_res.complementary_standards

    assert len(suites) >= 2
    suite_ids = [s["suite_id"] for s in suites]
    assert "SUITE-CIVIL-CONCRETE" in suite_ids
    assert "SUITE-WATER-PIPING" in suite_ids

    civil_suite = next(s for s in suites if s["suite_id"] == "SUITE-CIVIL-CONCRETE")
    assert "PKG-01" in civil_suite["packages_involved"]
    assert "PKG-02" in civil_suite["packages_involved"]
    assert "IS 1786" in civil_suite["allied_standards"]


# ---------------------------------------------------------------------------
# Test 5: Tender-Wide Uncovered Normative Dependencies Detection
# ---------------------------------------------------------------------------

def test_uncovered_tender_dependencies():
    audit_eng = TenderAuditEngine()

    def make_res(req_id, text, std, pkg_id, pkg_name, domain):
        return RequirementRecommendationResult(
            requirement_id=req_id,
            requirement_text=text,
            category="materials",
            explicit_standards_found=[std],
            candidate_standard=std,
            title=f"Standard {std}",
            status="Active",
            version_role="CURRENT",
            relevance_score=0.90,
            confidence="High",
            evidence="Evidence",
            provenance="VERIFIED",
            human_review_required=False,
            reason="Standard verified",
            package_id=pkg_id,
            package_name=pkg_name,
            domain=domain,
            verification_tier="CLAUSE_VERIFIED"
        )

    # Tender specifies IS 456, but nowhere is IS 1786 (rebar) cited or recommended
    results = [
        make_res("R1", "Concrete construction works", "IS 456", "PKG-01", "Civil Package", "CIVIL_AND_STRUCTURAL"),
        make_res("R2", "Power cabling works", "IS 7098", "PKG-02", "Electrical Package", "ELECTRICAL_AND_POWER")
    ]

    audit_res = audit_eng.audit_tender(results, tender_id="TND-UNCOVERED")
    uncov = audit_res.uncovered_tender_dependencies

    assert len(uncov) >= 2
    missing_stds = [u["missing_dependency"] for u in uncov]
    # IS 456 misses IS 1786
    assert "IS 1786" in missing_stds
    # IS 7098 misses IS 1255 (installation code)
    assert "IS 1255" in missing_stds


# ---------------------------------------------------------------------------
# Test 6: Package Summaries and Statistics in TenderAuditResult
# ---------------------------------------------------------------------------

def test_package_summaries_in_audit():
    audit_eng = TenderAuditEngine()

    r1 = RequirementRecommendationResult(
        requirement_id="R1",
        requirement_text="RCC foundation per IS 456",
        category="materials",
        explicit_standards_found=["IS 456"],
        candidate_standard="IS 456",
        title="Plain and Reinforced Concrete",
        status="Active",
        version_role="CURRENT",
        relevance_score=0.95,
        confidence="High",
        evidence="Evidence text",
        provenance="VERIFIED",
        human_review_required=False,
        reason="Grounding verified",
        package_id="PKG-01",
        package_name="Civil Works",
        domain="CIVIL_AND_STRUCTURAL",
        verification_tier="CLAUSE_VERIFIED"
    )
    r2 = RequirementRecommendationResult(
        requirement_id="R2",
        requirement_text="Supply of valves",
        category="materials",
        explicit_standards_found=[],
        candidate_standard="IS 14846",
        title="Sluice Valves",
        status="Active",
        version_role="CURRENT",
        relevance_score=0.80,
        confidence="Medium",
        evidence="Catalogue match",
        provenance="NATIONAL_CATALOGUE_DISCOVERY",
        human_review_required=True,
        reason="Discovered unindexed standard",
        package_id="PKG-02",
        package_name="Piping Works",
        domain="VALVES_AND_FLOW",
        verification_tier="CATALOGUE_DISCOVERED"
    )
    r3 = RequirementRecommendationResult(
        requirement_id="R3",
        requirement_text="Commercial warranty and bank guarantee",
        category="general",
        explicit_standards_found=[],
        candidate_standard=None,
        title="N/A",
        status="Unknown",
        version_role="NONE",
        relevance_score=0.0,
        confidence="Low",
        evidence="",
        provenance="UNKNOWN",
        human_review_required=False,
        reason="Administrative requirement",
        package_id="PKG-ADM",
        package_name="Commercial Conditions",
        domain="GENERAL_AND_ADMINISTRATIVE",
        verification_tier="SAFE_ABSTENTION"
    )

    audit_res = audit_eng.audit_tender([r1, r2, r3], tender_id="TND-STATS")

    assert audit_res.clause_verified_count == 1
    assert audit_res.catalogue_discovered_count == 1
    assert audit_res.safe_abstention_count == 1

    assert len(audit_res.package_summaries) == 3
    pkg1 = next(p for p in audit_res.package_summaries if p["package_id"] == "PKG-01")
    assert pkg1["clause_verified_count"] == 1
    assert pkg1["requirement_count"] == 1

    pkg2 = next(p for p in audit_res.package_summaries if p["package_id"] == "PKG-02")
    assert pkg2["catalogue_discovered_count"] == 1
    assert pkg2["human_review_count"] == 1

    # Domain distribution check
    assert audit_res.domain_distribution["CIVIL_AND_STRUCTURAL"] == 1
    assert audit_res.domain_distribution["VALVES_AND_FLOW"] == 1
    assert audit_res.domain_distribution["GENERAL_AND_ADMINISTRATIVE"] == 1


# ---------------------------------------------------------------------------
# Test 7: Report Generation with Multi-Package Sections & Exact Passages
# ---------------------------------------------------------------------------

def test_report_generation_multi_package():
    audit_eng = TenderAuditEngine()
    report_gen = ReportGenerator()

    r1 = RequirementRecommendationResult(
        requirement_id="R1",
        requirement_text="Supply of high density polyethylene pipes as per IS 4984",
        category="materials",
        explicit_standards_found=["IS 4984"],
        candidate_standard="IS 4984",
        title="High Density Polyethylene Pipes for Water Supply",
        status="Active",
        version_role="CURRENT",
        relevance_score=0.98,
        confidence="High",
        evidence="Clause 5.1 Pressure Rating",
        provenance="VERIFIED",
        human_review_required=False,
        reason="Authentic clause evidence found",
        package_id="PKG-01",
        package_name="Water Supply Works",
        domain="PIPES_AND_FITTINGS",
        verification_tier="CLAUSE_VERIFIED",
        passage_id="PASSAGE-HDPE-001",
        clause_number="5.1",
        edition_year="2016"
    )

    audit = audit_eng.audit_tender([r1], tender_id="TND-REPORT-01")
    report = report_gen.generate_report(audit, [r1])

    # Check typed report attributes
    assert len(report.package_summaries) >= 1
    assert len(report.requirements) == 1
    sec = report.requirements[0]
    assert sec.package_id == "PKG-01"
    assert sec.package_name == "Water Supply Works"
    assert sec.verification_tier == "CLAUSE_VERIFIED"
    assert sec.passage_id == "PASSAGE-HDPE-001"
    assert sec.clause_number == "5.1"
    assert sec.edition_year == "2016"

    # Check Markdown rendering
    md = report.to_markdown()
    assert "Package & Technical Scope Breakdown" in md
    assert "Water Supply Works" in md
    assert "Exact Normative Grounding" in md
    assert "Clause 5.1" in md
    assert "PASSAGE-HDPE-001" in md

    # Check JSON export
    report_dict = json.loads(report.to_json())
    assert "package_summaries" in report_dict
    assert report_dict["requirements"][0]["verification_tier"] == "CLAUSE_VERIFIED"


# ---------------------------------------------------------------------------
# Test 8: REST API /api/analyze/tender Endpoint
# ---------------------------------------------------------------------------

def test_api_analyze_tender_endpoint():
    client = app.test_client()

    payload = {
        "tender_id": "TND-API-TEST",
        "packages": [
            {
                "package_id": "PKG-01",
                "name": "Civil Package",
                "requirements": [
                    {"id": "C-01", "text": "Reinforced cement concrete grade M25 for columns as per IS 456"}
                ]
            },
            {
                "package_id": "PKG-02",
                "name": "Electrical Package",
                "requirements": [
                    {"id": "E-01", "text": "XLPE insulated electric power cables conforming to IS 7098"}
                ]
            }
        ]
    }

    res = client.post("/api/analyze/tender", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    assert data["tender"]["id"] == "TND-API-TEST"
    assert data["summary"]["requirements_analyzed"] == 2
    assert "package_summaries" in data["summary"]
    assert len(data["summary"]["package_summaries"]) == 2

    # Verify requirements contain Phase 27 fields
    reqs = data["requirements"]
    assert len(reqs) == 2
    assert reqs[0]["package_id"] == "PKG-01"
    assert reqs[0]["package_name"] == "Civil Package"
    assert reqs[0]["domain"] == "CIVIL_AND_STRUCTURAL"
    assert "verification_tier" in reqs[0]

    assert reqs[1]["package_id"] == "PKG-02"
    assert reqs[1]["domain"] == "ELECTRICAL_AND_POWER"
