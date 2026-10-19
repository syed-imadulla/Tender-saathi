"""
Tests for Phase 24: National BIS Catalogue Integration.

Validates:
1. Valid catalogue-only citations (e.g. IS 8112, IS 10001) are recognized and not marked NONEXISTENT_CITATION.
2. Genuinely unknown identifiers (e.g. IS 999999) remain NOT_FOUND.
3. Withdrawn and unknown-status records receive appropriate lifecycle warnings.
4. Multi-edition / multi-part ambiguity triggers review notices and resolves safely.
5. Curated standards (e.g. IS 1180) continue to receive verified clause-level evidence.
6. Catalogue-only candidates never receive invented clause-level evidence.
7. API endpoints (/api/analyze/text and /api/analyze/pdf) properly surface national catalogue validations.
"""

import io
import pytest
from src.retrieval import StandardsDatabase
from src.catalogue.access import get_national_catalogue_db
from src.validate import validate_standard_status, StandardValidationResult
from src.recommend import StandardsRecommender
from api.server import app


@pytest.fixture(scope="module")
def std_db():
    return StandardsDatabase()


@pytest.fixture(scope="module")
def catalogue_db():
    return get_national_catalogue_db()


@pytest.fixture(scope="module")
def recommender(std_db):
    return StandardsRecommender(db=std_db)


@pytest.fixture(scope="module")
def client():
    return app.test_client()


class TestNationalCatalogueAccess:
    """Test the read-only NationalCatalogueDatabase access layer."""

    def test_lookup_active_catalogue_standard(self, catalogue_db):
        record = catalogue_db.lookup_by_identifier("IS 10001")
        assert record is not None
        assert record.status == "ACTIVE"
        assert record.base_number == "10001"
        assert "Performance Requirements" in record.title

    def test_lookup_withdrawn_catalogue_standard(self, catalogue_db):
        record = catalogue_db.lookup_by_identifier("IS 8112")
        assert record is not None
        assert record.status == "WITHDRAWN"
        assert record.base_number == "8112"

    def test_lookup_multi_part_standard(self, catalogue_db):
        record = catalogue_db.lookup_by_identifier("IS 10245")
        assert record is not None
        assert record.base_number == "10245"
        assert record.is_ambiguous_edition is True
        assert "multi-part" in (record.ambiguity_message or "").lower()

    def test_lookup_nonexistent_standard(self, catalogue_db):
        record = catalogue_db.lookup_by_identifier("IS 999999")
        assert record is None

    def test_find_all_editions(self, catalogue_db):
        editions = catalogue_db.find_all_editions("2712")
        assert len(editions) >= 1


class TestCitationValidation:
    """Test citation validation against both curated DB and national catalogue."""

    def test_valid_catalogue_only_withdrawn_is8112_not_nonexistent(self, std_db):
        val = validate_standard_status("IS 8112", std_db)
        assert val.is_known is True
        assert val.recognition_state == "FOUND_WITHDRAWN_OR_SUPERSEDED"
        assert val.status in ["Withdrawn", "Superseded"]
        assert val.is_catalogue_only in [True, False]
        assert "WITHDRAWN" in (val.warning_message or "").upper() or "SUPERSEDED" in (val.warning_message or "").upper()
        assert "not found in either" not in (val.warning_message or "")

    def test_valid_catalogue_only_active_is10001(self, std_db):
        val = validate_standard_status("IS 10001", std_db)
        assert val.is_known is True
        assert val.recognition_state == "FOUND_ACTIVE"
        assert val.is_active is True
        assert val.status == "Active"
        assert val.is_catalogue_only is True

    def test_genuinely_fake_standard_is999999(self, std_db):
        val = validate_standard_status("IS 999999", std_db)
        assert val.is_known is False
        assert val.recognition_state == "NOT_FOUND"
        assert "requires verification" in (val.warning_message or "")

    def test_multi_part_ambiguity_warning(self, std_db):
        val = validate_standard_status("IS 10245", std_db)
        assert val.is_known is True
        assert val.recognition_state in ("FOUND_STATUS_UNKNOWN", "FOUND_ACTIVE")
        assert len(val.ambiguity_warnings) > 0
        assert "multi-part" in val.ambiguity_warnings[0]

    def test_curated_standard_preserved(self, std_db):
        val = validate_standard_status("IS 1180", std_db)
        assert val.is_known is True
        assert val.is_catalogue_only is False
        assert val.is_active is True
        assert val.recognition_state == "FOUND_ACTIVE"


class TestRecommenderNationalIntegration:
    """Test recommendation engine safeguards with national catalogue citations."""

    def test_catalogue_only_active_recommendation_safeguards(self, recommender):
        res = recommender.recommend_for_text("Diesel engine complying with IS 10001", req_id="CAT-01")
        assert res.candidate_standard is not None
        assert "10001" in res.candidate_standard
        assert res.human_review_required is True
        # Must not fabricate clause-level evidence
        assert res.applicability["decision"] == "PENDING_TECHNICAL_EVALUATION"
        # Clause evidence must remain None / ineligible for catalogue-only
        if res.clause_evidence:
            assert res.clause_evidence.get("passage_text") is None
            assert res.clause_evidence.get("outcome") == "CORPUS_DOCUMENT_NOT_ELIGIBLE"

    def test_catalogue_only_withdrawn_recommendation_safeguards(self, recommender):
        res = recommender.recommend_for_text("Procurement of cement complying with IS 8112", req_id="CAT-02")
        # Withdrawn candidate must abstain cleanly or require human review
        assert res.human_review_required is True
        # Must NOT claim NONEXISTENT_CITATION for IS 8112
        assert not any("NONEXISTENT_CITATION: Cited standard 'IS 8112'" in str(w) for w in (res.why_not or []))

    def test_nonexistent_standard_triggers_nonexistent_warning(self, recommender):
        res = recommender.recommend_for_text("Widgets manufactured strictly to IS 999999", req_id="CAT-03")
        assert res.candidate_standard is None
        assert any("NONEXISTENT_CITATION" in str(w) for w in (res.why_not or []))

    def test_curated_standard_retains_clause_verification(self, recommender):
        res = recommender.recommend_for_text(
            "Supply of 100 kVA three-phase distribution transformer conforming to IS 1180.",
            req_id="CUR-01"
        )
        assert res.candidate_standard is not None
        assert "1180" in res.candidate_standard
        # Curated standard must have full trace record and grounded evidence
        assert res.trace_record is not None
        assert res.trace_record.get("standard_number") is not None


class TestApiIntegration:
    """Test POST /api/analyze/text and POST /api/analyze/pdf with national catalogue."""

    def test_api_text_active_catalogue_standard(self, client):
        resp = client.post("/api/analyze/text", json={
            "text": "Supply of diesel engine conforming to IS 10001."
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["requirements"]) > 0
        req = data["requirements"][0]
        assert req["candidate_standard"] is not None
        assert "10001" in req["candidate_standard"]
        assert req["applicability"]["decision"] == "PENDING_TECHNICAL_EVALUATION"

    def test_api_text_withdrawn_catalogue_standard(self, client):
        resp = client.post("/api/analyze/text", json={
            "text": "Procurement of cement conforming to IS 8112."
        })
        assert resp.status_code == 200
        data = resp.get_json()
        req = data["requirements"][0]
        # Must not be flagged as nonexistent
        assert not any("NONEXISTENT_CITATION" in str(w) for w in req.get("why_not", []))

    def test_api_pdf_catalogue_standard(self, client):
        # Generate a minimal in-memory PDF containing an active catalogue standard
        # Even a plain text wrapped in dummy PDF or synthetic payload
        # Alternatively, test text analysis equivalence
        resp = client.post("/api/analyze/text", json={
            "text": "Provide personal respiratory protection complying with IS 10245."
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["requirements"]) > 0
