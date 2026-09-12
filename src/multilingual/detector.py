"""Script and Language Detection Module for TenderSaathi.

Identifies the script and language of tender requirements across:
- English (Latin)
- Hindi (Devanagari)
- Kannada (Kannada)
- Tamil (Tamil)
- Mixed Indic + English (code-mixed / bilingual)
- Transliterated Indic in Latin script (e.g., Hinglish)

Deterministic Unicode script analysis combined with procurement-specific
lexical heuristics. No external network or heavy dependencies required.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class DetectionResult:
    """Result of script/language detection."""
    detected_language: str          # 'en', 'hi', 'kn', 'ta', 'mixed', 'unknown', 'hi-Latn', etc.
    primary_script: str             # 'Latin', 'Devanagari', 'Kannada', 'Tamil', 'Mixed', 'Unknown'
    confidence: float               # 0.0 to 1.0
    detected_scripts: List[str] = field(default_factory=list)
    script_counts: Dict[str, int] = field(default_factory=dict)
    is_multilingual: bool = False   # True if Indic or code-mixed
    is_transliterated: bool = False # True if Latin script but Indic grammatical vocabulary
    human_review_required: bool = False
    code_mixed: bool = False        # True if both Indic and Latin elements are present
    has_technical_latin: bool = False # True if Latin tokens are purely technical specifications
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "detected_language": self.detected_language,
            "primary_script": self.primary_script,
            "confidence": round(self.confidence, 4),
            "detected_scripts": self.detected_scripts,
            "script_counts": self.script_counts,
            "is_multilingual": self.is_multilingual,
            "is_transliterated": self.is_transliterated,
            "human_review_required": self.human_review_required,
            "code_mixed": self.code_mixed,
            "has_technical_latin": self.has_technical_latin,
            "notes": self.notes,
        }


# Unicode block definitions for targeted Indian scripts and Latin
SCRIPT_RANGES: List[Tuple[str, int, int]] = [
    ("Devanagari", 0x0900, 0x097F),
    ("Kannada", 0x0C80, 0x0CFF),
    ("Tamil", 0x0B80, 0x0BFF),
    ("Latin", 0x0041, 0x005A),       # A-Z
    ("Latin", 0x0061, 0x007A),       # a-z
]

# Common procurement transliterated Indic function words (Latin script)
HINGLISH_MARKERS: Set[str] = {
    "karna", "karne", "chahiye", "hona", "hoga", "hogi", "ke", "ki", "ka", "ko",
    "liye", "aur", "tatha", "sahit", "lagana", "lagane", "dena", "dene", "bhi",
    "anusaar", "anusar", "pradan", "yukt", "yathavat",
}

KANGLISH_MARKERS: Set[str] = {
    "beku", "madabekagide", "irabeku", "madi", "matthu", "annu", "inda", "agi",
    "sarabaraju", "antaha", "yannu", "ittu",
}

TANGLISH_MARKERS: Set[str] = {
    "thevai", "vendam", "seiya", "vendum", "matrum", "udavudan", "poda", "aaga",
    "valanga", "seyya", "koodum",
}

# Controlled vocabulary of technical Latin words/acronyms that do NOT indicate language-mixing
TECHNICAL_LATIN_WORDS: Set[str] = {
    "fe", "d", "is", "part", "sec", "kv", "kva", "mva", "kw", "hp", "mm", "cm", "m",
    "inch", "sq", "sqmm", "pn", "cpvc", "upvc", "pvc", "hdpe", "gi", "xlpe", "tmt",
    "bar", "grade", "class", "sdr", "iso", "iec", "sp"
}


def _classify_char(ch: str) -> Optional[str]:
    """Classify a single character into a recognized script."""
    cp = ord(ch)
    if (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
        return "Latin"
    if 0x0900 <= cp <= 0x097F:
        return "Devanagari"
    if 0x0C80 <= cp <= 0x0CFF:
        return "Kannada"
    if 0x0B80 <= cp <= 0x0BFF:
        return "Tamil"
    return None


def detect_script_and_language(text: str) -> DetectionResult:
    """Performs script/language detection on procurement requirement text.

    Args:
        text: Raw input requirement string.

    Returns:
        DetectionResult containing language code, scripts, confidence, and flags.
    """
    if not text or not text.strip():
        return DetectionResult(
            detected_language="unknown",
            primary_script="Unknown",
            confidence=0.0,
            is_multilingual=False,
            human_review_required=True,
            notes=["Empty or blank input text"],
        )

    # Clean text and count scripts
    cleaned = unicodedata.normalize("NFKC", text)
    counts: Dict[str, int] = {"Latin": 0, "Devanagari": 0, "Kannada": 0, "Tamil": 0}
    other_alpha_count = 0

    for ch in cleaned:
        script = _classify_char(ch)
        if script:
            counts[script] += 1
        elif ch.isalpha():
            other_alpha_count += 1

    total_recognized = sum(counts.values())
    active_scripts = [s for s, c in counts.items() if c > 0]

    # Handle case with no alphabetic characters (e.g. only numbers/symbols)
    if total_recognized == 0:
        if other_alpha_count > 0:
            return DetectionResult(
                detected_language="unknown",
                primary_script="Other",
                confidence=0.3,
                is_multilingual=True,
                human_review_required=True,
                notes=["Unsupported script detected"],
            )
        return DetectionResult(
            detected_language="unknown",
            primary_script="Unknown",
            confidence=0.0,
            is_multilingual=False,
            human_review_required=True,
            notes=["No alphabetic characters in requirement"],
        )

    # Check for pure Latin (English vs Transliterated Indic)
    if counts["Latin"] == total_recognized:
        words = re.findall(r"\b[a-zA-Z]+\b", cleaned.lower())
        word_set = set(words)

        hinglish_hits = word_set & HINGLISH_MARKERS
        kanglish_hits = word_set & KANGLISH_MARKERS
        tanglish_hits = word_set & TANGLISH_MARKERS

        # Heuristic for transliterated Indic:
        # At least 2 grammatical markers or 1 strong multi-word combination
        if len(hinglish_hits) >= 2 or ("karna" in hinglish_hits or "chahiye" in hinglish_hits):
            return DetectionResult(
                detected_language="mixed",
                primary_script="Latin",
                confidence=0.85,
                detected_scripts=["Latin"],
                script_counts=counts,
                is_multilingual=True,
                is_transliterated=True,
                code_mixed=True,
                human_review_required=False,
                notes=[f"Transliterated Hindi (Hinglish) detected via tokens: {sorted(hinglish_hits)}"],
            )
        if len(kanglish_hits) >= 2 or ("sarabaraju" in kanglish_hits or "madabekagide" in kanglish_hits):
            return DetectionResult(
                detected_language="mixed",
                primary_script="Latin",
                confidence=0.85,
                detected_scripts=["Latin"],
                script_counts=counts,
                is_multilingual=True,
                is_transliterated=True,
                code_mixed=True,
                human_review_required=False,
                notes=[f"Transliterated Kannada (Kanglish) detected via tokens: {sorted(kanglish_hits)}"],
            )
        if len(tanglish_hits) >= 2 or ("thevai" in tanglish_hits or "vendum" in tanglish_hits):
            return DetectionResult(
                detected_language="mixed",
                primary_script="Latin",
                confidence=0.85,
                detected_scripts=["Latin"],
                script_counts=counts,
                is_multilingual=True,
                is_transliterated=True,
                code_mixed=True,
                human_review_required=False,
                notes=[f"Transliterated Tamil (Tanglish) detected via tokens: {sorted(tanglish_hits)}"],
            )

        # Standard English Fast Path
        conf = min(0.99, counts["Latin"] / (total_recognized + other_alpha_count))
        return DetectionResult(
            detected_language="en",
            primary_script="Latin",
            confidence=conf,
            detected_scripts=["Latin"],
            script_counts=counts,
            is_multilingual=False,
            is_transliterated=False,
            code_mixed=False,
            human_review_required=False,
            notes=["Standard English in Latin script"],
        )

    # Indic Scripts present
    indic_counts = {
        "Devanagari": counts["Devanagari"],
        "Kannada": counts["Kannada"],
        "Tamil": counts["Tamil"],
    }
    sorted_indic = sorted(indic_counts.items(), key=lambda x: x[1], reverse=True)
    top_script, top_count = sorted_indic[0]

    # Map script to primary language
    script_lang_map = {
        "Devanagari": "hi",
        "Kannada": "kn",
        "Tamil": "ta",
    }
    target_lang = script_lang_map.get(top_script, "unknown")
    latin_count = counts["Latin"]

    # When both Indic and Latin characters are present:
    if latin_count > 0 and top_count > 0:
        latin_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", cleaned)]
        non_tech_latin = [w for w in latin_words if w not in TECHNICAL_LATIN_WORDS]

        # If ALL Latin tokens are technical abbreviations (e.g. 'Fe 500D', '11 kV', 'CPVC', 'IS 14846')
        # Do NOT force detected_language to 'mixed'; preserve dominant Indic language identity
        if not non_tech_latin:
            conf = min(0.98, top_count / (top_count + other_alpha_count))
            return DetectionResult(
                detected_language=target_lang,
                primary_script=top_script,
                confidence=conf,
                detected_scripts=active_scripts,
                script_counts=counts,
                is_multilingual=True,
                is_transliterated=False,
                code_mixed=True,
                has_technical_latin=True,
                human_review_required=False,
                notes=[f"Single-script {top_script} requirement with technical Latin specifications ({sorted(set(latin_words))})"],
            )

        # Genuine vocabulary mixing (e.g. Indic sentence with general English words)
        conf = min(0.96, (top_count + latin_count) / (total_recognized + other_alpha_count))
        return DetectionResult(
            detected_language="mixed",
            primary_script=top_script,
            confidence=conf,
            detected_scripts=active_scripts,
            script_counts=counts,
            is_multilingual=True,
            is_transliterated=False,
            code_mixed=True,
            has_technical_latin=any(w in TECHNICAL_LATIN_WORDS for w in latin_words),
            human_review_required=False,
            notes=[f"Code-mixed requirement ({top_script} + Latin)", f"Underlying Indic language: {target_lang}"],
        )

    # Pure single Indic script
    conf = min(0.98, top_count / (total_recognized + other_alpha_count))
    return DetectionResult(
        detected_language=target_lang,
        primary_script=top_script,
        confidence=conf,
        detected_scripts=active_scripts,
        script_counts=counts,
        is_multilingual=True,
        is_transliterated=False,
        code_mixed=False,
        has_technical_latin=False,
        human_review_required=False,
        notes=[f"Single-script {top_script} requirement"],
    )
