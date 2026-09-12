"""
api/ingestion/ocr_service.py — Pluggable OCR service interface.

Architecture:
  OCRService (abstract base)
    └── TesseractOCREngine (concrete — Tesseract + pytesseract)

The engine is chosen at runtime.  If Tesseract is unavailable, the engine
raises OCRUnavailableError rather than silently failing or returning garbage.

Contract:
  - confidence is None when the engine cannot provide a reliable value.
    It is NEVER invented.
  - language is a BCP-47 tag or None.
  - text is the raw OCR output; downstream analysis normalises it.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Optional, Any, Dict

from .document_model import PageResult

logger = logging.getLogger("tendersaathi.ocr")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class OCRUnavailableError(RuntimeError):
    """Raised when the requested OCR engine binary or library is not installed."""


class OCRProcessingError(RuntimeError):
    """Raised when OCR fails on a specific image (e.g. corrupt data)."""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OCRResult:
    """
    Structured result from one OCR call.

    Fields
    ------
    text          Raw extracted text (may be empty string for blank pages).
    language      BCP-47 language code or None.
    confidence    Float in [0, 1] or None when unavailable.
    page          1-indexed page number.
    source_type   Always 'image' for images.
    ocr_used      Always True for OCR results.
    quality_flag  'HIGH' / 'MEDIUM' / 'LOW' based on confidence, or None.
    """

    text: str
    language: Optional[str]
    confidence: Optional[float]  # None = engine could not provide a reliable value
    page: int
    source_type: str = "image"
    ocr_used: bool = True
    quality_flag: Optional[str] = None

    def to_page_result(self) -> PageResult:
        """Convert to the normalized PageResult used by Document."""
        return PageResult(
            page_number=self.page,
            source_type=self.source_type,
            extracted_text=self.text,
            ocr_used=self.ocr_used,
            language=self.language,
            confidence=self.confidence,
            ocr_quality_flag=self.quality_flag,
        )

    @staticmethod
    def _quality_flag(confidence: Optional[float]) -> Optional[str]:
        if confidence is None:
            return None
        if confidence >= 0.80:
            return "HIGH"
        if confidence >= 0.50:
            return "MEDIUM"
        return "LOW"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class OCRService(abc.ABC):
    """Abstract OCR service.  Implement this to add a new OCR provider."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True when the engine's binary/API is reachable."""

    @abc.abstractmethod
    def process_image(
        self,
        image: Any,  # PIL.Image.Image
        page_number: int = 1,
        language_hint: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from a PIL image.

        Parameters
        ----------
        image         PIL.Image.Image
        page_number   1-indexed page number within the document.
        language_hint BCP-47 hint (e.g. 'eng', 'hin') or None.

        Returns
        -------
        OCRResult with text, language, confidence.

        Raises
        ------
        OCRUnavailableError  if the engine is not installed.
        OCRProcessingError   if the image cannot be processed.
        """


# ---------------------------------------------------------------------------
# Tesseract implementation
# ---------------------------------------------------------------------------

class TesseractOCREngine(OCRService):
    """
    OCR engine backed by Tesseract via pytesseract.

    Installation (not done automatically):
        sudo apt install tesseract-ocr tesseract-ocr-hin  # system binary
        pip install pytesseract                            # Python wrapper

    If the system binary is absent, every call raises OCRUnavailableError.
    """

    def __init__(self) -> None:
        self._pytesseract_available: Optional[bool] = None
        self._tesseract_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # Internal checks (lazy)
    # ------------------------------------------------------------------

    def _check_pytesseract(self) -> bool:
        if self._pytesseract_available is None:
            try:
                import pytesseract as _pt  # noqa: F401
                self._pytesseract_available = True
            except ImportError:
                self._pytesseract_available = False
                logger.warning(
                    "pytesseract not installed. "
                    "Run: pip install pytesseract"
                )
        return self._pytesseract_available

    def _check_tesseract_binary(self) -> bool:
        if self._tesseract_available is None:
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                self._tesseract_available = True
            except Exception:
                self._tesseract_available = False
                logger.warning(
                    "Tesseract binary not found. "
                    "Run: sudo apt install tesseract-ocr"
                )
        return self._tesseract_available

    def is_available(self) -> bool:
        return self._check_pytesseract() and self._check_tesseract_binary()

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def process_image(
        self,
        image: Any,
        page_number: int = 1,
        language_hint: Optional[str] = None,
    ) -> OCRResult:
        if not self._check_pytesseract():
            raise OCRUnavailableError(
                "pytesseract is not installed. "
                "Install it with: pip install pytesseract"
            )
        if not self._check_tesseract_binary():
            raise OCRUnavailableError(
                "Tesseract binary not found. "
                "Install it with: sudo apt install tesseract-ocr"
            )

        try:
            import pytesseract

            lang = language_hint or "eng+hin"  # default: English + Hindi

            # Get text
            text: str = pytesseract.image_to_string(image, lang=lang)

            # Attempt confidence (Tesseract outputs per-word data)
            confidence: Optional[float] = None
            try:
                import pandas as pd  # noqa: F401 — used below
                data = pytesseract.image_to_data(
                    image,
                    lang=lang,
                    output_type=pytesseract.Output.DICT,
                )
                confs = [
                    c for c in data.get("conf", [])
                    if isinstance(c, (int, float)) and c >= 0
                ]
                if confs:
                    confidence = round(sum(confs) / len(confs) / 100.0, 4)
            except Exception:
                confidence = None  # never invent a value

            # Detect language from Tesseract OSD when possible
            detected_lang: Optional[str] = None
            try:
                osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
                script = osd.get("script")
                if script:
                    detected_lang = script.lower()
            except Exception:
                detected_lang = language_hint

            quality_flag = OCRResult._quality_flag(confidence)

            logger.info(
                "OCR page %d: %d chars, confidence=%s, quality=%s",
                page_number,
                len(text),
                confidence,
                quality_flag,
            )

            return OCRResult(
                text=text.strip(),
                language=detected_lang,
                confidence=confidence,
                page=page_number,
                source_type="image",
                ocr_used=True,
                quality_flag=quality_flag,
            )

        except (OCRUnavailableError, OCRProcessingError):
            raise
        except Exception as exc:
            logger.error("Tesseract OCR failed on page %d: %s", page_number, exc)
            raise OCRProcessingError(f"OCR processing failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Default engine (singleton)
# ---------------------------------------------------------------------------

_default_engine: Optional[TesseractOCREngine] = None


def get_default_ocr_engine() -> TesseractOCREngine:
    """Return the shared TesseractOCREngine instance (created once)."""
    global _default_engine
    if _default_engine is None:
        _default_engine = TesseractOCREngine()
    return _default_engine
