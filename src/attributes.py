"""
Module: src/attributes.py
Purpose: Generalized attribute extraction for Ambiguity Engine V2.1.
Derives comparable attributes from catalogue metadata and tender text to drive
generalizable technical discriminators without relying on hardcoded standard numbers.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import re

@dataclass
class StandardAttributes:
    product_family: str = "Unknown"
    material: Optional[str] = None
    voltage_rating: Optional[str] = None
    insulation: Optional[str] = None
    pump_type: Optional[str] = None
    valve_type: Optional[str] = None
    power_rating: Optional[str] = None
    grade_or_class: Optional[str] = None
    phase: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def _extract_material(text: str) -> Optional[str]:
    text = text.lower()
    materials = {
        "xlpe": ["xlpe", "cross linked polyethylene", "cross-linked polyethylene", "crosslinked polyethylene"],
        "pvc": ["pvc", "polyvinyl chloride"],
        "cpvc": ["cpvc", "chlorinated polyvinyl chloride"],
        "upvc": ["upvc", "unplasticized pvc"],
        "hdpe": ["hdpe", "high density polyethylene"],
        "ductile iron": ["di", "ductile iron", "spheroidal graphite iron"],
        "cast iron": ["ci", "cast iron", "sluice"],
        "mild steel": ["ms", "mild steel"],
        "stainless steel": ["ss", "stainless steel"],
        "brass": ["brass"],
        "gunmetal": ["gunmetal", "leaded tin bronze"],
        "galvanized iron": ["gi", "galvanized iron", "galvanised iron"],
        "aluminium": ["aluminium", "aluminum"],
        "copper": ["copper"],
        "vitreous china": ["vitreous china", "vitreous sanitary"],
        "elastomeric": ["elastomer", "rubber", "epdm", "nitrile", "neoprene"],
        "concrete": ["concrete", "rcc", "pcc"]
    }
    for mat, keywords in materials.items():
        if any(re.search(rf"\b{re.escape(k)}\b", text) for k in keywords):
            return mat
    return None

def _extract_voltage(text: str) -> Optional[str]:
    text = text.lower()
    lv_keywords = ["lv", "low voltage", "up to 1100 v", "1100 v", "415 v", "415v", "240v"]
    if any(re.search(rf"\b{re.escape(w)}\b", text) for w in lv_keywords):
        return "LV"
    hv_keywords = ["mv", "hv", "medium voltage", "high voltage", "3.3 kv", "11 kv", "33 kv", "66 kv"]
    if any(re.search(rf"\b{re.escape(w)}\b", text) for w in hv_keywords):
        return "MV/HV"
    return None

def _extract_product_family(text: str) -> str:
    text = text.lower()
    if "cable" in text: return "cable"
    if "valve" in text: return "valve"
    if "pump" in text: return "pump"
    if "pipe" in text or "tube" in text: return "pipe"
    if "motor" in text: return "motor"
    if any(w in text for w in ["switchgear", "panel", "distribution board", "vfd", "power drive"]): return "panel"
    if "cement" in text: return "cement"
    if "transformer" in text: return "transformer"
    if "flange" in text: return "flange"
    if "gasket" in text: return "gasket"
    if any(w in text for w in ["bib tap", "pillar tap", "stop tap"]): return "tap"
    if "cistern" in text: return "cistern"
    if any(w in text for w in ["sanitary", "closet", "wash basin", "urinal"]): return "sanitaryware"
    if "luminaire" in text or "lighting" in text: return "luminaire"
    return "other"

def extract_standard_attributes(standard_number: str, title: str, scope: str = "") -> StandardAttributes:
    """Derives attributes from standard metadata."""
    combined = f"{title} {scope}"
    attrs = StandardAttributes()
    attrs.product_family = _extract_product_family(combined)
    attrs.material = _extract_material(combined)
    attrs.voltage_rating = _extract_voltage(combined)
    
    # Specifics
    combined_low = combined.lower()
    if "submersible" in combined_low: attrs.pump_type = "submersible"
    elif "centrifugal" in combined_low: attrs.pump_type = "centrifugal"
    
    if "gate" in combined_low or "sluice" in combined_low: attrs.valve_type = "gate"
    elif "butterfly" in combined_low: attrs.valve_type = "butterfly"
    elif "check" in combined_low or "non-return" in combined_low: attrs.valve_type = "check"
    elif "globe" in combined_low: attrs.valve_type = "globe"
    elif "ball" in combined_low: attrs.valve_type = "ball"
    elif "air" in combined_low and "valve" in combined_low: attrs.valve_type = "air"
    
    if "3 phase" in combined_low or "three phase" in combined_low or "three-phase" in combined_low: attrs.phase = "3-phase"
    elif "1 phase" in combined_low or "single phase" in combined_low or "single-phase" in combined_low: attrs.phase = "1-phase"

    if "opc" in combined_low or "ordinary portland" in combined_low: attrs.grade_or_class = "OPC"
    elif "ppc" in combined_low or "pozzolana portland" in combined_low: attrs.grade_or_class = "PPC"
    elif "psc" in combined_low or "slag cement" in combined_low: attrs.grade_or_class = "PSC"

    if "vfd" in combined_low or "variable frequency" in combined_low or "power drive" in combined_low: attrs.product_family = "vfd"

    return attrs

def extract_tender_attributes(tender_text: str) -> StandardAttributes:
    """Extracts available parameters from the tender requirement text."""
    # For now, it shares the same extraction logic as standards, 
    # but in a real-world scenario, this might use NER or an LLM call.
    return extract_standard_attributes("TENDER", tender_text, "")

def same_procurement_object(attr_a: StandardAttributes, attr_b: StandardAttributes) -> bool:
    """
    Checks if two standards describe roughly the same item.
    If product_families differ and neither is 'other', they don't compete.
    e.g., A 'flange' does not compete with a 'gasket'.
    """
    if attr_a.product_family != attr_b.product_family:
        if attr_a.product_family != "other" and attr_b.product_family != "other":
            return False
    return True

def find_discriminators(attr_a: StandardAttributes, attr_b: StandardAttributes) -> List[str]:
    """
    Returns a list of attribute keys where the two candidates have conflicting specified values.
    """
    dict_a = attr_a.to_dict()
    dict_b = attr_b.to_dict()
    discriminators = []
    
    for key in dict_a.keys():
        if key == "product_family": continue
        if key in dict_b and dict_a[key] != dict_b[key]:
            discriminators.append(key)
    
    return discriminators

def discriminator_specified_in_tender(discriminator: str, tender_attrs: StandardAttributes) -> bool:
    """Checks if the tender provides the value for a given discriminator."""
    dict_t = tender_attrs.to_dict()
    return discriminator in dict_t
