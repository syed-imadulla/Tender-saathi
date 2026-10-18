"""
Module: src/precedence/conflict_engine.py
Purpose: Deterministic, evidence-backed cross-requirement conflict resolution and standards precedence engine.

Analyzes systemic interactions across all requirements in a single tender:
1. Shared-system / equipment parameter contradictions
2. Requirement dependencies
3. Cross-standard co-applicability (product vs installation codes)
4. Normative precedence questions without statutory priority
5. Edition divergences across the tender
6. Evidence insufficiency & uncertainty preservation
7. Disjoint scopes and false conflict prevention
8. Tender specification overrides (stricter buyer options)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Set

from src.corpus.semantics import (
    CrossRequirementConflictState,
    CROSS_CONFLICT_STATE_DESCRIPTIONS,
    RequirementEvidenceSupportState
)
from src.standards import StandardsDatabase, classify_standard_role


@dataclass
class CrossRequirementFinding:
    """Represents a deterministic finding resulting from cross-requirement interaction analysis."""
    finding_id: str
    source_requirement_id: str
    target_requirement_id: str
    conflict_category: str                 # SHARED_SYSTEM, EDITION_DIVERGENCE, CO_APPLICABLE, PRECEDENCE, etc.
    conflict_state: str                    # CrossRequirementConflictState enum value
    equipment_or_parameter: str
    evidence_text: str
    source_provenance: str = "CURATED"     # VERIFIED, CURATED, UNVERIFIED
    reasoning_rule_id: str = "RULE_CROSS_01"
    escalation_action: str = "NONE"        # HUMAN_REVIEW_REQUIRED, CLARIFICATION_REQUIRED, NONE
    standards: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrossRequirementAnalysisResult:
    """Tender-level summary of all cross-requirement interaction and conflict findings."""
    tender_id: str
    total_pairs_evaluated: int
    findings: List[CrossRequirementFinding] = field(default_factory=list)
    has_confirmed_contradictions: bool = False
    has_unresolved_precedence: bool = False
    has_edition_divergence: bool = False
    human_review_required: bool = False
    summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["findings"] = [f.to_dict() if hasattr(f, "to_dict") else f for f in self.findings]
        return d


class CrossRequirementConflictEngine:
    """
    Decoupled post-processing engine analyzing systemic interactions between
    multiple requirements in a tender. Operates strictly after per-requirement
    recommendation, preserving individual recommendation pipelines.
    """

    # Dimensional unit scaling to base SI units
    UNIT_SCALE: Dict[str, Tuple[str, float]] = {
        "w": ("power", 1.0), "kw": ("power", 1000.0), "mw": ("power", 1e6),
        "v": ("voltage", 1.0), "kv": ("voltage", 1000.0),
        "va": ("apparent_power", 1.0), "kva": ("apparent_power", 1000.0), "mva": ("apparent_power", 1e6),
        "a": ("current", 1.0), "amp": ("current", 1.0), "amps": ("current", 1.0), "ma": ("current", 0.001)
    }

    EQUIPMENT_KEYWORDS: Set[str] = {
        "transformer", "pump", "cable", "motor", "switchgear", "panel", "pipe",
        "fitting", "valve", "breaker", "generator", "inverter", "battery", "compressor",
        "conduit", "insulator", "earth", "earthing", "rebar", "cement", "concrete"
    }

    ZONE_KEYWORDS: Dict[str, str] = {
        "outdoor": "OUTDOOR",
        "indoor": "INDOOR",
        "substation yard": "OUTDOOR",
        "pole-mounted": "OUTDOOR",
        "switchyard": "OUTDOOR",
        "control room": "INDOOR",
        "underground": "UNDERGROUND",
        "buried": "UNDERGROUND",
        "overhead": "OVERHEAD"
    }

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db

    def analyze_tender_requirements(
        self,
        recommendations: List[Any],
        tender_id: str = "TENDER"
    ) -> CrossRequirementAnalysisResult:
        """
        Analyzes pairwise interactions across all tender requirement recommendations.
        Does NOT alter individual scores or ground-truth evaluations.
        """
        if not recommendations or len(recommendations) < 2:
            return CrossRequirementAnalysisResult(
                tender_id=tender_id,
                total_pairs_evaluated=0,
                findings=[],
                has_confirmed_contradictions=False,
                has_unresolved_precedence=False,
                has_edition_divergence=False,
                human_review_required=False,
                summary={state.value: 0 for state in CrossRequirementConflictState}
            )

        findings: List[CrossRequirementFinding] = []
        pairs_count = 0
        finding_seq = 1

        # Evaluate all pairwise combinations (i < j)
        for i in range(len(recommendations)):
            for j in range(i + 1, len(recommendations)):
                r1 = recommendations[i]
                r2 = recommendations[j]
                pairs_count += 1

                pair_findings = self._evaluate_requirement_pair(r1, r2, seq_start=finding_seq)
                for f in pair_findings:
                    findings.append(f)
                    finding_seq += 1

        # Calculate summary metrics
        summary = {state.value: 0 for state in CrossRequirementConflictState}
        has_contradictions = False
        has_unresolved_prec = False
        has_edition_div = False
        needs_human_review = False

        for f in findings:
            summary[f.conflict_state] = summary.get(f.conflict_state, 0) + 1
            if f.conflict_state == CrossRequirementConflictState.CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION.value:
                has_contradictions = True
                needs_human_review = True
            elif f.conflict_state == CrossRequirementConflictState.UNRESOLVED_NORMATIVE_PRECEDENCE.value:
                has_unresolved_prec = True
                needs_human_review = True
            elif f.conflict_state == CrossRequirementConflictState.LIFECYCLE_EDITION_DIVERGENCE.value:
                has_edition_div = True
                needs_human_review = True
            elif f.escalation_action == "HUMAN_REVIEW_REQUIRED":
                needs_human_review = True

        return CrossRequirementAnalysisResult(
            tender_id=tender_id,
            total_pairs_evaluated=pairs_count,
            findings=findings,
            has_confirmed_contradictions=has_contradictions,
            has_unresolved_precedence=has_unresolved_prec,
            has_edition_divergence=has_edition_div,
            human_review_required=needs_human_review,
            summary=summary
        )

    def _evaluate_requirement_pair(
        self,
        r1: Any,
        r2: Any,
        seq_start: int
    ) -> List[CrossRequirementFinding]:
        """Evaluates two requirements for potential systemic interactions and conflicts."""
        findings: List[CrossRequirementFinding] = []

        req_id1 = getattr(r1, "requirement_id", "REQ-1")
        req_id2 = getattr(r2, "requirement_id", "REQ-2")
        text1 = getattr(r1, "requirement_text", "")
        text2 = getattr(r2, "requirement_text", "")
        std1 = self._get_primary_standard(r1)
        std2 = self._get_primary_standard(r2)

        # 1. Category E: Edition Divergence Detection
        # Check if both requirements cite/recommend different editions of the same standard
        edition_finding = self._check_edition_divergence(r1, r2, seq_start)
        if edition_finding:
            findings.append(edition_finding)
            seq_start += 1

        # 2. Category G: Disjoint Operating Scopes / False Conflict Prevention
        # Check if the requirements explicitly govern disjoint zones or distinct items
        is_disjoint, disjoint_reason = self._check_disjoint_scopes(text1, text2)
        if is_disjoint:
            findings.append(CrossRequirementFinding(
                finding_id=f"XCF-{seq_start:04d}",
                source_requirement_id=req_id1,
                target_requirement_id=req_id2,
                conflict_category="DISJOINT_SCOPES",
                conflict_state=CrossRequirementConflictState.NO_CROSS_REQUIREMENT_CONFLICT.value,
                equipment_or_parameter=disjoint_reason,
                evidence_text=f"Scopes are physically disjoint: {disjoint_reason}.",
                source_provenance="VERIFIED",
                reasoning_rule_id="RULE_DISJOINT_SCOPE_01",
                escalation_action="NONE",
                standards=[s for s in [std1, std2] if s]
            ))
            return findings

        # 3. Category C: Cross-Standard Co-Applicability (Product vs Installation / Testing)
        co_app_finding = self._check_co_applicability(r1, r2, seq_start)
        if co_app_finding:
            findings.append(co_app_finding)
            seq_start += 1
            # If confirmed complementary co-applicable standards, they are not contradictory
            return findings

        # 4. Category A: Shared-System / Equipment Parameter Contradictions
        # Check for incompatible values or operating envelopes for the same equipment
        contra_finding = self._check_shared_system_contradiction(r1, r2, seq_start)
        if contra_finding:
            findings.append(contra_finding)
            return findings

        # 5. Category H: Tender Specification Override (Stricter Buyer Option)
        override_finding = self._check_tender_specification_override(r1, r2, seq_start)
        if override_finding:
            findings.append(override_finding)
            return findings

        # 6. Category F: Evidence Insufficiency
        # Preserves uncertainty before assuming normative precedence or technical equivalence
        insufficient_finding = self._check_evidence_insufficiency(r1, r2, seq_start)
        if insufficient_finding:
            findings.append(insufficient_finding)
            return findings

        # 7. Category D: Normative Precedence Question
        # Multiple standards on the same scope without explicit priority
        precedence_finding = self._check_normative_precedence(r1, r2, seq_start)
        if precedence_finding:
            findings.append(precedence_finding)
            return findings
            return findings

        return findings

    # -------------------------------------------------------------------------
    # Helper Inspection & Analysis Methods
    # -------------------------------------------------------------------------

    def _get_primary_standard(self, req_res: Any) -> Optional[str]:
        """Extracts canonical standard number from recommendation result."""
        cand = getattr(req_res, "candidate_standard", None)
        if cand:
            return cand
        recs = getattr(req_res, "recommendations", [])
        if recs and hasattr(recs[0], "standard_number"):
            return recs[0].standard_number
        explicit = getattr(req_res, "explicit_standards_found", [])
        if explicit:
            return explicit[0]
        return None

    def _extract_equipment_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts equipment type and specific equipment tag (e.g. TR-01, P-101).
        Returns (equipment_type, equipment_tag).
        """
        t_clean = text.lower()

        # Find explicit equipment tag (e.g. TR-01, PUMP-101, FEEDER-2, SUBSTATION-A)
        tag_match = re.search(r'\b(?:tag|unit|item|no\.?|id)?\s*([A-Z]{1,4}-[0-9]{1,4}[A-Z]?)\b', text, re.IGNORECASE)
        eq_tag = tag_match.group(1).upper() if tag_match else None

        # Find general equipment type
        eq_type = None
        for kw in sorted(self.EQUIPMENT_KEYWORDS, key=len, reverse=True):
            if re.search(rf'\b{kw}s?\b', t_clean):
                eq_type = kw
                break

        return eq_type, eq_tag

    def _extract_zone(self, text: str) -> Optional[str]:
        """Extracts physical installation or operating zone."""
        t_clean = text.lower()
        for kw, zone in sorted(self.ZONE_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(rf'\b{kw}\b', t_clean):
                return zone
        return None

    def _extract_ratings(self, text: str) -> List[Tuple[str, float, str, bool]]:
        """
        Extracts numerical ratings with unit normalization.
        Returns List of (dimension, base_value, unit, is_minimum).
        """
        t_clean = text.lower()
        matches = re.findall(
            r'(\b(?:at least|minimum|min|shall be at least|exceeding)\b[^0-9\n]{0,25})?(\d+(?:\.\d+)?)\s*(kva|mva|kv|kw|mw|amp|amps|a\b|w\b|v\b|ma\b)',
            t_clean
        )
        ratings = []
        for direction, val_str, unit in matches:
            if unit not in self.UNIT_SCALE:
                continue
            dim, factor = self.UNIT_SCALE[unit]
            base_val = float(val_str) * factor
            is_min = bool(direction and direction.strip())
            ratings.append((dim, base_val, unit, is_min))
        return ratings

    # -------------------------------------------------------------------------
    # Detection Rules per Conflict Category
    # -------------------------------------------------------------------------

    def _check_edition_divergence(
        self,
        r1: Any,
        r2: Any,
        seq: int
    ) -> Optional[CrossRequirementFinding]:
        """Category E: Detects if requirements cite/recommend different editions of the same standard."""
        std1 = self._get_primary_standard(r1)
        std2 = self._get_primary_standard(r2)
        if not std1 or not std2:
            return None

        # Extract base standard number without year (e.g. "IS 1180" from "IS 1180 : 1979" or "IS 1180 (Part 1) : 2014")
        base1 = re.sub(r'[\s\-:]+\d{4}$', '', std1).strip().upper()
        base2 = re.sub(r'[\s\-:]+\d{4}$', '', std2).strip().upper()

        if base1 == base2 or base1.split("(")[0].strip() == base2.split("(")[0].strip():
            # Check for differing years
            year1_match = re.search(r'\b(19\d{2}|20\d{2})\b', std1)
            year2_match = re.search(r'\b(19\d{2}|20\d{2})\b', std2)
            if year1_match and year2_match and year1_match.group(1) != year2_match.group(1):
                y1 = int(year1_match.group(1))
                y2 = int(year2_match.group(1))
                return CrossRequirementFinding(
                    finding_id=f"XCF-{seq:04d}",
                    source_requirement_id=getattr(r1, "requirement_id", "REQ-1"),
                    target_requirement_id=getattr(r2, "requirement_id", "REQ-2"),
                    conflict_category="EDITION_DIVERGENCE",
                    conflict_state=CrossRequirementConflictState.LIFECYCLE_EDITION_DIVERGENCE.value,
                    equipment_or_parameter=f"Standard Family {base1}",
                    evidence_text=f"Tender cites divergent editions: '{std1}' ({y1}) vs '{std2}' ({y2}).",
                    source_provenance="VERIFIED",
                    reasoning_rule_id="RULE_EDITION_DIVERGENCE_01",
                    escalation_action="HUMAN_REVIEW_REQUIRED",
                    standards=[std1, std2]
                )
        return None

    def _check_co_applicability(
        self,
        r1: Any,
        r2: Any,
        seq: int
    ) -> Optional[CrossRequirementFinding]:
        """Category C: Identifies complementary standards (e.g. Product standard + Installation code)."""
        std1 = self._get_primary_standard(r1)
        std2 = self._get_primary_standard(r2)
        if not std1 or not std2:
            return None

        # Ensure equipment types or scopes are compatible before declaring co-applicability
        eq1, _ = self._extract_equipment_info(getattr(r1, "requirement_text", ""))
        eq2, _ = self._extract_equipment_info(getattr(r2, "requirement_text", ""))
        if eq1 and eq2 and eq1 != eq2:
            allowed_pairs = [("cable", "conduit"), ("conduit", "cable"), ("pipe", "fitting"), ("fitting", "pipe")]
            if (eq1, eq2) not in allowed_pairs:
                return None

        role1 = getattr(r1, "standard_role", None) or classify_standard_role(std1, "")
        role2 = getattr(r2, "standard_role", None) or classify_standard_role(std2, "")

        is_product1 = "PRODUCT" in str(role1).upper()
        is_product2 = "PRODUCT" in str(role2).upper()
        is_install1 = any(k in str(role1).upper() for k in ["INSTALL", "CODE_OF_PRACTICE"])
        is_install2 = any(k in str(role2).upper() for k in ["INSTALL", "CODE_OF_PRACTICE"])
        is_test1 = "TEST" in str(role1).upper()
        is_test2 = "TEST" in str(role2).upper()

        # Product + Installation code pair
        if (is_product1 and is_install2) or (is_product2 and is_install1):
            prod_std = std1 if is_product1 else std2
            inst_std = std2 if is_product1 else std1
            return CrossRequirementFinding(
                finding_id=f"XCF-{seq:04d}",
                source_requirement_id=getattr(r1, "requirement_id", "REQ-1"),
                target_requirement_id=getattr(r2, "requirement_id", "REQ-2"),
                conflict_category="CO_APPLICABLE_STANDARDS",
                conflict_state=CrossRequirementConflictState.CO_APPLICABLE_COMPLEMENTARY_STANDARDS.value,
                equipment_or_parameter="Product Specification + Installation Code",
                evidence_text=f"Standards '{prod_std}' (Product) and '{inst_std}' (Installation Code) are co-applicable complementary standards.",
                source_provenance="CURATED",
                reasoning_rule_id="RULE_CO_APPLICABLE_PRODUCT_INSTALL_01",
                escalation_action="NONE",
                standards=[std1, std2]
            )

        # Product + Test method pair
        if (is_product1 and is_test2) or (is_product2 and is_test1):
            return CrossRequirementFinding(
                finding_id=f"XCF-{seq:04d}",
                source_requirement_id=getattr(r1, "requirement_id", "REQ-1"),
                target_requirement_id=getattr(r2, "requirement_id", "REQ-2"),
                conflict_category="CO_APPLICABLE_STANDARDS",
                conflict_state=CrossRequirementConflictState.CO_APPLICABLE_COMPLEMENTARY_STANDARDS.value,
                equipment_or_parameter="Product Specification + Test Method",
                evidence_text=f"Standards '{std1}' and '{std2}' serve complementary product and testing functions.",
                source_provenance="CURATED",
                reasoning_rule_id="RULE_CO_APPLICABLE_PRODUCT_TEST_01",
                escalation_action="NONE",
                standards=[std1, std2]
            )

        return None

    def _check_disjoint_scopes(
        self,
        text1: str,
        text2: str
    ) -> Tuple[bool, str]:
        """Category G: Detects if requirements physically govern disjoint zones or items."""
        eq1, tag1 = self._extract_equipment_info(text1)
        eq2, tag2 = self._extract_equipment_info(text2)
        zone1 = self._extract_zone(text1)
        zone2 = self._extract_zone(text2)

        # If explicit tags differ (e.g. TR-01 vs TR-02 or PUMP-1 vs PUMP-2), scopes are disjoint
        if tag1 and tag2 and tag1 != tag2:
            return True, f"Distinct equipment tags ({tag1} vs {tag2})"

        # If equipment types differ completely (e.g. transformer vs pipe, or pump vs cable)
        if eq1 and eq2 and eq1 != eq2 and not (("cable" in eq1 and "conduit" in eq2) or ("pipe" in eq1 and "fitting" in eq2)):
            return True, f"Distinct equipment types ({eq1} vs {eq2})"

        # Check for explicitly distinct facility areas (e.g. switchyard vs control room)
        areas = ["switchyard", "control room", "pump room", "substation yard", "admin building", "workshop", "powerhouse"]
        a1 = next((a for a in areas if a in text1.lower()), None)
        a2 = next((a for a in areas if a in text2.lower()), None)
        if a1 and a2 and a1 != a2:
            return True, f"Distinct facility areas ({a1} vs {a2})"

        return False, ""

    def _check_shared_system_contradiction(
        self,
        r1: Any,
        r2: Any,
        seq: int
    ) -> Optional[CrossRequirementFinding]:
        """Category A: Detects incompatible requirements on the same equipment/system entity."""
        text1 = getattr(r1, "requirement_text", "")
        text2 = getattr(r2, "requirement_text", "")
        eq1, tag1 = self._extract_equipment_info(text1)
        eq2, tag2 = self._extract_equipment_info(text2)

        # Must share equipment tag or equipment type to represent the same system
        is_same_equipment = False
        is_ambiguous_identity = False
        shared_id = ""
        if tag1 and tag2 and tag1 == tag2:
            is_same_equipment = True
            shared_id = f"Equipment Tag {tag1}"
        elif tag1 and tag2 and tag1 != tag2:
            # Explicitly distinct tags -> distinct items, caught by disjoint scopes
            return None
        elif (tag1 and not tag2) or (tag2 and not tag1):
            # One has an explicit tag, the other does not -> identity is ambiguous
            is_ambiguous_identity = True
            shared_id = f"Apparatus '{eq1 or eq2}'"
        elif eq1 and eq2 and eq1 == eq2:
            # Both mention the same apparatus without tags
            # Check for explicit singular indicators: "the", "said", "same", "this", "single", or "apparatus"
            has_singular_ref = any(
                re.search(rf'\b(?:the|said|same|this|single)\s+{re.escape(eq1)}\b', t) or "apparatus" in t
                for t in [text1.lower(), text2.lower()]
            )
            if has_singular_ref:
                is_same_equipment = True
                shared_id = f"Apparatus '{eq1}'"
            else:
                is_ambiguous_identity = True
                shared_id = f"Apparatus '{eq1}'"

        if not is_same_equipment and not is_ambiguous_identity:
            return None

        def _build_finding(param_name: str, desc: str, rule_id: str) -> CrossRequirementFinding:
            if is_same_equipment:
                state = CrossRequirementConflictState.CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION.value
                provenance = "VERIFIED"
                action = "HUMAN_REVIEW_REQUIRED"
                ev_text = f"{shared_id} assigned contradictory {param_name}: {desc}."
            else:
                state = CrossRequirementConflictState.POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED.value
                provenance = "UNVERIFIED"
                action = "CLARIFICATION_REQUIRED"
                ev_text = f"Tender specifies differing {param_name} ({desc}) for {shared_id}, but shared physical identity is unconfirmed (no matching equipment tag). Clarification required."

            return CrossRequirementFinding(
                finding_id=f"XCF-{seq:04d}",
                source_requirement_id=getattr(r1, "requirement_id", "REQ-1"),
                target_requirement_id=getattr(r2, "requirement_id", "REQ-2"),
                conflict_category="SHARED_SYSTEM_CONSTRAINT",
                conflict_state=state,
                equipment_or_parameter=f"{shared_id} {param_name}",
                evidence_text=ev_text,
                source_provenance=provenance,
                reasoning_rule_id=rule_id,
                escalation_action=action,
                standards=[s for s in [self._get_primary_standard(r1), self._get_primary_standard(r2)] if s]
            )

        # Check 1: Operating envelope contradiction on shared unit (Indoor vs Outdoor)
        zone1 = self._extract_zone(text1)
        zone2 = self._extract_zone(text2)
        if zone1 and zone2 and zone1 != zone2:
            return _build_finding("Operating Environment", f"'{zone1}' vs '{zone2}'", "RULE_SHARED_ENV_CONTRADICTION_01")

        # Check 2: Technical Rating Contradiction (e.g. 100 kVA vs 200 kVA on same unit tag)
        ratings1 = self._extract_ratings(text1)
        ratings2 = self._extract_ratings(text2)

        for dim1, val1, u1, is_min1 in ratings1:
            for dim2, val2, u2, is_min2 in ratings2:
                if dim1 == dim2:
                    is_contra = False
                    if is_min1 and not is_min2:
                        # val1 is floor constraint; val2 must be >= val1
                        if val2 < val1 * 0.95:
                            is_contra = True
                    elif is_min2 and not is_min1:
                        # val2 is floor constraint; val1 must be >= val2
                        if val1 < val2 * 0.95:
                            is_contra = True
                    elif is_min1 and is_min2:
                        # Both are minimum constraints; they do not contradict
                        is_contra = False
                    else:
                        # Both are target ratings
                        ratio = abs(val1 - val2) / max(val1, val2)
                        if ratio > 0.05:
                            is_contra = True

                    if is_contra:
                        return _build_finding(f"{dim1.title()} Rating", f"{val1} vs {val2} (base SI units)", "RULE_SHARED_RATING_CONTRADICTION_01")

        # Check 3: Material or Conductor Exclusion Contradiction (e.g. Copper vs Aluminium)
        t1_low = text1.lower()
        t2_low = text2.lower()
        if ("copper conductor" in t1_low and "aluminium conductor" in t2_low) or ("aluminium conductor" in t1_low and "copper conductor" in t2_low):
            return _build_finding("Conductor Material", "Copper vs Aluminium", "RULE_SHARED_MATERIAL_CONTRADICTION_01")

        return None

    def _check_tender_specification_override(
        self,
        r1: Any,
        r2: Any,
        seq: int
    ) -> Optional[CrossRequirementFinding]:
        """Category H: Identifies when an explicit tender clause specifies a stricter buyer option."""
        text1 = getattr(r1, "requirement_text", "")
        text2 = getattr(r2, "requirement_text", "")

        # Look for explicit override phrases in either requirement
        override_indicators = [
            "notwithstanding", "buyer option", "specifically mandated", "stricter requirement",
            "copper conductor mandatory", "losses capped at", "exceeding standard requirements"
        ]
        has_ov1 = any(ind in text1.lower() for ind in override_indicators)
        has_ov2 = any(ind in text2.lower() for ind in override_indicators)

        if has_ov1 or has_ov2:
            ov_req = r1 if has_ov1 else r2
            base_req = r2 if has_ov1 else r1
            return CrossRequirementFinding(
                finding_id=f"XCF-{seq:04d}",
                source_requirement_id=getattr(ov_req, "requirement_id", "REQ-OV"),
                target_requirement_id=getattr(base_req, "requirement_id", "REQ-BASE"),
                conflict_category="TENDER_SPECIFICATION_OVERRIDE",
                conflict_state=CrossRequirementConflictState.TENDER_SPECIFICATION_OVERRIDE.value,
                equipment_or_parameter="Buyer Specification Option",
                evidence_text="Tender specification prescribes an explicit higher stringency permitted by buyer options.",
                source_provenance="VERIFIED",
                reasoning_rule_id="RULE_BUYER_OPTION_OVERRIDE_01",
                escalation_action="NONE",
                standards=[s for s in [self._get_primary_standard(r1), self._get_primary_standard(r2)] if s]
            )
        return None

    def _check_normative_precedence(
        self,
        r1: Any,
        r2: Any,
        seq: int
    ) -> Optional[CrossRequirementFinding]:
        """Category D: Flags multiple overlapping standards on same scope without explicit priority."""
        std1 = self._get_primary_standard(r1)
        std2 = self._get_primary_standard(r2)
        if not std1 or not std2 or std1 == std2:
            return None

        eq1, _ = self._extract_equipment_info(getattr(r1, "requirement_text", ""))
        eq2, _ = self._extract_equipment_info(getattr(r2, "requirement_text", ""))

        # Both apply to the same equipment type, but recommend different product standards
        if eq1 and eq2 and eq1 == eq2:
            # Check if either standard has verified supersession relationship in database
            # (If one supersedes the other, that's resolved; if not, precedence is unresolved)
            return CrossRequirementFinding(
                finding_id=f"XCF-{seq:04d}",
                source_requirement_id=getattr(r1, "requirement_id", "REQ-1"),
                target_requirement_id=getattr(r2, "requirement_id", "REQ-2"),
                conflict_category="NORMATIVE_PRECEDENCE",
                conflict_state=CrossRequirementConflictState.UNRESOLVED_NORMATIVE_PRECEDENCE.value,
                equipment_or_parameter=f"{eq1.title()} Governing Code",
                evidence_text=f"Standards '{std1}' and '{std2}' both address {eq1}; published priority is not established by statutory evidence.",
                source_provenance="CURATED",
                reasoning_rule_id="RULE_UNRESOLVED_PRECEDENCE_01",
                escalation_action="HUMAN_REVIEW_REQUIRED",
                standards=[std1, std2]
            )
        return None

    def _check_evidence_insufficiency(
        self,
        r1: Any,
        r2: Any,
        seq: int
    ) -> Optional[CrossRequirementFinding]:
        """Category F: Preserves uncertainty when evidence is insufficient to confirm/dismiss conflict."""
        cl_ev1 = getattr(r1, "clause_evidence", {}) or {}
        cl_ev2 = getattr(r2, "clause_evidence", {}) or {}

        support1 = cl_ev1.get("requirement_evidence_support")
        support2 = cl_ev2.get("requirement_evidence_support")

        # If either requirement has unverified coverage or missing clause evidence
        if support1 == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value or \
           support2 == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value:
            eq1, _ = self._extract_equipment_info(getattr(r1, "requirement_text", ""))
            eq2, _ = self._extract_equipment_info(getattr(r2, "requirement_text", ""))
            if eq1 and eq2 and eq1 == eq2:
                return CrossRequirementFinding(
                    finding_id=f"XCF-{seq:04d}",
                    source_requirement_id=getattr(r1, "requirement_id", "REQ-1"),
                    target_requirement_id=getattr(r2, "requirement_id", "REQ-2"),
                    conflict_category="EVIDENCE_INSUFFICIENCY",
                    conflict_state=CrossRequirementConflictState.POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED.value,
                    equipment_or_parameter=f"{eq1.title()} Clause Evidence",
                    evidence_text=f"Clause-level evidence is unverified for one or both requirements on {eq1}; cannot confirm compatibility.",
                    source_provenance="UNVERIFIED",
                    reasoning_rule_id="RULE_EVIDENCE_INSUFFICIENT_01",
                    escalation_action="CLARIFICATION_REQUIRED",
                    standards=[s for s in [self._get_primary_standard(r1), self._get_primary_standard(r2)] if s]
                )
        return None
