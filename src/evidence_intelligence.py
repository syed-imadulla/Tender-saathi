"""
Module: src/evidence_intelligence.py
Purpose: Evidence-First Standards Intelligence layer for TenderSaathi.

Architectural Principles:
1. The Evidence Engine EXPLAINS and TRACES decisions; it does not make recommendations.
2. Retrieval similarity is NEVER presented as authoritative proof; it is a supporting signal.
3. BIS scope evidence is never fabricated. Missing scope is explicitly marked as UNKNOWN.
4. Lifecycle status is strictly ACTIVE, WITHDRAWN, or UNKNOWN; ACTIVE is never guessed from missing data.
5. Relationships (supersession, equivalents) require explicit evidentiary support; never infer supersession.
6. Provenance is strictly tracked with source, URL, raw record ref, and verification status.
7. Safe abstentions produce structured uncertainty and actionable clarification questions.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional, Set
import re
import os
import sqlite3

from src.standards import StandardsDatabase, classify_standard_role
from src.search import SearchResult
from src.applicability import ApplicabilityResult, ApplicabilityDecision
from src.ambiguity import AmbiguityReport, AmbiguityState


class EvidenceStrength(str, Enum):
    """Hierarchical evidence strength classification."""
    STRONG_EXPLICIT_CITATION = "STRONG_EXPLICIT_CITATION"
    STRONG_AUTHORITATIVE_SCOPE = "STRONG_AUTHORITATIVE_SCOPE"
    MEDIUM_TECHNICAL_MATCH = "MEDIUM_TECHNICAL_MATCH"
    MEDIUM_APPLICABILITY_SUPPORT = "MEDIUM_APPLICABILITY_SUPPORT"
    WEAK_RETRIEVAL_ONLY = "WEAK_RETRIEVAL_ONLY"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


@dataclass
class LifecycleEvidence:
    """Canonical lifecycle intelligence backed by explicit evidence."""
    status: str                                # "ACTIVE", "WITHDRAWN", "UNKNOWN"
    is_active: bool = False
    is_withdrawn: bool = False
    is_unknown: bool = True
    reaffirmed_year: Optional[int] = None
    amendment_count: int = 0
    source: str = "UNKNOWN"
    evidence_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RelationshipEvidence:
    """Authoritative standards relationships supported by source records."""
    supersedes: List[Dict[str, str]] = field(default_factory=list)
    superseded_by: List[Dict[str, str]] = field(default_factory=list)
    international_equivalent: List[Dict[str, str]] = field(default_factory=list)
    normative_references: List[str] = field(default_factory=list)
    related_standards: List[Dict[str, str]] = field(default_factory=list)
    has_relationships: bool = False
    relationship_evidence_summary: str = "No explicit relationship evidence recorded in catalogue"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceEvidence:
    """End-to-end data provenance tracking back to authoritative ingestion."""
    source: str = "UNKNOWN"
    source_type: str = "UNKNOWN"
    source_url: Optional[str] = None
    raw_record_ref: Optional[str] = None
    ingestion_run_id: Optional[str] = None
    verification_status: str = "UNKNOWN"       # VERIFIED, CURATED, INFERRED, UNKNOWN
    retrieved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicabilityEvidence:
    """Consumes and structures the result of the Applicability Engine."""
    decision: str = "UNKNOWN"                  # APPLICABLE, REVIEW_REQUIRED, NOT_APPLICABLE, UNKNOWN
    domain_match: bool = False
    product_match: bool = False
    scope_match: bool = False
    application_match: bool = False
    evidence_support: bool = False
    satisfied_conditions: List[str] = field(default_factory=list)
    conflict_flags: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StructuredExplanation:
    """Deterministic, structured explainability without LLM hallucination."""
    why_selected: str
    supporting_facts: List[str] = field(default_factory=list)
    applicability_summary: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    human_review_required: bool = False
    review_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StructuredEvidence:
    """Comprehensive evidence container uniting all evidentiary dimensions."""
    standard_number: Optional[str]
    official_title: Optional[str]
    evidence_strength: str
    bis_scope_evidence: Optional[str]
    scope_status: str                          # AUTHORITATIVE_VERIFIED, CURATED, UNKNOWN
    requirement_match: Dict[str, Any]
    lifecycle: LifecycleEvidence
    relationships: RelationshipEvidence
    provenance: ProvenanceEvidence
    applicability: ApplicabilityEvidence
    explanation: StructuredExplanation
    uncertainty_and_gaps: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_number": self.standard_number,
            "official_title": self.official_title,
            "evidence_strength": self.evidence_strength,
            "bis_scope_evidence": self.bis_scope_evidence,
            "scope_status": self.scope_status,
            "requirement_match": self.requirement_match,
            "lifecycle": self.lifecycle.to_dict(),
            "relationships": self.relationships.to_dict(),
            "provenance": self.provenance.to_dict(),
            "applicability": self.applicability.to_dict(),
            "explanation": self.explanation.to_dict(),
            "uncertainty_and_gaps": self.uncertainty_and_gaps
        }


class StandardsEvidenceBuilder:
    """Assembles traceable structured evidence for recommendations and safe abstentions."""

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db or StandardsDatabase()

    def build_structured_evidence(
        self,
        standard_number: Optional[str],
        requirement_text: str,
        title: Optional[str] = None,
        candidate_search_result: Optional[SearchResult] = None,
        applicability_result: Optional[ApplicabilityResult] = None,
        ambiguity_report: Optional[AmbiguityReport] = None,
        explicit_citation: bool = False,
        missing_information: Optional[List[str]] = None,
        human_review_required: bool = False,
        decision_reason: str = ""
    ) -> StructuredEvidence:
        """Constructs a deterministic, fully grounded StructuredEvidence instance."""

        # ---------------------------------------------------------
        # Case A: Safe Abstention (no standard recommended)
        # ---------------------------------------------------------
        if not standard_number or standard_number in ["INSUFFICIENT_INFORMATION", "UNKNOWN", "NONE"]:
            missing_params = list(missing_information or [])
            if ambiguity_report and ambiguity_report.missing_information:
                for m in ambiguity_report.missing_information:
                    if m not in missing_params:
                        missing_params.append(m)

            competing_cands = []
            clarification = None
            if ambiguity_report:
                competing_cands = ambiguity_report.competing_interpretations or []
                clarification = ambiguity_report.suggested_clarification_question

            uncertainties = []
            if missing_params:
                uncertainties.append(f"Tender specification omits discriminating technical parameter(s): {', '.join(missing_params)}")
            if competing_cands:
                c_names = [c.get("standard_number", "") for c in competing_cands if isinstance(c, dict)]
                uncertainties.append(f"Multiple candidate standards ({' vs '.join(c_names)}) compete for applicability")
            if not uncertainties and decision_reason:
                uncertainties.append(decision_reason)

            review_reasons = []
            if missing_params:
                review_reasons.append("Specification incomplete: engineer clarification required.")
            if competing_cands:
                review_reasons.append("Ambiguity: close competition between standards without distinguishing technical parameters.")

            explanation = StructuredExplanation(
                why_selected="System safely abstained because tender specification lacks critical discriminating parameters to identify a single standard with certainty.",
                supporting_facts=["Tender clause processed by decomposition and applicability analysis."],
                applicability_summary=["No candidate could satisfy unambiguous applicability criteria."],
                uncertainties=uncertainties,
                human_review_required=True,
                review_reasons=review_reasons
            )

            req_match = {
                "matched_text": requirement_text,
                "explicit_citation_found": False,
                "retrieval_signals": {
                    "signal_type": "ABSTENTION_NO_MATCH",
                    "note": "Retrieval candidates were evaluated but failed unambiguous applicability."
                }
            }

            return StructuredEvidence(
                standard_number=None,
                official_title=None,
                evidence_strength=EvidenceStrength.INSUFFICIENT_INFORMATION.value,
                bis_scope_evidence=None,
                scope_status="UNKNOWN",
                requirement_match=req_match,
                lifecycle=LifecycleEvidence(status="UNKNOWN", is_unknown=True, evidence_text="No recommended standard; lifecycle not applicable."),
                relationships=RelationshipEvidence(relationship_evidence_summary="No standard recommended."),
                provenance=ProvenanceEvidence(source="SYSTEM_ABSTENTION", source_type="SAFE_ABSTENTION_ENGINE", verification_status="VERIFIED"),
                applicability=ApplicabilityEvidence(
                    decision="REVIEW_REQUIRED",
                    rejection_reasons=[decision_reason] if decision_reason else ["Insufficient specification parameters."]
                ),
                explanation=explanation,
                uncertainty_and_gaps={
                    "missing_parameters": missing_params,
                    "competing_candidates": competing_cands,
                    "suggested_clarification": clarification or (
                        f"Please specify {', '.join(missing_params)} to identify the exact applicable Indian Standard."
                        if missing_params else "Clarification required from procurement authority."
                    )
                }
            )

        # ---------------------------------------------------------
        # Case B: Standard Recommended (or candidate being evaluated)
        # ---------------------------------------------------------
        std_num_clean = standard_number.split("(")[0].strip()
        db_record = self._lookup_standard_record(standard_number, std_num_clean)

        # Official title
        official_title = (
            (candidate_search_result.full_title if candidate_search_result else None)
            or (db_record.get("full_title") if db_record else None)
            or title
            or "Title not available"
        )

        # 1. BIS Scope Evidence (Never Fabricate!)
        scope_raw = None
        scope_status = "UNKNOWN"
        if db_record and db_record.get("scope"):
            sc = db_record["scope"].strip()
            # Distinguish real scope from synthetic placeholder notes
            if len(sc) > 15 and not sc.lower().startswith("curated reference standard for"):
                scope_raw = sc
                v_stat = db_record.get("verification_status", "CURATED")
                scope_status = "AUTHORITATIVE_VERIFIED" if v_stat == "VERIFIED" else "CURATED"
            elif candidate_search_result and candidate_search_result.scope_summary:
                css = candidate_search_result.scope_summary.strip()
                if len(css) > 15 and not css.lower().startswith("curated reference standard"):
                    scope_raw = css
                    scope_status = "CURATED"

        # 2. Lifecycle Evidence
        lifecycle = self._extract_lifecycle(db_record, candidate_search_result)

        # 3. Relationships Evidence (Authoritative Only)
        relationships = self._extract_relationships(standard_number, db_record, candidate_search_result)

        # 4. Provenance Evidence
        provenance = self._extract_provenance(db_record, candidate_search_result)

        # 5. Applicability Evidence
        app_ev = self._extract_applicability(applicability_result)

        # 6. Requirement Match & Retrieval Signals
        req_match = self._build_requirement_match(
            requirement_text, standard_number, candidate_search_result, explicit_citation
        )

        # 7. Evidence Strength Classification
        ev_strength = self._classify_evidence_strength(
            explicit_citation=explicit_citation,
            has_scope=(scope_raw is not None),
            applicability_result=applicability_result,
            candidate_search_result=candidate_search_result
        )

        # 8. Deterministic Explanation
        explanation = self._build_deterministic_explanation(
            standard_number=standard_number,
            official_title=official_title,
            evidence_strength=ev_strength,
            scope_raw=scope_raw,
            lifecycle=lifecycle,
            applicability_evidence=app_ev,
            human_review_required=human_review_required,
            decision_reason=decision_reason,
            missing_information=missing_information
        )

        # 9. Uncertainty & Gaps
        uncertainty_dict = {
            "missing_parameters": list(missing_information or []),
            "competing_candidates": ambiguity_report.competing_interpretations if ambiguity_report else [],
            "suggested_clarification": ambiguity_report.suggested_clarification_question if ambiguity_report else None,
            "scope_available": (scope_raw is not None),
            "lifecycle_verified": (lifecycle.status in ["ACTIVE", "WITHDRAWN"])
        }

        return StructuredEvidence(
            standard_number=standard_number,
            official_title=official_title,
            evidence_strength=ev_strength.value,
            bis_scope_evidence=scope_raw,
            scope_status=scope_status,
            requirement_match=req_match,
            lifecycle=lifecycle,
            relationships=relationships,
            provenance=provenance,
            applicability=app_ev,
            explanation=explanation,
            uncertainty_and_gaps=uncertainty_dict
        )

    # -----------------------------------------------------------------------
    # Helper extractors
    # -----------------------------------------------------------------------

    def _lookup_standard_record(self, std_num: str, std_num_clean: str) -> Optional[Dict[str, Any]]:
        """Queries database for canonical standard record."""
        # 1. Try canonical ID / standard number lookup
        cand_id = re.sub(r'[\s/:]+', '-', std_num).strip('-')
        rec = self.db.get_standard(cand_id)
        if rec:
            return rec

        cand_id_clean = re.sub(r'[\s/:]+', '-', std_num_clean).strip('-')
        rec = self.db.get_standard(cand_id_clean)
        if rec:
            return rec

        # 2. Try standard_number query
        try:
            with self.db._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM standards WHERE standard_number = ? OR original_standard_identifier = ? OR standard_number LIKE ? LIMIT 1",
                    (std_num, std_num, f"{std_num_clean}%")
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception:
            pass

        return None

    def _extract_lifecycle(
        self,
        db_record: Optional[Dict[str, Any]],
        search_result: Optional[SearchResult]
    ) -> LifecycleEvidence:
        """Extracts canonical lifecycle state: ACTIVE, WITHDRAWN, or UNKNOWN."""
        raw_status = None
        reaffirmed = None
        amends = 0
        src = "UNKNOWN"

        if db_record:
            raw_status = db_record.get("status")
            reaffirmed = db_record.get("reaffirmed_year")
            amends = db_record.get("amendments_count") or 0
            src = db_record.get("source", "STANDARDS_DB")
        elif search_result:
            raw_status = search_result.status
            src = search_result.source_provenance or "SEARCH_RESULT"

        if not raw_status:
            return LifecycleEvidence(
                status="UNKNOWN",
                is_active=False,
                is_withdrawn=False,
                is_unknown=True,
                reaffirmed_year=None,
                amendment_count=0,
                source=src,
                evidence_text="Lifecycle status not found in standard record; marked UNKNOWN."
            )

        st_lower = str(raw_status).strip().lower()
        if "active" in st_lower or st_lower == "current":
            ev_msg = f"BIS catalogue explicitly records status as Active"
            if reaffirmed:
                ev_msg += f" (Reaffirmed: {reaffirmed})"
            if amends > 0:
                ev_msg += f" with {amends} amendment(s)"
            return LifecycleEvidence(
                status="ACTIVE",
                is_active=True,
                is_withdrawn=False,
                is_unknown=False,
                reaffirmed_year=reaffirmed,
                amendment_count=amends,
                source=src,
                evidence_text=ev_msg
            )
        elif "withdrawn" in st_lower or "superseded" in st_lower:
            return LifecycleEvidence(
                status="WITHDRAWN",
                is_active=False,
                is_withdrawn=True,
                is_unknown=False,
                reaffirmed_year=reaffirmed,
                amendment_count=amends,
                source=src,
                evidence_text="BIS catalogue records status as Withdrawn / Superseded."
            )
        else:
            return LifecycleEvidence(
                status="UNKNOWN",
                is_active=False,
                is_withdrawn=False,
                is_unknown=True,
                reaffirmed_year=reaffirmed,
                amendment_count=amends,
                source=src,
                evidence_text=f"Unrecognized lifecycle status '{raw_status}'; marked UNKNOWN."
            )

    def _extract_relationships(
        self,
        std_num: str,
        db_record: Optional[Dict[str, Any]],
        search_result: Optional[SearchResult]
    ) -> RelationshipEvidence:
        """Extracts strictly authoritative relationship evidence (never inferred)."""
        supersedes = []
        superseded_by = []
        intl_equiv = []
        norm_refs = []
        related = []

        std_id = db_record.get("standard_id") if db_record else None
        if not std_id and search_result:
            std_id = search_result.standard_id

        # 1. Explicit relationships from database
        raw_rels = []
        if std_id:
            try:
                raw_rels = self.db.get_relationships(std_id)
            except Exception:
                pass

        if not raw_rels and search_result and search_result.explicit_relationships:
            raw_rels = search_result.explicit_relationships

        for r in raw_rels:
            target = r.get("target") or r.get("target_standard") or ""
            rtype = (r.get("type") or r.get("relationship_type") or "").upper()
            ev = r.get("evidence") or "Authoritative database relationship record"

            if rtype == "SUPERSEDES":
                supersedes.append({"target_standard": target, "evidence": ev})
            elif rtype == "SUPERSEDED_BY":
                superseded_by.append({"target_standard": target, "evidence": ev})
            elif rtype in ["IDENTICAL_ADOPTION", "EQUIVALENT", "INTERNATIONAL_EQUIVALENT"]:
                intl_equiv.append({"target_standard": target, "degree": rtype, "evidence": ev})
            else:
                related.append({"target_standard": target, "relationship_type": rtype, "evidence": ev})

        # 2. Normative references from database
        if std_id:
            try:
                refs = self.db.get_references(std_id)
                norm_refs = [
                    f"{r['referenced_standard_number']}{' (' + str(r['referenced_year']) + ')' if r.get('referenced_year') else ''}"
                    for r in refs
                ]
            except Exception:
                pass
        elif search_result and search_result.referenced_standards:
            norm_refs = search_result.referenced_standards[:10]

        has_any = bool(supersedes or superseded_by or intl_equiv or norm_refs or related)
        summary = (
            f"Verified relationships: {len(supersedes)} superseded, {len(superseded_by)} replaced by, "
            f"{len(intl_equiv)} international adoptions, {len(norm_refs)} normative references."
            if has_any else "No explicit relationship evidence recorded in catalogue."
        )

        return RelationshipEvidence(
            supersedes=supersedes,
            superseded_by=superseded_by,
            international_equivalent=intl_equiv,
            normative_references=norm_refs,
            related_standards=related,
            has_relationships=has_any,
            relationship_evidence_summary=summary
        )

    def _extract_provenance(
        self,
        db_record: Optional[Dict[str, Any]],
        search_result: Optional[SearchResult]
    ) -> ProvenanceEvidence:
        """Preserves end-to-end data provenance metadata."""
        if db_record:
            return ProvenanceEvidence(
                source=db_record.get("source", "BIS_CATALOGUE"),
                source_type="STANDARDS_DB",
                source_url=db_record.get("source_url"),
                raw_record_ref=db_record.get("original_standard_identifier"),
                ingestion_run_id=None,
                verification_status=db_record.get("verification_status", "CURATED"),
                retrieved_at=db_record.get("retrieved_at")
            )
        elif search_result:
            return ProvenanceEvidence(
                source=search_result.source_provenance or "RETRIEVAL_INDEX",
                source_type="CATALOGUE_INDEX",
                source_url=None,
                raw_record_ref=search_result.standard_id,
                ingestion_run_id=None,
                verification_status=search_result.verification_status,
                retrieved_at=None
            )
        return ProvenanceEvidence(
            source="LOCAL_CATALOGUE",
            source_type="INFERRED",
            verification_status="INFERRED"
        )

    def _extract_applicability(
        self,
        app_res: Optional[ApplicabilityResult]
    ) -> ApplicabilityEvidence:
        """Converts ApplicabilityResult into structured applicability evidence."""
        if not app_res:
            return ApplicabilityEvidence(
                decision="UNKNOWN",
                rejection_reasons=["Applicability evaluation not performed."]
            )

        satisfied = []
        if app_res.domain_match:
            satisfied.append("Engineering domain matches tender requirement.")
        if app_res.product_match:
            satisfied.append("Procurement object / product matches standard specification scope.")
        if app_res.scope_match:
            satisfied.append("Scope clause explicitly covers requirement use case.")
        if app_res.application_match:
            satisfied.append("Application environment and installation context compatible.")
        if app_res.evidence_support:
            satisfied.append("Supported by verifiable technical keywords.")

        return ApplicabilityEvidence(
            decision=app_res.decision,
            domain_match=app_res.domain_match,
            product_match=app_res.product_match,
            scope_match=app_res.scope_match,
            application_match=app_res.application_match,
            evidence_support=app_res.evidence_support,
            satisfied_conditions=satisfied,
            conflict_flags=list(app_res.conflict_flags or []),
            rejection_reasons=list(app_res.rejection_reasons or [])
        )

    def _build_requirement_match(
        self,
        req_text: str,
        standard_number: str,
        candidate_search_result: Optional[SearchResult],
        explicit_citation: bool
    ) -> Dict[str, Any]:
        """Captures requirement matching details and preserves retrieval as a supporting signal."""
        retrieval_signals = {}
        if candidate_search_result:
            retrieval_signals = {
                "bm25_score": round(candidate_search_result.bm25_score, 3),
                "semantic_score": round(candidate_search_result.semantic_score, 3),
                "relevance_score": round(candidate_search_result.relevance_score, 3),
                "final_retrieval_score": round(candidate_search_result.final_score, 3),
                "signal_role": "SUPPORTING_RETRIEVAL_SIGNAL_ONLY",
                "note": "Retrieval similarity discovers candidates; authoritative applicability determines applicability."
            }

        return {
            "requirement_text": req_text,
            "target_standard": standard_number,
            "explicit_citation_found": explicit_citation,
            "retrieval_signals": retrieval_signals
        }

    def _classify_evidence_strength(
        self,
        explicit_citation: bool,
        has_scope: bool,
        applicability_result: Optional[ApplicabilityResult],
        candidate_search_result: Optional[SearchResult]
    ) -> EvidenceStrength:
        """Determines evidence hierarchy level without overstating weak signals."""
        if applicability_result and not applicability_result.applicable:
            return EvidenceStrength.CONFLICTING_EVIDENCE

        if explicit_citation:
            return EvidenceStrength.STRONG_EXPLICIT_CITATION

        if has_scope and applicability_result and applicability_result.scope_match:
            return EvidenceStrength.STRONG_AUTHORITATIVE_SCOPE

        if applicability_result and (applicability_result.product_match or applicability_result.application_match):
            return EvidenceStrength.MEDIUM_TECHNICAL_MATCH

        if applicability_result and applicability_result.applicable:
            return EvidenceStrength.MEDIUM_APPLICABILITY_SUPPORT

        if candidate_search_result and (candidate_search_result.bm25_score > 0 or candidate_search_result.semantic_score > 0):
            return EvidenceStrength.WEAK_RETRIEVAL_ONLY

        return EvidenceStrength.INSUFFICIENT_INFORMATION

    def _build_deterministic_explanation(
        self,
        standard_number: str,
        official_title: str,
        evidence_strength: EvidenceStrength,
        scope_raw: Optional[str],
        lifecycle: LifecycleEvidence,
        applicability_evidence: ApplicabilityEvidence,
        human_review_required: bool,
        decision_reason: str,
        missing_information: Optional[List[str]]
    ) -> StructuredExplanation:
        """Constructs plain, deterministic factual explanation sentences."""
        supporting_facts = []
        applicability_summary = list(applicability_evidence.satisfied_conditions)
        uncertainties = []
        review_reasons = []

        # 1. Headline selection reason
        if evidence_strength == EvidenceStrength.STRONG_EXPLICIT_CITATION:
            why_selected = f"Standard {standard_number} is explicitly cited in the procurement tender specification."
            supporting_facts.append("Explicit normative citation detected in requirement text.")
        elif evidence_strength == EvidenceStrength.STRONG_AUTHORITATIVE_SCOPE:
            why_selected = f"Standard {standard_number} matches the required procurement specification and is supported by authoritative BIS scope clause."
            supporting_facts.append("Authoritative BIS scope clause explicitly covers the product/application domain.")
        elif evidence_strength == EvidenceStrength.MEDIUM_TECHNICAL_MATCH:
            why_selected = f"Standard {standard_number} ('{official_title}') covers the technical product and application specified in the tender."
            supporting_facts.append("Extracted technical attributes and product category match the standard specification.")
        else:
            why_selected = f"Standard {standard_number} was identified from the requirement context as a potential match."
            supporting_facts.append("Identified via candidate retrieval and verified against engineering domain constraints.")

        # 2. Lifecycle facts
        if lifecycle.status == "ACTIVE":
            supporting_facts.append(f"Standard is Active in the BIS catalogue{f' (Reaffirmed {lifecycle.reaffirmed_year})' if lifecycle.reaffirmed_year else ''}.")
        elif lifecycle.status == "WITHDRAWN":
            supporting_facts.append("Standard is Withdrawn or Superseded; replacement standard should be verified.")
            uncertainties.append("Standard is not current; verify superseding revision.")
        else:
            uncertainties.append("BIS catalogue does not contain explicit active/withdrawn lifecycle evidence for this entry.")

        # 3. Scope availability
        if not scope_raw:
            uncertainties.append("Full BIS scope clause text is unavailable in the captured catalogue record.")

        # 4. Applicability conflict flags
        if applicability_evidence.conflict_flags:
            for flag in applicability_evidence.conflict_flags:
                uncertainties.append(f"Applicability caveat: {flag}")

        # 5. Missing engineering dimensions
        if missing_information:
            uncertainties.append(f"Missing engineering parameters: {', '.join(missing_information)}")

        # 6. Human review reasons
        if human_review_required:
            if missing_information:
                review_reasons.append(f"Tender specification omits details: {', '.join(missing_information)}.")
            if decision_reason:
                review_reasons.append(decision_reason)
            if not review_reasons:
                review_reasons.append("Technical verification recommended before tender publication.")

        return StructuredExplanation(
            why_selected=why_selected,
            supporting_facts=supporting_facts,
            applicability_summary=applicability_summary,
            uncertainties=uncertainties,
            human_review_required=human_review_required,
            review_reasons=review_reasons
        )
