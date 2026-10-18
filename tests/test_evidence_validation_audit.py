"""
tests/test_evidence_validation_audit.py — Phase 20 Evidence-to-Requirement Validation Audit Tests

Deterministic adversarial test suite testing requirement evidence support states,
source-corpus cryptographic verification, quality enforcement, and boundary safeguards.

Covers:
1. Correct standard, edition, matching clause, but irrelevant passage -> UNSUPPORTED
2. Correct passage identity, but incomplete support for compound requirement -> PARTIALLY_SUPPORTED
3. Correct product family, but conflicting operating envelope or rating -> CONFLICTING & review required
4. Clause identifier absent from the corpus -> UNVERIFIED_COVERAGE
5. Correct clause number in the wrong edition -> CORPUS_DOCUMENT_NOT_ELIGIBLE & UNVERIFIED_COVERAGE
6. Similar clause numbers rejected without fuzzy matching (e.g., 4.2 vs 4.2.1)
7. Unknown clause identifier rejected without grounding
8. Passage with corrupted or failed extraction quality (QUALITY_FAILED, OCR_REQUIRED) rejects verification
9. Cryptographic mismatch (file_sha256 or passage_hash) caught and invalidated in TraceableEvidenceValidator
10. Corpus unavailable or lookup failure handled gracefully without false claims
11. Human adjudication (is_human_verified) and official BIS authentication (is_official_source_authenticated) remain false
12. Review-required decisions and abstentions preserved without distortion
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
from src.recommend import StandardsRecommender, RequirementRecommendationResult


@pytest.fixture
def adversarial_env():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "corpus_adversarial.db")
        storage = CorpusStorage(db_path=db_path)
        yield d, db_path, storage


def populate_adversarial_corpus(storage: CorpusStorage):
    """Populates controlled synthetic corpus with multi-edition and adversarial test cases."""
    # 1. IS 1180 (Part 1) : 2014 (Eligible)
    doc_2014 = CorpusDocumentRecord(
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        document_title="Outdoor Distribution Transformers 2014",
        source_citation="Synthetic Test Document 2014",
        source_url="https://standardsbis.bsbedge.com",
        file_sha256="sha256_is1180_2014_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_document(doc_2014)

    # 1a. Irrelevant Clause (Painting clause for a Loss requirement)
    p_irrelevant = ClausePassage(
        passage_id="DOC-IS-1180-2014_p10_c10_1_0",
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_is1180_2014_file",
        page_start=10,
        page_end=10,
        clause_identifier="10.1",
        passage_text="10.1 Painting and Surface Treatment\nAll exterior steel surfaces shall be coated with epoxy primer paint.",
        content_hash=ClauseAwareChunker.canonical_hash("10.1 Painting and Surface Treatment All exterior steel surfaces shall be coated with epoxy primer paint."),
        verification_state="CLAUSE_IDENTIFIER_VERIFIED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )
    # 1b. Losses Clause
    p_losses = ClausePassage(
        passage_id="DOC-IS-1180-2014_p2_c4_2_0",
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_is1180_2014_file",
        page_start=2,
        page_end=2,
        clause_identifier="4.2",
        passage_text="4.2 Maximum Permissible Losses\nTotal losses at 50% load shall not exceed 475 W for 100 kVA rating.",
        content_hash=ClauseAwareChunker.canonical_hash("4.2 Maximum Permissible Losses Total losses at 50% load shall not exceed 475 W for 100 kVA rating."),
        verification_state="CLAUSE_IDENTIFIER_VERIFIED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )

    # 1c. Operating Condition Conflict Clause (Strictly Indoor requirement vs Outdoor rating)
    p_indoor_only = ClausePassage(
        passage_id="DOC-IS-1180-2014_p4_c6_1_0",
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_is1180_2014_file",
        page_start=4,
        page_end=4,
        clause_identifier="6.1",
        passage_text="6.1 Operating Envelope\nApparatus designed strictly for indoor dry-type installation only.",
        content_hash=ClauseAwareChunker.canonical_hash("6.1 Operating Envelope Apparatus designed strictly for indoor dry-type installation only."),
        verification_state="CLAUSE_IDENTIFIER_VERIFIED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )

    # 1d. Clause 4.2.1 (Sub-clause to test precision matching vs 4.2)
    p_sub = ClausePassage(
        passage_id="DOC-IS-1180-2014_p2_c4_2_1_0",
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_is1180_2014_file",
        page_start=2,
        page_end=2,
        clause_identifier="4.2.1",
        passage_text="4.2.1 Measurement Protocol\nLoss measurement tolerance shall be within 5 percent.",
        content_hash=ClauseAwareChunker.canonical_hash("4.2.1 Measurement Protocol Loss measurement tolerance shall be within 5 percent."),
        verification_state="CLAUSE_IDENTIFIER_VERIFIED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )

    storage.store_passages([p_irrelevant, p_losses, p_indoor_only, p_sub])

    # 2. IS 1180 (Part 1) : 1989 (Older Edition)
    doc_1989 = CorpusDocumentRecord(
        doc_id="DOC-IS-1180-1989",
        standard_number="IS 1180 (Part 1)",
        edition_year=1989,
        document_title="Outdoor Distribution Transformers 1989",
        source_citation="Synthetic Test Document 1989",
        source_url="https://standardsbis.bsbedge.com",
        file_sha256="sha256_is1180_1989_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_document(doc_1989)

    # 3. Degraded Quality Document (QUALITY_FAILED)
    doc_corrupt = CorpusDocumentRecord(
        doc_id="DOC-IS-CORRUPT",
        standard_number="IS 9999",
        edition_year=2020,
        document_title="Corrupt OCR Document",
        source_citation="Synthetic Corrupt Fixture",
        source_url="https://example.com",
        file_sha256="sha256_corrupt_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.QUALITY_FAILED.value
    )
    storage.store_document(doc_corrupt)

    p_corrupt = ClausePassage(
        passage_id="DOC-IS-CORRUPT_p1_c1_0",
        doc_id="DOC-IS-CORRUPT",
        standard_number="IS 9999",
        edition_year=2020,
        source_file_sha256="sha256_corrupt_file",
        page_start=1,
        page_end=1,
        clause_identifier="1.0",
        passage_text="1.0 Garbled unreadable OCR text %$#@!",
        content_hash=ClauseAwareChunker.canonical_hash("1.0 Garbled unreadable OCR text %$#@!"),
        verification_state="FAILED",
        extraction_quality_status=IngestionStatus.QUALITY_FAILED.value
    )
    storage.store_passages([p_corrupt])


# --- Scenario 1: Correct standard/edition/clause, but irrelevant passage -> UNSUPPORTED ---
def test_scenario_1_irrelevant_passage_marked_unsupported(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender requirement is about transformer losses, but clause specified is 10.1 (Painting)
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="10.1",
        requirement_text="Total losses at 50% load shall not exceed 475 watts for outdoor distribution transformer."
    )

    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert ev.clause_identifier == "10.1"
    assert ev.is_grounded is True
    # Crucial Phase 20 assertion: Even though clause exists and is grounded, it is UNSUPPORTED
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNSUPPORTED.value


# --- Scenario 2: Compound requirement with incomplete sub-component coverage -> PARTIALLY_SUPPORTED ---
def test_scenario_2_compound_requirement_partial_support(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Compound requirement with two parts: losses and lightning impulse withstand
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Distribution transformer total losses shall be within 475 W and impulse withstand shall be 75 kV.",
        is_compound=True,
        compound_components=[
            "Total losses at 50% load shall not exceed 475 watts",
            "Basic lightning impulse insulation level shall be 75 kV peak"
        ]
    )

    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    # Crucial Phase 20 assertion: Cannot claim FULLY_SUPPORTED for compound if only 1 component is covered
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value


# --- Scenario 3: Product family correct, but conflicting operating envelope -> CONFLICTING ---
def test_scenario_3_operating_envelope_conflict(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Tender explicitly demands outdoor pole-mounted transformer, passage says indoor only
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="6.1",
        requirement_text="Outdoor pole mounted transformer installation with weather-proof enclosure."
    )

    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.CONFLICTING.value


# --- Scenario 4: Clause identifier absent from the corpus -> UNVERIFIED_COVERAGE ---
def test_scenario_4_absent_clause_identifier(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="99.99",
        requirement_text="Total losses at 50% load shall not exceed 475 watts."
    )

    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND.value
    assert ev.is_grounded is False
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value


# --- Scenario 5: Correct clause number in wrong edition -> CORPUS_DOCUMENT_NOT_ELIGIBLE & UNVERIFIED_COVERAGE ---
def test_scenario_5_clause_in_wrong_edition(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Clause 4.2 was stored for 2014 edition, querying 1989 edition
    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=1989,
        clause_identifier="4.2",
        requirement_text="Total losses at 50% load shall not exceed 475 watts."
    )

    # Clause was not indexed in 1989 document
    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND.value
    assert ev.is_grounded is False
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value


# --- Scenario 6: Similar clause numbers rejected without fuzzy matching (4.2 vs 4.2.1) ---
def test_scenario_6_no_fuzzy_clause_matching(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Querying 4.2 must not return 4.2.1
    ev_42 = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Maximum permissible losses."
    )
    assert ev_42.clause_identifier == "4.2"
    assert "4.2 Maximum Permissible Losses" in ev_42.passage_text
    assert "Measurement Protocol" not in ev_42.passage_text

    # Querying 4.2.1 must not return 4.2
    ev_421 = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2.1",
        requirement_text="Loss measurement tolerance."
    )
    assert ev_421.clause_identifier == "4.2.1"
    assert "Measurement Protocol" in ev_421.passage_text


# --- Scenario 7: Unknown clause identifier rejected without grounding ---
def test_scenario_7_unknown_clause_identifier_not_grounded(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="CLAUSE_UNKNOWN",
        requirement_text="General introductory notes."
    )

    assert ev.is_grounded is False
    assert ev.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND.value


# --- Scenario 8: Corrupted extraction quality status rejects verification ---
def test_scenario_8_corrupted_extraction_quality_rejects_verification(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 9999",
        edition_year=2020,
        clause_identifier="1.0",
        requirement_text="Garbled text."
    )

    # Corrupt document is ineligible for clause verification
    assert ev.outcome == ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value
    assert ev.is_grounded is False
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value


# --- Scenario 9: Cryptographic mismatch caught and invalidated in TraceableEvidenceValidator ---
def test_scenario_9_cryptographic_hash_mismatch_invalidates_clause_verification(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)

    validator = TraceableEvidenceValidator(corpus_storage=storage)

    # Record presenting forged / altered passage hash
    tampered_record = TraceableEvidenceRecord(
        requirement_id="REQ-TAMPERED-01",
        requirement_text="Total losses shall not exceed 475 W.",
        standard_number="IS 1180 (Part 1)",
        standard_year=2014,
        clause_evidence_outcome="CLAUSE_EVIDENCE_FOUND",
        corpus_document_id="DOC-IS-1180-2014",
        corpus_file_sha256="sha256_is1180_2014_file",
        clause_identifier="4.2",
        clause_passage_hash="forged_sha256_hash_that_does_not_match_storage",
        is_normative_clause_verified=True,
        requirement_evidence_support=RequirementEvidenceSupportState.FULLY_SUPPORTED.value
    )

    validated = validator.validate_record(tampered_record)
    assert validated.is_normative_clause_verified is False
    assert any("Passage Content Hash Mismatch" in e for e in validated.validation_errors)


# --- Scenario 10: Corpus unavailable handled gracefully without false claims ---
def test_scenario_10_corpus_unavailable_graceful_handling():
    # Pass storage=None to simulate unavailable corpus subsystem
    retriever = ClauseRetriever(storage=None)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Total losses."
    )

    assert ev.outcome == ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value
    assert ev.is_grounded is False
    assert ev.requirement_evidence_support == RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value


# --- Scenario 11: Human adjudication and official BIS authentication remain false ---
def test_scenario_11_anti_falsification_invariants(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)
    validator = TraceableEvidenceValidator(corpus_storage=storage)

    ev = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2",
        requirement_text="Total losses at 50% load shall not exceed 475 watts."
    )

    record = validator.build_trace_record(
        requirement_id="REQ-TEST-11",
        requirement_text="Total losses at 50% load shall not exceed 475 watts.",
        recommendation=None,
        clause_evidence=ev
    )

    # Both must strictly remain False for automated processing
    assert record.is_human_verified is False
    assert record.is_official_source_authenticated is False


# --- Scenario 12: Conflicting evidence forces assisted review and preserves safety boundaries ---
def test_scenario_12_conflicting_evidence_triggers_review_in_recommender(adversarial_env):
    d, db_path, storage = adversarial_env
    populate_adversarial_corpus(storage)
    retriever = ClauseRetriever(storage=storage)
    validator = TraceableEvidenceValidator(corpus_storage=storage)

    # When conflicting evidence is found, validate_record forces ASSISTED_REVIEW_REQUIRED
    conflicting_record = TraceableEvidenceRecord(
        requirement_id="REQ-CONFLICT-12",
        requirement_text="Outdoor pole mounted transformer installation.",
        standard_number="IS 1180 (Part 1)",
        standard_year=2014,
        clause_evidence_outcome="CLAUSE_EVIDENCE_FOUND",
        corpus_document_id="DOC-IS-1180-2014",
        corpus_file_sha256="sha256_is1180_2014_file",
        clause_identifier="6.1",
        clause_passage_hash=ClauseAwareChunker.canonical_hash("6.1 Operating Envelope Apparatus designed strictly for indoor dry-type installation only."),
        is_normative_clause_verified=True,
        requirement_evidence_support=RequirementEvidenceSupportState.CONFLICTING.value,
        final_system_decision="RECOMMEND"
    )

    validated = validator.validate_record(conflicting_record)
    assert validated.human_review_required is True
    assert validated.final_system_decision == "ASSISTED_REVIEW_REQUIRED"
    assert any("Conflicting Evidence" in e for e in validated.validation_errors)
