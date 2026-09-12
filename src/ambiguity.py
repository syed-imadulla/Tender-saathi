"""
Module: src/ambiguity.py
Purpose: Deterministic Ambiguity Detection, Classification, and Clarification Engine for TenderSaathi.

Core Principles:
1. correct abstention > unsupported recommendation
2. retrieval != applicability
3. semantic similarity != evidence
4. graph relationship != applicability
5. multiple candidates != ambiguity
6. zero retrieval != proof of non-existence of an Indian Standard

Standardizes exactly 6 non-collapsed Ambiguity States:
- CLEAR
- AMBIGUOUS
- INCOMPLETE
- CONFLICTING
- NO_RELIABLE_MATCH
- REVIEW_REQUIRED

Enforces strict 8-stage decision pipeline with clean responsibility separation:
Stage 1: Conflict Detection
Stage 2: Catalogue Retrieval / Coverage
Stage 3: Specification Completeness
Stage 4: Candidate Applicability
Stage 5: Candidate Competition & Separation
Stage 6: Evidence Trust Validation
Stage 7: Lifecycle & Regulatory Review
Stage 8: Final Resolution (CLEAR vs REVIEW_REQUIRED)
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple
import re

from src.search import SearchResult
from src.decompose import RequirementComponent
from src.completeness import SpecificationCompletenessReport
from src.standards import classify_standard_role
from src.attributes import extract_standard_attributes, extract_tender_attributes, same_procurement_object, find_discriminators, discriminator_specified_in_tender


# ---------------------------------------------------------------------------
# 1. Ambiguity States
# ---------------------------------------------------------------------------

class AmbiguityState(str, Enum):
    CLEAR = "CLEAR"
    AMBIGUOUS = "AMBIGUOUS"
    INCOMPLETE = "INCOMPLETE"
    CONFLICTING = "CONFLICTING"
    NO_RELIABLE_MATCH = "NO_RELIABLE_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# 2. Data Models
# ---------------------------------------------------------------------------

@dataclass
class CompetingInterpretation:
    """A materially competing candidate standard when ambiguity exists."""
    standard_number: str
    title: str
    interpretation: str
    relevance_score: float
    distinguishing_parameter_needed: str
    why_plausible: Optional[str] = None
    evidence: Optional[str] = None
    provenance: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AmbiguityReport:
    """Structured output of the Ambiguity Engine for a requirement."""
    ambiguity_state: AmbiguityState
    ambiguity_reason: str
    retrieval_status: str = "CANDIDATES_FOUND"       # CANDIDATES_FOUND | ZERO_RESULTS
    applicability_status: str = "VIABLE_CANDIDATE"   # VIABLE_CANDIDATE | ALL_REJECTED
    evidence_status: str = "VALID"                   # VALID | INSUFFICIENT | GROUNDING_FAILED
    missing_information: List[str] = field(default_factory=list)
    competing_interpretations: List[Dict[str, Any]] = field(default_factory=list)
    affected_requirements: List[str] = field(default_factory=list)
    human_review_required: bool = False
    suggested_clarification_question: Optional[str] = None
    unresolved_components: List[str] = field(default_factory=list)
    separation_margin: Optional[float] = None
    conflict_rule_id: Optional[str] = None
    decision_confidence: str = "High"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ambiguity_state"] = self.ambiguity_state.value
        return d


# ---------------------------------------------------------------------------
# 3. Evidence-Backed Conflict Registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConflictRule:
    rule_id: str
    name: str
    technical_rationale: str
    authoritative_evidence: str
    evidence_clause: Optional[str] = None


class ConflictRegistry:
    """Registry of verified, authoritative engineering conflict rules.
    
    No rule is included unless supported by verifiable statutory or BIS code evidence.
    Speculative engineering logic is strictly excluded.
    """

    RULES: Dict[str, ConflictRule] = {
        "CONF-01-AGRI-IND-MV": ConflictRule(
            rule_id="CONF-01-AGRI-IND-MV",
            name="Agricultural Standard Applied to Industrial Medium/High-Voltage System",
            technical_rationale=(
                "Agricultural irrigation standards are technically restricted to low-pressure, "
                "rural/surface water delivery and are incompatible with industrial medium-voltage installations."
            ),
            authoritative_evidence=(
                "Central Electricity Authority (CEA) Technical Standards for Construction of Electrical Plants "
                "and Lines Regulations, paired with Scope Clause 1 of Indian Agricultural Equipment Standards."
            ),
            evidence_clause="Scope Clause 1 (Application Limits)"
        ),
        "CONF-02-PRESS-TEMP-INCOMPAT": ConflictRule(
            rule_id="CONF-02-PRESS-TEMP-INCOMPAT",
            name="Thermoplastic Piping Specified for Continuous Superheated Steam",
            technical_rationale=(
                "Chlorinated Polyvinyl Chloride (CPVC) piping has a standardized maximum service temperature "
                "limit of 93°C for pressurized water. Specifying it for continuous superheated steam (>=150°C) "
                "creates severe thermal decomposition and blowout risk."
            ),
            authoritative_evidence="IS 15778 : 2007 Clause 1.1 & Table 1 (Temperature & Pressure Limits).",
            evidence_clause="IS 15778 : 2007 Clause 1.1"
        ),
        "CONF-03-CONTRADICTORY-SPECS": ConflictRule(
            rule_id="CONF-03-CONTRADICTORY-SPECS",
            name="Mutually Exclusive Physical Specifications Within Item",
            technical_rationale=(
                "Requirement combines physical manufacturing attributes that are mutually exclusive in a single product "
                "(e.g., solid copper conductor aluminium wire, unarmoured strip armoured cable)."
            ),
            authoritative_evidence="IS 694 / IS 7098 manufacturing product specifications.",
            evidence_clause="Conductor and Armouring Construction Clauses"
        ),
        "CONF-04-VOLTAGE-CONFLICT": ConflictRule(
            rule_id="CONF-04-VOLTAGE-CONFLICT",
            name="Low-Voltage Wiring Standard Specified for Medium or High Voltage System",
            technical_rationale=(
                "IS 694 is technically restricted to working voltages up to and including 1100 V (1.1 kV). "
                "Specifying IS 694 for medium-voltage (3.3 kV to 33 kV) or high-voltage circuits exceeds insulation "
                "dielectric breakdown limits and violates Central Electricity Authority safety standards."
            ),
            authoritative_evidence="IS 694 : 2010 Clause 1.1 (Rated voltage up to and including 1100 V a.c.).",
            evidence_clause="IS 694 : 2010 Clause 1.1"
        ),
        "CONF-05-TILE-CRANE-CONFLICT": ConflictRule(
            rule_id="CONF-05-TILE-CRANE-CONFLICT",
            name="Ceramic Architectural Tile Standard Specified for Heavy Crane Rail Infrastructure",
            technical_rationale=(
                "IS 15622 governs pressed ceramic tiles for architectural floor and wall finishes. "
                "Specifying ceramic tile specifications for heavy crane rail tracks (RMQC) represents a fundamental domain conflict."
            ),
            authoritative_evidence="IS 15622 : 2017 Scope Clause 1.",
            evidence_clause="IS 15622 : 2017 Clause 1"
        )
    }

    @classmethod
    def check_conflict(
        cls,
        text: str,
        components: List[RequirementComponent],
        candidates: List[SearchResult]
    ) -> Optional[Tuple[ConflictRule, str]]:
        """Evaluates requirement and candidate context against explicit conflict rules.
        
        Returns (rule, reason) if triggered, otherwise None.
        """
        t_low = text.lower()

        # Rule CONF-04: Low-voltage wire/cable standard (IS 694) cited for MV/HV (3.3 kV to 33 kV)
        has_mv_hv_voltage = bool(re.search(r'\b(?:3\.3\s*kv|6\.6\s*kv|11\s*kv|22\s*kv|33\s*kv|66\s*kv|medium\s*voltage|mv\b|high\s*voltage|substation|transmission\s*line)\b', t_low))
        has_is694 = bool(re.search(r'\bis\s*694\b', t_low)) or any("694" in c.standard_number for c in candidates[:3])
        if has_mv_hv_voltage and has_is694:
            rule = cls.RULES["CONF-04-VOLTAGE-CONFLICT"]
            reason = (
                f"Conflict detected [{rule.rule_id}]: Low-voltage cable standard IS 694 (rated up to 1100 V) "
                f"specified for medium/high voltage (>1.1 kV) installation. {rule.technical_rationale}"
            )
            return rule, reason

        # Rule CONF-05: Ceramic tile standard (IS 15622) cited for heavy machinery / crane rail track
        has_heavy_rail = any(kw in t_low for kw in ["crane rail", "crane rail track", "rmqc", "quay crane"])
        has_tile = bool(re.search(r'\bis\s*15622\b', t_low)) or any("15622" in c.standard_number for c in candidates[:3])
        if has_heavy_rail and has_tile:
            rule = cls.RULES["CONF-05-TILE-CRANE-CONFLICT"]
            reason = (
                f"Conflict detected [{rule.rule_id}]: Ceramic tile standard IS 15622 specified for heavy crane rail track infrastructure. "
                f"{rule.technical_rationale}"
            )
            return rule, reason

        # Rule CONF-01: Agricultural code vs Industrial MV/HV/Process
        has_industrial_mv = any(
            kw in t_low for kw in [
                "industrial", "process water", "substation", "medium voltage", "3.3 kv", "6.6 kv", "11 kv",
                "33 kv", "vfd", "mcc panel", "switchyard", "refinery", "chemical plant", "boiler feed"
            ]
        )
        has_pump_context = any(
            kw in t_low for kw in [
                "pump", "pumps", "pumping", "water treatment", "process water", "fluid", "irrigation"
            ]
        ) or bool(re.search(r'\bis\s*9079\b', t_low))
        has_agri_std = bool(re.search(r'\bis\s*9079\b', t_low))
        for cand in candidates[:3]:
            title_low = cand.full_title.lower()
            if any(kw in title_low for kw in ["agricultural", "irrigation equipment", "agricultural pump"]):
                has_agri_std = True
                break

        if has_industrial_mv and has_pump_context and has_agri_std:
            rule = cls.RULES["CONF-01-AGRI-IND-MV"]
            reason = (
                f"Conflict detected [{rule.rule_id}]: Requirement specifies industrial process/equipment, "
                f"but cites or matches agricultural irrigation standard. {rule.technical_rationale}"
            )
            return rule, reason

        # Rule CONF-02: CPVC with continuous steam service
        has_cpvc = bool(re.search(r'\bcpvc\b', t_low))
        has_steam = bool(re.search(r'\b(?:superheated\s+steam|continuous\s+steam|steam\s+lines?|boiler\s+steam)\b', t_low))
        if has_cpvc and has_steam:
            rule = cls.RULES["CONF-02-PRESS-TEMP-INCOMPAT"]
            reason = (
                f"Conflict detected [{rule.rule_id}]: Requirement specifies CPVC piping for continuous steam service. "
                f"{rule.technical_rationale} (Evidence: {rule.authoritative_evidence})"
            )
            return rule, reason

        # Rule CONF-03: Contradictory physical specifications
        contradictions = [
            (r'\bsolid\s+copper\s+conductor\b.*\baluminium\s+wire\b', "Solid Copper Conductor combined with Aluminium Wire"),
            (r'\baluminium\s+conductor\b.*\bcopper\s+wire\b', "Aluminium Conductor combined with Copper Wire"),
            (r'\bunarmoured\b.*\b(?:strip|wire)\s+armoured\b', "Unarmoured combined with Armoured construction"),
        ]
        for pattern, desc in contradictions:
            if re.search(pattern, t_low):
                rule = cls.RULES["CONF-03-CONTRADICTORY-SPECS"]
                reason = (
                    f"Conflict detected [{rule.rule_id}]: Requirement contains self-contradictory specifications: "
                    f"{desc}. {rule.technical_rationale}"
                )
                return rule, reason

        return None


# ---------------------------------------------------------------------------
# 4. Ambiguity Engine
# ---------------------------------------------------------------------------

class AmbiguityEngine:
    """Deterministic ambiguity analyzer executing the strict 8-stage pipeline."""

    def __init__(self, separation_threshold: float = 0.12):
        # Configurable candidate separation threshold (default 0.12 based on sweep)
        self.separation_threshold = separation_threshold

    def evaluate(
        self,
        requirement_text: str,
        decomposed_components: List[RequirementComponent],
        completeness_report: Optional[SpecificationCompletenessReport],
        retrieved_candidates: List[SearchResult],
        applicable_candidates: List[SearchResult],
        rejected_candidates: List[Any],
        candidate_applicability_map: Dict[str, Any],
        critic_outcome: Optional[Any],
        explicit_standards: List[str],
        unresolved_components: Optional[List[str]] = None
    ) -> AmbiguityReport:
        """Executes the strict 8-stage decision pipeline.
        
        No stage may secretly perform the responsibility of another stage.
        Downstream stages cannot override upstream abstention gates.
        """
        text = requirement_text.strip()
        unresolved = unresolved_components or []

        # -------------------------------------------------------------------
        # Stage 1: Conflict Detection
        # -------------------------------------------------------------------
        conflict_result = ConflictRegistry.check_conflict(
            text=text,
            components=decomposed_components,
            candidates=retrieved_candidates
        )
        if conflict_result:
            rule, reason = conflict_result
            return AmbiguityReport(
                ambiguity_state=AmbiguityState.CONFLICTING,
                ambiguity_reason=reason,
                conflict_rule_id=rule.rule_id,
                retrieval_status="CANDIDATES_FOUND" if retrieved_candidates else "ZERO_RESULTS",
                applicability_status="ALL_REJECTED",
                evidence_status="VALID",
                human_review_required=True,
                suggested_clarification_question=(
                    "The tender contains conflicting specifications. Please clarify whether "
                    "industrial specifications or alternative material/service ratings apply."
                ),
                decision_confidence="High"
            )

        # -------------------------------------------------------------------
        # Stage 2: Catalogue Retrieval / Coverage
        # Evaluates retrieval ONLY. Does NOT use Applicability Gate results.
        # -------------------------------------------------------------------
        if not retrieved_candidates:
            return AmbiguityReport(
                ambiguity_state=AmbiguityState.NO_RELIABLE_MATCH,
                ambiguity_reason="No reliable catalogue candidate was retrieved for this requirement.",
                retrieval_status="ZERO_RESULTS",
                applicability_status="ALL_REJECTED",
                evidence_status="INSUFFICIENT",
                human_review_required=True,
                suggested_clarification_question=(
                    "No relevant Indian Standard was found in the catalogue. Please specify if an "
                    "international standard (ISO/IEC) or project-specific specification governs this item."
                ),
                decision_confidence="High"
            )

        # -------------------------------------------------------------------
        # Stage 3: Candidate Applicability Gate
        # Eliminates out-of-domain / uncatalogued technologies before generic completeness checks.
        # Examples: liquid sodium pump, deep subsea umbilical -> NO_RELIABLE_MATCH.
        # -------------------------------------------------------------------
        if not applicable_candidates:
            return AmbiguityReport(
                ambiguity_state=AmbiguityState.NO_RELIABLE_MATCH,
                ambiguity_reason="Retrieved candidates did not pass the domain/product applicability checks.",
                retrieval_status="CANDIDATES_FOUND",
                applicability_status="ALL_REJECTED",
                evidence_status="INSUFFICIENT",
                human_review_required=True,
                suggested_clarification_question=(
                    "Retrieved standards belong to incompatible product domains. Please specify the "
                    "applicable Indian Standard or exact technical classification for this item."
                ),
                decision_confidence="High"
            )

        primary_crit = getattr(critic_outcome, "primary_critique", None)
        crit_decision = getattr(primary_crit, "decision", "") if primary_crit else ""
        if crit_decision in ["REJECT", "REJECT_NO_MATCH"]:
            return AmbiguityReport(
                ambiguity_state=AmbiguityState.NO_RELIABLE_MATCH,
                ambiguity_reason="Retrieved candidates were evaluated and rejected due to technical mismatch or domain conflict.",
                retrieval_status="CANDIDATES_FOUND",
                applicability_status="ALL_REJECTED",
                evidence_status="INSUFFICIENT",
                human_review_required=True,
                suggested_clarification_question=(
                    "Retrieved standards do not reliably cover this requirement. Please specify the "
                    "applicable Indian Standard or exact technical classification for this item."
                ),
                decision_confidence="High"
            )

        # -------------------------------------------------------------------
        # Stage 4: Candidate Competition & Disambiguation (AMBIGUOUS)
        # Evaluates whether the catalogue has established multiple viable, materially different
        # candidate interpretations whose selection depends on a missing discriminating parameter.
        # -------------------------------------------------------------------
        if len(applicable_candidates) >= 2 and len(explicit_standards) != 1:
            # Bound the pool to the primary product candidates
            primary_candidates = []
            for c in applicable_candidates:
                role = classify_standard_role(c.standard_number, c.full_title, c.scope_summary)
                if role == "PRIMARY_PRODUCT":
                    primary_candidates.append(c)
            
            # If no primary products, use the applicable ones
            pool = primary_candidates if primary_candidates else applicable_candidates
            
            if len(pool) >= 2:
                c_top = pool[0]
                tender_attrs = extract_tender_attributes(text)
                
                competing_found = False
                chosen_c1, chosen_c2, chosen_param, chosen_expl = None, None, None, {}
                
                for alt in pool[1:]:
                    is_mat, param, expl = self.is_true_competing_interpretation(
                        text, c_top, alt, completeness_report, decomposed_components, tender_attrs
                    )
                    if is_mat:
                        competing_found = True
                        chosen_c1 = c_top
                        chosen_c2 = alt
                        chosen_param = param
                        chosen_expl = expl
                        break
                
                if competing_found and chosen_c1 and chosen_c2:
                    delta = round(abs(chosen_c1.final_score - chosen_c2.final_score), 3)
                    competing = [
                        CompetingInterpretation(
                            standard_number=chosen_c1.standard_number,
                            title=chosen_c1.full_title,
                            interpretation=self._summarize_interpretation(chosen_c1),
                            relevance_score=chosen_c1.final_score,
                            distinguishing_parameter_needed=chosen_param,
                            why_plausible=chosen_expl.get("why_plausible", "Applicable product standard for requirement domain."),
                            evidence=chosen_expl.get("evidence_a", chosen_c1.scope_summary or chosen_c1.relevance_reason),
                            provenance=chosen_c1.verification_status
                        ).to_dict(),
                        CompetingInterpretation(
                            standard_number=chosen_c2.standard_number,
                            title=chosen_c2.full_title,
                            interpretation=self._summarize_interpretation(chosen_c2),
                            relevance_score=chosen_c2.final_score,
                            distinguishing_parameter_needed=chosen_param,
                            why_plausible=chosen_expl.get("why_plausible", "Applicable product standard for requirement domain."),
                            evidence=chosen_expl.get("evidence_b", chosen_c2.scope_summary or chosen_c2.relevance_reason),
                            provenance=chosen_c2.verification_status
                        ).to_dict()
                    ]
                    reason_msg = (
                        f"Multiple competing Indian Standards ({chosen_c1.standard_number} and {chosen_c2.standard_number}) "
                        f"have competing applicability for the same procurement object. "
                        f"The tender does not contain distinguishing specifications ({chosen_param}) to select between them."
                    )
                    return AmbiguityReport(
                        ambiguity_state=AmbiguityState.AMBIGUOUS,
                        ambiguity_reason=reason_msg,
                        retrieval_status="CANDIDATES_FOUND",
                        applicability_status="VIABLE_CANDIDATE",
                        evidence_status="VALID",
                        competing_interpretations=competing,
                        separation_margin=delta,
                        missing_information=[chosen_param],
                        human_review_required=True,
                        suggested_clarification_question=(
                            f"Which standard or specification is intended: {chosen_c1.standard_number} or {chosen_c2.standard_number}? "
                            f"Please specify {chosen_param}."
                        ),
                        decision_confidence="High"
                    )

        # -------------------------------------------------------------------
        # Stage 5: Specification Completeness (INCOMPLETE)
        # Evaluates whether critical discriminating technical parameters are missing when
        # no competing candidate interpretations were established in Stage 4.
        # -------------------------------------------------------------------
        if not explicit_standards and applicable_candidates:
            # Generalize completeness by using attributes
            tender_attrs = extract_tender_attributes(text)
            c_top = applicable_candidates[0]
            top_attrs = extract_standard_attributes(c_top.standard_number, c_top.full_title, c_top.scope_summary)
            
            missing = []
            if top_attrs.product_family != "other":
                if top_attrs.material and not tender_attrs.material: missing.append("material")
                if top_attrs.voltage_rating and not tender_attrs.voltage_rating: missing.append("voltage rating")
                if top_attrs.valve_type and not tender_attrs.valve_type: missing.append("valve type")
                if top_attrs.pump_type and not tender_attrs.pump_type: missing.append("pump type")
                
            if len(missing) >= 2:
                domain = top_attrs.product_family
                question = self._build_incomplete_clarification_question(domain, missing)
                reason_msg = (
                    f"Tender requirement specifies '{domain}' equipment but omits critical discriminating "
                    f"technical parameters ({', '.join(missing)}). A specific Indian Standard "
                    f"cannot be safely selected without guessing."
                )
                return AmbiguityReport(
                    ambiguity_state=AmbiguityState.INCOMPLETE,
                    ambiguity_reason=reason_msg,
                    retrieval_status="CANDIDATES_FOUND",
                    applicability_status="VIABLE_CANDIDATE",
                    evidence_status="VALID",
                    missing_information=missing,
                    human_review_required=True,
                    suggested_clarification_question=question,
                    decision_confidence="High"
                )

        # -------------------------------------------------------------------
        # Stage 6: Evidence Trust Validation
        # Validates evidence existence, strength, grounding, and canonical identity.
        # Evidence NONE -> REVIEW_REQUIRED with evidence_status = "INSUFFICIENT"
        # -------------------------------------------------------------------
        top_cand = applicable_candidates[0]
        primary_crit = getattr(critic_outcome, "primary_critique", None)
        crit_ev = getattr(primary_crit, "evidence", None) if primary_crit else None
        ev_strength = getattr(crit_ev, "evidence_strength", "NONE") if crit_ev else "NONE"
        grounded = getattr(crit_ev, "grounded", False) if crit_ev else False

        if ev_strength == "NONE":
            return AmbiguityReport(
                ambiguity_state=AmbiguityState.REVIEW_REQUIRED,
                ambiguity_reason=(
                    f"Candidate {top_cand.standard_number} lacks direct scope evidence supporting this tender application. "
                    f"Engineering review required prior to procurement."
                ),
                retrieval_status="CANDIDATES_FOUND",
                applicability_status="VIABLE_CANDIDATE",
                evidence_status="INSUFFICIENT",
                human_review_required=True,
                suggested_clarification_question=(
                    f"Please confirm whether candidate standard {top_cand.standard_number} ({top_cand.full_title}) "
                    f"is acceptable for this specific requirement."
                ),
                decision_confidence="Medium"
            )

        if not grounded:
            return AmbiguityReport(
                ambiguity_state=AmbiguityState.REVIEW_REQUIRED,
                ambiguity_reason=(
                    f"Evidence grounding validation failed for {top_cand.standard_number}. "
                    f"Clause-level support could not be verified."
                ),
                retrieval_status="CANDIDATES_FOUND",
                applicability_status="VIABLE_CANDIDATE",
                evidence_status="GROUNDING_FAILED",
                human_review_required=True,
                suggested_clarification_question=(
                    f"Evidence clause grounding for {top_cand.standard_number} needs technical verification."
                ),
                decision_confidence="Medium"
            )

        # -------------------------------------------------------------------
        # Stage 7: Lifecycle & Regulatory Review
        # Evaluates active lifecycle, superseded citations, QCO reviews,
        # and compound unresolved components.
        # -------------------------------------------------------------------
        lifecycle_review_needed = False
        lifecycle_reasons = []

        # Check superseded citations
        if getattr(top_cand, "_explicit_successor_warning", None):
            lifecycle_review_needed = True
            lifecycle_reasons.append(getattr(top_cand, "_explicit_successor_warning"))

        # Check auxiliary unresolved components in compound requirements
        if unresolved:
            lifecycle_review_needed = True
            lifecycle_reasons.append(
                f"Primary standard {top_cand.standard_number} is supported, but auxiliary components "
                f"({', '.join(unresolved)}) require separate technical specification or review."
            )

        # Check regulatory review flag
        reg_decision = getattr(critic_outcome, "decision", "")
        if reg_decision in ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE", "REJECT"]:
            lifecycle_review_needed = True
            if getattr(critic_outcome, "risk_reasons", None):
                lifecycle_reasons.extend(critic_outcome.risk_reasons)

        # Check potentially missing discriminating parameters in domains like valves where metallurgy/size must be confirmed
        if completeness_report:
            domain = completeness_report.domain
            if domain == "valve":
                body_mat = completeness_report.parameters.get("body_material")
                if body_mat and body_mat.status != "KNOWN":
                    lifecycle_review_needed = True
                    lifecycle_reasons.append(
                        "Valve body metallurgy/material is not specified in tender. Human review recommended to confirm metallurgy (copper alloy vs cast iron vs steel)."
                    )
            elif not completeness_report.is_adequately_specified:
                lifecycle_review_needed = True
                missing_items = ", ".join(completeness_report.potentially_missing_parameters[:3])
                lifecycle_reasons.append(
                    f"Specification lacks key parameters ({missing_items}). Human review recommended."
                )

        if lifecycle_review_needed:
            reason_text = "; ".join(lifecycle_reasons) if lifecycle_reasons else "Technical review required prior to procurement."
            return AmbiguityReport(
                ambiguity_state=AmbiguityState.REVIEW_REQUIRED,
                ambiguity_reason=reason_text,
                retrieval_status="CANDIDATES_FOUND",
                applicability_status="VIABLE_CANDIDATE",
                evidence_status="VALID",
                unresolved_components=unresolved,
                human_review_required=True,
                suggested_clarification_question=(
                    f"Verify application of {top_cand.standard_number} and review the following notes: {reason_text}"
                ),
                decision_confidence="High"
            )

        # -------------------------------------------------------------------
        # Stage 8: Final Resolution -> CLEAR
        # Active lifecycle + sufficient valid evidence + no unresolved review condition
        # -------------------------------------------------------------------
        return AmbiguityReport(
            ambiguity_state=AmbiguityState.CLEAR,
            ambiguity_reason=f"Primary applicable standard {top_cand.standard_number} is clearly identifiable and sufficiently supported.",
            retrieval_status="CANDIDATES_FOUND",
            applicability_status="VIABLE_CANDIDATE",
            evidence_status="VALID",
            human_review_required=False,
            decision_confidence="High"
        )

    # -----------------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------------

    def is_true_competing_interpretation(
        self,
        text: str,
        c1: SearchResult,
        c2: SearchResult,
        completeness_report: Optional[SpecificationCompletenessReport] = None,
        components: Optional[List[RequirementComponent]] = None,
        tender_attrs: Optional[Any] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Deterministic Semantic Competition Gate using General Attributes.

        Returns (is_competing, discriminator_description, explanation_dict).
        """
        s1 = c1.standard_number.strip()
        s2 = c2.standard_number.strip()
        t1 = (c1.full_title or "").lower()
        t2 = (c2.full_title or "").lower()
        text_lower = (text or "").lower()

        if s1 == s2:
            return False, "", {}
        from src.critic import are_standards_equivalent
        if are_standards_equivalent(s1, s2):
            return False, "", {}

        # 1. Standard Role Gate
        role1 = classify_standard_role(s1, t1, c1.scope_summary)
        role2 = classify_standard_role(s2, t2, c2.scope_summary)
        if role1 != role2:
            return False, "", {}

        # 2. Attribute Derivation
        attr1 = extract_standard_attributes(s1, t1, c1.scope_summary)
        attr2 = extract_standard_attributes(s2, t2, c2.scope_summary)
        if not tender_attrs:
            tender_attrs = extract_tender_attributes(text)

        # 3. Object matching
        if not same_procurement_object(attr1, attr2):
            return False, "", {}
            
        # Hard safety override for VFD vs Switchgear since they share product family "panel" in our simple attribute extractor
        if ("vfd" in t1 or "power drive" in t1) and ("switchgear" in t2 or "controlgear" in t2):
            return False, "", {}
        if ("vfd" in t2 or "power drive" in t2) and ("switchgear" in t1 or "controlgear" in t1):
            return False, "", {}
            
        # Food safety edge case override
        if "food" in t1 and "food" in t2:
            has_haccp = "haccp" in text_lower or "15000" in text_lower
            has_gen = "basic hygiene" in text_lower or "2491" in text_lower
            if has_haccp != has_gen:
                return False, "", {}

        # 4. Discriminator Detection
        discriminators = find_discriminators(attr1, attr2)
        if not discriminators:
            return False, "", {}

        # 5. Check if discriminator is explicitly specified in the tender
        for disc in discriminators:
            if not discriminator_specified_in_tender(disc, tender_attrs):
                param_desc = f"{disc} ({getattr(attr1, disc, 'Unknown')} vs {getattr(attr2, disc, 'Unknown')})"
                expl = {
                    "candidate_a": s1,
                    "candidate_b": s2,
                    "discriminator": param_desc,
                    "why_plausible": f"Both {s1} and {s2} are applicable specifications for this {attr1.product_family}.",
                    "evidence_a": c1.scope_summary or c1.relevance_reason,
                    "evidence_b": c2.scope_summary or c2.relevance_reason,
                    "abstention_rationale": f"Tender specification lacks the required technical discriminator ({disc}) needed to select between them."
                }
                return True, param_desc, expl
                
        return False, "", {}

    def _are_candidates_competing(
        self,
        c1: SearchResult,
        c2: SearchResult,
        completeness_report: Optional[SpecificationCompletenessReport],
        text: str = ""
    ) -> Tuple[bool, str]:
        """Backward-compatible wrapper for is_true_competing_interpretation."""
        is_competing, param, _ = self.is_true_competing_interpretation(
            text=text,
            c1=c1,
            c2=c2,
            completeness_report=completeness_report
        )
        return is_competing, param

    def _summarize_interpretation(self, cand: SearchResult) -> str:
        """Generates a concise plain-English interpretation for a candidate standard."""
        snum = cand.standard_number
        title = cand.full_title
        if "694" in snum:
            return "PVC Insulated Cables for working voltages up to and including 1100 V"
        if "7098" in snum:
            return "Crosslinked Polyethylene (XLPE) Insulated Thermoplastic Sheathed Cables"
        if "778" in snum:
            return "Copper Alloy Gate, Globe and Check Valves for waterworks"
        if "14846" in snum:
            return "Sluice Valves for Waterworks Purposes (Cast Iron, 50 to 1200 mm)"
        if "269" in snum:
            return "Ordinary Portland Cement (33, 43, and 53 grades)"
        if "1489" in snum:
            return "Portland Pozzolana Cement (Fly-ash / Calcined clay based)"
        if "2491" in snum:
            return "Food Hygiene - General Principles - Code of Practice"
        if "15000" in snum:
            return "Hazard Analysis and Critical Control Point (HACCP) - Requirements for Food Chain"
        if "458" in snum:
            return "Precast Concrete Pipes (with and without Reinforcement)"
        if "14333" in snum:
            return "High Density Polyethylene (HDPE) Pipes for Sewerage"
        if "1239" in snum:
            return "Steel Tubes, Tubulars and Other Wrought Steel Fittings (Part 1 Tubes)"
        if "8329" in snum:
            return "Centrifugally Cast (Ductile) Iron Pressure Pipes for Water, Gas and Sewage"
        return title[:90] + ("..." if len(title) > 90 else "")

    def _build_incomplete_clarification_question(self, domain: str, missing_params: List[str]) -> str:
        """Builds domain-tailored clarification question for tender officers."""
        if domain == "cable":
            return "What voltage rating (e.g. 1.1 kV / 11 kV), conductor material (Copper / Aluminium), and insulation type (PVC / XLPE) are required?"
        elif domain == "valve":
            return "What valve type (gate, globe, check, ball), body metallurgy (bronze, cast iron, forged steel), and nominal diameter (DN) should be specified?"
        elif domain == "pipe":
            return "What piping material (CPVC, uPVC, HDPE, DI, GI) and application environment (potable water, drainage, industrial) are required?"
        elif domain == "motor":
            return "What operating voltage (LT / HT), rated power (kW/HP), and duty enclosure (TEFC / Flameproof) are required?"
        elif domain == "pump":
            return "What pump mechanism (centrifugal, submersible, monobloc), operating discharge (Q), and head (H) are required?"
        return f"Please clarify the following missing technical parameters: {', '.join(missing_params)}."


def is_true_competing_interpretation(
    text: str,
    c1: SearchResult,
    c2: SearchResult,
    completeness_report: Optional[SpecificationCompletenessReport] = None,
    components: Optional[List[RequirementComponent]] = None,
    separation_threshold: float = 0.08,
    tender_attrs: Optional[Any] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """Standalone wrapper around AmbiguityEngine.is_true_competing_interpretation."""
    engine = AmbiguityEngine(separation_threshold=separation_threshold)
    return engine.is_true_competing_interpretation(text, c1, c2, completeness_report, components, tender_attrs)
