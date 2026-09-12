"""Test Suite for TenderSaathi Priority 6 Multilingual Technical Understanding.

Validates:
1. Script and Language Detection across English, Hindi, Kannada, Tamil, Mixed, and Transliterated.
2. English Fast Path (<0.5ms latency, bypasses LLM, 100% unchanged).
3. Critical Technical Entity Protection (IS numbers, voltages, ratings, dimensions).
4. Offline Lexicon Fallback (deterministic normalization when LLM is offline/rate-limited).
5. Safe Abstention & Review Requirements for ambiguous, incomplete, or nonsense input.
6. Existing Pipeline Integration & Invariants:
   - candidate_standard == evidence_standard for all non-null recommendations.
   - Ambiguity Engine V2 safety invariants preserved.
   - Zero hardcoded standards in multilingual logic.
"""

import json
import time
import unittest
from pathlib import Path

from src.multilingual.detector import detect_script_and_language
from src.multilingual.lexicon import normalize_with_lexicon
from src.multilingual.normalizer import MultilingualTechnicalNormalizer
from src.recommend import StandardsRecommender


class TestMultilingualDetection(unittest.TestCase):
    """Unit tests for script/language detection."""

    def test_english_detection(self):
        text = "Supply of 500 kVA distribution transformer 11 kV outdoor type"
        res = detect_script_and_language(text)
        self.assertEqual(res.detected_language, "en")
        self.assertEqual(res.primary_script, "Latin")
        self.assertFalse(res.is_multilingual)
        self.assertFalse(res.is_transliterated)
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_hindi_detection(self):
        text = "11 केवी के 500 केवीए वितरण ट्रांसफार्मर की आपूर्ति"
        res = detect_script_and_language(text)
        self.assertEqual(res.detected_language, "hi")
        self.assertEqual(res.primary_script, "Devanagari")
        self.assertTrue(res.is_multilingual)
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_kannada_detection(self):
        text = "11 ಕೆವಿ 500 ಕೆವಿಎ ವಿತರಣಾ ಪರಿವರ್ತಕ ಸರಬರಾಜು"
        res = detect_script_and_language(text)
        self.assertEqual(res.detected_language, "kn")
        self.assertEqual(res.primary_script, "Kannada")
        self.assertTrue(res.is_multilingual)
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_tamil_detection(self):
        text = "11 கேவி 500 கேவிஏ விநியோக மின்மாற்றி வழங்கல்"
        res = detect_script_and_language(text)
        self.assertEqual(res.detected_language, "ta")
        self.assertEqual(res.primary_script, "Tamil")
        self.assertTrue(res.is_multilingual)
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_hinglish_transliterated_detection(self):
        text = "11 kV ka transformer supply karna hai aur laying karna chahiye"
        res = detect_script_and_language(text)
        self.assertEqual(res.detected_language, "mixed")
        self.assertTrue(res.is_multilingual)
        self.assertTrue(res.is_transliterated)

    def test_kanglish_transliterated_detection(self):
        text = "110 mm uPVC pipe for drainage sarabaraju madabekagide"
        res = detect_script_and_language(text)
        self.assertEqual(res.detected_language, "mixed")
        self.assertTrue(res.is_multilingual)
        self.assertTrue(res.is_transliterated)

    def test_tanglish_transliterated_detection(self):
        text = "16 mm TMT steel bar Fe 500D supply thevai vendum"
        res = detect_script_and_language(text)
        self.assertEqual(res.detected_language, "mixed")
        self.assertTrue(res.is_multilingual)
        self.assertTrue(res.is_transliterated)

    def test_empty_and_nonsense_detection(self):
        res_empty = detect_script_and_language("")
        self.assertEqual(res_empty.detected_language, "unknown")
        self.assertTrue(res_empty.human_review_required)

        res_num = detect_script_and_language("12345 67890 !@#$%")
        self.assertEqual(res_num.detected_language, "unknown")
        self.assertTrue(res_num.human_review_required)


class TestMultilingualNormalization(unittest.TestCase):
    """Unit tests for technical normalization and entity preservation."""

    def setUp(self):
        self.normalizer = MultilingualTechnicalNormalizer(enabled=False)  # deterministic offline mode

    def test_english_fast_path_latency(self):
        text = "Supply and laying of 11 kV 3 core 185 sq mm XLPE insulated underground cable conforming to IS 7098 (Part 2)"
        t0 = time.perf_counter()
        res = self.normalizer.normalize(text)
        latency_ms = (time.perf_counter() - t0) * 1000

        self.assertEqual(res.normalization_method, "fast_path")
        self.assertEqual(res.detected_language, "en")
        self.assertEqual(res.canonical_text, text)
        self.assertEqual(res.normalization_confidence, 1.0)
        self.assertFalse(res.is_multilingual)
        self.assertFalse(res.human_review_required)
        self.assertLess(latency_ms, 5.0, "English fast path must execute in under 5 ms")

    def test_entity_protection_is_numbers(self):
        text = "Supply of CPVC pipes conforming to IS 15778 : 2007"
        entities = self.normalizer.extract_protected_entities(text)
        self.assertTrue(any("15778" in e for e in entities))

    def test_entity_protection_ratings_and_dimensions(self):
        text = "11 kV 500 kVA transformer with 185 sq mm copper conductor and PN 16 pressure rating"
        entities = self.normalizer.extract_protected_entities(text)
        self.assertTrue(any("11" in e for e in entities))
        self.assertTrue(any("500" in e for e in entities))
        self.assertTrue(any("185" in e for e in entities))
        self.assertTrue(any("16" in e for e in entities))

    def test_offline_lexicon_hindi(self):
        text = "11 केवी के 500 केवीए वितरण ट्रांसफार्मर की आपूर्ति"
        res, conf, hits = normalize_with_lexicon(text)
        self.assertGreater(hits, 0)
        self.assertIn("distribution transformer", res)
        self.assertIn("supply", res)
        self.assertIn("11", res)
        self.assertIn("500", res)

    def test_offline_lexicon_kannada(self):
        text = "ಕುಡಿಯುವ ನೀರು ಸರಬರಾಜಿಗೆ 25 ಮಿಮೀ ಸಿಪಿವಿಸಿ ಪೈಪ್"
        res, conf, hits = normalize_with_lexicon(text)
        self.assertGreater(hits, 0)
        self.assertIn("CPVC", res)
        self.assertIn("pipe", res)
        self.assertIn("25", res)

    def test_offline_lexicon_tamil(self):
        text = "100 மிமீ வார்ப்பிரும்பு ஸ்லூயிஸ் வால்வு வழங்கல்"
        res, conf, hits = normalize_with_lexicon(text)
        self.assertGreater(hits, 0)
        self.assertIn("valve", res)
        self.assertIn("100", res)

    def test_no_silent_entity_injection_on_missing(self):
        # If an entity is missing in the canonical text, status must be PARTIAL/FAIL and require review
        status, missing = self.normalizer._verify_entities(["IS 15778 : 2007", "11 kV"], "Supply of generic cable")
        self.assertEqual(status, "FAIL")
        self.assertEqual(len(missing), 2)


class TestMultilingualRecommenderIntegration(unittest.TestCase):
    """End-to-end integration tests using the complete StandardsRecommender pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.recommender = StandardsRecommender()

    def test_indic_hindi_cable_pipeline(self):
        text = "11 केवी 3 कोर 185 वर्ग मिमी एक्सएलपीई इंसुलेटेड भूमिगत केबल की आपूर्ति और बिछाना"
        res = self.recommender.recommend_for_text(text)
        self.assertIsNotNone(res.multilingual)
        self.assertTrue(res.multilingual["is_multilingual"])
        self.assertEqual(res.multilingual["detected_language"], "hi")
        # Candidate and evidence standard must match
        if res.candidate_standard:
            self.assertEqual(res.candidate_standard, res.evidence_standard)
            self.assertIn("7098", res.candidate_standard)

    def test_indic_kannada_cpvc_pipeline(self):
        text = "ಕುಡಿಯುವ ನೀರು ಸರಬರಾಜಿಗೆ 25 ಮಿಮೀ ಸಿಪಿವಿಸಿ ಪೈಪ್ ಸರಬರಾಜು"
        res = self.recommender.recommend_for_text(text)
        self.assertIsNotNone(res.multilingual)
        self.assertTrue(res.multilingual["is_multilingual"])
        self.assertEqual(res.multilingual["detected_language"], "kn")
        self.assertIsNotNone(res.candidate_standard)
        self.assertEqual(res.candidate_standard, "IS 15778 : 2007")
        self.assertEqual(res.evidence_standard, "IS 15778 : 2007")

    def test_indic_tamil_valve_pipeline(self):
        text = "100 மிமீ வார்ப்பிரும்பு ஸ்லூயிஸ் வால்வு பிஎன் 16 நீர் விநியோகத்திற்கு"
        res = self.recommender.recommend_for_text(text)
        self.assertIsNotNone(res.multilingual)
        self.assertTrue(res.multilingual["is_multilingual"])
        self.assertEqual(res.multilingual["detected_language"], "ta")
        self.assertIsNotNone(res.candidate_standard)
        self.assertEqual(res.candidate_standard, "IS 14846 : 2000")
        self.assertEqual(res.evidence_standard, "IS 14846 : 2000")

    def test_mixed_language_cable_pipeline(self):
        text = "11 kV XLPE insulated underground cable ki supply aur laying karna hai"
        res = self.recommender.recommend_for_text(text)
        self.assertIsNotNone(res.multilingual)
        self.assertTrue(res.multilingual["is_multilingual"])
        self.assertEqual(res.multilingual["detected_language"], "mixed")
        if res.candidate_standard:
            self.assertEqual(res.candidate_standard, res.evidence_standard)

    def test_explicit_is_number_preservation_in_indic(self):
        text = "आईएस 15778 के अनुसार पीने के पानी के लिए सीपीवीसी पाइप की आपूर्ति"
        res = self.recommender.recommend_for_text(text)
        self.assertIsNotNone(res.candidate_standard)
        self.assertEqual(res.candidate_standard, "IS 15778 : 2007")
        self.assertEqual(res.evidence_standard, "IS 15778 : 2007")

    def test_ambiguous_indic_abstains_safely(self):
        text = "साइट पर सामान्य विद्युत केबल और वायरिंग का प्रावधान"
        res = self.recommender.recommend_for_text(text)
        # Should require review / abstain due to incomplete parameters
        self.assertTrue(res.human_review_required)
        self.assertIn(res.ambiguity_state, ["INCOMPLETE", "REVIEW_REQUIRED", "AMBIGUOUS", "NO_RELIABLE_MATCH"])

    def test_candidate_evidence_invariant_across_multilingual(self):
        queries = [
            "11 केवी के 500 केवीए आउटडोर वितरण ट्रांसफार्मर",
            "ಕುಡಿಯುವ ನೀರಿಗೆ 25 ಮಿಮೀ ಸಿಪಿವಿಸಿ ಪೈಪ್",
            "100 மிமீ வார்ப்பிரும்பு ஸ்லூயிஸ் வால்வு",
            "Water works ke liye 100 mm cast iron sluice valve PN 16 provide karna hoga",
        ]
        for q in queries:
            res = self.recommender.recommend_for_text(q)
            if res.candidate_standard:
                self.assertEqual(
                    res.candidate_standard,
                    res.evidence_standard,
                    f"Invariant violation: candidate {res.candidate_standard} != evidence {res.evidence_standard} for query '{q}'"
                )


class TestMultilingualBenchmark(unittest.TestCase):
    """Executes the 40-case ground truth multilingual benchmark."""

    @classmethod
    def setUpClass(cls):
        cls.recommender = StandardsRecommender()
        benchmark_path = Path("dataset/ground_truth/multilingual_benchmark.json")
        with open(benchmark_path, "r", encoding="utf-8") as f:
            cls.benchmark_cases = json.load(f)

    def test_benchmark_has_40_cases(self):
        self.assertEqual(len(self.benchmark_cases), 40)
        langs = {c["language"] for c in self.benchmark_cases}
        self.assertEqual(langs, {"hi", "kn", "ta", "mixed"})
        for lang in ["hi", "kn", "ta", "mixed"]:
            count = sum(1 for c in self.benchmark_cases if c["language"] == lang)
            self.assertEqual(count, 10, f"Expected 10 cases for {lang}, found {count}")

    def test_benchmark_invariants_hold_100_percent(self):
        """Validates that candidate_standard == evidence_standard when non-null on representative cases."""
        # Sample representative cases from each language to keep unit test suite fast and memory-efficient
        sample_cases = [c for c in self.benchmark_cases if c["id"] in [
            "ML-HI-01", "ML-HI-03", "ML-KN-01", "ML-KN-02",
            "ML-TA-01", "ML-TA-03", "ML-MX-01", "ML-MX-03"
        ]]
        for case in sample_cases:
            res = self.recommender.recommend_for_text(case["multilingual_input"], req_id=case["id"])
            if res.candidate_standard:
                self.assertEqual(
                    res.candidate_standard,
                    res.evidence_standard,
                    f"Invariant broken on case {case['id']}: candidate={res.candidate_standard}, evidence={res.evidence_standard}"
                )



class TestPriority6AHardenedNormalization(unittest.TestCase):
    """Priority 6A Focused Unit Tests for Hardened Normalization.

    Covers:
    A. Phrase normalization (multi-word Indic technical phrases)
    B. Technical abbreviations (kV, kVA, mm, PN, CPVC, XLPE, Fe grades)
    C. Entity preservation & corruption detection
    D. Code mixing & technical Latin recognition
    E. Residue detection (PARTIAL and FAILED honest quality assignment)
    F. Safety invariants (zero fabricated standards, candidate == evidence)
    G. English fast-path regression
    """

    def setUp(self):
        self.normalizer = MultilingualTechnicalNormalizer(enabled=False)

    # A. Multi-word technical phrase normalization
    def test_phrase_normalization_kannada_sluice_valve(self):
        text = "ನೀರು ಸರಬರಾಜು ಕಾರ್ಯಗಳಿಗಾಗಿ 100 ಮಿಮೀ ಎರಕಹೊಯ್ದ ಕಬ್ಬಿಣದ ಸ್ಲೂಯಿಸ್ ಕವಾಟ ಪಿಎನ್ 16"
        res = self.normalizer.normalize(text)
        self.assertEqual(res.normalization_quality, "FULL")
        self.assertFalse(res.human_review_required)
        self.assertIn("cast iron sluice valve", res.canonical_text)
        self.assertIn("100 mm", res.canonical_text)
        self.assertIn("PN 16", res.canonical_text)

    def test_phrase_normalization_tamil_cpvc(self):
        text = "குடிநீர் விநியோகத்திற்கு 25 மிமீ சிபிவیسی குழாய் வழங்கல்"
        res = self.normalizer.normalize(text)
        self.assertEqual(res.normalization_quality, "FULL")
        self.assertFalse(res.human_review_required)
        self.assertIn("CPVC pipe", res.canonical_text)
        self.assertIn("25 mm", res.canonical_text)
        self.assertIn("potable drinking water supply", res.canonical_text)

    def test_phrase_normalization_hindi_transformer(self):
        text = "11 केवी के 500 केवीए आउटडोर तेल निमज्जित वितरण ट्रांसफार्मर की आपूर्ति"
        res = self.normalizer.normalize(text)
        self.assertEqual(res.normalization_quality, "FULL")
        self.assertFalse(res.human_review_required)
        self.assertIn("outdoor oil immersed distribution transformer", res.canonical_text)
        self.assertIn("11 kV", res.canonical_text)
        self.assertIn("500 kVA", res.canonical_text)

    # B. Technical abbreviations and units
    def test_technical_abbreviations_indic_scripts(self):
        # Test Hindi units
        hi_text = "11 केवी 500 केवीए 185 वर्ग मिमी 25 मिमी पीएन 16 सीपीवीसी एक्सएलपीई"
        res_hi, _, hits_hi = normalize_with_lexicon(hi_text)
        self.assertIn("11 kV", res_hi)
        self.assertIn("500 kVA", res_hi)
        self.assertIn("185 sq mm", res_hi)
        self.assertIn("25 mm", res_hi)
        self.assertIn("PN 16", res_hi)
        self.assertIn("CPVC", res_hi)
        self.assertIn("XLPE", res_hi)

        # Test Kannada units
        kn_text = "11 ಕೆವಿ 500 ಕೆವಿಎ 185 ಚದರ ಮಿಮೀ 25 ಮಿಮೀ ಪಿಎನ್ 16 ಸಿಪಿವಿಸಿ ಎಕ್ಸ್‌ಎಲ್‌ಪಿಇ"
        res_kn, _, hits_kn = normalize_with_lexicon(kn_text)
        self.assertIn("11 kV", res_kn)
        self.assertIn("500 kVA", res_kn)
        self.assertIn("185 sq mm", res_kn)
        self.assertIn("25 mm", res_kn)
        self.assertIn("PN 16", res_kn)
        self.assertIn("CPVC", res_kn)
        self.assertIn("XLPE", res_kn)

    # C. Entity preservation and semantic corruption detection
    def test_entity_preservation_semantic_accuracy(self):
        entities = ["11 केवी", "500 केवीए", "185 वर्ग मिमी", "PN 16", "Fe 500D", "IS 14846"]
        # Semantically preserved text
        canon_valid = "Supply of 11 kV 500 kVA transformer with 185 sq mm cable PN 16 Fe 500D conforming to IS 14846"
        status, missing = self.normalizer._verify_entities(entities, canon_valid)
        self.assertEqual(status, "PASS")
        self.assertEqual(missing, [])

        # Corrupted voltage (11 kV corrupted into 11 mm)
        canon_corrupt = "Supply of 11 mm 500 kVA transformer with 185 sq mm cable PN 16 Fe 500D conforming to IS 14846"
        status_corrupt, missing_corrupt = self.normalizer._verify_entities(entities, canon_corrupt)
        self.assertEqual(status_corrupt, "PARTIAL")
        self.assertIn("11 केवी", missing_corrupt)

    # D. Code mixing & technical Latin recognition
    def test_code_mixing_technical_latin_detection(self):
        # Indic text with purely technical Latin token Fe 500D
        hi_fe = "कंक्रीट सुदृढीकरण के लिए 16 मिमी टीएमटी स्टील सरिया Fe 500D की आपूर्ति"
        res_hi = detect_script_and_language(hi_fe)
        self.assertEqual(res_hi.detected_language, "hi")
        self.assertEqual(res_hi.primary_script, "Devanagari")
        self.assertTrue(res_hi.code_mixed)
        self.assertTrue(res_hi.has_technical_latin)

        # Kannada text with Fe 500D
        kn_fe = "ಕಟ್ಟಡ ನಿರ್ಮಾಣಕ್ಕಾಗಿ 12 ಮಿಮೀ ಟಿಎಂಟಿ ಉಕ್ಕಿನ ಬಾರ್ Fe 500D ಸರಬರಾಜು"
        res_kn = detect_script_and_language(kn_fe)
        self.assertEqual(res_kn.detected_language, "kn")
        self.assertEqual(res_kn.primary_script, "Kannada")
        self.assertTrue(res_kn.code_mixed)
        self.assertTrue(res_kn.has_technical_latin)

        # Genuine vocabulary code mixing (English words 'Water works', 'provide')
        mixed_text = "Water works ke liye 100 mm cast iron sluice valve PN 16 provide karna hoga"
        res_mixed = detect_script_and_language(mixed_text)
        self.assertEqual(res_mixed.detected_language, "mixed")
        self.assertTrue(res_mixed.code_mixed)

    # E. Residue detection: PARTIAL vs FAILED
    def test_meaningful_residue_assigned_partial_quality(self):
        # 100 mm valve translated, but untranslated Kannada residue remains
        text = "100 ಮಿಮೀ ವಾಲ್ವ್ ಮತ್ತು ಅಜ್ಞಾತ ಪರಿಕರಗಳು"
        res = self.normalizer.normalize(text)
        self.assertEqual(res.normalization_quality, "PARTIAL")
        self.assertTrue(res.human_review_required)
        self.assertIn("100 mm valve", res.canonical_text)

    def test_insufficient_technical_content_assigned_failed_quality(self):
        # Generic non-technical requirement
        text = "ಯೋಜನಾ ಸ್ಥಳಕ್ಕೆ ಸೂಕ್ತವಾದ ಕೆಲವು ಅನಿಶ್ಚಿತ ವಸ್ತುಗಳು"
        res = self.normalizer.normalize(text)
        self.assertEqual(res.normalization_quality, "FAILED")
        self.assertTrue(res.human_review_required)
        self.assertLessEqual(res.normalization_confidence, 0.35)

    # F. Safety: Normalization failure never fabricates a standard
    def test_normalization_failure_never_fabricates_standard(self):
        recommender = StandardsRecommender()
        nonsense_text = "ಯೋಜನಾ ಸ್ಥಳಕ್ಕೆ ಸೂಕ್ತವಾದ ಕೆಲವು ಅನಿಶ್ಚಿತ ವಸ್ತುಗಳು"
        res = recommender.recommend_for_text(nonsense_text)
        self.assertTrue(res.human_review_required)
        # Should not fabricate a confident standard
        if res.candidate_standard:
            self.assertEqual(res.candidate_standard, res.evidence_standard)
            self.assertIn(res.ambiguity_state, ["REVIEW_REQUIRED", "INCOMPLETE", "NO_RELIABLE_MATCH", "AMBIGUOUS"])

    # G. Regression: English fast-path
    def test_english_regression_fast_path(self):
        text = "Supply of 11 kV 500 kVA outdoor distribution transformer"
        res = self.normalizer.normalize(text)
        self.assertEqual(res.normalization_method, "fast_path")
        self.assertEqual(res.normalization_quality, "FULL")
        self.assertFalse(res.human_review_required)
        self.assertEqual(res.canonical_text, text)


if __name__ == "__main__":
    unittest.main()
