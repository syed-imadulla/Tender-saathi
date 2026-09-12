"""api/ingestion/__init__.py — Document ingestion package for TenderSaathi."""

from .document_model import Document, PageResult, IngestionMetadata
from .ocr_service import (
    OCRService,
    TesseractOCREngine,
    OCRResult,
    OCRUnavailableError,
    OCRProcessingError,
    get_default_ocr_engine,
)
from .image_processor import ImageProcessor, ImageValidationError

__all__ = [
    "Document",
    "PageResult",
    "IngestionMetadata",
    "OCRService",
    "TesseractOCREngine",
    "OCRResult",
    "OCRUnavailableError",
    "OCRProcessingError",
    "ImageProcessor",
    "ImageValidationError",
    "get_default_ocr_engine",
]
