"""
Module: src/applicability.py
Purpose: Applicability + Abstention Gate for TenderSaathi.

Core Principle:
"AI interprets. Retrieval finds candidates. Evidence validates applicability. Humans decide."

This gate ensures TenderSaathi does NOT recommend an unrelated Indian Standard
merely because it is the highest-scoring candidate from the catalogue.

Evaluates candidates on:
1. Domain Match (prevents cross-domain hallucinations e.g. crane rail vs valve)
2. Product / Equipment Match (ensures candidate actually covers procured item)
3. Scope Match & Technical Grounding (substantive technical scope grounding, not generic stopwords)
4. Application Match (application environment and service compatibility)
5. Evidence Support (verifies applicability evidence, not just standard existence)
6. Hard Conflict Detection (strictly overrides high retrieval scores)
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple

from src.search import SearchResult
from src.decompose import RequirementComponent


class ApplicabilityDecision(str, Enum):
    APPLICABLE = "APPLICABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class ApplicabilityResult:
    standard_number: str
    title: str
    applicable: bool                      # True if APPLICABLE or REVIEW_REQUIRED (not rejected)
    decision: str                         # APPLICABLE, REVIEW_REQUIRED, NOT_APPLICABLE
    applicability_score: float            # 0.0 to 1.0 composite applicability score
    domain_match: bool                    # Does standard belong to same engineering domain?
    product_match: bool                   # Does standard cover the product/equipment being procured?
    scope_match: bool                     # Does authoritative standard scope support the requirement?
    application_match: bool               # Does the use case/application environment match?
    evidence_support: bool                # Is there genuine domain/technical evidence (not mere stopwords)?
    conflict_flags: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_number": self.standard_number,
            "title": self.title,
            "applicable": self.applicable,
            "decision": self.decision,
            "applicability_score": round(self.applicability_score, 3),
            "domain_match": self.domain_match,
            "product_match": self.product_match,
            "scope_match": self.scope_match,
            "application_match": self.application_match,
            "evidence_support": self.evidence_support,
            "conflict_flags": self.conflict_flags,
            "reasons": self.reasons,
            "rejection_reasons": self.rejection_reasons
        }


# ---------------------------------------------------------------------------
# Generic non-technical stopwords
# These must NEVER be counted as technical scope overlap!
# ---------------------------------------------------------------------------
GENERIC_STOPWORDS: Set[str] = {
    "and", "for", "the", "with", "including", "allied", "works", "replacement",
    "supply", "installation", "system", "systems", "dock", "area", "berth",
    "service", "services", "requirements", "specification", "specifications",
    "test", "testing", "shall", "standard", "code", "practice", "general",
    "part", "section", "clause", "type", "types", "method", "methods",
    "materials", "procurement", "work", "grade", "conforming", "conform",
    "repair", "overhaul", "maintenance", "operation", "at", "in", "on", "of",
    "to", "by", "from", "an", "as", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "can", "could", "should", "would",
    "may", "might", "must", "new", "old", "used", "nos", "no", "berths", "tender",
    "item", "items", "etc", "such", "than", "or", "not", "only", "both", "all", "without"
}


# ---------------------------------------------------------------------------
# Technical Domain Profiles
# ---------------------------------------------------------------------------
DOMAINS = {
    "CRANES_AND_RAIL": {
        "keywords": {
            "crane", "cranes", "rail", "rails", "track", "tracks", "rmqc",
            "quay", "gantry", "hoist", "hoists", "trolley", "locomotive",
            "rolling stock", "wagon", "berth crane", "container crane", "derrick"
        },
        "description": "Heavy Machinery / Cranes & Rail Track Infrastructure"
    },
    "VALVES_AND_FLOW": {
        "keywords": {
            "valve", "valves", "gate valve", "sluice valve", "globe valve",
            "check valve", "ball valve", "butterfly valve", "plug valve",
            "cock", "bonnet", "bolted bonnet", "flow control", "flanged valve"
        },
        "description": "Valves & Flow Control Equipment"
    },
    "PIPES_AND_FITTINGS": {
        "keywords": {
            "pipe", "pipes", "piping", "fitting", "fittings", "tube", "tubes",
            "cpvc", "upvc", "pvc", "hdpe", "ductile iron", "cast iron pipe",
            "gi pipe", "plumbing", "water supply", "potable water distribution",
            "drainage", "sewerage pipe"
        },
        "description": "Pipes, Tubes & Plumbing Distribution"
    },
    "ELECTRICAL_AND_POWER": {
        "keywords": {
            "cable", "cables", "conductor", "conductors", "wire", "wires",
            "transformer", "switchgear", "vfd", "motor", "inverter",
            "substation", "circuit breaker", "panel", "voltage", "1.1 kv",
            "3.3 kv", "11 kv", "33 kv", "ht cable", "lt cable", "power distribution"
        },
        "description": "Electrical Equipment & Power Distribution"
    },
    "PUMPS_AND_ROTATING": {
        "keywords": {
            "pump", "pumps", "pumping", "submersible", "slurry pump",
            "centrifugal pump", "impeller", "sump pump", "water pump", "dewatering"
        },
        "description": "Pumps & Pumping Machinery"
    },
    "CIVIL_AND_STRUCTURAL": {
        "keywords": {
            "structural steel", "truss", "trusses", "girder", "rebar",
            "cement", "concrete", "rcc", "tile", "tiles", "ceramic tile",
            "masonry", "brick", "asphalt", "roofing", "bituminous", "flooring"
        },
        "description": "Civil & Structural Engineering"
    },
    "FOOD_AND_AGRICULTURE": {
        "keywords": {
            "food", "dairy", "milk", "grain", "agriculture", "agricultural",
            "pesticide", "irrigation", "agro", "hygiene", "haccp", "canteen", "catering"
        },
        "description": "Food Products, Hygiene & Agriculture"
    },
    "FIRE_SAFETY": {
        "keywords": {
            "fire extinguisher", "sprinkler", "fire hydrant", "fire alarm",
            "smoke detector", "fire fighting", "fire hose"
        },
        "description": "Fire Protection & Safety"
    },
    "THERMAL_INSULATION": {
        "keywords": {
            "insulation", "thermal insulation", "mineral wool", "calcium silicate",
            "lagging", "refractory"
        },
        "description": "Thermal & Acoustic Insulation Materials"
    },
    "AEROSPACE_AND_DEFENSE": {
        "keywords": {
            "aerospace", "aircraft", "fuselage", "avionics", "supersonic",
            "spacecraft", "satellite", "prepreg", "flight", "rocket"
        },
        "description": "Aerospace, Defense & Advanced Flight Structures"
    }
}

# Conflict matrix between mutually exclusive domains for specific equipment procurements
DOMAIN_CONFLICTS = {
    ("CRANES_AND_RAIL", "VALVES_AND_FLOW"): "Requirement specifies crane rail track / cranes, but candidate standard covers industrial valves.",
    ("CRANES_AND_RAIL", "FOOD_AND_AGRICULTURE"): "Requirement specifies crane/rail machinery, but candidate standard covers food/agriculture.",
    ("CRANES_AND_RAIL", "PIPES_AND_FITTINGS"): "Requirement specifies crane rail machinery, but candidate standard covers pipes/plumbing.",
    ("CRANES_AND_RAIL", "THERMAL_INSULATION"): "Requirement specifies crane/rail machinery, but candidate standard covers thermal insulation.",
    ("ELECTRICAL_AND_POWER", "VALVES_AND_FLOW"): "Requirement specifies electrical/power equipment, but candidate standard covers valves.",
    ("ELECTRICAL_AND_POWER", "FOOD_AND_AGRICULTURE"): "Requirement specifies electrical equipment, but candidate standard covers food products.",
    ("PUMPS_AND_ROTATING", "CIVIL_AND_STRUCTURAL"): "Requirement specifies pumps/rotating machinery, but candidate standard covers civil/structural materials.",
    ("PUMPS_AND_ROTATING", "FOOD_AND_AGRICULTURE"): "Requirement specifies industrial pumps, but candidate standard covers food.",
    ("PUMPS_AND_ROTATING", "THERMAL_INSULATION"): "Requirement specifies pumps/rotating equipment, but candidate standard covers thermal insulation.",
    ("PUMPS_AND_ROTATING", "PIPES_AND_FITTINGS"): "Requirement specifies pumps/rotating machinery, but candidate standard covers pipes/fittings.",
    ("CIVIL_AND_STRUCTURAL", "VALVES_AND_FLOW"): "Requirement specifies structural/civil works, but candidate standard covers valves.",
    ("CIVIL_AND_STRUCTURAL", "PIPES_AND_FITTINGS"): "Requirement specifies structural/civil works, but candidate standard covers pipes/plumbing.",
    ("PIPES_AND_FITTINGS", "FOOD_AND_AGRICULTURE"): "Requirement specifies piping systems, but candidate standard covers food products.",
    ("AEROSPACE_AND_DEFENSE", "PIPES_AND_FITTINGS"): "Requirement specifies aerospace/aircraft structures, but candidate standard covers pipe flanges/plumbing.",
    ("AEROSPACE_AND_DEFENSE", "VALVES_AND_FLOW"): "Requirement specifies aerospace/aircraft structures, but candidate standard covers civil/plumbing valves.",
    ("AEROSPACE_AND_DEFENSE", "FOOD_AND_AGRICULTURE"): "Requirement specifies aerospace/aircraft structures, but candidate standard covers food/agriculture.",
    ("AEROSPACE_AND_DEFENSE", "TILES_AND_SURFACES"): "Requirement specifies aerospace/aircraft structures, but candidate standard covers ceramic tiles.",
    ("AEROSPACE_AND_DEFENSE", "CEMENT_AND_CONCRETE"): "Requirement specifies aerospace/aircraft structures, but candidate standard covers cement/concrete.",
}


class ApplicabilityGate:
    """
    Evaluates whether a candidate standard is genuinely applicable to a tender requirement.
    Enforces the Core Trust Rule:
    A high retrieval score (BM25, Semantic, Reranker) can NEVER override a strong technical conflict.
    """

    def __init__(
        self,
        applicability_threshold: Optional[float] = None,
        review_threshold: Optional[float] = None
    ):
        # Configurable thresholds via env vars or constructor
        self.applicability_threshold = applicability_threshold or float(
            os.environ.get("TENDERSAATHI_APPLICABILITY_THRESHOLD", "0.60")
        )
        self.review_threshold = review_threshold or float(
            os.environ.get("TENDERSAATHI_REVIEW_THRESHOLD", "0.35")
        )

    def _stem_word(self, w: str) -> str:
        """Rule-based English stemmer for technical vocabulary plurals and variations."""
        if len(w) <= 3:
            return w
        if w.endswith("ies") and len(w) > 4:
            return w[:-3] + "y"
        if w.endswith("es") and len(w) > 4 and w[-3] in "shxz":
            return w[:-2]
        if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            return w[:-1]
        return w

    def extract_technical_tokens(self, text: str) -> Set[str]:
        """Extracts meaningful technical stemmed words, excluding generic stopwords."""
        raw_words = re.findall(r'\b[a-zA-Z0-9_\-]{3,}\b', text.lower())
        tokens = set()
        for w in raw_words:
            if w not in GENERIC_STOPWORDS:
                tokens.add(w)
                stemmed = self._stem_word(w)
                if stemmed not in GENERIC_STOPWORDS:
                    tokens.add(stemmed)
        return tokens

    def detect_domains(self, text: str) -> List[str]:
        """Detects engineering domains present in text based on technical keywords."""
        t_low = text.lower()
        detected = []
        for d_key, d_info in DOMAINS.items():
            for kw in d_info["keywords"]:
                # Word boundary check for single words, substring for phrases
                if " " in kw:
                    if kw in t_low:
                        detected.append(d_key)
                        break
                else:
                    if re.search(rf'\b{re.escape(kw)}\b', t_low):
                        detected.append(d_key)
                        break
        return detected

    def evaluate_candidate(
        self,
        candidate: SearchResult,
        requirement_text: str,
        components: Optional[List[RequirementComponent]] = None,
        parsed_ai: Optional[Any] = None,
        is_explicitly_cited: bool = False
    ) -> ApplicabilityResult:
        """
        Evaluates a single candidate standard for applicability.
        Operates per-candidate, preserving multi-standard recommendations.
        """
        std_num = candidate.standard_number
        title = candidate.full_title
        scope = candidate.scope_summary or ""

        conflict_flags: List[str] = []
        reasons: List[str] = []
        rejection_reasons: List[str] = []

        # 1. Technical Tokens Extraction
        req_tech_tokens = self.extract_technical_tokens(requirement_text)
        cand_corpus = f"{title} {scope}"
        cand_tech_tokens = self.extract_technical_tokens(cand_corpus)

        # 2. Domain Identification
        req_domains = self.detect_domains(requirement_text)
        # Enrich domain detection with AI facets if available
        if parsed_ai and hasattr(parsed_ai, "equipment"):
            eq_text = " ".join(parsed_ai.equipment or [])
            req_domains.extend(self.detect_domains(eq_text))
        if parsed_ai and hasattr(parsed_ai, "application"):
            app_text = " ".join(parsed_ai.application or [])
            req_domains.extend(self.detect_domains(app_text))
        req_domains = list(set(req_domains))

        cand_domains = self.detect_domains(f"{title} {scope}")

        # 3. Check Domain Conflict
        # A conflict only occurs if candidate and requirement domains are DISJOINT (no shared domain)
        has_domain_conflict = False
        domain_conflict_desc = ""

        shared_domains = set(req_domains).intersection(set(cand_domains))
        if req_domains and cand_domains and not shared_domains:
            for rd in req_domains:
                for cd in cand_domains:
                    conflict_msg = DOMAIN_CONFLICTS.get((rd, cd)) or DOMAIN_CONFLICTS.get((cd, rd))
                    if conflict_msg:
                        has_domain_conflict = True
                        domain_conflict_desc = conflict_msg
                        conflict_flags.append(f"DOMAIN_CONFLICT: {rd} vs {cd}")
                        rejection_reasons.append(conflict_msg)
                        break
                if has_domain_conflict:
                    break

        domain_match = (
            not has_domain_conflict and
            (bool(shared_domains) or not req_domains or not cand_domains)
        )

        # 4. Product / Equipment Match
        product_match = False
        substantive_overlap = req_tech_tokens.intersection(cand_tech_tokens)

        # AI equipment alignment
        ai_equipment_tokens: Set[str] = set()
        if parsed_ai and hasattr(parsed_ai, "equipment"):
            for eq in (parsed_ai.equipment or []):
                ai_equipment_tokens.update(self.extract_technical_tokens(eq))

        if ai_equipment_tokens:
            eq_overlap = ai_equipment_tokens.intersection(cand_tech_tokens)
            if eq_overlap:
                product_match = True
                reasons.append(f"Standard covers requirement equipment: {', '.join(sorted(eq_overlap))}")
            elif substantive_overlap and not has_domain_conflict:
                # Coupled sub-component match (e.g. pump coupled with electric motor)
                product_match = True
                reasons.append(f"Technical token overlap found: {', '.join(sorted(substantive_overlap)[:4])}")
            else:
                product_match = False
                rejection_reasons.append(
                    f"Equipment mismatch: Requirement specifies '{', '.join(sorted(ai_equipment_tokens))}' which is not covered by standard '{title}'"
                )
        elif substantive_overlap:
            product_match = True
            reasons.append(f"Technical token overlap found: {', '.join(sorted(substantive_overlap)[:4])}")

        # 5. Scope Match & Technical Grounding
        # Substantive technical overlap between requirement and scope
        scope_match = len(substantive_overlap) > 0 and not has_domain_conflict
        if not scope_match:
            if not substantive_overlap:
                rejection_reasons.append("No substantive technical vocabulary overlap with standard scope (generic words only).")

        # 6. Application Match
        application_match = True
        req_text_low = requirement_text.lower()
        cand_corpus_low = cand_corpus.lower()

        # If application strongly conflicts with standard title/scope
        if "refinery" in cand_corpus_low and ("domestic" in req_text_low or "potable" in req_text_low):
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: industrial/petrochemical vs domestic water")
            rejection_reasons.append("Application conflict: Petrochemical standard applied to domestic potable installation.")

        # Specialized technologies outside standard catalogue scope
        if any(k in req_text_low for k in ["liquid sodium", "fast breeder", "liquid metal sodium"]) or ("sodium" in req_text_low and "coolant" in req_text_low):
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: nuclear liquid sodium coolant")
            rejection_reasons.append("Application conflict: General water/steam piping or standard pumps do not cover liquid metal sodium nuclear coolant circuits.")

        if ("subsea" in req_text_low and "umbilical" in req_text_low) or "dynamic umbilical" in req_text_low or "deep ocean" in req_text_low:
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: deep ocean subsea umbilical")
            rejection_reasons.append("Application conflict: Terrestrial building power cable standards do not cover deep ocean subsea dynamic electro-hydraulic umbilicals.")

        if "quantum dot" in req_text_low or ("optical film" in req_text_low and "television" in req_text_low):
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: display optical film")
            rejection_reasons.append("Application conflict: Agricultural, mechanical, or photography standards do not cover advanced television display optical film.")

        # Equipment scope gate: Adjustable speed electrical power drives (IS/IEC 61800) vs Switchgear assemblies
        is_cand_vfd = "61800" in std_num or "power drive" in cand_corpus_low
        has_vfd_kw = bool(re.search(r'\b(?:vfd|variable\s+frequency|variable\s+speed|power\s+drive|frequency\s+converter|inverter\s+drive|ac\s+drive|drive\s+panel)\b', req_text_low))
        is_swg_req = bool(re.search(r'\b(?:switchgear|controlgear)\b', req_text_low))
        if is_cand_vfd and is_swg_req and not has_vfd_kw:
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: power drive system vs switchgear assembly")
            rejection_reasons.append("Equipment mismatch: Standard covers adjustable speed power drive systems (VFD), but requirement specifies switchgear/controlgear assembly without power drive system.")

        # Product boundary gates (Section 10 critical safety tests):
        # 1. XLPE Cable Voltage Tier Gate: IS 7098 Part 1 (<= 1100 V) vs Part 2 (3.3 kV to 33 kV)
        is_7098 = "7098" in std_num
        if is_7098:
            has_mv_or_ht = bool(re.search(r'\b(?:11\s*kv|33\s*kv|3\.3\s*kv|6\.6\s*kv|22\s*kv|ht\s+cable|medium\s+voltage|high\s+voltage)\b', req_text_low))
            has_lv_or_lt = bool(re.search(r'\b(?:1\.1\s*kv|1100\s*v|lt\s+cable|low\s+voltage)\b', req_text_low))
            is_part_1 = "part 1" in std_num.lower() or "part-1" in std_num.lower() or "part 1" in cand_corpus_low
            is_part_2 = "part 2" in std_num.lower() or "part-2" in std_num.lower() or "part 2" in cand_corpus_low

            if is_part_1 and has_mv_or_ht and not has_lv_or_lt:
                application_match = False
                conflict_flags.append("VOLTAGE_CONFLICT: 11 kV / HT cable exceeds IS 7098 Part 1 maximum voltage rating (1.1 kV / 1100 V)")
                rejection_reasons.append("Voltage rating conflict: IS 7098 (Part 1) only covers working voltages up to and including 1100 V (1.1 kV). For medium/high voltage (e.g. 11 kV), applicable standard is IS 7098 (Part 2).")
            elif is_part_2 and has_lv_or_lt and not has_mv_or_ht:
                application_match = False
                conflict_flags.append("VOLTAGE_CONFLICT: LT / 1.1 kV cable is below IS 7098 Part 2 minimum voltage rating (3.3 kV)")
                rejection_reasons.append("Voltage rating conflict: IS 7098 (Part 2) covers voltages from 3.3 kV up to 33 kV. For low voltage / 1.1 kV, applicable standard is IS 7098 (Part 1).")

        # 2. Steel Reinforcement Process & Grade Gate: IS 432 (Mild steel) vs IS 1786 (High strength deformed / TMT)
        is_432 = "432" in std_num
        has_tmt_or_deformed = bool(re.search(r'\b(?:fe\s*500d?|fe\s*415|fe\s*550d?|fe\s*600|tmt|thermo\s*mechanically\s*treated|high\s+strength\s+deformed|deformed\s+bar|ctd)\b', req_text_low))
        if is_432 and has_tmt_or_deformed:
            application_match = False
            conflict_flags.append("GRADE_OR_PROCESS_CONFLICT: Fe 500D / TMT vs mild steel IS 432")
            rejection_reasons.append("Grade/process conflict: Requirement specifies high strength deformed / TMT reinforcement steel bars (Fe 500/500D), but IS 432 covers only mild steel (Fe 250) and medium tensile steel bars. Applicable standard is IS 1786.")

        # 3. Piping Application Gate: IS 4985 (Potable water pressure) vs IS 15328 (Underground drainage/sewerage)
        is_4985 = "4985" in std_num
        has_drainage_or_sewer = bool(re.search(r'\b(?:drainage|sewerage|sewer|underground\s+drainage|gravity\s+drainage|non-pressure\s+drainage)\b', req_text_low))
        if is_4985 and has_drainage_or_sewer:
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: underground drainage/sewerage vs potable water supply IS 4985")
            rejection_reasons.append("Application conflict: Requirement specifies underground drainage/sewerage piping, but IS 4985 covers unplasticized PVC pipes for potable water supplies. Applicable standard for underground drainage/sewerage is IS 15328.")

        # 4. Equipment Type Gate: IS 5039 (Distribution pillars / junction boxes) vs IS 1180 (Distribution transformers)
        is_5039 = "5039" in std_num
        has_transformer = bool(re.search(r'\b(?:transformer|transformers|distribution\s+transformer|kva|mva|oil\s+immersed\s+transformer)\b', req_text_low))
        if is_5039 and has_transformer:
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: distribution transformer vs distribution pillar IS 5039")
            rejection_reasons.append("Equipment mismatch: Requirement specifies outdoor oil-immersed distribution transformer, but IS 5039 covers distribution pillars (feeder pillars / junction boxes). Applicable standard is IS 1180 (Part 1).")

        # 5. Pump Type Gate: IS 8034 specifically covers submersible pumpsets
        is_8034 = "8034" in std_num
        is_pump_req = bool(re.search(r'\b(?:pump|pumps|pumpset|pumpsets)\b', req_text_low))
        is_explicitly_non_submersible = bool(re.search(r'\b(?:non[-\s]+submersible|not\s+submersible)\b', req_text_low))
        has_submersible = bool(re.search(r'(?<!\bnon-)(?<!\bnon\s)(?<!\bnot\s)\b(?:submersible|borewell|deep\s*well|submerged)\b', req_text_low)) and not is_explicitly_non_submersible
        if is_8034 and is_pump_req and not has_submersible:
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: non-submersible pump vs submersible pumpset IS 8034")
            rejection_reasons.append("Application conflict: IS 8034 specifically covers submersible pumpsets. Requirement specifies a non-submersible / surface coupled process pump.")

        # 7. Evidence Support
        # Standard exists and has scope, but does it evidence THIS requirement?
        evidence_support = (
            candidate.verification_status in ["VERIFIED", "CURATED"] and
            scope_match and
            not has_domain_conflict and
            application_match
        )

        # 8. Score Calculation & TRUST OVERRIDE RULE
        if has_domain_conflict or not application_match:
            # HARD OVERRIDE: Retrieval score cannot override domain or application conflict!
            applicability_score = 0.0
            decision = ApplicabilityDecision.NOT_APPLICABLE.value
            applicable = False
        elif not substantive_overlap and not is_explicitly_cited:
            # Zero technical overlap -> pure false positive from retrieval forcing
            applicability_score = 0.10
            decision = ApplicabilityDecision.NOT_APPLICABLE.value
            applicable = False
            rejection_reasons.append("Zero substantive technical term overlap between requirement and standard.")
        else:
            # Calculate composite applicability score
            domain_weight = 0.35 if domain_match else 0.0
            product_weight = 0.30 if product_match else 0.10
            scope_weight = 0.20 if scope_match else 0.0
            evidence_weight = 0.15 if evidence_support else 0.05

            base_score = domain_weight + product_weight + scope_weight + evidence_weight

            # Explicit citation boost (gives strong citation ground, but still requires lifecycle/compatibility)
            if is_explicitly_cited:
                base_score = max(base_score, 0.85)
                reasons.append(f"Standard {std_num} was explicitly cited in tender specification.")

            # Influence of cross-encoder / final retrieval score as secondary ranking signal
            retrieval_signal = min(1.0, max(0.0, float(candidate.final_score or candidate.relevance_score)))
            applicability_score = round(0.70 * base_score + 0.30 * retrieval_signal, 3)

            # Decision classification based on conservative thresholds
            if applicability_score >= self.applicability_threshold and not conflict_flags:
                decision = ApplicabilityDecision.APPLICABLE.value
                applicable = True
                reasons.append(f"Applicability score {applicability_score:.2f} exceeds threshold ({self.applicability_threshold:.2f})")
            elif applicability_score >= self.review_threshold:
                decision = ApplicabilityDecision.REVIEW_REQUIRED.value
                applicable = True
                reasons.append(f"Moderate applicability ({applicability_score:.2f}). Requires technical engineer review.")
            else:
                decision = ApplicabilityDecision.NOT_APPLICABLE.value
                applicable = False
                rejection_reasons.append(f"Applicability score {applicability_score:.2f} is below review threshold ({self.review_threshold:.2f})")

        return ApplicabilityResult(
            standard_number=std_num,
            title=title,
            applicable=applicable,
            decision=decision,
            applicability_score=applicability_score,
            domain_match=domain_match,
            product_match=product_match,
            scope_match=scope_match,
            application_match=application_match,
            evidence_support=evidence_support,
            conflict_flags=conflict_flags,
            reasons=reasons,
            rejection_reasons=rejection_reasons
        )
