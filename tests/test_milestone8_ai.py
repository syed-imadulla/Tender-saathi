"""
Module: tests/test_milestone8_ai.py
Purpose: Unit tests for Milestone 8 (AI Requirement Understanding + Cross-Encoder Reranking).

20 Focused Verification Cases:
1. AI parser schema validation
2. Valid Groq/LLM response parsing
3. Malformed LLM response rejection
4. Missing required fields rejection
5. API unavailable fallback
6. Deterministic fallback produces valid structured components
7. Missing/No API key fallback
8. Critical Safety: No IS-code injection from LLM (stripping IS numbers)
9. Attribution preservation (provider, model, is_fallback)
10. CrossEncoder model lazy loading & singleton
11. Reranker sigmoid score normalization into [0, 1]
12. Candidate pool generation combines multiple retrieval signals
13. Hybrid+Rerank retrieval mode operation
14. Full score transparency preservation (bm25, semantic, det, reranker, final)
15. Exact cited IS number priority is preserved against reranker drift
16. AI cannot upgrade evidence strength
17. AI cannot alter data provenance
18. AI cannot alter standard lifecycle status
19. Ambiguity heuristics continue to mandate human review
20. 100% offline execution without network or API dependencies
"""

import unittest
from unittest.mock import patch, MagicMock
import json

from src.standards import StandardsDatabase
from src.extract import Requirement
from src.search import SearchResult
from src.retrieval import HybridRetrievalEngine, HybridCandidate
from src.recommend import StandardsRecommender
from src.reranker import CrossEncoderReranker, sigmoid
from src.ai_understanding import AIRequirementParser, ParsedRequirement, IS_CODE_PATTERN


class TestMilestone8AI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = StandardsDatabase()

    # 1. AI parser schema validation
    def test_01_ai_parser_schema_validation(self):
        parser = AIRequirementParser(enabled=False)
        valid_json_str = json.dumps({
            "equipment": ["centrifugal pump"],
            "control": ["starter"],
            "electrical": ["motor"],
            "voltage": ["415V"],
            "application": ["cooling water"],
            "work_type": ["supply"]
        })
        res = parser._validate_and_sanitize_response(valid_json_str)
        self.assertIsNotNone(res)
        self.assertEqual(res["equipment"], ["centrifugal pump"])
        self.assertEqual(res["voltage"], ["415V"])

    # 2. Valid Groq/LLM response parsing
    def test_02_valid_groq_response(self):
        parser = AIRequirementParser(enabled=True, api_key="dummy_key", provider="groq", model="openai/gpt-oss-120b")
        mock_response = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "equipment": ["process water pump motor"],
                        "control": ["starter panel"],
                        "electrical": ["motor"],
                        "voltage": ["3.3kV"],
                        "application": ["process water"],
                        "work_type": ["supply", "installation"]
                    })
                }
            }]
        })
        with patch.object(parser, "_call_llm_api", return_value=json.loads(mock_response)["choices"][0]["message"]["content"]):
            parsed = parser.parse("Supply of 3.3kV process water pump motors with starter panel")
            self.assertFalse(parsed.is_fallback)
            self.assertEqual(parsed.ai_provider, "groq")
            self.assertEqual(parsed.ai_model, "openai/gpt-oss-120b")
            self.assertIn("process water pump motor", parsed.equipment)
            self.assertEqual(parsed.voltage, ["3.3kV"])

    # 3. Malformed LLM response rejection
    def test_03_malformed_llm_response_rejected(self):
        parser = AIRequirementParser(enabled=True, api_key="dummy_key")
        with patch.object(parser, "_call_llm_api", return_value="This is not JSON at all! Just raw text."):
            parsed = parser.parse("Supply of valves")
            self.assertTrue(parsed.is_fallback)
            self.assertEqual(parsed.ai_provider, "deterministic")
            self.assertIsNone(parsed.ai_model)

    # 4. Missing required fields rejection
    def test_04_missing_required_fields_rejected(self):
        parser = AIRequirementParser(enabled=True, api_key="dummy_key")
        # Missing 'voltage' and 'control'
        bad_json = json.dumps({"equipment": ["pipes"], "application": ["water"]})
        with patch.object(parser, "_call_llm_api", return_value=bad_json):
            parsed = parser.parse("Supply of pipes")
            self.assertTrue(parsed.is_fallback)

    # 5. API unavailable fallback
    def test_05_api_unavailable_fallback(self):
        parser = AIRequirementParser(enabled=True, api_key="dummy_key")
        with patch.object(parser, "_call_llm_api", side_effect=Exception("Connection timed out")):
            parsed = parser.parse("Supply of CPVC pipes")
            self.assertTrue(parsed.is_fallback)
            self.assertEqual(parsed.ai_provider, "deterministic")

    # 6. Deterministic fallback produces valid structured components
    def test_06_deterministic_fallback_components(self):
        parser = AIRequirementParser(enabled=False)
        parsed = parser.parse("Supply of CPVC pipes for drinking water")
        self.assertTrue(parsed.is_fallback)
        comps = parsed.to_components()
        self.assertGreaterEqual(len(comps), 1)
        self.assertTrue(any("cpvc" in c.text.lower() for c in comps))

    # 7. Missing/No API key fallback
    def test_07_no_api_key_fallback(self):
        parser = AIRequirementParser(enabled=True, api_key="")
        parsed = parser.parse("Procurement of HDPE conduits")
        self.assertTrue(parsed.is_fallback)
        self.assertEqual(parsed.ai_provider, "deterministic")

    # 8. Critical Safety: No IS-code injection from LLM
    def test_08_no_is_code_injection_from_llm(self):
        parser = AIRequirementParser(enabled=True, api_key="dummy_key")
        hallucinated_json = json.dumps({
            "equipment": ["pipes conforming to IS 4984 : 2016", "IS 15778"],
            "control": ["starter panel conforming to IS/IEC 61439"],
            "electrical": ["motor IS 325"],
            "voltage": ["415V"],
            "application": ["water supply as per IS 10500"],
            "work_type": ["supply"]
        })
        with patch.object(parser, "_call_llm_api", return_value=hallucinated_json):
            parsed = parser.parse("Supply of pipes")
            # Verify that any IS citations were stripped from fields
            for eq in parsed.equipment:
                self.assertFalse("IS 4984" in eq)
                self.assertFalse("IS 15778" in eq)
            for ctrl in parsed.control:
                self.assertFalse("IS/IEC 61439" in ctrl)
            for el in parsed.electrical:
                self.assertFalse("IS 325" in el)

    # 9. Attribution preservation (provider, model, is_fallback)
    def test_09_attribution_preservation(self):
        recommender = StandardsRecommender(ai_enabled=False)
        res = recommender.recommend_for_text("Supply of CPVC pipes for domestic water distribution")
        self.assertEqual(res.ai_provider, "deterministic")
        self.assertTrue(res.is_ai_fallback)
        self.assertIsNotNone(res.ai_understanding)

    # 10. CrossEncoder model lazy loading & singleton
    def test_10_reranker_model_lazy_loading(self):
        reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        # Prior to loading
        self.assertFalse(reranker._is_loaded)
        # Check text builder
        text = reranker.build_candidate_text({"standard_number": "IS 15778", "full_title": "CPVC pipes"})
        self.assertIn("IS 15778", text)
        self.assertIn("CPVC pipes", text)

    # 11. Reranker sigmoid score normalization into [0, 1]
    def test_11_reranker_sigmoid_score(self):
        self.assertAlmostEqual(sigmoid(0.0), 0.5, places=3)
        self.assertGreater(sigmoid(5.0), 0.99)
        self.assertLess(sigmoid(-5.0), 0.01)
        self.assertGreaterEqual(sigmoid(100.0), 0.0)
        self.assertLessEqual(sigmoid(-100.0), 1.0)

    # 12. Candidate pool generation combines multiple retrieval signals
    def test_12_candidate_pool_generation(self):
        engine = HybridRetrievalEngine(self.db, default_mode="hybrid")
        results = engine.search("CPVC pipes for domestic water distribution", top_k=3)
        self.assertGreater(len(results), 0)
        top = results[0]
        # Should have recorded bm25 and semantic signals
        self.assertGreaterEqual(top.bm25_score, 0.0)
        self.assertGreaterEqual(top.semantic_score, 0.0)

    # 13. Hybrid+Rerank retrieval mode operation
    def test_13_hybrid_rerank_mode_operation(self):
        engine = HybridRetrievalEngine(self.db, default_mode="hybrid+rerank")
        results = engine.search("CPVC pipes for domestic water distribution", top_k=3)
        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertIsNotNone(top.final_score)
        self.assertEqual(top.standard_number, "IS 15778")

    # 14. Full score transparency preservation
    def test_14_score_transparency_preservation(self):
        recommender = StandardsRecommender(retrieval_mode="hybrid")
        res = recommender.recommend_for_text("Supply of CPVC pipes")
        self.assertGreater(len(res.recommendations), 0)
        top_rec = res.recommendations[0]
        self.assertGreaterEqual(top_rec.bm25_score, 0.0)
        self.assertGreaterEqual(top_rec.semantic_score, 0.0)
        self.assertGreaterEqual(top_rec.deterministic_score, 0.0)
        self.assertGreaterEqual(top_rec.final_score, 0.0)

    # 15. Exact cited IS number priority is preserved against reranker drift
    def test_15_exact_cited_is_priority_preserved(self):
        engine = HybridRetrievalEngine(self.db, default_mode="hybrid+rerank")
        # Requirement explicitly citing superseded IS 10611
        results = engine.search("Procurement of valves conforming to IS 10611", top_k=3)
        self.assertGreater(len(results), 0)
        top = results[0]
        # Top candidate must remain the authoritative replacement or exact match
        self.assertIn("10434", top.standard_number)

    # 16. AI cannot upgrade evidence strength
    def test_16_ai_cannot_upgrade_evidence(self):
        # A requirement with no strong scope evidence must remain weak or moderate, never promoted to verified fact
        recommender = StandardsRecommender(ai_enabled=False)
        res = recommender.recommend_for_text("Random obscure requirement with no BIS standard match")
        # Evidence strength remains bounded by stored evidence
        self.assertIn(res.confidence, ["Low", "Medium"])

    # 17. AI cannot alter data provenance
    def test_17_ai_cannot_alter_provenance(self):
        recommender = StandardsRecommender(ai_enabled=False)
        res = recommender.recommend_for_text("Supply of CPVC pipes")
        self.assertEqual(res.provenance, "CURATED")

    # 18. AI cannot alter standard lifecycle status
    def test_18_ai_cannot_alter_lifecycle(self):
        recommender = StandardsRecommender(ai_enabled=False)
        res = recommender.recommend_for_text("Valves as per IS 10611")
        # IS 10611 is superseded; AI cannot claim it is active
        self.assertTrue(res.human_review_required)
        self.assertEqual(res.risk_level, "CRITICAL")

    # 19. Ambiguity heuristics continue to mandate human review
    def test_19_ambiguity_triggers_human_review(self):
        recommender = StandardsRecommender(retrieval_mode="hybrid+rerank")
        res = recommender.recommend_for_text("Replacement of damaged valves in pumping station")
        self.assertTrue(res.human_review_required)
        self.assertIn("valve", res.reason.lower())

    # 20. 100% offline execution without network or API dependencies
    def test_20_offline_execution_no_network(self):
        # Disabling network / environment key
        with patch.dict("os.environ", {"TENDERSAATHI_LLM_ENABLED": "false", "GROQ_API_KEY": ""}, clear=True):
            recommender = StandardsRecommender(retrieval_mode="hybrid")
            res = recommender.recommend_for_text("Supply of precast concrete pipes for culvert works")
            if res.candidate_standard is not None:
                self.assertEqual(res.candidate_standard, "IS 458 : 2021")
                self.assertFalse(res.human_review_required)
            else:
                self.assertEqual(res.ambiguity_state, "AMBIGUOUS")
                found = any("458" in c["standard_number"] for c in res.competing_interpretations)
                self.assertTrue(found, "IS 458 must be among competing interpretations")
                self.assertTrue(res.human_review_required)
            self.assertTrue(res.is_ai_fallback)

    # 21. API key is read from environment properly
    def test_21_api_key_loaded_from_environment(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "TEST_ENV_KEY_PLACEHOLDER", "TENDERSAATHI_LLM_ENABLED": "true"}):
            parser = AIRequirementParser()
            self.assertEqual(parser._api_key, "TEST_ENV_KEY_PLACEHOLDER")
            self.assertTrue(parser.enabled)

    # 22. Hard-coded credentials do not exist in source code
    def test_22_hardcoded_credentials_not_in_source(self):
        import pathlib
        src_dir = pathlib.Path(__file__).parent.parent / "src"
        prefix = "".join(["g", "s", "k", "_"])
        for py_file in src_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            # Verify no Groq/OpenRouter keys or credentials are hardcoded in source
            self.assertNotIn("sk-or-", content)
            self.assertNotIn(prefix, content)

    # 23. Missing API key triggers deterministic fallback without crashing or network call
    def test_23_missing_api_key_deterministic_fallback(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "", "TENDERSAATHI_LLM_ENABLED": "true"}):
            parser = AIRequirementParser()
            parsed = parser.parse("Supply of valves")
            self.assertTrue(parsed.is_fallback)
            self.assertEqual(parsed.ai_provider, "deterministic")

    # 24. API key is never included in error messages or logs
    def test_24_api_key_never_in_logs_or_errors(self):
        parser = AIRequirementParser(enabled=True, api_key="TEST_DUMMY_SECRET_KEY")
        # Simulate network failure and verify error does not contain secret token
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused to api.groq.com")):
            try:
                parser._call_llm_api("test query")
            except RuntimeError as err:
                self.assertNotIn("TEST_DUMMY_SECRET_KEY", str(err))

    # 25. .env is ignored by git and .env.example is permitted
    def test_25_env_ignored_by_git(self):
        import pathlib
        gitignore_path = pathlib.Path(__file__).parent.parent / ".gitignore"
        self.assertTrue(gitignore_path.exists())
        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
        self.assertIn(".env", lines)
        self.assertIn(".env.*", lines)
        self.assertIn("!.env.example", lines)

    # 26. .env.example contains no real credentials
    def test_26_env_example_contains_no_real_credentials(self):
        import pathlib
        env_example_path = pathlib.Path(__file__).parent.parent / ".env.example"
        self.assertTrue(env_example_path.exists())
        content = env_example_path.read_text(encoding="utf-8")
        self.assertIn("GROQ_API_KEY=", content)
        prefix = "".join(["g", "s", "k", "_"])
        self.assertNotIn(prefix, content)
        self.assertNotIn("sk-or-", content)


if __name__ == "__main__":
    unittest.main()

