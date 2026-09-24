"""
Module: src/regulatory/external_authority.py
Purpose: Verified External Authority Advisory Layer (FSSAI, CEA, CPWD).

Strict architectural boundaries:
1. External authorities exist solely in this decoupled advisory registry.
2. External authorities NEVER enter standards.db or bis_catalogue.json as BIS standards.
3. External authorities CANNOT become candidate_standard.
4. Every statutory instrument is verified against official government gazettes or orders.
5. All signals carry the mandatory non-legal advisory disclaimer.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import re


STATUTORY_DISCLAIMER = (
    "Regulatory signals are advisory engineering heuristics based on published "
    "statutory frameworks and gazette notifications. They do not constitute statutory "
    "legal certifications or official compliance certificates."
)


@dataclass
class ExternalAuthoritySignal:
    """Represents a verified external statutory or ministerial regulatory signal."""
    authority_code: str                      # "FSSAI", "CEA", "CPWD"
    authority_name: str                      # Official authority name
    statutory_instrument: str                # Official gazetted regulation or specification
    applicable_clause: str                   # Section / Regulation / Clause
    related_indian_standards: List[str]      # Verified cited Indian Standards
    signal_type: str                         # "MANDATORY_STATUTORY_RULE", "ADVISORY_CODE_OF_PRACTICE"
    advisory_summary: str                    # Summary of statutory relevance to procurement
    statutory_provenance: str                # "GAZETTE_NOTIFICATION", "OFFICIAL_MANUAL"
    disclaimer: str = STATUTORY_DISCLAIMER
    review_status: str = "ADVISORY_REVIEW"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Verified statutory instruments backed by official publications
VERIFIED_STATUTORY_INSTRUMENTS = [
    {
        "authority_code": "FSSAI",
        "authority_name": "Food Safety and Standards Authority of India",
        "statutory_instrument": "Food Safety and Standards (Packaging) Regulations, 2018",
        "applicable_clause": "Regulation 4(4) and Schedule I (Food Contact Materials)",
        "related_indian_standards": ["IS 10146", "IS 10151", "IS 15000", "IS 2491"],
        "signal_type": "MANDATORY_STATUTORY_RULE",
        "advisory_summary": (
            "FSSAI Packaging Regulations mandate that plastics and materials in direct contact "
            "with food or potable water must comply with prescribed Indian Standards (IS 10146 / "
            "IS 10151). Food handling premises require HACCP and hygiene compliance aligned with IS 2491."
        ),
        "statutory_provenance": "GAZETTE_NOTIFICATION",
        "domain_keywords": ["food", "canteen", "catering", "haccp", "kitchen", "hygiene", "packaging", "potable water"],
        "std_patterns": [r"15000", r"2491", r"10146", r"10151"]
    },
    {
        "authority_code": "CEA",
        "authority_name": "Central Electricity Authority",
        "statutory_instrument": "CEA (Measures relating to Safety and Electric Supply) Regulations, 2023",
        "applicable_clause": "Regulations 29, 35, 43, 67 (Earthing, Cable Laying & Substation Safety)",
        "related_indian_standards": ["IS 3043", "IS 732", "IS 1255", "IS 7098", "IS 2026", "IS 1180"],
        "signal_type": "MANDATORY_STATUTORY_RULE",
        "advisory_summary": (
            "CEA Safety Regulations mandate strict adherence to Indian Standards for electrical system "
            "earthing (IS 3043), wiring installation execution (IS 732), underground power cable installation "
            "(IS 1255), and distribution transformers (IS 1180 / IS 2026) in public and industrial supplies."
        ),
        "statutory_provenance": "GAZETTE_NOTIFICATION",
        "domain_keywords": ["cable", "wiring", "electrical", "earthing", "transformer", "switchgear", "substation", "xlpe"],
        "std_patterns": [r"7098", r"3043", r"732", r"1255", r"1180", r"2026", r"694"]
    },
    {
        "authority_code": "CPWD",
        "authority_name": "Central Public Works Department",
        "statutory_instrument": "CPWD Specifications 2019 / 2023 (Civil & Electrical Works)",
        "applicable_clause": "Section 19 (Water Supply), Section 20 (Drainage), Section 31 (Electrical)",
        "related_indian_standards": ["IS 458", "IS 783", "IS 1239", "IS 4985", "IS 15778", "IS 15905", "IS 732"],
        "signal_type": "ADVISORY_CODE_OF_PRACTICE",
        "advisory_summary": (
            "CPWD Works Specifications govern execution, laying, jointing and testing of water supply pipelines, "
            "sewerage conduits and electrical installations for central works, mandating compliance with "
            "IS 783 (laying concrete pipes), IS 15778 (CPVC plumbing), and IS 1239 (mild steel piping)."
        ),
        "statutory_provenance": "OFFICIAL_MANUAL",
        "domain_keywords": ["pipe", "piping", "plumbing", "drainage", "sewerage", "laying", "jointing", "cpwd", "civil"],
        "std_patterns": [r"458", r"783", r"1239", r"4985", r"15778", r"15905", r"8329"]
    }
]


class ExternalAuthorityRegistry:
    """
    Registry for verified statutory advisory signals.
    Provides external regulatory context without contaminating BIS standards catalogue.
    """

    def __init__(self):
        self.instruments = VERIFIED_STATUTORY_INSTRUMENTS

    def get_signals_for_requirement(
        self,
        requirement_text: str,
        candidate_standard: Optional[str] = None
    ) -> List[ExternalAuthoritySignal]:
        """
        Retrieves matching external authority signals based on requirement text
        and recommended candidate standard.
        """
        text_lower = (requirement_text or "").lower()
        cand_norm = (candidate_standard or "").upper()

        matched_signals: List[ExternalAuthoritySignal] = []

        for inst in self.instruments:
            # Check domain keywords
            kw_match = any(kw in text_lower for kw in inst["domain_keywords"])

            # Check candidate standard number
            std_match = False
            if cand_norm:
                std_match = any(re.search(pat, cand_norm) for pat in inst["std_patterns"])

            if kw_match or std_match:
                matched_signals.append(ExternalAuthoritySignal(
                    authority_code=inst["authority_code"],
                    authority_name=inst["authority_name"],
                    statutory_instrument=inst["statutory_instrument"],
                    applicable_clause=inst["applicable_clause"],
                    related_indian_standards=inst["related_indian_standards"],
                    signal_type=inst["signal_type"],
                    advisory_summary=inst["advisory_summary"],
                    statutory_provenance=inst["statutory_provenance"],
                    disclaimer=STATUTORY_DISCLAIMER
                ))

        return matched_signals

    def match_signals(
        self,
        requirement_text: str,
        candidate_standard: Optional[str] = None
    ) -> List[ExternalAuthoritySignal]:
        """Convenience alias for get_signals_for_requirement."""
        return self.get_signals_for_requirement(requirement_text, candidate_standard)

    def get_signals_as_dicts(
        self,
        requirement_text: str,
        candidate_standard: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Convenience method returning serialized dictionary list."""
        signals = self.get_signals_for_requirement(requirement_text, candidate_standard)
        return [s.to_dict() for s in signals]
