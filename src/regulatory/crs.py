"""
Compulsory Registration Scheme (CRS) Intelligence Engine for TenderSaathi.

Evaluates applicability of BIS Scheme-II (Compulsory Registration Scheme)
notified primarily under MeitY and MNRE Orders under Section 16 of the BIS Act, 2016.

Strict rules enforced:
- Must match an authoritative CRS product-category mapping.
- The word "Electronics" alone is strictly INSUFFICIENT to trigger CRS.
- Requires product category keyword match or canonical standard number match.
- Zero LLM involvement; 100% deterministic evaluation.
"""

import json
import os
import re
from typing import Optional, Dict, Any, List

from src.regulatory.provenance import (
    RegulatoryProvenanceLevel,
    RegulatoryCategory,
    RegulatoryStatus,
    RegulatoryApplicabilityResult,
)
from src.catalogue.normalizer import StandardIdentifierNormalizer


class CRSEngine:
    """
    Deterministic evaluation engine for Compulsory Registration Scheme (CRS).
    """
    DEFAULT_DATA_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "regulatory", "crs", "crs_master.json"
    )

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self.normalizer = StandardIdentifierNormalizer()
        self.crs_products: List[Dict[str, Any]] = []
        self._standard_map: Dict[str, Dict[str, Any]] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not os.path.exists(self.data_path):
            self.crs_products = []
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.crs_products = data.get("crs_products", [])
        self._standard_map = {}

        for prod in self.crs_products:
            std_num = prod.get("standard_number", "")
            base_std = prod.get("base_standard", "")

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
                if k not in self._standard_map:
                    self._standard_map[k] = []
                self._standard_map[k].append(prod)

    def evaluate_crs(
        self,
        standard_number: Optional[str] = None,
        product_text: Optional[str] = None
    ) -> RegulatoryApplicabilityResult:
        """
        Evaluate CRS applicability.
        Enforces: "Electronics" alone is insufficient.
        Requires either:
        1. Explicit match on a recognized CRS standard, AND/OR
        2. Specific keyword match on an official CRS product category.
        """
        # 1. Check product text keyword match (reject generic words like "electronics" alone)
        prod_match: Optional[Dict[str, Any]] = None
        if product_text and product_text.strip():
            text_lower = product_text.lower()
            generic_cleaned = re.sub(r"\b(electronics?|electrical|equipment|device|goods)\b", "", text_lower).strip()
            
            if len(generic_cleaned) > 2:  # Only if specific terms remain
                for item in self.crs_products:
                    for kw in item.get("keywords", []):
                        pattern = r"\b" + re.escape(kw) + r"\b"
                        if re.search(pattern, text_lower):
                            prod_match = item
                            break
                    if prod_match:
                        break

        # 2. Check standard match
        std_matches: List[Dict[str, Any]] = []
        if standard_number and standard_number.strip():
            norm_id = self.normalizer.normalize_identifier(standard_number)
            std_matches = self._standard_map.get(norm_id) or self._standard_map.get(standard_number.strip().upper()) or []
            if not std_matches and ":" in standard_number:
                base_part = standard_number.split(":")[0].strip()
                base_norm = self.normalizer.normalize_identifier(base_part)
                std_matches = self._standard_map.get(base_norm) or self._standard_map.get(base_part.upper()) or []

        # Resolve matched_item
        matched_item: Optional[Dict[str, Any]] = None
        if std_matches:
            # If prod_match is in std_matches, prioritize it
            if prod_match and any(p["product_category_id"] == prod_match["product_category_id"] for p in std_matches):
                matched_item = prod_match
            else:
                # If product_text matched any keywords of std_matches
                text_lower = (product_text or "").lower()
                for p in std_matches:
                    for kw in p.get("keywords", []):
                        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                            matched_item = p
                            break
                    if matched_item:
                        break
                if not matched_item:
                    matched_item = std_matches[0]
        elif prod_match:
            matched_item = prod_match

        if matched_item:
            cat_name = matched_item.get("product_category_name", "")
            std_num = matched_item.get("standard_number", standard_number or "")
            order_ref = matched_item.get("order_reference", "")
            ministry = matched_item.get("notifying_ministry", "")
            eff_date = matched_item.get("effective_date")
            src_url = matched_item.get("source_url", "")

            explanation = (
                f"Mandatory CRS (Scheme-II) Registration applicable: Category '{cat_name}' is covered under "
                f"{order_ref} issued by {ministry}. Requires BIS registration and standard wording "
                f"'Self Declaration - Conforming to {std_num}'."
            )

            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.CRS.value,
                status=RegulatoryStatus.APPLICABLE.value,
                matched_product=cat_name,
                standard_number=std_num,
                legal_basis=matched_item.get("legal_basis", "Section 16, BIS Act 2016 / Scheme-II"),
                source=src_url or order_ref,
                effective_date=eff_date,
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=1.0 if (std_matches and prod_match) else 0.9,
                human_review_required=True,
                explanation=explanation,
                additional_metadata={
                    "product_category_id": matched_item.get("product_category_id"),
                    "order_reference": order_ref,
                    "notifying_ministry": ministry
                }
            )

        # Non-matching
        is_generic_electronics = False
        if product_text:
            text_lower = product_text.lower()
            if "electronic" in text_lower or "electronics" in text_lower:
                is_generic_electronics = True

        if is_generic_electronics:
            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.CRS.value,
                status=RegulatoryStatus.NOT_IDENTIFIED.value,
                matched_product="",
                standard_number=standard_number or "",
                legal_basis="Section 16, BIS Act, 2016 / Scheme-II (CRS)",
                source="MeitY / BIS Compulsory Registration Portal",
                effective_date=None,
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=0.9,
                human_review_required=True,
                explanation="Generic 'electronics' mention detected, but product does not match any specific gazetted CRS product category. CRS registration cannot be established without specific product classification."
            )

        return RegulatoryApplicabilityResult(
            category=RegulatoryCategory.CRS.value,
            status=RegulatoryStatus.NOT_IDENTIFIED.value,
            matched_product="",
            standard_number=standard_number or "",
            legal_basis="",
            source="MeitY / BIS Compulsory Registration Portal",
            effective_date=None,
            provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
            confidence=0.95,
            human_review_required=False,
            explanation="Product / standard not identified under the Compulsory Registration Scheme (CRS)."
        )
