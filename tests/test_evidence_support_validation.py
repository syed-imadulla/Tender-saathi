"""
tests/test_evidence_support_validation.py — Phase 21 Independent Adversarial Validation Matrix

Implements the 18-case deterministic offline test matrix auditing:
1. Correct clause identifier but irrelevant technical subject -> UNSUPPORTED
2. Matching subject but unsupported operating conditions -> CONFLICTING
3. Exact numeric match -> FULLY_SUPPORTED
4. Conflicting numeric rating -> CONFLICTING
5. Equivalent units (kW vs W) with valid conversion -> properly evaluated without false conflict
6. Inequality-direction mismatch ("at least" vs "at most") -> CONFLICTING
7. Tolerance and range mismatch -> PARTIALLY_SUPPORTED
8. Negation and exclusions ("without X" vs "shall include X") -> CONFLICTING
9. Indoor vs outdoor conditions -> CONFLICTING
10. Compound requirement with 1 supported component and 1 unsupported component -> PARTIALLY_SUPPORTED
11. Conflicting evidence across two passages -> CONFLICTING
12. Correct clause number in the wrong edition -> CORPUS_DOCUMENT_NOT_ELIGIBLE & UNVERIFIED_COVERAGE
13. Missing or unverified extraction-quality metadata -> rejected in TraceableEvidenceValidator
14. OCR-required or quality-failed source -> ineligible
15. Missing corpus storage and database lookup failures -> UNVERIFIED_COVERAGE
16. Tampered document or passage hashes -> invalidated in validator
17. Clause identifiers differing superficially (4.2 vs 4.20) -> strictly distinguished
18. Requirements whose technical parameters cannot be parsed safely -> EXPERT_REVIEW_REQUIRED / conservative fallback
"""

import os
import tempfile
import pytest

from src.corpus.manifest import LicensingStatus, IngestionStatus, CorpusDocumentRecord
from src.corpus.chunker import ClauseAwareChunker, ClausePassage
from src.corpus.storage import CorpusStorage
from src.corpus.retriever import ClauseRetriever, ClauseEvidenceOutcome
from src.corpus.semantics import RequirementEvidenceSupportState
from src.traceability import TraceableEvidenceValidator, TraceableEvidenceRecord


@pytest.fixture
def matrix_env():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "corpus_matrix.db")
        storage = CorpusStorage(db_path=db_path)
        yield d, db_path, storage


def populate_matrix_corpus(storage: CorpusStorage):
    """Populates synthetic documents and passages for the 18 matrix cases."""
    doc_transformer = CorpusDocumentRecord(
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        document_title="Outdoor Distribution Transformers",
        source_citation="Synthetic Standard 2014",
        source_url="https://standardsbis.bsbedge.com",
        file_sha256="sha256_is1180_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_document(doc_transformer)

    passages = [
        # Cl 4.2: Max permissible losses in Watts
        ClausePassage(
            passage_id="DOC-IS-1180-2014_p2_c4_2_0",
            doc_id="DOC-IS-1180-2014",
            standard_number="IS 1180 (Part 1)",
            edition_year=2014,
            source_file_sha256="sha256_is1180_file",
            page_start=2,
            page_end=2,
            clause_identifier="4.2",
            passage_text="4.2 Maximum Permissible Losses\nTotal losses at 50% load shall not exceed 500 W for 100 kVA rating.",
            content_hash=ClauseAwareChunker.canonical_hash("4.2 Maximum Permissible Losses Total losses at 50% load shall not exceed 500 W for 100 kVA rating."),
            verification_state="CLAUSE_IDENTIFIER_VERIFIED",
            extraction_quality_status=IngestionStatus.EXTRACTED.value
        ),
        # Cl 4.20: Supervisory and auxiliary wiring (to test superficial discrimination against 4.2)
        ClausePassage(
            passage_id="DOC-IS-1180-2014_p20_c4_20_0",
            doc_id="DOC-IS-1180-2014",
            standard_number="IS 1180 (Part 1)",
            edition_year=2014,
            source_file_sha256="sha256_is1180_file",
            page_start=20,
            page_end=20,
            clause_identifier="4.20",
            passage_text="4.20 Auxiliary Wiring\nControl marshalling box wiring shall have copper conductor.",
            content_hash=ClauseAwareChunker.canonical_hash("4.20 Auxiliary Wiring Control marshalling box wiring shall have copper conductor."),
            verification_state="CLAUSE_IDENTIFIER_VERIFIED",
            extraction_quality_status=IngestionStatus.EXTRACTED.value
        ),
        # Cl 5.1: Tolerance passage
        ClausePassage(
            passage_id="DOC-IS-1180-2014_p5_c5_1_0",
            doc_id="DOC-IS-1180-2014",
            standard_number="IS 1180 (Part 1)",
            edition_year=2014,
            source_file_sha256="sha256_is1180_file",
            page_start=5,
            page_end=5,
            clause_identifier="5.1",
            passage_text="5.1 Measurement Tolerance\nLoss measurement tolerance shall be within 5 percent.",
            content_hash=ClauseAwareChunker.canonical_hash("5.1 Measurement Tolerance Loss measurement tolerance shall be within 5 percent."),
            verification_state="CLAUSE_IDENTIFIER_VERIFIED",
            extraction_quality_status=IngestionStatus.EXTRACTED.value
        ),
        # Cl 6.1: Indoor dry-type operating condition
        ClausePassage(
            passage_id="DOC-IS-1180-2014_p6_c6_1_0",
            doc_id="DOC-IS-1180-2014",
            standard_number="IS 1180 (Part 1)",
            edition_year=2014,
            source_file_sha256="sha256_is1180_file",
            page_start=6,
            page_end=6,
            clause_identifier="6.1",
            passage_text="6.1 Operating Envelope\nApparatus designed strictly for indoor dry-type installation only.",
            content_hash=ClauseAwareChunker.canonical_hash("6.1 Operating Envelope Apparatus designed strictly for indoor dry-type installation only."),
            verification_state="CLAUSE_IDENTIFIER_VERIFIED",
            extraction_quality_status=IngestionStatus.EXTRACTED.value
        ),
        # Cl 7.1: Negation passage (Requires conservator tank)
        ClausePassage(
            passage_id="DOC-IS-1180-2014_p7_c7_1_0",
            doc_id="DOC-IS-1180-2014",
            standard_number="IS 1180 (Part 1)",
            edition_year=2014,
            source_file_sha256="sha256_is1180_file",
            page_start=7,
            page_end=7,
            clause_identifier="7.1",
            passage_text="7.1 Conservator Tank\nAll transformers shall have conservator tank with silica gel breather.",
            content_hash=ClauseAwareChunker.canonical_hash("7.1 Conservator Tank All transformers shall have conservator tank with silica gel breather."),
            verification_state="CLAUSE_IDENTIFIER_VERIFIED",
            extraction_quality_status=IngestionStatus.EXTRACTED.value
        ),
        # Cl 8.1: Conflicting secondary passage for lexical search conflict test
        ClausePassage(
            passage_id="DOC-IS-1180-2014_p8_c8_1_0",
            doc_id="DOC-IS-1180-2014",
            standard_number="IS 1180 (Part 1)",
            edition_year=2014,
            source_file_sha256="sha256_is1180_file",
            page_start=8,
            page_end=8,
            clause_identifier="8.1",
            passage_text="8.1 Alternative Cooling\nTransformer oil cooling apparatus strictly for indoor use only.",
            content_hash=ClauseAwareChunker.canonical_hash("8.1 Alternative Cooling Transformer oil cooling apparatus strictly for indoor use only."),
            verification_state="CLAUSE_IDENTIFIER_VERIFIED",
            extraction_quality_status=IngestionStatus.EXTRACTED.value
        )
    ]
    storage.store_passages(passages)


# Case 1: Correct clause ID but irrelevant technical subject -> UNSUPPORTED
def test_case_01_correct_clause_irrelevant_subject(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Clause 4.20 is about auxiliary wiring, query asks for foundation concrete
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.20",
        requirement_text="Reinforced cement concrete foundation raft for transformer pad."
    )
    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNSUPPORTED.value


# Case 2: Matching subject but unsupported operating conditions -> CONFLICTING
def test_case_02_unsupported_operating_conditions(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="6.1",
        requirement_text="Outdoor pole-mounted distribution transformer."
    )
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.CONFLICTING.value


# Case 3: Exact numeric match -> FULLY_SUPPORTED
def test_case_03_exact_numeric_match(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Total losses at 50% load shall not exceed 500 W for 100 kVA rating."
    )
    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.FULLY_SUPPORTED.value


# Case 4: Conflicting numeric rating -> CONFLICTING
def test_case_04_conflicting_numeric_rating(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender permits 600 W losses, but standard caps max permissible at 500 W
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Total losses at 50% load shall not exceed 600 W for 100 kVA rating."
    )
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.CONFLICTING.value


# Case 5: Equivalent units (0.5 kW vs 500 W) -> converted without false conflict
def test_case_05_equivalent_units_conversion(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender specifies 0.5 kW (= 500 W). Standard specifies 500 W. Should match!
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Total losses at 50% load shall not exceed 0.5 kW for 100 kVA rating."
    )
    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.FULLY_SUPPORTED.value


# Case 6: Inequality direction mismatch ("at least" vs ceiling)
def test_case_06_inequality_direction_mismatch(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender demands "at least 600 W", but standard mandates "shall not exceed 500 W"
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Apparatus shall be at least 600 W rating."
    )
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.CONFLICTING.value


# Case 7: Tolerance mismatch -> PARTIALLY_SUPPORTED
def test_case_07_tolerance_mismatch(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender requires tighter +/- 2% tolerance, standard specifies +/- 5%
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="5.1",
        requirement_text="Loss measurement tolerance within 2 percent."
    )
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value


# Case 8: Negation / Exclusion ("without conservator" vs mandatory conservator) -> CONFLICTING
def test_case_08_negation_exclusion_conflict(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender demands hermetically sealed transformer without conservator tank
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="7.1",
        requirement_text="Hermetically sealed transformer without conservator tank."
    )
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.CONFLICTING.value


# Case 9: Indoor vs outdoor conditions -> CONFLICTING
def test_case_09_indoor_outdoor_operating_conflict(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="6.1",
        requirement_text="Outdoor yard installation."
    )
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.CONFLICTING.value


# Case 10: Compound requirement with 1 supported and 1 unsupported component -> PARTIALLY_SUPPORTED
def test_case_10_compound_one_supported_one_unsupported(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Transformer losses within 500 W and nitrogen fire fighting system.",
        is_compound=True,
        compound_components=[
            "Total losses shall not exceed 500 W",
            "Nitrogen gas injection fire protection system"
        ]
    )
    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value


# Case 11: Conflicting evidence across two candidate passages in lexical search -> CONFLICTING
def test_case_11_conflicting_evidence_across_passages(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Searching for "outdoor cooling apparatus" matches Cl 8.1 which says "strictly for indoor use only"
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        query_text="outdoor cooling apparatus",
        requirement_text="Outdoor oil cooling apparatus for distribution transformer."
    )
    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.CONFLICTING.value


# Case 12: Correct clause in wrong edition -> CORPUS_DOCUMENT_NOT_ELIGIBLE & UNVERIFIED_COVERAGE
def test_case_12_wrong_edition_isolation(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=1979,
        clause_identifier="4.2",
        requirement_text="Total losses."
    )
    assert ev.outcome == ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value


# Case 13: Missing or unverified extraction quality metadata -> rejected in validator
def test_case_13_missing_extraction_quality_metadata(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    validator = TraceableEvidenceValidator(corpus_storage=storage)

    # Storing document with None/empty extraction quality
    doc_bad = CorpusDocumentRecord(
        doc_id="DOC-IS-UNVERIFIED",
        standard_number="IS 2026",
        edition_year=2011,
        document_title="Unverified Document",
        source_citation="Test",
        source_url="https://example.com",
        file_sha256="sha256_unverified_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=""  # Empty/unspecified status
    )
    storage.store_document(doc_bad)

    rec = TraceableEvidenceRecord(
        requirement_id="REQ-BAD-QUAL",
        requirement_text="Power transformer testing.",
        standard_number="IS 2026",
        standard_year=2011,
        clause_evidence_outcome="CLAUSE_EVIDENCE_FOUND",
        corpus_document_id="DOC-IS-UNVERIFIED",
        corpus_file_sha256="sha256_unverified_file",
        clause_identifier="1.0",
        is_normative_clause_verified=True,
        requirement_evidence_support=RequirementEvidenceSupportState.FULLY_SUPPORTED.value
    )

    validated = validator.validate_record(rec)
    assert validated.is_normative_clause_verified is False
    assert any("Ineligible Corpus Document" in e for e in validated.validation_errors)


# Case 14: OCR-required or quality-failed source -> ineligible
def test_case_14_ocr_required_ineligible(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    doc_ocr = CorpusDocumentRecord(
        doc_id="DOC-IS-OCR",
        standard_number="IS 3043",
        edition_year=2018,
        document_title="Earthing Code",
        source_citation="Scanned PDF",
        source_url="https://example.com",
        file_sha256="sha256_ocr_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.OCR_REQUIRED.value
    )
    storage.store_document(doc_ocr)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 3043",
        edition_year=2018,
        clause_identifier="5.1",
        requirement_text="Earthing resistance."
    )
    assert ev.outcome == ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value
    assert ev.extraction_quality_status == IngestionStatus.OCR_REQUIRED.value


# Case 15: Missing corpus storage and DB lookup failures -> UNVERIFIED_COVERAGE
def test_case_15_missing_corpus_storage():
    retriever = ClauseRetriever(storage=None)
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Total losses."
    )
    assert ev.outcome == ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value


# Case 16: Tampered document or passage hashes -> invalidated in validator
def test_case_16_tampered_document_hashes(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    validator = TraceableEvidenceValidator(corpus_storage=storage)

    rec = TraceableEvidenceRecord(
        requirement_id="REQ-TAMPER-16",
        requirement_text="Total losses.",
        standard_number="IS 1180 (Part 1)",
        standard_year=2014,
        clause_evidence_outcome="CLAUSE_EVIDENCE_FOUND",
        corpus_document_id="DOC-IS-1180-2014",
        corpus_file_sha256="forged_sha256_file_hash",
        clause_identifier="4.2",
        is_normative_clause_verified=True,
        requirement_evidence_support=RequirementEvidenceSupportState.FULLY_SUPPORTED.value
    )
    validated = validator.validate_record(rec)
    assert validated.is_normative_clause_verified is False
    assert any("Corpus File Hash Mismatch" in e for e in validated.validation_errors)


# Case 17: Clause identifiers differing superficially (4.2 vs 4.20) -> strictly distinguished
def test_case_17_clause_identifier_superficial_discrimination(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev_42 = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Maximum permissible losses."
    )
    assert ev_42.clause_identifier == "4.2"
    assert "Losses" in ev_42.passage_text
    assert "Auxiliary Wiring" not in ev_42.passage_text

    ev_420 = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.20",
        requirement_text="Auxiliary marshalling box wiring."
    )
    assert ev_420.clause_identifier == "4.20"
    assert "Auxiliary Wiring" in ev_420.passage_text
    assert "Permissible Losses" not in ev_420.passage_text


# Case 18: Requirements whose technical parameters cannot be parsed safely -> conservative fallback
def test_case_18_unparseable_technical_parameters(matrix_env):
    d, db_path, storage = matrix_env
    populate_matrix_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender has complex unparseable formula: "loss coefficient alpha = e^(x/y) with non-standard flux"
    # Passage only talks about 500 W losses.
    # Because tender technical parameters are absent from passage, must fall back conservatively to PARTIALLY_SUPPORTED
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Transformer losses with specialized loss coefficient alpha = e^(x/y) and 33 kV insulation."
    )
    # The 33 kV parameter is completely missing from the passage (which only specifies 500 W for 100 kVA)
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value
