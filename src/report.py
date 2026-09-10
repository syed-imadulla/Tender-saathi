"""
Module: src/report.py
Purpose: Evidence-Backed Indian Standards Review Report Generator for TenderSaathi.

Converts structured intelligence from M1–M6 (TenderAuditResult,
RequirementRecommendationResult, CandidateCritique, SpecificationCompletenessReport,
and StandardsGraph) into a deterministic, officer-facing Evidence-Backed Standards
Review Report.

STRICT CONSTRAINTS & PRINCIPLES:
- Deterministic, explainable, and grounded in stored evidence only (no LLMs).
- Non-legalistic: aids standards review; does NOT certify statutory/legal compliance.
- Preserves provenance (VERIFIED, CURATED, INFERRED) and evidence strength without inflation.
- Preserves graph boundary: 'Related standard identified for review' (RELATED != APPLICABLE).
- Formats supported: Structured Object, Markdown, and machine-readable JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
import os
import re

from src.audit import TenderAuditResult, ReviewQueueItem
from src.recommend import RequirementRecommendationResult, TenderRecommendationReport


# ---------------------------------------------------------------------------
# Report Data Models
# ---------------------------------------------------------------------------

@dataclass
class TenderInformation:
    """Procurement tender metadata for the review report."""
    tender_id: str
    tender_title: Optional[str] = None
    organisation: Optional[str] = None
    source_file: Optional[str] = None
    date: Optional[str] = None
    requirements_analyzed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequirementReviewSection:
    """Detailed standards evaluation for an individual procurement requirement."""
    requirement_id: str
    requirement_text: str
    category: str
    components: List[Dict[str, Any]] = field(default_factory=list)
    recommended_standard: str = "NONE"
    recommended_title: str = "No standard recommended"
    relevance_score: float = 0.0
    lifecycle_status: str = "Unknown"
    successor_standard: Optional[str] = None
    superseded_citation: Optional[str] = None
    evidence_strength: str = "NONE"
    provenance: str = "UNKNOWN"
    evidence_text: str = ""
    evidence_source: Optional[str] = None
    why_this: List[str] = field(default_factory=list)
    why_not: List[str] = field(default_factory=list)
    completeness_label: str = "NOT_APPLICABLE"
    potentially_missing_parameters: List[str] = field(default_factory=list)
    known_parameters: Dict[str, Any] = field(default_factory=dict)
    related_standards: List[Dict[str, Any]] = field(default_factory=list)
    decision: str = "REVIEW_REQUIRED"
    risk_level: str = "LOW"
    risk_reasons: List[str] = field(default_factory=list)
    human_review_required: bool = False
    confidence: str = "Low"
    review_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceSummary:
    """High-level summary of evidence strength and provenance distribution."""
    evidence_distribution: Dict[str, int]
    provenance_distribution: Dict[str, int]
    note: str = (
        "AI/retrieval results are not treated as authoritative evidence by themselves. "
        "Factual standards claims are constrained by the available evidence and provenance."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TenderReviewReport:
    """Comprehensive, officer-facing Evidence-Backed Standards Review Report."""
    title: str = "TenderSaathi Evidence-Backed Indian Standards Review Report"
    subtitle: str = "Standards review aid for procurement specifications"
    tender_info: TenderInformation = field(default_factory=lambda: TenderInformation(tender_id="UNKNOWN"))
    publication_readiness: str = "REVIEW_REQUIRED"
    readiness_reasons: List[str] = field(default_factory=list)
    readiness_disclaimer: str = (
        "This report is a standards-review aid and does not constitute legal compliance certification."
    )
    executive_summary: Dict[str, Any] = field(default_factory=dict)
    requirements: List[RequirementReviewSection] = field(default_factory=list)
    review_queue: List[ReviewQueueItem] = field(default_factory=list)
    evidence_summary: Optional[EvidenceSummary] = None
    footer_disclaimer: str = (
        "TenderSaathi is a standards-review aid for procurement specifications. "
        "Final applicability, specification, procurement, regulatory and legal decisions "
        "remain with the responsible human authority."
    )

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "title": self.title,
            "subtitle": self.subtitle,
            "tender_info": self.tender_info.to_dict(),
            "publication_readiness": self.publication_readiness,
            "readiness_reasons": self.readiness_reasons,
            "readiness_disclaimer": self.readiness_disclaimer,
            "executive_summary": self.executive_summary,
            "requirements": [r.to_dict() for r in self.requirements],
            "review_queue": [q.to_dict() for q in self.review_queue],
            "evidence_summary": self.evidence_summary.to_dict() if self.evidence_summary else None,
            "footer_disclaimer": self.footer_disclaimer
        }
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serializes the report to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Renders the report as clean, GitHub-flavored Markdown for officers and judges."""
        md = []

        # 1. Title & Subtitle
        md.append(f"# {self.title}\n")
        md.append(f"**{self.subtitle}**\n")
        md.append("> [!NOTE]")
        md.append(f"> {self.readiness_disclaimer}\n")
        md.append("---\n")

        # 2. Tender Information
        md.append("## 1. Tender Information\n")
        md.append(f"- **Tender ID:** `{self.tender_info.tender_id}`")
        if self.tender_info.tender_title:
            md.append(f"- **Tender Title:** {self.tender_info.tender_title}")
        if self.tender_info.organisation:
            md.append(f"- **Organisation / Department:** {self.tender_info.organisation}")
        if self.tender_info.source_file:
            md.append(f"- **Source File:** `{self.tender_info.source_file}`")
        if self.tender_info.date:
            md.append(f"- **Date / Timestamp:** {self.tender_info.date}")
        md.append(f"- **Requirements Analysed:** {self.tender_info.requirements_analyzed}\n")

        # 3. Publication Readiness
        md.append("## 2. Publication Readiness\n")
        stat = self.publication_readiness
        badge = "🟢 READY_FOR_REVIEW" if stat == "READY_FOR_REVIEW" else ("🟡 REVIEW_REQUIRED" if stat == "REVIEW_REQUIRED" else "🔴 INSUFFICIENT_EVIDENCE")
        md.append(f"**Status:** {badge}\n")

        if self.readiness_reasons:
            md.append("### Key Observations:")
            for r in self.readiness_reasons:
                md.append(f"- {r}")
            md.append("")

        # 4. Executive Summary
        md.append("## 3. Executive Summary\n")
        es = self.executive_summary
        md.append("| Metric | Count / Distribution | Notes |")
        md.append("|---|---|---|")
        md.append(f"| **Requirements Analysed** | {es.get('requirements_analyzed', 0)} | Total clauses extracted |")
        md.append(f"| **Direct Recommendations** | {es.get('recommendations_count', 0)} | Active standards grounded in evidence |")
        md.append(f"| **Review Required** | {es.get('review_required_count', 0)} | Flagged for engineering attention |")
        md.append(f"| **Insufficient Evidence** | {es.get('insufficient_evidence_count', 0)} | No reliable standard matched |")
        md.append(f"| **Active Standards** | {es.get('active_count', 0)} | Verified current in BIS catalogue |")
        md.append(f"| **Superseded Standards** | {es.get('superseded_count', 0)} | Outdated standards identified |")
        md.append(f"| **Withdrawn Standards** | {es.get('withdrawn_count', 0)} | Cancelled standards |")
        md.append(f"| **Unknown Lifecycle** | {es.get('unknown_lifecycle_count', 0)} | Unindexed in local catalogue |")
        md.append(f"| **Related Standards to Review** | {es.get('related_standards_count', 0)} | Discovered via relationship graph (depth=1) |")
        md.append("")

        # Risk & Evidence Distribution Tables
        ev_dist = es.get("evidence_distribution", {})
        comp_dist = es.get("completeness_distribution", {})
        risk_dist = es.get("risk_distribution", {})

        md.append("### Governance Distributions\n")
        md.append(f"- **Evidence Strength:** STRONG: `{ev_dist.get('STRONG', 0)}` | MODERATE: `{ev_dist.get('MODERATE', 0)}` | WEAK: `{ev_dist.get('WEAK', 0)}` | NONE: `{ev_dist.get('NONE', 0)}`")
        md.append(f"- **Specification Review Completeness:** KNOWN: `{comp_dist.get('KNOWN', 0)}` | POTENTIALLY_MISSING: `{comp_dist.get('POTENTIALLY_MISSING', 0)}` | UNKNOWN: `{comp_dist.get('UNKNOWN', 0)}` | NOT_APPLICABLE: `{comp_dist.get('NOT_APPLICABLE', 0)}`")
        md.append(f"- **Risk Distribution:** CRITICAL: `{risk_dist.get('CRITICAL', 0)}` | HIGH: `{risk_dist.get('HIGH', 0)}` | MEDIUM: `{risk_dist.get('MEDIUM', 0)}` | LOW: `{risk_dist.get('LOW', 0)}`\n")

        # 5. Human Review Queue
        md.append("## 4. Prioritized Human Review Queue\n")
        if not self.review_queue:
            md.append("*No requirements currently require human technical review.*\n")
        else:
            md.append("| # | Priority | Requirement ID | Candidate Standard | Issue / Primary Reason |")
            md.append("|---|---|---|---|---|")
            for idx, q in enumerate(self.review_queue, 1):
                clean_txt = q.requirement_text.replace("\n", " ").strip()
                if len(clean_txt) > 60:
                    clean_txt = clean_txt[:57] + "..."
                md.append(f"| {idx} | **{q.risk_level}** | `{q.requirement_id}` | `{q.candidate_standard}` | {q.primary_reason} |")
            md.append("")

        # 6. Requirement-by-Requirement Review
        md.append("## 5. Requirement-by-Requirement Review\n")
        for idx, req in enumerate(self.requirements, 1):
            md.append(f"### 5.{idx} Requirement `{req.requirement_id}` [{req.category.upper()}]\n")
            md.append(f"**Original Requirement Text:**\n> \"{req.requirement_text}\"\n")

            # Components
            if req.components:
                comp_strs = []
                for c in req.components:
                    aspect = c.get("aspect", "general")
                    text_c = c.get("text", "")
                    subcat = c.get("subcategory", "")
                    label = f"{aspect}: {text_c}" + (f" ({subcat})" if subcat else "")
                    comp_strs.append(f"`{label}`")
                md.append(f"- **Decomposed Technical Components:** {', '.join(comp_strs)}")

            # Recommended Standard & Lifecycle
            md.append(f"- **Recommended Standard:** **{req.recommended_standard}** — *{req.recommended_title}*")
            status_upper = req.lifecycle_status.upper()
            status_badge = f"**{status_upper}**"
            if status_upper == "SUPERSEDED" and req.successor_standard:
                status_badge += f" (Superseded by `{req.successor_standard}`)"
            elif req.superseded_citation:
                status_badge += f" (Active successor replacing cited superseded `{req.superseded_citation}`)"
            elif req.successor_standard and req.successor_standard != req.recommended_standard:
                status_badge += f" (Superseded by `{req.successor_standard}`)"
            md.append(f"- **Lifecycle Status:** {status_badge} | **Composite Relevance Score:** `{req.relevance_score:.3f}`")

            # Evidence & Provenance
            md.append(f"- **Evidence Strength:** `{req.evidence_strength}` | **Provenance:** `{req.provenance}`")
            if req.evidence_text:
                src_label = f" ({req.evidence_source})" if req.evidence_source else ""
                md.append(f"- **Verbatim Evidence{src_label}:** \"{req.evidence_text}\"")

            # Why this
            if req.why_this:
                md.append("- **Why This Standard?:**")
                for w in req.why_this:
                    md.append(f"  - {w}")

            # Why not / Alternatives
            if req.why_not:
                md.append("- **Why Not Alternatives?:**")
                for wn in req.why_not:
                    md.append(f"  - {wn}")

            # Completeness
            comp_details = f"`{req.completeness_label}`"
            if req.potentially_missing_parameters:
                comp_details += f" (Potentially missing: {', '.join(req.potentially_missing_parameters)})"
            if req.known_parameters:
                known_str = ", ".join(f"{k}={v}" for k, v in req.known_parameters.items())
                comp_details += f" | Known: [{known_str}]"
            md.append(f"- **Specification Review Completeness:** {comp_details}")

            # Related Standards (M5 Graph)
            if req.related_standards:
                md.append("- **Related Standards Identified for Review (Graph Depth = 1):**")
                for rel in req.related_standards:
                    dir_sym = "→" if rel.get("direction") == "OUTGOING" else "←"
                    rel_type = rel.get("relationship_type", "REFERENCES")
                    rel_num = rel.get("standard_number", "")
                    rel_title = rel.get("title", "")
                    rel_stat = rel.get("lifecycle_status", "Active")
                    rel_note = rel.get("review_note", "Related standard to review")
                    md.append(f"  - [{dir_sym} {rel_type}] `{rel_num}` — *{rel_title}* ({rel_stat}) — *Note:* {rel_note}")

            # Decision & Risk
            md.append(f"- **Standards Review Decision:** `{req.decision}` | **Risk Level:** `{req.risk_level}` | **Confidence:** `{req.confidence}`")
            if req.human_review_required:
                md.append(f"- ⚠ **Human Technical Review Required:** {req.review_reason or 'Verification required'}")

            md.append("\n---\n")

        # 7. Evidence & Provenance Summary
        md.append("## 6. Evidence & Provenance Governance Summary\n")
        if self.evidence_summary:
            md.append(f"> [!IMPORTANT]\n> {self.evidence_summary.note}\n")
            md.append("| Provenance Tier | Criteria | Count in Tender | Evidence Strength Produced |")
            md.append("|---|---|---|---|")
            md.append(f"| **VERIFIED** | Authoritative BSB Edge / BIS portal record manually verified | {self.evidence_summary.provenance_distribution.get('VERIFIED', 0)} | `STRONG` |")
            md.append(f"| **CURATED** | Loaded from official BIS Standards Catalogues / Excel indices | {self.evidence_summary.provenance_distribution.get('CURATED', 0)} | `MODERATE` |")
            md.append(f"| **INFERRED** | Contextual heuristic or tender co-citation (strictly unverified) | {self.evidence_summary.provenance_distribution.get('INFERRED', 0)} | `WEAK` |")
            md.append("")

        # 8. Report Footer / Disclaimer
        md.append("## 7. Officer Notice & Disclaimer\n")
        md.append(f"{self.footer_disclaimer}\n")

        return "\n".join(md)

    def save_markdown(self, filepath: str) -> None:
        """Saves report to a Markdown file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())

    def save_json(self, filepath: str) -> None:
        """Saves report to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=2))


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """
    Deterministic report engine assembling TenderReviewReport from
    TenderAuditResult and requirement recommendation results.
    """

    def generate_report(
        self,
        audit_result: TenderAuditResult,
        requirement_results: List[RequirementRecommendationResult],
        tender_metadata: Optional[Dict[str, Any]] = None
    ) -> TenderReviewReport:
        """Assembles a full TenderReviewReport."""
        meta = tender_metadata or {}
        tender_id = audit_result.tender_id

        # 1. Tender Information
        tender_info = TenderInformation(
            tender_id=tender_id,
            tender_title=meta.get("tender_title") or meta.get("title"),
            organisation=meta.get("organisation") or meta.get("department"),
            source_file=meta.get("source_file") or meta.get("filename"),
            date=meta.get("date") or meta.get("timestamp"),
            requirements_analyzed=audit_result.requirements_analyzed
        )

        # 2. Executive Summary
        exec_summary = audit_result.to_dict()

        # 3. Requirement Review Sections
        req_sections: List[RequirementReviewSection] = []
        prov_dist = {"VERIFIED": 0, "CURATED": 0, "INFERRED": 0, "UNKNOWN": 0}

        for r in requirement_results:
            prov = (r.provenance or "UNKNOWN").upper()
            prov_dist[prov] = prov_dist.get(prov, 0) + 1

            # Extract evidence strength
            crit_res = getattr(r, "critic_result", None) or {}
            ev_dict = crit_res.get("evidence") or {}
            ev_strength = ev_dict.get("evidence_strength")
            if not ev_strength:
                # Fallback to provenance mapping
                ev_strength = "STRONG" if prov == "VERIFIED" else ("MODERATE" if prov == "CURATED" else ("WEAK" if prov == "INFERRED" else "NONE"))

            ev_text = ev_dict.get("evidence_text") or r.evidence or ""
            ev_src = ev_dict.get("evidence_source") or ("BSB Edge Portal" if prov == "VERIFIED" else ("BIS Standards Catalogue" if prov == "CURATED" else None))

            # Extract completeness
            spec_comp = getattr(r, "specification_completeness", None) or {}
            comp_label = spec_comp.get("completeness_label", "NOT_APPLICABLE")
            missing_params = spec_comp.get("potentially_missing_parameters", [])
            known_params = spec_comp.get("known_parameters", {})

            # Extract successor standard if candidate is superseded, OR cited standard if candidate is active successor
            succ_std = None
            superseded_cite = None
            explicit_stds = getattr(r, "explicit_standards_found", []) or []

            if (r.status or "").lower() == "superseded":
                for rec in getattr(r, "recommendations", []) or []:
                    warn = getattr(rec, "superseded_warning", "") or ""
                    match = re.search(r'SUPERSEDED by\s+([A-Za-z0-9/:\s\-]+?)(?:\.|$)', warn, re.IGNORECASE)
                    if match:
                        succ_std = match.group(1).strip()
                        break
                if not succ_std:
                    for rel in getattr(r, "related_standards", []) or []:
                        if rel.get("relationship_type") in ["SUPERSEDED_BY", "SUPERSEDES"]:
                            succ_std = rel.get("standard_number")
                            break
            elif explicit_stds:
                for rec in getattr(r, "recommendations", []) or []:
                    warn = getattr(rec, "superseded_warning", "") or ""
                    if "superseded" in warn.lower():
                        superseded_cite = explicit_stds[0]
                        break
                if not superseded_cite:
                    for rel in getattr(r, "related_standards", []) or []:
                        if rel.get("relationship_type") == "SUPERSEDES" and rel.get("lifecycle_status") == "Superseded":
                            superseded_cite = rel.get("standard_number")
                            break
            elif getattr(r, "recommendations", []):
                for rec in r.recommendations:
                    warn = getattr(rec, "superseded_warning", "") or ""
                    if "superseded" in warn.lower():
                        match = re.search(r"(?:IS\s*(?:/|\s*)?(?:ISO|IEC)?\s*\d+)", warn)
                        if match:
                            superseded_cite = match.group(0)
                            break

            # Standards review decision categorization strictly matching M6 audit logic
            crit_decision = crit_res.get("decision")
            if (
                crit_decision == "INSUFFICIENT_EVIDENCE" or
                not r.candidate_standard or
                r.candidate_standard in ["INSUFFICIENT_INFORMATION", "", "UNKNOWN", "NONE"]
            ):
                decision = "INSUFFICIENT_EVIDENCE"
            elif r.human_review_required or crit_decision in ["REVIEW_REQUIRED", "RECOMMEND_WITH_REVIEW", "REJECT"]:
                decision = "REVIEW_REQUIRED"
            else:
                decision = "RECOMMEND"

            req_sections.append(RequirementReviewSection(
                requirement_id=r.requirement_id,
                requirement_text=r.requirement_text,
                category=r.category,
                components=getattr(r, "decomposed_components", []) or [],
                recommended_standard=r.candidate_standard or "NONE",
                recommended_title=r.title or "No Title",
                relevance_score=r.relevance_score or 0.0,
                lifecycle_status=r.status or "Unknown",
                successor_standard=succ_std,
                superseded_citation=superseded_cite,
                evidence_strength=ev_strength,
                provenance=prov,
                evidence_text=ev_text,
                evidence_source=ev_src,
                why_this=getattr(r, "why_this", []) or ([r.reason] if r.reason else []),
                why_not=getattr(r, "why_not", []) or [],
                completeness_label=comp_label,
                potentially_missing_parameters=missing_params,
                known_parameters=known_params,
                related_standards=getattr(r, "related_standards", []) or [],
                decision=decision,
                risk_level=getattr(r, "risk_level", "LOW") or "LOW",
                risk_reasons=getattr(r, "risk_reasons", []) or [],
                human_review_required=r.human_review_required,
                confidence=r.confidence or "Low",
                review_reason=r.reason
            ))

        # 4. Evidence Summary
        evidence_summary = EvidenceSummary(
            evidence_distribution=audit_result.evidence_distribution,
            provenance_distribution=prov_dist
        )

        return TenderReviewReport(
            tender_info=tender_info,
            publication_readiness=audit_result.publication_readiness,
            readiness_reasons=audit_result.readiness_reasons,
            executive_summary=exec_summary,
            requirements=req_sections,
            review_queue=audit_result.review_queue,
            evidence_summary=evidence_summary
        )

    def generate_and_save(
        self,
        audit_result: TenderAuditResult,
        requirement_results: List[RequirementRecommendationResult],
        output_dir: str = "reports/generated",
        tender_metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """Generates report and saves both Markdown and JSON files to output_dir."""
        report = self.generate_report(audit_result, requirement_results, tender_metadata=tender_metadata)
        t_id = audit_result.tender_id or "TENDER"
        safe_id = re.sub(r'[^\w\-]', '_', t_id).lower()

        md_path = os.path.join(output_dir, f"{safe_id}_review_report.md")
        json_path = os.path.join(output_dir, f"{safe_id}_review_report.json")

        report.save_markdown(md_path)
        report.save_json(json_path)

        return md_path, json_path
