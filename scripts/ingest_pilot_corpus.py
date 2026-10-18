"""
scripts/ingest_pilot_corpus.py — Controlled Pilot Corpus Ingestion Runner

CLI runner for ingesting a pilot corpus of technical standards PDFs into
the versioned manifest and clause-aware SQLite database. Enforces provenance,
licensing tracking, quality checks, and deterministic offline execution.
"""

from __future__ import annotations

import os
import sys
import argparse
from typing import Dict, Any, List

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.corpus.manifest import (
    LicensingStatus,
    IngestionStatus,
    CorpusDocumentRecord,
    CorpusManifest,
)
from src.corpus.extractor import PDFExtractor
from src.corpus.chunker import ClauseAwareChunker
from src.corpus.storage import CorpusStorage


def ingest_document(
    file_path: str,
    doc_id: str,
    standard_number: str,
    edition_year: int | None = None,
    document_title: str = "",
    source_url: str | None = None,
    source_citation: str | None = None,
    licensing_status: str = LicensingStatus.UNKNOWN.value,
    usage_restrictions: str = "",
    manifest_path: str = "data/standards/corpus_manifest.json",
    db_path: str = "data/standards/corpus.db",
) -> Dict[str, Any]:
    """Ingests a single PDF standards document end-to-end."""
    extractor = PDFExtractor()
    chunker = ClauseAwareChunker()
    manifest = CorpusManifest(manifest_path=manifest_path)
    storage = CorpusStorage(db_path=db_path)

    # 1. Extraction & Quality Check
    extracted_doc = extractor.extract(file_path, doc_id=doc_id)

    # 2. Manifest Registration Record
    doc_record = CorpusDocumentRecord(
        doc_id=doc_id,
        standard_number=standard_number,
        edition_year=edition_year,
        document_title=document_title,
        source_url=source_url,
        source_citation=source_citation,
        file_sha256=extracted_doc.file_sha256,
        file_size_bytes=extracted_doc.file_size_bytes,
        licensing_status=licensing_status,
        usage_restrictions=usage_restrictions,
        extraction_method=extracted_doc.extraction_method,
        ingestion_status=extracted_doc.ingestion_status,
        failure_reasons=extracted_doc.failure_reasons,
        page_count=extracted_doc.page_count,
        table_warnings=extracted_doc.table_warnings,
    )

    reg_ok, reg_err = manifest.register_document(doc_record)
    if not reg_ok:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": f"Manifest registration rejected: {reg_err}",
            "ingestion_status": IngestionStatus.FAILED.value
        }

    # 3. Store in SQLite Database
    storage.store_document(doc_record, extracted_doc=extracted_doc)

    # 4. Chunk into Clause Passages if extraction succeeded
    passages = []
    if extracted_doc.ingestion_status == IngestionStatus.EXTRACTED.value:
        passages = chunker.chunk_document(extracted_doc, doc_record)
        storage.store_passages(passages)

    return {
        "success": True,
        "doc_id": doc_id,
        "standard_number": standard_number,
        "edition_year": edition_year,
        "ingestion_status": extracted_doc.ingestion_status,
        "pages_extracted": extracted_doc.page_count,
        "passages_created": len(passages),
        "table_warnings": len(extracted_doc.table_warnings),
        "failure_reasons": extracted_doc.failure_reasons
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest controlled standards pilot corpus")
    parser.add_argument("--pdf", type=str, help="Path to standards PDF file")
    parser.add_argument("--doc-id", type=str, help="Internal document ID (e.g. DOC-IS-1180-2014)")
    parser.add_argument("--standard", type=str, help="Standard number (e.g. 'IS 1180 (Part 1)')")
    parser.add_argument("--year", type=int, default=None, help="Edition year")
    parser.add_argument("--title", type=str, default="", help="Standard title")
    parser.add_argument("--citation", type=str, default=None, help="Documentary citation / gazette reference")
    parser.add_argument("--url", type=str, default=None, help="Source URL (http/https)")
    parser.add_argument("--license", type=str, default=LicensingStatus.UNKNOWN.value, help="Licensing status")
    parser.add_argument("--stats", action="store_true", help="Print corpus summary statistics")

    args = parser.parse_args()

    storage = CorpusStorage()
    if args.stats:
        stats = storage.get_corpus_statistics()
        print("\n--- Corpus Audit Statistics ---")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    if not args.pdf or not args.doc_id or not args.standard:
        print("Error: --pdf, --doc-id, and --standard are required for document ingestion.")
        sys.exit(1)

    result = ingest_document(
        file_path=args.pdf,
        doc_id=args.doc_id,
        standard_number=args.standard,
        edition_year=args.year,
        document_title=args.title,
        source_url=args.url,
        source_citation=args.citation,
        licensing_status=args.license
    )

    print("\n--- Ingestion Result ---")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
