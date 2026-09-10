"""
Module: src/audit.py
Purpose: Tender Audit & Publication Readiness Engine for TenderSaathi.

Aggregates requirement-level recommendation, critic, completeness, and graph results
into a comprehensive, deterministic tender-level standards review audit.

IMPORTANT PRINCIPLES:
- This is a standards-review readiness assessment, NOT a legal compliance engine.
- Never asserts "compliant", "non-compliant", "legally valid", or "legally invalid".
- Strictly deterministic: no LLMs, no fake percentage scores.
- Preserves the distinction between retrieval score, evidence strength, and applicability.
- Categorizes publication readiness as:
    - READY_FOR_REVIEW
    - REVIEW_REQUIRED
    - INSUFFICIENT_EVIDENCE
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from src.recommend import RequirementRecommendationResult, TenderRecommendationReport


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
        "Standards review readiness assessment for procurement officers. "
        "Does NOT constitute legal compliance certification."
    )

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


# ---------------------------------------------------------------------------
# Tender Audit Engine
# ---------------------------------------------------------------------------

class TenderAuditEngine:
    """
    Deterministic audit engine aggregating requirement-level recommendation results
    into tender-level standards review metrics and a prioritized review queue.
    """

    def audit_tender(
        self,
        results: List[RequirementRecommendationResult],
        tender_id: str = "TENDER_AUDIT"
    ) -> TenderAuditResult:
        """Audits a list of requirement recommendation results for a tender."""
        requirements_analyzed = len(results)

        # Handle edge case: Empty tender / zero requirements
        if requirements_analyzed == 0:
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
                readiness_reasons=["No requirements identified in tender for standards review."]
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

            # 5. Related standards count (Milestone 5 graph results)
            rel_stds = getattr(r, "related_standards", None) or []
            related_standards_count += len(rel_stds)

            # 6. Standards Review Decision Categorization
            crit_res = getattr(r, "critic_result", None) or {}
            decision = crit_res.get("decision") or ("REVIEW_REQUIRED" if r.human_review_required else "RECOMMEND")
            is_review_req = bool(r.human_review_required or decision in ["REVIEW_REQUIRED", "RECOMMEND_WITH_REVIEW"])

            is_insufficient = (
                decision == "INSUFFICIENT_EVIDENCE" or
                r.candidate_standard in ["INSUFFICIENT_INFORMATION", "", "UNKNOWN", "NONE"]
            )

            if is_insufficient:
                insufficient_evidence_count += 1
            elif is_review_req:
                review_required_count += 1
            else:
                recommendations_count += 1

            # 7. Check if Item belongs in the Human Review Queue
            needs_queue = (
                is_review_req or
                is_insufficient or
                risk_lvl in ["CRITICAL", "HIGH", "MEDIUM"] or
                life_status in ["Superseded", "Withdrawn"]
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
                    priority=priority_val
                ))

        # Sort Review Queue: CRITICAL (1) -> HIGH (2) -> MEDIUM (3) -> LOW (4)
        # Secondary sort: Evidence severity (NONE -> WEAK -> MODERATE -> STRONG)
        # Tertiary sort: Completeness severity (UNKNOWN -> POTENTIALLY_MISSING -> NOT_APPLICABLE -> KNOWN)
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
            readiness_reasons=readiness_reasons
        )

    def audit_report(self, report: TenderRecommendationReport) -> TenderAuditResult:
        """Audits a TenderRecommendationReport produced by the recommendation pipeline."""
        return self.audit_tender(report.results, tender_id=report.tender_id)

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
        if r.risk_reasons:
            return r.risk_reasons[0]
        if life_status == "Superseded":
            return f"Tender cited or recommended superseded standard '{r.candidate_standard}'."
        if life_status == "Withdrawn":
            return f"Standard '{r.candidate_standard}' is withdrawn in official BIS catalogue."
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
