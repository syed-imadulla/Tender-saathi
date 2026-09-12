"""Technical Normalization Module for Multilingual Procurement Requirements.

Converts multilingual Indic (Hindi, Kannada, Tamil, mixed, transliterated)
specifications into a canonical English technical representation.

ARCHITECTURAL & TRUST CONSTRAINTS:
1. Pure linguistic / technical terminology normalization ONLY.
2. The normalizer MUST NOT recommend standards, decide applicability,
   declare compliance, or alter evidence.
3. Fast-path bypass for English input (<0.5 ms latency overhead).
4. Critical entity protection: IS numbers, ratings, voltages, dimensions,
   pressure, grades, and units are pre-extracted and verified post-normalization.
5. Missing or corrupted entities trigger decreased confidence and require
   human review — NEVER silently injected or falsified.
6. Honest Normalization Quality:
   - FULL: Required entities preserved, 0 Indic residue, identifiable product.
   - PARTIAL: Meaningful Indic residue or incomplete mappings -> human review.
   - FAILED: Insufficient technical product content or corrupt entities -> review/abstain.
7. Offline deterministic fallback via procurement lexicon with lookaround boundaries.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k not in os.environ:
                    os.environ[k] = v.strip()


from src.multilingual.detector import DetectionResult, detect_script_and_language
from src.multilingual.lexicon import normalize_with_lexicon


# Regex pattern to match explicit IS numbers
EXPLICIT_IS_REGEX = re.compile(
    r"\b(?:IS|IS/ISO|IS/IEC|SP)\s*(?:/|\s*)?\d+(?:\s*(?:Part|Sec)\s*\d+)*(?:\s*\(Part\s*\d+\))?(?:\s*:\s*\d{4})?",
    re.IGNORECASE,
)

# Protected technical parameter regex patterns using Unicode-aware lookarounds
ENTITY_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("is_standard", EXPLICIT_IS_REGEX),
    ("power", re.compile(r"(?<![a-zA-Z0-9\u0900-\u0D7F])\d+(?:\.\d+)?\s*(?:kVA|kva|KVA|MVA|mva|kW|kw|KW|HP|hp|केवीए|ಕೆವಿಎ|கேவிஏ)(?![a-zA-Z0-9\u0900-\u0D7F])", re.IGNORECASE)),
    ("voltage", re.compile(r"(?<![a-zA-Z0-9\u0900-\u0D7F])\d+(?:\.\d+)?\s*(?:kV|KV|kv|V|volts|केवी|ಕೆವಿ|கேவி)(?![a-zA-Z0-9\u0900-\u0D7F])", re.IGNORECASE)),
    ("dimension_area", re.compile(r"(?<![a-zA-Z0-9\u0900-\u0D7F])\d+(?:\.\d+)?\s*(?:sq\s*mm|sqmm|वर्ग\s*मिमी|स्क्वायर\s*एमएम|ಚದರ\s*ಮಿಮೀ|ವರ್ಗ\s*ಮಿಮೀ|சதுர\s*மிமீ)(?![a-zA-Z0-9\u0900-\u0D7F])", re.IGNORECASE)),
    ("dimension_linear", re.compile(r"(?<![a-zA-Z0-9\u0900-\u0D7F])\d+(?:\.\d+)?\s*(?:mm|cm|m|meter|ಮೀಟರ್|मीटर|மீட்டர்|inch|inches|मिमी|ಮಿಮೀ|மிமீ)(?![a-zA-Z0-9\u0900-\u0D7F])", re.IGNORECASE)),
    ("pressure", re.compile(r"(?<![a-zA-Z0-9\u0900-\u0D7F])(?:PN\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:bar|kg/cm2|पார்|ಬಾರ್|बार))(?![a-zA-Z0-9\u0900-\u0D7F])", re.IGNORECASE)),
    ("grade_or_class", re.compile(r"\b(?:Grade\s*[A-Za-z0-9]+|Class\s*[A-Za-z0-9]+|SDR\s*\d+|Fe\s*\d+[A-Za-z]?)\b", re.IGNORECASE)),
    ("percentage", re.compile(r"\b\d+(?:\.\d+)?\s*%\b")),
    ("numeric_spec", re.compile(r"(?<![a-zA-Z0-9])\d+(?:\.\d+)?(?![a-zA-Z0-9])")),
]

# Recognized engineering product terms for validation
KNOWN_PRODUCT_KEYWORDS: Set[str] = {
    "transformer", "cable", "conductor", "pipe", "valve", "pump", "pumpset",
    "switchgear", "breaker", "motor", "cement", "steel", "bar", "rebar", "wire",
    "wiring", "drainage", "sewerage", "fitting", "flange", "gasket", "insulator",
    "pvc", "cpvc", "xlpe", "hdpe", "upvc", "iron", "galvanized", "sluice",
}


@dataclass
class NormalizationResult:
    """Outcome of technical normalization."""
    original_text: str
    canonical_text: str
    detected_language: str
    language_confidence: float
    normalization_confidence: float
    entity_preservation_status: str     # 'PASS', 'PARTIAL', 'FAIL', 'N/A'
    is_multilingual: bool
    is_translated: bool
    human_review_required: bool
    extracted_entities: List[str] = field(default_factory=list)
    missing_entities: List[str] = field(default_factory=list)
    normalization_method: str = "fast_path"  # 'fast_path', 'llm', 'offline_lexicon', 'untranslated'
    normalization_quality: str = "FULL"      # 'FULL', 'PARTIAL', 'FAILED'
    detection_details: Optional[Dict[str, Any]] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "canonical_text": self.canonical_text,
            "detected_language": self.detected_language,
            "language_confidence": round(self.language_confidence, 4),
            "normalization_confidence": round(self.normalization_confidence, 4),
            "entity_preservation_status": self.entity_preservation_status,
            "normalization_quality": self.normalization_quality,
            "is_multilingual": self.is_multilingual,
            "is_translated": self.is_translated,
            "human_review_required": self.human_review_required,
            "extracted_entities": self.extracted_entities,
            "missing_entities": self.missing_entities,
            "normalization_method": self.normalization_method,
            "notes": self.notes,
        }


LLM_NORMALIZATION_PROMPT = """You are a multilingual technical procurement assistant for Indian government tenders.
Your task is to translate and normalize the following requirement into a clear, concise, canonical English technical specification.

REQUIREMENT:
"{text}"

RULES:
1. Translate Hindi, Kannada, Tamil, or code-mixed terms into standard English technical terminology (e.g. 'वितरण ट्रांसफार्मर' -> 'distribution transformer', 'ಸಿಪಿವಿಸಿ ಪೈಪ್' -> 'CPVC pipe').
2. PRESERVE EXACTLY all numerical values, ratings, units, dimensions, voltages, capacities, and explicit standards (e.g. 11 kV, 500 kVA, 25 mm, IS 1180). DO NOT alter numbers.
3. DO NOT recommend, invent, or add any Indian Standard (IS) numbers that are NOT present in the input text.
4. DO NOT make any compliance, legal, or eligibility claims.
5. Return ONLY a JSON object with this exact structure:
{{
  "canonical_text": "Canonical technical English specification",
  "notes": "Brief note on terminology mapped"
}}
"""


class MultilingualTechnicalNormalizer:
    """Normalizes multilingual tender requirements into canonical technical English."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 8.0,
    ):
        env_enabled = os.getenv("TENDERSAATHI_LLM_ENABLED", "false").lower() in ("true", "1", "yes")
        self.enabled = env_enabled if enabled is None else enabled
        self.provider = (provider or os.getenv("TENDERSAATHI_LLM_PROVIDER", "groq")).lower()
        self.model = model or os.getenv("TENDERSAATHI_LLM_MODEL", "openai/gpt-oss-120b")
        self.timeout = timeout

        if api_key is not None:
            self._api_key = api_key.strip()
        elif self.provider == "groq":
            self._api_key = os.getenv("GROQ_API_KEY", "").strip()
        elif self.provider == "openrouter":
            self._api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        else:
            self._api_key = os.getenv("LLM_API_KEY", "").strip()

    def extract_protected_entities(self, text: str) -> List[str]:
        """Extracts technical entities (standards, ratings, dimensions) that must be preserved."""
        entities: Set[str] = set()
        for _, pattern in ENTITY_PATTERNS:
            matches = pattern.findall(text)
            for m in matches:
                if isinstance(m, str):
                    m_str = m.strip()
                    if m_str:
                        entities.add(m_str)
                elif isinstance(m, tuple):
                    for item in m:
                        if item.strip():
                            entities.add(item.strip())
        # Sort by length descending for deterministic validation order
        return sorted(list(entities), key=len, reverse=True)

    def _verify_entities(
        self,
        original_entities: List[str],
        canonical_text: str,
    ) -> Tuple[str, List[str]]:
        """Verifies semantic preservation of protected entities in canonical text.

        Checks both numerical value preservation and semantic unit preservation
        (e.g., ensuring a 11 kV voltage wasn't corrupted into 11 mm dimension).
        """
        if not original_entities:
            return "N/A", []

        missing: List[str] = []
        canonical_lower = canonical_text.lower()

        for ent in original_entities:
            ent_lower = ent.lower()

            # 1. Power (Check before voltage because kVA contains kV)
            if re.search(r"(?<![a-zA-Z0-9\u0900-\u0D7F])(?:kva|kw|hp|mva|केवीए|ಕೆವಿಎ|கேவிஏ)(?![a-zA-Z0-9\u0900-\u0D7F])", ent_lower):
                m = re.search(r"\d+(?:\.\d+)?", ent_lower)
                if m:
                    val = m.group(0)
                    if not (re.search(r"(?<!\d)" + val + r"(?!\d)", canonical_text) and re.search(r"\b(?:kva|kw|hp|mva)\b", canonical_lower)):
                        missing.append(ent)
                continue

            # 2. Voltage
            if re.search(r"(?<![a-zA-Z0-9\u0900-\u0D7F])(?:kv|केवी|ಕೆವಿ|கேவி)(?![a-zA-Z0-9\u0900-\u0D7F])", ent_lower):
                m = re.search(r"\d+(?:\.\d+)?", ent_lower)
                if m:
                    val = m.group(0)
                    if not (re.search(r"(?<!\d)" + val + r"(?!\d)", canonical_text) and re.search(r"\bkv\b", canonical_lower)):
                        missing.append(ent)
                continue

            # 3. Dimension sq mm (Check before mm)
            if re.search(r"(?:sq\s*mm|वर्ग\s*मिमी|ಸ್ಕ್ವೇರ್\s*ಎಂಎಂ|ಚದರ\s*ಮಿಮೀ|ವರ್ಗ\s*ಮಿಮೀ|சதுர\s*மிமீ)", ent_lower):
                m = re.search(r"\d+(?:\.\d+)?", ent_lower)
                if m:
                    val = m.group(0)
                    if not (re.search(r"(?<!\d)" + val + r"(?!\d)", canonical_text) and re.search(r"\b(?:sq\s*mm|sqmm)\b", canonical_lower)):
                        missing.append(ent)
                continue

            # 4. Linear Dimension mm / inch / m
            if re.search(r"(?<![a-zA-Z0-9\u0900-\u0D7F])(?:mm|मिमी|ಮಿಮೀ|மிமீ)(?![a-zA-Z0-9\u0900-\u0D7F])", ent_lower):
                m = re.search(r"\d+(?:\.\d+)?", ent_lower)
                if m:
                    val = m.group(0)
                    if not (re.search(r"(?<!\d)" + val + r"(?!\d)", canonical_text) and re.search(r"\bmm\b", canonical_lower)):
                        missing.append(ent)
                continue

            # 5. Pressure PN / bar
            if re.search(r"(?:pn|bar|பார்|ಬಾರ್|बार)", ent_lower):
                m = re.search(r"\d+(?:\.\d+)?", ent_lower)
                if m:
                    val = m.group(0)
                    if not (re.search(r"(?<!\d)" + val + r"(?!\d)", canonical_text) and re.search(r"\b(?:pn|bar)\b", canonical_lower)):
                        missing.append(ent)
                continue

            # 6. Fe steel grade (e.g. Fe 500D)
            if "fe" in ent_lower:
                m = re.search(r"\d+[a-z]?", ent_lower)
                if m:
                    val = m.group(0)
                    if not (re.search(r"(?<![a-z0-9])" + val + r"(?![a-z0-9])", canonical_lower) and "fe" in canonical_lower):
                        missing.append(ent)
                continue

            # 7. Explicit IS standard code
            if re.search(r"\b(?:is|sp)\b", ent_lower):
                m = re.search(r"\d{3,5}", ent_lower)
                if m:
                    val = m.group(0)
                    if not re.search(r"(?<!\d)" + val + r"(?!\d)", canonical_text):
                        missing.append(ent)
                continue

            # 8. Plain numeric values
            m = re.search(r"\d+(?:\.\d+)?", ent_lower)
            if m:
                val = m.group(0)
                if not re.search(r"(?<!\d)" + val + r"(?!\d)", canonical_text):
                    missing.append(ent)
                continue

            # 9. Generic textual token fallback
            ent_clean = re.sub(r"\s+", "", ent_lower)
            canon_clean = re.sub(r"\s+", "", canonical_lower)
            if ent_clean not in canon_clean:
                missing.append(ent)

        if not missing:
            return "PASS", []
        if len(missing) < len(original_entities):
            return "PARTIAL", missing
        return "FAIL", missing

    def _evaluate_normalization_quality(
        self,
        original_text: str,
        canonical_text: str,
        protected_entities: List[str],
        entity_status: str,
        method: str,
        raw_conf: float,
    ) -> Tuple[str, bool, float, List[str]]:
        """Evaluates honest FULL / PARTIAL / FAILED normalization quality.

        Quality criteria:
        - FULL: All entities preserved, zero Indic residue, primary product identifiable.
        - PARTIAL: Meaningful Indic residue remains or incomplete mappings -> human review.
        - FAILED: Corrupted entities or insufficient technical product -> review / abstain.
        """
        notes: List[str] = []

        # Count remaining Indic script characters
        indic_chars = [ch for ch in canonical_text if 0x0900 <= ord(ch) <= 0x0D7F and ch.isalpha()]
        total_alpha = [ch for ch in canonical_text if ch.isalpha()]

        # Check for identifiable engineering product keywords
        canon_words = set(re.findall(r"\b[a-zA-Z]+\b", canonical_text.lower()))
        has_product = bool(canon_words & KNOWN_PRODUCT_KEYWORDS)

        # 1. Critical Entity Failure
        if entity_status == "FAIL":
            notes.append("Critical technical parameters failed preservation")
            return "FAILED", True, min(0.35, raw_conf), notes

        # 2. Meaningful Indic Residue
        if len(indic_chars) > 0:
            residue_ratio = len(indic_chars) / max(1, len(total_alpha))
            notes.append(f"Meaningful Indic residue detected ({len(indic_chars)} chars remaining)")
            if residue_ratio > 0.60 and not has_product:
                notes.append("Overwhelming untranslated residue without identifiable product")
                return "FAILED", True, 0.20, notes
            final_conf = max(0.35, min(0.70, 0.75 - (0.50 * residue_ratio)))
            return "PARTIAL", True, final_conf, notes

        # 3. Product Identifiability
        if not has_product and len(protected_entities) == 0:
            notes.append("No identifiable engineering product or technical parameters found in specification")
            return "FAILED", True, 0.20, notes

        # 4. Partial Entity Preservation
        if entity_status == "PARTIAL":
            notes.append("Some technical entities were not preserved in canonical representation")
            return "PARTIAL", True, min(0.65, raw_conf), notes

        # 5. Clean Canonical Representation (FULL)
        notes.append("Complete technical canonical representation achieved (zero residue, entities preserved)")
        review_required = False if method in ("fast_path", "llm", "offline_lexicon") else True
        final_conf = max(0.85, raw_conf) if method in ("llm", "offline_lexicon") else raw_conf
        return "FULL", review_required, final_conf, notes

    def _call_llm(self, text: str) -> Optional[str]:
        """Invokes Groq/LLM for technical translation and normalization."""
        if not self.enabled or not self._api_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a specialized multilingual technical procurement normalizer. Return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": LLM_NORMALIZATION_PROMPT.format(text=text),
                },
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TenderSaathi-Multilingual/1.0",
        }

        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                res_obj = json.loads(body)
                return res_obj["choices"][0]["message"]["content"]
        except Exception:
            return None

    def normalize(self, text: str) -> NormalizationResult:
        """Main entry point: Detects language, protects entities, normalizes, and audits outcome."""
        clean_text = text.strip() if text else ""
        if not clean_text:
            return NormalizationResult(
                original_text=text,
                canonical_text="",
                detected_language="unknown",
                language_confidence=0.0,
                normalization_confidence=0.0,
                entity_preservation_status="N/A",
                normalization_quality="FAILED",
                is_multilingual=False,
                is_translated=False,
                human_review_required=True,
                notes=["Empty requirement text"],
            )

        # 1. Script and Language Detection
        detection = detect_script_and_language(clean_text)

        # 2. English Fast Path (<0.5 ms overhead)
        if detection.detected_language == "en" and not detection.is_transliterated:
            return NormalizationResult(
                original_text=clean_text,
                canonical_text=clean_text,
                detected_language="en",
                language_confidence=detection.confidence,
                normalization_confidence=1.0,
                entity_preservation_status="N/A",
                normalization_quality="FULL",
                is_multilingual=False,
                is_translated=False,
                human_review_required=False,
                normalization_method="fast_path",
                detection_details=detection.to_dict(),
                notes=["English fast path: bypassed translation"],
            )

        # 3. Multilingual or Transliterated: Pre-extract protected entities
        protected_entities = self.extract_protected_entities(clean_text)

        # 4. Try LLM Normalization if enabled
        llm_raw = self._call_llm(clean_text)
        if llm_raw:
            try:
                clean_raw = llm_raw.strip()
                if clean_raw.startswith("```"):
                    clean_raw = re.sub(r"^```(?:json)?\s*", "", clean_raw)
                    clean_raw = re.sub(r"\s*```$", "", clean_raw)
                parsed = json.loads(clean_raw)
                candidate_canonical = parsed.get("canonical_text", "").strip()

                if candidate_canonical:
                    # Strip any fabricated IS citations not present in original text
                    orig_is_codes = set(re.findall(EXPLICIT_IS_REGEX, clean_text))
                    cand_is_codes = re.findall(EXPLICIT_IS_REGEX, candidate_canonical)
                    for cic in cand_is_codes:
                        if cic not in orig_is_codes:
                            candidate_canonical = re.sub(re.escape(cic), "", candidate_canonical).strip()

                    # Audit protected entities and evaluate honest quality
                    status, missing = self._verify_entities(protected_entities, candidate_canonical)
                    quality, review_req, norm_conf, qual_notes = self._evaluate_normalization_quality(
                        clean_text, candidate_canonical, protected_entities, status, "llm", 0.95
                    )

                    all_notes = ["Normalized via LLM"] + qual_notes
                    if missing:
                        all_notes.append(f"Missing entities: {missing}")

                    return NormalizationResult(
                        original_text=clean_text,
                        canonical_text=candidate_canonical,
                        detected_language=detection.detected_language,
                        language_confidence=detection.confidence,
                        normalization_confidence=norm_conf,
                        entity_preservation_status=status,
                        normalization_quality=quality,
                        is_multilingual=True,
                        is_translated=True,
                        human_review_required=review_req,
                        extracted_entities=protected_entities,
                        missing_entities=missing,
                        normalization_method="llm",
                        detection_details=detection.to_dict(),
                        notes=all_notes,
                    )
            except Exception:
                pass

        # 5. Deterministic Offline Lexicon Fallback (with details)
        lex_text, lex_conf, hit_count, lex_details = normalize_with_lexicon(clean_text, return_details=True)
        if hit_count > 0:
            status, missing = self._verify_entities(protected_entities, lex_text)
            quality, review_req, final_conf, qual_notes = self._evaluate_normalization_quality(
                clean_text, lex_text, protected_entities, status, "offline_lexicon", lex_conf
            )

            all_notes = [f"Normalized via offline lexicon ({hit_count} terms mapped)"] + qual_notes
            if missing:
                all_notes.append(f"Missing entities in lexicon fallback: {missing}")

            return NormalizationResult(
                original_text=clean_text,
                canonical_text=lex_text,
                detected_language=detection.detected_language,
                language_confidence=detection.confidence,
                normalization_confidence=final_conf,
                entity_preservation_status=status,
                normalization_quality=quality,
                is_multilingual=True,
                is_translated=True,
                human_review_required=review_req,
                extracted_entities=protected_entities,
                missing_entities=missing,
                normalization_method="offline_lexicon",
                detection_details=detection.to_dict(),
                notes=all_notes,
            )

        # 6. Untranslated Fallback: Lexicon had 0 hits
        status, missing = self._verify_entities(protected_entities, clean_text)
        return NormalizationResult(
            original_text=clean_text,
            canonical_text=clean_text,
            detected_language=detection.detected_language,
            language_confidence=detection.confidence,
            normalization_confidence=0.20,
            entity_preservation_status=status,
            normalization_quality="FAILED",
            is_multilingual=True,
            is_translated=False,
            human_review_required=True,
            extracted_entities=protected_entities,
            missing_entities=[],
            normalization_method="untranslated",
            detection_details=detection.to_dict(),
            notes=["No terms matched in offline lexicon, untranslated fallback; quality set to FAILED"],
        )
