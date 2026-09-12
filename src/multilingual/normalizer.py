"""Technical Normalization Module for Multilingual Procurement Requirements.

Converts multilingual Indic (Hindi, Kannada, Tamil, mixed, transliterated)
specifications into a canonical English technical representation.

ARCHITECTURAL & TRUST CONSTRAINTS:
1. Pure linguistic / technical terminology normalization ONLY.
2. The normalizer MUST NOT recommend standards, decide applicability,
   declare compliance, or alter evidence.
3. Fast-path bypass for English input (<0.5 ms latency overhead).
4. Critical entity protection: IS numbers, ratings, voltages, dimensions,
   and units are pre-extracted and verified post-normalization.
5. Missing or corrupted entities trigger decreased confidence and require
   human review — NEVER silently injected or falsified.
6. Offline deterministic fallback via procurement lexicon.
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

# Protected technical parameter regex patterns
ENTITY_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("is_standard", EXPLICIT_IS_REGEX),
    ("voltage", re.compile(r"\b\d+(?:\.\d+)?\s*(?:kV|KV|kv|V|volts|केवी|ಕೆವಿ|கேவி)\b", re.IGNORECASE)),
    ("power", re.compile(r"\b\d+(?:\.\d+)?\s*(?:kVA|kva|KVA|MVA|mva|kW|kw|KW|HP|hp|केवीए|ಕೆವಿಎ|கேவிஏ)\b", re.IGNORECASE)),
    ("dimension", re.compile(r"\b\d+(?:\.\d+)?\s*(?:sq\s*mm|sqmm|mm|cm|m|inch|inches|मिमी|ಮಿಮೀ|மிமீ)\b", re.IGNORECASE)),
    ("pressure", re.compile(r"\b(?:PN\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:bar|kg/cm2))\b", re.IGNORECASE)),
    ("grade_or_class", re.compile(r"\b(?:Grade\s*[A-Za-z0-9]+|Class\s*[A-Za-z0-9]+|SDR\s*\d+|Fe\s*\d+)\b", re.IGNORECASE)),
    ("percentage", re.compile(r"\b\d+(?:\.\d+)?\s*%\b")),
    ("numeric_spec", re.compile(r"\b\d+(?:\.\d+)?\b")),
]



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
                    entities.add(m.strip())
                elif isinstance(m, tuple):
                    entities.add(m[0].strip())
        return sorted(list(entities))

    def _verify_entities(self, original_entities: List[str], canonical_text: str) -> Tuple[str, List[str]]:
        """Verifies whether pre-extracted entities exist in the normalized canonical text.

        Returns:
            Tuple of (status, missing_entities).
            status is 'PASS', 'PARTIAL', 'FAIL', or 'N/A'.
        """
        if not original_entities:
            return "N/A", []

        missing = []
        canonical_lower = canonical_text.lower()
        canon_clean = re.sub(r"\s+", "", canonical_lower)

        for ent in original_entities:
            # 1. Explicit IS standard code
            if EXPLICIT_IS_REGEX.search(ent):
                ent_clean = re.sub(r"\s+", "", ent.lower())
                if ent_clean not in canon_clean:
                    missing.append(ent)
                continue

            # 2. Entities with numeric values (ratings, voltages, dimensions)
            digits = re.findall(r"\b\d+(?:\.\d+)?\b", ent)
            if digits:
                num_missing = False
                for d in digits:
                    if not re.search(r"(?<!\d)" + re.escape(d) + r"(?!\d)", canonical_text):
                        num_missing = True
                        break
                if num_missing:
                    missing.append(ent)
                continue

            # 3. Pure string entity
            ent_clean = re.sub(r"\s+", "", ent.lower())
            if ent_clean not in canon_clean:
                missing.append(ent)

        if not missing:
            return "PASS", []
        if len(missing) < len(original_entities):
            return "PARTIAL", missing
        return "FAIL", missing


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
                # Strip code fences if present
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
                            # Strip unverified IS citation from canonical text
                            candidate_canonical = re.sub(re.escape(cic), "", candidate_canonical).strip()

                    # Audit protected entities
                    status, missing = self._verify_entities(protected_entities, candidate_canonical)

                    # Calculate normalization confidence based on entity audit
                    norm_conf = 0.95
                    review_req = False
                    notes = ["Normalized via Groq LLM"]

                    if status == "PARTIAL":
                        norm_conf = 0.65
                        review_req = True
                        notes.append(f"Missing entities: {missing}")
                    elif status == "FAIL":
                        norm_conf = 0.35
                        review_req = True
                        notes.append(f"Failed entity preservation: {missing}")

                    return NormalizationResult(
                        original_text=clean_text,
                        canonical_text=candidate_canonical,
                        detected_language=detection.detected_language,
                        language_confidence=detection.confidence,
                        normalization_confidence=norm_conf,
                        entity_preservation_status=status,
                        is_multilingual=True,
                        is_translated=True,
                        human_review_required=review_req,
                        extracted_entities=protected_entities,
                        missing_entities=missing,
                        normalization_method="llm",
                        detection_details=detection.to_dict(),
                        notes=notes,
                    )
            except Exception:
                pass

        # 5. Deterministic Offline Lexicon Fallback
        lex_text, lex_conf, hit_count = normalize_with_lexicon(clean_text)
        if hit_count > 0:
            status, missing = self._verify_entities(protected_entities, lex_text)
            review_req = True  # Offline lexicon output always requires human review
            notes = [f"Normalized via offline lexicon ({hit_count} terms mapped)"]
            if missing:
                notes.append(f"Missing entities in lexicon fallback: {missing}")

            return NormalizationResult(
                original_text=clean_text,
                canonical_text=lex_text,
                detected_language=detection.detected_language,
                language_confidence=detection.confidence,
                normalization_confidence=lex_conf,
                entity_preservation_status=status,
                is_multilingual=True,
                is_translated=True,
                human_review_required=review_req,
                extracted_entities=protected_entities,
                missing_entities=missing,
                normalization_method="offline_lexicon",
                detection_details=detection.to_dict(),
                notes=notes,
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
            is_multilingual=True,
            is_translated=False,
            human_review_required=True,
            extracted_entities=protected_entities,
            missing_entities=[],
            normalization_method="untranslated",
            detection_details=detection.to_dict(),
            notes=["No terms matched in offline lexicon, untranslated fallback"],
        )
