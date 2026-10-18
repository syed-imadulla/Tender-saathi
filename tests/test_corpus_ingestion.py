"""
tests/test_corpus_ingestion.py — Comprehensive Offline Tests for Standards Corpus Ingestion Subsystem

Tests:
1. Valid text-based PDF extraction and clause grounding
2. Scanned / low-density PDF detection (triggers OCR_REQUIRED)
3. Empty (0-byte) and corrupt header files
4. Duplicate file hash rejection in manifest
5. Multi-edition standards isolation under identical standard numbers
6. Clause-boundary detection and explicit CLAUSE_UNKNOWN tagging
7. Strict page-number preservation
8. Table structure detection and extraction warnings
9. High replacement character ratio (triggers QUALITY_FAILED)
10. Stable chunk IDs and deterministic canonical SHA-256 hashing
11. Cross-edition chunk isolation during retrieval
12. Manifest provenance and licensing status validation
13. Anti-falsification boundary enforcement (no false official authentication or human adjudication)
14. Backward compatibility with catalogue-only recommendations
15. 7-tier verification state machine semantics and transition validation
"""

import os
import tempfile
import pytest
import pymupdf as fitz

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
    PDFExtractor,
    ExtractedDocument,
)
from src.corpus.chunker import (
    ClauseAwareChunker,
    ClausePassage,
)
from src.corpus.storage import CorpusStorage
from src.corpus.retriever import ClauseRetriever
from src.traceability import (
    TraceableEvidenceValidator,
    TraceableEvidenceRecord,
    EvidenceCompletenessState,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def create_sample_text_pdf(path: str, title: str = "IS 1180 (Part 1) : 2014") -> str:
    """Helper: creates a well-structured synthetic PDF for testing."""
    doc = fitz.open()
    # Page 1: Foreword & Scope
    page1 = doc.new_page()
    page1.insert_text((50, 72), f"{title}\nIndian Standard\nOUTDOOR DISTRIBUTION TRANSFORMERS")
    page1.insert_text((50, 130), "Foreword\nThis standard was adopted by the Bureau of Indian Standards.")
    page1.insert_text((50, 200), "1 Scope\nThis standard specifies requirements for mineral oil immersed distribution transformers.")
    
    # Page 2: Clause 4.2 and Table 1
    page2 = doc.new_page()
    page2.insert_text((50, 72), "4.2 Maximum Permissible Losses\nThe total losses at 50 percent and 100 percent load shall not exceed the values in Table 1.")
    page2.insert_text((50, 150), "Table 1 Maximum Losses at Rated Frequency\nRating (kVA) | Max Losses at 50% (W) | Max Losses at 100% (W)\n100 | 475 | 1650\n200 | 780 | 2300")
    page2.insert_text((50, 250), "Clause 5.1 Temperature Rise Limit\nThe temperature-rise shall not exceed 35 deg C for top oil.")

    doc.save(path)
    doc.close()
    return path


def test_1_valid_text_pdf_extraction(temp_dir):
    pdf_path = os.path.join(temp_dir, "is1180_2014.pdf")
    create_sample_text_pdf(pdf_path)

    extractor = PDFExtractor()
    doc = extractor.extract(pdf_path, doc_id="DOC-IS-1180-2014")

    assert doc.ingestion_status == IngestionStatus.EXTRACTED.value
    assert doc.page_count == 2
    assert doc.total_characters > 200
    assert doc.empty_page_count == 0
    assert doc.replacement_char_ratio == 0.0
    assert len(doc.pages) == 2
    assert "OUTDOOR DISTRIBUTION TRANSFORMERS" in doc.pages[0].text
    assert "Maximum Permissible Losses" in doc.pages[1].text


def test_2_scanned_or_empty_pdf_detection(temp_dir):
    # Create empty page PDF
    pdf_path = os.path.join(temp_dir, "scanned_doc.pdf")
    doc = fitz.open()
    doc.new_page()  # 1 blank page
    doc.save(pdf_path)
    doc.close()

    extractor = PDFExtractor(min_char_density=50)
    res = extractor.extract(pdf_path, doc_id="DOC-SCANNED")

    assert res.ingestion_status == IngestionStatus.OCR_REQUIRED.value
    assert "OCR required" in res.failure_reasons[0]


def test_3_empty_and_corrupt_files(temp_dir):
    empty_path = os.path.join(temp_dir, "zero_bytes.pdf")
    with open(empty_path, "wb") as f:
        pass  # 0 bytes

    corrupt_path = os.path.join(temp_dir, "corrupt.pdf")
    with open(corrupt_path, "wb") as f:
        f.write(b"NOT A VALID PDF HEADER STREAM")

    extractor = PDFExtractor()
    
    # 0 bytes
    res_empty = extractor.extract(empty_path, doc_id="DOC-EMPTY")
    assert res_empty.ingestion_status == IngestionStatus.FAILED.value
    assert "0 bytes" in res_empty.failure_reasons[0]

    # Corrupt
    res_corrupt = extractor.extract(corrupt_path, doc_id="DOC-CORRUPT")
    assert res_corrupt.ingestion_status == IngestionStatus.CORRUPT.value
    assert "Invalid PDF header" in res_corrupt.failure_reasons[0]


def test_4_duplicate_file_hash_rejection(temp_dir):
    manifest_path = os.path.join(temp_dir, "manifest.json")
    manifest = CorpusManifest(manifest_path=manifest_path)

    rec1 = CorpusDocumentRecord(
        doc_id="DOC-1",
        standard_number="IS 1180",
        file_sha256="aabbccddeeff11223344",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value
    )
    ok1, err1 = manifest.register_document(rec1)
    assert ok1 is True
    assert err1 is None

    # Different doc_id, identical file hash
    rec2 = CorpusDocumentRecord(
        doc_id="DOC-2",
        standard_number="IS 1180",
        file_sha256="aabbccddeeff11223344",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value
    )
    ok2, err2 = manifest.register_document(rec2)
    assert ok2 is False
    assert "Duplicate file hash" in err2


def test_5_multi_edition_standards_segregation(temp_dir):
    manifest_path = os.path.join(temp_dir, "manifest.json")
    manifest = CorpusManifest(manifest_path=manifest_path)

    # 1989 edition
    rec_1989 = CorpusDocumentRecord(
        doc_id="DOC-IS-1180-1989",
        standard_number="IS 1180 (Part 1)",
        edition_year=1989,
        file_sha256="hash_1989",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value
    )
    manifest.register_document(rec_1989)

    # 2014 edition
    rec_2014 = CorpusDocumentRecord(
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        file_sha256="hash_2014",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value
    )
    manifest.register_document(rec_2014)

    docs_all = manifest.get_documents_by_standard("IS 1180 (Part 1)")
    assert len(docs_all) == 2

    docs_2014 = manifest.get_documents_by_standard("IS 1180 (Part 1)", edition_year=2014)
    assert len(docs_2014) == 1
    assert docs_2014[0].doc_id == "DOC-IS-1180-2014"


def test_6_clause_boundary_detection_and_unknown_clauses(temp_dir):
    pdf_path = os.path.join(temp_dir, "clauses.pdf")
    create_sample_text_pdf(pdf_path)

    extractor = PDFExtractor()
    extracted = extractor.extract(pdf_path, doc_id="DOC-CLAUSES")

    rec = CorpusDocumentRecord(
        doc_id="DOC-CLAUSES",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        file_sha256=extracted.file_sha256
    )

    chunker = ClauseAwareChunker()
    passages = chunker.chunk_document(extracted, rec)

    clause_ids = [p.clause_identifier for p in passages]
    assert "Foreword" in clause_ids
    assert "1" in clause_ids
    assert "4.2" in clause_ids
    assert "Table 1" in clause_ids
    assert "5.1" in clause_ids

    # Unidentified clause on header
    assert any(p.clause_identifier == "CLAUSE_UNKNOWN" for p in passages)

    # Ensure no semantic inference took place
    for p in passages:
        if p.clause_identifier != "CLAUSE_UNKNOWN":
            assert any(p.clause_identifier in line for line in p.passage_text.split("\n"))


def test_7_page_number_preservation(temp_dir):
    pdf_path = os.path.join(temp_dir, "pages.pdf")
    create_sample_text_pdf(pdf_path)

    extractor = PDFExtractor()
    extracted = extractor.extract(pdf_path, doc_id="DOC-PAGES")

    rec = CorpusDocumentRecord(
        doc_id="DOC-PAGES",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        file_sha256=extracted.file_sha256
    )

    chunker = ClauseAwareChunker()
    passages = chunker.chunk_document(extracted, rec)

    for p in passages:
        assert p.page_start == p.page_end  # Passages never cross page boundaries
        assert p.page_start in (1, 2)


def test_8_table_extraction_warnings(temp_dir):
    pdf_path = os.path.join(temp_dir, "table_doc.pdf")
    create_sample_text_pdf(pdf_path)

    extractor = PDFExtractor()
    extracted = extractor.extract(pdf_path, doc_id="DOC-TABLE")

    assert len(extracted.table_warnings) > 0
    assert any("Table structure detected" in w for w in extracted.table_warnings)
    assert extracted.pages[1].has_table is True


def test_9_low_quality_replacement_characters(temp_dir):
    pdf_path = os.path.join(temp_dir, "bad_encoding.pdf")
    doc = fitz.open()
    page = doc.new_page()
    # Insert high concentration of replacement characters
    bad_text = "Standard \ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd specification requirements"
    page.insert_text((50, 72), bad_text)
    doc.save(pdf_path)
    doc.close()

    extractor = PDFExtractor(min_char_density=10)
    res = extractor.extract(pdf_path, doc_id="DOC-BAD-ENC")

    assert res.ingestion_status == IngestionStatus.QUALITY_FAILED.value
    assert "replacement character ratio" in res.failure_reasons[0]


def test_10_stable_chunk_ids_and_canonical_hashes(temp_dir):
    pdf_path = os.path.join(temp_dir, "stable_hash.pdf")
    create_sample_text_pdf(pdf_path)

    extractor = PDFExtractor()
    extracted = extractor.extract(pdf_path, doc_id="DOC-HASH")

    rec = CorpusDocumentRecord(
        doc_id="DOC-HASH",
        standard_number="IS 1180",
        edition_year=2014,
        file_sha256=extracted.file_sha256
    )

    chunker = ClauseAwareChunker()
    passages_run1 = chunker.chunk_document(extracted, rec)
    passages_run2 = chunker.chunk_document(extracted, rec)

    assert len(passages_run1) == len(passages_run2)
    for p1, p2 in zip(passages_run1, passages_run2):
        assert p1.passage_id == p2.passage_id
        assert p1.content_hash == p2.content_hash
        assert len(p1.content_hash) == 64


def test_11_cross_edition_chunk_isolation(temp_dir):
    db_path = os.path.join(temp_dir, "corpus.db")
    storage = CorpusStorage(db_path=db_path)

    # 1989 passage
    p_1989 = ClausePassage(
        passage_id="DOC-1989_p1_c4_2_0",
        doc_id="DOC-1989",
        standard_number="IS 1180",
        edition_year=1989,
        source_file_sha256="hash_89",
        page_start=1,
        page_end=1,
        clause_identifier="4.2",
        passage_text="Losses for 1989 edition: total loss 650 W",
        content_hash=ClauseAwareChunker.canonical_hash("Losses for 1989 edition: total loss 650 W"),
        verification_state=VerificationState.CLAUSE_IDENTIFIER_VERIFIED.value,
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )

    # 2014 passage
    p_2014 = ClausePassage(
        passage_id="DOC-2014_p1_c4_2_0",
        doc_id="DOC-2014",
        standard_number="IS 1180",
        edition_year=2014,
        source_file_sha256="hash_14",
        page_start=1,
        page_end=1,
        clause_identifier="4.2",
        passage_text="Losses for 2014 edition: total loss 475 W",
        content_hash=ClauseAwareChunker.canonical_hash("Losses for 2014 edition: total loss 475 W"),
        verification_state=VerificationState.CLAUSE_IDENTIFIER_VERIFIED.value,
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )

    storage.store_document(CorpusDocumentRecord(
        doc_id="DOC-1989",
        standard_number="IS 1180",
        edition_year=1989,
        file_sha256="hash_89",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value
    ))
    storage.store_document(CorpusDocumentRecord(
        doc_id="DOC-2014",
        standard_number="IS 1180",
        edition_year=2014,
        file_sha256="hash_14",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value
    ))

    storage.store_passages([p_1989, p_2014])

    retriever = ClauseRetriever(storage=storage)
    
    # Query with 2014 edition restriction
    res_2014 = retriever.get_clause(standard_number="IS 1180", clause_identifier="4.2", edition_year=2014)
    assert res_2014 is not None
    assert "475 W" in res_2014.passage_text

    # Query with 1989 edition restriction
    res_1989 = retriever.get_clause(standard_number="IS 1180", clause_identifier="4.2", edition_year=1989)
    assert res_1989 is not None
    assert "650 W" in res_1989.passage_text


def test_12_missing_source_provenance_and_licensing(temp_dir):
    manifest_path = os.path.join(temp_dir, "manifest.json")
    manifest = CorpusManifest(manifest_path=manifest_path)

    # Unrecorded licensing status defaults cleanly to UNKNOWN
    rec = CorpusDocumentRecord(
        doc_id="DOC-TEST-LIC",
        standard_number="IS 732",
        file_sha256="dummy_hash_lic",
        licensing_status="INVALID_LICENSE"
    )
    ok, err = manifest.register_document(rec)
    assert ok is True
    assert manifest.get_document("DOC-TEST-LIC").licensing_status == LicensingStatus.UNKNOWN.value


def test_13_anti_falsification_guard(temp_dir):
    # Ensure neither parser run nor hash match grants official authentication or human adjudication
    db_path = os.path.join(temp_dir, "corpus.db")
    storage = CorpusStorage(db_path=db_path)

    passage = ClausePassage(
        passage_id="DOC-IS-1180_p2_c4_2_0",
        doc_id="DOC-IS-1180",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_official_pdf",
        page_start=2,
        page_end=2,
        clause_identifier="4.2",
        passage_text="The total losses at 50 percent load shall not exceed 475 W.",
        content_hash=ClauseAwareChunker.canonical_hash("The total losses at 50 percent load shall not exceed 475 W."),
        verification_state=VerificationState.CLAUSE_IDENTIFIER_VERIFIED.value,
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_document(CorpusDocumentRecord(
        doc_id="DOC-IS-1180",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        file_sha256="sha256_official_pdf",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value
    ))
    storage.store_passages([passage])

    validator = TraceableEvidenceValidator(corpus_storage=storage)

    # Synthetic recommendation with matching clause passage
    class MockRec:
        standard_number = "IS 1180 (Part 1)"
        title = "Outdoor Type Oil Immersed Distribution Transformers"
        status = "ACTIVE"
        evidence = "The total losses at 50 percent load shall not exceed 475 W."
        structured_evidence = {
            "bis_scope_evidence": "The total losses at 50 percent load shall not exceed 475 W.",
            "scope_status": "VERIFIED"
        }
        human_review_required = False
        relevance_score = 0.95

    # Note: IS 1180 (Part 1) exists in the local SQLite catalogue data/standards/standards.db
    record = validator.build_trace_record(
        requirement_id="REQ-1",
        requirement_text="100 kVA distribution transformer with max 475W loss at 50% load",
        recommendation=MockRec(),
        critic_decision="RECOMMEND"
    )

    # Guaranteed non-falsification assertions:
    assert record.is_normative_clause_verified is True
    assert record.is_official_source_authenticated is False  # MUST remain False: Offline SQLite storage is not live statutory portal
    assert record.is_human_verified is False                 # MUST remain False: Machine extraction is not human adjudication


def test_14_backward_compatibility_catalogue_only():
    # Calling validator without corpus_storage preserves exact Phase 17 behavior
    validator = TraceableEvidenceValidator(corpus_storage=None)

    class MockRec:
        standard_number = "IS 1180 (Part 1)"
        title = "Outdoor Type Oil Immersed Distribution Transformers"
        status = "ACTIVE"
        evidence = "This standard specifies requirements for mineral oil immersed distribution transformers."
        structured_evidence = {
            "bis_scope_evidence": "This standard specifies requirements for mineral oil immersed distribution transformers.",
            "scope_status": "VERIFIED"
        }
        human_review_required = False

    record = validator.build_trace_record(
        requirement_id="REQ-OLD",
        requirement_text="Oil immersed distribution transformer",
        recommendation=MockRec(),
        critic_decision="RECOMMEND"
    )

    assert record.is_catalogue_verified is True
    assert record.is_local_catalogue_verified is True
    assert record.is_normative_clause_verified is False  # Safely remains False without corpus storage
    assert record.is_official_source_authenticated is False
    assert record.is_human_verified is False


def test_15_verification_state_transitions():
    # Valid progressive sequence
    assert can_transition(VerificationState.DOCUMENT_SOURCE_RECORDED, VerificationState.PDF_TEXT_EXTRACTED) is True
    assert can_transition(VerificationState.PDF_TEXT_EXTRACTED, VerificationState.EXTRACTION_QUALITY_CHECKED) is True
    assert can_transition(VerificationState.EXTRACTION_QUALITY_CHECKED, VerificationState.PASSAGE_MATCHES_STORED_DOCUMENT) is True
    assert can_transition(VerificationState.PASSAGE_MATCHES_STORED_DOCUMENT, VerificationState.CLAUSE_IDENTIFIER_VERIFIED) is True
    assert can_transition(VerificationState.CLAUSE_IDENTIFIER_VERIFIED, VerificationState.ENGINEERING_APPLICABILITY_REVIEWED) is True
    assert can_transition(VerificationState.ENGINEERING_APPLICABILITY_REVIEWED, VerificationState.HUMAN_EXPERT_ADJUDICATED) is True

    # Illegal jumps / skipping steps
    assert can_transition(VerificationState.DOCUMENT_SOURCE_RECORDED, VerificationState.HUMAN_EXPERT_ADJUDICATED) is False
    assert can_transition(VerificationState.PDF_TEXT_EXTRACTED, VerificationState.CLAUSE_IDENTIFIER_VERIFIED) is False
    assert can_transition(VerificationState.DOCUMENT_SOURCE_RECORDED, VerificationState.PASSAGE_MATCHES_STORED_DOCUMENT) is False

    # Descriptions ensure semantic boundaries
    desc = get_state_semantics(VerificationState.HUMAN_EXPERT_ADJUDICATED)
    assert "NEVER be set automatically" in desc["does_not_mean"]
