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
        has_agri_std = bool(re.search(r'\bis\s*9079\b', t_low))
        for cand in candidates[:3]:
            title_low = cand.full_title.lower()
            if any(kw in title_low for kw in ["agricultural", "irrigation equipment", "agricultural pump"]):
                has_agri_std = True
                break

        if has_industrial_mv and has_agri_std:
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

    def __init__(self, separation_threshold: float = 0.03):
        # Configurable candidate separation threshold (default 0.03)
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
            competing_found = False
            chosen_c1 = None
            chosen_c2 = None
            chosen_param = None
            chosen_delta = 0.0

            top_cand = applicable_candidates[0]
            top_pool = applicable_candidates[1:4]
            for c_j in top_pool:
                delta = round(abs(top_cand.final_score - c_j.final_score), 3)
                if delta < self.separation_threshold:
                    is_mat, param = self._are_candidates_competing(top_cand, c_j, completeness_report, text)
                    if is_mat:
                        competing_found = True
                        chosen_c1 = top_cand
                        chosen_c2 = c_j
                        chosen_param = param
                        chosen_delta = delta
                        break

            if competing_found and chosen_c1 and chosen_c2:
                competing = [
                    CompetingInterpretation(
                        standard_number=chosen_c1.standard_number,
                        title=chosen_c1.full_title,
                        interpretation=self._summarize_interpretation(chosen_c1),
                        relevance_score=chosen_c1.final_score,
                        distinguishing_parameter_needed=chosen_param
                    ).to_dict(),
                    CompetingInterpretation(
                        standard_number=chosen_c2.standard_number,
                        title=chosen_c2.full_title,
                        interpretation=self._summarize_interpretation(chosen_c2),
                        relevance_score=chosen_c2.final_score,
                        distinguishing_parameter_needed=chosen_param
                    ).to_dict()
                ]
                return AmbiguityReport(
                    ambiguity_state=AmbiguityState.AMBIGUOUS,
                    ambiguity_reason=(
                        f"Multiple competing Indian Standards ({chosen_c1.standard_number} and {chosen_c2.standard_number}) "
                        f"have comparable applicability (score delta: {chosen_delta:.3f} < {self.separation_threshold:.2f}). "
                        f"The tender does not contain distinguishing specifications to select between them."
                    ),
                    retrieval_status="CANDIDATES_FOUND",
                    applicability_status="VIABLE_CANDIDATE",
                    evidence_status="VALID",
                    competing_interpretations=competing,
                    separation_margin=chosen_delta,
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
        if completeness_report and not explicit_standards:
            domain = completeness_report.domain
            is_critically_incomplete = False
            domain_discrim_needed = []

            if domain == "cable":
                has_volt = any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["voltage_rating"])
                has_ins = any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["insulation_type"]) or any(k in text.lower() for k in ["paper", "pilc", "rubber", "mineral", "telephone", "optical"])
                has_app = any(k in text.lower() for k in ["amf", "dg set", "generator", "stp", "substation", "switchyard", "underground"])
                if not has_volt and not has_ins and not has_app:
                    is_critically_incomplete = True
                    domain_discrim_needed = ["voltage rating (e.g. 1.1 kV / 11 kV)", "conductor material", "insulation type (PVC / XLPE)"]

            elif domain == "valve":
                has_type = any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["valve_type"])
                has_mat = any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["body_material"])
                if not has_type and not has_mat:
                    is_critically_incomplete = True
                    domain_discrim_needed = [
                        "valve nominal diameter (DN)",
                        "pressure rating (PN)",
                        "body metallurgy (cast iron vs bronze vs forged steel)",
                        "process medium"
                    ]

            elif domain == "pipe":
                has_mat = any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["material"])
                if not has_mat:
                    is_critically_incomplete = True
                    domain_discrim_needed = ["pipe material (CPVC/uPVC/HDPE/DI/GI/Concrete)", "application environment"]

            elif domain == "pump":
                has_type = (
                    any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["pump_type", "motor_details"])
                    or any(k in text.lower() for k in ["3.3 kv", "415 v", "11 kv", "coupled with", "vfd", "centrifugal", "submersible", "monobloc"])
                )
                if not has_type:
                    is_critically_incomplete = True
                    domain_discrim_needed = ["pump mechanism (centrifugal/submersible/monobloc)", "operating discharge (Q) and head (H)"]

            elif domain == "motor":
                has_volt = any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["voltage_rating"])
                has_power = any(p in completeness_report.parameters and completeness_report.parameters[p].status == "KNOWN" for p in ["power_rating"])
                if not has_volt and not has_power:
                    is_critically_incomplete = True
                    domain_discrim_needed = ["operating voltage (LT/HT)", "rated output / power (kW/HP)"]

            elif domain in ["panel", "switchgear", "distribution_board"] or any(k in text.lower() for k in ["distribution panel", "distribution board", "switchboard", "mccb panel"]):
                has_rating = any(k in text.lower() for k in ["ampere", " amp", "415v", "11kv", "fault rating", "form 4", "ip54", "ip55", "ip65", "distribution board", "feeder pillar"])
                if not has_rating:
                    is_critically_incomplete = True
                    domain_discrim_needed = ["voltage rating", "busbar current rating (Amperes)", "short-circuit fault rating (kA)", "enclosure IP rating"]

            elif domain == "cement" or any(k in text.lower() for k in ["cement bags", "supply of cement", "standard cement"]):
                has_grade = any(k in text.lower() for k in ["43 grade", "53 grade", "33 grade", "opc", "ppc", "psc", "pozzolana", "slag"])
                if not has_grade:
                    is_critically_incomplete = True
                    domain_discrim_needed = ["cement type (Ordinary Portland Cement vs Portland Pozzolana Cement)", "strength grade (33 / 43 / 53)"]

            if is_critically_incomplete:
                question = self._build_incomplete_clarification_question(domain, domain_discrim_needed)
                if domain == "valve":
                    reason_msg = (
                        "Tender specifies valve work without defining valve nominal diameter (DN), "
                        "pressure rating (PN), body metallurgy (cast iron vs bronze vs forged steel), or process medium."
                    )
                else:
                    reason_msg = (
                        f"Tender requirement specifies '{domain}' equipment but omits critical discriminating "
                        f"technical parameters ({', '.join(domain_discrim_needed)}). A specific Indian Standard "
                        f"cannot be safely selected without guessing."
                    )
                return AmbiguityReport(
                    ambiguity_state=AmbiguityState.INCOMPLETE,
                    ambiguity_reason=reason_msg,
                    retrieval_status="CANDIDATES_FOUND",
                    applicability_status="VIABLE_CANDIDATE",
                    evidence_status="VALID",
                    missing_information=domain_discrim_needed,
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

    def _are_candidates_competing(
        self,
        c1: SearchResult,
        c2: SearchResult,
        completeness_report: Optional[SpecificationCompletenessReport],
        text: str = ""
    ) -> Tuple[bool, str]:
        """Determination of whether two candidates represent distinct, mutually exclusive options.
        
        Generic product category nouns (cable, pipe, valve, gasket, luminaire) do NOT
        automatically trigger ambiguity. Competition requires substantive technical-attribute,
        metallurgy, material, rating, or functional conflict.
        """
        s1 = c1.standard_number.strip()
        s2 = c2.standard_number.strip()
        
        # 0. Candidate cannot compete against itself or equivalent standard
        if s1 == s2:
            return False, ""
        from src.critic import are_standards_equivalent
        if are_standards_equivalent(s1, s2):
            return False, ""

        t1 = c1.full_title.lower()
        t2 = c2.full_title.lower()
        comb1 = f"{s1} {t1}".lower()
        comb2 = f"{s2} {t2}".lower()

        # 1. Complementary check: Code of Practice / Installation vs Manufactured Product
        cop_stds = {"1255", "783", "732", "1661", "14164", "3043", "SP 30", "SP 57"}
        product_stds = {
            "7098", "694", "1554", "458", "14333", "15778", "4985", "1239", "8329",
            "778", "14846", "10434", "269", "1489", "15622", "6392", "2712", "781",
            "774", "10322", "60034", "325", "5120", "9694", "16088", "15905", "5039"
        }

        def is_code_of_practice(s: str, t: str) -> bool:
            if any(p in s for p in product_stds):
                return False
            if any(num in s for num in cop_stds):
                return True
            return "code of practice" in t and not any(p in s for p in product_stds)

        if is_code_of_practice(s1, t1) != is_code_of_practice(s2, t2):
            return False, ""

        c1_is_test = "method of test" in t1 or "methods of test" in t1 or "testing" in t1
        c2_is_test = "method of test" in t2 or "methods of test" in t2 or "testing" in t2
        if c1_is_test != c2_is_test:
            return False, ""
            
        c1_is_gloss = "glossary" in t1 or "vocabulary" in t1
        c2_is_gloss = "glossary" in t2 or "vocabulary" in t2
        if c1_is_gloss != c2_is_gloss:
            return False, ""

        # 2. Complementary Assembly Parts (Distinct Functional Items in an engineered assembly)
        def get_assembly_classes(s: str, t: str) -> set:
            classes = set()
            if "6392" in s or "pipe flange" in t:
                classes.add("flange")
            if "2712" in s or "jointing sheet" in t or "gasket" in t:
                classes.add("gasket")
            if "781" in s or "bib tap" in t or "bib cock" in t:
                classes.add("bib_tap")
            if "774" in s or "cistern" in t:
                classes.add("cistern")
            if "2556" in s or "vitreous" in t:
                classes.add("vitreous_sanitary")
            if "10322" in s or "floodlight" in t or "luminaire" in t:
                classes.add("luminaire")
            if ("61439-3" in s or "5039" in s or "distribution board" in t) and "61800" not in s:
                classes.add("distribution_board")
            return classes

        c1_cls = get_assembly_classes(s1, t1)
        c2_cls = get_assembly_classes(s2, t2)
        if c1_cls and c2_cls and not (c1_cls & c2_cls):
            comp_pairs = [
                ({"flange"}, {"gasket"}),
                ({"bib_tap"}, {"cistern"}),
                ({"bib_tap"}, {"vitreous_sanitary"}),
                ({"cistern"}, {"vitreous_sanitary"}),
                ({"luminaire"}, {"distribution_board"}),
            ]
            for p1, p2 in comp_pairs:
                if (c1_cls == p1 and c2_cls == p2) or (c1_cls == p2 and c2_cls == p1):
                    return False, ""

        # 3. Substantive Technical-Attribute Conflicts
        # A. VFD vs Switchgear Panel (Compound case - T013)
        is_vfd1 = "61800" in s1 or "power drive" in comb1 or "vfd" in comb1
        is_vfd2 = "61800" in s2 or "power drive" in comb2 or "vfd" in comb2
        is_pnl1 = "61439" in s1 or "switchgear" in comb1
        is_pnl2 = "61439" in s2 or "switchgear" in comb2
        if (is_vfd1 and is_pnl2) or (is_vfd2 and is_pnl1):
            return True, "Equipment Scope (Variable Frequency Drive [IS/IEC 61800] vs Power Switchgear Panel [IS/IEC 61439])"

        # B. Food Safety Management Framework (AMB-AMB-05)
        is_food1 = any(k in comb1 for k in ["2491", "15000", "fssai", "food hygiene", "haccp"])
        is_food2 = any(k in comb2 for k in ["2491", "15000", "fssai", "food hygiene", "haccp"])
        if is_food1 and is_food2:
            has_2491 = "2491" in s1 or "2491" in s2
            has_alt = "15000" in s1 or "15000" in s2 or "fssai" in comb1 or "fssai" in comb2
            if has_2491 and has_alt:
                return True, "Food Safety Regulatory Framework (General Food Hygiene [IS 2491] vs HACCP / Statutory FSSAI Licensing)"

        # C. Valve Mechanism Conflicts (AMB-AMB-07)
        if ("5312" in s1 and "778" in s2) or ("778" in s1 and "5312" in s2):
            return True, "Valve Mechanism (Copper Alloy Gate/Globe Valve [IS 778] vs Swing Check Valve [IS 5312])"

        # D. Material / Metallurgy / Manufacturing Conflicts
        materials = {
            "pvc": ["pvc", "polyvinyl chloride", "694"],
            "xlpe": ["xlpe", "crosslinked polyethylene", "7098"],
            "concrete": ["concrete", "precast concrete", "458"],
            "hdpe": ["polyethylene", "hdpe", "14333"],
            "cpvc": ["cpvc", "chlorinated", "15778"],
            "upvc": ["upvc", "unplasticized", "4985"],
            "gi_steel": ["mild steel", "galvanized", "steel tubes", "1239"],
            "ductile_iron": ["ductile iron", "8329"],
            "copper_alloy": ["copper alloy", "bronze", "brass", "778"],
            "cast_iron": ["cast iron", "sluice", "14846"],
            "cast_steel": ["bolted bonnet steel", "10434"],
            "opc": ["ordinary portland", "opc", "269"],
            "ppc": ["portland pozzolana", "ppc", "1489"],
            "dry_pressed": ["dry-pressed", "dry pressed", "15622"],
            "extruded": ["extruded", "13712"],
            "oil_immersed": ["oil immersed", "1180"],
            "dry_type": ["dry type", "2026"],
            "hot_rolled": ["hot rolled", "800"],
            "cold_formed": ["cold formed", "801"]
        }

        mat_conflicts = [
            ({"pvc"}, {"xlpe"}, "Cable Insulation Polymer (PVC [IS 694] vs XLPE [IS 7098])"),
            ({"concrete"}, {"hdpe"}, "Piping Material (Precast Concrete [IS 458] vs Structured Wall Polyethylene [IS 14333])"),
            ({"concrete"}, {"cpvc"}, "Piping Material (Precast Concrete vs CPVC)"),
            ({"gi_steel"}, {"ductile_iron"}, "Piping Material (Galvanized Steel [IS 1239] vs Ductile Iron [IS 8329])"),
            ({"copper_alloy"}, {"cast_iron"}, "Body Metallurgy (Copper Alloy [IS 778] vs Cast Iron [IS 14846])"),
            ({"copper_alloy"}, {"cast_steel"}, "Body Metallurgy (Copper Alloy [IS 778] vs Cast Steel [IS 10434])"),
            ({"cast_iron"}, {"cast_steel"}, "Body Metallurgy (Cast Iron [IS 14846] vs Cast Steel [IS 10434])"),
            ({"opc"}, {"ppc"}, "Cement Chemistry (Ordinary Portland [IS 269] vs Portland Pozzolana [IS 1489])"),
            ({"dry_pressed"}, {"extruded"}, "Tile Manufacturing Process (Dry-pressed [IS 15622] vs Extruded [IS 13712])"),
            ({"oil_immersed"}, {"dry_type"}, "Transformer Cooling / Rating (Outdoor Oil Immersed [IS 1180] vs Power Transformer [IS 2026])"),
            ({"hot_rolled"}, {"cold_formed"}, "Structural Steel Section (Hot-Rolled [IS 800] vs Cold-Formed Light Gauge [IS 801])"),
        ]

        STD_MATERIAL_MAP = {
            "458": "concrete",
            "14333": "hdpe",
            "7098": "xlpe",
            "694": "pvc",
            "15778": "cpvc",
            "4985": "upvc",
            "1239": "gi_steel",
            "3589": "gi_steel",
            "8329": "ductile_iron",
            "778": "copper_alloy",
            "14846": "cast_iron",
            "10434": "cast_steel",
            "10611": "cast_steel",
            "269": "opc",
            "1489": "ppc",
            "15622": "dry_pressed",
            "13712": "extruded",
            "1180": "oil_immersed",
            "2026": "dry_type",
            "800": "hot_rolled",
            "801": "cold_formed",
        }

        def get_mat_tags(s: str, comb: str) -> set:
            for num, tag in STD_MATERIAL_MAP.items():
                if num in s:
                    return {tag}
            tags = set()
            for tag, words in materials.items():
                if any(w in comb for w in words):
                    tags.add(tag)
            return tags

        m1 = get_mat_tags(s1, comb1)
        m2 = get_mat_tags(s2, comb2)
        for f1, f2, desc in mat_conflicts:
            if (m1 & f1 and m2 & f2) or (m1 & f2 and m2 & f1):
                text_lower = text.lower() if text else ""
                t1_specified = any(any(w in text_lower for w in materials[tag]) for tag in (m1 & (f1 | f2)))
                t2_specified = any(any(w in text_lower for w in materials[tag]) for tag in (m2 & (f1 | f2)))
                if t1_specified and not t2_specified:
                    return False, ""
                if t2_specified and not t1_specified:
                    return False, ""
                return True, desc

        # E. Sizing / Diameter Conflict for Same Material (e.g., steel tubes <=150 mm vs >150 mm)
        if ("1239" in s1 and "3589" in s2) or ("3589" in s1 and "1239" in s2):
            return True, "Pipe Nominal Diameter (Up to 150 mm [IS 1239] vs Above 150 mm [IS 3589])"

        # F. Voltage Grade Conflict for Cable Product Specifications
        is_lt1 = any(v in comb1 for v in ["1100 v", "1.1 kv", "part 1", "low voltage", "lt "])
        is_ht1 = any(v in comb1 for v in ["11 kv", "33 kv", "part 2", "medium voltage", "high voltage", "ht "])
        is_lt2 = any(v in comb2 for v in ["1100 v", "1.1 kv", "part 1", "low voltage", "lt "])
        is_ht2 = any(v in comb2 for v in ["11 kv", "33 kv", "part 2", "medium voltage", "high voltage", "ht "])
        if not is_code_of_practice(s1, t1) and not is_code_of_practice(s2, t2):
            if (is_lt1 and is_ht2 and not is_ht1) or (is_ht1 and is_lt2 and not is_lt1):
                if "cable" in comb1 and "cable" in comb2:
                    return True, "Voltage Grade (Low Voltage / 1.1 kV vs Medium/High Voltage / 11-33 kV)"

        return False, ""

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
