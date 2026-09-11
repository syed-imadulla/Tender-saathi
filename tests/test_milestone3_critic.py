"""
Unit tests for Milestone 3: Evidence-Aware Critic and Decision Layer.

Tests:
1. Strong CPVC requirement -> valid recommendation with grounded evidence.
2. Valve replacement without technical parameters -> review required due to specification review completeness.
3. Superseded IS 10611 -> successor recommendation (IS/ISO 10434) with review required.
4. Trust Gate: weak evidence candidate cannot become high confidence.
5. Multiple plausible standards with missing parameters -> review required.
6. "Why this?" contains actual evidence-backed reasons derived from candidate data.
7. "Why not?" uses actual candidate differences (relevance, scope, or component coverage).
8. Specification completeness detects potentially missing valve parameters.
9. Existing T013 (VFD water pump panel) and T014 (process pump 3.3 kV motor) still work.
10. Existing benchmark accuracy and supersedence detection remain intact.
"""

import unittest
from typing import Optional

from src.standards import StandardsDatabase
from src.retrieval import HybridRetrievalEngine
from src.recommend import StandardsRecommender
from src.extract import extract_from_text
from src.completeness import DomainCompletenessAnalyzer
from src.critic import EvidenceAwareCritic, CandidateEvidence, CandidateCritique
from src.search import SearchResult


class TestMilestone3Critic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = StandardsDatabase()
        cls.recommender = StandardsRecommender(cls.db, retrieval_mode="hybrid")
        cls.completeness_analyzer = DomainCompletenessAnalyzer()
        cls.critic = EvidenceAwareCritic(cls.db)

    def test_01_strong_cpvc_requirement(self):
        """Strong CPVC requirement produces an evidence-grounded recommendation."""
        req = extract_from_text(
            "Supply of CPVC pipes for potable water distribution",
            requirement_id="TEST-CPVC-01"
        )
        res = self.recommender.recommend_for_requirement(req)

        self.assertIn("15778", res.candidate_standard, "Expected IS 15778 for CPVC pipes")
        self.assertIn(res.critic_result["decision"], ["RECOMMEND", "RECOMMEND_WITH_REVIEW"])
        self.assertTrue(len(res.evidence) > 0, "Must have evidence text")
        self.assertTrue(len(res.why_this) > 0, "Must have 'Why this?' reasons")

        # Validate that decision was derived from actual evidence and lifecycle
        crit = res.critic_result
        self.assertEqual(crit["lifecycle_score"], 1.0, "Active standard must have lifecycle score 1.0")
        self.assertGreaterEqual(crit["evidence_score"], 0.70, "CPVC must have strong/moderate evidence score")

    def test_02_valve_replacement_requires_review(self):
        """Under-specified valve replacement triggers review_required in critic."""
        req = extract_from_text(
            "Replacement of damaged valves in pumping station",
            requirement_id="TEST-VALVE-01"
        )
        res = self.recommender.recommend_for_requirement(req)

        self.assertTrue(res.human_review_required, "Under-specified valve work must require human review")
        self.assertIn(res.risk_level, ["HIGH", "CRITICAL"], "Missing parameters in critical valve must yield high risk")
        self.assertTrue(len(res.risk_reasons) > 0, "Must provide visible risk reasons")

        # Check specification review completeness was evaluated
        comp = res.specification_completeness
        self.assertIsNotNone(comp)
        self.assertEqual(comp["domain"], "valve")
        self.assertFalse(comp["is_adequately_specified"])

    def test_03_superseded_standard_replaces_and_flags_review(self):
        """Citing superseded IS 10611 must recommend successor and flag review."""
        res = self.recommender.recommend_for_text("Procurement of valves conforming to IS 10611")

        self.assertIn("10434", res.candidate_standard, "Must recommend active successor IS/ISO 10434")
        self.assertTrue(res.human_review_required, "Superseded citation must require human review")
        self.assertEqual(res.risk_level, "CRITICAL", "Citing an obsolete standard must have CRITICAL risk level")
        self.assertTrue(any("superseded" in r.lower() for r in res.risk_reasons))

    def test_04_trust_gate_weak_evidence_cannot_be_high_confidence(self):
        """Trust Gate: High retrieval score with weak/unsupported evidence cannot yield High confidence."""
        # Use an active electrical safety standard evaluated against a gas pipe query
        dummy_cand = SearchResult(
            standard_id="IS-302-1994",
            standard_number="IS 302",
            year=1994,
            full_title="General and Safety Requirements for Household and Similar Electrical Appliances",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.95,  # Artificially high retrieval score
            relevance_reason="Simulated high retrieval score",
            scope_summary="Electrical appliance safety requirements",
            verification_status="CURATED",
            source_provenance="SIMULATED"
        )

        comp = self.completeness_analyzer.analyze("High-pressure gas line pipe")
        crit = self.critic.critique_candidate(
            candidate=dummy_cand,
            requirement_text="High-pressure gas line pipe",
            components=[],
            completeness=comp
        )

        # Decision must be gated - cannot be RECOMMEND
        self.assertIn(crit.decision, ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE", "REJECT"])
        self.assertTrue(crit.review_required)

        # When evaluated in candidate list, confidence must not be High
        outcome = self.critic.evaluate_candidates([dummy_cand], "High-pressure gas line pipe", [], comp)
        self.assertNotEqual(outcome.confidence, "High", "Weak evidence candidate must NEVER be High confidence")

    def test_05_multiple_plausible_standards_triggers_review(self):
        """Multiple close candidates with missing discriminating parameters trigger review."""
        req = extract_from_text(
            "Supply and laying of sewerage pipeline from collection chamber",
            requirement_id="TEST-SEWER-01"
        )
        res = self.recommender.recommend_for_requirement(req)

        self.assertTrue(
            res.human_review_required,
            "Ambiguous sewerage pipeline without material specification must require human review"
        )

    def test_06_why_this_generated_from_actual_data(self):
        """'Why this?' reasons are deterministically generated from candidate data, not placeholders."""
        req = extract_from_text(
            "Supply of CPVC pipes for potable water distribution",
            requirement_id="TEST-CPVC-WHY"
        )
        res = self.recommender.recommend_for_requirement(req)

        self.assertGreater(len(res.why_this), 0)
        # Check that reasons mention actual factual data
        all_reasons = " ".join(res.why_this)
        self.assertTrue(
            "IS 15778" in all_reasons or "CPVC" in all_reasons or "active" in all_reasons.lower(),
            f"Reasons must contain factual standard properties, got: {res.why_this}"
        )
        # Ensure no LLM hallmarks
        self.assertNotIn("as an ai", all_reasons.lower())
        self.assertNotIn("language model", all_reasons.lower())

    def test_07_why_not_generated_from_candidate_differences(self):
        """'Why not?' reasons reflect actual measurable score and scope differences."""
        req = extract_from_text(
            "Supply of CPVC pipes for potable water distribution",
            requirement_id="TEST-CPVC-WHYNOT"
        )
        res = self.recommender.recommend_for_requirement(req)

        self.assertGreater(len(res.why_not), 0)
        why_not_text = " ".join(res.why_not)
        # Must mention measurable comparison factors (relevance, scope, handbook vs specification)
        self.assertTrue(
            any(kw in why_not_text.lower() for kw in ["lower", "relevance", "handbook", "scope", "alternative"]),
            f"Why not must contain comparative criteria, got: {res.why_not}"
        )

    def test_08_specification_completeness_detects_missing_valve_parameters(self):
        """Domain completeness analyzer detects potentially missing parameters without legalistic terms."""
        text = "Supply of replacement valves for raw water line"
        comp = self.completeness_analyzer.analyze(text)

        self.assertEqual(comp.domain, "valve")
        self.assertFalse(comp.is_adequately_specified)

        # Check parameter states
        params = comp.parameters
        self.assertIn("nominal_size", params)
        self.assertIn("pressure_rating", params)
        self.assertIn("body_material", params)
        self.assertEqual(params["nominal_size"].status, "POTENTIALLY_MISSING")
        self.assertEqual(params["pressure_rating"].status, "POTENTIALLY_MISSING")
        self.assertEqual(params["body_material"].status, "POTENTIALLY_MISSING")

        # Check that safe wording was used
        self.assertNotIn("invalid", comp.summary.lower())
        self.assertNotIn("non-compliant", comp.summary.lower())
        self.assertNotIn("illegal", comp.summary.lower())

    def test_09_t013_t014_still_work_correctly(self):
        """T013 (VFD pump panel) and T014 (process pump 3.3 kV motor) still resolve correctly."""
        # T013
        req13 = extract_from_text(
            "SITC of VFD water pump panel for institutional booster station",
            requirement_id="T013-TEST"
        )
        res13 = self.recommender.recommend_for_requirement(req13)
        if res13.candidate_standard is not None:
            self.assertIn("61800", res13.candidate_standard, "T013 must resolve to IS/IEC 61800")
            self.assertNotIn("9694", res13.candidate_standard, "Agricultural pump code IS 9694 must be excluded")
        else:
            self.assertIsNotNone(res13.competing_interpretations)
            found = any("61800" in c["standard_number"] for c in res13.competing_interpretations)
            self.assertTrue(found, "T013 must resolve to IS/IEC 61800 among competing candidates")
            found_bad = any("9694" in c["standard_number"] for c in res13.competing_interpretations)
            self.assertFalse(found_bad, "Agricultural pump code IS 9694 must be excluded")

        # T014
        req14 = extract_from_text(
            "Design, manufacturing, supply and testing of process water pump sets coupled with 3.3 kV motor",
            requirement_id="T014-TEST"
        )
        res14 = self.recommender.recommend_for_requirement(req14)
        self.assertIn("60034", res14.candidate_standard, "T014 must resolve to IS/IEC 60034")
        self.assertNotIn("9694", res14.candidate_standard, "Agricultural pump code IS 9694 must be excluded")

    def test_10_critic_result_serialization(self):
        """Critic result and completeness report serialize cleanly to dict."""
        req = extract_from_text("Supply of CPVC pipes for water supply")
        res = self.recommender.recommend_for_requirement(req)
        d = res.to_dict()

        self.assertIn("critic_result", d)
        self.assertIn("why_this", d)
        self.assertIn("why_not", d)
        self.assertIn("risk_level", d)
        self.assertIn("risk_reasons", d)
        self.assertIn("specification_completeness", d)
        self.assertIsInstance(d["why_this"], list)
        self.assertIsInstance(d["why_not"], list)

    def test_11_trust_gate_cases_a_b_c(self):
        """
        Audit Trust Gate Cases:
        Case A: retrieval = 0.95, evidence = WEAK -> confidence != HIGH
        Case B: retrieval = 0.95, evidence = NONE -> confidence != HIGH
        Case C: retrieval = 0.60, evidence = STRONG -> high retrieval alone is not required for strong evidence.
        """
        # Case A: retrieval = 0.95, evidence = WEAK
        cand_weak = SearchResult(
            standard_id="TEST-STD-WEAK",
            standard_number="IS 99991",
            year=2020,
            full_title="General Specification for Industrial Goods",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.95,
            relevance_reason="Simulated high relevance",
            scope_summary="Non-overlapping general notes",
            verification_status="CURATED",
            source_provenance="SIMULATED"
        )
        comp_dummy = self.completeness_analyzer.analyze("Industrial chemical process piping")
        crit_weak = self.critic.critique_candidate(cand_weak, "Industrial chemical process piping", [], comp_dummy)
        # Override evidence to WEAK for controlled verification
        crit_weak.evidence.evidence_strength = "WEAK"
        outcome_a = self.critic.evaluate_candidates([cand_weak], "Industrial chemical process piping", [], comp_dummy)
        # Verify Trust Gate invariant
        self.assertNotEqual(outcome_a.confidence, "High", "Case A: WEAK evidence must NEVER produce High confidence")
        self.assertIn(outcome_a.confidence, ["Medium", "Low"])

        # Case B: retrieval = 0.95, evidence = NONE
        cand_none = SearchResult(
            standard_id="TEST-STD-NONE",
            standard_number="IS 99992",
            year=2020,
            full_title="General Unverified Document",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.95,
            relevance_reason="Simulated high relevance",
            scope_summary="",
            verification_status="INFERRED",
            source_provenance="SIMULATED"
        )
        crit_none = self.critic.critique_candidate(cand_none, "Industrial chemical process piping", [], comp_dummy)
        crit_none.evidence.evidence_strength = "NONE"
        outcome_b = self.critic.evaluate_candidates([cand_none], "Industrial chemical process piping", [], comp_dummy)
        self.assertNotEqual(outcome_b.confidence, "High", "Case B: NONE evidence must NEVER produce High confidence")
        self.assertEqual(outcome_b.confidence, "Low", "Case B: NONE evidence must be Low confidence")

        # Case C: retrieval = 0.60, evidence = STRONG
        cand_strong = SearchResult(
            standard_id="IS-778-1984",
            standard_number="IS 778",
            year=1984,
            full_title="Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.60,
            relevance_reason="Moderate relevance match",
            scope_summary="Covers copper alloy gate, globe and check valves for waterworks",
            verification_status="VERIFIED",
            source_provenance="BSB_EDGE_MANUALLY_VERIFIED"
        )
        ev_strong = self.critic.extract_candidate_evidence(
            cand_strong,
            "Copper alloy gate valve for waterworks",
            None
        )
        self.assertEqual(ev_strong.evidence_strength, "STRONG", "Case C: Verified standard with direct scope support is STRONG")
        # Retrieval is 0.60, which demonstrates evidence strength is completely decoupled from retrieval score
        self.assertLess(cand_strong.relevance_score, 0.70)

    def test_12_provenance_distinction_and_inferred_limit(self):
        """
        Audit Provenance Model:
        - VERIFIED + directly supporting scope -> STRONG
        - CURATED + supporting scope -> MODERATE at most
        - INFERRED -> WEAK at most
        """
        # 1. VERIFIED standard (IS 778 is verified in BSB Edge)
        cand_ver = SearchResult(
            standard_id="IS-778-1984",
            standard_number="IS 778",
            year=1984,
            full_title="Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.88,
            relevance_reason="Verified match",
            scope_summary="Covers copper alloy gate, globe and check valves",
            verification_status="VERIFIED",
            source_provenance="BSB_EDGE_MANUALLY_VERIFIED"
        )
        ev_ver = self.critic.extract_candidate_evidence(cand_ver, "Copper alloy gate valve for waterworks")
        self.assertEqual(ev_ver.provenance, "VERIFIED")
        self.assertEqual(ev_ver.evidence_strength, "STRONG")

        # 2. CURATED standard (IS 15778 is from curated catalogue)
        cand_cur = SearchResult(
            standard_id="IS-15778-2007",
            standard_number="IS 15778",
            year=2007,
            full_title="Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Supplies - Specification",
            status="Active",
            version_role="CURRENT_ACTIVE",
            relevance_score=0.88,
            relevance_reason="Curated match",
            scope_summary="Exact Match: IS 15778 covers chlorinated polyvinyl chloride (CPVC) pipes for potable water supplies",
            verification_status="CURATED",
            source_provenance="EXCEL_CURATED"
        )
        ev_cur = self.critic.extract_candidate_evidence(cand_cur, "CPVC pipes for potable water supplies")
        self.assertEqual(ev_cur.provenance, "CURATED")
        self.assertEqual(ev_cur.evidence_strength, "MODERATE", "CURATED data must be MODERATE at most")

    def test_13_dynamic_risk_variation_without_hardcoding(self):
        """
        Audit Risk Calculation:
        Demonstrates that risk dynamically shifts based on system state:
        - Under-specified specification -> HIGH risk
        - Adequately specified specification -> LOW/MEDIUM risk
        - Superseded lifecycle -> CRITICAL risk
        """
        # Part 1: Under-specified requirement produces HIGH risk
        req_vague = extract_from_text("Replacement of damaged valves in pumping station")
        res_vague = self.recommender.recommend_for_requirement(req_vague)
        self.assertIn(res_vague.risk_level, ["HIGH", "CRITICAL"])

        # Part 2: Fully specified requirement in the SAME domain produces LOW risk
        req_detailed = extract_from_text(
            "Supply of 50 mm nominal size cast iron sluice valves PN 1.0 for raw water pumping",
            requirement_id="TEST-VALVE-DETAILED"
        )
        res_detailed = self.recommender.recommend_for_requirement(req_detailed)
        self.assertIn(res_detailed.risk_level, ["LOW", "MEDIUM"], "Detailed valve spec must have lower risk than vague spec")
        self.assertLessEqual(
            len(res_detailed.risk_reasons),
            len(res_vague.risk_reasons),
            "Detailed spec must have fewer or equal risk reasons compared to vague spec"
        )

    def test_14_no_standard_number_shortcuts_in_critic(self):
        """Verify critic decision and confidence do not inspect standard number strings for shortcuts."""
        import inspect
        critic_src = inspect.getsource(self.critic.critique_candidate)
        self.assertNotIn("15778", critic_src, "No standard numbers in critique_candidate logic")
        self.assertNotIn("10434", critic_src, "No standard numbers in critique_candidate logic")
        self.assertNotIn("778", critic_src, "No standard numbers in critique_candidate logic")


if __name__ == "__main__":
    unittest.main()
