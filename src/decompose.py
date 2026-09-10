"""
Module: src/decompose.py
Purpose: Reusable deterministic compound requirement decomposition layer.

Breaks down procurement requirements into structured technical components:
- materials
- products / equipment
- electrical & control components
- applications / environments
- execution / installation activities
- testing activities
- specifications & technical ratings (voltage, pressure, dimensions, grades)

This layer operates BEFORE standards retrieval, providing explainable multi-component
attribution for complex procurement requirements.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
import re


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class RequirementComponent:
    """A discrete technical component extracted from a requirement."""
    text: str                                  # Exact or normalized snippet (e.g. "VFD", "water pump")
    component_type: str                        # material, product, equipment, electrical, control, installation, testing, application, specification
    domain: str                                # electrical, mechanical, civil, piping, sanitary, food_safety, general
    extracted_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecompositionResult:
    """Complete output of the requirement decomposition layer."""
    original_text: str
    components: List[RequirementComponent] = field(default_factory=list)
    decomposition_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "components": [c.to_dict() for c in self.components],
            "decomposition_confidence": self.decomposition_confidence
        }


# ---------------------------------------------------------------------------
# Technical Lexicons and Pattern Matchers
# ---------------------------------------------------------------------------

# 1. Numerical Specifications & Engineering Ratings
SPECIFICATION_PATTERNS = [
    # Voltage (e.g., "3.3 kV", "11 kV", "415 V", "1100 V", "250 V")
    (
        re.compile(r'\b(\d+(?:\.\d+)?\s*(?:k\s*V|V\s*AC|V\s*DC|V|volts?))\b', re.IGNORECASE),
        "voltage",
        "electrical"
    ),
    # Voltage Class acronyms (e.g., "LT", "HT", "MV", "HV", "EHV")
    (
        re.compile(r'\b(HT|LT|MV|HV|EHV)\b', re.IGNORECASE),
        "voltage_class",
        "electrical"
    ),
    # Pipe Pressure / Class ratings (e.g., "PN 10", "PN 16", "Class 1", "Class 150", "SDR 11", "SDR 13.5", "NP2", "NP3")
    (
        re.compile(r'\b(PN\s*\d+|Class\s*\d+|Class\s*150|Class\s*300|300#|150#|SDR\s*\d+(?:\.\d+)?|NP[1-4])\b', re.IGNORECASE),
        "pressure_or_pipe_class",
        "piping"
    ),
    # Dimensions (e.g., "100 mm", "50 to 1200 mm", "DN 80", "25 mm dia", "4 core 16 sqmm")
    (
        re.compile(r'\b(\d+(?:\s*to\s*\d+)?\s*(?:mm|cm|m|inch(?:es)?|\"|dia|diameter|sqmm|sq\s*mm|core))\b', re.IGNORECASE),
        "dimension",
        "general"
    ),
    # Material Grades (e.g., "Grade 43", "Grade 304", "SS 316", "OPC 43", "OPC 53", "PPC")
    (
        re.compile(r'\b(Grade\s*\w+|SS\s*304|SS\s*316|OPC\s*\d+|PPC)\b', re.IGNORECASE),
        "material_grade",
        "civil"
    )
]

# 2. Domain Entities Dictionary: (Pattern, component_type, domain, attribute_generator)
ENTITY_PATTERNS = [
    # --- CONTROL & DRIVES ---
    (
        re.compile(r'\b(vfd|variable\s+frequency\s+drive|variable\s+speed\s+drive|adjustable\s+speed\s+drive|ac\s+drive|inverter\s+drive|soft\s+starter)\b', re.IGNORECASE),
        "control",
        "electrical",
        lambda m: {"category": "drive_control", "standard_focus": "IS/IEC 61800"}
    ),

    # --- ELECTRICAL SWITCHGEAR & PANELS ---
    (
        re.compile(r'\b(control\s+panel|starter\s+panel|feeder\s+pillar|distribution\s+pillar|distribution\s+board|sub-distribution\s+board|switchgear|controlgear|mccb|mcb|dbo|panel)\b', re.IGNORECASE),
        "electrical",
        "electrical",
        lambda m: {"category": "switchgear_enclosure", "standard_focus": "IS/IEC 61439"}
    ),

    # --- ELECTRICAL MACHINES & MOTORS ---
    (
        re.compile(r'\b(induction\s+motors?|submersible\s+motors?|electric\s+motors?|rotating\s+electrical\s+machines?|motors?)\b', re.IGNORECASE),
        "electrical",
        "electrical",
        lambda m: {"category": "electric_machine", "standard_focus": "IS/IEC 60034-1"}
    ),

    # --- POWER CABLES & CONDUCTORS ---
    (
        re.compile(r'\b(underground\s+power\s+cables?|underground\s+cables?|power\s+cables?|xlpe\s+cables?|pvc\s+insulated\s+cables?|armoured\s+cables?|cables?|wiring|conductor|bus\s+trunking)\b', re.IGNORECASE),
        "material",
        "electrical",
        lambda m: {"category": "cable_distribution", "standard_focus": "IS 7098 / IS 1554"}
    ),

    # --- EARTHING & POWER APPARATUS ---
    (
        re.compile(r'\b(neutral\s+earthing|earthing|earth\s+electrode|transformer|dg\s+set|diesel\s+generator|plugs?\s+and\s+sockets?|power\s+sockets?)\b', re.IGNORECASE),
        "equipment",
        "electrical",
        lambda m: {"category": "earthing_generation", "standard_focus": "IS 3043 / IS 1293"}
    ),

    # --- LIGHTING ---
    (
        re.compile(r'\b(sports\s+lighting|floodlights?|luminaires?|light\s+fittings?|defective\s+lights?|led\s+lights?)\b', re.IGNORECASE),
        "equipment",
        "electrical",
        lambda m: {"category": "illumination", "standard_focus": "IS 10322"}
    ),

    # --- PUMPS & HYDRAULIC EQUIPMENT ---
    (
        re.compile(r'\b(process\s+water\s+pumps?|centrifugal\s+pumps?|submersible\s+pumps?|booster\s+pumps?|slurry\s+pumps?|water\s+pumps?|pumps?)\b', re.IGNORECASE),
        "product",
        "mechanical",
        lambda m: {
            "category": "pump_rotodynamic",
            "is_process": bool(re.search(r'process', m.group(0), re.IGNORECASE))
        }
    ),

    # --- VALVES & PIPING ACCESSORIES ---
    (
        re.compile(r'\b(sluice\s+valves?|gate\s+valves?|globe\s+valves?|check\s+valves?|non-return\s+valves?|butterfly\s+valves?|ball\s+valves?|air\s+valves?|pressure\s+relief\s+valves?|bib\s+taps?|stop\s+valves?|valves?)\b', re.IGNORECASE),
        "product",
        "mechanical",
        lambda m: {"category": "flow_control_valve"}
    ),

    # --- FLANGES & SEALS ---
    (
        re.compile(r'\b(steel\s+pipe\s+flanges?|flanges?|jointing\s+sheets?|asbestos\s+fiber\s+sheets?|gaskets?|flange\s+joints?)\b', re.IGNORECASE),
        "material",
        "mechanical",
        lambda m: {"category": "flange_jointing", "standard_focus": "IS 6392 / IS 2712"}
    ),

    # --- THERMAL INSULATION ---
    (
        re.compile(r'\b(thermal\s+insulation|mineral\s+wool|bonded\s+mineral\s+wool|glass\s+wool|insulation\s+work|insulation)\b', re.IGNORECASE),
        "material",
        "mechanical",
        lambda m: {"category": "thermal_insulation", "standard_focus": "IS 14164 / IS 8183"}
    ),

    # --- PIPING MATERIALS ---
    (
        re.compile(r'\b(cpvc\s+pipes?|hubless\s+pipes?|cast\s+iron\s+pipes?|gi\s+pipes?|galvanized\s+iron\s+pipes?|pvc\s+pipes?|hdpe\s+pipes?|precast\s+concrete\s+pipes?|rcc\s+pipes?|polyethylene\s+pipes?|mild\s+steel\s+pipes?|steel\s+tubes?|sewerage\s+pipelines?|sewerage\s+pipes?|pipelines?|pipes?)\b', re.IGNORECASE),
        "material",
        "piping",
        lambda m: {"category": "pipe_material"}
    ),

    # --- SANITARY WARE & FITTINGS ---
    (
        re.compile(r'\b(sanitary\s+fittings?|vitreous\s+china|vitreous\s+sanitary\s+appliances?|wash\s+basins?|water\s+closets?|urinals?|flushing\s+cisterns?)\b', re.IGNORECASE),
        "product",
        "sanitary",
        lambda m: {"category": "sanitaryware", "standard_focus": "IS 2556 / IS 774"}
    ),

    # --- CIVIL & STRUCTURAL FINISHES ---
    (
        re.compile(r'\b(ceramic\s+tiles?|vitrified\s+tiles?|glazed\s+tiles?|wall\s+tiles?|floor\s+tiles?|pressed\s+ceramic\s+tiles?|tiles?)\b', re.IGNORECASE),
        "material",
        "civil",
        lambda m: {"category": "tiles", "standard_focus": "IS 15622"}
    ),
    (
        re.compile(r'\b(cement\s+plaster|plaster\s+repairing|plastering|ordinary\s+portland\s+cement|opc|cement|concrete)\b', re.IGNORECASE),
        "material",
        "civil",
        lambda m: {"category": "cement_plaster", "standard_focus": "IS 1661 / IS 269"}
    ),
    (
        re.compile(r'\b(upvc\s+profiles?|upvc\s+partition\s+wall|partition\s+walls?)\b', re.IGNORECASE),
        "material",
        "civil",
        lambda m: {"category": "upvc_profiles", "standard_focus": "IS 16088"}
    ),

    # --- APPLICATIONS & ENVIRONMENTS ---
    (
        re.compile(r'\b(potable\s+water\s+supply|potable\s+water|drinking\s+water|water\s+supply)\b', re.IGNORECASE),
        "application",
        "water_supply",
        lambda m: {"application_type": "drinking_water"}
    ),
    (
        re.compile(r'\b(sewerage\s+pipeline|sewerage|waste\s+water|drainage|industrial\s+effluent|effluent)\b', re.IGNORECASE),
        "application",
        "sanitary_sewerage",
        lambda m: {"application_type": "sewerage_drainage"}
    ),
    (
        re.compile(r'\b(food\s+hygiene|food\s+safety|food\s+outlet|canteen|cafeteria|catering|haccp|food\s+premises)\b', re.IGNORECASE),
        "application",
        "food_safety",
        lambda m: {"application_type": "food_hygiene_haccp", "standard_focus": "IS 2491 / IS 15000"}
    ),
    (
        re.compile(r'\b(food\s+storage\s+depot|fsd|warehouse|stadium|sports\s+stadium|laboratory|cleanroom|stp|sewage\s+treatment\s+plant|hospital)\b', re.IGNORECASE),
        "application",
        "infrastructure",
        lambda m: {"facility_type": m.group(0).lower()}
    ),

    # --- INSTALLATION & EXECUTION ACTIVITIES ---
    (
        re.compile(r'\b(sitc|supply,\s+installation,\s+testing\s+and\s+commissioning|commissioning|laying\s+of|laying\s+underground|laying|erection|cable\s+laying|trenching|excavation|dismantling|shifting|reinstallation|replacement|replacing|repairing|repairs?|maint|maintenance|overhaul|renovation|upgradation)\b', re.IGNORECASE),
        "installation",
        "execution",
        lambda m: {"action": m.group(0).lower()}
    ),

    # --- TESTING & QUALITY ASSURANCE ---
    (
        re.compile(r'\b(testing|hydrostatic\s+test|pressure\s+test|dielectric\s+test|insulation\s+resistance|inspection)\b', re.IGNORECASE),
        "testing",
        "quality_assurance",
        lambda m: {"test_type": m.group(0).lower()}
    )
]


# ---------------------------------------------------------------------------
# Decomposer Engine
# ---------------------------------------------------------------------------

class CompoundRequirementDecomposer:
    """
    Deterministic rule-based technical decomposition engine.
    Extracts structured technical components, specifications, and domains from requirement strings.
    """

    def decompose(self, text: str) -> DecompositionResult:
        if not text or not text.strip():
            return DecompositionResult(original_text=text or "", components=[], decomposition_confidence=0.0)

        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        components: List[RequirementComponent] = []
        matched_spans: List[Tuple[int, int]] = []

        # Step 1: Extract numerical specifications (voltage, dimensions, ratings)
        for pattern, spec_type, domain in SPECIFICATION_PATTERNS:
            for match in pattern.finditer(cleaned_text):
                val = match.group(1).strip()
                attrs = {"spec_type": spec_type, "value": val}

                # Enhance voltage attributes
                if spec_type == "voltage":
                    kv_match = re.search(r'(\d+(?:\.\d+)?)\s*k\s*V', val, re.IGNORECASE)
                    if kv_match:
                        kv_val = float(kv_match.group(1))
                        attrs["kv"] = kv_val
                        attrs["level"] = "medium_or_high_voltage" if kv_val >= 1.0 else "low_voltage"
                    v_match = re.search(r'(\d+)\s*V\b', val, re.IGNORECASE)
                    if v_match and not kv_match:
                        v_val = int(v_match.group(1))
                        attrs["volts"] = v_val
                        attrs["level"] = "high_voltage" if v_val >= 1000 else "low_voltage"

                components.append(RequirementComponent(
                    text=val,
                    component_type="specification",
                    domain=domain,
                    extracted_attributes=attrs
                ))
                matched_spans.append((match.start(), match.end()))

        # Step 2: Extract technical entities (material, product, electrical, control, etc.)
        # Sort patterns by pattern length descending to prefer longer/more specific phrases
        seen_texts = set()
        for pattern, comp_type, domain, attr_fn in ENTITY_PATTERNS:
            for match in pattern.finditer(cleaned_text):
                match_str = match.group(0).strip()
                # Check for overlap or substring duplication
                norm_str = match_str.lower()
                if norm_str in seen_texts:
                    continue

                # Avoid adding generic "pipe" if "cpvc pipe" was already matched
                if any(norm_str in existing and norm_str != existing for existing in seen_texts):
                    continue

                seen_texts.add(norm_str)
                attrs = attr_fn(match) if attr_fn else {}

                components.append(RequirementComponent(
                    text=match_str,
                    component_type=comp_type,
                    domain=domain,
                    extracted_attributes=attrs
                ))

        # Sort components in order of appearance in original text
        def find_pos(c: RequirementComponent) -> int:
            pos = cleaned_text.lower().find(c.text.lower())
            return pos if pos >= 0 else 999

        components.sort(key=find_pos)

        # Remove redundant sub-components (e.g. "pipe" if "cpvc pipe" exists, "motors" if "water pump motors" exists)
        final_components: List[RequirementComponent] = []
        for i, c in enumerate(components):
            c_low = c.text.lower()
            is_sub = False
            for j, other in enumerate(components):
                if i != j:
                    other_low = other.text.lower()
                    if c_low != other_low and c_low in other_low and c.component_type == other.component_type:
                        is_sub = True
                        break
            if not is_sub:
                final_components.append(c)

        # Compute decomposition confidence
        # Confidence is high if at least one core noun (material, product, electrical, control) is identified
        has_core = any(c.component_type in ["material", "product", "equipment", "electrical", "control"] for c in final_components)
        has_spec_or_app = any(c.component_type in ["specification", "application"] for c in final_components)

        if has_core and has_spec_or_app:
            confidence = 1.0
        elif has_core:
            confidence = 0.90
        elif final_components:
            confidence = 0.70
        else:
            confidence = 0.30

        return DecompositionResult(
            original_text=cleaned_text,
            components=final_components,
            decomposition_confidence=round(confidence, 2)
        )


# Singleton helper function for direct module-level use
_decomposer_instance = CompoundRequirementDecomposer()

def decompose_requirement(text: str) -> DecompositionResult:
    """Convenience functional API for requirement decomposition."""
    return _decomposer_instance.decompose(text)
