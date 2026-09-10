"""
Module: src/recommend.py
Purpose: Central StandardsRecommender coordinating the end-to-end pipeline.

Pipeline:
Tender PDF / Text
  -> Requirement extraction & categorization (src.extract)
  -> Standards search with version-awareness (src.search)
  -> Status & supersession validation (src.validate)
  -> Evidence grounding against Scope/Metadata (src.evidence)
  -> Confidence calibration & Ambiguity detection
  -> Human-review decision
  -> Final structured recommendation
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import re

from src.standards import StandardsDatabase
from src.search import SearchResult
from src.retrieval import HybridRetrievalEngine
from src.validate import validate_standard_status, StandardValidationResult
from src.evidence import EvidenceVerifier
from src.extract import Requirement, extract_from_text, extract_from_pdf
from src.decompose import CompoundRequirementDecomposer, RequirementComponent
from src.completeness import DomainCompletenessAnalyzer, SpecificationCompletenessReport
from src.critic import EvidenceAwareCritic, CandidateCritique, DecisionOutcome
from src.graph import StandardsGraph, RelatedStandardResult


# ---------------------------------------------------------------------------
# Output Data Models
# ---------------------------------------------------------------------------

@dataclass
class StandardRecommendation:
    standard_number: str
    title: str
    status: str
    version_role: str                     # CURRENT_ACTIVE, REPLACED_OR_SUPERSEDED, REFERENCE_ONLY
    relevance_score: float
    confidence: str                       # High, Medium, Low
    evidence: str
    provenance: str                       # VERIFIED (BSB Edge), CURATED (BIS Catalogue), INFERRED
    superseded_warning: Optional[str] = None
    technical_committee: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequirementRecommendationResult:
    requirement_id: str
    requirement_text: str
    category: str
    explicit_standards_found: List[str]
    candidate_standard: str               # Top-1 candidate
    title: str
    status: str
    version_role: str
    relevance_score: float
    confidence: str
    evidence: str
    provenance: str
    human_review_required: bool
    reason: str
    recommendations: List[StandardRecommendation] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    decomposed_components: List[Dict[str, Any]] = field(default_factory=list)
    # Milestone 3 Critic & Decision Layer fields:
    critic_result: Optional[Dict[str, Any]] = None
    why_this: List[str] = field(default_factory=list)
    why_not: List[str] = field(default_factory=list)
    risk_level: str = "LOW"
    risk_reasons: List[str] = field(default_factory=list)
    specification_completeness: Optional[Dict[str, Any]] = None
    # Milestone 5 Evidence & Relationship Graph fields:
    related_standards: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TenderRecommendationReport:
    tender_id: str
    total_requirements: int
    results: List[RequirementRecommendationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Ambiguity & Specificity Rules
# ---------------------------------------------------------------------------

# Patterns where requirement text is under-specified and requires human engineer clarification
AMBIGUITY_PATTERNS = [
    (r'\bvalves?\b', r'(?:(?:repair|replacement|overhaul|maintenance).*valve|valve.*(?:repair|replacement|overhaul|maintenance))',
     "Tender specifies valve work without defining valve nominal diameter (DN), pressure rating (PN), body metallurgy (cast iron vs bronze vs forged steel), or process medium."),
    (r'\b(?:food outlet|canteen|cafeteria|catering|kiosk)\b.*(?:bot|concession|revenue share)', r'.*',
     "Commercial BOT concession agreement: requires administrative review to confirm whether technical scoring mandates BIS food hygiene codes (IS 2491 / IS 15000) or FSSAI statutory licensing."),
    (r'\bsewerage\s+pipeline\b', r'sewerage.*pipeline.*(?!rcc|hdpe|pvc|ci|concrete)',
     "Tender states 'Sewerage pipeline' without specifying pipe material (Precast Concrete IS 458 vs Structured Wall Polyethylene IS 14333). Inspection of detailed Bill of Quantities (BOQ) required.")
]


# ---------------------------------------------------------------------------
# Recommender Engine
# ---------------------------------------------------------------------------

class StandardsRecommender:
    """End-to-end Indian Standards Recommendation Engine with compound decomposition."""

    def __init__(self, db: Optional[StandardsDatabase] = None, retrieval_mode: str = "hybrid"):
        self.db = db or StandardsDatabase()
        self.retrieval_mode = retrieval_mode
        self.search_engine = HybridRetrievalEngine(self.db, default_mode=retrieval_mode)
        self.verifier = EvidenceVerifier(self.db)
        self.decomposer = CompoundRequirementDecomposer()
        self.completeness_analyzer = DomainCompletenessAnalyzer()
        self.critic = EvidenceAwareCritic(self.db)
        self.graph = StandardsGraph(self.db)

    def recommend_for_requirement(self, req: Requirement) -> RequirementRecommendationResult:
        """Processes an individual Requirement through the end-to-end recommendation workflow."""
        text = req.requirement_text
        req_id = req.requirement_id
        cat = req.category

        # Decompose requirement if components not already present
        if not getattr(req, "components", None):
            decomp = self.decomposer.decompose(text)
            req.components = decomp.components
            req.decomposition_confidence = decomp.decomposition_confidence

        # Analyze specification completeness across engineering domain
        completeness_report = self.completeness_analyzer.analyze(text, req.components)

        # Step 1: Detect explicit standards mentioned and validate status
        explicit_stds = req.explicit_standards or []
        superseded_explicit_warnings = []
        successor_recommendations = []

        for exp in explicit_stds:
            val_res = validate_standard_status(exp, self.db)
            if not val_res.is_active and val_res.successor_standard:
                superseded_explicit_warnings.append(val_res.warning_message)
                successor_recommendations.append(StandardRecommendation(
                    standard_number=val_res.successor_standard,
                    title=val_res.successor_title or "Authoritative Successor Standard",
                    status="Active",
                    version_role="CURRENT_ACTIVE",
                    relevance_score=1.0,
                    confidence="High",
                    evidence=val_res.evidence or "Explicit supersedence relationship recorded in BIS database.",
                    provenance="VERIFIED",
                    superseded_warning=f"Tender cited superseded standard '{exp}'. Recommended current active replacement.",
                    technical_committee=None
                ))

        # Step 2: Multi-modal Search over BIS Standards with Decomposed Components
        # Primary search using full requirement text and decomposed components
        search_results = self.search_engine.search(
            text, top_k=5, components=req.components, mode=self.retrieval_mode
        )

        # Secondary search if primary yields low results or for multi-item requirements
        if len(search_results) < 2:
            # Extract key noun chunks from components or text
            sub_queries = [c.text for c in req.components if c.component_type in ["material", "product", "equipment", "control", "electrical"]]
            if not sub_queries:
                sub_queries = self._extract_subqueries(text)
            for sq in sub_queries:
                extra_hits = self.search_engine.search(
                    sq, top_k=3, components=req.components, mode=self.retrieval_mode
                )
                for eh in extra_hits:
                    if not any(r.standard_id == eh.standard_id for r in search_results):
                        search_results.append(eh)

        # Step 3: Check Ambiguity Heuristics
        ambiguity_flag = False
        ambiguity_reason = ""
        for pattern_kw, pattern_full, reason_desc in AMBIGUITY_PATTERNS:
            if re.search(pattern_kw, text, re.IGNORECASE) and re.search(pattern_full, text, re.IGNORECASE):
                ambiguity_flag = True
                ambiguity_reason = reason_desc
                break

        # Step 4: Run Critic across Candidate Pool
        critic_outcome = self.critic.evaluate_candidates(
            candidates=search_results,
            requirement_text=text,
            components=req.components,
            completeness=completeness_report
        )

        # Step 5: Validate and Ground Candidates
        recommendations: List[StandardRecommendation] = []

        # Add any successors from explicit mentions first
        for sr in successor_recommendations:
            recommendations.append(sr)

        for sr in search_results:
            # Avoid duplicate standard numbers
            if any(r.standard_number == sr.standard_number for r in recommendations):
                continue

            # Ground claim with Scope / Title evidence
            claim = self.verifier.verify_claim(sr.full_title, sr.standard_id, expected_section="Scope")
            evidence_str = claim.source_text if claim.is_grounded else sr.scope_summary or sr.relevance_reason

            # Validate active/superseded status
            val_info = validate_standard_status(sr.standard_number, self.db)
            status_str = val_info.status if val_info.is_known else sr.status
            version_role = "CURRENT_ACTIVE" if val_info.is_active else "REPLACED_OR_SUPERSEDED"

            # Confidence Calibration with Trust Gate
            cand_ev = self.critic.extract_candidate_evidence(sr, text, val_info)
            if cand_ev.evidence_strength in ["WEAK", "NONE"]:
                conf = "Medium" if sr.relevance_score >= 0.70 and cand_ev.evidence_strength == "WEAK" else "Low"
            elif sr.relevance_score >= 0.75 and val_info.is_active:
                conf = "High"
            elif sr.relevance_score >= 0.40 and val_info.is_active:
                conf = "Medium"
            else:
                conf = "Low"

            if ambiguity_flag:
                conf = "Low" if conf == "Medium" else "Medium"

            warning = val_info.warning_message if not val_info.is_active else None

            recommendations.append(StandardRecommendation(
                standard_number=f"{sr.standard_number} : {sr.year}" if sr.year else sr.standard_number,
                title=sr.full_title,
                status=status_str,
                version_role=version_role,
                relevance_score=round(sr.relevance_score, 3),
                confidence=conf,
                evidence=evidence_str,
                provenance=sr.verification_status,
                superseded_warning=warning,
                technical_committee=None
            ))

        # Step 6: Format Final Result and Human-Review Gating
        if not recommendations:
            return RequirementRecommendationResult(
                requirement_id=req_id,
                requirement_text=text,
                category=cat,
                explicit_standards_found=explicit_stds,
                candidate_standard="INSUFFICIENT_INFORMATION",
                title="No Applicable Standard in Local Database",
                status="Unknown",
                version_role="UNKNOWN",
                relevance_score=0.0,
                confidence="Low",
                evidence="Insufficient evidence from the retrieved BIS standards to establish applicability.",
                provenance="UNKNOWN",
                human_review_required=True,
                reason=ambiguity_reason if ambiguity_flag else "No matching standard with sufficient confidence found in local catalogue. Requires BIS portal search.",
                recommendations=[],
                alternatives=[],
                decomposed_components=[c.to_dict() if hasattr(c, "to_dict") else c for c in getattr(req, "components", [])],
                critic_result=critic_outcome.primary_critique.to_dict(),
                why_this=critic_outcome.why_this,
                why_not=critic_outcome.why_not,
                risk_level=critic_outcome.risk_level,
                risk_reasons=critic_outcome.risk_reasons,
                specification_completeness=completeness_report.to_dict()
            )

        top_rec = recommendations[0]
        alternatives = [r.standard_number for r in recommendations[1:4]]

        # Human Review and Risk Decision Logic
        if successor_recommendations:
            human_review_required = True
            decision_reason = f"Tender cited superseded standard '{explicit_stds[0]}'. Recommended current active replacement."
            risk_level = "CRITICAL"
            risk_reasons = ["Tender explicitly cited a superseded standard requiring replacement verification."]
            why_this = ["Recommended authoritative active successor standard recorded in BIS database."]
            why_not = ["Original cited standard is superseded/obsolete."]
            conf = "High"
        elif ambiguity_flag:
            human_review_required = True
            decision_reason = ambiguity_reason
            risk_level = "HIGH"
            risk_reasons = critic_outcome.risk_reasons or [ambiguity_reason]
            why_this = critic_outcome.why_this
            why_not = critic_outcome.why_not
            conf = "Low" if top_rec.confidence == "Medium" else top_rec.confidence
        elif top_rec.confidence == "Low" or top_rec.relevance_score < 0.35:
            human_review_required = True
            decision_reason = "Low confidence retrieval match (<0.35 score). Technical engineer verification required."
            risk_level = "HIGH"
            risk_reasons = critic_outcome.risk_reasons or ["Low confidence retrieval match (<0.35 score)"]
            why_this = critic_outcome.why_this
            why_not = critic_outcome.why_not
            conf = "Low"
        elif top_rec.version_role == "REPLACED_OR_SUPERSEDED":
            human_review_required = True
            decision_reason = f"Candidate standard {top_rec.standard_number} is superseded. Review replacement status."
            risk_level = "CRITICAL"
            risk_reasons = [f"Standard {top_rec.standard_number} is superseded"]
            why_this = critic_outcome.why_this
            why_not = critic_outcome.why_not
            conf = "Low"
        elif critic_outcome.decision in ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE", "REJECT"]:
            human_review_required = True
            decision_reason = (
                critic_outcome.primary_critique.reasons[0]
                if critic_outcome.primary_critique.reasons else
                "Review required prior to procurement."
            )
            risk_level = critic_outcome.risk_level
            risk_reasons = critic_outcome.risk_reasons
            why_this = critic_outcome.why_this
            why_not = critic_outcome.why_not
            conf = critic_outcome.confidence
        else:
            human_review_required = False
            conf = critic_outcome.confidence
            decision_reason = f"Authoritative active standard {top_rec.standard_number} verified against scope with {conf} confidence."
            risk_level = critic_outcome.risk_level
            risk_reasons = critic_outcome.risk_reasons
            why_this = critic_outcome.why_this
            why_not = critic_outcome.why_not

        # Step 7: Explore lightweight Evidence & Relationship Graph (Depth = 1)
        related_stds_res = self.graph.get_related_standards(top_rec.standard_number, limit=5)
        related_standards_dicts = [r.to_dict() for r in related_stds_res]

        return RequirementRecommendationResult(
            requirement_id=req_id,
            requirement_text=text,
            category=cat,
            explicit_standards_found=explicit_stds,
            candidate_standard=top_rec.standard_number,
            title=top_rec.title,
            status=top_rec.status,
            version_role=top_rec.version_role,
            relevance_score=top_rec.relevance_score,
            confidence=conf,
            evidence=top_rec.evidence,
            provenance=top_rec.provenance,
            human_review_required=human_review_required,
            reason=decision_reason,
            recommendations=recommendations,
            alternatives=alternatives,
            decomposed_components=[c.to_dict() if hasattr(c, "to_dict") else c for c in getattr(req, "components", [])],
            critic_result=critic_outcome.primary_critique.to_dict(),
            why_this=why_this,
            why_not=why_not,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            specification_completeness=completeness_report.to_dict(),
            related_standards=related_standards_dicts
        )

    def recommend_for_text(self, text: str, req_id: str = "REQ-001") -> RequirementRecommendationResult:
        """Extracts requirement from text and executes recommendation."""
        req = extract_from_text(text, requirement_id=req_id)
        return self.recommend_for_requirement(req)

    def recommend_for_pdf(self, pdf_path: str, tender_id: Optional[str] = None) -> TenderRecommendationReport:
        """Extracts all requirements from a tender PDF and runs the recommendation pipeline."""
        reqs = extract_from_pdf(pdf_path, tender_id=tender_id)
        results = [self.recommend_for_requirement(r) for r in reqs]
        t_id = tender_id or (reqs[0].tender_id if reqs else "T_UNKNOWN")
        return TenderRecommendationReport(
            tender_id=t_id,
            total_requirements=len(results),
            results=results
        )

    def _extract_subqueries(self, text: str) -> List[str]:
        """Extracts key noun phrases or sub-clauses for targeted retrieval."""
        subqueries = []
        chunks = re.split(r'[,;]|\band\b|\bincl\b|\bwith\b', text, flags=re.IGNORECASE)
        for ch in chunks:
            clean = ch.strip()
            if len(clean) > 8 and any(kw in clean.lower() for kw in [
                "pipe", "valve", "tile", "sanitary", "fittings", "cable", "transformer",
                "food", "hygiene", "concrete", "earthing", "pump", "insulation", "panel"
            ]):
                subqueries.append(clean)
        return subqueries
