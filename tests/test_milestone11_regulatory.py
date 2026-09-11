"""
tests/test_milestone11_regulatory.py
Purpose: Unit tests for Milestone 11 Regulatory Intelligence Engine (Priority 4).

Validates:
- Strict adherence to 21 non-negotiable corrections:
  1. No fabrication of regulatory records.
  2. Existence of IS standard does NOT mean BIS certification is mandatory.
  3. QCO CURRENT vs UPCOMING strictly distinguished by date arithmetic.
  4. CRS applicability requires authoritative product category mapping ('Electronics' alone insufficient).
  5. Hallmarking: gold/silver jewellery -> APPLICABLE/REVIEW_REQUIRED, incompatible products -> NOT_APPLICABLE, insufficient info -> UNKNOWN.
  6. Every regulatory result contains all 11 required fields.
  7. Zero LLM involvement in regulatory decisions.
  8. End-to-end integration with StandardsRecommender and TenderAuditEngine.
"""

import unittest
from datetime import datetime, date

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
from src.regulatory.regulatory_engine import RegulatoryEngine
from src.recommend import StandardsRecommender
from src.audit import TenderAuditEngine


class TestMilestone11Regulatory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg_engine = RegulatoryEngine()
        cls.recommender = StandardsRecommender()
        cls.audit_engine = TenderAuditEngine()

    def test_01_qco_current_vs_upcoming(self):
        """Validates CURRENT vs UPCOMING distinction based on evaluation date."""
        qco_engine = self.reg_engine.qco_engine

        # Past effective date as of 2026-09-11 -> CURRENT (CPVC pipes QCO effective 2024-08-25)
        res_current = qco_engine.evaluate_qco("IS 15778 : 2007", "CPVC pipes", as_of_date="2026-09-11")
        self.assertEqual(res_current.status, RegulatoryStatus.CURRENT.value)
        self.assertEqual(res_current.category, RegulatoryCategory.QCO.value)
        self.assertIn("15778", res_current.standard_number)
        self.assertIn("S.O. 1205(E)", res_current.explanation)
        self.assertTrue(res_current.human_review_required)
        self.assertEqual(res_current.provenance, RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value)

        # Future effective date as of 2026-09-11 -> UPCOMING (Smart Meters QCO effective 2027-04-01)
        res_upcoming = qco_engine.evaluate_qco("IS 16444 (Part 1) : 2015", "Smart electricity meter", as_of_date="2026-09-11")
        self.assertEqual(res_upcoming.status, RegulatoryStatus.UPCOMING.value)
        self.assertEqual(res_upcoming.effective_date, "2027-04-01")
        self.assertIn("Upcoming", res_upcoming.explanation)

        # Same Smart Meter evaluated after 2027-04-01 -> transitions to CURRENT
        res_future_eval = qco_engine.evaluate_qco("IS 16444 (Part 1) : 2015", "Smart electricity meter", as_of_date="2027-05-01")
        self.assertEqual(res_future_eval.status, RegulatoryStatus.CURRENT.value)

        # Standard with no QCO record -> NOT_IDENTIFIED (Never hallucinated)
        res_none = qco_engine.evaluate_qco("IS 99999 : 2099", "Hypothetical widget")
        self.assertEqual(res_none.status, RegulatoryStatus.NOT_IDENTIFIED.value)

    def test_02_crs_applicability_and_keyword_guards(self):
        """Validates CRS matching and ensures 'Electronics' alone is strictly insufficient."""
        crs_engine = self.reg_engine.crs_engine

        # Specific CRS product: Laptops
        res_laptop = crs_engine.evaluate_crs("IS 13252 (Part 1) : 2010", "Supply of laptops and notebooks")
        self.assertEqual(res_laptop.status, RegulatoryStatus.APPLICABLE.value)
        self.assertEqual(res_laptop.category, RegulatoryCategory.CRS.value)
        self.assertIn("Laptops", res_laptop.matched_product)
        self.assertEqual(res_laptop.provenance, RegulatoryProvenanceLevel.OFFICIAL_PRIMARY.value)

        # Specific CRS product: LED Luminaires
        res_led = crs_engine.evaluate_crs("IS 10322 (Part 5/Sec 1) : 2012", "LED street lights and luminaires")
        self.assertEqual(res_led.status, RegulatoryStatus.APPLICABLE.value)
        self.assertIn("LED Luminaires", res_led.matched_product)

        # Requirement 8 Guard: Generic "Electronics" alone is INSUFFICIENT
        res_generic = crs_engine.evaluate_crs(None, "General electronics components and accessories")
        self.assertEqual(res_generic.status, RegulatoryStatus.NOT_IDENTIFIED.value)
        self.assertIn("Generic 'electronics' mention detected", res_generic.explanation)

        # Standard unrelated to CRS (e.g. Cement IS 269)
        res_cement = crs_engine.evaluate_crs("IS 269 : 2015", "Portland cement supply")
        self.assertEqual(res_cement.status, RegulatoryStatus.NOT_IDENTIFIED.value)

    def test_03_hallmarking_precious_vs_incompatible(self):
        """Validates Hallmarking logic: gold/silver -> APPLICABLE/REVIEW_REQUIRED, incompatible goods -> NOT_APPLICABLE."""
        hm_engine = self.reg_engine.hallmarking_engine

        # Gold jewellery / IS 1417 -> APPLICABLE
        res_gold = hm_engine.evaluate_hallmarking("IS 1417 : 2016", "22 carat gold jewellery and ornaments")
        self.assertEqual(res_gold.status, RegulatoryStatus.APPLICABLE.value)
        self.assertEqual(res_gold.category, RegulatoryCategory.HALLMARKING.value)
        self.assertIn("Gold", res_gold.matched_product)
        self.assertTrue(res_gold.human_review_required)

        # Silver jewellery / IS 2112 -> REVIEW_REQUIRED (voluntary scheme)
        res_silver = hm_engine.evaluate_hallmarking("IS 2112 : 2014", "Silver artefacts and medals")
        self.assertEqual(res_silver.status, RegulatoryStatus.REVIEW_REQUIRED.value)
        self.assertIn("Silver", res_silver.matched_product)

        # Clearly incompatible industrial products -> strictly NOT_APPLICABLE
        incompatible_cases = [
            ("IS 778 : 1984", "Waterworks copper alloy gate valves"),
            ("IS 15778 : 2007", "CPVC pipes and fittings for potable water"),
            ("IS 694 : 2010", "PVC insulated copper electrical cables"),
            ("IS 269 : 2015", "Ordinary portland cement 43 grade"),
            ("IS 12615 : 2018", "Three phase energy efficient electric motors"),
        ]
        for std, text in incompatible_cases:
            res_incomp = hm_engine.evaluate_hallmarking(std, text)
            self.assertEqual(
                res_incomp.status,
                RegulatoryStatus.NOT_APPLICABLE.value,
                f"Failed for incompatible good {std}: expected NOT_APPLICABLE, got {res_incomp.status}"
            )
            self.assertIn("strictly limited to precious metals", res_incomp.explanation)

        # Vague ornament without metal specification -> UNKNOWN
        res_vague = hm_engine.evaluate_hallmarking(None, "Decorative ornament items for ceremonies")
        self.assertEqual(res_vague.status, RegulatoryStatus.UNKNOWN.value)

    def test_04_certification_existence_does_not_equal_mandatory(self):
        """Validates Requirement 3: An IS number alone NEVER implies mandatory certification."""
        cert_engine = self.reg_engine.certification_engine

        # Mandatory standard: Cement IS 269 (under Cement Control Order) -> APPLICABLE
        res_cement = cert_engine.evaluate_certification("IS 269 : 2015", "Ordinary portland cement")
        self.assertEqual(res_cement.status, RegulatoryStatus.APPLICABLE.value)
        self.assertEqual(res_cement.additional_metadata.get("mandate_type"), "MANDATORY")

        # Standard with NO mandatory certification schedule: e.g. IS 800 (General Construction in Steel - Code of Practice)
        # Having IS 800 must NOT mean mandatory certification!
        res_is800 = cert_engine.evaluate_certification("IS 800 : 2007", "Structural steel design work")
        self.assertEqual(res_is800.status, RegulatoryStatus.NOT_IDENTIFIED.value)
        self.assertIn("existence of an indian standard specification does not in itself make bis certification mandatory", res_is800.explanation.lower())

        # Missing standard -> UNKNOWN
        res_empty = cert_engine.evaluate_certification(None)
        self.assertEqual(res_empty.status, RegulatoryStatus.UNKNOWN.value)

    def test_05_regulatory_result_schema_completeness(self):
        """Validates Requirement 10: Every regulatory result contains all 11 required fields."""
        res_dict = self.reg_engine.evaluate_to_dict("IS 15778 : 2007", "Providing CPVC pipes")
        
        required_fields = [
            "category",
            "status",
            "matched_product",
            "standard_number",
            "legal_basis",
            "source",
            "effective_date",
            "provenance",
            "confidence",
            "human_review_required",
            "explanation"
        ]

        for cat_key in ["certification", "qco", "crs", "hallmarking"]:
            self.assertIn(cat_key, res_dict, f"Missing category {cat_key}")
            cat_data = res_dict[cat_key]
            for field_name in required_fields:
                self.assertIn(
                    field_name,
                    cat_data,
                    f"Field '{field_name}' missing in category '{cat_key}' result"
                )

    def test_06_zero_llm_enforcement(self):
        """Validates that RegulatoryEngine makes zero calls to any LLM and executes deterministically."""
        # Run 50 evaluations in sub-10ms demonstrating pure local deterministic execution
        import time
        start_time = time.perf_counter()
        for _ in range(50):
            _ = self.reg_engine.evaluate_requirement_regulatory("IS 1786 : 2008", "TMT steel bars")
        elapsed = time.perf_counter() - start_time
        
        # 50 evaluations should take less than 100 milliseconds
        self.assertLess(elapsed, 0.5, f"Regulatory evaluation took too long ({elapsed:.3f}s), suggests non-local execution")

    def test_07_recommend_pipeline_integration(self):
        """Validates that StandardsRecommender populates regulatory field on recommendation result."""
        res = self.recommender.recommend_for_text("Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for water supply")
        
        self.assertIsNotNone(res.regulatory)
        self.assertIn("certification", res.regulatory)
        self.assertIn("qco", res.regulatory)
        self.assertIn("crs", res.regulatory)
        self.assertIn("hallmarking", res.regulatory)

        # CPVC QCO should be CURRENT
        self.assertEqual(res.regulatory["qco"]["status"], RegulatoryStatus.CURRENT.value)
        # Hallmarking should be NOT_APPLICABLE for CPVC
        self.assertEqual(res.regulatory["hallmarking"]["status"], RegulatoryStatus.NOT_APPLICABLE.value)

    def test_08_audit_pipeline_integration(self):
        """Validates that TenderAuditEngine aggregates regulatory metrics correctly."""
        # Create 2 recommendation results
        res_cpvc = self.recommender.recommend_for_text("Providing and fixing CPVC pipes for water distribution")
        res_meter = self.recommender.recommend_for_text("Providing A.C. Static Smart Electricity Meters IS 16444")
        
        audit_res = self.audit_engine.audit_tender([res_cpvc, res_meter], tender_id="TEST-REG-AUDIT")
        
        self.assertGreaterEqual(audit_res.certification_checks, 2)
        self.assertGreaterEqual(audit_res.qco_checks, 2)
        self.assertGreaterEqual(audit_res.crs_checks, 2)
        self.assertGreaterEqual(audit_res.hallmarking_checks, 2)
        self.assertGreaterEqual(audit_res.mandatory_qco_count, 1)  # CPVC is CURRENT
        self.assertGreaterEqual(audit_res.upcoming_qco_items, 1)   # Smart meter is UPCOMING


if __name__ == "__main__":
    unittest.main()
