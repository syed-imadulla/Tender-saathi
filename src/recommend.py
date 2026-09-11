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
from src.critic import EvidenceAwareCritic, CandidateCritique, DecisionOutcome, are_standards_equivalent
from src.graph import StandardsGraph, RelatedStandardResult
from src.audit import TenderAuditEngine, TenderAuditResult
from src.applicability import ApplicabilityGate, ApplicabilityResult, ApplicabilityDecision
from src.regulatory.regulatory_engine import RegulatoryEngine


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
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    deterministic_score: float = 0.0
    reranker_score: Optional[float] = None
    final_score: float = 0.0
    applicability: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequirementRecommendationResult:
    requirement_id: str
    requirement_text: str
    category: str
    explicit_standards_found: List[str]
    candidate_standard: Optional[str]     # Top-1 candidate or None
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
    # Milestone 8 AI Understanding & Reranking fields:
    ai_understanding: Optional[Dict[str, Any]] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    is_ai_fallback: bool = True
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    deterministic_score: float = 0.0
    reranker_score: Optional[float] = None
    final_score: float = 0.0
    # Milestone 9 Applicability Gate fields:
    applicability: Optional[Dict[str, Any]] = None
    # Milestone 10 Standards Dependency & Coverage fields:
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    standards_coverage: Optional[Dict[str, Any]] = None
    potential_gaps: List[Dict[str, Any]] = field(default_factory=list)
    verified_missing: List[Dict[str, Any]] = field(default_factory=list)
    potentially_missing: List[Dict[str, Any]] = field(default_factory=list)
    related_for_review: List[Dict[str, Any]] = field(default_factory=list)
    # Milestone 10 Evidence Consistency & Explanation fields:
    evidence_standard: Optional[str] = None
    why_it_matches: Optional[str] = None
    # Milestone 11 Regulatory & Certification fields:
    regulatory: Optional[Dict[str, Any]] = None

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

    def __init__(
        self,
        db: Optional[StandardsDatabase] = None,
        retrieval_mode: str = "hybrid",
        ai_enabled: Optional[bool] = None,
        ai_parser: Optional[Any] = None
    ):
        self.db = db or StandardsDatabase()
        self.retrieval_mode = retrieval_mode
        self.search_engine = HybridRetrievalEngine(self.db, default_mode=retrieval_mode)
        self.verifier = EvidenceVerifier(self.db)
        self.decomposer = CompoundRequirementDecomposer()
        self.completeness_analyzer = DomainCompletenessAnalyzer()
        self.critic = EvidenceAwareCritic(self.db)
        self.graph = StandardsGraph(self.db)
        self.audit_engine = TenderAuditEngine()
        self.applicability_gate = ApplicabilityGate()
        from src.dependencies import StandardsDependencyEngine
        from src.gap_detection import StandardsGapDetector
        self.dependency_engine = StandardsDependencyEngine(self.graph, self.applicability_gate)
        self.gap_detector = StandardsGapDetector()
        self.regulatory_engine = RegulatoryEngine()
        from src.ai_understanding import AIRequirementParser
        self.ai_parser = ai_parser or AIRequirementParser(enabled=ai_enabled)


    def recommend_for_requirement(self, req: Any, tender_cited_standards: Optional[List[str]] = None) -> RequirementRecommendationResult:
        """Processes an individual Requirement through the end-to-end recommendation workflow."""
        if isinstance(req, str):
            req = extract_from_text(req)
        text = req.requirement_text
        req_id = req.requirement_id
        cat = req.category

        # Step 0: AI Requirement Understanding (converts natural text to structured facets)
        parsed_ai = self.ai_parser.parse(text)

        # Decompose requirement if components not already present
        if not getattr(req, "components", None):
            decomp = self.decomposer.decompose(text)
            req.components = decomp.components
            req.decomposition_confidence = decomp.decomposition_confidence

        # Enrich components with non-duplicate AI understanding facets if active
        if not parsed_ai.is_fallback:
            ai_components = parsed_ai.to_components()
            existing_texts = {c.text.lower() for c in req.components}
            for ac in ai_components:
                if ac.text.lower() not in existing_texts:
                    req.components.append(ac)
                    existing_texts.add(ac.text.lower())


        # Analyze specification completeness across engineering domain
        completeness_report = self.completeness_analyzer.analyze(text, req.components)

        # Step 1: Detect explicit standards mentioned and validate status
        explicit_stds = req.explicit_standards or []
        superseded_explicit_warnings = []
        explicit_search_results = []

        for exp in explicit_stds:
            val_res = validate_standard_status(exp, self.db)
            
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                # 1. Inject the explicit citation itself
                cursor.execute("SELECT * FROM standards WHERE standard_number = ?", (exp,))
                row = cursor.fetchone()
                if row:
                    r_dict = dict(row)
                    exact_res = self.search_engine.det_engine._format_result(
                        r_dict, 
                        score=1.0, 
                        reason=f"Explicitly cited in tender: {exp}"
                    )
                    exact_res.deterministic_score = 1.0
                    exact_res.final_score = 1.0
                    explicit_search_results.append(exact_res)

                # 2. Inject the authoritative successor if superseded
                if not val_res.is_active and val_res.successor_standard:
                    superseded_explicit_warnings.append(val_res.warning_message)
                    successor_number = val_res.successor_standard.split(" : ")[0].strip()
                    succ_row = cursor.execute("SELECT * FROM standards WHERE standard_number = ? OR standard_id = ?",
                                              (successor_number, val_res.successor_standard)).fetchone()
                    if succ_row:
                        s_dict = dict(succ_row)
                        succ_res = self.search_engine.det_engine._format_result(
                            s_dict,
                            score=1.0,
                            reason=f"Authoritative successor for cited standard {exp}"
                        )
                        succ_res.deterministic_score = 1.0
                        succ_res.final_score = 1.0
                        setattr(succ_res, "_explicit_successor_warning", f"Tender cited superseded standard '{exp}'. Recommended current active replacement.")
                        explicit_search_results.append(succ_res)

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

        # Merge explicit citations into search_results so they are evaluated by the Critic
        for esr in explicit_search_results:
            existing = next((r for r in search_results if r.standard_number == esr.standard_number), None)
            if not existing:
                search_results.insert(0, esr)
            else:
                existing.deterministic_score = 1.0
                existing.final_score = max(existing.final_score, 1.0)
                existing.relevance_score = 1.0
                existing.relevance_reason = esr.relevance_reason + " | " + existing.relevance_reason
                if hasattr(esr, "_explicit_successor_warning"):
                    setattr(existing, "_explicit_successor_warning", getattr(esr, "_explicit_successor_warning"))

        # Step 3: Check Ambiguity Heuristics
        ambiguity_flag = False
        ambiguity_reason = ""
        for pattern_kw, pattern_full, reason_desc in AMBIGUITY_PATTERNS:
            if re.search(pattern_kw, text, re.IGNORECASE) and re.search(pattern_full, text, re.IGNORECASE):
                ambiguity_flag = True
                ambiguity_reason = reason_desc
                break

        # Step 3.5: NEW APPLICABILITY GATE (Milestone 9)
        # Evaluate each candidate independently through the Applicability Gate
        applicable_candidates: List[SearchResult] = []
        rejected_candidates: List[Tuple[SearchResult, ApplicabilityResult]] = []
        candidate_applicability_map: Dict[str, ApplicabilityResult] = {}

        for cand in search_results:
            is_explicit = any(exp in cand.relevance_reason or exp in cand.standard_number for exp in explicit_stds)
            app_res = self.applicability_gate.evaluate_candidate(
                candidate=cand,
                requirement_text=text,
                components=req.components,
                parsed_ai=parsed_ai,
                is_explicitly_cited=is_explicit
            )
            candidate_applicability_map[cand.standard_number] = app_res
            if app_res.applicable:
                applicable_candidates.append(cand)
            else:
                rejected_candidates.append((cand, app_res))

        # If ALL candidates fail the applicability gate: ABSTAIN cleanly
        if not applicable_candidates:
            why_not_reasons = []
            for cand, app_res in rejected_candidates[:3]:
                reasons_str = "; ".join(app_res.rejection_reasons) if app_res.rejection_reasons else "Insufficient domain applicability"
                why_not_reasons.append(f"Standard {cand.standard_number} ({cand.full_title}) rejected: {reasons_str}")

            primary_app_res = rejected_candidates[0][1].to_dict() if rejected_candidates else None
            user_facing_explanation = (
                "No reliable Indian Standard match found. "
                "We could not establish a sufficiently supported Indian Standard for this requirement from the available catalogue. "
                "Human review required."
            )

            return RequirementRecommendationResult(
                requirement_id=req_id,
                requirement_text=text,
                category=cat,
                explicit_standards_found=explicit_stds,
                candidate_standard=None,
                title="No Reliable Indian Standard Match Found",
                status="Unknown",
                version_role="UNKNOWN",
                relevance_score=0.0,
                confidence="Low",
                evidence="We could not establish a sufficiently supported Indian Standard for this requirement from the available catalogue.",
                provenance="UNKNOWN",
                human_review_required=True,
                reason=user_facing_explanation,
                recommendations=[],
                alternatives=[],
                decomposed_components=[c.to_dict() if hasattr(c, "to_dict") else c for c in getattr(req, "components", [])],
                critic_result={
                    "decision": "NO_RELIABLE_MATCH",
                    "reasons": ["All candidates rejected by Applicability Gate."],
                    "risk_level": "HIGH",
                    "risk_reasons": ["No reliable Indian Standard match found in available catalogue."]
                },
                why_this=[],
                why_not=why_not_reasons,
                risk_level="HIGH",
                risk_reasons=["No reliable Indian Standard match found in available catalogue."],
                specification_completeness=completeness_report.to_dict(),
                ai_understanding=parsed_ai.to_dict(),
                ai_provider=parsed_ai.ai_provider,
                ai_model=parsed_ai.ai_model,
                is_ai_fallback=parsed_ai.is_fallback,
                bm25_score=0.0,
                semantic_score=0.0,
                deterministic_score=0.0,
                reranker_score=None,
                final_score=0.0,
                applicability=primary_app_res,
                evidence_standard=None,
                why_it_matches="No reliable Indian Standard match found in the available catalogue.",
                regulatory=self.regulatory_engine.evaluate_to_dict(None, text)
            )

        # Step 4: Run Critic across Applicable Candidate Pool
        critic_outcome = self.critic.evaluate_candidates(
            candidates=applicable_candidates,
            requirement_text=text,
            components=req.components,
            completeness=completeness_report
        )

        # Step 5: Validate and Ground Candidates
        recommendations: List[StandardRecommendation] = []

        for sr in applicable_candidates:
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
            
            # If this candidate was injected as an authoritative successor, preserve the warning
            if hasattr(sr, "_explicit_successor_warning"):
                warning = getattr(sr, "_explicit_successor_warning")

            app_dict = candidate_applicability_map.get(sr.standard_number).to_dict() if sr.standard_number in candidate_applicability_map else None

            if sr.year and not (f": {sr.year}" in sr.standard_number or sr.standard_number.endswith(str(sr.year))):
                rec_std_num = f"{sr.standard_number} : {sr.year}"
            else:
                rec_std_num = sr.standard_number

            recommendations.append(StandardRecommendation(
                standard_number=rec_std_num,
                title=sr.full_title,
                status=status_str,
                version_role=version_role,
                relevance_score=round(sr.relevance_score, 3),
                confidence=conf,
                evidence=evidence_str,
                provenance=sr.verification_status,
                superseded_warning=warning,
                technical_committee=None,
                bm25_score=round(sr.bm25_score, 3),
                semantic_score=round(sr.semantic_score, 3),
                deterministic_score=round(sr.deterministic_score, 3),
                reranker_score=round(sr.reranker_score, 3) if sr.reranker_score is not None else None,
                final_score=round(sr.final_score, 3),
                applicability=app_dict
            ))

        top_rec = recommendations[0]
        alternatives = [r.standard_number for r in recommendations[1:4]]

        # Human Review and Risk Decision Logic
        if superseded_explicit_warnings:
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

        # Step 8: Standards Dependency & Coverage Analysis (Milestone 10)
        dep_report = self.dependency_engine.analyze_dependencies(
            requirement=req,
            primary_standard=top_rec.standard_number,
            primary_title=top_rec.title
        )
        cov_map = self.gap_detector.detect_gaps(
            requirement=req,
            primary_standard=top_rec.standard_number,
            primary_title=top_rec.title,
            dependency_report=dep_report,
            completeness_report=completeness_report.to_dict(),
            tender_cited_standards=explicit_stds
        )

        dep_dicts = [d.to_dict() for d in dep_report.all_dependencies]
        cov_dict = cov_map.to_dict()
        all_gap_dicts = [g.to_dict() for g in cov_map.all_gaps]
        ver_missing_dicts = [g.to_dict() for g in cov_map.standard_gaps if g.gap_severity == "VERIFIED_MISSING"]
        pot_missing_dicts = [g.to_dict() for g in cov_map.standard_gaps if g.gap_severity == "POTENTIALLY_MISSING"]
        rel_review_dicts = [g.to_dict() for g in cov_map.standard_gaps if g.gap_severity == "RELATED_FOR_REVIEW"]

        # Strict Evidence Consistency Rule Check:
        primary_crit = critic_outcome.primary_critique
        crit_ev = primary_crit.evidence if primary_crit else None
        evidence_std = getattr(crit_ev, "standard_number", None) or top_rec.standard_number

        is_ev_consistent = are_standards_equivalent(top_rec.standard_number, evidence_std)
        if not is_ev_consistent:
            why_it_matches = "Match identified from the requirement context; supporting evidence needs review."
            human_review_required = True
            decision_reason = "Evidence consistency validation failed: candidate and evidence standards mismatch."
            evidence_std = None
        else:
            # Canonical alignment: ensure evidence_standard strictly matches candidate_standard
            evidence_std = top_rec.standard_number
            # Build clean candidate-specific why_it_matches
            scope_snip = None
            for item in why_this:
                if "Authoritative scope explicitly covers application:" in item:
                    scope_snip = item.replace("Authoritative scope explicitly covers application:", "").strip(' "\'')
                    scope_snip = re.sub(r'^(Exact Match:\s*|Direct Match:\s*)', '', scope_snip, flags=re.IGNORECASE).strip()
                    break

            if scope_snip and len(scope_snip) > 10 and not scope_snip.lower().startswith("insufficient"):
                why_it_matches = scope_snip
            elif top_rec.evidence and "insufficient" not in top_rec.evidence.lower():
                why_it_matches = re.sub(r'^(Exact Match:\s*|Direct Match:\s*)', '', top_rec.evidence, flags=re.IGNORECASE).strip()
            elif top_rec.title:
                why_it_matches = f"Official title aligns with specification: {top_rec.title}."
            else:
                why_it_matches = f"Standard {top_rec.standard_number} verified against requirement specification."

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
            related_standards=related_standards_dicts,
            ai_understanding=parsed_ai.to_dict(),
            ai_provider=parsed_ai.ai_provider,
            ai_model=parsed_ai.ai_model,
            is_ai_fallback=parsed_ai.is_fallback,
            bm25_score=top_rec.bm25_score,
            semantic_score=top_rec.semantic_score,
            deterministic_score=top_rec.deterministic_score,
            reranker_score=top_rec.reranker_score,
            final_score=top_rec.final_score,
            applicability=top_rec.applicability,
            dependencies=dep_dicts,
            standards_coverage=cov_dict,
            potential_gaps=all_gap_dicts,
            verified_missing=ver_missing_dicts,
            potentially_missing=pot_missing_dicts,
            related_for_review=rel_review_dicts,
            evidence_standard=evidence_std,
            why_it_matches=why_it_matches,
            regulatory=self.regulatory_engine.evaluate_to_dict(top_rec.standard_number, text)
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

    def audit_tender(
        self,
        results: List[RequirementRecommendationResult],
        tender_id: str = "TENDER_AUDIT"
    ) -> TenderAuditResult:
        """Audits a list of requirement recommendation results for a tender."""
        return self.audit_engine.audit_tender(results, tender_id=tender_id)

    def audit_pdf(self, pdf_path: str, tender_id: Optional[str] = None) -> TenderAuditResult:
        """Extracts requirements from PDF, runs recommendations, and performs full tender audit."""
        report = self.recommend_for_pdf(pdf_path, tender_id=tender_id)
        return self.audit_engine.audit_report(report)

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
