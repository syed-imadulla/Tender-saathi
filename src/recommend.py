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
from typing import List, Optional, Dict, Any, Tuple
import re

from src.standards import StandardsDatabase, classify_standard_role
from src.search import SearchResult
from src.retrieval import HybridRetrievalEngine
from src.validate import validate_standard_status, StandardValidationResult
from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.evidence import EvidenceVerifier
from src.extract import Requirement, extract_from_text, extract_from_pdf, detect_technical_domain
from src.decompose import CompoundRequirementDecomposer, RequirementComponent
from src.completeness import DomainCompletenessAnalyzer, SpecificationCompletenessReport
from src.critic import EvidenceAwareCritic, CandidateCritique, DecisionOutcome, are_standards_equivalent
from src.graph import StandardsGraph, RelatedStandardResult
from src.audit import TenderAuditEngine, TenderAuditResult
from src.applicability import ApplicabilityGate, ApplicabilityResult, ApplicabilityDecision
from src.regulatory.regulatory_engine import RegulatoryEngine
from src.ambiguity import AmbiguityEngine, AmbiguityState, AmbiguityReport
from src.evidence_intelligence import StandardsEvidenceBuilder
from src.regulatory.external_authority import ExternalAuthorityRegistry


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
    standard_role: str = "PRIMARY_PRODUCT"
    structured_evidence: Optional[Dict[str, Any]] = None
    trace_record: Optional[Dict[str, Any]] = None
    clause_evidence: Optional[Dict[str, Any]] = None

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
    # Milestone 12 Ambiguity & Clarification fields:
    ambiguity_state: str = "CLEAR"
    ambiguity_reason: str = ""
    retrieval_status: str = "CANDIDATES_FOUND"
    applicability_status: str = "VIABLE_CANDIDATE"
    evidence_status: str = "VALID"
    missing_information: List[str] = field(default_factory=list)
    competing_interpretations: List[Dict[str, Any]] = field(default_factory=list)
    suggested_clarification_question: Optional[str] = None
    unresolved_components: List[str] = field(default_factory=list)
    standard_role: str = "PRIMARY_PRODUCT"
    multilingual: Optional[Dict[str, Any]] = None
    structured_evidence: Optional[Dict[str, Any]] = None
    # Phase 9: Multi-Component, External Regulatory & Lifecycle Currency fields:
    component_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    external_regulations: List[Dict[str, Any]] = field(default_factory=list)
    lifecycle_warnings: List[Dict[str, Any]] = field(default_factory=list)
    amendment_metadata: Optional[Dict[str, Any]] = None
    # Phase 16 Evidence Traceability & Verification fields:
    trace_record: Optional[Dict[str, Any]] = None
    component_trace_records: List[Dict[str, Any]] = field(default_factory=list)
    clause_evidence: Optional[Dict[str, Any]] = None
    # Phase 27: Multi-Package & Traceability Tier fields:
    package_id: Optional[str] = "PKG-01"
    package_name: Optional[str] = "Main Scope"
    domain: Optional[str] = None
    verification_tier: Optional[str] = None  # CLAUSE_VERIFIED, CATALOGUE_DISCOVERED, SAFE_ABSTENTION
    passage_id: Optional[str] = None
    clause_number: Optional[str] = None
    edition_year: Optional[str] = None
    traversed_cross_references: List[Dict[str, Any]] = field(default_factory=list)

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
        ai_parser: Optional[Any] = None,
        ambiguity_engine: Optional[Any] = None,
        applicability_gate: Optional[Any] = None,
        critic: Optional[Any] = None,
        corpus_storage: Optional[Any] = None,
        clause_retriever: Optional[Any] = None
    ):
        self.db = db or StandardsDatabase()
        self.retrieval_mode = retrieval_mode
        self.search_engine = HybridRetrievalEngine(self.db, default_mode=retrieval_mode)
        self.verifier = EvidenceVerifier(self.db)
        self.decomposer = CompoundRequirementDecomposer()
        self.completeness_analyzer = DomainCompletenessAnalyzer()
        self.critic = critic or EvidenceAwareCritic(self.db)
        self.graph = StandardsGraph(self.db)
        self.audit_engine = TenderAuditEngine()
        self.applicability_gate = applicability_gate or ApplicabilityGate()
        from src.dependencies import StandardsDependencyEngine
        from src.gap_detection import StandardsGapDetector
        self.dependency_engine = StandardsDependencyEngine(self.graph, self.applicability_gate)
        self.gap_detector = StandardsGapDetector()
        self.regulatory_engine = RegulatoryEngine()
        from src.ai_understanding import AIRequirementParser
        self.ai_parser = ai_parser or AIRequirementParser(enabled=ai_enabled)
        from src.ambiguity import AmbiguityEngine
        self.ambiguity_engine = ambiguity_engine or AmbiguityEngine()
        from src.multilingual import MultilingualTechnicalNormalizer
        self.multilingual_normalizer = MultilingualTechnicalNormalizer()
        self.evidence_builder = StandardsEvidenceBuilder(self.db)
        self.external_authority_registry = ExternalAuthorityRegistry()
        from src.corpus.storage import CorpusStorage
        from src.corpus.retriever import ClauseRetriever
        self.corpus_storage = corpus_storage or CorpusStorage()
        self.clause_retriever = clause_retriever or ClauseRetriever(storage=self.corpus_storage)
        from src.traceability import TraceableEvidenceValidator
        self.evidence_validator = TraceableEvidenceValidator(self.db, corpus_storage=self.corpus_storage)

    def _evaluate_component_recommendations(
        self,
        req_id: str,
        components: List[Any],
        category: str
    ) -> List[Dict[str, Any]]:
        """
        Evaluates independent technical components from compound requirements
        without mutual suppression, providing per-component candidates and dependencies.
        """
        component_bundles: List[Dict[str, Any]] = []
        substantive_types = {"material", "product", "equipment", "electrical", "control"}

        substantive_comps = [
            c for c in components
            if (getattr(c, "component_type", None) or (c.get("component_type") if isinstance(c, dict) else None)) in substantive_types
        ]

        # Deduplicate components by text
        seen_texts = set()
        dedup_comps = []
        for c in substantive_comps:
            t = (getattr(c, "text", None) or (c.get("text") if isinstance(c, dict) else str(c))).strip().lower()
            if t and t not in seen_texts:
                seen_texts.add(t)
                dedup_comps.append(c)

        for idx, comp in enumerate(dedup_comps):
            comp_text = getattr(comp, "text", None) or (comp.get("text") if isinstance(comp, dict) else str(comp))
            comp_domain = getattr(comp, "domain", None) or (comp.get("domain") if isinstance(comp, dict) else category)
            comp_role = getattr(comp, "role", None) or (comp.get("role") if isinstance(comp, dict) else getattr(comp, "component_type", None)) or "COMPONENT"
            comp_id = f"{req_id}-C{idx + 1}"

            comp_query = f"{comp_text} {comp_domain}".strip()
            c_search = self.search_engine.search(comp_query, top_k=3, mode="hybrid")

            matched_c = None
            for cs in c_search:
                # Multi-part disambiguation guard for components
                cs_num = cs.standard_number
                c_low = comp_query.lower()
                if "1239" in cs_num:
                    if "Part 2" in cs_num and any(k in c_low for k in ["tube", "tubes", "pipe", "pipes"]) and not any(k in c_low for k in ["fitting", "fittings", "elbow", "tee", "socket", "union"]):
                        continue
                    if "Part 1" in cs_num and any(k in c_low for k in ["fitting", "fittings", "elbow", "tee", "socket", "union"]):
                        continue
                if "7098" in cs_num:
                    if "Part 2" in cs_num and any(k in c_low for k in ["lt", "low tension", "low voltage", "1.1 kv", "1100 v"]):
                        continue
                    if "Part 1" in cs_num and any(k in c_low for k in ["ht", "mv", "hv", "high tension", "11 kv", "33 kv", "medium voltage"]):
                        continue
                if "1489" in cs_num:
                    if "Part 2" in cs_num and any(k in c_low for k in ["fly ash", "flyash"]):
                        continue
                    if "Part 1" in cs_num and any(k in c_low for k in ["calcined clay", "clay"]):
                        continue

                app_check = self.applicability_gate.evaluate_candidate(
                    candidate=cs,
                    requirement_text=comp_query,
                    components=[comp] if isinstance(comp, RequirementComponent) else [],
                    parsed_ai=None,
                    is_explicitly_cited=False
                )
                if app_check.applicable and cs.relevance_score >= 0.40:
                    matched_c = (cs, app_check)
                    break

            if matched_c:
                c_std, c_app = matched_c
                # Prevent duplicate recommendation for the same standard across overlapping components
                if any(cb.get("candidate_standard") == c_std.standard_number for cb in component_bundles):
                    continue
                sub_dep = self.dependency_engine.analyze_dependencies(
                    requirement=comp_text,
                    primary_standard=c_std.standard_number,
                    primary_title=c_std.full_title
                )
                c_year_match = re.search(r':\s*(\d{4})\b', c_std.standard_number)
                c_year = int(c_year_match.group(1)) if c_year_match else getattr(c_std, "year", None)
                c_clause_ev = self.clause_retriever.retrieve_clause_evidence(
                    standard_number=c_std.standard_number,
                    edition_year=c_year,
                    query_text=comp_text,
                    requirement_text=comp_text
                )
                is_cat = getattr(c_std, "_is_catalogue_only", False) or getattr(c_app, "decision", "") == "PENDING_TECHNICAL_EVALUATION"
                c_human_review = True if is_cat else False
                c_app_decision = "PENDING_TECHNICAL_EVALUATION" if is_cat else "APPLICABLE"
                c_confidence = "Low" if is_cat else ("High" if c_std.relevance_score >= 0.75 else "Medium")
                component_bundles.append({
                    "component_id": comp_id,
                    "component_text": comp_text,
                    "component_domain": comp_domain,
                    "component_role": comp_role,
                    "candidate_standard": c_std.standard_number,
                    "title": c_std.full_title,
                    "confidence": c_confidence,
                    "relevance_score": round(c_std.relevance_score, 3),
                    "evidence": c_std.scope_summary or c_std.relevance_reason or f"Standard applies to technical component '{comp_text}'.",
                    "applicability_decision": c_app_decision,
                    "dependencies": sub_dep.to_dict(),
                    "human_review_required": c_human_review,
                    "why_matched": f"Component '{comp_text}' matches standard {c_std.standard_number} ({c_std.full_title}).",
                    "clause_evidence": c_clause_ev.to_dict() if hasattr(c_clause_ev, "to_dict") else c_clause_ev
                })
            else:
                component_bundles.append({
                    "component_id": comp_id,
                    "component_text": comp_text,
                    "component_domain": comp_domain,
                    "component_role": comp_role,
                    "candidate_standard": None,
                    "title": "Review Required",
                    "confidence": "Low",
                    "relevance_score": 0.0,
                    "evidence": f"No unambiguous Indian Standard confirmed for component '{comp_text}'.",
                    "applicability_decision": "REVIEW_REQUIRED",
                    "dependencies": {},
                    "human_review_required": True,
                    "why_matched": f"Component '{comp_text}' requires engineering review.",
                    "clause_evidence": None
                })

        return component_bundles


    def recommend_for_requirement(self, req: Any, tender_cited_standards: Optional[List[str]] = None) -> RequirementRecommendationResult:
        """Processes an individual Requirement through the end-to-end recommendation workflow."""
        if isinstance(req, str):
            req = extract_from_text(req)
        text = req.requirement_text
        req_id = req.requirement_id
        cat = req.category

        # Step -1: Multilingual Preprocessing & Normalization
        norm_result = self.multilingual_normalizer.normalize(text)
        working_text = norm_result.canonical_text if norm_result.is_multilingual and norm_result.canonical_text else text
        multilingual_payload = norm_result.to_dict()

        # Augment explicit standards if multilingual extraction found explicit IS numbers not caught by initial regex
        for ent in norm_result.extracted_entities:
            if re.match(r"^(?:IS|SP)\s*(?:/|\s*)?\d+", ent, re.IGNORECASE) and ent not in req.explicit_standards:
                req.explicit_standards.append(ent)

        # Step 0: AI Requirement Understanding (converts natural text to structured facets)
        parsed_ai = self.ai_parser.parse(working_text)

        # Decompose requirement if components not already present
        if not getattr(req, "components", None):
            decomp = self.decomposer.decompose(working_text)
            req.components = decomp.components
            req.decomposition_confidence = decomp.decomposition_confidence

        # Enrich components with non-duplicate AI understanding facets if active
        if not parsed_ai.is_fallback:
            ai_components = parsed_ai.to_components()
            existing_texts = {c.text.lower() for c in req.components}
            for ac in ai_components:
                ac_lower = ac.text.lower()
                if not any(ac_lower == et or ac_lower in et or et in ac_lower for et in existing_texts):
                    req.components.append(ac)
                    existing_texts.add(ac_lower)

        # Analyze specification completeness across engineering domain
        completeness_report = self.completeness_analyzer.analyze(working_text, req.components)


        # Step 1: Detect explicit standards mentioned and validate status
        explicit_stds = req.explicit_standards or []
        superseded_explicit_warnings = []
        nonexistent_citation_warnings = []
        explicit_search_results = []

        for exp in explicit_stds:
            val_res = validate_standard_status(exp, self.db)
            if not val_res.is_known:
                nonexistent_citation_warnings.append(
                    f"NONEXISTENT_CITATION: Cited standard '{exp}' was not found in the BIS standards catalogue."
                )
                continue
            
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                # 1. Inject the explicit citation itself
                exp_base = re.sub(r'\s*:\s*\d{4}\b', '', exp).strip()
                parsed_exp = StandardIdentifierNormalizer.parse(exp)
                norm_exp_base = parsed_exp.base_standard_number if parsed_exp.is_valid else exp_base
                norm_exp_id = parsed_exp.canonical_id if parsed_exp.is_valid else exp
                cursor.execute(
                    "SELECT * FROM standards WHERE standard_number = ? OR standard_number = ? OR standard_number = ? OR standard_id = ? OR standard_id LIKE ?",
                    (exp, exp_base, norm_exp_base, exp, f"{norm_exp_id}%")
                )
                rows = cursor.fetchall()
                row = None

                if rows:
                    if parsed_exp.part is not None:
                        matching_rows = [
                            r for r in rows
                            if StandardIdentifierNormalizer.parse(dict(r)["standard_number"]).part == parsed_exp.part
                        ]
                        row = matching_rows[0] if matching_rows else rows[0]
                    elif len(rows) > 1:
                        # Multi-part standard cited without explicit part number
                        tw = working_text.lower()
                        is_bare_ambiguous = False

                        if "1239" in norm_exp_id:
                            fittings_kws = ["fitting", "fittings", "tubulars", "elbow", "tee", "socket", "union", "coupling", "nipple"]
                            tubes_kws = ["tube", "tubes", "pipe", "pipes", "tubular"]
                            has_fitting = any(re.search(rf"\b{k}\b", tw) for k in fittings_kws)
                            has_tube = any(re.search(rf"\b{k}\b", tw) for k in tubes_kws)
                            if has_fitting:
                                p2 = [r for r in rows if StandardIdentifierNormalizer.parse(dict(r)["standard_number"]).part == 2]
                                row = p2[0] if p2 else rows[0]
                            elif has_tube:
                                p1 = [r for r in rows if StandardIdentifierNormalizer.parse(dict(r)["standard_number"]).part == 1]
                                row = p1[0] if p1 else rows[0]
                            else:
                                is_bare_ambiguous = True
                                row = rows[0]
                        elif "7098" in norm_exp_id:
                            ht_kws = ["11 kv", "33 kv", "3.3 kv", "6.6 kv", "ht", "medium voltage", "high tension"]
                            lt_kws = ["1.1 kv", "1100 v", "lt", "low voltage", "low tension"]
                            has_ht = any(k in tw for k in ht_kws)
                            has_lt = any(k in tw for k in lt_kws)
                            if has_ht:
                                p2 = [r for r in rows if StandardIdentifierNormalizer.parse(dict(r)["standard_number"]).part == 2]
                                row = p2[0] if p2 else rows[0]
                            elif has_lt:
                                p1 = [r for r in rows if StandardIdentifierNormalizer.parse(dict(r)["standard_number"]).part == 1]
                                row = p1[0] if p1 else rows[0]
                            else:
                                is_bare_ambiguous = True
                                row = rows[0]
                        elif "1489" in norm_exp_id:
                            clay_kws = ["calcined clay", "calcined", "clay"]
                            has_clay = any(k in tw for k in clay_kws)
                            if has_clay:
                                p2 = [r for r in rows if StandardIdentifierNormalizer.parse(dict(r)["standard_number"]).part == 2]
                                row = p2[0] if p2 else rows[0]
                            else:
                                p1 = [r for r in rows if StandardIdentifierNormalizer.parse(dict(r)["standard_number"]).part == 1]
                                row = p1[0] if p1 else rows[0]
                        else:
                            row = rows[0]

                        if is_bare_ambiguous:
                            part_options = [dict(r).get("standard_number") for r in rows]
                            superseded_explicit_warnings.append(
                                f"AMBIGUOUS_MULTI_PART_CITATION: Cited standard '{exp}' is a multi-part specification ({', '.join(part_options)}). "
                                "Tender specification lacks discriminating product parameters to determine the exact part. Human review required."
                            )
                    else:
                        row = rows[0]

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
                elif val_res.is_catalogue_only and val_res.catalogue_record:
                    # Construct validated national catalogue candidate
                    cat_rec = val_res.catalogue_record
                    exact_res = SearchResult(
                        standard_id=cat_rec["canonical_id"],
                        standard_number=cat_rec.get("standard_number") or cat_rec["canonical_id"],
                        year=cat_rec.get("year"),
                        full_title=cat_rec.get("title") or "Indian Standard",
                        status=val_res.status,
                        version_role="CURRENT_ACTIVE" if val_res.is_active else ("WITHDRAWN" if "withdrawn" in val_res.status.lower() else "REPLACED_OR_SUPERSEDED"),
                        relevance_score=1.0,
                        relevance_reason=f"Explicitly cited in tender: {exp} (Validated in National BIS Catalogue)",
                        scope_summary="[National BIS Catalogue entry: scope text unindexed in local semantic corpus]",
                        referenced_standards=[],
                        explicit_relationships=[],
                        verification_status="CATALOGUE_VERIFIED",
                        source_provenance=cat_rec.get("source") or "National BIS Catalogue",
                        deterministic_score=1.0,
                        final_score=1.0
                    )
                    setattr(exact_res, "_is_catalogue_only", True)
                    setattr(exact_res, "_catalogue_record", cat_rec)
                    explicit_search_results.append(exact_res)

                # 2. Inject the authoritative successor if superseded or outdated edition
                if not val_res.is_active:
                    if val_res.warning_message and val_res.warning_message not in superseded_explicit_warnings:
                        superseded_explicit_warnings.append(val_res.warning_message)
                    if val_res.successor_standard:
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

                for aw in getattr(val_res, "ambiguity_warnings", []):
                    if aw not in superseded_explicit_warnings:
                        superseded_explicit_warnings.append(aw)

        # Step 2: Multi-modal Search over BIS Standards with Decomposed Components
        # Primary search using full requirement text and decomposed components
        search_results = self.search_engine.search(
            working_text, top_k=8, components=req.components, mode=self.retrieval_mode
        )

        # Secondary search if primary yields low results or for multi-item requirements
        if len(search_results) < 2:
            # Extract key noun chunks from components or text
            sub_queries = [c.text for c in req.components if c.component_type in ["material", "product", "equipment", "control", "electrical"]]
            if not sub_queries:
                sub_queries = self._extract_subqueries(working_text)
            for sq in sub_queries:
                extra_hits = self.search_engine.search(
                    sq, top_k=3, components=req.components, mode=self.retrieval_mode
                )
                for eh in extra_hits:
                    if not any(r.standard_id == eh.standard_id for r in search_results):
                        search_results.append(eh)

        # Merge explicit citations into search_results so they are evaluated by the Critic
        from src.ambiguity import ConflictRegistry, ConflictRule
        for esr in explicit_search_results:
            citation_conflict = ConflictRegistry.check_conflict(working_text, req.components, [esr])
            # Pre-Citation Operational Envelope Gate (Milestone 8, Task 3):
            # Prior to granting deterministic citation bonus (1.0), evaluate the candidate against
            # the Applicability Gate's operational envelope and domain checks.
            if not citation_conflict:
                app_eval = self.applicability_gate.evaluate_candidate(
                    candidate=esr,
                    requirement_text=working_text,
                    components=req.components,
                    parsed_ai=parsed_ai,
                    is_explicitly_cited=True
                )
                if (not app_eval.applicable) or bool(app_eval.conflict_flags):
                    rule_id = "ENVELOPE-VIOLATION"
                    reason_desc = app_eval.human_reason or ("; ".join(app_eval.rejection_reasons) if app_eval.rejection_reasons else "Operational envelope violation")
                    citation_conflict = (ConflictRule(
                        rule_id=rule_id,
                        name="Operational Envelope Violation",
                        technical_rationale=reason_desc,
                        authoritative_evidence=f"Standard {esr.standard_number} Scope"
                    ), reason_desc)

            existing = next((r for r in search_results if r.standard_number == esr.standard_number), None)
            if citation_conflict:
                rule, reason = citation_conflict
                esr.relevance_score = 0.10
                esr.deterministic_score = 0.0
                esr.final_score = 0.10
                esr.relevance_reason = f"CONFLICT DETECTED [{rule.rule_id}]: {reason}"
                setattr(esr, "_conflict_detected", reason)
                if not existing:
                    search_results.append(esr)
                else:
                    existing.relevance_score = 0.10
                    existing.deterministic_score = 0.0
                    existing.final_score = 0.10
                    existing.relevance_reason = esr.relevance_reason
                    setattr(existing, "_conflict_detected", reason)
            else:
                if not existing:
                    search_results.insert(0, esr)
                else:
                    existing.deterministic_score = 1.0
                    existing.final_score = max(existing.final_score, 1.0)
                    existing.relevance_score = 1.0
                    existing.relevance_reason = esr.relevance_reason + " | " + existing.relevance_reason
                    if hasattr(esr, "_explicit_successor_warning"):
                        setattr(existing, "_explicit_successor_warning", getattr(esr, "_explicit_successor_warning"))
                    # Promote explicit citation match to head of search_results
                    search_results.remove(existing)
                    search_results.insert(0, existing)

        # Step 3: Check Ambiguity Heuristics
        ambiguity_flag = False
        ambiguity_reason = ""
        for pattern_kw, pattern_full, reason_desc in AMBIGUITY_PATTERNS:
            if re.search(pattern_kw, working_text, re.IGNORECASE) and re.search(pattern_full, working_text, re.IGNORECASE):
                ambiguity_flag = True
                ambiguity_reason = reason_desc
                break

        # Step 3.5: NEW APPLICABILITY GATE (Milestone 9)
        # Evaluate each candidate independently through the Applicability Gate
        applicable_candidates: List[SearchResult] = []
        rejected_candidates: List[Tuple[SearchResult, ApplicabilityResult]] = []
        candidate_applicability_map: Dict[str, ApplicabilityResult] = {}

        for cand in search_results:
            has_conflict = getattr(cand, "_conflict_detected", None) is not None
            is_explicit = any(exp in cand.relevance_reason or exp in cand.standard_number for exp in explicit_stds) and not has_conflict
            app_res = self.applicability_gate.evaluate_candidate(
                candidate=cand,
                requirement_text=working_text,
                components=req.components,
                parsed_ai=parsed_ai,
                is_explicitly_cited=is_explicit
            )
            candidate_applicability_map[cand.standard_number] = app_res
            if app_res.applicable:
                applicable_candidates.append(cand)
            else:
                rejected_candidates.append((cand, app_res))

        # Task 4: Anti-Fallthrough for Nonexistent / Hallucinated Explicit Citations
        # If all cited standards in requirement are nonexistent in the catalogue, do not fall through
        # to spurious lexical hits (e.g. generic tokens like 'pipe').
        if nonexistent_citation_warnings and not explicit_search_results:
            for ac in applicable_candidates:
                fake_app = candidate_applicability_map.get(ac.standard_number)
                if fake_app:
                    rejected_candidates.append((ac, fake_app))
            applicable_candidates = []

        # Check if requirement seeks product procurement (cables, pipes, valves, switchgear, etc.)
        t_low = working_text.lower()
        is_pure_installation = any(re.search(rf'\b{w}\b', t_low) for w in ["connection", "laying", "erection", "commissioning", "jointing"]) and not any(re.search(rf'\b{w}\b', t_low) for w in ["supply", "procurement", "purchase", "procuring", "deliver"])
        prod_nouns = [
            "cable", "cables", "pipe", "pipes", "piping", "valve", "valves",
            "pump", "pumps", "motor", "motors", "switchgear", "controlgear", "panel", "panels",
            "transformer", "transformers", "cement", "tile", "tiles", "tube", "tubes",
            "wire", "wires", "conductor", "conductors", "flange", "flanges", "fitting", "fittings",
            "engine", "engines", "generator", "generators"
        ]
        is_prod_req = (not is_pure_installation) and any(re.search(rf'\b{w}\b', t_low) for w in prod_nouns)

        # Architectural Composite Component Prioritization:
        # In composite installations containing an ENERGY_TRANSFORMATION_COMPONENT (e.g. power/distribution transformer)
        # alongside subordinate distribution/protection components, prioritize candidates that fulfill the primary
        # energy transformation component role.
        has_et_component = any(
            getattr(c, "role", None) == "ENERGY_TRANSFORMATION_COMPONENT"
            for c in (req.components or [])
        )
        if has_et_component:
            def et_role_priority(c: SearchResult) -> Tuple[int, float]:
                cand_text = f"{c.full_title} {c.scope_summary or ''}".lower()
                is_et_std = any(k in cand_text for k in ["transformer", "transformers", "distribution transformer", "power conversion"])
                return (0 if is_et_std else 1, -c.relevance_score)
            applicable_candidates.sort(key=et_role_priority)
        elif is_prod_req and any(classify_standard_role(c.standard_number, c.full_title, c.scope_summary) == "PRIMARY_PRODUCT" for c in applicable_candidates):
            best_score = max(c.relevance_score for c in applicable_candidates) if applicable_candidates else 0.0
            def role_priority(c: SearchResult) -> Tuple[int, float]:
                role = classify_standard_role(c.standard_number, c.full_title, c.scope_summary)
                # Product preference only applies when candidate score is within 0.20 of the best score
                if (best_score - c.relevance_score) <= 0.20:
                    if role == "PRIMARY_PRODUCT":
                        r_order = 0
                    elif role in ["INSTALLATION", "CODE_OF_PRACTICE", "FACILITY_PREMISE"]:
                        r_order = 1
                    else:
                        r_order = 2
                else:
                    r_order = 3
                return (r_order, -c.relevance_score)
            applicable_candidates.sort(key=role_priority)


        # If ALL candidates fail the applicability gate: ABSTAIN cleanly
        if not applicable_candidates:
            why_not_reasons = []
            for cand, app_res in rejected_candidates[:3]:
                reasons_str = "; ".join(app_res.rejection_reasons) if app_res.rejection_reasons else "Insufficient domain applicability"
                why_not_reasons.append(f"Standard {cand.standard_number} ({cand.full_title}) rejected: {reasons_str}")

        # Step 4: Run Critic across Applicable Candidate Pool (if candidates exist)
        critic_outcome = None
        if applicable_candidates:
            critic_outcome = self.critic.evaluate_candidates(
                candidates=applicable_candidates,
                requirement_text=working_text,
                components=req.components,
                completeness=completeness_report
            )

        # Ambiguity Engine Evaluation across strict 8-stage decision pipeline
        ambiguity_report = self.ambiguity_engine.evaluate(
            requirement_text=working_text,
            decomposed_components=req.components,
            completeness_report=completeness_report,
            retrieved_candidates=search_results,
            applicable_candidates=applicable_candidates,
            rejected_candidates=rejected_candidates,
            candidate_applicability_map=candidate_applicability_map,
            critic_outcome=critic_outcome,
            explicit_standards=explicit_stds,
            unresolved_components=None
        )

        # Phase 9: Multi-component bundles & External Authority Signals
        component_recs = self._evaluate_component_recommendations(
            req_id=req_id,
            components=req.components or [],
            category=cat
        )
        external_signals = self.external_authority_registry.match_signals(working_text)
        external_regs = [s.to_dict() for s in external_signals]

        # Clean Abstention for INCOMPLETE, AMBIGUOUS, CONFLICTING, NO_RELIABLE_MATCH
        if ambiguity_report.ambiguity_state in [
            AmbiguityState.INCOMPLETE,
            AmbiguityState.AMBIGUOUS,
            AmbiguityState.CONFLICTING,
            AmbiguityState.NO_RELIABLE_MATCH
        ]:
            primary_app_res = rejected_candidates[0][1].to_dict() if rejected_candidates else None

            if ambiguity_report.ambiguity_state == AmbiguityState.NO_RELIABLE_MATCH:
                why_not_reasons = []
                for cand, app_res in rejected_candidates[:4]:
                    r_code = app_res.reason_code.value if hasattr(app_res.reason_code, 'value') else str(app_res.reason_code)
                    r_msg = app_res.human_reason or ("; ".join(app_res.rejection_reasons) if app_res.rejection_reasons else "Insufficient domain applicability")
                    why_not_reasons.append(f"[{r_code}] Standard {cand.standard_number} ({cand.full_title}) rejected: {r_msg}")
                if nonexistent_citation_warnings:
                    for ncw in reversed(nonexistent_citation_warnings):
                        why_not_reasons.insert(0, ncw)
                    user_facing_explanation = f"{nonexistent_citation_warnings[0]} Human review required."
                    title = "Nonexistent Standard Citation Detected"
                    critic_decision = "NO_RELIABLE_MATCH"
                    critic_reasons = list(nonexistent_citation_warnings)
                    why_it_matches = "Cited standard does not exist in the official BIS standards catalogue."
                elif superseded_explicit_warnings:
                    for sew in reversed(superseded_explicit_warnings):
                        why_not_reasons.insert(0, sew)
                    user_facing_explanation = f"{superseded_explicit_warnings[0]}"
                    title = "Inactive or Ambiguous Citation Detected"
                    critic_decision = "REVIEW_REQUIRED"
                    critic_reasons = list(superseded_explicit_warnings)
                    why_it_matches = "Tender cites an inactive, superseded, or ambiguous multi-part standard."
                else:
                    if not why_not_reasons:
                        why_not_reasons = ["No reliable candidate standards retrieved from catalogue."]
                    user_facing_explanation = (
                        "No reliable Indian Standard match found. "
                        "We could not establish a sufficiently supported Indian Standard for this requirement from the available catalogue. "
                        "Human review required."
                    )
                    title = "No Reliable Indian Standard Match Found"
                    critic_decision = "NO_RELIABLE_MATCH"
                    critic_reasons = ["All candidates rejected by Applicability Gate." if rejected_candidates else "Zero candidates retrieved from catalogue."]
                    why_it_matches = "No reliable Indian Standard match found in the available catalogue."
            elif ambiguity_report.ambiguity_state == AmbiguityState.INCOMPLETE:
                why_not_reasons = [
                    f"Specification omits critical discriminating parameters: {', '.join(ambiguity_report.missing_information)}."
                ]
                user_facing_explanation = ambiguity_report.ambiguity_reason
                title = "Requirement Specification Incomplete - Clarification Required"
                critic_decision = "REVIEW_REQUIRED"
                critic_reasons = [ambiguity_report.ambiguity_reason]
                why_it_matches = "Tender specification omits critical discriminating parameters required to identify an applicable Indian Standard."
            elif ambiguity_report.ambiguity_state == AmbiguityState.AMBIGUOUS:
                why_not_reasons = [
                    f"Candidate standard {c.get('standard_number')} competes within separation threshold: {c.get('distinguishing_parameter_needed') or 'distinguishing specification missing'}."
                    for c in ambiguity_report.competing_interpretations
                ]
                user_facing_explanation = ambiguity_report.ambiguity_reason
                title = "Ambiguous Requirement - Multiple Competing Standards"
                critic_decision = "REVIEW_REQUIRED"
                critic_reasons = [ambiguity_report.ambiguity_reason]
                why_it_matches = "Multiple candidate Indian Standards are applicable with close relevance scores; tender lacks distinguishing parameters."
            elif ambiguity_report.ambiguity_state == AmbiguityState.CONFLICTING:
                why_not_reasons = [
                    f"Conflict rule {ambiguity_report.conflict_rule_id} triggered: {ambiguity_report.ambiguity_reason}"
                ]
                user_facing_explanation = ambiguity_report.ambiguity_reason
                title = "Conflicting Specification Detected - Clarification Required"
                critic_decision = "REVIEW_REQUIRED"
                critic_reasons = [ambiguity_report.ambiguity_reason]
                why_it_matches = "Conflicting technical parameters or standard scopes detected in specification."

            abstain_struct_ev = self.evidence_builder.build_structured_evidence(
                standard_number=None,
                requirement_text=working_text,
                title=title,
                candidate_search_result=None,
                applicability_result=None,
                ambiguity_report=ambiguity_report,
                explicit_citation=False,
                missing_information=ambiguity_report.missing_information if ambiguity_report else [],
                human_review_required=True,
                decision_reason=user_facing_explanation
            )

            return RequirementRecommendationResult(
                requirement_id=req_id,
                requirement_text=text,
                category=cat,
                explicit_standards_found=explicit_stds,
                candidate_standard=None,
                title=title,
                status="Unknown",
                version_role="UNKNOWN",
                relevance_score=0.0,
                confidence="Low",
                evidence="We could not establish a sufficiently supported Indian Standard for this requirement from the available catalogue.",
                provenance="UNKNOWN",
                human_review_required=True,
                reason=user_facing_explanation,
                recommendations=[],
                alternatives=[c.get("standard_number") for c in ambiguity_report.competing_interpretations],
                decomposed_components=[c.to_dict() if hasattr(c, "to_dict") else c for c in getattr(req, "components", [])],
                critic_result={
                    "decision": critic_decision,
                    "reasons": critic_reasons,
                    "risk_level": "HIGH",
                    "risk_reasons": critic_reasons
                },
                why_this=[],
                why_not=why_not_reasons,
                risk_level="HIGH",
                risk_reasons=critic_reasons,
                specification_completeness=completeness_report.to_dict() if completeness_report else None,
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
                why_it_matches=why_it_matches,
                regulatory=self.regulatory_engine.evaluate_to_dict(None, working_text),
                ambiguity_state=ambiguity_report.ambiguity_state.value,
                ambiguity_reason=ambiguity_report.ambiguity_reason,
                retrieval_status=ambiguity_report.retrieval_status,
                applicability_status=ambiguity_report.applicability_status,
                evidence_status=ambiguity_report.evidence_status,
                missing_information=ambiguity_report.missing_information,
                competing_interpretations=ambiguity_report.competing_interpretations,
                suggested_clarification_question=ambiguity_report.suggested_clarification_question,
                unresolved_components=ambiguity_report.unresolved_components,
                multilingual=multilingual_payload,
                structured_evidence=abstain_struct_ev.to_dict(),
                component_recommendations=component_recs,
                external_regulations=external_regs,
                lifecycle_warnings=[],
                amendment_metadata=None,
                trace_record=self.evidence_validator.build_trace_record(
                    requirement_id=req_id,
                    requirement_text=text,
                    recommendation=type("AbstainRec", (), {
                        "candidate_standard": None,
                        "title": "N/A",
                        "status": "UNKNOWN",
                        "evidence": "",
                        "structured_evidence": abstain_struct_ev.to_dict(),
                        "critic_result": {"decision": critic_decision},
                        "applicability": primary_app_res,
                        "ambiguity_state": ambiguity_report.ambiguity_state.value,
                        "competing_interpretations": ambiguity_report.competing_interpretations,
                        "human_review_required": True,
                        "relevance_score": 0.0,
                        "provenance": "NONE",
                        "clause_evidence": None
                    })(),
                    rank_position=1,
                    clause_evidence=None
                ).to_dict(),
                component_trace_records=[
                    self.evidence_validator.build_trace_record(
                        requirement_id=req_id,
                        requirement_text=text,
                        recommendation=type("CompRec", (), {
                            "candidate_standard": c.get("candidate_standard"),
                            "title": c.get("title", ""),
                            "status": c.get("lifecycle_status", "UNKNOWN"),
                            "evidence": c.get("evidence", ""),
                            "structured_evidence": c.get("structured_evidence"),
                            "critic_result": {"decision": "REVIEW_REQUIRED" if c.get("human_review_required") else "RECOMMEND"},
                            "applicability": {"decision": c.get("applicability_decision", "UNKNOWN")},
                            "ambiguity_state": "CLEAR",
                            "competing_interpretations": [],
                            "human_review_required": c.get("human_review_required", False),
                            "relevance_score": c.get("relevance_score", 0.0),
                            "provenance": c.get("provenance", "UNKNOWN"),
                            "clause_evidence": c.get("clause_evidence")
                        })(),
                        sub_requirement_id=c.get("component_id"),
                        sub_requirement_text=c.get("component_text"),
                        rank_position=idx + 1,
                        clause_evidence=c.get("clause_evidence")
                    ).to_dict()
                    for idx, c in enumerate(component_recs) if isinstance(c, dict)
                ],
                clause_evidence=None,
                package_id=getattr(req, "package_id", "PKG-01"),
                package_name=getattr(req, "package_name", "Main Scope"),
                domain=getattr(req, "domain", None) or detect_technical_domain(working_text),
                verification_tier="SAFE_ABSTENTION",
                passage_id=None,
                clause_number=None,
                edition_year=None
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

            rec_role = classify_standard_role(sr.standard_number, sr.full_title, sr.scope_summary)
            cand_app_obj = candidate_applicability_map.get(sr.standard_number)
            cand_human_review = (not val_info.is_active or conf == "Low" or sr.relevance_score < 0.35)
            cand_decision_reason = warning or ("Low confidence retrieval match." if conf == "Low" else "Applicable standard candidate.")
            cand_struct_ev = self.evidence_builder.build_structured_evidence(
                standard_number=rec_std_num,
                requirement_text=working_text,
                title=sr.full_title,
                candidate_search_result=sr,
                applicability_result=cand_app_obj,
                ambiguity_report=ambiguity_report,
                explicit_citation=any(e in sr.standard_number for e in explicit_stds),
                missing_information=ambiguity_report.missing_information if ambiguity_report else [],
                human_review_required=cand_human_review,
                decision_reason=cand_decision_reason
            )
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
                applicability=app_dict,
                standard_role=rec_role,
                structured_evidence=cand_struct_ev.to_dict()
            ))

        top_rec = recommendations[0]
        alternatives = [r.standard_number for r in recommendations[1:4]]

        # Human Review and Risk Decision Logic
        any_conflict_detected = any(getattr(sr, "_conflict_detected", None) for sr in search_results)
        is_ms_column_rebar = (
            ("432" in top_rec.standard_number) and
            any(w in working_text.lower() for w in ["column", "columns", "beam", "beams", "rcc", "seismic", "frame", "residential"])
        )
        foreign_matches = re.findall(r'\b(?:DIN|ASTM|ASME|BS\s*EN|JIS)\s+[A-Za-z0-9\-]+', working_text, re.IGNORECASE)
        has_unmapped_foreign = bool(foreign_matches and not explicit_stds)
        has_adversarial = getattr(req, "has_adversarial_directive", False)

        if superseded_explicit_warnings:
            human_review_required = True
            decision_reason = superseded_explicit_warnings[0]
            risk_level = "CRITICAL" if any("CRITICAL" in w for w in superseded_explicit_warnings) else "HIGH"
            risk_reasons = list(superseded_explicit_warnings)
            why_this = ["Recommended authoritative active successor standard recorded in BIS database."]
            why_not = ["Original cited standard is superseded, obsolete, or an older revision requiring technical verification."]
            conf = "High"
        elif any_conflict_detected:
            human_review_required = True
            conflict_reasons = [getattr(sr, "_conflict_detected") for sr in search_results if getattr(sr, "_conflict_detected", None)]
            decision_reason = f"Conflict detected with tender requirement: {conflict_reasons[0]}"
            risk_level = "HIGH"
            risk_reasons = conflict_reasons
            why_this = critic_outcome.why_this if critic_outcome else []
            why_not = conflict_reasons
            conf = "Low"
        elif is_ms_column_rebar:
            human_review_required = True
            decision_reason = "Mild steel reinforcement bars (IS 432) specified for building columns/frames requires structural engineering verification against modern deformed bar standards (IS 1786)."
            risk_level = "HIGH"
            risk_reasons = ["Engineering verification required: mild steel plain round bars (IS 432) vs high-strength deformed rebar (IS 1786) for structural columns."]
            why_this = ["Standard covers mild steel reinforcement bars."]
            why_not = ["Structural column design requires verification of steel grade and rebar deformation per IS 456 / IS 1786."]
            conf = "Medium"
        elif has_unmapped_foreign:
            human_review_required = True
            decision_reason = f"Foreign specification ({', '.join(foreign_matches)}) cited without Indian Standard equivalent. Engineering review required for cross-standard substitution."
            risk_level = "HIGH"
            risk_reasons = [f"Unmapped foreign specification: {', '.join(foreign_matches)}"]
            why_this = critic_outcome.why_this if critic_outcome else []
            why_not = [f"Tender specifies foreign specification {', '.join(foreign_matches)}; cross-standard substitution requires human verification."]
            conf = "Low"
        elif has_adversarial:
            human_review_required = True
            decision_reason = "Adversarial prompt injection directive detected and neutralized at ingestion boundary. Engineering review required."
            risk_level = "HIGH"
            risk_reasons = ["Ingestion trust boundary: prompt injection attempt stripped; requires manual verification."]
            why_this = critic_outcome.why_this if critic_outcome else []
            why_not = ["Input contained instruction overrides or adversarial prompt directives."]
            conf = "Medium"
        elif ambiguity_report.human_review_required or ambiguity_flag:
            human_review_required = True
            decision_reason = ambiguity_report.ambiguity_reason or ambiguity_reason
            risk_level = "HIGH"
            risk_reasons = critic_outcome.risk_reasons or [decision_reason] if critic_outcome else [decision_reason]
            why_this = critic_outcome.why_this if critic_outcome else []
            why_not = critic_outcome.why_not if critic_outcome else []
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
        # Ensure any supporting installation / code of practice recommendations are exposed in dependencies
        for r in recommendations:
            if r.standard_role in ["INSTALLATION", "CODE_OF_PRACTICE"] and r.standard_number != top_rec.standard_number:
                if not any(d.get("standard_number") == r.standard_number for d in dep_dicts):
                    dep_dicts.append({
                        "standard_number": r.standard_number,
                        "title": r.title,
                        "relationship_type": "INSTALLATION_STANDARD" if r.standard_role == "INSTALLATION" else "CODE_OF_PRACTICE",
                        "dependency_status": "INSTALLATION_DEPENDENCY",
                        "functional_category": "installation",
                        "evidence": r.evidence or r.title,
                        "is_satisfied": False,
                        "context_applicability": "APPLICABLE",
                        "provenance": r.provenance
                    })
        cov_dict = cov_map.to_dict()
        all_gap_dicts = [g.to_dict() for g in cov_map.all_gaps]
        ver_missing_dicts = [g.to_dict() for g in cov_map.standard_gaps if g.gap_severity == "VERIFIED_MISSING"]
        pot_missing_dicts = [g.to_dict() for g in cov_map.standard_gaps if g.gap_severity == "POTENTIALLY_MISSING"]
        rel_review_dicts = [g.to_dict() for g in cov_map.standard_gaps if g.gap_severity == "RELATED_FOR_REVIEW"]

        # Strict Evidence Consistency Rule Check:
        primary_crit = critic_outcome.primary_critique if critic_outcome else None
        crit_ev = primary_crit.evidence if primary_crit else None
        evidence_std = getattr(crit_ev, "standard_number", None) or top_rec.standard_number

        is_ev_consistent = are_standards_equivalent(top_rec.standard_number, evidence_std)
        if not is_ev_consistent:
            why_it_matches = "Match identified from the requirement context; supporting evidence needs review."
            human_review_required = True
            decision_reason = "Evidence consistency validation failed: candidate and evidence standards mismatch."
            evidence_status_val = "GROUNDING_FAILED"
            ambiguity_state_val = "REVIEW_REQUIRED"
            evidence_std = top_rec.standard_number  # canonical identity for non-null recommendation!
        else:
            # Canonical alignment: ensure evidence_standard strictly matches candidate_standard
            evidence_std = top_rec.standard_number
            evidence_status_val = ambiguity_report.evidence_status
            if ambiguity_report.ambiguity_state == AmbiguityState.CLEAR and not human_review_required:
                ambiguity_state_val = "CLEAR"
            else:
                ambiguity_state_val = "REVIEW_REQUIRED"

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

        # Re-evaluate with any auxiliary/unresolved missing gaps or nonexistent citations
        unresolved_missing = [(g.title or g.description or g.standard_number or "unspecified") for g in cov_map.standard_gaps if g.gap_severity == "VERIFIED_MISSING"]
        if unresolved_missing or norm_result.human_review_required or (norm_result.is_multilingual and norm_result.normalization_confidence < 0.60) or nonexistent_citation_warnings or any_conflict_detected or is_ms_column_rebar:
            human_review_required = True
            ambiguity_state_val = "REVIEW_REQUIRED"
            for ncw in nonexistent_citation_warnings:
                risk_reasons.append(ncw)
                why_not.append(ncw)
            if nonexistent_citation_warnings:
                conf = "Medium"
            if any_conflict_detected:
                conf = "Low"

        if dep_report.lifecycle_warnings:
            for lw in dep_report.lifecycle_warnings:
                msg = f"Lifecycle warning for dependency {lw.get('standard_number')}: {lw.get('reason')} (Active successor: {lw.get('active_successor')})"
                if msg not in risk_reasons:
                    risk_reasons.append(msg)

        # AUDIT-01: Parent-level rollup of component review requirements
        review_required_comps = []
        for c in (component_recs or []):
            if not isinstance(c, dict):
                continue
            needs_review = c.get("human_review_required")
            app_dec = c.get("applicability_decision")
            cand_std = c.get("candidate_standard")
            if needs_review is True or app_dec in ("REVIEW_REQUIRED", "REJECT", "INSUFFICIENT_EVIDENCE", "PENDING_TECHNICAL_EVALUATION") or (cand_std is None and needs_review is not False):
                review_required_comps.append(c)

        critic_dict = critic_outcome.primary_critique.to_dict() if critic_outcome and critic_outcome.primary_critique else {}

        if review_required_comps:
            human_review_required = True
            ambiguity_state_val = "REVIEW_REQUIRED"
            for c in review_required_comps:
                c_text = c.get("component_text") or c.get("component_id") or "subcomponent"
                c_reason = c.get("why_matched") or c.get("evidence") or "Requires engineering review"
                msg = f"Subcomponent '{c_text}' requires engineering review: {c_reason}"
                if msg not in risk_reasons:
                    risk_reasons.append(msg)
                if msg not in why_not:
                    why_not.append(msg)

            if not superseded_explicit_warnings and not any_conflict_detected and not is_ms_column_rebar:
                decision_reason = f"Primary standard {top_rec.standard_number} identified, but composite subcomponent(s) require engineering review."

            if critic_dict.get("decision") == "RECOMMEND":
                critic_dict["decision"] = "RECOMMEND_WITH_REVIEW"
                reasons_list = critic_dict.setdefault("reasons", [])
                for c in review_required_comps:
                    c_text = c.get("component_text") or c.get("component_id") or "subcomponent"
                    comp_msg = f"Subcomponent '{c_text}' requires engineering review."
                    if comp_msg not in reasons_list:
                        reasons_list.append(comp_msg)

        if human_review_required and critic_dict.get("decision") == "RECOMMEND":
            critic_dict["decision"] = "RECOMMEND_WITH_REVIEW"

        top_app = candidate_applicability_map.get(top_rec.standard_number) or (
            candidate_applicability_map.get(top_rec.standard_number.split(":")[0].strip()) if ":" in top_rec.standard_number else None
        )
        top_sr = next((sr for sr in applicable_candidates if sr.standard_number in top_rec.standard_number or top_rec.standard_number in sr.standard_number), None)
        top_struct_ev = self.evidence_builder.build_structured_evidence(
            standard_number=top_rec.standard_number,
            requirement_text=working_text,
            title=top_rec.title,
            candidate_search_result=top_sr,
            applicability_result=top_app,
            ambiguity_report=ambiguity_report,
            explicit_citation=any(e in top_rec.standard_number for e in explicit_stds),
            missing_information=ambiguity_report.missing_information if ambiguity_report else [],
            human_review_required=human_review_required,
            decision_reason=decision_reason
        )

        # Phase 19: Clause Evidence Retrieval for candidate standard
        std_year_match = re.search(r':\s*(\d{4})\b', top_rec.standard_number)
        std_year = int(std_year_match.group(1)) if std_year_match else getattr(top_rec, "year", None)
        if not std_year and hasattr(top_rec, "standard_year"):
            std_year = getattr(top_rec, "standard_year")
        if not std_year:
            std_entry = self.db.get_standard(top_rec.standard_number)
            if std_entry:
                std_year = std_entry.get("year")

        top_clause_ev = self.clause_retriever.retrieve_clause_evidence(
            standard_number=top_rec.standard_number,
            edition_year=std_year,
            query_text=working_text,
            requirement_text=working_text,
            is_compound=bool(component_recs and len(component_recs) > 1),
            compound_components=component_recs
        )
        top_rec.clause_evidence = top_clause_ev.to_dict()

        if top_clause_ev.requirement_evidence_support == "CONFLICTING":
            human_review_required = True
            top_rec.human_review_required = True
            decision_reason = f"Conflicting Evidence: Normative clause passage contradicts requirement parameters. {decision_reason}"

        # Phase 24 & 25: Handle catalogue-only candidates (both cited and NL-discovered)
        is_top_cat_only = getattr(top_sr, "_is_catalogue_only", False) or getattr(top_rec, "_is_catalogue_only", False)
        if is_top_cat_only:
            is_explicit = any(e in top_rec.standard_number for e in explicit_stds)
            human_review_required = True
            top_rec.human_review_required = True
            top_rec.provenance = "NATIONAL_CATALOGUE_CITATION" if is_explicit else "NATIONAL_CATALOGUE_DISCOVERY"
            source_desc = "validated citation" if is_explicit else "discovered standard"
            top_rec.evidence = (
                f"Standard {top_rec.standard_number} is an authentic {source_desc} from the National BIS Catalogue ({top_rec.title}), "
                f"but its technical clause text is not yet indexed in the local semantic corpus. "
                f"Applicability decision is PENDING_TECHNICAL_EVALUATION; manual engineering review required."
            )
            top_rec.applicability = {
                "decision": "PENDING_TECHNICAL_EVALUATION",
                "applicable": True,
                "rejection_reasons": [],
                "reason_code": "PENDING_TECHNICAL_EVALUATION",
                "human_reason": "Technical clauses unindexed in local corpus; pending manual engineering verification.",
            }
            conf = "Medium" if top_rec.status == "Active" else "Low"
            prefix = "Validated National Catalogue Citation" if is_explicit else "Discovered National Catalogue Standard"
            decision_reason = f"{prefix} (Scope Unindexed): {top_rec.evidence}"

        # Phase 27 & 30: Verification tier and exact passage metadata
        # CLAUSE_VERIFIED requires authentic local normative evidence matching canonical standard, active lifecycle, and no superseded warnings
        has_lifecycle_or_successor_conflict = bool(
            superseded_explicit_warnings
            or (explicit_stds and not any(exp.split(":")[0].strip() in top_rec.standard_number for exp in explicit_stds))
            or top_rec.status != "Active"
        )
        if (
            top_clause_ev 
            and getattr(top_clause_ev, "is_grounded", False) 
            and getattr(top_clause_ev, "passage_text", None)
            and not has_lifecycle_or_successor_conflict
            and not human_review_required
            and getattr(top_clause_ev, "requirement_evidence_support", "") == "FULLY_SUPPORTED"
        ):
            verification_tier = "CLAUSE_VERIFIED"
            p_sha = getattr(top_clause_ev, "passage_sha256", None)
            doc_id = getattr(top_clause_ev, "document_id", None)
            cl_id = getattr(top_clause_ev, "clause_identifier", None)
            passage_id = p_sha[:16] if p_sha else (f"{doc_id}_cl{cl_id}" if doc_id else "PS-VERIFIED")
            clause_number = cl_id
        elif (
            (is_top_cat_only or (top_rec.standard_number and top_rec.standard_number not in ["NONE", "INSUFFICIENT_INFORMATION", "UNKNOWN"]))
            and critic_dict.get("decision") not in ["INSUFFICIENT_EVIDENCE", "NO_RELIABLE_MATCH"]
            and top_rec.relevance_score >= 0.25
            and getattr(req, "domain", "") != "GENERAL_AND_ADMINISTRATIVE"
        ):
            verification_tier = "CATALOGUE_DISCOVERED"
            passage_id = None
            clause_number = None
        else:
            verification_tier = "SAFE_ABSTENTION"
            passage_id = None
            clause_number = None

        ed_year_str = str(std_year) if std_year else (
            str(top_clause_ev.edition_year) if (top_clause_ev and getattr(top_clause_ev, "edition_year", None)) else None
        )

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
            critic_result=critic_dict,
            why_this=why_this,
            why_not=why_not,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            specification_completeness=completeness_report.to_dict() if completeness_report else None,
            related_standards=related_standards_dicts,
            ai_understanding=parsed_ai.to_dict() if parsed_ai else None,
            ai_provider=parsed_ai.ai_provider if parsed_ai else None,
            ai_model=parsed_ai.ai_model if parsed_ai else None,
            is_ai_fallback=parsed_ai.is_fallback if parsed_ai else True,
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
            regulatory=self.regulatory_engine.evaluate_to_dict(top_rec.standard_number, working_text),
            ambiguity_state=ambiguity_state_val,
            ambiguity_reason=ambiguity_report.ambiguity_reason,
            retrieval_status=ambiguity_report.retrieval_status,
            applicability_status=ambiguity_report.applicability_status,
            evidence_status=evidence_status_val,
            missing_information=ambiguity_report.missing_information,
            competing_interpretations=ambiguity_report.competing_interpretations,
            suggested_clarification_question=ambiguity_report.suggested_clarification_question,
            unresolved_components=unresolved_missing,
            standard_role=top_rec.standard_role,
            multilingual=multilingual_payload,
            structured_evidence=top_struct_ev.to_dict(),
            component_recommendations=component_recs,
            external_regulations=external_regs,
            lifecycle_warnings=dep_report.lifecycle_warnings,
            amendment_metadata=dep_report.amendment_metadata,
            trace_record=self.evidence_validator.build_trace_record(
                requirement_id=req_id,
                requirement_text=text,
                recommendation=top_rec,
                rank_position=1,
                human_review_required=human_review_required,
                critic_decision=critic_dict.get("decision", "RECOMMEND"),
                final_decision="ASSISTED_REVIEW_REQUIRED" if human_review_required else "RECOMMEND",
                clause_evidence=top_clause_ev
            ).to_dict(),
            component_trace_records=[
                self.evidence_validator.build_trace_record(
                    requirement_id=req_id,
                    requirement_text=text,
                    recommendation=type("CompRec", (), {
                        "candidate_standard": c.get("candidate_standard"),
                        "title": c.get("title", ""),
                        "status": c.get("lifecycle_status", "UNKNOWN"),
                        "evidence": c.get("evidence", ""),
                        "structured_evidence": c.get("structured_evidence"),
                        "critic_result": {"decision": "REVIEW_REQUIRED" if c.get("human_review_required") else "RECOMMEND"},
                        "applicability": {"decision": c.get("applicability_decision", "UNKNOWN")},
                        "ambiguity_state": "CLEAR",
                        "competing_interpretations": [],
                        "human_review_required": c.get("human_review_required", False),
                        "relevance_score": c.get("relevance_score", 0.0),
                        "provenance": c.get("provenance", "UNKNOWN"),
                        "clause_evidence": c.get("clause_evidence")
                    })(),
                    sub_requirement_id=c.get("component_id"),
                    sub_requirement_text=c.get("component_text"),
                    rank_position=idx + 1,
                    clause_evidence=c.get("clause_evidence")
                ).to_dict()
                for idx, c in enumerate(component_recs) if isinstance(c, dict)
            ],
            clause_evidence=top_clause_ev.to_dict(),
            package_id=getattr(req, "package_id", "PKG-01"),
            package_name=getattr(req, "package_name", "Main Scope"),
            domain=getattr(req, "domain", None) or detect_technical_domain(working_text),
            verification_tier=verification_tier,
            passage_id=passage_id,
            clause_number=clause_number,
            edition_year=ed_year_str,
            traversed_cross_references=getattr(dep_report, "traversed_cross_references", []) or []
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
