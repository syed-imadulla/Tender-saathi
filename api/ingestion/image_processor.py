"""
api/ingestion/image_processor.py — Image validation and OCR orchestration.

Validates uploaded images, converts them to a form suitable for OCR,
calls the OCRService, and returns normalized PageResult objects.

Security:
  - Input files are validated before any processing.
  - PIL.Image.verify() or open() is used to detect corrupt files.
  - No uploaded content is executed.
  - Temp files are not created; images are processed in-memory.
"""

from __future__ import annotations

import io
import logging
from typing import List, Optional, Tuple

from .document_model import Document, PageResult
from .ocr_service import OCRService, OCRResult, OCRUnavailableError, OCRProcessingError, get_default_ocr_engine

logger = logging.getLogger("tendersaathi.image_processor")

# ---------------------------------------------------------------------------
# Limits (tunable)
# ---------------------------------------------------------------------------

MAX_IMAGE_BYTES = 10 * 1024 * 1024          # 10 MB per image
MAX_IMAGE_DIMENSION = 8000                   # pixels per side
MAX_IMAGES_PER_REQUEST = 5
SUPPORTED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ImageValidationError(ValueError):
    """Raised when an uploaded image fails validation."""


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------

class ImageProcessor:
    """
    Validates and processes image uploads for OCR.

    Usage::

        processor = ImageProcessor()
        document = processor.process_images([(image_bytes, "scan.png")], ...)
    """

    def __init__(self, ocr_engine: Optional[OCRService] = None) -> None:
        self._ocr = ocr_engine or get_default_ocr_engine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_image_bytes(
        self,
        data: bytes,
        filename: str,
        *,
        max_bytes: int = MAX_IMAGE_BYTES,
        max_dimension: int = MAX_IMAGE_DIMENSION,
    ) -> None:
        """
        Validate raw image bytes.

        Raises ImageValidationError with a user-readable message on failure.
        """
        from PIL import Image, UnidentifiedImageError

        # 1. Size check
        if len(data) > max_bytes:
            mb = max_bytes // (1024 * 1024)
            raise ImageValidationError(
                f"File too large: '{filename}'. Maximum image size is {mb} MB."
            )

        # 2. Extension check (defence-in-depth; MIME check follows)
        ext = ("." + filename.rsplit(".", 1)[-1]).lower() if "." in filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            raise ImageValidationError(
                f"Unsupported file type: '{filename}'. "
                f"Accepted formats: PNG, JPG, WEBP."
            )

        # 3. MIME / format check via PIL (not just extension)
        try:
            img = Image.open(io.BytesIO(data))
            fmt = (img.format or "").lower()
            if fmt not in {"png", "jpeg", "webp"}:
                raise ImageValidationError(
                    f"Unrecognised image format in '{filename}'. "
                    f"Accepted formats: PNG, JPG, WEBP."
                )
        except (ImageValidationError, UnidentifiedImageError):
            raise ImageValidationError(
                f"File '{filename}' could not be read as an image. "
                f"It may be corrupt or an unsupported format."
            )
        except Exception as e:
            raise ImageValidationError(
                f"Could not verify image '{filename}': {e}"
            )

        # 4. Dimension check
        try:
            img = Image.open(io.BytesIO(data))
            w, h = img.size
            if w > max_dimension or h > max_dimension:
                raise ImageValidationError(
                    f"Image '{filename}' is too large ({w}×{h} px). "
                    f"Maximum dimension is {max_dimension} px per side."
                )
        except ImageValidationError:
            raise
        except Exception as e:
            raise ImageValidationError(
                f"Could not read image dimensions for '{filename}': {e}"
            )

    def process_images(
        self,
        images: List[Tuple[bytes, str]],   # (file_bytes, filename)
        source_name: str = "images",
        language_hint: Optional[str] = None,
    ) -> Document:
        """
        Validate, OCR, and package a list of images into a Document.

        Parameters
        ----------
        images       List of (file_bytes, filename) tuples, in order.
        source_name  Human-readable document name for the report.
        language_hint  Optional BCP-47 hint for OCR (e.g. 'eng', 'hin').

        Returns
        -------
        Document with one PageResult per image.  If OCR is unavailable,
        returns a Document whose pages contain empty text and
        ocr_quality_flag='UNAVAILABLE'.

        Raises
        ------
        ImageValidationError  if any image fails validation.
        """
        from PIL import Image

        if not images:
            raise ImageValidationError("No images provided.")
        if len(images) > MAX_IMAGES_PER_REQUEST:
            raise ImageValidationError(
                f"Too many files: {len(images)}. "
                f"Maximum is {MAX_IMAGES_PER_REQUEST} images per request."
            )

        # Validate all first (fail fast)
        for data, fname in images:
            self.validate_image_bytes(data, fname)

        ocr_available = self._ocr.is_available()
        if not ocr_available:
            logger.warning(
                "OCR engine unavailable. Images will produce empty text. "
                "Install tesseract-ocr to enable OCR."
            )

        pages: List[PageResult] = []
        total_bytes = sum(len(d) for d, _ in images)

        for idx, (data, fname) in enumerate(images, start=1):
            pil_img = Image.open(io.BytesIO(data)).convert("RGB")

            if not ocr_available:
                # Return a page with empty text and a quality flag indicating unavailability
                pages.append(PageResult(
                    page_number=idx,
                    source_type="image",
                    extracted_text="",
                    ocr_used=False,
                    language=None,
                    confidence=None,
                    ocr_quality_flag="UNAVAILABLE",
                    raw_metadata={"filename": fname, "ocr_error": "OCR engine not installed"},
                ))
                continue

            try:
                result: OCRResult = self._ocr.process_image(
                    pil_img,
                    page_number=idx,
                    language_hint=language_hint,
                )
                page = result.to_page_result()
                page.raw_metadata["filename"] = fname
                pages.append(page)

            except OCRUnavailableError as exc:
                logger.warning("OCR unavailable for page %d: %s", idx, exc)
                pages.append(PageResult(
                    page_number=idx,
                    source_type="image",
                    extracted_text="",
                    ocr_used=False,
                    language=None,
                    confidence=None,
                    ocr_quality_flag="UNAVAILABLE",
                    raw_metadata={"filename": fname, "ocr_error": str(exc)},
                ))

            except OCRProcessingError as exc:
                logger.error("OCR processing error on page %d (%s): %s", idx, fname, exc)
                pages.append(PageResult(
                    page_number=idx,
                    source_type="image",
                    extracted_text="",
                    ocr_used=True,
                    language=None,
                    confidence=None,
                    ocr_quality_flag="FAILED",
                    raw_metadata={"filename": fname, "ocr_error": str(exc)},
                ))

        return Document.from_pages(
            pages=pages,
            source_name=source_name,
            source_type="multi_image" if len(pages) > 1 else "image",
            file_size_bytes=total_bytes,
        )
