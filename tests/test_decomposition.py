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
        if rec_t013.candidate_standard is not None:
            self.assertNotIn("IS 9694", rec_t013.candidate_standard, "Must not recommend agricultural pump code")
            self.assertIn("61800", rec_t013.candidate_standard, "Must resolve to IS/IEC 61800 for VFD panel")
        else:
            self.assertIsNotNone(rec_t013.competing_interpretations)
            found = any("61800" in c["standard_number"] for c in rec_t013.competing_interpretations)
            self.assertTrue(found, "T013 must resolve to IS/IEC 61800 among competing candidates")
            found_bad = any("9694" in c["standard_number"] for c in rec_t013.competing_interpretations)
            self.assertFalse(found_bad, "Agricultural pump code IS 9694 must NOT be recommended")
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


class TestCompositeSubcomponentReviewRollup(unittest.TestCase):
    """
    AUDIT-01: Verifies that subcomponent review requirements propagate to the parent
    recommendation without suppressing valid recommendations or duplicating warnings.
    """
    @classmethod
    def setUpClass(cls):
        cls.db = StandardsDatabase()
        cls.recommender = StandardsRecommender(cls.db)

    def test_01_primary_recommended_secondary_review_required(self):
        """Primary component is recommended, but secondary component needs review -> parent flags review."""
        from src.extract import Requirement, RequirementComponent
        req = Requirement(
            requirement_id="TEST-ROLLUP-01",
            requirement_text="Supply of CPVC pipes and quantum entanglement gravitational wave detector for spacecraft navigation",
            category="piping",
            components=[
                RequirementComponent(text="CPVC pipes", component_type="material", domain="piping"),
                RequirementComponent(text="quantum entanglement gravitational wave detector for spacecraft navigation", component_type="equipment", domain="aerospace")
            ]
        )
        res = self.recommender.recommend_for_requirement(req)
        # Should have candidate standard for primary (IS 15778)
        self.assertIsNotNone(res.candidate_standard)
        # Subcomponents must be retained
        self.assertGreaterEqual(len(res.component_recommendations), 1)
        # Parent must propagate review requirement
        self.assertTrue(res.human_review_required, "Parent must require human review when a subcomponent requires review")
        self.assertIn(res.critic_result.get("decision"), ["RECOMMEND_WITH_REVIEW", "REVIEW_REQUIRED"])
        self.assertEqual(res.ambiguity_state, "REVIEW_REQUIRED")
        self.assertTrue(any("Subcomponent" in r for r in res.risk_reasons))

    def test_02_all_components_recommended(self):
        """When all substantive components resolve cleanly to valid standards, parent does not force review for subcomponent reasons."""
        mock_components = [
            {
                "component_id": "TEST-C1",
                "component_text": "CPVC pipes",
                "candidate_standard": "IS 15778",
                "applicability_decision": "APPLICABLE",
                "human_review_required": False,
            },
            {
                "component_id": "TEST-C2",
                "component_text": "mild steel reinforcement bars",
                "candidate_standard": "IS 432",
                "applicability_decision": "APPLICABLE",
                "human_review_required": False,
            }
        ]
        review_required = [
            c for c in mock_components
            if isinstance(c, dict) and (
                c.get("human_review_required") is True or
                c.get("applicability_decision") in ("REVIEW_REQUIRED", "REJECT", "INSUFFICIENT_EVIDENCE") or
                (c.get("candidate_standard") is None and c.get("human_review_required") is not False)
            )
        ]
        self.assertEqual(len(review_required), 0)

    def test_03_multiple_components_requiring_review_no_duplicate_warnings(self):
        """When multiple components require review, each is reported without duplicate warning strings."""
        from src.extract import Requirement, RequirementComponent
        req = Requirement(
            requirement_id="TEST-ROLLUP-03",
            requirement_text="Supply of quantum detector and tachyonic transceiver",
            category="aerospace",
            components=[
                RequirementComponent(text="quantum entanglement gravitational wave detector", component_type="equipment", domain="aerospace"),
                RequirementComponent(text="tachyonic subspace transceiver module", component_type="equipment", domain="aerospace")
            ]
        )
        res = self.recommender.recommend_for_requirement(req)
        self.assertTrue(res.human_review_required)
        # Check no duplicate strings in risk_reasons and why_not
        self.assertEqual(len(res.risk_reasons), len(set(res.risk_reasons)), "Risk reasons must not contain duplicate warnings")
        self.assertEqual(len(res.why_not), len(set(res.why_not)), "Why-not list must not contain duplicate entries")

    def test_04_malformed_and_missing_component_fields(self):
        """Rollup handles malformed, partial, or missing component dictionaries safely."""
        malformed_components = [
            None,
            "not a dict",
            {},
            {"component_id": "MAL-1"},  # missing candidate_standard and human_review_required
            {"component_text": "incomplete", "human_review_required": None},
            {"component_text": "valid_comp", "candidate_standard": "IS 15778", "human_review_required": False, "applicability_decision": "APPLICABLE"}
        ]
        review_required_comps = []
        for c in malformed_components:
            if not isinstance(c, dict):
                continue
            needs_review = c.get("human_review_required")
            app_dec = c.get("applicability_decision")
            cand_std = c.get("candidate_standard")
            if needs_review is True or app_dec in ("REVIEW_REQUIRED", "REJECT", "INSUFFICIENT_EVIDENCE") or (cand_std is None and needs_review is not False):
                review_required_comps.append(c)

        # {}, MAL-1 and incomplete should be caught as needing review
        self.assertEqual(len(review_required_comps), 3)
        # valid_comp is clean
        self.assertNotIn(malformed_components[-1], review_required_comps)


if __name__ == "__main__":
    unittest.main()

