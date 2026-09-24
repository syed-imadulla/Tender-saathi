"""
Module: src/audit.py
Purpose: Tender Audit & Standards Gap Intelligence Engine for TenderSaathi.

Extends TenderSaathi from RETRIEVE → APPLY → DECIDE → EXPLAIN to AUDIT.
Aggregates requirement-level recommendation, critic, applicability, ambiguity,
and structured evidence results into a comprehensive, deterministic,
evidence-backed tender-level standards review audit.

IMPORTANT PRINCIPLES:
- Deterministic, evidence-backed standards review audit for procurement officers.
- Does NOT constitute legal compliance certification.
- Never asserts "compliant", "non-compliant", "legally valid", or "legally invalid".
- Strictly deterministic: no LLMs, no arbitrary percentage scores.
- Preserves the distinction between authoritative, curated, inferred, and unknown evidence.
- POTENTIAL_GAP means: "The system could not establish sufficient standards coverage
  from the available evidence. This does NOT indicate that no Indian Standard exists."
- COVERED means: "Available evidence supports applicable standards for the analyzed
  requirement/components, with no unresolved blocker. (Does not imply legal certification)."
- Withdrawn standards trigger lifecycle review findings; never automatically replaced
  unless an authoritative replacement relationship is verified in the BIS catalogue.
- Categorizes publication readiness as:
    - READY_FOR_REVIEW
    - REVIEW_REQUIRED
    - INSUFFICIENT_EVIDENCE
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from src.recommend import RequirementRecommendationResult, TenderRecommendationReport


# ---------------------------------------------------------------------------
# Phase 4 Categorical Enums and State Constants
# ---------------------------------------------------------------------------

class CoverageState:
    """Explicit standards coverage states for requirements across a tender."""
    COVERED = "COVERED"
    PARTIAL = "PARTIAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    POTENTIAL_GAP = "POTENTIAL_GAP"
    UNKNOWN = "UNKNOWN"


class AuditFindingType:
    """Deterministic categorization of tender-level standards audit findings."""
    STANDARD_COVERED = "STANDARD_COVERED"
    PARTIAL_STANDARD_COVERAGE = "PARTIAL_STANDARD_COVERAGE"
    POTENTIAL_STANDARD_GAP = "POTENTIAL_STANDARD_GAP"
    LIFECYCLE_CONCERN = "LIFECYCLE_CONCERN"
    LIFECYCLE_DEPENDENCY_SUPERSEDED = "LIFECYCLE_DEPENDENCY_SUPERSEDED"
    EXTERNAL_STATUTORY_SIGNAL = "EXTERNAL_STATUTORY_SIGNAL"
    MULTI_COMPONENT_COVERAGE = "MULTI_COMPONENT_COVERAGE"
    AMBIGUOUS_REQUIREMENT = "AMBIGUOUS_REQUIREMENT"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class ReviewQueueCategory:
    """Actionable human review routing categories."""
    HIGH_PRIORITY_REVIEW = "HIGH_PRIORITY_REVIEW"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    LIFECYCLE_REVIEW = "LIFECYCLE_REVIEW"
    POTENTIAL_COVERAGE_GAP = "POTENTIAL_COVERAGE_GAP"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"


# ---------------------------------------------------------------------------
# Phase 4 Data Models
# ---------------------------------------------------------------------------

@dataclass
class AuditFinding:
    """Represents an atomic, evidence-backed finding from the tender audit."""
    finding_id: str
    requirement_id: str
    finding_type: str                     # From AuditFindingType
    title: str
    standards: List[str] = field(default_factory=list)
    applicability_decision: str = "UNKNOWN"
    evidence_strength: str = "NONE"       # STRONG, MODERATE, WEAK, NONE
    supporting_facts: List[str] = field(default_factory=list)
    lifecycle_status: str = "UNKNOWN"     # ACTIVE, WITHDRAWN, UNKNOWN
    lifecycle_note: Optional[str] = None
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    uncertainty: str = ""
    human_review_required: bool = False
    review_action: str = ""
    severity: str = "INFO"                # CRITICAL, HIGH, MEDIUM, LOW, INFO

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequirementCoverageItem:
    """Standards coverage evaluation for a single tender requirement."""
    requirement_id: str
    requirement_text: str
    coverage_state: str                   # COVERED, PARTIAL, REVIEW_REQUIRED, POTENTIAL_GAP, UNKNOWN
    primary_standards: List[str] = field(default_factory=list)
    component_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    gap_details: Optional[Dict[str, Any]] = None
    lifecycle_concerns: List[Dict[str, Any]] = field(default_factory=list)
    ambiguity_details: Optional[Dict[str, Any]] = None
    lifecycle_warnings: List[Dict[str, Any]] = field(default_factory=list)
    external_regulations: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[AuditFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["findings"] = [f.to_dict() if hasattr(f, "to_dict") else f for f in self.findings]
        return d


@dataclass
class TenderAuditSummary:
    """Tender-wide aggregation metrics for executive standards oversight."""
    requirements_analyzed: int
    supported_standards_count: int
    safe_abstention_count: int
    clarification_required_count: int
    lifecycle_concern_count: int
    potential_gap_count: int
    multi_standard_count: int
    human_review_count: int
    coverage_distribution: Dict[str, int]
    finding_distribution: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewQueueItem:
    """Represents a prioritized requirement flagged for human technical review."""
    requirement_id: str
    requirement_text: str
    risk_level: str                       # CRITICAL, HIGH, MEDIUM, LOW
    decision: str                         # REVIEW_REQUIRED, RECOMMEND_WITH_REVIEW, INSUFFICIENT_EVIDENCE, REJECT
    candidate_standard: str
    evidence_strength: str                # STRONG, MODERATE, WEAK, NONE
    primary_reason: str
    priority: int                         # 1 (Highest / CRITICAL) to 4 (Lowest / LOW)
    category: str = "HIGH_PRIORITY_REVIEW"# From ReviewQueueCategory
    component_id: Optional[str] = None
    review_action: str = ""
    uncertainty: str = ""
    what_to_check: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StructuredTenderAuditReport:
    """Complete machine-readable tender audit report."""
    tender_id: str
    summary: TenderAuditSummary
    coverage_matrix: List[RequirementCoverageItem] = field(default_factory=list)
    covered_requirements: List[RequirementCoverageItem] = field(default_factory=list)
    potential_gaps: List[AuditFinding] = field(default_factory=list)
    lifecycle_concerns: List[AuditFinding] = field(default_factory=list)
    ambiguous_requirements: List[AuditFinding] = field(default_factory=list)
    multi_standard_requirements: List[RequirementCoverageItem] = field(default_factory=list)
    evidence_audit: Dict[str, Any] = field(default_factory=dict)
    human_review_queue: List[ReviewQueueItem] = field(default_factory=list)
    disclaimers_and_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tender_id": self.tender_id,
            "summary": self.summary.to_dict(),
            "coverage_matrix": [item.to_dict() for item in self.coverage_matrix],
            "covered_requirements": [item.to_dict() for item in self.covered_requirements],
            "potential_gaps": [g.to_dict() for g in self.potential_gaps],
            "lifecycle_concerns": [l.to_dict() for l in self.lifecycle_concerns],
            "ambiguous_requirements": [a.to_dict() for a in self.ambiguous_requirements],
            "multi_standard_requirements": [m.to_dict() for m in self.multi_standard_requirements],
            "evidence_audit": self.evidence_audit,
            "human_review_queue": [q.to_dict() for q in self.human_review_queue],
            "disclaimers_and_notes": self.disclaimers_and_notes,
        }


@dataclass
class TenderAuditResult:
    """Tender-level audit and publication readiness evaluation."""
    tender_id: str
    requirements_analyzed: int
    recommendations_count: int
    review_required_count: int
    insufficient_evidence_count: int
    superseded_count: int
    withdrawn_count: int
    active_count: int
    unknown_lifecycle_count: int
    evidence_distribution: Dict[str, int]
    completeness_distribution: Dict[str, int]
    risk_distribution: Dict[str, int]
    lifecycle_distribution: Dict[str, int]
    related_standards_count: int
    review_queue: List[ReviewQueueItem] = field(default_factory=list)
    publication_readiness: str = "REVIEW_REQUIRED"
    readiness_reasons: List[str] = field(default_factory=list)
    readiness_note: str = (
        "Deterministic, evidence-backed standards review audit for procurement officers. "
        "Does NOT constitute legal compliance certification."
    )
    # Milestone 10 Standards Dependency & Coverage metrics:
    dependency_count: int = 0
    normative_reference_count: int = 0
    allied_standard_count: int = 0
    test_standard_count: int = 0
    installation_standard_count: int = 0
    verified_missing_count: int = 0
    potentially_missing_count: int = 0
    related_for_review_count: int = 0
    standards_coverage: Dict[str, Any] = field(default_factory=dict)
    gap_summary: Dict[str, Any] = field(default_factory=dict)
    # Milestone 11 Regulatory Intelligence metrics:
    certification_checks: int = 0
    qco_checks: int = 0
    crs_checks: int = 0
    hallmarking_checks: int = 0
    regulatory_review_items: int = 0
    unknown_regulatory_items: int = 0
    upcoming_qco_items: int = 0
    mandatory_qco_count: int = 0
    mandatory_certification_count: int = 0
    crs_applicable_count: int = 0
    hallmarking_applicable_count: int = 0
    # Phase 4 Tender Audit & Standards Gap Intelligence metrics & artifacts:
    supported_standards_count: int = 0
    safe_abstention_count: int = 0
    clarification_required_count: int = 0
    lifecycle_concern_count: int = 0
    potential_gap_count: int = 0
    multi_standard_count: int = 0
    human_review_count: int = 0
    coverage_distribution: Dict[str, int] = field(default_factory=dict)
    audit_summary: Optional[Dict[str, Any]] = None
    coverage_matrix: List[Dict[str, Any]] = field(default_factory=list)
    audit_findings: List[Dict[str, Any]] = field(default_factory=list)
    gap_findings: List[Dict[str, Any]] = field(default_factory=list)
    lifecycle_findings: List[Dict[str, Any]] = field(default_factory=list)
    ambiguity_findings: List[Dict[str, Any]] = field(default_factory=list)
    multi_standard_items: List[Dict[str, Any]] = field(default_factory=list)
    structured_audit_report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["review_queue"] = [item.to_dict() for item in self.review_queue]
        return d


# ---------------------------------------------------------------------------
# Priority Mapping
# ---------------------------------------------------------------------------

RISK_PRIORITY = {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4
}

EVIDENCE_SEVERITY = {
    "NONE": 1,
    "WEAK": 2,
    "MODERATE": 3,
    "STRONG": 4
}

COMPLETENESS_SEVERITY = {
    "UNKNOWN": 1,
    "POTENTIALLY_MISSING": 2,
    "NOT_APPLICABLE": 3,
    "KNOWN": 4
}

AUDIT_DISCLAIMERS = [
    "Deterministic, evidence-backed standards review audit for procurement officers. Does NOT constitute legal compliance certification.",
    "A status of COVERED indicates that available evidence supports applicable standards for the analyzed requirement/components, with no unresolved blocker. It does not imply legal compliance or certification.",
    "A status of POTENTIAL_GAP indicates that the system could not establish sufficient standards coverage from the available evidence. This does NOT indicate that no Indian Standard exists.",
    "Withdrawn standards require technical review. Automatic substitution is strictly prohibited unless an authoritative replacement relationship is verified in the BIS catalogue.",
    "Safe abstentions and ambiguous specifications route to the human review queue with targeted clarification questions rather than speculative standard assignments."
]


# ---------------------------------------------------------------------------
# Tender Audit Engine
# ---------------------------------------------------------------------------

class TenderAuditEngine:
    """
    Deterministic audit engine aggregating requirement-level recommendation results
    into tender-level standards review metrics, coverage matrix, gap intelligence,
    lifecycle audits, ambiguity summaries, and a prioritized review queue.
    """

    def __init__(self, db: Optional[Any] = None):
        self.db = db

    def audit_tender(
        self,
        results: List[RequirementRecommendationResult],
        tender_id: str = "TENDER_AUDIT"
    ) -> TenderAuditResult:
        """Audits a list of requirement recommendation results for a tender."""
        requirements_analyzed = len(results)

        # Handle edge case: Empty tender / zero requirements
        if requirements_analyzed == 0:
            empty_summary = TenderAuditSummary(
                requirements_analyzed=0,
                supported_standards_count=0,
                safe_abstention_count=0,
                clarification_required_count=0,
                lifecycle_concern_count=0,
                potential_gap_count=0,
                multi_standard_count=0,
                human_review_count=0,
                coverage_distribution={
                    CoverageState.COVERED: 0,
                    CoverageState.PARTIAL: 0,
                    CoverageState.REVIEW_REQUIRED: 0,
                    CoverageState.POTENTIAL_GAP: 0,
                    CoverageState.UNKNOWN: 0
                },
                finding_distribution={}
            )
            empty_report = StructuredTenderAuditReport(
                tender_id=tender_id,
                summary=empty_summary,
                coverage_matrix=[],
                covered_requirements=[],
                potential_gaps=[],
                lifecycle_concerns=[],
                ambiguous_requirements=[],
                multi_standard_requirements=[],
                evidence_audit={},
                human_review_queue=[],
                disclaimers_and_notes=AUDIT_DISCLAIMERS
            )
            return TenderAuditResult(
                tender_id=tender_id,
                requirements_analyzed=0,
                recommendations_count=0,
                review_required_count=0,
                insufficient_evidence_count=0,
                superseded_count=0,
                withdrawn_count=0,
                active_count=0,
                unknown_lifecycle_count=0,
                evidence_distribution={"STRONG": 0, "MODERATE": 0, "WEAK": 0, "NONE": 0},
                completeness_distribution={"KNOWN": 0, "POTENTIALLY_MISSING": 0, "UNKNOWN": 0, "NOT_APPLICABLE": 0},
                risk_distribution={"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
                lifecycle_distribution={"Active": 0, "Superseded": 0, "Withdrawn": 0, "Unknown": 0},
                related_standards_count=0,
                review_queue=[],
                publication_readiness="INSUFFICIENT_EVIDENCE",
                readiness_reasons=["No requirements identified in tender for standards review."],
                coverage_distribution={
                    CoverageState.COVERED: 0,
                    CoverageState.PARTIAL: 0,
                    CoverageState.REVIEW_REQUIRED: 0,
                    CoverageState.POTENTIAL_GAP: 0,
                    CoverageState.UNKNOWN: 0
                },
                audit_summary=empty_summary.to_dict(),
                coverage_matrix=[],
                audit_findings=[],
                gap_findings=[],
                lifecycle_findings=[],
                ambiguity_findings=[],
                multi_standard_items=[],
                structured_audit_report=empty_report.to_dict()
            )

        # Initialize distribution counters
        evidence_dist = {"STRONG": 0, "MODERATE": 0, "WEAK": 0, "NONE": 0}
        completeness_dist = {"KNOWN": 0, "POTENTIALLY_MISSING": 0, "UNKNOWN": 0, "NOT_APPLICABLE": 0}
        risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        lifecycle_dist = {"Active": 0, "Superseded": 0, "Withdrawn": 0, "Unknown": 0}

        recommendations_count = 0
        review_required_count = 0
        insufficient_evidence_count = 0
        related_standards_count = 0

        review_queue: List[ReviewQueueItem] = []

        # Phase 4 Aggregation structures
        coverage_matrix_items: List[RequirementCoverageItem] = []
        all_findings: List[AuditFinding] = []
        gap_findings: List[AuditFinding] = []
        lifecycle_findings: List[AuditFinding] = []
        ambiguity_findings: List[AuditFinding] = []
        multi_standard_items: List[RequirementCoverageItem] = []
        covered_requirements: List[RequirementCoverageItem] = []

        supported_standards_count = 0
        safe_abstention_count = 0
        clarification_required_count = 0
        potential_gap_count = 0
        multi_standard_count = 0
        human_review_count = 0

        coverage_dist = {
            CoverageState.COVERED: 0,
            CoverageState.PARTIAL: 0,
            CoverageState.REVIEW_REQUIRED: 0,
            CoverageState.POTENTIAL_GAP: 0,
            CoverageState.UNKNOWN: 0
        }
        finding_dist: Dict[str, int] = {}

        for r in results:
            # 1. Resolve Evidence Strength
            ev_strength = self._extract_evidence_strength(r)
            evidence_dist[ev_strength] = evidence_dist.get(ev_strength, 0) + 1

            # 2. Resolve Specification Completeness
            comp_label = self._extract_completeness_label(r)
            completeness_dist[comp_label] = completeness_dist.get(comp_label, 0) + 1

            # 3. Resolve Risk Level
            risk_lvl = (r.risk_level or "LOW").upper()
            if risk_lvl not in risk_dist:
                risk_lvl = "LOW"
            risk_dist[risk_lvl] = risk_dist.get(risk_lvl, 0) + 1

            # 4. Resolve Lifecycle Status
            life_status = self._extract_lifecycle_status(r)
            lifecycle_dist[life_status] = lifecycle_dist.get(life_status, 0) + 1

            # 5. Related standards count
            rel_stds = getattr(r, "related_standards", None) or []
            related_standards_count += len(rel_stds)

            # 6. Standards Review Decision Categorization (Preserve Conservation Law)
            crit_res = getattr(r, "critic_result", None) or {}
            decision = crit_res.get("decision") or ("REVIEW_REQUIRED" if r.human_review_required else "RECOMMEND")
            is_review_req = bool(r.human_review_required or decision in ["REVIEW_REQUIRED", "RECOMMEND_WITH_REVIEW"])

            is_insufficient = (
                decision == "INSUFFICIENT_EVIDENCE" or
                r.candidate_standard in ["INSUFFICIENT_INFORMATION", "", "UNKNOWN", "NONE", None]
            )

            if is_insufficient:
                insufficient_evidence_count += 1
            elif is_review_req:
                review_required_count += 1
            else:
                recommendations_count += 1

            # -------------------------------------------------------------------
            # Phase 4 Requirement Coverage & Intelligence Evaluation
            # -------------------------------------------------------------------
            cov_item, req_findings, queue_cat, queue_action = self._evaluate_requirement_coverage(
                r=r,
                life_status=life_status,
                comp_label=comp_label,
                ev_strength=ev_strength,
                decision=decision,
                is_insufficient=is_insufficient
            )
            coverage_matrix_items.append(cov_item)
            all_findings.extend(req_findings)

            # Update coverage distribution
            coverage_dist[cov_item.coverage_state] = coverage_dist.get(cov_item.coverage_state, 0) + 1

            # Track findings by type
            for f in req_findings:
                finding_dist[f.finding_type] = finding_dist.get(f.finding_type, 0) + 1
                if f.finding_type == AuditFindingType.POTENTIAL_STANDARD_GAP:
                    gap_findings.append(f)
                elif f.finding_type == AuditFindingType.LIFECYCLE_CONCERN:
                    lifecycle_findings.append(f)
                elif f.finding_type in [AuditFindingType.AMBIGUOUS_REQUIREMENT, AuditFindingType.CLARIFICATION_REQUIRED]:
                    ambiguity_findings.append(f)

            # Track specific categories
            if cov_item.coverage_state == CoverageState.COVERED:
                covered_requirements.append(cov_item)
                supported_standards_count += 1
            elif cov_item.coverage_state == CoverageState.POTENTIAL_GAP:
                potential_gap_count += 1

            if len(cov_item.component_breakdown) > 1 or cov_item.coverage_state == CoverageState.PARTIAL:
                multi_standard_items.append(cov_item)
                multi_standard_count += 1

            is_safe_abstention = (
                getattr(r, "ambiguity_state", "") == "SAFE_ABSTENTION_GENUINE_AMBIGUITY" or
                (is_insufficient and r.human_review_required and getattr(r, "ambiguity_state", "CLEAR") != "CLEAR")
            )
            if is_safe_abstention:
                safe_abstention_count += 1

            if any(f.finding_type in [AuditFindingType.CLARIFICATION_REQUIRED, AuditFindingType.AMBIGUOUS_REQUIREMENT] for f in req_findings):
                clarification_required_count += 1

            if any(f.human_review_required for f in req_findings) or cov_item.coverage_state in [CoverageState.REVIEW_REQUIRED, CoverageState.POTENTIAL_GAP, CoverageState.PARTIAL]:
                human_review_count += 1

            # 7. Check if Item belongs in the Human Review Queue (Preserve ReviewQueueItem contract)
            needs_queue = (
                is_review_req or
                is_insufficient or
                risk_lvl in ["CRITICAL", "HIGH", "MEDIUM"] or
                life_status in ["Superseded", "Withdrawn"] or
                cov_item.coverage_state in [CoverageState.POTENTIAL_GAP, CoverageState.PARTIAL]
            )

            if needs_queue:
                primary_reason = self._determine_primary_reason(r, life_status, comp_label, ev_strength)
                priority_val = RISK_PRIORITY.get(risk_lvl, 3)

                review_queue.append(ReviewQueueItem(
                    requirement_id=r.requirement_id or "REQ-UNKNOWN",
                    requirement_text=r.requirement_text or "",
                    risk_level=risk_lvl,
                    decision=decision,
                    candidate_standard=r.candidate_standard or "NONE",
                    evidence_strength=ev_strength,
                    primary_reason=primary_reason,
                    priority=priority_val,
                    category=queue_cat,
                    review_action=queue_action,
                    uncertainty=cov_item.gap_details.get("uncertainty", "") if cov_item.gap_details else "",
                    what_to_check=primary_reason
                ))

        # Aggregate Milestone 10 Standards Dependency & Coverage metrics
        dependency_count = 0
        normative_ref_count = 0
        allied_std_count = 0
        test_std_count = 0
        install_std_count = 0
        ver_missing_count = 0
        pot_missing_count = 0
        rel_review_count = 0

        for r in results:
            deps = getattr(r, "dependencies", []) or []
            dependency_count += len(deps)
            for d in deps:
                rtype = d.get("relationship_type", "")
                if rtype in ["NORMATIVE_REFERENCE", "REFERENCES"]:
                    normative_ref_count += 1
                elif rtype == "TEST_METHOD":
                    test_std_count += 1
                elif rtype in ["INSTALLATION_STANDARD", "CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"]:
                    install_std_count += 1
                elif rtype == "ALLIED_STANDARD":
                    allied_std_count += 1

            vm = getattr(r, "verified_missing", []) or []
            pm = getattr(r, "potentially_missing", []) or []
            rr = getattr(r, "related_for_review", []) or []
            ver_missing_count += len(vm)
            pot_missing_count += len(pm)
            rel_review_count += len(rr)

        # Aggregate Milestone 11 Regulatory Intelligence metrics
        certification_checks = 0
        qco_checks = 0
        crs_checks = 0
        hallmarking_checks = 0
        regulatory_review_items = 0
        unknown_regulatory_items = 0
        upcoming_qco_items = 0
        mandatory_qco_count = 0
        mandatory_certification_count = 0
        crs_applicable_count = 0
        hallmarking_applicable_count = 0

        for r in results:
            reg = getattr(r, "regulatory", None) or {}
            if reg:
                cert = reg.get("certification") or {}
                qco = reg.get("qco") or {}
                crs = reg.get("crs") or {}
                hm = reg.get("hallmarking") or {}

                if cert:
                    certification_checks += 1
                    if cert.get("status") == "APPLICABLE":
                        mandatory_certification_count += 1
                    if cert.get("human_review_required"):
                        regulatory_review_items += 1
                    if cert.get("status") == "UNKNOWN":
                        unknown_regulatory_items += 1

                if qco:
                    qco_checks += 1
                    if qco.get("status") == "CURRENT":
                        mandatory_qco_count += 1
                    elif qco.get("status") == "UPCOMING":
                        upcoming_qco_items += 1
                    if qco.get("status") == "UNKNOWN":
                        unknown_regulatory_items += 1

                if crs:
                    crs_checks += 1
                    if crs.get("status") == "APPLICABLE":
                        crs_applicable_count += 1
                    if crs.get("status") == "UNKNOWN":
                        unknown_regulatory_items += 1

                if hm:
                    hallmarking_checks += 1
                    if hm.get("status") == "APPLICABLE":
                        hallmarking_applicable_count += 1
                    if hm.get("status") == "UNKNOWN":
                        unknown_regulatory_items += 1

        # Sort Review Queue: CRITICAL (1) -> HIGH (2) -> MEDIUM (3) -> LOW (4)
        review_queue.sort(
            key=lambda item: (
                item.priority,
                EVIDENCE_SEVERITY.get(item.evidence_strength, 5),
                item.requirement_id
            )
        )

        superseded_count = lifecycle_dist["Superseded"]
        withdrawn_count = lifecycle_dist["Withdrawn"]
        active_count = lifecycle_dist["Active"]
        unknown_lifecycle_count = lifecycle_dist["Unknown"]

        # 8. Determine Publication Readiness
        readiness, readiness_reasons = self._determine_publication_readiness(
            requirements_analyzed=requirements_analyzed,
            recommendations_count=recommendations_count,
            review_required_count=review_required_count,
            insufficient_evidence_count=insufficient_evidence_count,
            superseded_count=superseded_count,
            withdrawn_count=withdrawn_count,
            risk_dist=risk_dist,
            evidence_dist=evidence_dist,
            completeness_dist=completeness_dist
        )

        # Standards coverage map summary
        covered_deps = sum(
            1 for r in results
            for d in (getattr(r, "standards_coverage", {}) or {}).get("dependencies_coverage", [])
            if d.get("coverage_status") == "COVERED_IN_TENDER"
        )
        standards_coverage = {
            "direct_standards_identified": recommendations_count + review_required_count,
            "total_dependencies": dependency_count,
            "normative_references": normative_ref_count,
            "testing_dependencies": test_std_count,
            "installation_dependencies": install_std_count,
            "allied_standards": allied_std_count,
            "covered_in_tender": covered_deps,
            "potential_gaps": pot_missing_count,
            "verified_gaps": ver_missing_count,
            "items_requiring_review": review_required_count
        }
        gap_summary = {
            "verified_missing_count": ver_missing_count,
            "potentially_missing_count": pot_missing_count,
            "related_for_review_count": rel_review_count
        }

        # Build Phase 4 Tender Audit Summary
        audit_summary = TenderAuditSummary(
            requirements_analyzed=requirements_analyzed,
            supported_standards_count=supported_standards_count,
            safe_abstention_count=safe_abstention_count,
            clarification_required_count=clarification_required_count,
            lifecycle_concern_count=len(lifecycle_findings),
            potential_gap_count=potential_gap_count,
            multi_standard_count=multi_standard_count,
            human_review_count=human_review_count,
            coverage_distribution=coverage_dist,
            finding_distribution=finding_dist
        )

        # Build Phase 4 Structured Tender Audit Report
        evidence_audit = {
            "evidence_distribution": evidence_dist,
            "provenance_distribution": {
                "VERIFIED": sum(1 for r in results if getattr(r, "provenance", "").upper() == "VERIFIED"),
                "CURATED": sum(1 for r in results if getattr(r, "provenance", "").upper() == "CURATED"),
                "INFERRED": sum(1 for r in results if getattr(r, "provenance", "").upper() == "INFERRED"),
                "UNKNOWN": sum(1 for r in results if getattr(r, "provenance", "").upper() not in ["VERIFIED", "CURATED", "INFERRED"])
            },
            "scope_status_distribution": {
                "AUTHORITATIVE_VERIFIED": sum(1 for r in results if (getattr(r, "structured_evidence", {}) or {}).get("scope_status") == "AUTHORITATIVE_VERIFIED"),
                "CURATED": sum(1 for r in results if (getattr(r, "structured_evidence", {}) or {}).get("scope_status") == "CURATED"),
                "UNKNOWN": sum(1 for r in results if (getattr(r, "structured_evidence", {}) or {}).get("scope_status") not in ["AUTHORITATIVE_VERIFIED", "CURATED"])
            }
        }

        structured_report = StructuredTenderAuditReport(
            tender_id=tender_id,
            summary=audit_summary,
            coverage_matrix=coverage_matrix_items,
            covered_requirements=covered_requirements,
            potential_gaps=gap_findings,
            lifecycle_concerns=lifecycle_findings,
            ambiguous_requirements=ambiguity_findings,
            multi_standard_requirements=multi_standard_items,
            evidence_audit=evidence_audit,
            human_review_queue=review_queue,
            disclaimers_and_notes=AUDIT_DISCLAIMERS
        )

        return TenderAuditResult(
            tender_id=tender_id,
            requirements_analyzed=requirements_analyzed,
            recommendations_count=recommendations_count,
            review_required_count=review_required_count,
            insufficient_evidence_count=insufficient_evidence_count,
            superseded_count=superseded_count,
            withdrawn_count=withdrawn_count,
            active_count=active_count,
            unknown_lifecycle_count=unknown_lifecycle_count,
            evidence_distribution=evidence_dist,
            completeness_distribution=completeness_dist,
            risk_distribution=risk_dist,
            lifecycle_distribution=lifecycle_dist,
            related_standards_count=related_standards_count,
            review_queue=review_queue,
            publication_readiness=readiness,
            readiness_reasons=readiness_reasons,
            dependency_count=dependency_count,
            normative_reference_count=normative_ref_count,
            allied_standard_count=allied_std_count,
            test_standard_count=test_std_count,
            installation_standard_count=install_std_count,
            verified_missing_count=ver_missing_count,
            potentially_missing_count=pot_missing_count,
            related_for_review_count=rel_review_count,
            standards_coverage=standards_coverage,
            gap_summary=gap_summary,
            certification_checks=certification_checks,
            qco_checks=qco_checks,
            crs_checks=crs_checks,
            hallmarking_checks=hallmarking_checks,
            regulatory_review_items=regulatory_review_items,
            unknown_regulatory_items=unknown_regulatory_items,
            upcoming_qco_items=upcoming_qco_items,
            mandatory_qco_count=mandatory_qco_count,
            mandatory_certification_count=mandatory_certification_count,
            crs_applicable_count=crs_applicable_count,
            hallmarking_applicable_count=hallmarking_applicable_count,
            supported_standards_count=supported_standards_count,
            safe_abstention_count=safe_abstention_count,
            clarification_required_count=clarification_required_count,
            lifecycle_concern_count=len(lifecycle_findings),
            potential_gap_count=potential_gap_count,
            multi_standard_count=multi_standard_count,
            human_review_count=human_review_count,
            coverage_distribution=coverage_dist,
            audit_summary=audit_summary.to_dict(),
            coverage_matrix=[item.to_dict() for item in coverage_matrix_items],
            audit_findings=[f.to_dict() for f in all_findings],
            gap_findings=[g.to_dict() for g in gap_findings],
            lifecycle_findings=[l.to_dict() for l in lifecycle_findings],
            ambiguity_findings=[a.to_dict() for a in ambiguity_findings],
            multi_standard_items=[m.to_dict() for m in multi_standard_items],
            structured_audit_report=structured_report.to_dict()
        )

    def audit_report(self, report: TenderRecommendationReport) -> TenderAuditResult:
        """Audits a TenderRecommendationReport produced by the recommendation pipeline."""
        return self.audit_tender(report.results, tender_id=report.tender_id)

    def generate_audit_report(
        self,
        results: List[RequirementRecommendationResult],
        tender_id: str = "TENDER_AUDIT"
    ) -> StructuredTenderAuditReport:
        """Direct method returning the typed StructuredTenderAuditReport model."""
        res = self.audit_tender(results, tender_id=tender_id)
        # Parse back into the StructuredTenderAuditReport
        return StructuredTenderAuditReport(
            tender_id=tender_id,
            summary=TenderAuditSummary(**res.audit_summary),
            coverage_matrix=[RequirementCoverageItem(**item) for item in res.coverage_matrix],
            covered_requirements=[RequirementCoverageItem(**item) for item in res.coverage_matrix if item["coverage_state"] == CoverageState.COVERED],
            potential_gaps=[AuditFinding(**g) for g in res.gap_findings],
            lifecycle_concerns=[AuditFinding(**l) for l in res.lifecycle_findings],
            ambiguous_requirements=[AuditFinding(**a) for a in res.ambiguity_findings],
            multi_standard_requirements=[RequirementCoverageItem(**item) for item in res.multi_standard_items],
            evidence_audit=res.structured_audit_report.get("evidence_audit", {}) if res.structured_audit_report else {},
            human_review_queue=res.review_queue,
            disclaimers_and_notes=AUDIT_DISCLAIMERS
        )

    # -----------------------------------------------------------------------
    # Phase 4 Intelligence Evaluation Helpers
    # -----------------------------------------------------------------------

    def _evaluate_requirement_coverage(
        self,
        r: RequirementRecommendationResult,
        life_status: str,
        comp_label: str,
        ev_strength: str,
        decision: str,
        is_insufficient: bool
    ) -> Tuple[RequirementCoverageItem, List[AuditFinding], str, str]:
        """
        Classifies standards coverage state and synthesizes evidence-backed audit findings.
        Returns:
            (RequirementCoverageItem, List[AuditFinding], queue_category, queue_action)
        """
        req_id = r.requirement_id or "REQ-UNKNOWN"
        req_text = r.requirement_text or ""
        struct_ev = getattr(r, "structured_evidence", None) or {}
        prov_dict = struct_ev.get("provenance") or {"source": getattr(r, "provenance", "UNKNOWN"), "verification_status": getattr(r, "provenance", "UNKNOWN")}
        findings: List[AuditFinding] = []

        # 1. Lifecycle Check: Has cited standard or matched standard with lifecycle concern
        lifecycle_finding = self._check_lifecycle_concern(r, life_status, struct_ev, prov_dict)
        lifecycle_concerns = [lifecycle_finding.to_dict()] if lifecycle_finding else []
        if lifecycle_finding:
            findings.append(lifecycle_finding)

        # Phase 9: Lifecycle dependency superseded findings
        for idx, lw in enumerate(getattr(r, "lifecycle_warnings", []) or []):
            findings.append(AuditFinding(
                finding_id=f"LIFECYCLE-DEP-{req_id}-{idx+1}",
                requirement_id=req_id,
                finding_type=AuditFindingType.LIFECYCLE_DEPENDENCY_SUPERSEDED,
                title=f"Superseded Related Dependency: {lw.get('standard_number')}",
                standards=[lw.get("standard_number")] if lw.get("standard_number") else [],
                applicability_decision="REVIEW_REQUIRED",
                evidence_strength="STRONG",
                supporting_facts=[
                    f"Dependency {lw.get('standard_number')} is superseded in BIS catalogue.",
                    f"Active successor: {lw.get('active_successor') or 'No active successor recorded'}.",
                    f"Reason: {lw.get('reason') or 'Superseded'}"
                ],
                lifecycle_status="WITHDRAWN",
                lifecycle_note=f"Active successor: {lw.get('active_successor')}",
                uncertainty="Related standard is superseded; procurement specifications should update to active successor.",
                human_review_required=True,
                review_action=f"Verify substitution of {lw.get('standard_number')} with {lw.get('active_successor') or 'successor'}.",
                severity="HIGH",
                provenance={"source": "BIS_CATALOGUE", "verified": True}
            ))

        # Phase 9: External statutory signals
        for idx, es in enumerate(getattr(r, "external_regulations", []) or []):
            findings.append(AuditFinding(
                finding_id=f"STATUTORY-{req_id}-{idx+1}",
                requirement_id=req_id,
                finding_type=AuditFindingType.EXTERNAL_STATUTORY_SIGNAL,
                title=f"Statutory Advisory Signal: {es.get('authority_name')} ({es.get('statutory_instrument')})",
                standards=es.get("related_indian_standards", []),
                applicability_decision="ADVISORY_SIGNAL",
                evidence_strength="STRONG",
                supporting_facts=[
                    f"Authority: {es.get('authority_name')} ({es.get('authority_code')})",
                    f"Instrument: {es.get('statutory_instrument')}, Clause: {es.get('applicable_clause')}",
                    f"Advisory: {es.get('advisory_summary')}"
                ],
                lifecycle_status="ACTIVE",
                uncertainty="External regulatory advisory signal. Does NOT constitute legal compliance certification.",
                human_review_required=False,
                review_action=f"Review statutory compliance with {es.get('statutory_instrument')}.",
                severity="INFO",
                provenance={"source": es.get("statutory_provenance", "OFFICIAL_GAZETTE"), "verified": True}
            ))

        # 2. Administrative / Non-technical check: UNKNOWN != GAP
        if self._is_non_technical_clause(r):
            finding = AuditFinding(
                finding_id=f"ADMIN-{req_id}",
                requirement_id=req_id,
                finding_type=AuditFindingType.EVIDENCE_INSUFFICIENT,
                title="Non-technical or administrative clause",
                standards=[],
                applicability_decision="NOT_APPLICABLE",
                evidence_strength="NONE",
                supporting_facts=["Requirement specifies commercial, administrative, or non-technical terms."],
                lifecycle_status="UNKNOWN",
                uncertainty="Non-technical clause outside Indian Standards scope. Coverage evaluation not applicable.",
                human_review_required=False,
                review_action="No technical standard evaluation required.",
                severity="INFO",
                provenance=prov_dict
            )
            findings.append(finding)
            cov_item = RequirementCoverageItem(
                requirement_id=req_id,
                requirement_text=req_text,
                coverage_state=CoverageState.UNKNOWN,
                primary_standards=[],
                component_breakdown=[],
                lifecycle_concerns=lifecycle_concerns,
                findings=findings
            )
            return cov_item, findings, ReviewQueueCategory.EVIDENCE_INSUFFICIENT, "Administrative or non-technical clause."

        # 3. Ambiguity / Safe Abstention check: CLARIFICATION_REQUIRED != GAP
        is_ambiguous, amb_details = self._check_ambiguity(r)
        if is_ambiguous:
            amb_title = "Specification parameter clarification required" if amb_details.get("missing_information") else "Ambiguous requirement with competing interpretations"
            amb_type = AuditFindingType.CLARIFICATION_REQUIRED if amb_details.get("missing_information") else AuditFindingType.AMBIGUOUS_REQUIREMENT
            finding = AuditFinding(
                finding_id=f"AMB-{req_id}",
                requirement_id=req_id,
                finding_type=amb_type,
                title=amb_title,
                standards=[r.candidate_standard] if r.candidate_standard and r.candidate_standard not in ["INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"] else [],
                applicability_decision=getattr(r, "applicability_status", "REVIEW_REQUIRED") or "REVIEW_REQUIRED",
                evidence_strength=ev_strength,
                supporting_facts=[
                    f"Ambiguity reason: {amb_details.get('ambiguity_reason') or 'Specification requires technical clarification.'}",
                    f"Missing technical parameters: {', '.join(amb_details.get('missing_information') or ['Technical parameters unspecified'])}"
                ],
                lifecycle_status=life_status.upper() if life_status in ["Active", "Withdrawn"] else "UNKNOWN",
                uncertainty="Requirement is underspecified or subject to competing interpretations. Safe abstention preserved.",
                human_review_required=True,
                review_action=amb_details.get("suggested_clarification_question") or "Request technical parameter clarification before standard selection.",
                severity="MEDIUM",
                provenance=prov_dict
            )
            findings.append(finding)
            cov_item = RequirementCoverageItem(
                requirement_id=req_id,
                requirement_text=req_text,
                coverage_state=CoverageState.REVIEW_REQUIRED,
                primary_standards=[r.candidate_standard] if r.candidate_standard and r.candidate_standard not in ["INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"] else [],
                component_breakdown=[],
                ambiguity_details=amb_details,
                lifecycle_concerns=lifecycle_concerns,
                findings=findings
            )
            return cov_item, findings, ReviewQueueCategory.CLARIFICATION_REQUIRED, amb_details.get("suggested_clarification_question") or "Clarify technical parameters."

        # 4. Multi-Component Requirement Analysis
        is_multi, comp_breakdown = self._check_multi_component(r)
        if is_multi:
            # Check how many components have valid standards
            covered_comps = [c for c in comp_breakdown if c.get("status") == CoverageState.COVERED]
            partial_state = CoverageState.COVERED if len(covered_comps) == len(comp_breakdown) else CoverageState.PARTIAL

            cov_title = "Multi-component requirement with complete standards coverage" if partial_state == CoverageState.COVERED else "Multi-component requirement with partial standards coverage"
            cov_finding_type = AuditFindingType.STANDARD_COVERED if partial_state == CoverageState.COVERED else AuditFindingType.PARTIAL_STANDARD_COVERAGE
            finding = AuditFinding(
                finding_id=f"MULTI-{req_id}",
                requirement_id=req_id,
                finding_type=cov_finding_type,
                title=cov_title,
                standards=[c["standard"] for c in comp_breakdown if c.get("standard")],
                applicability_decision="APPLICABLE" if partial_state == CoverageState.COVERED else "REVIEW_REQUIRED",
                evidence_strength=ev_strength,
                supporting_facts=[
                    f"Decomposed into {len(comp_breakdown)} technical components.",
                    f"Covered components: {len(covered_comps)} of {len(comp_breakdown)}."
                ],
                lifecycle_status="ACTIVE",
                uncertainty="Multi-standard requirement; verify all sub-components are addressed.",
                human_review_required=(partial_state == CoverageState.PARTIAL),
                review_action="Review individual component coverage across distinct standards." if partial_state == CoverageState.PARTIAL else "Multi-component coverage verified.",
                severity="LOW" if partial_state == CoverageState.COVERED else "MEDIUM",
                provenance=prov_dict
            )
            findings.append(finding)
            cov_item = RequirementCoverageItem(
                requirement_id=req_id,
                requirement_text=req_text,
                coverage_state=partial_state,
                primary_standards=[c["standard"] for c in comp_breakdown if c.get("standard")],
                component_breakdown=comp_breakdown,
                lifecycle_concerns=lifecycle_concerns,
                findings=findings
            )
            q_cat = ReviewQueueCategory.POTENTIAL_COVERAGE_GAP if partial_state == CoverageState.PARTIAL else ReviewQueueCategory.HIGH_PRIORITY_REVIEW
            return cov_item, findings, q_cat, "Review component standards coverage."

        # 5. Potential Gap Check: Sufficiently specified technical requirement with no supported standard
        if self._is_potential_gap(r, is_insufficient):
            gap_details = {
                "reason": "The system could not establish sufficient standards coverage from the available evidence.",
                "uncertainty": "The system could not establish sufficient standards coverage from the available evidence. This does NOT indicate that no Indian Standard exists.",
                "human_review_action": "Procurement technical officer should verify if an applicable Indian Standard exists in the official BIS directory or if departmental specifications apply."
            }
            finding = AuditFinding(
                finding_id=f"GAP-{req_id}",
                requirement_id=req_id,
                finding_type=AuditFindingType.POTENTIAL_STANDARD_GAP,
                title="Potential standards coverage gap",
                standards=[],
                applicability_decision=getattr(r, "applicability_status", "NOT_APPLICABLE") or "NOT_APPLICABLE",
                evidence_strength="NONE",
                supporting_facts=[
                    "Technical requirement specified, but no supported standard was identified from available evidence.",
                    "Available catalogue evidence does not establish viable standards coverage."
                ],
                lifecycle_status="UNKNOWN",
                uncertainty=gap_details["uncertainty"],
                human_review_required=True,
                review_action=gap_details["human_review_action"],
                severity="HIGH",
                provenance=prov_dict
            )
            findings.append(finding)
            cov_item = RequirementCoverageItem(
                requirement_id=req_id,
                requirement_text=req_text,
                coverage_state=CoverageState.POTENTIAL_GAP,
                primary_standards=[],
                gap_details=gap_details,
                lifecycle_concerns=lifecycle_concerns,
                findings=findings
            )
            return cov_item, findings, ReviewQueueCategory.POTENTIAL_COVERAGE_GAP, gap_details["human_review_action"]

        # 6. Covered Requirement Check
        cand_std = r.candidate_standard
        has_valid_cand = bool(cand_std and cand_std not in [None, "", "INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"])
        is_clean_applicable = (
            has_valid_cand and
            decision == "RECOMMEND" and
            not r.human_review_required and
            life_status in ["Active", "Unknown"] and
            not lifecycle_finding
        )

        if is_clean_applicable:
            finding = AuditFinding(
                finding_id=f"COV-{req_id}",
                requirement_id=req_id,
                finding_type=AuditFindingType.STANDARD_COVERED,
                title=f"Applicable Standard Identified: {cand_std}",
                standards=[cand_std],
                applicability_decision="APPLICABLE",
                evidence_strength=ev_strength,
                supporting_facts=[
                    f"Candidate standard '{cand_std}' is verified applicable with {ev_strength} evidence.",
                    "Available evidence supports applicable standards for the analyzed requirement/components, with no unresolved blocker."
                ],
                lifecycle_status=life_status.upper() if life_status in ["Active", "Withdrawn"] else "UNKNOWN",
                uncertainty="Available evidence supports standard applicability. Does NOT constitute legal compliance certification.",
                human_review_required=False,
                review_action="Standard identified; proceed with standard technical review.",
                severity="INFO",
                provenance=prov_dict
            )
            findings.append(finding)
            cov_item = RequirementCoverageItem(
                requirement_id=req_id,
                requirement_text=req_text,
                coverage_state=CoverageState.COVERED,
                primary_standards=[cand_std],
                component_breakdown=[],
                lifecycle_concerns=lifecycle_concerns,
                findings=findings
            )
            return cov_item, findings, ReviewQueueCategory.HIGH_PRIORITY_REVIEW, "Standard identified."

        # 7. Otherwise: Candidate exists but requires human review (e.g. high risk, parameter incompleteness, or review flag)
        rev_reason = self._determine_primary_reason(r, life_status, comp_label, ev_strength)
        finding = AuditFinding(
            finding_id=f"REV-{req_id}",
            requirement_id=req_id,
            finding_type=AuditFindingType.HUMAN_REVIEW_REQUIRED,
            title="Technical review required for recommended standard",
            standards=[cand_std] if has_valid_cand else [],
            applicability_decision=getattr(r, "applicability_status", "REVIEW_REQUIRED") or "REVIEW_REQUIRED",
            evidence_strength=ev_strength,
            supporting_facts=[rev_reason],
            lifecycle_status=life_status.upper() if life_status in ["Active", "Withdrawn"] else "UNKNOWN",
            uncertainty="Candidate standard identified but technical review conditions remain.",
            human_review_required=True,
            review_action=f"Technical engineer should verify: {rev_reason}",
            severity="MEDIUM" if (r.risk_level or "LOW").upper() in ["LOW", "MEDIUM"] else "HIGH",
            provenance=prov_dict
        )
        findings.append(finding)
        cov_item = RequirementCoverageItem(
            requirement_id=req_id,
            requirement_text=req_text,
            coverage_state=CoverageState.REVIEW_REQUIRED,
            primary_standards=[cand_std] if has_valid_cand else [],
            component_breakdown=[],
            lifecycle_concerns=lifecycle_concerns,
            findings=findings
        )
        queue_category = ReviewQueueCategory.LIFECYCLE_REVIEW if lifecycle_finding else ReviewQueueCategory.HIGH_PRIORITY_REVIEW
        return cov_item, findings, queue_category, rev_reason

    def _is_non_technical_clause(self, r: RequirementRecommendationResult) -> bool:
        """Identifies purely administrative, commercial, or legal clauses."""
        cat = (r.category or "").upper()
        if cat in ["ADMINISTRATIVE", "COMMERCIAL", "LEGAL", "FINANCIAL", "SUBMISSION", "ELIGIBILITY", "GENERAL_CONDITIONS"]:
            return True

        text = (r.requirement_text or "").lower()
        admin_indicators = [
            "earnest money deposit", "emd", "security deposit", "payment terms",
            "submission deadline", "tender fee", "arbitration clause", "penalty clause",
            "force majeure", "bid validity", "turnover criteria", "gst registration",
            "pan card", "experience certificate", "terms of payment", "liquidated damages",
            "jurisdiction of court", "validity of tender"
        ]
        has_admin = any(ind in text for ind in admin_indicators)
        if has_admin:
            # Confirm there are no technical procurement products in the text
            tech_indicators = ["pipe", "valve", "cable", "transformer", "pump", "cement", "steel", "motor", "switchgear", "concrete", "paint", "luminaire", "panel", "compressor"]
            if not any(t in text for t in tech_indicators):
                return True
        return False

    def _check_ambiguity(self, r: RequirementRecommendationResult) -> Tuple[bool, Dict[str, Any]]:
        """Extracts ambiguity state and parameters from requirement intelligence."""
        amb_state = (getattr(r, "ambiguity_state", "CLEAR") or "CLEAR").upper()
        missing_info = getattr(r, "missing_information", []) or []
        competing = getattr(r, "competing_interpretations", []) or []
        clarif_q = getattr(r, "suggested_clarification_question", None)
        amb_reason = getattr(r, "ambiguity_reason", "") or ""

        is_ambiguous = (
            amb_state in [
                "AMBIGUOUS", "AMBIGUOUS_PARAMETER_GAP", "AMBIGUOUS_MULTI_DOMAIN",
                "AMBIGUOUS_COMPETING_STANDARDS", "SAFE_ABSTENTION_GENUINE_AMBIGUITY",
                "CLARIFICATION_REQUIRED", "INCOMPLETE"
            ] or
            bool(missing_info and (not r.candidate_standard or r.candidate_standard in ["INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"])) or
            bool(r.human_review_required and (competing or clarif_q))
        )
        details = {
            "ambiguity_state": amb_state,
            "ambiguity_reason": amb_reason,
            "missing_information": missing_info,
            "competing_interpretations": competing,
            "suggested_clarification_question": clarif_q,
            "unresolved_components": getattr(r, "unresolved_components", []) or []
        }
        return is_ambiguous, details

    def _check_multi_component(self, r: RequirementRecommendationResult) -> Tuple[bool, List[Dict[str, Any]]]:
        """Evaluates whether requirement involves composite multi-standard components."""
        comp_recs = getattr(r, "component_recommendations", []) or []
        if comp_recs and len(comp_recs) > 1:
            breakdown = [
                {
                    "component_id": c.get("component_id"),
                    "component_name": c.get("component_text"),
                    "standard": c.get("candidate_standard"),
                    "status": CoverageState.COVERED if c.get("applicability_decision") == "APPLICABLE" else CoverageState.REVIEW_REQUIRED,
                    "confidence": c.get("confidence", "Medium"),
                    "evidence": c.get("evidence", "")
                }
                for c in comp_recs
            ]
            return True, breakdown

        comps = getattr(r, "decomposed_components", []) or []
        recs = getattr(r, "recommendations", []) or []

        if len(comps) > 1:
            breakdown: List[Dict[str, Any]] = []
            for i, c in enumerate(comps):
                comp_name = c.get("component_text") or c.get("name") or f"Component {i+1}"
                comp_std = c.get("assigned_standard") or (recs[i].standard_number if i < len(recs) else None)
                status = CoverageState.COVERED if comp_std else CoverageState.POTENTIAL_GAP
                breakdown.append({
                    "component_id": c.get("component_id") or f"C{i+1}",
                    "component_name": comp_name,
                    "standard": comp_std,
                    "status": status
                })
            return True, breakdown

        if len(recs) > 1 and getattr(r, "category", "") in ["MULTI_DOMAIN", "COMPOSITE"]:
            breakdown = [
                {
                    "component_id": f"C{idx+1}",
                    "component_name": rec.title or f"Sub-item {idx+1}",
                    "standard": rec.standard_number,
                    "status": CoverageState.COVERED if rec.applicability and rec.applicability.get("decision") == "APPLICABLE" else CoverageState.REVIEW_REQUIRED
                }
                for idx, rec in enumerate(recs)
            ]
            return True, breakdown

        return False, []

    def _is_potential_gap(self, r: RequirementRecommendationResult, is_insufficient: bool) -> bool:
        """
        Conservative check for potential standards coverage gap.
        Triggers only when requirement specifies technical parameters/domain,
        is NOT administrative, is NOT an ambiguous requirement awaiting clarification,
        and available evidence fails to establish coverage.
        """
        cand = r.candidate_standard
        has_no_cand = (cand is None or cand in ["", "INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"])

        app_info = getattr(r, "applicability", None) or {}
        app_dec = app_info.get("decision", "")
        all_rejected = (app_dec in ["INCOMPATIBLE", "REJECT"] or getattr(r, "applicability_status", "") == "INCOMPATIBLE")

        crit = getattr(r, "critic_result", None) or {}
        ev_info = crit.get("evidence", {}) if isinstance(crit, dict) else {}
        ev_str = ev_info.get("evidence_strength") or self._extract_evidence_strength(r)
        has_no_ev = (ev_str == "NONE" and has_no_cand)

        return (has_no_cand or all_rejected or (has_no_ev and is_insufficient))

    def _check_lifecycle_concern(
        self,
        r: RequirementRecommendationResult,
        life_status: str,
        struct_ev: Dict[str, Any],
        prov_dict: Dict[str, Any]
    ) -> Optional[AuditFinding]:
        """Detects cited or matched withdrawn standards without automated replacement."""
        req_id = r.requirement_id or "REQ-UNKNOWN"

        # Check explicit standards found in requirement text
        cited_stds = getattr(r, "explicit_standards_found", []) or []
        for cited in cited_stds:
            is_withdrawn = False
            if life_status == "Withdrawn" or (r.status or "").lower() == "withdrawn" or any("withdrawn" in s.lower() for s in (r.risk_reasons or [])):
                is_withdrawn = True
            elif self.db:
                try:
                    matches = self.db.find_standards_by_number(cited)
                    if matches and any(m.get("status", "").upper() == "WITHDRAWN" for m in matches):
                        is_withdrawn = True
                except Exception:
                    pass

            if is_withdrawn:
                # Check for authoritative replacement relationship
                rels = struct_ev.get("relationships") or {}
                superseded_by = rels.get("superseded_by") or []
                if superseded_by:
                    rep_std = superseded_by[0].get("target_standard") or "successor standard"
                    rep_note = f"Authoritative replacement standard recorded in catalogue: {rep_std}."
                else:
                    rep_note = "No verified replacement standard recorded in catalogue. Do NOT automatically substitute."

                return AuditFinding(
                    finding_id=f"LIFE-{req_id}-{cited}",
                    requirement_id=req_id,
                    finding_type=AuditFindingType.LIFECYCLE_CONCERN,
                    title=f"Tender cites withdrawn standard '{cited}'",
                    standards=[cited],
                    lifecycle_status="WITHDRAWN",
                    lifecycle_note=rep_note,
                    severity="HIGH",
                    human_review_required=True,
                    review_action=f"Verify if cited standard '{cited}' should be revised. {rep_note}",
                    uncertainty="Standard is withdrawn in official BIS records.",
                    provenance=prov_dict
                )

        # Check candidate standard lifecycle
        if life_status == "Withdrawn" and r.candidate_standard not in [None, "", "INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"]:
            rels = struct_ev.get("relationships") or {}
            superseded_by = rels.get("superseded_by") or []
            if superseded_by:
                rep_std = superseded_by[0].get("target_standard") or "successor standard"
                rep_note = f"Authoritative replacement standard recorded in catalogue: {rep_std}."
            else:
                rep_note = "Standard is marked WITHDRAWN in official BIS records. No verified replacement standard recorded in catalogue. Do NOT automatically substitute."

            return AuditFinding(
                finding_id=f"LIFE-{req_id}-{r.candidate_standard}",
                requirement_id=req_id,
                finding_type=AuditFindingType.LIFECYCLE_CONCERN,
                title=f"Matched standard '{r.candidate_standard}' is withdrawn",
                standards=[r.candidate_standard],
                lifecycle_status="WITHDRAWN",
                lifecycle_note=rep_note,
                severity="HIGH",
                human_review_required=True,
                review_action=f"Review candidate standard '{r.candidate_standard}' which is withdrawn in official catalogue. {rep_note}",
                uncertainty="Candidate standard is withdrawn.",
                provenance=prov_dict
            )

        return None

    # -----------------------------------------------------------------------
    # Helper Extraction Methods
    # -----------------------------------------------------------------------

    def _extract_evidence_strength(self, r: RequirementRecommendationResult) -> str:
        """Extracts verified evidence strength, avoiding retrieval score conflation."""
        crit_res = getattr(r, "critic_result", None)
        if crit_res and isinstance(crit_res, dict):
            ev_info = crit_res.get("evidence")
            if ev_info and isinstance(ev_info, dict):
                ev_str = ev_info.get("evidence_strength")
                if ev_str in ["STRONG", "MODERATE", "WEAK", "NONE"]:
                    return ev_str

        # Fallback to provenance metadata if critic evidence dict is absent
        prov = getattr(r, "provenance", "").upper()
        ev_text = getattr(r, "evidence", "") or ""

        if not ev_text or "insufficient" in ev_text.lower():
            return "NONE"
        if prov == "VERIFIED":
            return "STRONG"
        if prov == "CURATED":
            return "MODERATE"
        if prov == "INFERRED":
            return "WEAK"
        return "NONE"

    def _extract_completeness_label(self, r: RequirementRecommendationResult) -> str:
        """Extracts specification review completeness state."""
        spec_comp = getattr(r, "specification_completeness", None)
        if spec_comp and isinstance(spec_comp, dict):
            label = spec_comp.get("completeness_label")
            if label in ["KNOWN", "POTENTIALLY_MISSING", "UNKNOWN", "NOT_APPLICABLE"]:
                return label

        return "NOT_APPLICABLE"

    def _extract_lifecycle_status(self, r: RequirementRecommendationResult) -> str:
        """Resolves lifecycle status from recommendation results."""
        status = (r.status or "").capitalize()
        version_role = getattr(r, "version_role", "")

        # Check explicit superseded indicators on candidate or cited requirement
        has_superseded_warning = (
            "superseded" in status.lower() or
            version_role == "REPLACED_OR_SUPERSEDED" or
            any("superseded" in s.lower() for s in (r.risk_reasons or [])) or
            bool(r.recommendations and getattr(r.recommendations[0], "superseded_warning", None))
        )
        if has_superseded_warning:
            return "Superseded"
        if "withdrawn" in status.lower():
            return "Withdrawn"
        if "active" in status.lower() or version_role == "CURRENT_ACTIVE":
            return "Active"
        return "Unknown"

    def _determine_primary_reason(
        self,
        r: RequirementRecommendationResult,
        life_status: str,
        comp_label: str,
        ev_strength: str
    ) -> str:
        """Synthesizes an explainable, fact-based reason for human review."""
        vm = getattr(r, "verified_missing", []) or []
        if vm:
            std_num = vm[0].get("standard_number") or "standard"
            return f"Verified missing standard dependency '{std_num}' required for specification."
        if r.risk_reasons:
            return r.risk_reasons[0]
        if life_status == "Superseded":
            return f"Tender cited or recommended superseded standard '{r.candidate_standard}'."
        if life_status == "Withdrawn":
            return f"Standard '{r.candidate_standard}' is withdrawn in official BIS catalogue."
        pm = getattr(r, "potentially_missing", []) or []
        if pm and not r.risk_reasons:
            std_num = pm[0].get("standard_number") or "standard"
            return f"Evidence-backed dependency '{std_num}' is potentially missing from tender."
        if comp_label == "POTENTIALLY_MISSING":
            spec_comp = getattr(r, "specification_completeness", None) or {}
            missing = spec_comp.get("potentially_missing_parameters", [])
            if missing:
                return f"Specification review identified potentially missing parameters: {', '.join(missing[:3])}."
            return "Specification review identified potentially missing parameters."
        if ev_strength in ["WEAK", "NONE"]:
            return f"Insufficient or weak supporting standards evidence ({ev_strength})."
        if r.reason:
            return r.reason
        return "Technical engineer review required."

    def _determine_publication_readiness(
        self,
        requirements_analyzed: int,
        recommendations_count: int,
        review_required_count: int,
        insufficient_evidence_count: int,
        superseded_count: int,
        withdrawn_count: int,
        risk_dist: Dict[str, int],
        evidence_dist: Dict[str, int],
        completeness_dist: Dict[str, int]
    ) -> tuple[str, List[str]]:
        """
        Determines deterministic publication readiness state and supporting reasons.
        States:
        - INSUFFICIENT_EVIDENCE
        - REVIEW_REQUIRED
        - READY_FOR_REVIEW
        """
        reasons: List[str] = []

        critical_count = risk_dist.get("CRITICAL", 0)
        high_count = risk_dist.get("HIGH", 0)
        none_ev_count = evidence_dist.get("NONE", 0)
        weak_ev_count = evidence_dist.get("WEAK", 0)
        pot_missing_count = completeness_dist.get("POTENTIALLY_MISSING", 0)

        # 1. Evaluate INSUFFICIENT_EVIDENCE threshold
        # Over half of requirements have zero evidence, or all are insufficient
        if none_ev_count > 0 and none_ev_count >= (requirements_analyzed / 2):
            reasons.append(f"{none_ev_count} of {requirements_analyzed} requirements lack verified standards evidence.")
            return "INSUFFICIENT_EVIDENCE", reasons

        if insufficient_evidence_count == requirements_analyzed:
            reasons.append("No reliable standards evidence identified across all requirements.")
            return "INSUFFICIENT_EVIDENCE", reasons

        # 2. Evaluate REVIEW_REQUIRED threshold
        # Any CRITICAL, HIGH risk, superseded/withdrawn standard, or explicit review request
        has_review_flags = (
            critical_count > 0 or
            high_count > 0 or
            superseded_count > 0 or
            withdrawn_count > 0 or
            review_required_count > 0 or
            insufficient_evidence_count > 0
        )

        if has_review_flags:
            if superseded_count > 0:
                reasons.append(f"{superseded_count} requirement(s) cite or match superseded standard(s).")
            if withdrawn_count > 0:
                reasons.append(f"{withdrawn_count} requirement(s) involve withdrawn standard(s).")
            if critical_count > 0:
                reasons.append(f"{critical_count} requirement(s) flagged with CRITICAL risk.")
            if high_count > 0:
                reasons.append(f"{high_count} requirement(s) flagged with HIGH risk.")
            if review_required_count > 0:
                reasons.append(f"{review_required_count} requirement(s) require technical engineer review.")
            if insufficient_evidence_count > 0:
                reasons.append(f"{insufficient_evidence_count} requirement(s) have insufficient standards evidence.")
            if pot_missing_count > 0:
                reasons.append(f"{pot_missing_count} requirement(s) have potentially missing specification parameters.")
            if weak_ev_count > 0:
                reasons.append(f"{weak_ev_count} requirement(s) supported only by weak/unverified evidence.")

            return "REVIEW_REQUIRED", reasons

        # 3. Otherwise, READY_FOR_REVIEW
        reasons.append(
            f"All {requirements_analyzed} requirement(s) have grounded standards evidence with no critical or high risk flags."
        )
        return "READY_FOR_REVIEW", reasons
