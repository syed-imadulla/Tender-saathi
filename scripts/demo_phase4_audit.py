"""
scripts/demo_phase4_audit.py

End-to-End Demonstration Scenario for Phase 4:
Tender Audit & Standards Gap Intelligence.

Demonstrates:
1. Clear covered requirement (Active IS 8034 : 2018)
2. Multi-standard requirement (Submersible pump + motor components)
3. Ambiguous requirement (Missing extinguishing agent & capacity)
4. Lifecycle concern (Explicit citation of withdrawn IS 8034 : 2002)
5. Potential coverage gap (Specialized cryogenic liquid helium siphon)

Trace output drill-down:
Requirement -> Standard -> Applicability -> Evidence -> Lifecycle -> Reason -> Review Action
"""

import sys
import os
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender, RequirementRecommendationResult, StandardRecommendation
from src.audit import (
    TenderAuditEngine,
    TenderAuditResult,
    CoverageState,
    AuditFindingType,
    ReviewQueueCategory,
    StructuredTenderAuditReport
)


def run_phase4_demo():
    print("=" * 80)
    print(" TENDERSAATHI PHASE 4: TENDER AUDIT & STANDARDS GAP INTELLIGENCE DEMO")
    print("=" * 80)
    print(" Pipeline Evolution: RETRIEVE -> APPLY -> DECIDE -> EXPLAIN -> AUDIT\n")

    db = StandardsDatabase()
    audit_engine = TenderAuditEngine(db=db)

    # 1. Clear Covered Requirement
    r1 = RequirementRecommendationResult(
        requirement_id="REQ-001",
        requirement_text="Providing, installing, testing and commissioning of submersible pumpsets conforming to IS 8034 for water supply.",
        category="PRODUCT",
        explicit_standards_found=["IS 8034"],
        candidate_standard="IS 8034 : 2018",
        title="Submersible pumpsets - Specification (Third Revision)",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.96,
        confidence="High",
        evidence="Title, product family, and deep-well submersible application match official scope.",
        provenance="VERIFIED",
        human_review_required=False,
        reason="Applicable standard verified in official BIS catalogue.",
        recommendations=[StandardRecommendation(
            standard_number="IS 8034 : 2018",
            title="Submersible pumpsets - Specification (Third Revision)",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.96,
            confidence="High",
            evidence="Authoritative BIS record matches submersible pumpset procurement object.",
            provenance="VERIFIED",
            applicability={"decision": "APPLICABLE", "is_applicable": True}
        )],
        critic_result={"decision": "RECOMMEND", "risk_level": "LOW", "evidence": {"evidence_strength": "STRONG", "grounded": True}},
        risk_level="LOW",
        applicability={"decision": "APPLICABLE", "is_applicable": True},
        structured_evidence={
            "standard_number": "IS 8034 : 2018",
            "official_title": "Submersible pumpsets - Specification (Third Revision)",
            "evidence_strength": "STRONG",
            "scope_status": "AUTHORITATIVE_VERIFIED",
            "lifecycle": {"status": "ACTIVE", "is_active": True, "is_withdrawn": False, "is_unknown": False},
            "relationships": {"supersedes": [], "superseded_by": [], "normative_references": ["IS 9283"]},
            "provenance": {"source": "BIS Official Catalogue", "verification_status": "VERIFIED"},
            "applicability": {"decision": "APPLICABLE", "domain_match": True, "product_match": True},
            "explanation": {"why_selected": "Grounded authoritative catalogue match", "human_review_required": False}
        }
    )

    # 2. Multi-Standard Requirement
    r2 = RequirementRecommendationResult(
        requirement_id="REQ-002",
        requirement_text="Supply of complete submersible pumping assembly comprising submersible pump unit and submersible induction motor operating on 415 V 3-phase AC.",
        category="COMPOSITE",
        explicit_standards_found=[],
        candidate_standard="IS 8034 : 2018",
        title="Submersible pumpsets and induction motors",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.92,
        confidence="High",
        evidence="Decomposed into pump unit and prime mover motor.",
        provenance="VERIFIED",
        human_review_required=False,
        reason="Multi-component procurement object with verified standard assignments.",
        recommendations=[
            StandardRecommendation(standard_number="IS 8034 : 2018", title="Submersible pumpsets", status="Active", version_role="CURRENT_ACTIVE", relevance_score=0.92, confidence="High", evidence="Pump unit", provenance="VERIFIED", applicability={"decision": "APPLICABLE"}),
            StandardRecommendation(standard_number="IS 9283 : 2024", title="Motors for submersible pumpsets", status="Active", version_role="CURRENT_ACTIVE", relevance_score=0.88, confidence="High", evidence="Motor unit", provenance="VERIFIED", applicability={"decision": "APPLICABLE"})
        ],
        decomposed_components=[
            {"component_id": "C1", "component_text": "Submersible pump unit", "assigned_standard": "IS 8034 : 2018"},
            {"component_id": "C2", "component_text": "Submersible induction motor", "assigned_standard": "IS 9283 : 2024"}
        ],
        critic_result={"decision": "RECOMMEND", "risk_level": "LOW", "evidence": {"evidence_strength": "STRONG", "grounded": True}},
        risk_level="LOW",
        applicability={"decision": "APPLICABLE", "is_applicable": True},
        structured_evidence={
            "standard_number": "IS 8034 : 2018",
            "evidence_strength": "STRONG",
            "scope_status": "AUTHORITATIVE_VERIFIED",
            "lifecycle": {"status": "ACTIVE", "is_active": True},
            "provenance": {"source": "BIS Official Catalogue", "verification_status": "VERIFIED"}
        }
    )

    # 3. Ambiguous Requirement (Missing Parameters)
    r3 = RequirementRecommendationResult(
        requirement_id="REQ-003",
        requirement_text="Supply and installation of portable fire extinguishers for administrative building safety.",
        category="PRODUCT",
        explicit_standards_found=[],
        candidate_standard="IS 15683 : 2018",
        title="Portable Fire Extinguishers - Performance and Construction",
        status="Active",
        version_role="CURRENT_ACTIVE",
        relevance_score=0.65,
        confidence="Medium",
        evidence="Generic fire extinguisher matched; missing extinguishing medium and capacity rating.",
        provenance="CURATED",
        human_review_required=True,
        reason="Specification omits critical discriminating parameters.",
        critic_result={"decision": "REVIEW_REQUIRED", "risk_level": "MEDIUM", "evidence": {"evidence_strength": "MODERATE", "grounded": True}},
        risk_level="MEDIUM",
        ambiguity_state="AMBIGUOUS_PARAMETER_GAP",
        ambiguity_reason="Missing critical engineering parameters: extinguishing agent (Water, Foam, Dry Powder, CO2) and capacity rating.",
        missing_information=["extinguishing agent (CO2, Powder, Foam)", "capacity rating (kg/litres)"],
        suggested_clarification_question="Please clarify the required extinguishing agent (CO2, Dry Powder, Foam) and capacity rating before standard finalization.",
        structured_evidence={
            "standard_number": "IS 15683 : 2018",
            "evidence_strength": "MODERATE",
            "scope_status": "CURATED",
            "lifecycle": {"status": "ACTIVE", "is_active": True},
            "provenance": {"source": "BIS Catalogue", "verification_status": "CURATED"}
        }
    )

    # 4. Lifecycle Concern (Cited Withdrawn Standard)
    r4 = RequirementRecommendationResult(
        requirement_id="REQ-004",
        requirement_text="Supply and delivery of deep-well submersible pumpsets strictly conforming to IS 8034 : 2002.",
        category="PRODUCT",
        explicit_standards_found=["IS 8034 : 2002"],
        candidate_standard="IS 8034 : 2002",
        title="Submersible Pumpsets - Specification (Second Revision)",
        status="Withdrawn",
        version_role="REPLACED_OR_SUPERSEDED",
        relevance_score=0.90,
        confidence="High",
        evidence="Explicit citation of withdrawn standard.",
        provenance="VERIFIED",
        human_review_required=True,
        reason="Cited standard is withdrawn in official BIS records.",
        risk_level="HIGH",
        risk_reasons=["Tender cites withdrawn standard IS 8034 : 2002."],
        critic_result={"decision": "REVIEW_REQUIRED", "risk_level": "HIGH", "evidence": {"evidence_strength": "STRONG", "grounded": True}},
        structured_evidence={
            "standard_number": "IS 8034 : 2002",
            "evidence_strength": "STRONG",
            "scope_status": "AUTHORITATIVE_VERIFIED",
            "lifecycle": {"status": "WITHDRAWN", "is_active": False, "is_withdrawn": True},
            "relationships": {
                "superseded_by": [{"target_standard": "IS 8034 : 2018", "evidence": "Official BIS Third Revision"}],
                "supersedes": []
            },
            "provenance": {"source": "BIS Production DB", "verification_status": "VERIFIED"}
        }
    )

    # 5. Potential Standards Coverage Gap
    r5 = RequirementRecommendationResult(
        requirement_id="REQ-005",
        requirement_text="Design, fabrication, and testing of specialized cryogenic liquid helium transfer siphon with vacuum superinsulation operating at 4.2 Kelvin.",
        category="PRODUCT",
        explicit_standards_found=[],
        candidate_standard=None,
        title="No Supported Standard",
        status="Unknown",
        version_role="REFERENCE_ONLY",
        relevance_score=0.0,
        confidence="Low",
        evidence="No matching Indian Standard identified in available catalogue.",
        provenance="UNKNOWN",
        human_review_required=True,
        reason="No applicable standard in catalogue.",
        risk_level="HIGH",
        applicability_status="NOT_APPLICABLE",
        critic_result={"decision": "INSUFFICIENT_EVIDENCE", "risk_level": "HIGH", "evidence": {"evidence_strength": "NONE", "grounded": False}},
        structured_evidence={
            "standard_number": None,
            "evidence_strength": "NONE",
            "scope_status": "UNKNOWN",
            "lifecycle": {"status": "UNKNOWN", "is_unknown": True},
            "provenance": {"source": "UNKNOWN", "verification_status": "UNKNOWN"}
        }
    )

    demo_results = [r1, r2, r3, r4, r5]

    # Run Tender Audit Engine
    report: StructuredTenderAuditReport = audit_engine.generate_audit_report(demo_results, tender_id="TENDER-DEMO-2026")

    # Display Executive Summary
    summary = report.summary
    print("=" * 80)
    print(f" TENDER AUDIT SUMMARY [{report.tender_id}]")
    print("=" * 80)
    print(f" Total Requirements Analyzed       : {summary.requirements_analyzed}")
    print(f" Requirements with Supported Standards: {summary.supported_standards_count}")
    print(f" Multi-Standard Requirements       : {summary.multi_standard_count}")
    print(f" Requirements Needing Clarification: {summary.clarification_required_count}")
    print(f" Requirements with Lifecycle Concerns: {summary.lifecycle_concern_count}")
    print(f" Potential Standards Coverage Gaps : {summary.potential_gap_count}")
    print(f" Total Human Review Queue Items    : {len(report.human_review_queue)}")
    print("-" * 80)
    print(f" Coverage State Distribution       : {summary.coverage_distribution}")
    print("=" * 80 + "\n")

    # Display Coverage Matrix
    print(" STANDARDS COVERAGE MATRIX:")
    print("-" * 80)
    print(f" {'REQ ID':<10} | {'COVERAGE STATE':<16} | {'PRIMARY STANDARD(S)':<22} | {'ACTION REQUIRED'}")
    print("-" * 80)
    for cov in report.coverage_matrix:
        stds_str = ", ".join(cov.primary_standards) if cov.primary_standards else "None"
        if cov.findings:
            f0 = cov.findings[0]
            action = f0.get("review_action") if isinstance(f0, dict) else getattr(f0, "review_action", "Proceed")
        else:
            action = "Proceed"
        print(f" {cov.requirement_id:<10} | {cov.coverage_state:<16} | {stds_str:<22} | {action[:32]}...")
    print("-" * 80 + "\n")

    # Deep-Dive Drill-Down into Lifecycle Finding (REQ-004)
    print("=" * 80)
    print(" DEEP-DIVE AUDIT FINDING TRACE [REQ-004: Cited Withdrawn Standard]")
    print("=" * 80)
    req4_item = next(item for item in report.coverage_matrix if item.requirement_id == "REQ-004")
    f = req4_item.findings[0]
    get_f = lambda k, default="": f.get(k, default) if isinstance(f, dict) else getattr(f, k, default)
    print(f" Requirement ID         : {get_f('requirement_id')}")
    print(f" Requirement Text       : {req4_item.requirement_text}")
    print(f" Finding Type           : {get_f('finding_type')}")
    print(f" Standard Cited         : {', '.join(get_f('standards', []))}")
    print(f" Lifecycle Status       : {get_f('lifecycle_status')}")
    print(f" Lifecycle Note         : {get_f('lifecycle_note')}")
    print(f" Evidence Strength      : {get_f('evidence_strength')}")
    prov = get_f('provenance', {})
    print(f" Provenance Source      : {prov.get('source') if isinstance(prov, dict) else getattr(prov, 'source', 'N/A')}")
    print(f" Uncertainty            : {get_f('uncertainty')}")
    print(f" Human Review Required  : {get_f('human_review_required')}")
    print(f" Review Action          : {get_f('review_action')}")
    print("=" * 80 + "\n")

    # Deep-Dive Drill-Down into Gap Finding (REQ-005)
    print("=" * 80)
    print(" DEEP-DIVE AUDIT FINDING TRACE [REQ-005: Potential Standards Gap]")
    print("=" * 80)
    req5_item = next(item for item in report.coverage_matrix if item.requirement_id == "REQ-005")
    f_gap = req5_item.findings[0]
    get_gap = lambda k, default="": f_gap.get(k, default) if isinstance(f_gap, dict) else getattr(f_gap, k, default)
    print(f" Requirement ID         : {get_gap('requirement_id')}")
    print(f" Requirement Text       : {req5_item.requirement_text}")
    print(f" Finding Type           : {get_gap('finding_type')}")
    print(f" Coverage State         : {req5_item.coverage_state}")
    print(f" Standards Found        : {get_gap('standards') or 'None'}")
    print(f" Uncertainty Disclaimer : {get_gap('uncertainty')}")
    print(f" Review Action          : {get_gap('review_action')}")
    print("=" * 80 + "\n")

    print(" DEMO COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_phase4_demo()
