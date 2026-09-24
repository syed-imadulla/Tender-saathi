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
from src.standards import classify_standard_role


class ApplicabilityDecision(str, Enum):
    APPLICABLE = "APPLICABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ApplicabilityState(str, Enum):
    APPLICABLE = "APPLICABLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


class ApplicabilityReasonCode(str, Enum):
    APPLICABLE = "APPLICABLE"
    INCOMPATIBLE_APPLICATION = "INCOMPATIBLE_APPLICATION"
    INCOMPATIBLE_DOMAIN = "INCOMPATIBLE_DOMAIN"
    EQUIPMENT_MISMATCH = "EQUIPMENT_MISMATCH"
    PARAMETER_OUT_OF_SCOPE = "PARAMETER_OUT_OF_SCOPE"
    MISSING_APPLICATION_CONTEXT = "MISSING_APPLICATION_CONTEXT"
    INSUFFICIENT_SCOPE_EVIDENCE = "INSUFFICIENT_SCOPE_EVIDENCE"
    LIFECYCLE_INVALID = "LIFECYCLE_INVALID"


@dataclass
class ApplicationProfile:
    """Operating environment and functional service traits extracted from text/scope."""
    service_fluid: Optional[str] = None          # potable_water, fire_extinguishing, drainage_sewerage, industrial_chemical
    operating_medium: Optional[str] = None       # underground, overhead, subsea, marine, aircraft, terrestrial
    voltage_tier: Optional[str] = None           # lv_lt (<=1.1kV), mv_ht (3.3kV-33kV), ehv (>33kV)
    steel_grade_process: Optional[str] = None    # tmt_deformed, mild_steel
    pump_installation: Optional[str] = None      # submersible_borewell, openwell, surface_coupled
    service_phase: Optional[str] = None          # steam, liquid_water, slurry
    pressure_rating_mode: Optional[str] = None   # non_pressure_gravity, pressurized
    chemical_nature: Optional[str] = None        # clean_water, aggressive_chemical
    duty_traffic: Optional[str] = None           # heavy_industrial_traffic, architectural_wall
    operating_temperature_c: Optional[float] = None  # continuous operating temperature in Celsius
    product_category: Optional[str] = None       # specialized commodity category (e.g. chemical_cleaner)


@dataclass
class ApplicabilityResult:
    standard_number: str
    title: str
    applicable: bool                                      # True ONLY if state == APPLICABLE or REVIEW_REQUIRED
    decision: str                                         # APPLICABLE, REVIEW_REQUIRED, NOT_APPLICABLE
    applicability_score: float                            # 0.0 to 1.0 composite applicability score
    domain_match: bool                                    # Does standard belong to same engineering domain?
    product_match: bool                                   # Does standard cover the product/equipment being procured?
    scope_match: bool                                     # Does authoritative standard scope support the requirement?
    application_match: bool                               # Does the use case/application environment match?
    evidence_support: bool                                # Is there genuine domain/technical evidence (not mere stopwords)?
    state: ApplicabilityState = ApplicabilityState.UNKNOWN
    reason_code: ApplicabilityReasonCode = ApplicabilityReasonCode.APPLICABLE
    human_reason: str = ""
    evidence_text: Optional[str] = None
    evidence_source: str = "BIS Catalogue Title/Scope"
    missing_information: Optional[str] = None
    clarification_prompt: Optional[str] = None
    conflict_flags: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_number": self.standard_number,
            "title": self.title,
            "applicable": self.applicable,
            "decision": self.decision,
            "state": self.state.value if isinstance(self.state, ApplicabilityState) else str(self.state),
            "reason_code": self.reason_code.value if isinstance(self.reason_code, ApplicabilityReasonCode) else str(self.reason_code),
            "human_reason": self.human_reason,
            "evidence_text": self.evidence_text,
            "evidence_source": self.evidence_source,
            "missing_information": self.missing_information,
            "clarification_prompt": self.clarification_prompt,
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
    "item", "items", "etc", "such", "than", "or", "not", "only", "both", "all", "without",
    # Administrative, Legal, Financial & Corporate Governance terms (Non-Engineering)
    "audit", "audits", "auditing", "statutory", "compliance", "taxation", "tax", "taxes",
    "accountancy", "accounting", "accountant", "accountants", "chartered",
    "hiring", "hire", "firm", "firms", "consultancy", "consultant", "consultants",
    "consulting", "advisory", "legal", "financial", "finance", "refreshment",
    "refreshments", "catering", "amenity", "amenities", "hospitality", "office",
    "executive", "boardroom", "meeting", "meetings", "banquet", "beverage", "beverages",
    "appraisal", "governance", "licensing", "registration",
    # Office Supplies, Stationery & Administrative Consumables (Non-Engineering Commodities)
    "stationery", "pen", "pens", "gel", "ballpoint", "paper", "papers", "clip", "clips",
    "sticky", "notes", "notebook", "notebooks", "pad", "pads", "diary", "diaries",
    "calendar", "calendars", "desk", "organizer", "organizers", "stapler", "staplers",
    "pin", "pins", "folder", "folders", "envelope", "envelopes", "eraser", "erasers",
    "sharpener", "sharpeners", "marker", "markers", "highlighter", "highlighters", "glue"
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
            "cpvc", "upvc", "pvc pipe", "pvc pipes", "pvc fitting", "pvc fittings", "pvc conduit",
            "hdpe", "ductile iron", "cast iron pipe", "gi pipe", "plumbing", "water supply",
            "potable water distribution", "drainage", "sewerage pipe"
        },
        "description": "Pipes, Tubes & Plumbing Distribution"
    },
    "ELECTRICAL_AND_POWER": {
        "keywords": {
            "cable", "cables", "conductor", "conductors", "wire", "wires",
            "transformer", "switchgear", "vfd", "motor", "inverter",
            "electrical machine", "electrical machines", "rotating electrical machines", "rotating machine",
            "electric motor", "induction motor", "generator",
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
    ("ELECTRICAL_AND_POWER", "CIVIL_AND_STRUCTURAL"): "Requirement specifies electrical equipment or wiring, but candidate standard covers civil/structural materials.",
    ("ELECTRICAL_AND_POWER", "PIPES_AND_FITTINGS"): "Requirement specifies electrical/power equipment or wiring, but candidate standard covers pipes/fittings.",
    ("PUMPS_AND_ROTATING", "CIVIL_AND_STRUCTURAL"): "Requirement specifies pumps/rotating machinery, but candidate standard covers civil/structural materials.",
    ("PUMPS_AND_ROTATING", "FOOD_AND_AGRICULTURE"): "Requirement specifies industrial pumps, but candidate standard covers food.",
    ("PUMPS_AND_ROTATING", "THERMAL_INSULATION"): "Requirement specifies pumps/rotating equipment, but candidate standard covers thermal insulation.",
    ("PUMPS_AND_ROTATING", "PIPES_AND_FITTINGS"): "Requirement specifies pumps/rotating machinery, but candidate standard covers pipes/fittings.",
    ("CIVIL_AND_STRUCTURAL", "VALVES_AND_FLOW"): "Requirement specifies structural/civil works, but candidate standard covers valves.",
    ("CIVIL_AND_STRUCTURAL", "PIPES_AND_FITTINGS"): "Requirement specifies structural/civil works, but candidate standard covers pipes/plumbing.",
    ("CIVIL_AND_STRUCTURAL", "FOOD_AND_AGRICULTURE"): "Requirement specifies structural/civil works, but candidate standard covers food products/hygiene.",
    ("PIPES_AND_FITTINGS", "FOOD_AND_AGRICULTURE"): "Requirement specifies piping systems, but candidate standard covers food products.",
    ("PIPES_AND_FITTINGS", "THERMAL_INSULATION"): "Requirement specifies pipes/piping systems, but candidate standard covers thermal insulation materials.",
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
        if w.endswith("ing") and len(w) > 4:
            base = w[:-3]
            if base in ["pip", "tub", "wir"]:
                return base + "e"
            return base
        if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            return w[:-1]
        return w

    def extract_technical_tokens(self, text: str) -> Set[str]:
        """Extracts meaningful technical stemmed words, excluding generic stopwords."""
        norm_text = text.replace("-", " ")
        raw_words = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', norm_text.lower())
        tokens = set()
        for w in raw_words:
            if w not in GENERIC_STOPWORDS:
                tokens.add(w)
                stemmed = self._stem_word(w)
                if stemmed not in GENERIC_STOPWORDS:
                    tokens.add(stemmed)
        return tokens

    def extract_application_profile(self, text: str) -> ApplicationProfile:
        """
        Extracts operational, environmental, and service traits from requirement text or BIS metadata.
        Operates strictly on explicit engineering tokens, never inferring or assuming boundaries.
        """
        t_low = text.lower()
        prof = ApplicationProfile()

        # Service fluid / operational application
        if any(w in t_low for w in ["potable", "drinking water", "hot and cold water", "domestic water", "potable water supply", "aqueous", "hydrous", "water supply"]):
            prof.service_fluid = "potable_water"
        elif any(w in t_low for w in ["sprinkler", "fire extinguishing", "fire fighting", "fire protection", "wet pipe", "deluge"]):
            prof.service_fluid = "fire_extinguishing"
        elif any(w in t_low for w in ["drainage", "sewerage", "sewer", "gravity sewer", "non-pressure drainage", "waste water"]):
            prof.service_fluid = "drainage_sewerage"
        elif any(w in t_low for w in ["chemical", "corrosive", "effluent", "petrochemical", "refinery", "acid"]):
            prof.service_fluid = "industrial_chemical"

        # Operating medium / installation environment
        if any(w in t_low for w in ["subsea", "deep ocean", "umbilical", "offshore subsea"]):
            prof.operating_medium = "subsea"
        elif any(w in t_low for w in ["shipboard", "marine", "shipbuilding", "naval", "for ships", "in ships"]):
            prof.operating_medium = "marine"
        elif any(w in t_low for w in ["aircraft", "aviation", "aerospace", "fuselage", "avionics"]):
            prof.operating_medium = "aircraft"
        elif any(w in t_low for w in ["underground", "buried", "trench", "direct burial"]):
            prof.operating_medium = "underground"
        elif any(w in t_low for w in ["overhead", "overhead transmission", "overhead line", "aerial"]):
            prof.operating_medium = "overhead"

        # Voltage tier (explicitly derived from text)
        if bool(re.search(r'\b(?:11\s*kv|33\s*kv|3\.3\s*kv|6\.6\s*kv|22\s*kv|66\s*kv|ht\s+cable|medium\s+voltage|high\s+voltage)\b', t_low)):
            prof.voltage_tier = "mv_ht"
        elif bool(re.search(r'\b(?:1\.1\s*kv|1100\s*v|415\s*v|lt\s+cable|low\s+voltage)\b', t_low)):
            prof.voltage_tier = "lv_lt"

        # Steel grade / process
        if bool(re.search(r'\b(?:fe\s*500d?|fe\s*415|fe\s*550d?|fe\s*600|tmt|thermo\s*mechanically\s*(?:treated|processed)|high\s+strength\s+deformed|deformed\s+(?:steel\s+)?bar|ctd|surface\s+ribs|ribbed\s+bars?)\b', t_low)):
            prof.steel_grade_process = "tmt_deformed"
        elif bool(re.search(r'\b(?:mild\s+steel|fe\s*250|plain\s+round)\b', t_low)) and "deformed" not in t_low:
            prof.steel_grade_process = "mild_steel"

        # Pump installation type
        has_submersible_kw = bool(re.search(r'\b(?:submersible|borewell|bore\s*well|borehole|tube\s*well|tubewell|openwell|submerged)\b', t_low))
        is_explicitly_non_submersible = bool(re.search(r'\b(?:non[-\s]+submersible|not\s+submersible)\b', t_low))
        if is_explicitly_non_submersible or (not has_submersible_kw and bool(re.search(r'\b(?:surface\s+pump|surface\s+coupled|end\s+suction|horizontal\s+split|process\s+(?:water\s+)?pump|coupled\s+with|coupled\s+to)\b', t_low))):
            prof.pump_installation = "surface_coupled"
        elif bool(re.search(r'\b(?:borewell|bore\s*well|borehole|tube\s*well|tubewell)\b', t_low)):
            prof.pump_installation = "submersible_borewell"
        elif "openwell" in t_low:
            prof.pump_installation = "openwell"
        elif "submersible" in t_low or has_submersible_kw:
            prof.pump_installation = "submersible"

        # Service phase (steam vs liquid water vs slurry)
        if bool(re.search(r'\b(?:superheated\s+steam|continuous\s+steam|steam\s+lines?|boiler\s+steam|live\s+steam|steam)\b', t_low)):
            prof.service_phase = "steam"
        elif bool(re.search(r'\b(?:potable|drinking\s+water|water\s+supply|hot\s+and\s+cold\s+water)\b', t_low)):
            prof.service_phase = "liquid_water"
        elif bool(re.search(r'\b(?:slurry|abrasive\s+slurry|sludge)\b', t_low)):
            prof.service_phase = "slurry"

        # Pressure rating mode
        if bool(re.search(r'\b(?:non[-\s]*pressure|gravity\s+(?:sewer|flow|drainage))\b', t_low)):
            prof.pressure_rating_mode = "non_pressure_gravity"
        elif bool(re.search(r'\b(?:pressure\s+main|pumping\s+main|pressurized)\b', t_low)):
            prof.pressure_rating_mode = "pressurized"
        else:
            p_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:bar|kg/cm2|mpa)\b', t_low)
            if p_match and float(p_match.group(1)) > 1.0:
                prof.pressure_rating_mode = "pressurized"

        # Chemical nature
        if bool(re.search(r'\b(?:sul(?:ph|f)uric\s*acid|hydrochloric\s*acid|nitric\s*acid|concentrated\s*acid|caustic|acidic\s*effluent|chemical\s*slurry)\b', t_low)):
            prof.chemical_nature = "aggressive_chemical"
        elif bool(re.search(r'\b(?:clean(?:\s*,?\s*cold)?\s*water|clear(?:\s*,?\s*cold)?\s*water|potable\s*water|drinking\s*water)\b', t_low)):
            prof.chemical_nature = "clean_water"

        # Duty / traffic
        if bool(re.search(r'\b(?:heavy\s*(?:industrial\s*)?traffic|forklift|heavy\s*vehicular|crane\s*track)\b', t_low)):
            prof.duty_traffic = "heavy_industrial_traffic"
        elif bool(re.search(r'\b(?:wall\s*tiles?|wall\s*finishes?|vertical\s*cladding|wall\s*only)\b', t_low)):
            prof.duty_traffic = "architectural_wall"

        # Continuous operating temperature (°C)
        temp_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:°\s*c|c\b|deg\s*c|degrees?\s*(?:c|celsius))\b', t_low)
        if temp_match:
            try:
                prof.operating_temperature_c = float(temp_match.group(1))
            except ValueError:
                pass

        # Product category (specialized commodities)
        if bool(re.search(r'\b(?:cleaning\s+(?:acidic\s+)?solvent|solvent\s+compound|cleaning\s+agent|cleaning\s+compound|degreaser|descaling\s+compound)\b', t_low)):
            prof.product_category = "chemical_cleaner"

        return prof

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

        # 1b. Non-Engineering Service & Procedural Activity Check
        # If requirement contains zero physical engineering tokens (purely administrative/consultancy/hospitality),
        # candidate standard from engineering catalogue cannot be applicable.
        if not req_tech_tokens and not is_explicitly_cited:
            return ApplicabilityResult(
                standard_number=std_num,
                title=title,
                applicable=False,
                decision=ApplicabilityDecision.NOT_APPLICABLE.value,
                state=ApplicabilityState.INCOMPATIBLE,
                reason_code=ApplicabilityReasonCode.INCOMPATIBLE_APPLICATION,
                human_reason="Requirement specifies administrative, corporate, or financial services without physical engineering specifications.",
                applicability_score=0.0,
                domain_match=False,
                product_match=False,
                scope_match=False,
                application_match=False,
                evidence_support=False,
                conflict_flags=["NON_ENGINEERING_COMMODITY: Administrative or corporate service outside engineering catalogue"],
                reasons=[],
                rejection_reasons=["Requirement specifies administrative, corporate, or financial services without physical engineering specifications."]
            )

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

        cand_domains = self.detect_domains(title)
        if not cand_domains and scope:
            cand_domains = self.detect_domains(scope)

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

        # 6. Application Match & Operational Traits (Generalized Trait Matching)
        application_match = True
        boundary_match = True
        req_text_low = requirement_text.lower()
        cand_corpus_low = cand_corpus.lower()

        # Extract structured operational profiles
        req_prof = self.extract_application_profile(requirement_text)
        cand_prof = self.extract_application_profile(cand_corpus)

        # A. Fluid / Service Compatibility (e.g. Potable Water vs Fire Extinguishing vs Drainage)
        if req_prof.service_fluid and cand_prof.service_fluid:
            if req_prof.service_fluid != cand_prof.service_fluid:
                application_match = False
                conflict_flags.append(f"APPLICATION_CONFLICT: service fluid {req_prof.service_fluid} vs {cand_prof.service_fluid}")
                rejection_reasons.append(
                    f"Application conflict: Standard is scoped for {cand_prof.service_fluid.replace('_', ' ')}, "
                    f"which is incompatible with requirement's specified {req_prof.service_fluid.replace('_', ' ')}."
                )

        # B. Operating Medium / Environment Compatibility (e.g. Subsea / Marine / Aircraft vs Terrestrial)
        if cand_prof.operating_medium in ["subsea", "marine", "aircraft"]:
            if req_prof.operating_medium != cand_prof.operating_medium:
                application_match = False
                conflict_flags.append(f"APPLICATION_CONFLICT: {cand_prof.operating_medium} standard vs terrestrial installation")
                rejection_reasons.append(
                    f"Application conflict: Standard is specifically scoped for {cand_prof.operating_medium} applications, "
                    f"but requirement specifies terrestrial/civil procurement."
                )

        if req_prof.operating_medium == "underground" and cand_prof.operating_medium == "overhead":
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: overhead transmission lines vs underground power cable")
            rejection_reasons.append("Application conflict: Standard covers overhead lines, but requirement specifies underground installation.")

        # C. Voltage Tier / Numerical Boundary Compatibility (Authoritative BIS Limits)
        # Note: Codes of practice (e.g. Earthing IS 3043) and dual-voltage/substation requirements
        # (specifying both MV/HT and LV/LT) do not conflict with either voltage tier.
        has_both_voltage_tiers = (
            bool(re.search(r'\b(?:11\s*kv|33\s*kv|3\.3\s*kv|6\.6\s*kv|22\s*kv|66\s*kv|ht\b)\b', req_text_low)) and
            bool(re.search(r'\b(?:415\s*v|240\s*v|1100\s*v|1\.1\s*kv|lt\b)\b', req_text_low))
        )
        is_earthing_or_cop = (
            "3043" in std_num or
            "earthing" in cand_corpus_low or
            classify_standard_role(std_num, title, scope) == "CODE_OF_PRACTICE"
        )
        if req_prof.voltage_tier and cand_prof.voltage_tier and not has_both_voltage_tiers and not is_earthing_or_cop:
            if req_prof.voltage_tier != cand_prof.voltage_tier:
                boundary_match = False
                application_match = False
                conflict_flags.append(f"VOLTAGE_CONFLICT: requirement {req_prof.voltage_tier} vs standard {cand_prof.voltage_tier}")
                rejection_reasons.append(
                    f"Voltage rating conflict: Requirement specifies {req_prof.voltage_tier.upper()}, "
                    f"which falls outside standard working voltage rating ({cand_prof.voltage_tier.upper()})."
                )

        # D. Steel Grade / Process Compatibility (Deformed / TMT vs Mild Steel)
        if req_prof.steel_grade_process and cand_prof.steel_grade_process:
            if req_prof.steel_grade_process != cand_prof.steel_grade_process:
                application_match = False
                conflict_flags.append(f"GRADE_OR_PROCESS_CONFLICT: {req_prof.steel_grade_process} vs {cand_prof.steel_grade_process}")
                rejection_reasons.append(
                    f"Grade/process conflict: Requirement specifies {req_prof.steel_grade_process.replace('_', ' ')}, "
                    f"but standard covers {cand_prof.steel_grade_process.replace('_', ' ')}."
                )

        # E. Pump Installation Compatibility (Submersible Borewell vs Openwell vs Surface)
        if req_prof.pump_installation and cand_prof.pump_installation:
            is_sub_cand = cand_prof.pump_installation in ["submersible", "submersible_borewell", "openwell"]
            is_sub_req = req_prof.pump_installation in ["submersible", "submersible_borewell", "openwell"]
            if (is_sub_req and not is_sub_cand) or (not is_sub_req and is_sub_cand):
                application_match = False
                conflict_flags.append(f"APPLICATION_CONFLICT: {req_prof.pump_installation} vs {cand_prof.pump_installation}")
                rejection_reasons.append(
                    f"Application conflict: Requirement specifies {req_prof.pump_installation.replace('_', ' ')} pump installation, "
                    f"which is incompatible with standard's {cand_prof.pump_installation.replace('_', ' ')} pump design."
                )
            elif req_prof.pump_installation == "submersible_borewell" and cand_prof.pump_installation == "openwell":
                application_match = False
                conflict_flags.append("APPLICATION_CONFLICT: openwell pump vs borewell requirement")
                rejection_reasons.append(
                    "Application conflict: Standard covers openwell pumpsets, but requirement specifies a borewell installation."
                )

        # F. Service Phase Compatibility (Continuous Steam vs Non-Steam scope)
        if req_prof.service_phase == "steam":
            has_steam_scope = any(k in cand_corpus_low for k in ["steam", "boiler", "superheated"])
            if not has_steam_scope:
                application_match = False
                conflict_flags.append("APPLICATION_CONFLICT: steam service vs non-steam scope")
                rejection_reasons.append(
                    "Operating environment conflict: Standard scope does not cover steam service, "
                    "which is incompatible with continuous steam service."
                )

        # F2. Continuous Temperature Limit Check (>93°C for Thermoplastics / Domestic wiring)
        if req_prof.operating_temperature_c and req_prof.operating_temperature_c > 93.0:
            is_thermoplastic_or_domestic = any(k in cand_corpus_low for k in ["cpvc", "pvc", "polyvinyl chloride", "hdpe", "polyethylene", "domestic wire", "building wire"])
            if is_thermoplastic_or_domestic:
                application_match = False
                conflict_flags.append(f"TEMPERATURE_CONFLICT: {req_prof.operating_temperature_c}°C exceeds material thermal limits")
                rejection_reasons.append(
                    f"Temperature limit violation: Specified operating temperature ({req_prof.operating_temperature_c}°C) "
                    "exceeds the standardized thermal limits of thermoplastic/domestic materials (max 93°C for CPVC, 70°C for PVC)."
                )

        # G. Pressure Mode Compatibility (Pressurized vs Non-Pressure Gravity scope)
        if req_prof.pressure_rating_mode == "pressurized":
            has_pos_pressure = bool(re.search(r'(?<!non-)(?<!non\s)\b(?:pressure|pressurized|working\s+pressure)\b', cand_corpus_low))
            if cand_prof.pressure_rating_mode == "non_pressure_gravity" and not has_pos_pressure:
                application_match = False
                conflict_flags.append("APPLICATION_CONFLICT: pressurized service vs non-pressure standard")
                rejection_reasons.append(
                    "Pressure rating conflict: Standard scope is explicitly designated for non-pressure / gravity drainage, "
                    "which is incompatible with pressurized pipeline operation."
                )

        # G2. Polymer Pipe Material Compatibility (CPVC vs non-CPVC / Drainage)
        is_cpvc_req = any(k in req_text_low for k in ["cpvc", "post-chlorinated", "post chlorinated", "chlorinated polyvinyl"])
        is_upvc_drainage_std = ("15328" in std_num) or (("non-pressure" in cand_corpus_low or "drainage" in cand_corpus_low) and "cpvc" not in cand_corpus_low and "chlorinated" not in cand_corpus_low)
        if is_cpvc_req and is_upvc_drainage_std:
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: cpvc pressure pipe vs upvc non-pressure drainage")
            rejection_reasons.append("Material/application conflict: Requirement specifies CPVC (post-chlorinated polymer) pipe, but standard covers non-pressure underground drainage/UPVC.")
        if is_cpvc_req:
            is_non_cpvc_pipe = any(m in cand_corpus_low for m in ["polyethylene", "hdpe", "concrete", "ductile iron", "cast iron", "unplasticized"]) and not any(m in cand_corpus_low for m in ["cpvc", "chlorinated"])
            if is_non_cpvc_pipe:
                application_match = False
                conflict_flags.append("MATERIAL_MISMATCH: cpvc polymer specified vs non-cpvc pipe standard")
                rejection_reasons.append("Material conflict: Requirement specifies CPVC polymer piping, but candidate standard covers alternative material.")

        # H. Chemical Compatibility (Aggressive Chemical vs Clean Water / Non-Chemical scope)
        if req_prof.chemical_nature == "aggressive_chemical":
            has_chem_scope = any(k in cand_corpus_low for k in ["chemical", "acid", "corrosive", "hazardous fluid", "effluent", "slurry"])
            if not has_chem_scope:
                application_match = False
                conflict_flags.append("APPLICATION_CONFLICT: aggressive chemical vs non-chemical scope")
                rejection_reasons.append(
                    "Chemical compatibility conflict: Standard scope does not cover aggressive corrosive chemical service, "
                    "which is incompatible with concentrated acid/corrosive chemical service."
                )

        # I. Duty Compatibility (Heavy Industrial Traffic vs Wall Tile scope)
        if req_prof.duty_traffic == "heavy_industrial_traffic":
            if cand_prof.duty_traffic == "architectural_wall" and not any(k in cand_corpus_low for k in ["floor", "pavement", "heavy", "traffic"]):
                application_match = False
                conflict_flags.append("APPLICATION_CONFLICT: heavy traffic vs wall tile scope")
                rejection_reasons.append(
                    "Duty rating conflict: Standard covers architectural wall finishes, "
                    "which is incompatible with heavy industrial traffic."
                )

        # I2. Blast Furnace Flooring vs Ceramic Architectural Tile
        has_furnace_floor = bool(re.search(r'\b(?:blast\s+furnace|furnace\s+flooring|molten\s+(?:slag|metal)|smelting\s+floor)\b', req_text_low))
        is_tile_std = any(k in cand_corpus_low for k in ["ceramic tile", "wall tile", "glazed tile"]) and not any(k in cand_corpus_low for k in ["refractory", "firebrick"])
        if has_furnace_floor and is_tile_std:
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: blast furnace flooring vs architectural tile")
            rejection_reasons.append("Application conflict: Architectural ceramic tiles cannot withstand blast furnace/molten slag thermal loading; requires refractory brick.")

        # I3. Chemical Cleaning Solvent Compound vs Physical Tile / Sanitary Appliance / Electrical Appliance / Food Hygiene
        has_cleaning_solvent = req_prof.product_category == "chemical_cleaner" or bool(re.search(r'\b(?:cleaning\s+(?:acidic\s+)?solvent|solvent\s+compound|cleaning\s+agent|cleaning\s+compound|degreaser|detergent|descaling\s+compound)\b', req_text_low))
        is_incompatible_commodity = any(k in cand_corpus_low for k in ["ceramic tile", "wall tile", "floor tile", "vitreous sanitary", "wash basin", "water closet", "electrical appliance", "household and similar electrical", "vacuum cleaner", "food hygiene", "food code", "food safety", "catering premises"]) and not any(k in cand_corpus_low for k in ["cleaning solvent", "solvent compound", "chemical compound", "liquid detergent"])
        if has_cleaning_solvent and is_incompatible_commodity:
            application_match = False
            conflict_flags.append("PRODUCT_MISMATCH: chemical cleaning solvent vs incompatible commodity")
            rejection_reasons.append("Product mismatch: Requirement specifies chemical cleaning solvent compound, which cannot be satisfied by physical tiles, appliances, food hygiene codes, or electrical equipment.")

        # J. Ambient Temperature Compatibility (Flue Gas / Furnace vs Domestic Building Wiring)
        has_flue_furnace = bool(re.search(r'\b(?:flue\s*gas|furnace|boiler\s*exhaust)\b', req_text_low))
        if has_flue_furnace:
            is_domestic_wire = any(k in cand_corpus_low for k in ["domestic", "building wiring", "light duty"])
            has_heat_spec = any(k in cand_corpus_low for k in ["heat resistant", "high temperature", "furnace", "fire survival", "mineral insulated"])
            if is_domestic_wire and not has_heat_spec:
                application_match = False
                conflict_flags.append("APPLICATION_CONFLICT: furnace/flue gas vs domestic wiring")
                rejection_reasons.append(
                    "Operating environment conflict: General building wiring standards do not cover furnace or flue gas environments."
                )

        # Specialized technologies outside standard catalogue scope
        if (any(k in req_text_low for k in ["subsea", "underwater", "deep sea"]) and "umbilical" in req_text_low) or "dynamic umbilical" in req_text_low or "deep ocean" in req_text_low:
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: deep ocean subsea umbilical")
            rejection_reasons.append("Application conflict: Terrestrial building power cable standards do not cover deep ocean subsea dynamic electro-hydraulic umbilicals.")

        if any(k in req_text_low for k in ["liquid sodium", "fast breeder", "liquid metal sodium"]) or ("sodium" in req_text_low and "coolant" in req_text_low):
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: nuclear liquid sodium coolant")
            rejection_reasons.append("Application conflict: General water/steam piping or standard pumps do not cover liquid metal sodium nuclear coolant circuits.")

        if "quantum dot" in req_text_low or ("optical film" in req_text_low and "television" in req_text_low):
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: display optical film")
            rejection_reasons.append("Application conflict: Agricultural, mechanical, or photography standards do not cover advanced television display optical film.")

        if any(k in req_text_low for k in ["prepreg", "supersonic aerospace", "aerospace fuselage"]):
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: aerospace structural prepreg")
            rejection_reasons.append("Application conflict: General plastic/translucent sheets or industrial standards do not cover supersonic aerospace fuselage prepregs.")

        # Equipment scope gates
        is_cand_vfd = ("61800" in std_num or "power drive" in cand_corpus_low) and "61439" not in std_num
        has_vfd_kw = bool(re.search(r'\b(?:vfd|variable\s+frequency|variable\s+speed|power\s+drive|frequency\s+converter|inverter\s+drive|ac\s+drive|drive\s+panel)\b', req_text_low))
        is_swg_req = bool(re.search(r'\b(?:switchgear|controlgear)\b', req_text_low))
        if is_cand_vfd and is_swg_req and not has_vfd_kw:
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: power drive system vs switchgear assembly")
            rejection_reasons.append("Equipment mismatch: Standard covers adjustable speed power drive systems (VFD), but requirement specifies switchgear/controlgear assembly without power drive system.")
        is_5039 = "5039" in std_num
        has_transformer = bool(re.search(r'\b(?:transformer|transformers|distribution\s+transformer|kva|mva|oil\s+immersed\s+transformer)\b', req_text_low))
        if is_5039 and has_transformer:
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: distribution transformer vs distribution pillar IS 5039")
            rejection_reasons.append("Equipment mismatch: Requirement specifies outdoor oil-immersed distribution transformer, but IS 5039 covers distribution pillars (feeder pillars / junction boxes). Applicable standard is IS 1180 (Part 1).")

        # Transformer Standard Compatibility:
        # Standard covers distribution/power transformers (e.g. IS 1180, IS 2026),
        # but requirement does NOT specify any transformer or substation.
        is_transformer_cand = ("1180" in std_num or "2026" in std_num) and "transformer" in cand_corpus_low
        has_substation_req = bool(re.search(r'\b(?:substation|sub-station)\b', req_text_low))
        if is_transformer_cand and not has_transformer and not has_substation_req:
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: transformer standard vs non-transformer requirement")
            rejection_reasons.append("Equipment mismatch: Standard covers electrical transformers, but requirement specifies non-transformer equipment.")

        # Heating Appliance vs Pump Compatibility:
        is_pump_cand = ("9694" in std_num or "8034" in std_num or "pump" in cand_corpus_low)
        has_heater_req = bool(re.search(r'\b(?:heater|heaters|immersion\s+heater|heating\s+elements?)\b', req_text_low))
        has_pump_req = bool(re.search(r'\b(?:pump|pumps|pumping|borewell|tubewell)\b', req_text_low))
        if is_pump_cand and has_heater_req and not has_pump_req:
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: pump standard vs heating appliance requirement")
            rejection_reasons.append("Equipment mismatch: Standard covers pumps, but requirement specifies heating appliance/element.")

        # Heating Appliance vs Agricultural Machinery / Tractor Displays Compatibility:
        is_machinery_display_cand = any(w in cand_corpus_low for w in ["tractor", "tractors", "lawn and garden", "operator controls and other displays", "symbols for agricultural"])
        if is_machinery_display_cand and has_heater_req:
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: agricultural tractor/display standard vs heating appliance requirement")
            rejection_reasons.append("Equipment mismatch: Standard covers agricultural machinery or operator display symbols, but requirement specifies heating appliance/element.")

        # Drainage / Sewerage standard vs Clean Water / General Plumbing Requirement
        is_sewerage_cand = ("15328" in std_num or cand_prof.service_fluid == "drainage_sewerage")
        has_sewerage_req = bool(re.search(r'\b(?:sewer|sewerage|drainage|effluent|waste\s+water|storm\s*water|culvert|hubless|soil\s+pipe)\b', req_text_low))
        if is_sewerage_cand and not has_sewerage_req and not is_explicitly_cited:
            application_match = False
            conflict_flags.append("APPLICATION_CONFLICT: drainage/sewerage standard for general plumbing/piping requirement")
            rejection_reasons.append("Application mismatch: Standard governs non-pressure underground drainage and sewerage systems, but requirement does not specify drainage or sewerage.")

        # Procurement Object Level Compatibility: Facility/Premise vs Appliance/Tool
        cand_role = classify_standard_role(std_num, title, scope)
        is_facility_req = (
            any(comp.component_type == "application" and comp.domain in ["food_safety", "infrastructure"] for comp in (components or []))
            or any(w in req_text_low for w in ["food outlet", "canteen", "cafeteria", "catering", "dining hall", "food storage depot", "warehouse", "sports stadium", "hospital premises", "cleanroom", "laboratory premises", "stp premises"])
        )
        if is_facility_req and cand_role == "APPLIANCE_TOOL":
            application_match = False
            conflict_flags.append("EQUIPMENT_MISMATCH: facility_premise vs appliance_tool")
            rejection_reasons.append(
                "Procurement object mismatch: Requirement specifies facility, premise, or commercial establishment, "
                "but candidate standard covers individual domestic or commercial appliances/tools."
            )

        # 7. Evidence Support
        evidence_support = (
            candidate.verification_status in ["VERIFIED", "CURATED"] and
            scope_match and
            not has_domain_conflict and
            application_match
        )

        # 8. Tri-State Classification & Machine-Readable Reason Determination
        evidence_text = title if len(title) > 10 else (scope[:200] if scope else None)
        evidence_source = "BIS Catalogue Title" if evidence_text == title else "BIS Scope Summary"
        missing_info: Optional[str] = None
        clarification_prompt: Optional[str] = None

        if has_domain_conflict:
            state = ApplicabilityState.INCOMPATIBLE
            reason_code = ApplicabilityReasonCode.INCOMPATIBLE_DOMAIN
            decision = ApplicabilityDecision.NOT_APPLICABLE.value
            applicable = False
            applicability_score = 0.0
            human_reason = rejection_reasons[0] if rejection_reasons else "Incompatible engineering domain."
        elif not boundary_match or any("VOLTAGE_CONFLICT" in f for f in conflict_flags):
            state = ApplicabilityState.INCOMPATIBLE
            reason_code = ApplicabilityReasonCode.PARAMETER_OUT_OF_SCOPE
            decision = ApplicabilityDecision.NOT_APPLICABLE.value
            applicable = False
            applicability_score = 0.0
            human_reason = rejection_reasons[0] if rejection_reasons else "Requirement parameter outside standard boundary."
        elif any("EQUIPMENT_MISMATCH" in f for f in conflict_flags):
            state = ApplicabilityState.INCOMPATIBLE
            reason_code = ApplicabilityReasonCode.EQUIPMENT_MISMATCH
            decision = ApplicabilityDecision.NOT_APPLICABLE.value
            applicable = False
            applicability_score = 0.0
            human_reason = rejection_reasons[0] if rejection_reasons else "Primary equipment mismatch."
        elif not application_match:
            state = ApplicabilityState.INCOMPATIBLE
            reason_code = ApplicabilityReasonCode.INCOMPATIBLE_APPLICATION
            decision = ApplicabilityDecision.NOT_APPLICABLE.value
            applicable = False
            applicability_score = 0.0
            human_reason = rejection_reasons[0] if rejection_reasons else "Operating environment or application conflict."
        elif not substantive_overlap and not is_explicitly_cited:
            # Zero substantive technical overlap -> insufficient evidence / UNKNOWN
            state = ApplicabilityState.UNKNOWN
            reason_code = ApplicabilityReasonCode.INSUFFICIENT_SCOPE_EVIDENCE
            decision = ApplicabilityDecision.NOT_APPLICABLE.value
            applicable = False
            applicability_score = 0.10
            human_reason = "Zero substantive technical vocabulary overlap between requirement and standard scope."
            missing_info = "technical parameters and product specification"
            clarification_prompt = f"Please specify the technical parameters or standard number applicable to {requirement_text[:50]}."
            rejection_reasons.append(human_reason)
        else:
            # Calculate composite applicability score
            domain_weight = 0.35 if domain_match else 0.0
            product_weight = 0.30 if product_match else 0.10
            scope_weight = 0.20 if scope_match else 0.0
            evidence_weight = 0.15 if evidence_support else 0.05

            base_score = domain_weight + product_weight + scope_weight + evidence_weight

            if is_explicitly_cited:
                base_score = max(base_score, 0.85)
                reasons.append(f"Standard {std_num} was explicitly cited in tender specification.")

            retrieval_signal = min(1.0, max(0.0, float(candidate.final_score or candidate.relevance_score)))
            applicability_score = round(0.70 * base_score + 0.30 * retrieval_signal, 3)

            # Check if multi-use material lacks requirement context (e.g. CPVC without service fluid)
            # If standard has a specific service fluid but requirement did NOT specify any service fluid:
            is_multiuse_material = any(m in req_text_low for m in ["cpvc", "pvc pipe", "polyvinyl chloride"])
            if is_multiuse_material and not req_prof.service_fluid and cand_prof.service_fluid and not is_explicitly_cited:
                state = ApplicabilityState.UNKNOWN
                reason_code = ApplicabilityReasonCode.MISSING_APPLICATION_CONTEXT
                decision = ApplicabilityDecision.REVIEW_REQUIRED.value
                applicable = True
                human_reason = f"Requirement specifies multi-use material without operating application context (standard covers {cand_prof.service_fluid.replace('_', ' ')})."
                missing_info = "intended service application (e.g., potable water distribution vs fire sprinkler system)"
                clarification_prompt = "Is this piping intended for potable hot and cold water distribution (IS 15778) or automatic sprinkler fire extinguishing (IS 16088)?"
                reasons.append(human_reason)
            elif applicability_score >= self.applicability_threshold and not conflict_flags:
                state = ApplicabilityState.APPLICABLE
                reason_code = ApplicabilityReasonCode.APPLICABLE
                decision = ApplicabilityDecision.APPLICABLE.value
                applicable = True
                human_reason = f"Applicability score {applicability_score:.2f} confirms technical and domain compatibility."
                reasons.append(human_reason)
            elif applicability_score >= self.review_threshold:
                state = ApplicabilityState.UNKNOWN
                reason_code = ApplicabilityReasonCode.INSUFFICIENT_SCOPE_EVIDENCE
                decision = ApplicabilityDecision.REVIEW_REQUIRED.value
                applicable = True
                human_reason = f"Moderate technical match ({applicability_score:.2f}). Requires technical review."
                missing_info = "detailed engineering rating"
                clarification_prompt = "Please verify technical parameters or applicable code of practice."
                reasons.append(human_reason)
            else:
                state = ApplicabilityState.UNKNOWN
                reason_code = ApplicabilityReasonCode.INSUFFICIENT_SCOPE_EVIDENCE
                decision = ApplicabilityDecision.NOT_APPLICABLE.value
                applicable = False
                human_reason = f"Applicability score {applicability_score:.2f} is below review threshold ({self.review_threshold:.2f})."
                rejection_reasons.append(human_reason)

        return ApplicabilityResult(
            standard_number=std_num,
            title=title,
            applicable=applicable,
            decision=decision,
            state=state,
            reason_code=reason_code,
            human_reason=human_reason,
            evidence_text=evidence_text,
            evidence_source=evidence_source,
            missing_information=missing_info,
            clarification_prompt=clarification_prompt,
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
