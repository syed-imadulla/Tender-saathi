"""
tests/test_clause_evidence_integration.py — Phase 19 Safe Clause-Level Evidence Integration Tests

Validates:
1. Exact standard and edition matching
2. Multiple editions isolation for the same standard number
3. Correct page number, clause identifier, document ID, and content hashes
4. Clause not found in an eligible corpus (CLAUSE_EVIDENCE_NOT_FOUND)
5. No corpus document available (CORPUS_DOCUMENT_NOT_ELIGIBLE)
6. Ineligible document with OCR_REQUIRED or QUALITY_FAILED status
7. Corrupt or uninitialized corpus database (CORPUS_NOT_AVAILABLE)
8. Similar clause identifiers not treated as exact matches (e.g. 4.2 vs 4.2.1)
9. Unknown clause identifiers (CLAUSE_UNKNOWN is not grounded)
10. Compound requirements with per-component clause evidence
11. Preservation of review-required and abstention decisions (no safety bypass)
12. Anti-falsification invariants (is_official_source_authenticated=False, is_human_verified=False)
13. API serialization verification
"""

import os
import json
import tempfile
import pytest
import pymupdf as fitz

from src.standards import StandardsDatabase
from src.corpus.manifest import LicensingStatus, IngestionStatus, CorpusDocumentRecord
from src.corpus.chunker import ClauseAwareChunker, ClausePassage
from src.corpus.storage import CorpusStorage
from src.corpus.retriever import ClauseRetriever, ClauseEvidenceOutcome
from src.traceability import TraceableEvidenceValidator
from src.recommend import StandardsRecommender, RequirementRecommendationResult


@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "corpus.db")
        storage = CorpusStorage(db_path=db_path)
        yield d, db_path, storage


def populate_test_corpus(storage: CorpusStorage):
    """Populates test corpus with multi-edition standards and controlled clauses."""
    # 1. IS 1180 (Part 1) : 2014 (Eligible)
    doc_2014 = CorpusDocumentRecord(
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        document_title="Outdoor Distribution Transformers",
        source_citation="BIS Gazette 2014",
        source_url="https://standardsbis.bsbedge.com",
        file_sha256="sha256_is1180_2014_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_document(doc_2014)

    p_42_2014 = ClausePassage(
        passage_id="DOC-IS-1180-2014_p2_c4_2_0",
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_is1180_2014_file",
        page_start=2,
        page_end=2,
        clause_identifier="4.2",
        passage_text="4.2 Maximum Permissible Losses\nTotal losses at 50% load shall not exceed 475 W.",
        content_hash=ClauseAwareChunker.canonical_hash("4.2 Maximum Permissible Losses Total losses at 50% load shall not exceed 475 W."),
        verification_state="CLAUSE_IDENTIFIER_VERIFIED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )

    p_51_2014 = ClausePassage(
        passage_id="DOC-IS-1180-2014_p3_c5_1_0",
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_is1180_2014_file",
        page_start=3,
        page_end=3,
        clause_identifier="5.1",
        passage_text="5.1 Temperature Rise Limit\nTop oil temperature rise shall not exceed 35 deg C.",
        content_hash=ClauseAwareChunker.canonical_hash("5.1 Temperature Rise Limit Top oil temperature rise shall not exceed 35 deg C."),
        verification_state="CLAUSE_IDENTIFIER_VERIFIED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )

    p_unk_2014 = ClausePassage(
        passage_id="DOC-IS-1180-2014_p1_cunknown_0",
        doc_id="DOC-IS-1180-2014",
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        source_file_sha256="sha256_is1180_2014_file",
        page_start=1,
        page_end=1,
        clause_identifier="CLAUSE_UNKNOWN",
        passage_text="General introductory notes on manufacturing methods.",
        content_hash=ClauseAwareChunker.canonical_hash("General introductory notes on manufacturing methods."),
        verification_state="EXTRACTION_QUALITY_CHECKED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_passages([p_42_2014, p_51_2014, p_unk_2014])

    # 2. IS 1180 (Part 1) : 1989 (Older Edition)
    doc_1989 = CorpusDocumentRecord(
        doc_id="DOC-IS-1180-1989",
        standard_number="IS 1180 (Part 1)",
        edition_year=1989,
        document_title="Outdoor Distribution Transformers 1989",
        source_citation="BIS Gazette 1989",
        file_sha256="sha256_is1180_1989_file",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_document(doc_1989)

    p_42_1989 = ClausePassage(
        passage_id="DOC-IS-1180-1989_p2_c4_2_0",
        doc_id="DOC-IS-1180-1989",
        standard_number="IS 1180 (Part 1)",
        edition_year=1989,
        source_file_sha256="sha256_is1180_1989_file",
        page_start=2,
        page_end=2,
        clause_identifier="4.2",
        passage_text="4.2 Losses\nTotal loss at 50% load shall not exceed 650 W for 1989 edition.",
        content_hash=ClauseAwareChunker.canonical_hash("4.2 Losses Total loss at 50% load shall not exceed 650 W for 1989 edition."),
        verification_state="CLAUSE_IDENTIFIER_VERIFIED",
        extraction_quality_status=IngestionStatus.EXTRACTED.value
    )
    storage.store_passages([p_42_1989])

    # 3. IS 694 : 2010 (Ineligible: OCR_REQUIRED)
    doc_ocr = CorpusDocumentRecord(
        doc_id="DOC-IS-694-OCR",
        standard_number="IS 694",
        edition_year=2010,
        document_title="PVC Insulated Cables",
        file_sha256="sha256_is694_scanned",
        licensing_status=LicensingStatus.PERMITTED_TEST_FIXTURE.value,
        ingestion_status=IngestionStatus.OCR_REQUIRED.value,
        failure_reasons=["Scanned PDF: OCR required"]
    )
    storage.store_document(doc_ocr)


def test_1_exact_standard_and_edition_matching(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Exact match for 2014 edition
    res_2014 = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2"
    )
    assert res_2014.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert res_2014.is_grounded is True
    assert "475 W" in (res_2014.passage_text or "")
    assert res_2014.page_number == 2
    assert res_2014.document_id == "DOC-IS-1180-2014"
    assert res_2014.file_sha256 == "sha256_is1180_2014_file"
    assert res_2014.extraction_quality_status == IngestionStatus.EXTRACTED.value


def test_2_multiple_editions_isolation(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # 1989 Edition
    res_1989 = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=1989,
        clause_identifier="4.2"
    )
    assert res_1989.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert res_1989.is_grounded is True
    assert "650 W" in (res_1989.passage_text or "")
    assert res_1989.document_id == "DOC-IS-1180-1989"

    # Non-existent edition (e.g. 2025)
    res_2025 = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2025,
        clause_identifier="4.2"
    )
    assert res_2025.outcome == ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value
    assert res_2025.is_grounded is False


def test_3_clause_not_found_in_eligible_corpus(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Document IS 1180:2014 exists and is eligible, but Clause 99.9 does not exist
    res = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="99.9"
    )
    assert res.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND.value
    assert res.is_grounded is False
    assert "Clause '99.9' not found" in res.message


def test_4_no_corpus_document_available(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Standard IS 4984 has no full-text corpus document
    res = retriever.retrieve_clause_evidence(
        standard_number="IS 4984",
        edition_year=2016,
        clause_identifier="5.2"
    )
    assert res.outcome == ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value
    assert res.is_grounded is False
    assert "No full-text corpus document registered" in res.message


def test_5_ineligible_document_ocr_required(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # IS 694 has document registered but status is OCR_REQUIRED
    res = retriever.retrieve_clause_evidence(
        standard_number="IS 694",
        edition_year=2010,
        clause_identifier="3.1"
    )
    assert res.outcome == ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value
    assert res.is_grounded is False
    assert "is ineligible" in res.message
    assert res.extraction_quality_status == IngestionStatus.OCR_REQUIRED.value


def test_6_corrupt_or_unavailable_corpus_database(tmp_path):
    db_file = str(tmp_path / "temp_corpus.db")
    storage = CorpusStorage(db_path=db_file)
    retriever = ClauseRetriever(storage=storage)

    # Subcase A: File does not exist / deleted
    os.remove(db_file)
    res_missing = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2"
    )
    assert res_missing.outcome == ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value
    assert res_missing.is_grounded is False

    # Subcase B: Corrupt SQLite file
    with open(db_file, "wb") as f:
        f.write(b"NOT_A_VALID_SQLITE_DATABASE_HEADER")
    res_corrupt = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2"
    )
    assert res_corrupt.outcome == ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value
    assert res_corrupt.is_grounded is False

    # Subcase C: Storage subsystem None
    res_none = ClauseRetriever(storage=None).retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2"
    )
    assert res_none.outcome == ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value


def test_7_similar_clause_identifiers_no_fuzzy_match(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Corpus has "4.2", but caller asks for "4.2.1"
    res = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="4.2.1"
    )
    assert res.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND.value
    assert res.is_grounded is False


def test_8_unknown_clause_identifiers_not_grounded(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)
    retriever = ClauseRetriever(storage=storage)

    # Retrieval of CLAUSE_UNKNOWN passage
    res = retriever.retrieve_clause_evidence(
        standard_number="IS 1180 (Part 1)",
        edition_year=2014,
        clause_identifier="CLAUSE_UNKNOWN"
    )
    assert res.outcome == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert res.is_grounded is False
    assert "grounding cannot be verified" in res.message


def test_9_recommender_integration_end_to_end(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)

    recommender = StandardsRecommender(corpus_storage=storage)

    # Recommend for requirement with explicit clause mention
    req_text = "Supply of 100 kVA outdoor distribution transformer conforming to IS 1180 (Part 1) : 2014 Clause 4.2"
    result = recommender.recommend_for_text(req_text, req_id="REQ-E2E-1")

    assert "IS 1180 (Part 1)" in result.candidate_standard
    assert result.clause_evidence is not None
    assert result.clause_evidence["outcome"] == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert result.clause_evidence["clause_identifier"] == "4.2"
    assert result.clause_evidence["is_grounded"] is True
    assert "475 W" in result.clause_evidence["passage_text"]

    # Trace record verification
    assert result.trace_record is not None
    assert result.trace_record["is_normative_clause_verified"] is True
    assert result.trace_record["clause_evidence_outcome"] == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value
    assert result.trace_record["clause_identifier"] == "4.2"
    assert result.trace_record["clause_page_number"] == 2

    # Invariants
    assert result.trace_record["is_official_source_authenticated"] is False
    assert result.trace_record["is_human_verified"] is False
    assert result.trace_record["is_catalogue_verified"] is True


def test_10_compound_requirements_per_component_clause_evidence(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)

    recommender = StandardsRecommender(corpus_storage=storage)

    # Compound requirement with transformer (eligible in corpus) and wiring
    req_text = "100 kVA distribution transformer with copper winding and external electrical wiring"
    result = recommender.recommend_for_text(req_text, req_id="REQ-COMP-1")

    # Overall candidate is IS 1180
    assert "IS 1180 (Part 1)" in result.candidate_standard
    assert result.clause_evidence is not None

    # Decomposed components
    comp_recs = result.component_recommendations
    assert len(comp_recs) >= 1
    # Each component bundle has clause_evidence dictionary or None
    for c in comp_recs:
        assert "clause_evidence" in c


def test_11_abstention_and_review_decisions_preserved(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)

    recommender = StandardsRecommender(corpus_storage=storage)

    # Negative control / non-standard requirement
    neg_req = "supply of generic catering services and fruit juice dispensers for staff cafeteria"
    result = recommender.recommend_for_text(neg_req, req_id="REQ-NEG-1")

    # Safety gates: must abstain
    assert result.candidate_standard is None
    assert result.human_review_required is True
    assert result.critic_result["decision"] in ("WITHHELD_INSUFFICIENT_EVIDENCE", "REVIEW_REQUIRED", "NO_RELIABLE_MATCH")
    assert result.trace_record["final_system_decision"] in ("WITHHELD_INSUFFICIENT_EVIDENCE", "ASSISTED_REVIEW_REQUIRED", "NO_RELIABLE_MATCH")
    assert result.trace_record["is_normative_clause_verified"] is False


def test_12_anti_falsification_boundaries(temp_env):
    _, _, storage = temp_env
    populate_test_corpus(storage)

    validator = TraceableEvidenceValidator(corpus_storage=storage)

    class MockRec:
        standard_number = "IS 1180 (Part 1)"
        title = "Outdoor Transformers"
        status = "ACTIVE"
        evidence = "Losses shall not exceed 475 W."
        structured_evidence = {
            "bis_scope_evidence": "This standard specifies requirements for mineral oil immersed distribution transformers.",
            "scope_status": "VERIFIED"
        }
        human_review_required = False
        relevance_score = 0.95
        clause_evidence = {
            "outcome": ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value,
            "clause_identifier": "4.2",
            "passage_text": "Losses shall not exceed 475 W.",
            "page_number": 2,
            "passage_sha256": "sha256_dummy",
            "document_id": "DOC-IS-1180-2014",
            "file_sha256": "sha256_file",
            "extraction_quality_status": "EXTRACTED",
            "is_grounded": True
        }

    rec = validator.build_trace_record(
        requirement_id="REQ-GUARD",
        requirement_text="100 kVA transformer Clause 4.2",
        recommendation=MockRec(),
        critic_decision="RECOMMEND"
    )

    # Core non-falsification guarantees
    assert rec.is_normative_clause_verified is True
    assert rec.is_official_source_authenticated is False  # Cannot declare live BIS authentication
    assert rec.is_human_verified is False                 # Cannot declare human expert adjudication
    assert rec.is_local_catalogue_verified is True


def test_13_api_serialization():
    from api.server import app

    client = app.test_client()
    resp = client.post("/api/analyze/text", json={"text": "100 kVA outdoor distribution transformer as per IS 1180 Clause 4.2"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "requirements" in data
    res0 = data["requirements"][0]

    assert "clause_evidence" in res0
    assert "trace_record" in res0
    assert "component_trace_records" in res0

    trace = res0["trace_record"]
    assert "clause_evidence_outcome" in trace
    assert "is_official_source_authenticated" in trace
    assert trace["is_official_source_authenticated"] is False
    assert trace["is_human_verified"] is False
