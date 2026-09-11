"""
Module: src/catalogue/provenance.py
Purpose: Strict provenance tracking, source priority, and evidentiary validation
for the Indian Standards catalogue.

Hierarchy:
  OFFICIAL_PRIMARY   -> Direct BIS / Government of India source
  OFFICIAL_SECONDARY -> Official BIS-derived structured publications
  CURATED            -> Manually verified / reviewed project engineering data
  INFERRED           -> Algorithmically derived (NEVER presented as authoritative fact)
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


class ProvenanceLevel(str, Enum):
    OFFICIAL_PRIMARY = "OFFICIAL_PRIMARY"
    OFFICIAL_SECONDARY = "OFFICIAL_SECONDARY"
    VERIFIED = "VERIFIED"
    CURATED = "CURATED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def is_valid(cls, val: str) -> bool:
        return val in cls._value2member_map_

    def rank(self) -> int:
        """Higher integer indicates higher evidentiary authority."""
        ranking = {
            ProvenanceLevel.OFFICIAL_PRIMARY: 4,
            ProvenanceLevel.VERIFIED: 4,
            ProvenanceLevel.OFFICIAL_SECONDARY: 3,
            ProvenanceLevel.CURATED: 2,
            ProvenanceLevel.INFERRED: 1,
            ProvenanceLevel.UNKNOWN: 0,
        }
        return ranking.get(self, 0)


class SourcePriority(int, Enum):
    """
    Source priority hierarchy for Indian Standards:
    1. BIS official standards portal (standardsbis.bsbedge.com / bis.gov.in)
    2. BIS Know Your Standard
    3. BIS official published documents / Gazette notifications
    4. Other Government of India authoritative ministry publications
    """
    BIS_PORTAL = 1
    BIS_KNOW_YOUR_STANDARD = 2
    BIS_GAZETTE_OR_OFFICIAL_DOC = 3
    GOI_MINISTRY_AUTHORITATIVE = 4
    CURATED_PROJECT_DATA = 5
    DISCOVERY_AID_UNOFFICIAL = 99


# Explicit whitelist of permitted authoritative source types
PERMITTED_SOURCE_TYPES = {
    "BIS_OFFICIAL_PORTAL",
    "BIS_KNOW_YOUR_STANDARD",
    "BIS_GAZETTE_NOTIFICATION",
    "GOI_MINISTRY_QCO_GAZETTE",
    "BIS_CRS_REGISTRY",
    "BIS_HALLMARKING_REGISTRY",
    "BIS_PRODUCT_CERTIFICATION_REGISTRY",
    "CPWD_OFFICIAL_SPECIFICATION",
    "CURATED_EXCEL_REPO",
    "VALIDATED_RESEARCH_BIS_CATALOGUE",
    "BSB_EDGE_MANUALLY_VERIFIED",
    "OFFLINE_EXPORT_AUTHORITATIVE",
}

# Explicit blacklist of disallowed sources for authoritative production claims
DISALLOWED_AUTHORITATIVE_SOURCES = {
    "WIKIPEDIA",
    "BLOG",
    "COMMERCIAL_RESELLER",
    "UNOFFICIAL_SCRAPE",
    "LLM_GENERATION",
}


@dataclass
class CatalogueSourceInfo:
    """Source attribution with strict audit trail."""
    source_type: str                          # e.g. "BIS_OFFICIAL_PORTAL", "GOI_MINISTRY_QCO_GAZETTE"
    source_url: Optional[str] = None          # Official URL or gazette URI
    retrieved_at: Optional[str] = None        # ISO timestamp
    provenance: str = ProvenanceLevel.OFFICIAL_PRIMARY.value
    confidence: float = 1.0                   # 1.0 for Primary, 0.85 for Curated, 0.5 for Inferred
    source_citation: Optional[str] = None     # Gazette/order number or document reference
    verification_notes: Optional[str] = None

    def validate(self) -> List[str]:
        """Validates source attribution compliance."""
        errors = []
        if not self.source_type:
            errors.append("source_type must not be empty.")
        if self.source_type.upper() in DISALLOWED_AUTHORITATIVE_SOURCES:
            errors.append(f"Source type '{self.source_type}' is disallowed as authoritative evidence.")
        if not ProvenanceLevel.is_valid(self.provenance):
            errors.append(f"Invalid provenance level '{self.provenance}'.")
        if self.provenance == ProvenanceLevel.INFERRED.value and self.confidence > 0.6:
            errors.append("INFERRED provenance confidence must not exceed 0.6.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def assert_no_inferred_as_authoritative(provenance: str, context: str = ""):
    """Guards against presenting algorithmic or inferred data as official fact."""
    if provenance == ProvenanceLevel.INFERRED.value:
        raise ValueError(
            f"INFERRED provenance data cannot be presented as authoritative fact! Context: {context}"
        )
