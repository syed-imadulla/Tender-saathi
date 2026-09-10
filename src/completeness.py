"""
Module: src/completeness.py
Purpose: Specification Review Completeness Analyzer for procurement requirements.

Analyzes whether an extracted procurement requirement contains key technical engineering
parameters necessary for definitive standard determination across domains (valves, pipes,
cables, motors, pumps, switchgear, food hygiene, etc.).

Distinguishes parameter states:
- KNOWN: Parameter value explicitly identified in the requirement or decomposed components.
- POTENTIALLY_MISSING: Parameter typically required for precise sizing/material discrimination but absent.
- UNKNOWN: Cannot be determined from the available text.
- NOT_APPLICABLE: Parameter not relevant for this particular item type.

IMPORTANT:
This module evaluates 'Specification Review Completeness'. It does NOT declare tenders
to be 'invalid', 'non-compliant', or 'legally incomplete'.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set
import re
from src.decompose import RequirementComponent


@dataclass
class ParameterAssessment:
    name: str
    display_name: str
    status: str                         # KNOWN, POTENTIALLY_MISSING, UNKNOWN, NOT_APPLICABLE
    extracted_value: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpecificationCompletenessReport:
    domain: str
    parameters: Dict[str, ParameterAssessment]
    known_count: int
    potentially_missing_count: int
    completeness_score: float                # [0, 1]
    is_adequately_specified: bool
    potentially_missing_parameters: List[str]
    summary: str
    critical_missing_count: int = 0

    @property
    def completeness_label(self) -> str:
        """Returns non-legalistic state label."""
        if not self.parameters:
            return "NOT_APPLICABLE"
        if self.known_count == 0:
            return "UNKNOWN"
        if self.potentially_missing_count > 0:
            return "POTENTIALLY_MISSING"
        return "KNOWN"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
            "known_count": self.known_count,
            "potentially_missing_count": self.potentially_missing_count,
            "completeness_score": round(self.completeness_score, 2),
            "is_adequately_specified": self.is_adequately_specified,
            "potentially_missing_parameters": self.potentially_missing_parameters,
            "summary": self.summary,
            "completeness_label": self.completeness_label,
            "critical_missing_count": self.critical_missing_count
        }


# ---------------------------------------------------------------------------
# Domain Parameter Definitions & Extraction Regexes
# ---------------------------------------------------------------------------

DOMAIN_DEFINITIONS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "valve": {
        "valve_type": {
            "display": "Valve Type",
            "regex": r'\b(sluice|gate|globe|check|ball|butterfly|air\s*release|non[-\s]*return|nrv|foot|pressure\s*reducing|prv|control|diaphragm|needle)\s*valves?\b',
            "critical": True
        },
        "nominal_size": {
            "display": "Nominal Size / Diameter (DN)",
            "regex": r'\b(?:dn\s*\d+|\d+\s*mm\s*(?:dia|diameter|nb|dn)?|\d+(?:\.\d+)?\s*(?:inch|in|\")|size\s*[:\-]?\s*\d+)\b',
            "critical": True
        },
        "pressure_rating": {
            "display": "Pressure Rating (PN / Class)",
            "regex": r'\b(?:pn\s*\d+|class\s*\d+|\d+\s*(?:bar|kg\s*/\s*cm2|psi|kpa|mpa)|rating\s*[:\-]?\s*(?:pn|class)?\s*\d+)\b',
            "critical": True
        },
        "body_material": {
            "display": "Body Metallurgy / Material",
            "regex": r'\b(cast\s*iron|ci|ductile\s*iron|di|bronze|gunmetal|brass|forged\s*steel|cast\s*steel|stainless\s*steel|ss\s*304|ss\s*316|copper\s*alloy|carbon\s*steel)\b',
            "critical": True
        },
        "fluid_medium": {
            "display": "Fluid Medium / Service",
            "regex": r'\b(potable\s*water|raw\s*water|drinking\s*water|sewage|wastewater|effluent|slurry|steam|oil|gas|chemical|cooling\s*water)\b',
            "critical": False
        }
    },
    "pipe": {
        "material": {
            "display": "Piping Material",
            "regex": r'\b(cpvc|upvc|pvc|hdpe|mdpe|polyethylene|di|ductile\s*iron|ci|cast\s*iron|gi|galvanized\s*iron|mild\s*steel|ms|precast\s*concrete|rcc|stoneware|copper|ss|stainless\s*steel)\b',
            "critical": True
        },
        "diameter": {
            "display": "Diameter / Nominal Bore (DN/OD)",
            "regex": r'\b(?:dn\s*\d+|\d+\s*mm\s*(?:dia|diameter|nb|od|dn)?|\d+(?:\.\d+)?\s*(?:inch|in|\")|outer\s*diameter\s*\d+)\b',
            "critical": False
        },
        "pressure_class": {
            "display": "Pressure Class / Schedule / SDR",
            "regex": r'\b(?:pn\s*\d+|class\s*(?:1|2|3|4|5|a|b|c|np\d)|sdr\s*\d+|sch(?:edule)?\s*\d+|\d+\s*(?:bar|kg\s*/\s*cm2|kpa|mpa))\b',
            "critical": False
        },
        "application": {
            "display": "Piping Application / Service",
            "regex": r'\b(water\s*supply|potable|drinking\s*water|hot\s*and\s*cold|sewerage|drainage|irrigation|plumbing|sanitary|industrial\s*effluent|gas|fire\s*fighting)\b',
            "critical": True
        }
    },
    "cable": {
        "voltage_rating": {
            "display": "Voltage Grade",
            "regex": r'\b(?:1\.1\s*kv|3\.3\s*kv|6\.6\s*kv|11\s*kv|22\s*kv|33\s*kv|66\s*kv|lt|ht|extra\s*high\s*tension|eht|low\s*tension|high\s*tension)\b',
            "critical": True
        },
        "conductor_material": {
            "display": "Conductor Material",
            "regex": r'\b(copper|aluminium|aluminum|cu|al)\b',
            "critical": True
        },
        "insulation_type": {
            "display": "Insulation Material",
            "regex": r'\b(xlpe|pvc|rubber|fep|ptfe|cross[-\s]*linked\s*polyethylene)\b',
            "critical": True
        },
        "cores_size": {
            "display": "Number of Cores & Cross-section",
            "regex": r'\b(?:\d+\s*(?:core|c)\s*x\s*\d+(?:\.\d+)?\s*(?:sq\s*mm|sqmm|mm2)|\d+\s*core|\d+(?:\.\d+)?\s*(?:sq\s*mm|sqmm|mm2))\b',
            "critical": False
        },
        "armouring": {
            "display": "Armouring Type",
            "regex": r'\b(armoured|armored|unarmoured|unarmored|strip\s*armoured|wire\s*armoured)\b',
            "critical": False
        }
    },
    "motor": {
        "voltage_rating": {
            "display": "Operating Voltage",
            "regex": r'\b(?:415\s*v|400\s*v|3\.3\s*kv|6\.6\s*kv|11\s*kv|230\s*v|lt|ht|medium\s*voltage|mv)\b',
            "critical": True
        },
        "power_rating": {
            "display": "Rated Output / Power",
            "regex": r'\b(?:\d+(?:\.\d+)?\s*(?:kw|hp|mw))\b',
            "critical": True
        },
        "speed_rpm": {
            "display": "Synchronous Speed / Pole count",
            "regex": r'\b(?:\d+\s*rpm|\d+\s*pole|\b2p\b|\b4p\b|\b6p\b)\b',
            "critical": False
        },
        "phase_frequency": {
            "display": "Phase & Supply Frequency",
            "regex": r'\b(3\s*phase|three\s*phase|single\s*phase|1\s*phase|50\s*hz)\b',
            "critical": False
        },
        "enclosure_type": {
            "display": "Enclosure / Duty Type",
            "regex": r'\b(tefc|flame\s*proof|submersible|ip\s*\d{2}|s1\s*duty|continuous\s*duty)\b',
            "critical": False
        }
    },
    "pump": {
        "pump_type": {
            "display": "Pump Mechanism / Type",
            "regex": r'\b(centrifugal|submersible|monobloc|vertical\s*turbine|split\s*case|end\s*suction|slurry|sewage|booster|horizontal|positive\s*displacement)\b',
            "critical": True
        },
        "flow_discharge": {
            "display": "Discharge / Flow Rate (Q)",
            "regex": r'\b(?:\d+(?:\.\d+)?\s*(?:lps|lpm|m3\s*/\s*hr|m3\s*/\s*h|cumec|gpm|flow))\b',
            "critical": False
        },
        "head": {
            "display": "Total Dynamic Head (H)",
            "regex": r'\b(?:\d+(?:\.\d+)?\s*(?:mwc|meters?\s*head|m\s*head|head\s*range))\b',
            "critical": False
        },
        "motor_details": {
            "display": "Motor Coupling / Prime Mover",
            "regex": r'\b(?:coupled\s*with|motor\s*rating|\d+\s*(?:kw|hp)\s*motor|\d+\s*kv\s*motor)\b',
            "critical": True
        },
        "application": {
            "display": "Process Application",
            "regex": r'\b(water\s*supply|process\s*water|drainage|dewatering|irrigation|agriculture|cooling|fire\s*fighting|sewage)\b',
            "critical": True
        }
    },
    "switchgear_panel": {
        "system_voltage": {
            "display": "System Nominal Voltage",
            "regex": r'\b(?:415\s*v|400\s*v|11\s*kv|3\.3\s*kv|6\.6\s*kv|230\s*v|lt|ht|mv)\b',
            "critical": True
        },
        "current_rating": {
            "display": "Busbar / Incomer Current Rating",
            "regex": r'\b(?:\d+\s*(?:a|amp|amps|amperes)|busbar\s*\d+\s*a|\d+\s*ka\s*breaking)\b',
            "critical": False
        },
        "control_drive": {
            "display": "Control Mechanism / Variable Speed Drive",
            "regex": r'\b(vfd|variable\s*frequency\s*drive|vfd\s*panel|dol|star[-\s]*delta|soft\s*starter|mcc|pcc|plc)\b',
            "critical": True
        },
        "enclosure_ip": {
            "display": "Enclosure Ingress Protection (IP)",
            "regex": r'\b(ip\s*42|ip\s*54|ip\s*55|ip\s*65|indoor|outdoor|compartmentalized)\b',
            "critical": False
        }
    },
    "food_hygiene": {
        "establishment_type": {
            "display": "Food Establishment Type",
            "regex": r'\b(canteen|cafeteria|restaurant|kiosk|food\s*outlet|catering|processing\s*unit|mess)\b',
            "critical": True
        },
        "operation_scope": {
            "display": "Food Preparation Scope",
            "regex": r'\b(cooking|storage|handling|hygiene|serving|catering|distribution|packaging)\b',
            "critical": True
        },
        "regulatory_mode": {
            "display": "Regulatory Hygiene Framework",
            "regex": r'\b(haccp|gmp|ghp|food\s*safety|hygiene\s*practices|fssai|is\s*2491|is\s*15000)\b',
            "critical": False
        }
    }
}


class DomainCompletenessAnalyzer:
    """Analyzes technical parameter completeness for tender specifications."""

    def detect_domain(
        self,
        text: str,
        components: Optional[List[RequirementComponent]] = None
    ) -> str:
        """Determines the primary engineering domain of the requirement."""
        t_low = text.lower()
        
        # Check components first if available
        if components:
            for c in components:
                c_low = c.text.lower()
                if any(k in c_low for k in ["valve", "sluice", "nrv"]):
                    return "valve"
                if any(k in c_low for k in ["pipe", "piping", "tubing"]):
                    return "pipe"
                if any(k in c_low for k in ["cable", "conductor", "wire"]):
                    return "cable"
                if any(k in c_low for k in ["panel", "switchgear", "vfd"]):
                    return "switchgear_panel"
                if any(k in c_low for k in ["pump", "pumping", "booster"]):
                    # If coupled with motor or panel, check specificity
                    if "panel" in t_low or "vfd" in t_low:
                        return "switchgear_panel"
                    if "motor" in t_low and "3.3" in t_low:
                        return "pump"
                    return "pump"
                if any(k in c_low for k in ["canteen", "cafeteria", "hygiene", "food"]):
                    return "food_hygiene"

        # Regex fallback on raw text
        if re.search(r'\b(?:valves?|sluice|nrv)\b', t_low):
            return "valve"
        if re.search(r'\b(?:vfd.*panel|control\s*panel|switchgear|switchboard|mcc|pcc)\b', t_low):
            return "switchgear_panel"
        if re.search(r'\b(?:pumps?|pumping|submersible)\b', t_low):
            return "pump"
        if re.search(r'\b(?:pipes?|piping|pipeline)\b', t_low):
            return "pipe"
        if re.search(r'\b(?:cables?|wires?|conductors?)\b', t_low):
            return "cable"
        if re.search(r'\b(?:motors?|induction\s*motor)\b', t_low):
            return "motor"
        if re.search(r'\b(?:food|canteen|cafeteria|catering|hygiene)\b', t_low):
            return "food_hygiene"

        return "general"

    def analyze(
        self,
        text: str,
        components: Optional[List[RequirementComponent]] = None,
        domain_override: Optional[str] = None
    ) -> SpecificationCompletenessReport:
        """
        Evaluates specification review completeness for the given text.
        Extracts known parameters and identifies potentially missing parameters.
        """
        domain = domain_override or self.detect_domain(text, components)
        param_defs = DOMAIN_DEFINITIONS.get(domain, {})

        if not param_defs:
            return SpecificationCompletenessReport(
                domain=domain,
                parameters={},
                known_count=0,
                potentially_missing_count=0,
                completeness_score=1.0,
                is_adequately_specified=True,
                potentially_missing_parameters=[],
                summary="General procurement requirement; standard parameter schema not applicable."
            )

        combined_text = text
        if components:
            combined_text += " " + " ".join(f"{c.component_type}:{c.text}" for c in components)

        assessments: Dict[str, ParameterAssessment] = {}
        known_count = 0
        potentially_missing: List[str] = []
        critical_missing_count = 0

        for p_name, p_spec in param_defs.items():
            display = p_spec["display"]
            rgx = p_spec["regex"]
            is_critical = p_spec["critical"]

            match = re.search(rgx, combined_text, re.IGNORECASE)
            if match:
                extracted = match.group(0).strip()
                assessments[p_name] = ParameterAssessment(
                    name=p_name,
                    display_name=display,
                    status="KNOWN",
                    extracted_value=extracted,
                    notes=f"Identified in specification text: '{extracted}'"
                )
                known_count += 1
            else:
                assessments[p_name] = ParameterAssessment(
                    name=p_name,
                    display_name=display,
                    status="POTENTIALLY_MISSING",
                    extracted_value=None,
                    notes="Parameter not found in procurement clause."
                )
                potentially_missing.append(display)
                if is_critical:
                    critical_missing_count += 1

        total_tracked = len(param_defs)
        completeness_ratio = known_count / total_tracked if total_tracked > 0 else 1.0

        # Specification adequacy for technical standard identification
        if domain == "pipe":
            # For piping, knowing the material (e.g. CPVC, HDPE, Concrete) is the primary determinant of the product standard
            has_material = assessments.get("material", ParameterAssessment("", "", "POTENTIALLY_MISSING")).status == "KNOWN"
            has_app = assessments.get("application", ParameterAssessment("", "", "POTENTIALLY_MISSING")).status == "KNOWN"
            is_adequate = has_material or (has_app and known_count >= 2)
        elif domain == "valve":
            # For valves, knowing at least 2 parameters (such as valve type and material or application) is needed to avoid ambiguity
            is_adequate = known_count >= 2
        elif domain == "pump":
            is_adequate = (critical_missing_count <= 1) and (known_count >= 2)
        elif domain == "switchgear_panel":
            is_adequate = known_count >= 1
        else:
            is_adequate = (critical_missing_count <= 1) and (completeness_ratio >= 0.40)

        # Summary note using safe non-legalistic language
        if is_adequate:
            summary = (
                f"Specification contains {known_count}/{total_tracked} key domain parameters. "
                "Adequate technical context for standard recommendation."
            )
        else:
            summary = (
                f"Specification lacks {len(potentially_missing)} engineering parameters "
                f"({', '.join(potentially_missing[:3])}). Specification review recommended prior to procurement."
            )

        return SpecificationCompletenessReport(
            domain=domain,
            parameters=assessments,
            known_count=known_count,
            potentially_missing_count=len(potentially_missing),
            completeness_score=completeness_ratio,
            is_adequately_specified=is_adequate,
            potentially_missing_parameters=potentially_missing,
            summary=summary,
            critical_missing_count=critical_missing_count
        )
