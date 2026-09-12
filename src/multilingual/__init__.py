"""Multilingual Preprocessing Layer for TenderSaathi.

Enables Indian-language (Hindi, Kannada, Tamil, mixed, transliterated)
procurement requirements to seamlessly run through the existing standards engine.
"""

from src.multilingual.detector import DetectionResult, detect_script_and_language
from src.multilingual.lexicon import normalize_with_lexicon
from src.multilingual.normalizer import (
    MultilingualTechnicalNormalizer,
    NormalizationResult,
)

__all__ = [
    "detect_script_and_language",
    "DetectionResult",
    "normalize_with_lexicon",
    "MultilingualTechnicalNormalizer",
    "NormalizationResult",
]
