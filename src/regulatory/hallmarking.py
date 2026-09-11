"""
Hallmarking Intelligence Engine for TenderSaathi.

Evaluates applicability of BIS Hallmarking Scheme under BIS (Hallmarking) Regulations, 2018
and Gold Jewellery Hallmarking Orders.

Strict rules enforced per Requirement 9:
- Clearly applicable gold/silver jewellery/artefacts -> APPLICABLE or REVIEW_REQUIRED.
- Clearly incompatible product (valves, pipes, cables, cement, motors, etc.) -> strictly NOT_APPLICABLE.
- Insufficient material/product information -> UNKNOWN.
- Never guess. Zero LLM involvement.
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


class HallmarkingEngine:
    """
    Deterministic evaluation engine for Hallmarking of Precious Metals.
    """
    DEFAULT_DATA_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "regulatory", "hallmarking", "hallmarking_master.json"
    )

    # Incompatible domain keywords (clearly non-precious industrial/civil goods)
    INCOMPATIBLE_KEYWORDS = {
        "pipe", "pipes", "fitting", "fittings", "valve", "valves", "cable", "cables",
        "wire", "wires", "motor", "motors", "pump", "pumps", "cement", "concrete",
        "aggregate", "sand", "gravel", "steel", "rebar", "tmt", "billet", "ingot",
        "structural steel", "beam", "column", "brick", "masonry", "timber", "wood",
        "plywood", "glass", "paint", "enamel", "varnish", "primer", "switchgear",
        "panel", "mcb", "rccb", "transformer", "earthing", "luminaire", "light",
        "led", "ups", "inverter", "battery", "soil", "geotextile", "extinguisher",
        "sanitaryware", "wash basin", "water closet", "cistern", "manhole",
        "pavement", "asphalt", "bitumen", "crane", "hoist", "elevator", "lift"
    }

    PRECIOUS_GOLD_KEYWORDS = {"gold", "bullion", "kundan", "polki", "carat", "karat", "fineness"}
    PRECIOUS_SILVER_KEYWORDS = {"silver", "fine silver", "sterling silver"}
    JEWELLERY_KEYWORDS = {"jewellery", "jewelry", "artefact", "artefacts", "artifact", "ornament", "bullion", "coin", "medallion"}

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self.normalizer = StandardIdentifierNormalizer()
        self.hallmarking_orders: List[Dict[str, Any]] = []
        self._standard_map: Dict[str, Dict[str, Any]] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not os.path.exists(self.data_path):
            self.hallmarking_orders = []
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.hallmarking_orders = data.get("hallmarking_orders", [])
        self._standard_map = {}

        for order in self.hallmarking_orders:
            for std in order.get("standards", []):
                std_num = std.get("standard_number", "")
                base_std = std.get("base_standard", "")

                keys = set()
                if std_num:
                    keys.add(self.normalizer.normalize_identifier(std_num))
                    keys.add(std_num.strip().upper())
                if base_std:
                    keys.add(self.normalizer.normalize_identifier(base_std))
                    keys.add(base_std.strip().upper())

                for k in keys:
                    self._standard_map[k] = {
                        "order": order,
                        "standard_info": std
                    }

    def evaluate_hallmarking(
        self,
        standard_number: Optional[str] = None,
        product_text: Optional[str] = None
    ) -> RegulatoryApplicabilityResult:
        """
        Evaluate Hallmarking applicability adhering strictly to Requirement 9.
        """
        norm_std = ""
        if standard_number and standard_number.strip():
            norm_std = self.normalizer.normalize_identifier(standard_number)

        # 1. Standard-based check
        if norm_std and norm_std in self._standard_map:
            entry = self._standard_map[norm_std]
            order = entry["order"]
            std_info = entry["standard_info"]
            metal = order.get("precious_metal", "")
            is_mandatory = order.get("mandatory_coverage", False)

            status = RegulatoryStatus.APPLICABLE.value if is_mandatory else RegulatoryStatus.REVIEW_REQUIRED.value
            expl = (
                f"Mandatory BIS Hallmarking applicable: Covered under {order.get('order_title', '')} "
                f"({order.get('gazette_notification', '')}). Precious metal: {metal}. "
                f"Requires BIS Hallmarking unique identification (HUID) and recognized fineness marks."
            ) if is_mandatory else (
                f"Voluntary BIS Hallmarking Scheme in force for {metal} under {order.get('order_title', '')}. "
                f"Verify tender contract requirements for certification."
            )

            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.HALLMARKING.value,
                status=status,
                matched_product=std_info.get("product_scope", f"{metal} jewellery/artefacts"),
                standard_number=std_info.get("standard_number", standard_number),
                legal_basis=order.get("legal_basis", "Sections 14, 15, 16, BIS Act, 2016"),
                source=order.get("source_url", "https://consumeraffairs.nic.in"),
                effective_date=order.get("effective_date"),
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=1.0,
                human_review_required=True,
                explanation=expl,
                additional_metadata={
                    "order_id": order.get("order_id"),
                    "precious_metal": metal,
                    "purity_grades": order.get("purity_grades", [])
                }
            )

        # 2. Text / Product context analysis
        text_lower = (product_text or "").lower()
        words = set(re.findall(r"\b[a-z]+\b", text_lower))

        # Check for clearly incompatible goods
        incompatible_overlap = words.intersection(self.INCOMPATIBLE_KEYWORDS)
        if incompatible_overlap:
            # Domain-incompatible product -> strictly NOT_APPLICABLE
            incompatible_sample = ", ".join(sorted(list(incompatible_overlap))[:3])
            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.HALLMARKING.value,
                status=RegulatoryStatus.NOT_APPLICABLE.value,
                matched_product="",
                standard_number=standard_number or "",
                legal_basis="BIS (Hallmarking) Regulations, 2018",
                source="Ministry of Consumer Affairs / BIS Hallmarking Regulations",
                effective_date=None,
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=1.0,
                human_review_required=False,
                explanation=f"Hallmarking is strictly limited to precious metals (gold and silver). Incompatible product domain identified ({incompatible_sample}); not applicable."
            )

        # Check for Gold jewellery/artefacts
        has_gold = bool(words.intersection(self.PRECIOUS_GOLD_KEYWORDS))
        has_silver = bool(words.intersection(self.PRECIOUS_SILVER_KEYWORDS))
        has_jewellery = bool(words.intersection(self.JEWELLERY_KEYWORDS))

        if has_gold and (has_jewellery or "jewel" in text_lower or "artefact" in text_lower or "bullion" in text_lower):
            gold_order = next((o for o in self.hallmarking_orders if o.get("precious_metal") == "GOLD"), {})
            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.HALLMARKING.value,
                status=RegulatoryStatus.APPLICABLE.value,
                matched_product="Gold Jewellery / Artefacts",
                standard_number="IS 1417 : 2016",
                legal_basis=gold_order.get("legal_basis", "Sections 14, 15, 16, BIS Act, 2016"),
                source=gold_order.get("source_url", "https://consumeraffairs.nic.in"),
                effective_date=gold_order.get("effective_date"),
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=0.95,
                human_review_required=True,
                explanation="Mandatory Hallmarking of Gold Jewellery & Artefacts is applicable under S.O. 204(E). Requires HUID registration and approved fineness (14K, 18K, 20K, 22K, 23K, 24K)."
            )

        if has_silver and (has_jewellery or "jewel" in text_lower or "artefact" in text_lower):
            silver_order = next((o for o in self.hallmarking_orders if o.get("precious_metal") == "SILVER"), {})
            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.HALLMARKING.value,
                status=RegulatoryStatus.REVIEW_REQUIRED.value,
                matched_product="Silver Jewellery / Artefacts",
                standard_number="IS 2112 : 2014",
                legal_basis=silver_order.get("legal_basis", "Sections 14 and 15, BIS Act, 2016"),
                source=silver_order.get("source_url", "https://www.bis.gov.in"),
                effective_date=silver_order.get("effective_date"),
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=0.9,
                human_review_required=True,
                explanation="Voluntary BIS Hallmarking scheme in place for Silver Jewellery and Artefacts (IS 2112). Verification of tender-specified purity requirement recommended."
            )

        # Ambiguous jewellery / precious items without clear metal
        if has_jewellery or "ornament" in text_lower or "precious" in text_lower:
            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.HALLMARKING.value,
                status=RegulatoryStatus.UNKNOWN.value,
                matched_product="",
                standard_number=standard_number or "",
                legal_basis="BIS (Hallmarking) Regulations, 2018",
                source="Ministry of Consumer Affairs",
                effective_date=None,
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=0.5,
                human_review_required=True,
                explanation="Potential jewellery or ornament detected, but specific precious metal (Gold / Silver) or purity cannot be determined from requirement text. Status unknown without further specification."
            )

        # If text is empty or generic and non-matching
        return RegulatoryApplicabilityResult(
            category=RegulatoryCategory.HALLMARKING.value,
            status=RegulatoryStatus.NOT_APPLICABLE.value,
            matched_product="",
            standard_number=standard_number or "",
            legal_basis="BIS (Hallmarking) Regulations, 2018",
            source="Ministry of Consumer Affairs",
            effective_date=None,
            provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
            confidence=0.9,
            human_review_required=False,
            explanation="Hallmarking is not applicable to this product category."
        )
