"""
Unit tests for the Compound Requirement Decomposition Layer:
- VFD water pump panel (control + mechanical + electrical)
- Process water pump 3.3 kV motor (mechanical + electrical + voltage specification)
- CPVC potable water pipe (material + drinking water application)
- Sewerage pipeline (piping + application + civil installation)
- Valve replacement (flow control product + execution)
- Simple non-compound requirement (wall tiles)
- End-to-end recommendation pipeline resolution for compound tenders
"""

import unittest
from src.decompose import decompose_requirement, CompoundRequirementDecomposer
from src.extract import extract_from_text
from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender


class TestCompoundDecomposition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decomposer = CompoundRequirementDecomposer()
        cls.db = StandardsDatabase()
        cls.db.load_verified_json("data/standards/verified_standards.json")
        cls.db.load_curated_excel("data/standards/standards.xlsx")
        cls.db.load_validated_candidates("dataset/ground_truth/validated_candidates.csv")
        cls.recommender = StandardsRecommender(cls.db)

    def test_01_vfd_water_pump_panel(self):
        """Test decomposition of 'VFD water pump panel' into control, mechanical, and electrical."""
        text = "SITC of VFD water pump panel"
        res = self.decomposer.decompose(text)
        self.assertGreaterEqual(res.decomposition_confidence, 0.85)

        comp_types = [c.component_type for c in res.components]
        comp_texts = [c.text.lower() for c in res.components]

        # Must detect VFD (control)
        self.assertIn("control", comp_types)
        self.assertTrue(any("vfd" in t for t in comp_texts))

        # Must detect pump (product)
        self.assertIn("product", comp_types)
        self.assertTrue(any("pump" in t for t in comp_texts))

        # Must detect panel (electrical)
        self.assertIn("electrical", comp_types)
        self.assertTrue(any("panel" in t for t in comp_texts))

    def test_02_process_water_pump_motor_3_3_kv(self):
        """Test decomposition of 'commissioning of three numbers of Process Water Pump motors 3.3 kV'."""
        text = "commissioning of three numbers of Process Water Pump motors 3.3 kV"
        res = self.decomposer.decompose(text)
        self.assertGreaterEqual(res.decomposition_confidence, 0.90)

        types = {c.component_type: c for c in res.components}

        # Specification component
        self.assertIn("specification", types)
        spec = types["specification"]
        self.assertIn("voltage", spec.extracted_attributes.get("spec_type", ""))
        self.assertEqual(spec.extracted_attributes.get("level"), "medium_or_high_voltage")
        self.assertEqual(spec.extracted_attributes.get("kv"), 3.3)

        # Electrical machine component
        self.assertIn("electrical", types)
        elec = types["electrical"]
        self.assertIn("motor", elec.text.lower())

        # Product pump component
        self.assertIn("product", types)
        prod = types["product"]
        self.assertIn("pump", prod.text.lower())
        self.assertTrue(prod.extracted_attributes.get("is_process"))

    def test_03_cpvc_potable_water_pipe(self):
        """Test decomposition of 'CPVC pipes for potable water supply'."""
        text = "CPVC pipes for potable water supply"
        res = self.decomposer.decompose(text)
        self.assertEqual(res.decomposition_confidence, 1.0)

        types = [c.component_type for c in res.components]
        self.assertIn("material", types)
        self.assertIn("application", types)

        mat = [c for c in res.components if c.component_type == "material"][0]
        self.assertIn("cpvc", mat.text.lower())

        app = [c for c in res.components if c.component_type == "application"][0]
        self.assertIn("water", app.text.lower())

    def test_04_sewerage_pipeline(self):
        """Test decomposition of 'laying sewerage pipeline including excavation and testing'."""
        text = "laying sewerage pipeline including excavation and testing"
        res = self.decomposer.decompose(text)

        types = [c.component_type for c in res.components]
        self.assertIn("installation", types)
        self.assertIn("material", types)
        self.assertIn("testing", types)

    def test_05_valve_replacement(self):
        """Test decomposition of 'Valve Replacement'."""
        text = "Valve Replacement"
        res = self.decomposer.decompose(text)

        types = [c.component_type for c in res.components]
        self.assertIn("product", types)
        self.assertIn("installation", types)

        prod = [c for c in res.components if c.component_type == "product"][0]
        self.assertIn("valve", prod.text.lower())

    def test_06_simple_non_compound_requirement(self):
        """Test decomposition of a simple non-compound requirement 'wall tiles'."""
        text = "wall tiles"
        res = self.decomposer.decompose(text)

        self.assertEqual(len(res.components), 1)
        self.assertEqual(res.components[0].component_type, "material")
        self.assertEqual(res.components[0].domain, "civil")
        self.assertIn("tile", res.components[0].text.lower())

    def test_07_e2e_recommender_compound_resolution(self):
        """Test that full recommendation pipeline uses decomposition to correctly resolve T013 and T014."""
        # 1. T013-R002: VFD pump panel must recommend drive / switchgear standard, NOT agricultural pump
        rec_t013 = self.recommender.recommend_for_text("SITC of VFD water pump panel", req_id="TEST-T013")
        self.assertNotIn("IS 9694", rec_t013.candidate_standard, "Must not recommend agricultural pump code")
        self.assertTrue(
            "61800" in rec_t013.candidate_standard or "61439" in rec_t013.candidate_standard,
            f"Expected VFD/switchgear standard but got: {rec_t013.candidate_standard}"
        )
        self.assertGreater(len(rec_t013.decomposed_components), 0, "Decomposed components must be recorded")

        # 2. T014-R002: Process water pump motors 3.3 kV must recommend 3.3 kV motor / process pump standard
        rec_t014 = self.recommender.recommend_for_text(
            "commissioning of three numbers of Process Water Pump motors 3.3 kV",
            req_id="TEST-T014"
        )
        self.assertNotIn("IS 9694", rec_t014.candidate_standard, "Must not recommend agricultural pump code")
        self.assertTrue(
            "60034" in rec_t014.candidate_standard or "5120" in rec_t014.candidate_standard,
            f"Expected rotating electrical machine / process pump standard but got: {rec_t014.candidate_standard}"
        )


if __name__ == "__main__":
    unittest.main()
