"""
Regulatory subsystem for TenderSaathi.
Provides deterministic, evidence-backed evaluation for:
- BIS Product Certification (Scheme-I / ISI mark)
- Quality Control Orders (QCO)
- Compulsory Registration Scheme (CRS)
- Hallmarking
"""

from src.regulatory.provenance import (
    RegulatoryProvenanceLevel,
    RegulatoryCategory,
    RegulatoryStatus,
    RegulatoryApplicabilityResult,
)

__all__ = [
    "RegulatoryProvenanceLevel",
    "RegulatoryCategory",
    "RegulatoryStatus",
    "RegulatoryApplicabilityResult",
]
