"""
Module: src/critic.py
Purpose: Evidence-Aware Critic and Decision Layer for Indian Standards Recommendations.

Evaluates retrieved candidates across FIVE core dimensions:
1. Relevance: Component-level and semantic alignment with requirement.
2. Evidence: Provenance, grounding, and strength of scope/metadata evidence.
3. Lifecycle: Active vs Superseded/Withdrawn status and successor availability.
4. Completeness: Specification review completeness from domain analyzer.
5. Ambiguity / Conflict: Competition against alternative candidates and domain coherence.

Trust Rules:
- Never converts weak evidence into high confidence, regardless of retrieval score.
- Distinguishes 'RECOMMEND', 'RECOMMEND_WITH_REVIEW', 'REVIEW_REQUIRED',
  'INSUFFICIENT_EVIDENCE', and 'REJECT'.
- Produces deterministic, evidence-backed 'Why this?' and 'Why not this?' explanations.
- Assigns deterministic risk levels (CRITICAL, HIGH, MEDIUM, LOW) with visible reasons.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
import re

from src.standards import StandardsDatabase
from src.search import SearchResult
from src.validate import validate_standard_status, StandardValidationResult
from src.decompose import RequirementComponent
from src.completeness import SpecificationCompletenessReport, DomainCompletenessAnalyzer
from src.graph import StandardsGraph
from src.applicability import GENERIC_STOPWORDS


@dataclass
class CandidateEvidence:
    """Standardized evidence payload anchored strictly in stored catalogue data."""
    evidence_text: str
    evidence_source: str                    # "BSB Edge Portal", "BIS Standards Catalogue", "Normative Reference"
    source_url: Optional[str]
    provenance: str                         # "VERIFIED", "CURATED", "INFERRED"
    evidence_type: str                      # "scope", "title", "reference", "supersession", "catalogue_metadata"
    evidence_strength: str                  # "STRONG", "MODERATE", "WEAK", "NONE"
    grounded: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateCritique:
    """Critic evaluation for a single candidate standard."""
    standard_number: str
    title: str
    relevance_score: float                  # [0, 1]
    evidence_score: float                   # [0, 1]
    lifecycle_score: float                  # [0, 1]
    completeness_score: float               # [0, 1]
    ambiguity_score: float                  # [0, 1]
    overall_score: float                    # Weighted composite
    decision: str                           # RECOMMEND, RECOMMEND_WITH_REVIEW, REVIEW_REQUIRED, INSUFFICIENT_EVIDENCE, REJECT
    review_required: bool
    risk_level: str                         # LOW, MEDIUM, HIGH, CRITICAL
    risk_reasons: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    evidence: Optional[CandidateEvidence] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_number": self.standard_number,
            "title": self.title,
            "relevance_score": self.relevance_score,
            "evidence_score": self.evidence_score,
            "lifecycle_score": self.lifecycle_score,
            "completeness_score": self.completeness_score,
            "ambiguity_score": self.ambiguity_score,
            "overall_score": self.overall_score,
            "decision": self.decision,
            "review_required": self.review_required,
            "risk_level": self.risk_level,
            "risk_reasons": self.risk_reasons,
            "reasons": self.reasons,
            "evidence": self.evidence.to_dict() if self.evidence else None
        }


@dataclass
class DecisionOutcome:
    """Final decision package for the requirement recommendation."""
    recommended_standard: str
    decision: str                        # RECOMMEND, RECOMMEND_WITH_REVIEW, REVIEW_REQUIRED, INSUFFICIENT_EVIDENCE, REJECT
    review_required: bool
    confidence: str                      # High, Medium, Low
    risk_level: str                      # CRITICAL, HIGH, MEDIUM, LOW
    risk_reasons: List[str]
    primary_critique: CandidateCritique
    all_critiques: List[CandidateCritique]
    why_this: List[str]
    why_not: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_standard": self.recommended_standard,
            "decision": self.decision,
            "review_required": self.review_required,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "risk_reasons": self.risk_reasons,
            "primary_critique": self.primary_critique.to_dict(),
            "all_critiques": [c.to_dict() for c in self.all_critiques],
            "why_this": self.why_this,
            "why_not": self.why_not
        }


class EvidenceAwareCritic:
    """
    Evaluates retrieved standard candidates across 5 deterministic dimensions:
    1. Relevance Score: normalized match score from hybrid retrieval [0, 1]
    2. Evidence Strength: grounded verbatim scope / clause support [0, 1]
    3. Lifecycle Status: active vs superseded vs withdrawn [0, 1]
    4. Specification Completeness: domain parameter coverage ratio [0, 1]
    5. Ambiguity / Conflict: candidate margin delta and domain conflict penalties [0, 1]
    """

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db or StandardsDatabase()
        self.completeness_analyzer = DomainCompletenessAnalyzer()
        self.graph = StandardsGraph(self.db)

    def extract_candidate_evidence(
        self,
        candidate: SearchResult,
        requirement_text: str,
        val_result: Optional[StandardValidationResult] = None
    ) -> CandidateEvidence:
        """
        Extracts and verifies stored evidentiary backing for a candidate.
        Does not invent evidence.
        """
        std = self.db.get_standard(candidate.standard_id)
        if not std:
            return CandidateEvidence(
                evidence_text="Insufficient evidence from the retrieved standards data.",
                evidence_source="UNKNOWN",
                source_url=None,
                provenance="UNKNOWN",
                evidence_type="catalogue_metadata",
                evidence_strength="NONE",
                grounded=False
            )

        provenance = std.get("verification_status", "INFERRED")
        source_url = std.get("source_url")
        scope = std.get("scope") or ""
        notes = std.get("notes") or ""
        source_name = "BSB Edge Portal" if provenance == "VERIFIED" else "BIS Standards Catalogue"

        # Check if this candidate is an authoritative successor
        if val_result and not val_result.is_active and val_result.successor_standard:
            ev_strength = "STRONG" if provenance == "VERIFIED" else "MODERATE"
            return CandidateEvidence(
                evidence_text=val_result.evidence or f"Explicit supersedence relationship recorded in BIS catalogue.",
                evidence_source="BIS Official Supersedence Register",
                source_url=source_url,
                provenance=provenance,
                evidence_type="supersession",
                evidence_strength=ev_strength,
                grounded=True
            )

        # Check if explicitly cited in tender
        if "Explicitly cited in tender" in candidate.relevance_reason:
            return CandidateEvidence(
                evidence_text=f"Tender explicitly requires compliance with {candidate.standard_number}.",
                evidence_source="Tender Document",
                source_url=None,
                provenance="VERIFIED",
                evidence_type="explicit_citation",
                evidence_strength="STRONG",
                grounded=True
            )


        # Check stored scope text
        has_scope = scope and len(scope.strip()) > 15 and "insufficient" not in scope.lower()
        if has_scope:
            full_evidence_corpus = f"{scope} {std.get('full_title', '')}"
            req_words = {w for w in re.findall(r'\b\w{3,}\b', requirement_text.lower()) if w not in GENERIC_STOPWORDS}
            ev_words = {w for w in re.findall(r'\b\w{3,}\b', full_evidence_corpus.lower()) if w not in GENERIC_STOPWORDS}
            overlap = req_words.intersection(ev_words)

            if len(overlap) >= 1:
                # Direct supporting evidence exists in stored scope/title
                if provenance == "VERIFIED":
                    strength = "STRONG"
                elif provenance == "CURATED":
                    strength = "MODERATE"
                else:
                    strength = "WEAK"
                return CandidateEvidence(
                    evidence_text=scope[:400].strip(),
                    evidence_source=source_name,
                    source_url=source_url,
                    provenance=provenance,
                    evidence_type="scope",
                    evidence_strength=strength,
                    grounded=True
                )
            else:
                # Stored scope exists, but does not support this requirement
                return CandidateEvidence(
                    evidence_text=scope[:400].strip(),
                    evidence_source=source_name,
                    source_url=source_url,
                    provenance=provenance,
                    evidence_type="scope",
                    evidence_strength="WEAK",
                    grounded=False
                )

        # Fallback to notes or reference relationships
        if notes and len(notes.strip()) > 15:
            strength = "MODERATE" if provenance == "VERIFIED" else "WEAK"
            return CandidateEvidence(
                evidence_text=notes[:300].strip(),
                evidence_source=source_name,
                source_url=source_url,
                provenance=provenance,
                evidence_type="reference",
                evidence_strength=strength,
                grounded=True
            )

        # Fallback to committee metadata (does not independently establish standard applicability)
        committee = std.get("technical_committee")
        if committee:
            ev_text = f"Catalogue Record: Sectional Committee {committee}, Title: {std.get('full_title')}"
            return CandidateEvidence(
                evidence_text=ev_text,
                evidence_source=source_name,
                source_url=source_url,
                provenance=provenance,
                evidence_type="catalogue_metadata",
                evidence_strength="WEAK",
                grounded=True
            )

        return CandidateEvidence(
            evidence_text="Insufficient evidence from the retrieved standards data.",
            evidence_source=source_name,
            source_url=source_url,
            provenance=provenance,
            evidence_type="catalogue_metadata",
            evidence_strength="NONE",
            grounded=False
        )

    def critique_candidate(
        self,
        candidate: SearchResult,
        requirement_text: str,
        components: List[RequirementComponent],
        completeness: SpecificationCompletenessReport,
        candidate_rank: int = 1,
        alternative_candidate: Optional[SearchResult] = None
    ) -> CandidateCritique:
        """
        Evaluates a candidate standard across the 5 dimensions and determines decision.
        """
        std_num = candidate.standard_number
        val_info = validate_standard_status(std_num, self.db)
        evidence = self.extract_candidate_evidence(candidate, requirement_text, val_info)

        risk_reasons: List[str] = []
        critique_reasons: List[str] = []

        # 1. Relevance Score [0, 1]
        relevance = min(1.0, max(0.0, float(candidate.relevance_score)))

        # 2. Evidence Score [0, 1]
        if evidence.evidence_strength == "STRONG":
            evidence_score = 0.95
            critique_reasons.append(f"Strong evidence grounded in {evidence.evidence_source} ({evidence.provenance})")
        elif evidence.evidence_strength == "MODERATE":
            evidence_score = 0.70
            critique_reasons.append(f"Moderate evidence grounded in {evidence.evidence_source}")
        elif evidence.evidence_strength == "WEAK":
            evidence_score = 0.35
            critique_reasons.append("Weak evidence overlap with stored scope text")
            risk_reasons.append("Weak evidentiary grounding between requirement and standard scope")
        else:
            evidence_score = 0.0
            critique_reasons.append("Insufficient evidence found in stored catalogue data")
            risk_reasons.append("Insufficient stored evidence to establish standard applicability")

        # 3. Lifecycle Score [0, 1]
        if val_info.is_active:
            lifecycle_score = 1.0
            critique_reasons.append("Standard is currently Active and verified in BIS catalogue")
        elif val_info.successor_standard:
            lifecycle_score = 0.30
            critique_reasons.append(f"Standard is SUPERSEDED by {val_info.successor_standard}")
            risk_reasons.append(f"Standard {std_num} is superseded by {val_info.successor_standard}")
        else:
            lifecycle_score = 0.0
            critique_reasons.append(f"Standard status is {val_info.status or 'Withdrawn'}")
            risk_reasons.append(f"Standard {std_num} is inactive ({val_info.status or 'Withdrawn'})")

        # 4. Completeness Score [0, 1]
        completeness_score = min(1.0, max(0.0, float(completeness.completeness_score)))
        if not completeness.is_adequately_specified:
            missing_str = ", ".join(completeness.potentially_missing_parameters[:3])
            critique_reasons.append(f"Specification review indicates missing parameters: {missing_str}")
            risk_reasons.append(f"Potentially missing engineering parameters: {missing_str}")
        else:
            critique_reasons.append(f"Adequate domain parameters identified ({completeness.known_count} known)")

        # 5. Ambiguity / Conflict Score [0, 1]
        ambiguity_score = 1.0
        if alternative_candidate and candidate_rank == 1:
            score_delta = candidate.relevance_score - alternative_candidate.relevance_score
            if score_delta < 0.05 and candidate.relevance_score > 0.40:
                ambiguity_score = 0.50
                critique_reasons.append(
                    f"Close competition with alternative {alternative_candidate.standard_number} (score delta: {score_delta:.3f})"
                )
                if not completeness.is_adequately_specified:
                    ambiguity_score = 0.30
                    risk_reasons.append(
                        f"Ambiguous choice between {std_num} and {alternative_candidate.standard_number} due to missing distinguishing parameters"
                    )

        # Check domain conflicts
        t_low = requirement_text.lower()
        title_low = candidate.full_title.lower()
        has_industrial_or_mv = any(kw in t_low for kw in ["industrial", "process water", "vfd", "medium voltage", "3.3 kv", "panel"])
        is_agri = "agriculture" in title_low or "agricultural" in title_low
        if is_agri and has_industrial_or_mv:
            ambiguity_score = 0.10
            critique_reasons.append("Domain conflict: Agricultural code applied to industrial/MV equipment")
            risk_reasons.append("Domain mismatch: Agricultural irrigation standard selected for industrial equipment")

        # Overall Critic Score
        overall_score = round(
            0.30 * relevance +
            0.30 * evidence_score +
            0.20 * lifecycle_score +
            0.10 * completeness_score +
            0.10 * ambiguity_score,
            3
        )

        # -------------------------------------------------------------------
        # Deterministic Decision Gating & Trust Rules
        # -------------------------------------------------------------------
        review_required = False
        decision = "REVIEW_REQUIRED"

        # Gate 1: Reject domain conflicts or inactive without successor
        if ambiguity_score <= 0.15:
            decision = "REJECT"
            review_required = True
        elif lifecycle_score == 0.0:
            decision = "REJECT"
            review_required = True
        # Gate 2: Insufficient evidence or very low relevance
        elif relevance < 0.35 or evidence.evidence_strength == "NONE" or not evidence.grounded:
            decision = "INSUFFICIENT_EVIDENCE"
            review_required = True
        # Gate 3: Superseded standard cited
        elif lifecycle_score < 1.0:
            decision = "REVIEW_REQUIRED"
            review_required = True
        # Gate 4: TRUST RULE - Strong retrieval + weak/none evidence CANNOT become High confidence recommendation
        elif evidence.evidence_strength in ["WEAK", "NONE"]:
            decision = "INSUFFICIENT_EVIDENCE" if evidence.evidence_strength == "NONE" else "REVIEW_REQUIRED"
            review_required = True
            risk_reasons.append("Trust Gate: High retrieval score capped due to weak/unsupported scope evidence")
        # Gate 5: Incomplete specification in domain requiring critical discriminating parameters
        elif not completeness.is_adequately_specified and getattr(completeness, "critical_missing_count", 0) > 0:
            decision = "REVIEW_REQUIRED"
            review_required = True
        # Gate 6: Close ambiguous candidates without adequate specification
        elif ambiguity_score <= 0.40:
            decision = "REVIEW_REQUIRED"
            review_required = True
        # Gate 7: Valid recommendation with minor review flags
        elif not completeness.is_adequately_specified or ambiguity_score < 0.80:
            decision = "RECOMMEND_WITH_REVIEW"
            review_required = True
        # Gate 8: Clean authoritative recommendation
        else:
            decision = "RECOMMEND"
            review_required = False

        # -------------------------------------------------------------------
        # Deterministic Risk Classification
        # -------------------------------------------------------------------
        if not val_info.is_active or "CRITICAL" in (val_info.warning_message or "") or "Domain conflict" in str(critique_reasons):
            risk_level = "CRITICAL"
        elif decision in ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE"] or len(risk_reasons) >= 2 or not completeness.is_adequately_specified:
            risk_level = "HIGH"
        elif decision == "RECOMMEND_WITH_REVIEW" or len(risk_reasons) == 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return CandidateCritique(
            standard_number=std_num,
            title=candidate.full_title,
            relevance_score=relevance,
            evidence_score=evidence_score,
            lifecycle_score=lifecycle_score,
            completeness_score=completeness_score,
            ambiguity_score=ambiguity_score,
            overall_score=overall_score,
            decision=decision,
            review_required=review_required,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            reasons=critique_reasons,
            evidence=evidence
        )

    def evaluate_candidates(
        self,
        candidates: List[SearchResult],
        requirement_text: str,
        components: List[RequirementComponent],
        completeness: SpecificationCompletenessReport
    ) -> DecisionOutcome:
        """
        Coordinates critique across all retrieved candidates and synthesizes
        'Why this?' and 'Why not this?' explanation outputs.
        """
        if not candidates:
            empty_critique = CandidateCritique(
                standard_number="INSUFFICIENT_INFORMATION",
                title="No Applicable Standard in Local Database",
                relevance_score=0.0,
                evidence_score=0.0,
                lifecycle_score=0.0,
                completeness_score=completeness.completeness_score,
                ambiguity_score=1.0,
                overall_score=0.0,
                decision="INSUFFICIENT_EVIDENCE",
                review_required=True,
                risk_level="HIGH",
                risk_reasons=["No matching standards retrieved from catalogue"],
                reasons=["No candidates met retrieval threshold"],
                evidence=CandidateEvidence(
                    evidence_text="Insufficient evidence from the retrieved standards data.",
                    evidence_source="NONE",
                    source_url=None,
                    provenance="UNKNOWN",
                    evidence_type="catalogue_metadata",
                    evidence_strength="NONE",
                    grounded=False
                )
            )
            return DecisionOutcome(
                recommended_standard="INSUFFICIENT_INFORMATION",
                decision="INSUFFICIENT_EVIDENCE",
                review_required=True,
                confidence="Low",
                risk_level="HIGH",
                risk_reasons=["No matching standards found in database."],
                primary_critique=empty_critique,
                all_critiques=[],
                why_this=["No applicable Indian Standard found in local catalogue meeting relevance criteria."],
                why_not=[]
            )

        # Critique each candidate
        critiques: List[CandidateCritique] = []
        alt = candidates[1] if len(candidates) > 1 else None

        for rank, cand in enumerate(candidates, start=1):
            crit = self.critique_candidate(
                candidate=cand,
                requirement_text=requirement_text,
                components=components,
                completeness=completeness,
                candidate_rank=rank,
                alternative_candidate=alt if rank == 1 else None
            )
            critiques.append(crit)

        top_critique = critiques[0]
        top_cand = candidates[0]

        # Calibrate Confidence with STRICT TRUST GATE INVARIANT:
        # If evidence_strength in ["WEAK", "NONE"], confidence MUST NOT become HIGH.
        if top_critique.evidence and top_critique.evidence.evidence_strength in ["WEAK", "NONE"]:
            if top_critique.evidence.evidence_strength == "NONE" or top_critique.relevance_score < 0.40:
                confidence = "Low"
            else:
                confidence = "Medium" if top_critique.relevance_score >= 0.70 else "Low"
        elif top_critique.decision == "RECOMMEND" and top_critique.relevance_score >= 0.70 and top_critique.evidence and top_critique.evidence.evidence_strength in ["STRONG", "MODERATE"]:
            confidence = "High"
        elif top_critique.decision in ["RECOMMEND", "RECOMMEND_WITH_REVIEW"] and top_critique.evidence and top_critique.evidence.evidence_strength in ["STRONG", "MODERATE"]:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Generate "Why This?"
        why_this = self._generate_why_this(top_critique, top_cand, components)

        # Generate "Why Not This?" for alternative
        why_not = self._generate_why_not(top_critique, critiques[1:] if len(critiques) > 1 else [], candidates)

        return DecisionOutcome(
            recommended_standard=top_critique.standard_number,
            decision=top_critique.decision,
            review_required=top_critique.review_required,
            confidence=confidence,
            risk_level=top_critique.risk_level,
            risk_reasons=top_critique.risk_reasons,
            primary_critique=top_critique,
            all_critiques=critiques,
            why_this=why_this,
            why_not=why_not
        )

    def _generate_why_this(
        self,
        critique: CandidateCritique,
        candidate: SearchResult,
        components: List[RequirementComponent]
    ) -> List[str]:
        """Generates structured evidence-backed reasons for selecting the primary standard."""
        reasons = []
        # Title alignment
        matched_comps = [c.text for c in components if c.text.lower() in candidate.full_title.lower()]
        if matched_comps:
            reasons.append(f"Standard title directly matches requirement component(s): '{', '.join(matched_comps)}'.")
        else:
            reasons.append(f"Official title aligns with specification: '{candidate.full_title}'.")

        # Scope grounding
        if critique.evidence and critique.evidence.grounded and critique.evidence.evidence_text != "Insufficient evidence from the retrieved standards data.":
            ev_snip = critique.evidence.evidence_text[:120].strip() + ("..." if len(critique.evidence.evidence_text) > 120 else "")
            reasons.append(f"Authoritative scope explicitly covers application: \"{ev_snip}\"")

        # Lifecycle
        if critique.lifecycle_score == 1.0:
            reasons.append("Standard is currently active in the BIS repository with verified currency.")

        # Provenance
        if critique.evidence:
            reasons.append(f"Provenance established via {critique.evidence.evidence_source} ({critique.evidence.provenance}).")

        # Multi-component coverage
        if len(components) >= 2:
            reasons.append(f"Candidate addresses multiple decomposed technical aspects of the requirement.")

        # Stored relationship context (depth = 1)
        if hasattr(self, "graph") and self.graph:
            related = self.graph.get_related_standards(candidate.standard_number, limit=2)
            for r in related:
                if r.relationship_type == "REFERENCES" and r.direction == "OUTGOING":
                    reasons.append(f"Cites normative reference {r.standard_number} ({r.title}).")
                elif r.relationship_type == "CODE_OF_PRACTICE_FOR" and r.direction == "OUTGOING":
                    reasons.append(f"Official code of practice associated with {r.standard_number}.")

        return reasons

    def _generate_why_not(
        self,
        primary: CandidateCritique,
        alternatives: List[CandidateCritique],
        candidates: List[SearchResult]
    ) -> List[str]:
        """Generates measurable contrastive reasons explaining why top alternatives were not ranked #1."""
        reasons = []
        if not alternatives:
            return ["No alternative candidate standards met the retrieval threshold."]

        top_alt = alternatives[0]
        alt_cand = candidates[1] if len(candidates) > 1 else None

        # Check explicit relationship from stored graph (e.g. Supersedence)
        if hasattr(self, "graph") and self.graph:
            expl = self.graph.explain_relationship(primary.standard_number, top_alt.standard_number)
            if not expl:
                expl = self.graph.explain_relationship(top_alt.standard_number, primary.standard_number)
            if expl and "SUPERSEDES" in expl:
                reasons.append(
                    f"{top_alt.standard_number} was not selected because the stored relationship identifies it as superseded by {primary.standard_number}."
                )

        # Relevance delta
        score_diff = primary.relevance_score - top_alt.relevance_score
        if score_diff > 0.05:
            reasons.append(
                f"Alternative standard {top_alt.standard_number} has lower composite relevance "
                f"({top_alt.relevance_score:.3f} vs {primary.relevance_score:.3f})."
            )

        # Lifecycle check
        if top_alt.lifecycle_score < primary.lifecycle_score:
            reasons.append(f"Alternative standard {top_alt.standard_number} has lifecycle limitations (status: {top_alt.decision}).")

        # Scope specificity
        if primary.evidence and top_alt.evidence:
            if primary.evidence.evidence_strength == "STRONG" and top_alt.evidence.evidence_strength in ["WEAK", "NONE"]:
                reasons.append(
                    f"Alternative standard {top_alt.standard_number} lacks strong grounded scope evidence for this requirement."
                )

        # Domain specificity
        if alt_cand and ("handbook" in alt_cand.full_title.lower() or "code of practice" in alt_cand.full_title.lower()):
            if "specification" in primary.title.lower():
                reasons.append(
                    f"Alternative {top_alt.standard_number} is a general code of practice/handbook rather than a direct manufacturing product specification."
                )

        if not reasons:
            reasons.append(
                f"Alternative standard {top_alt.standard_number} scored lower across the 5-dimension critic evaluation."
            )

        return reasons
