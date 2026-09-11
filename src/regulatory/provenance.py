"""
Regulatory Provenance and Data Types for TenderSaathi.

Defines the evidentiary data structures, provenance levels, and strict
type representations for regulatory intelligence (BIS Product Certification,
Quality Control Orders, Compulsory Registration Scheme, and Hallmarking).

All decisions must adhere to strict provenance rules:
- OFFICIAL_PRIMARY: e-Gazette notifications, official BIS orders / circulars.
- OFFICIAL_SECONDARY: Ministry portals, official dashboard registries.
- CURATED: Verified human audit against primary gazette records.
- INFERRED: Strictly forbidden for production legal / regulatory compliance conclusions.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List


class RegulatoryProvenanceLevel(str, Enum):
    OFFICIAL_PRIMARY = "OFFICIAL_PRIMARY"
    OFFICIAL_SECONDARY = "OFFICIAL_SECONDARY"
    CURATED = "CURATED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class RegulatoryCategory(str, Enum):
    BIS_PRODUCT_CERTIFICATION = "BIS_PRODUCT_CERTIFICATION"
    QCO = "QCO"
    CRS = "CRS"
    HALLMARKING = "HALLMARKING"


class RegulatoryStatus(str, Enum):
    # Common / Specific statuses
    APPLICABLE = "APPLICABLE"
    NOT_IDENTIFIED = "NOT_IDENTIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    
    # QCO specific states
    CURRENT = "CURRENT"
    UPCOMING = "UPCOMING"
    AMENDED = "AMENDED"
    SUPERSEDED = "SUPERSEDED"


@dataclass
class RegulatoryApplicabilityResult:
    """
    Structured regulatory applicability result satisfying Requirement 10:
    - category
    - status
    - matched product
    - standard number where applicable
    - legal/evidentiary basis
    - source URL/reference
    - effective date where applicable
    - provenance
    - confidence
    - human_review_required
    - explanation
    """
    category: str
    status: str
    matched_product: str
    standard_number: str
    legal_basis: str
    source: str
    effective_date: Optional[str] = None
    provenance: str = RegulatoryProvenanceLevel.UNKNOWN.value
    confidence: float = 0.0
    human_review_required: bool = True
    explanation: str = ""
    additional_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "status": self.status,
            "matched_product": self.matched_product,
            "standard_number": self.standard_number,
            "legal_basis": self.legal_basis,
            "source": self.source,
            "source_url": self.source,  # Alias for API/UI compatibility
            "effective_date": self.effective_date,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "human_review_required": self.human_review_required,
            "explanation": self.explanation,
            "additional_metadata": self.additional_metadata,
        }
