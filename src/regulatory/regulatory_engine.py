"""
Unified Regulatory Intelligence Engine for TenderSaathi.

Orchestrates deterministic evaluation of all 4 regulatory dimensions:
1. BIS Product Certification (Scheme-I / ISI Mark)
2. Quality Control Orders (QCO)
3. Compulsory Registration Scheme (CRS)
4. Hallmarking of Precious Metals

Strictly satisfies:
- Independent of standard retrieval.
- Zero LLM involvement in regulatory decisions.
- Every result contains all 11 required fields.
- 100% deterministic, evidence-backed evaluation.
"""

from typing import Optional, Dict, Any, List

from src.regulatory.provenance import (
    RegulatoryProvenanceLevel,
    RegulatoryCategory,
    RegulatoryStatus,
    RegulatoryApplicabilityResult,
)
from src.regulatory.certification import BISCertificationEngine
from src.regulatory.qco import QCOEngine
from src.regulatory.crs import CRSEngine
from src.regulatory.hallmarking import HallmarkingEngine


class RegulatoryEngine:
    """
    Central orchestrator for TenderSaathi Regulatory Intelligence.
    """
    def __init__(
        self,
        qco_data_path: Optional[str] = None,
        crs_data_path: Optional[str] = None,
        hallmarking_data_path: Optional[str] = None,
        certification_data_path: Optional[str] = None,
    ):
        self.certification_engine = BISCertificationEngine(data_path=certification_data_path)
        self.qco_engine = QCOEngine(data_path=qco_data_path)
        self.crs_engine = CRSEngine(data_path=crs_data_path)
        self.hallmarking_engine = HallmarkingEngine(data_path=hallmarking_data_path)

    def evaluate_requirement_regulatory(
        self,
        standard_number: Optional[str],
        requirement_text: Optional[str] = None,
        as_of_date: Optional[str] = "2026-09-11"
    ) -> Dict[str, RegulatoryApplicabilityResult]:
        """
        Evaluate all four regulatory categories for a given standard number and requirement context.
        Returns a dictionary mapping category names to RegulatoryApplicabilityResult instances.
        """
        cert_res = self.certification_engine.evaluate_certification(
            standard_number=standard_number,
            product_text=requirement_text
        )

        qco_res = self.qco_engine.evaluate_qco(
            standard_number=standard_number,
            product_text=requirement_text,
            as_of_date=as_of_date
        )

        crs_res = self.crs_engine.evaluate_crs(
            standard_number=standard_number,
            product_text=requirement_text
        )

        hm_res = self.hallmarking_engine.evaluate_hallmarking(
            standard_number=standard_number,
            product_text=requirement_text
        )

        return {
            "certification": cert_res,
            "qco": qco_res,
            "crs": crs_res,
            "hallmarking": hm_res,
        }

    def evaluate_to_dict(
        self,
        standard_number: Optional[str],
        requirement_text: Optional[str] = None,
        as_of_date: Optional[str] = "2026-09-11"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate and return plain serializable dictionaries for API and UI responses.
        """
        results = self.evaluate_requirement_regulatory(
            standard_number=standard_number,
            requirement_text=requirement_text,
            as_of_date=as_of_date
        )
        return {k: v.to_dict() for k, v in results.items()}
