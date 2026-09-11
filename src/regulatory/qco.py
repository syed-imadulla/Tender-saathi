"""
Quality Control Order (QCO) Intelligence Engine for TenderSaathi.

Evaluates applicability of Quality Control Orders issued under Section 16 of the BIS Act, 2016.
Strict rules enforced:
- Must be backed by an authoritative QCO record in qco_master.json.
- CURRENT and UPCOMING statuses remain strictly distinct by comparing effective_date with evaluation date.
- Never infers a QCO merely because an Indian Standard exists.
- Zero LLM involvement; 100% deterministic legal status evaluation.
"""

import json
import os
import re
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from src.regulatory.provenance import (
    RegulatoryProvenanceLevel,
    RegulatoryCategory,
    RegulatoryStatus,
    RegulatoryApplicabilityResult,
)
from src.catalogue.normalizer import StandardIdentifierNormalizer


class QCOEngine:
    """
    Deterministic evaluation engine for Quality Control Orders (QCOs).
    """
    DEFAULT_DATA_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "regulatory", "qco", "qco_master.json"
    )

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self.normalizer = StandardIdentifierNormalizer()
        self.orders: List[Dict[str, Any]] = []
        self._standard_to_order_map: Dict[str, List[Dict[str, Any]]] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not os.path.exists(self.data_path):
            self.orders = []
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.orders = data.get("orders", [])
        self._standard_to_order_map = {}

        for order in self.orders:
            for std in order.get("standards", []):
                std_num = std.get("standard_number", "")
                base_std = std.get("base_standard", "")
                
                # Normalize keys
                keys_to_index = set()
                if std_num:
                    keys_to_index.add(self.normalizer.normalize_identifier(std_num))
                    keys_to_index.add(std_num.strip().upper())
                if base_std:
                    keys_to_index.add(self.normalizer.normalize_identifier(base_std))
                    keys_to_index.add(base_std.strip().upper())

                # Also index bare base number without parts (e.g. IS 16444 for IS 16444 Part 1)
                parsed = self.normalizer.parse(std_num or base_std)
                if parsed.base_number:
                    bare_slug = f"{parsed.prefix.replace('/', '-')}-{parsed.base_number}"
                    bare_num = f"{parsed.prefix} {parsed.base_number}"
                    keys_to_index.add(bare_slug)
                    keys_to_index.add(bare_num.upper())

                for k in keys_to_index:
                    if k not in self._standard_to_order_map:
                        self._standard_to_order_map[k] = []
                    self._standard_to_order_map[k].append({
                        "order": order,
                        "standard_info": std
                    })

    def evaluate_qco(
        self,
        standard_number: Optional[str],
        product_text: Optional[str] = None,
        as_of_date: Optional[str] = "2026-09-11"
    ) -> RegulatoryApplicabilityResult:
        """
        Evaluate QCO applicability for a standard and optional product context.
        """
        # If no standard is provided, we cannot establish a QCO without an authoritative match
        norm_id = self.normalizer.normalize_identifier(standard_number) if standard_number else ""
        norm_key = standard_number.strip().upper() if standard_number else ""

        matches = (self._standard_to_order_map.get(norm_id) or self._standard_to_order_map.get(norm_key)) if norm_id else None

        # Also attempt base standard matching if standard contains year
        if not matches and standard_number and ":" in standard_number:
            base_part = standard_number.split(":")[0].strip()
            base_norm = self.normalizer.normalize_identifier(base_part)
            matches = self._standard_to_order_map.get(base_norm) or self._standard_to_order_map.get(base_part.upper())

        # If no match on candidate standard, check if product_text explicitly cites a QCO standard
        if not matches and product_text:
            text_stds = re.findall(r'\b(IS\s*(?:/\s*IEC)?\s*\d+(?:\s*(?:\(Part\s*\d+\)|Part\s*\d+))?)\b', product_text, flags=re.IGNORECASE)
            for ts in text_stds:
                ts_norm = self.normalizer.normalize_identifier(ts)
                m = self._standard_to_order_map.get(ts_norm) or self._standard_to_order_map.get(ts.strip().upper())
                if m:
                    matches = m
                    standard_number = ts
                    break

        if not matches:
            if not standard_number or not standard_number.strip():
                return RegulatoryApplicabilityResult(
                    category=RegulatoryCategory.QCO.value,
                    status=RegulatoryStatus.NOT_IDENTIFIED.value,
                    matched_product="",
                    standard_number="",
                    legal_basis="",
                    source="",
                    effective_date=None,
                    provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                    confidence=1.0,
                    human_review_required=False,
                    explanation="No Indian Standard provided to evaluate Quality Control Order applicability."
                )

        if not matches:
            return RegulatoryApplicabilityResult(
                category=RegulatoryCategory.QCO.value,
                status=RegulatoryStatus.NOT_IDENTIFIED.value,
                matched_product="",
                standard_number=standard_number,
                legal_basis="",
                source="e-Gazette of India / DPIIT QCO Registry",
                effective_date=None,
                provenance=RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value,
                confidence=0.9,
                human_review_required=True,
                explanation=f"No mandatory Quality Control Order (QCO) identified in authoritative gazette registry for {standard_number}. Verify ministry specific notifications."
            )

        # Process the primary matching order
        match = matches[0]
        order = match["order"]
        std_info = match["standard_info"]

        effective_date_str = order.get("effective_date")
        curr_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()

        status = RegulatoryStatus.CURRENT.value
        if effective_date_str:
            try:
                eff_date = datetime.strptime(effective_date_str, "%Y-%m-%d").date()
                if curr_date < eff_date:
                    status = RegulatoryStatus.UPCOMING.value
                else:
                    status = RegulatoryStatus.CURRENT.value
            except ValueError:
                status = RegulatoryStatus.UNKNOWN.value

        order_title = order.get("order_title", "")
        gazette_notif = order.get("gazette_notification", "")
        ministry = order.get("ministry", "")
        source_url = order.get("source_url", "")
        product_name = std_info.get("product_name", "")

        if status == RegulatoryStatus.CURRENT.value:
            explanation = (
                f"Mandatory QCO in force: Covered under {order_title} ({gazette_notif}) issued by {ministry}. "
                f"Effective from {effective_date_str}. Compliance and Standard Mark are mandatory under Section 16, BIS Act 2016."
            )
        elif status == RegulatoryStatus.UPCOMING.value:
            explanation = (
                f"Upcoming mandatory QCO: Notified under {order_title} ({gazette_notif}) issued by {ministry}. "
                f"Becomes effective on {effective_date_str}. Currently in transition period."
            )
        else:
            explanation = f"QCO record found: {order_title} ({gazette_notif}). Date verification required."

        return RegulatoryApplicabilityResult(
            category=RegulatoryCategory.QCO.value,
            status=status,
            matched_product=product_name,
            standard_number=std_info.get("standard_number", standard_number),
            legal_basis=order.get("legal_basis", "Section 16, BIS Act, 2016"),
            source=source_url or gazette_notif,
            effective_date=effective_date_str,
            provenance=order.get("provenance", RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value),
            confidence=1.0,
            human_review_required=True,
            explanation=explanation,
            additional_metadata={
                "order_id": order.get("order_id"),
                "order_title": order_title,
                "ministry": ministry,
                "gazette_notification": gazette_notif,
                "notification_date": order.get("notification_date")
            }
        )
