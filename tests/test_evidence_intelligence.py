"""
tests/test_evidence_intelligence.py
Purpose: Test suite for Phase 3 Evidence-First Standards Intelligence.

Verifies:
1. Confident recommendation produces complete structured evidence.
2. Provenance is present, traceable, and distinguishes VERIFIED vs CURATED vs INFERRED.
3. Lifecycle ACTIVE is represented correctly without contradiction.
4. Lifecycle WITHDRAWN is represented correctly without contradiction.
5. Unknown lifecycle remains UNKNOWN; ACTIVE is never guessed from missing data.
6. Relationship evidence is preserved when authoritative (supersedes, references, international adoptions).
7. Incompatible candidates are rejected and never presented as positive supporting evidence.
8. Safe abstention produces structured uncertainty and missing parameter lists.
9. Ambiguity exposes competing candidates and clarification question.
10. Missing BIS scope does not cause fabricated scope text (scope_status remains UNKNOWN, scope is None).
11. Retrieval similarity is never labelled as authoritative evidence (marked as SUPPORTING_RETRIEVAL_ONLY).
12. Inferred relationship is not labelled VERIFIED.
13. API backward compatibility is preserved (all legacy fields intact).
14. Existing applicability result is correctly represented.
15. Existing ambiguity result is correctly represented.
"""

import unittest
from typing import Dict, Any

from src.recommend import StandardsRecommender
from src.evidence_intelligence import (
    StandardsEvidenceBuilder,
    StructuredEvidence,
    EvidenceStrength,
    LifecycleEvidence,
    RelationshipEvidence,
    ProvenanceEvidence,
    ApplicabilityEvidence,
    StructuredExplanation
)
from src.applicability import ApplicabilityResult, ApplicabilityDecision
from src.ambiguity import AmbiguityReport, AmbiguityState
from src.search import SearchResult


class TestEvidenceIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recommender = StandardsRecommender()
        cls.builder = StandardsEvidenceBuilder(cls.recommender.db)

    def test_01_confident_recommendation_has_complete_structured_evidence(self):
        """A confident recommendation must produce complete, valid structured evidence."""
        text = "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for hot and cold water distribution"
        res = self.recommender.recommend_for_text(text, req_id="TEST-EV-01")

        self.assertIsNotNone(res.candidate_standard)
        self.assertIsNotNone(res.structured_evidence)
        ev = res.structured_evidence

        # Check required top-level keys
        for key in [
            "standard_number", "official_title", "evidence_strength",
            "bis_scope_evidence", "scope_status", "requirement_match",
            "lifecycle", "relationships", "provenance", "applicability",
            "explanation", "uncertainty_and_gaps"
        ]:
            self.assertIn(key, ev, f"Missing key '{key}' in structured_evidence")

        # Verify evidence strength is strong/medium (not weak retrieval or insufficient)
        self.assertIn(
            ev["evidence_strength"],
            [EvidenceStrength.STRONG_AUTHORITATIVE_SCOPE.value, EvidenceStrength.MEDIUM_TECHNICAL_MATCH.value]
        )
        self.assertEqual(ev["lifecycle"]["status"], "ACTIVE")
        self.assertTrue(ev["lifecycle"]["is_active"])
        self.assertFalse(ev["lifecycle"]["is_withdrawn"])

    def test_02_provenance_traceability(self):
        """Provenance must be explicit, traceable, and report verification status."""
        text = "Supply of copper alloy gate valves for waterworks purposes"
        res = self.recommender.recommend_for_text(text, req_id="TEST-EV-02")

        self.assertIsNotNone(res.structured_evidence)
        prov = res.structured_evidence["provenance"]

        self.assertTrue(bool(prov["source"]), "Source must not be empty")
        self.assertIn(
            prov["verification_status"],
            ["VERIFIED", "CURATED", "INFERRED"],
            f"Invalid verification status: {prov['verification_status']}"
        )

    def test_03_lifecycle_active_represented_correctly(self):
        """Active standards must be clearly marked ACTIVE without contradictory withdrawal flags."""
        ev = self.builder._extract_lifecycle(
            db_record={"status": "Active", "reaffirmed_year": 2020, "amendments_count": 2, "source": "TEST_DB"},
            search_result=None
        )
        self.assertEqual(ev.status, "ACTIVE")
        self.assertTrue(ev.is_active)
        self.assertFalse(ev.is_withdrawn)
        self.assertFalse(ev.is_unknown)
        self.assertEqual(ev.reaffirmed_year, 2020)
        self.assertEqual(ev.amendment_count, 2)
        self.assertIn("Active", ev.evidence_text)

    def test_04_lifecycle_withdrawn_represented_correctly(self):
        """Withdrawn standards must be clearly marked WITHDRAWN without contradictory active flags."""
        ev = self.builder._extract_lifecycle(
            db_record={"status": "Withdrawn", "reaffirmed_year": None, "amendments_count": 0, "source": "TEST_DB"},
            search_result=None
        )
        self.assertEqual(ev.status, "WITHDRAWN")
        self.assertFalse(ev.is_active)
        self.assertTrue(ev.is_withdrawn)
        self.assertFalse(ev.is_unknown)
        self.assertIn("Withdrawn", ev.evidence_text)

    def test_05_unknown_lifecycle_remains_unknown(self):
        """When lifecycle is missing or unrecognized, it must remain UNKNOWN and not be guessed."""
        ev_missing = self.builder._extract_lifecycle(db_record=None, search_result=None)
        self.assertEqual(ev_missing.status, "UNKNOWN")
        self.assertFalse(ev_missing.is_active)
        self.assertFalse(ev_missing.is_withdrawn)
        self.assertTrue(ev_missing.is_unknown)

        ev_unrecognized = self.builder._extract_lifecycle(
            db_record={"status": "Under Review Draft", "source": "TEST_DB"},
            search_result=None
        )
        self.assertEqual(ev_unrecognized.status, "UNKNOWN")
        self.assertTrue(ev_unrecognized.is_unknown)
        self.assertFalse(ev_unrecognized.is_active)

    def test_06_relationship_evidence_preservation(self):
        """Authoritative relationships from database must be structured with their evidence."""
        rels = self.builder._extract_relationships(
            std_num="IS/ISO 10434",
            db_record={"standard_id": "IS-ISO-10434-2020"},
            search_result=None
        )
        self.assertTrue(rels.has_relationships)
        # Should record supersession of IS 10611 or adoption of ISO 10434
        all_targets = [r.get("target_standard") for r in rels.supersedes + rels.international_equivalent]
        self.assertTrue(
            any("10611" in str(t) or "10434" in str(t) for t in all_targets),
            f"Expected relationship to 10611 or 10434, got: {rels.to_dict()}"
        )

    def test_07_incompatible_candidates_not_presented_as_positive_evidence(self):
        """Incompatible candidate must yield CONFLICTING_EVIDENCE strength and record rejection reasons."""
        fake_app = ApplicabilityResult(
            standard_number="IS 302",
            title="Safety of Household and Similar Electrical Appliances",
            applicable=False,
            decision=ApplicabilityDecision.NOT_APPLICABLE.value,
            applicability_score=0.10,
            domain_match=False,
            product_match=False,
            scope_match=False,
            application_match=False,
            evidence_support=False,
            conflict_flags=["EQUIPMENT_MISMATCH: facility_premise vs appliance_tool"],
            rejection_reasons=["Candidate standard covers household appliances, but requirement describes a food facility."]
        )
        ev = self.builder.build_structured_evidence(
            standard_number="IS 302",
            requirement_text="Low-Oil Food Outlet on BOT concession",
            applicability_result=fake_app
        )
        self.assertEqual(ev.evidence_strength, EvidenceStrength.CONFLICTING_EVIDENCE.value)
        self.assertEqual(ev.applicability.decision, "NOT_APPLICABLE")
        self.assertIn("EQUIPMENT_MISMATCH: facility_premise vs appliance_tool", ev.applicability.conflict_flags)

    def test_08_safe_abstention_produces_structured_uncertainty(self):
        """Safe abstention on under-specified query must expose missing parameters and uncertainty."""
        res = self.recommender.recommend_for_text("Valve Replacement", req_id="TEST-EV-VALVE")
        self.assertIsNone(res.candidate_standard)
        self.assertTrue(res.human_review_required)
        self.assertIsNotNone(res.structured_evidence)

        ev = res.structured_evidence
        self.assertEqual(ev["evidence_strength"], EvidenceStrength.INSUFFICIENT_INFORMATION.value)
        self.assertIsNone(ev["standard_number"])
        self.assertEqual(ev["scope_status"], "UNKNOWN")

        # Must record missing parameters and suggested clarification
        gaps = ev["uncertainty_and_gaps"]
        self.assertTrue(len(gaps["missing_parameters"]) > 0)
        self.assertTrue(len(gaps["suggested_clarification"]) > 10)

    def test_09_ambiguity_exposes_competing_candidates_and_clarification(self):
        """Ambiguous requirement must expose competing candidate standards in uncertainty_and_gaps."""
        amb_report = AmbiguityReport(
            ambiguity_state=AmbiguityState.AMBIGUOUS,
            ambiguity_reason="Voltage tier missing between Part 1 (LT) and Part 2 (HT)",
            retrieval_status="CANDIDATES_FOUND",
            applicability_status="AMBIGUOUS",
            evidence_status="VALID",
            competing_interpretations=[
                {"standard_number": "IS 7098 (Part 1)", "voltage": "up to 1100 V"},
                {"standard_number": "IS 7098 (Part 2)", "voltage": "3.3 kV to 33 kV"}
            ],
            missing_information=["Voltage Grade"],
            suggested_clarification_question="Specify operating voltage grade (LT <= 1.1 kV or HT > 1.1 kV)."
        )
        ev = self.builder.build_structured_evidence(
            standard_number=None,
            requirement_text="Supply of XLPE power cable to electrical room",
            ambiguity_report=amb_report,
            missing_information=["Voltage Grade"],
            human_review_required=True,
            decision_reason="Voltage tier ambiguous"
        )
        self.assertEqual(ev.evidence_strength, EvidenceStrength.INSUFFICIENT_INFORMATION.value)
        gaps = ev.uncertainty_and_gaps
        self.assertEqual(len(gaps["competing_candidates"]), 2)
        self.assertIn("Voltage Grade", gaps["missing_parameters"])
        self.assertEqual(gaps["suggested_clarification"], "Specify operating voltage grade (LT <= 1.1 kV or HT > 1.1 kV).")

    def test_10_missing_bis_scope_does_not_fabricate_scope_text(self):
        """When standard has no scope in DB, bis_scope_evidence must be None and scope_status UNKNOWN."""
        ev = self.builder.build_structured_evidence(
            standard_number="IS 99999",
            requirement_text="Synthetic requirement with unknown standard",
            title="Synthetic Standard Title Without Scope"
        )
        self.assertIsNone(ev.bis_scope_evidence)
        self.assertEqual(ev.scope_status, "UNKNOWN")
        self.assertIn(
            "Full BIS scope clause text is unavailable in the captured catalogue record.",
            ev.explanation.uncertainties
        )

    def test_11_retrieval_similarity_never_labelled_authoritative(self):
        """Retrieval similarity must be marked SUPPORTING_RETRIEVAL_SIGNAL_ONLY, not authoritative."""
        fake_sr = SearchResult(
            standard_id="IS-99999",
            standard_number="IS 99999",
            year=2020,
            full_title="Some Standard",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.88,
            relevance_reason="High semantic similarity",
            scope_summary="",
            bm25_score=0.45,
            semantic_score=0.85,
            final_score=0.88
        )
        ev = self.builder.build_structured_evidence(
            standard_number="IS 99999",
            requirement_text="Query text",
            candidate_search_result=fake_sr
        )
        signals = ev.requirement_match["retrieval_signals"]
        self.assertEqual(signals["signal_role"], "SUPPORTING_RETRIEVAL_SIGNAL_ONLY")
        self.assertIn("Retrieval similarity discovers candidates", signals["note"])

    def test_12_inferred_relationship_not_labelled_verified(self):
        """If relationship data is absent, has_relationships must be False and not labelled verified."""
        rels = self.builder._extract_relationships(
            std_num="IS 99999",
            db_record=None,
            search_result=None
        )
        self.assertFalse(rels.has_relationships)
        self.assertEqual(rels.supersedes, [])
        self.assertEqual(rels.superseded_by, [])
        self.assertEqual(rels.relationship_evidence_summary, "No explicit relationship evidence recorded in catalogue.")

    def test_13_api_backward_compatibility_preserved(self):
        """All legacy fields in RequirementRecommendationResult must remain present and accessible."""
        res = self.recommender.recommend_for_text(
            "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for hot and cold water",
            req_id="TEST-COMPAT-01"
        )
        # Check that legacy attributes exist and are accessible
        self.assertTrue(hasattr(res, "candidate_standard"))
        self.assertTrue(hasattr(res, "title"))
        self.assertTrue(hasattr(res, "status"))
        self.assertTrue(hasattr(res, "version_role"))
        self.assertTrue(hasattr(res, "relevance_score"))
        self.assertTrue(hasattr(res, "confidence"))
        self.assertTrue(hasattr(res, "evidence"))
        self.assertTrue(hasattr(res, "provenance"))
        self.assertTrue(hasattr(res, "human_review_required"))
        self.assertTrue(hasattr(res, "reason"))
        self.assertTrue(hasattr(res, "why_it_matches"))
        self.assertTrue(hasattr(res, "why_this"))
        self.assertTrue(hasattr(res, "why_not"))
        self.assertTrue(hasattr(res, "applicability"))
        self.assertTrue(hasattr(res, "dependencies"))
        self.assertTrue(hasattr(res, "ambiguity_state"))
        self.assertTrue(hasattr(res, "alternatives"))

        # In addition, structured_evidence is present
        self.assertTrue(hasattr(res, "structured_evidence"))
        self.assertIsInstance(res.structured_evidence, dict)

    def test_14_existing_applicability_result_correctly_represented(self):
        """Applicability decision and flags must map cleanly into structured_evidence."""
        res = self.recommender.recommend_for_text(
            "Replacement of damaged pipelines by Hubless cast iron pipes",
            req_id="TEST-EV-HUBLESS"
        )
        self.assertIsNotNone(res.structured_evidence)
        app = res.structured_evidence["applicability"]
        self.assertEqual(app["decision"], "APPLICABLE")
        self.assertTrue(app["domain_match"])
        self.assertTrue(app["product_match"])

    def test_15_existing_ambiguity_result_correctly_represented(self):
        """Ambiguity state from AmbiguityEngine must be faithfully exposed in structured evidence."""
        # Query with sewerage pipeline without material specification -> safe abstention / material ambiguity
        res = self.recommender.recommend_for_text(
            "Sewerage Pipeline works from Collection Chamber to STP",
            req_id="TEST-EV-SEWERAGE"
        )
        self.assertIsNone(res.candidate_standard)
        self.assertTrue(res.human_review_required)
        ev = res.structured_evidence
        self.assertEqual(ev["evidence_strength"], EvidenceStrength.INSUFFICIENT_INFORMATION.value)
        self.assertTrue(len(ev["uncertainty_and_gaps"]["competing_candidates"]) > 0 or len(ev["uncertainty_and_gaps"]["missing_parameters"]) > 0)


if __name__ == "__main__":
    unittest.main()
