"""
BIS Product Certification (Scheme-I / ISI Mark) Engine for TenderSaathi.

Evaluates applicability of BIS Product Certification Scheme-I (ISI Mark) under
the Bureau of Indian Standards (Conformity Assessment) Regulations, 2018.

Strict rules enforced per Requirements 3 & 6:
- Do NOT treat the existence of an Indian Standard as proof that BIS certification is mandatory.
- Certification applicability must be based on authoritative BIS/product-certification evidence.
- Never guess. Zero LLM involvement.
"""

import json
import os
from typing import Optional, Dict, Any, List

from src.regulatory.provenance import (
    RegulatoryProvenanceLevel,
    RegulatoryCategory,
    RegulatoryStatus,
    RegulatoryApplicabilityResult,
)
from src.catalogue.normalizer import StandardIdentifierNormalizer


class BISCertificationEngine:
    """
    Deterministic evaluation engine for BIS Product Certification (Scheme-I / ISI Mark).
    """
    DEFAULT_DATA_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "regulatory", "certification", "certification_master.json"
    )

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self.normalizer = StandardIdentifierNormalizer()
        self.mandatory_standards: List[Dict[str, Any]] = []
        self._standard_map: Dict[str, Dict[str, Any]] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not os.path.exists(self.data_path):
            self.mandatory_standards = []
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.mandatory_standards = data.get("mandatory_scheme_i_standards", [])
        self._standard_map = {}

        for item in self.mandatory_standards:
            std_num = item.get("standard_number", "")
            base_std = item.get("base_standard", "")

            keys = set()
            if std_num:
                keys.add(self.normalizer.normalize_identifier(std_num))
                keys.add(std_num.strip().upper())
            if base_std:
                keys.add(self.normalizer.normalize_identifier(base_std))
                keys.add(base_std.strip().upper())

            # Also index bare base number without parts
            parsed = self.normalizer.parse(std_num or base_std)
            if parsed.base_number:
                bare_slug = f"{parsed.prefix.replace('/', '-')}-{parsed.base_number}"
                bare_num = f"{parsed.prefix} {parsed.base_number}"
                keys.add(bare_slug)
                keys.add(bare_num.upper())

            for k in keys:
                self._standard_map[k] = item

    def evaluate_certification(
        self,
        standard_number: Optional[str] = None,
        product_text: Optional[str] = None
    ) -> RegulatoryApplicabilityResult:
        """
        Evaluate BIS Product Certification applicability.
        Adheres to Requirement 3: An IS number alone NEVER implies mandatory certification.
        """
        norm_id = self.normalizer.normalize_identifier(standard_number) if standard_number else ""
        match = (self._standard_map.get(norm_id) or self._standard_map.get(standard_number.strip().upper())) if norm_id else None

        if not match and standard_number and ":" in standard_number:
            base_part = standard_number.split(":")[0].strip()
            base_norm = self.normalizer.normalize_identifier(base_part)
            match = self._standard_map.get(base_norm) or self._standard_map.get(base_part.upper())

        # If no match on candidate standard, check if product_text explicitly cites a mandatory certified standard
        if not match and product_text:
            import re
            text_stds = re.findall(r'\b(IS\s*(?:/\s*IEC)?\s*\d+(?:\s*(?:\(Part\s*\d+\)|Part\s*\d+))?)\b', product_text, flags=re.IGNORECASE)
            for ts in text_stds:
                ts_norm = self.normalizer.normalize_identifier(ts)
                m = self._standard_map.get(ts_norm) or self._standard_map.get(ts.strip().upper())
                if m:
                    match = m
                    standard_number = ts
                    break

        if not match:
            if not standard_number or not standard_number.strip():
                return RegulatoryApplicabilityResult(
                    category=RegulatoryCategory.BIS_PRODUCT_CERTIFICATION.value,
                    status=RegulatoryStatus.UNKNOWN.value,
                    matched_product="",
                    standard_number="",
                    legal_basis="Bureau of Indian Standards Act, 2016",
                    source="https://www.manakonline.in",
                    effective_date=None,
                    provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                    confidence=0.5,
                    human_review_required=True,
                    explanation="No Indian Standard provided to establish BIS Product Certification status."
                )

        if match:
            prod_name = match.get("product_name", "")
            scheme = match.get("scheme", "Scheme-I (ISI Mark)")
            order = match.get("governing_order", "")
            legal_basis = match.get("legal_basis", "Section 16, BIS Act, 2016")
            source_url = match.get("source_url", "https://www.manakonline.in")

            explanation = (
                f"Mandatory BIS Product Certification ({scheme}) applicable for {prod_name}. "
                f"Governing Order: {order}. Manufacturers must obtain a valid BIS licence before supply."
            )

            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.BIS_PRODUCT_CERTIFICATION.value,
                status=RegulatoryStatus.APPLICABLE.value,
                matched_product=prod_name,
                standard_number=match.get("standard_number", standard_number),
                legal_basis=legal_basis,
                source=source_url,
                effective_date=None,
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=1.0,
                human_review_required=True,
                explanation=explanation,
                additional_metadata={
                    "scheme": scheme,
                    "governing_order": order,
                    "mandate_type": "MANDATORY"
                }
            )

        # Crucial Requirement 3: An IS number does NOT mean mandatory certification!
        explanation = (
            f"Mandatory BIS certification is NOT identified for {standard_number} in current statutory schedules. "
            f"Note: Existence of an Indian Standard specification does not in itself make BIS certification mandatory; "
            f"voluntary certification under Scheme-I may be available upon application."
        )

        return RegulatoryApplicabilityResult(
            category=RegulatoryCategory.BIS_PRODUCT_CERTIFICATION.value,
            status=RegulatoryStatus.NOT_IDENTIFIED.value,
            matched_product="",
            standard_number=standard_number,
            legal_basis="BIS (Conformity Assessment) Regulations, 2018",
            source="https://www.manakonline.in",
            effective_date=None,
            provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
            confidence=0.9,
            human_review_required=True,
            explanation=explanation,
            additional_metadata={
                "mandate_type": "VOLUNTARY_OR_UNREGULATED"
            }
        )
