"""
src/corpus/__init__.py — Standards Corpus Ingestion Subsystem
"""

from src.corpus.manifest import (
    LicensingStatus,
    IngestionStatus,
    CorpusDocumentRecord,
    CorpusManifest,
)
from src.corpus.semantics import (
    VerificationState,
    can_transition,
    get_state_semantics,
)
from src.corpus.extractor import (
    ExtractedPage,
    ExtractedDocument,
    PDFExtractor,
)
from src.corpus.chunker import (
    ClausePassage,
    ClauseAwareChunker,
)
from src.corpus.storage import CorpusStorage
from src.corpus.retriever import ClauseRetriever

__all__ = [
    "LicensingStatus",
    "IngestionStatus",
    "CorpusDocumentRecord",
    "CorpusManifest",
    "VerificationState",
    "can_transition",
    "get_state_semantics",
    "ExtractedPage",
    "ExtractedDocument",
    "PDFExtractor",
    "ClausePassage",
    "ClauseAwareChunker",
    "CorpusStorage",
    "ClauseRetriever",
]
