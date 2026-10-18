"""
tests/test_targeted_normative_ingestion.py — Phase 26 Targeted Normative Evidence Ingestion Tests

Tests:
1. Exact standard, part, and edition matching.
2. Clause-level traceability and parameter support for IS 456, IS 4984, and IS 1489.
3. Authoritative supersedence warning for withdrawn IS 8112 -> IS 269.
4. Edition mismatch safeguard: obsolete editions (e.g. IS 4984:1995) do not falsely ground to 2016 passages.
5. Catalogue-only candidates remain strictly PENDING_TECHNICAL_EVALUATION with zero fabricated clauses.
6. Safe abstention on service-only tenders is strictly preserved.
7. Provenance and statutory licensing invariants in CorpusStorage.
"""

import pytest
import sqlite3
from src.extract import extract_from_text
from src.recommend import StandardsRecommender
from src.corpus.storage import CorpusStorage
from src.corpus.retriever import ClauseRetriever
from src.corpus.manifest import LicensingStatus, IngestionStatus


@pytest.fixture(scope="module")
def recommender():
    return StandardsRecommender()


@pytest.fixture(scope="module")
def corpus_storage():
    return CorpusStorage("data/standards/corpus.db")


@pytest.fixture(scope="module")
def clause_retriever(corpus_storage):
    return ClauseRetriever(storage=corpus_storage)


def test_is456_corpus_document_and_passages(corpus_storage, clause_retriever):
    """Verify IS 456 document is stored with authentic normative passages."""
    docs = corpus_storage.get_documents_by_standard("IS 456", edition_year=2000)
    assert len(docs) >= 1, "IS 456 : 2000 document must be registered in corpus.db"
    doc = docs[0]
    assert doc["licensing_status"] == LicensingStatus.STATUTORY_PUBLIC_GAZETTE.value
    assert doc["ingestion_status"] == IngestionStatus.EXTRACTED.value
    assert "Plain and Reinforced Concrete" in doc["document_title"]

    # Verify key clauses exist
    cl_1_1 = clause_retriever.get_clause("IS 456", "1.1", edition_year=2000)
    assert cl_1_1 is not None
    assert "plain and reinforced concrete" in cl_1_1.passage_text.lower()

    cl_6_1 = clause_retriever.get_clause("IS 456", "6.1", edition_year=2000)
    assert cl_6_1 is not None
    assert "grades of concrete" in cl_6_1.passage_text.lower()
    assert "m25" in cl_6_1.passage_text.lower()

    cl_8_2 = clause_retriever.get_clause("IS 456", "8.2", edition_year=2000)
    assert cl_8_2 is not None
    assert "table 5" in cl_8_2.passage_text.lower()
    assert "water-cement ratio" in cl_8_2.passage_text.lower()


def test_is456_recommendation_and_clause_evidence(recommender):
    """Verify IS 456 concrete tender requirement produces clause-grounded recommendation."""
    text = "Design and casting of plain and reinforced concrete foundation columns using M25 grade concrete mix conforming to IS 456."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert "456" in res.candidate_standard
    assert res.confidence == "High"
    assert res.clause_evidence is not None
    assert res.clause_evidence.get("clause_identifier") in ["1.1", "6.1", "8.2", "5.1"]
    assert res.clause_evidence.get("requirement_evidence_support") in ["FULLY_SUPPORTED", "PARTIALLY_SUPPORTED"]


def test_is4984_hdpe_pipe_clauses_and_recommendation(corpus_storage, clause_retriever, recommender):
    """Verify IS 4984 HDPE pipe document, pressure/material clauses, and recommendation."""
    docs = corpus_storage.get_documents_by_standard("IS 4984", edition_year=2016)
    assert len(docs) >= 1, "IS 4984 : 2016 must be registered in corpus.db"
    doc = docs[0]
    assert doc["licensing_status"] == LicensingStatus.STATUTORY_PUBLIC_GAZETTE.value

    # Verify material (Cl 4.1) and pressure rating (Cl 4.2)
    cl_4_1 = clause_retriever.get_clause("IS 4984", "4.1", edition_year=2016)
    assert cl_4_1 is not None
    assert "pe 100" in cl_4_1.passage_text.lower()

    cl_4_2 = clause_retriever.get_clause("IS 4984", "4.2", edition_year=2016)
    assert cl_4_2 is not None
    assert "pn 10" in cl_4_2.passage_text.lower()

    # Verify recommendation
    text = "Supply of HDPE pipes for potable water supply conforming to IS 4984 PN 10 PE 100 DN 110 mm."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert "4984" in res.candidate_standard
    assert res.confidence == "High"
    assert res.clause_evidence is not None
    assert res.clause_evidence.get("clause_identifier") is not None


def test_is1489_part1_ppc_cement_clauses_and_recommendation(corpus_storage, clause_retriever, recommender):
    """Verify IS 1489 (Part 1) PPC cement clauses and recommendation."""
    docs = corpus_storage.get_documents_by_standard("IS 1489 (Part 1)", edition_year=2015)
    assert len(docs) >= 1, "IS 1489 (Part 1) : 2015 must be registered in corpus.db"

    # Verify fly ash content clause
    cl_5_2 = clause_retriever.get_clause("IS 1489 (Part 1)", "5.2", edition_year=2015)
    assert cl_5_2 is not None
    assert "fly ash" in cl_5_2.passage_text.lower()
    assert "15 percent" in cl_5_2.passage_text.lower()

    # Verify compressive strength clause
    cl_7_2 = clause_retriever.get_clause("IS 1489 (Part 1)", "7.2", edition_year=2015)
    assert cl_7_2 is not None
    assert "33 mpa" in cl_7_2.passage_text.lower()

    # Verify recommendation
    text = "Supply of Portland Pozzolana Cement conforming to IS 1489 (Part 1) for masonry and plastering work."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert "1489" in res.candidate_standard
    assert res.confidence == "High"
    assert res.clause_evidence is not None
    assert res.clause_evidence.get("clause_identifier") is not None


def test_is8112_supersedence_to_is269(recommender):
    """Verify citing withdrawn IS 8112 mandates human review, abstains safely, and links to IS 269."""
    text = "Supply of 43 Grade Ordinary Portland Cement conforming to IS 8112."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    # Withdrawn standard must mandate human review and avoid autonomous endorsement
    assert res.human_review_required is True
    assert res.candidate_standard is None
    assert not any("NONEXISTENT_CITATION" in str(w) for w in (res.why_not or []))

    # Verify normative relationship is recorded in relationships.json
    import json
    with open("data/standards/relationships.json", "r") as f:
        rels = json.load(f)
    superseded_links = [
        r for r in rels
        if "8112" in r.get("source_standard", "") and "269" in r.get("target_standard", "")
    ]
    assert len(superseded_links) >= 1, "Normative graph must record IS 8112 superseded by IS 269"
    assert superseded_links[0]["relationship_type"] == "SUPERSEDED_BY"


def test_edition_mismatch_prevents_false_grounding(clause_retriever):
    """Verify obsolete edition IS 4984:1995 does not inherit 2016 passages."""
    p_1995 = clause_retriever.get_clause("IS 4984", "4.1", edition_year=1995)
    assert p_1995 is None, "Edition 1995 must not inherit passages from edition 2016"

    p_2016 = clause_retriever.get_clause("IS 4984", "4.1", edition_year=2016)
    assert p_2016 is not None, "Edition 2016 passage must be accessible"


def test_non_ingested_catalogue_remains_pending_evaluation(recommender):
    """Verify un-ingested catalogue candidates remain strictly PENDING_TECHNICAL_EVALUATION."""
    text = "Procurement of marine propulsion diesel engines for coastal patrol vessels."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is not None
    assert res.human_review_required is True
    assert getattr(res, "applicability", {}).get("decision") == "PENDING_TECHNICAL_EVALUATION"
    # Ensure zero fabricated clause evidence
    assert res.clause_evidence.get("outcome") == "CORPUS_DOCUMENT_NOT_ELIGIBLE"
    assert res.clause_evidence.get("passage_text") is None
    assert res.clause_evidence.get("is_grounded") is False


def test_safe_abstention_preserved(recommender):
    """Verify non-engineering administrative services abstain cleanly."""
    text = "Hiring of Chartered Accountant firm for statutory financial audit and taxation compliance."
    req = extract_from_text(text)
    res = recommender.recommend_for_requirement(req)

    assert res.candidate_standard is None
    assert res.human_review_required is True
    assert res.critic_result.get("decision") == "NO_RELIABLE_MATCH"


def test_corpus_storage_provenance_and_licensing(corpus_storage):
    """Verify document records have valid provenance, licensing, and file hashes."""
    with sqlite3.connect(corpus_storage.db_path) as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT doc_id, standard_number, edition_year, licensing_status, file_sha256
            FROM corpus_documents
        """).fetchall()

        assert len(rows) >= 4, "Must contain at least the 4 ingested documents"
        for doc_id, std_num, yr, license_st, sha in rows:
            assert doc_id.startswith("DOC-")
            assert std_num in ["IS 456", "IS 4984", "IS 1489 (Part 1)", "IS 8112"]
            assert license_st == LicensingStatus.STATUTORY_PUBLIC_GAZETTE.value
            assert len(sha) == 64, "File hash must be a valid 64-char SHA-256"
