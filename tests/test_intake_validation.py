"""
tests/test_intake_validation.py — Unit Tests for Source Document & Under-Specified Intake Validation

Verifies:
1. SourceDocumentRecord URL, hash, and physical file validation.
2. UnderSpecifiedIntakeRecord 6-dimension schema and detailed narrative enforcement.
3. Anti-falsification boundary: Rejects synthetic expert claims without recognized roles.
4. CorpusInventoryGenerator produces complete 41-case inventory with valid cohort mappings.
5. TenderSplitter near-duplicate text leakage detection across Train/Val/Test splits.
"""

import os
import pytest
from src.intake import (
    SourceDocumentRecord,
    UnderSpecifiedIntakeRecord,
    CorpusInventoryGenerator,
    UNDER_SPECIFIED_DIMENSIONS,
    APPROVED_ROLES
)
from src.calibrate import TenderSplitter


def test_source_document_record_validation():
    # Valid existing file
    valid_rec = SourceDocumentRecord(
        document_id="DOC-CPPP-2026-ISMD-921565",
        tender_id="T001",
        source_url="https://eprocure.gov.in/eprocure/app?component=DirectLink",
        retrieval_date_utc="2026-09-04",
        file_path="tenders/raw/eProcurement System Government of India2.pdf",
        file_sha256="",
        procurement_authority="IIT ISM Dhanbad",
        work_category="Works",
        licensing_or_access_notes="Public tender notice downloaded from CPPP portal under RTI guidelines"
    )
    assert valid_rec.validate() is True
    assert valid_rec.is_physically_available is True
    assert len(valid_rec.file_sha256) == 64

    # Invalid URL and missing hash on non-existent file
    invalid_rec = SourceDocumentRecord(
        document_id="DOC-INVALID",
        tender_id="T999",
        source_url="ftp://invalid-url",
        retrieval_date_utc="invalid-date",
        file_path="nonexistent/path/file.pdf",
        file_sha256="",
        procurement_authority="Unknown",
        work_category="Works",
        licensing_or_access_notes=""
    )
    assert invalid_rec.validate() is False
    assert any("source_url" in err for err in invalid_rec.validation_errors)
    assert any("retrieval_date_utc" in err for err in invalid_rec.validation_errors)
    assert any("file_sha256" in err for err in invalid_rec.validation_errors)


def test_under_specified_record_validation():
    # Valid under-specified record
    valid_rec = UnderSpecifiedIntakeRecord(
        case_id="T002-R002",
        tender_id="T002",
        source_document="tenders/raw/eProcurement System Government of India3.pdf",
        source_page=1,
        raw_excerpt_text="Valve Replacement in Heavy Water Plant chemical services",
        procurement_sector="PROVISIONAL:MECHANICAL",
        procurement_object="valve",
        missing_dimensions=["dimensions_or_sizes", "electrical_or_mechanical_ratings", "material_grade_or_composition"],
        missing_details_narrative="Missing nominal bore (DN), pressure class rating (150/300), and fluid service metallurgy (bronze vs cast iron vs steel).",
        candidate_competing_standards=["IS 778", "IS 14846", "IS 13095"],
        is_expert_adjudicated=False
    )
    assert valid_rec.validate() is True

    # Invalid missing dimension and too short narrative
    invalid_rec = UnderSpecifiedIntakeRecord(
        case_id="INVALID-CASE",
        tender_id="T002",
        source_document="tenders/raw/eProcurement System Government of India3.pdf",
        source_page=1,
        raw_excerpt_text="Valve",
        procurement_sector="PROVISIONAL:MECHANICAL",
        procurement_object="valve",
        missing_dimensions=["random_unknown_dimension"],
        missing_details_narrative="Too short",
        is_expert_adjudicated=False
    )
    assert invalid_rec.validate() is False
    assert any("Invalid missing dimension" in err for err in invalid_rec.validation_errors)
    assert any("missing_details_narrative" in err for err in invalid_rec.validation_errors)


def test_anti_falsification_role_boundary():
    # Attempting to declare expert verified with unapproved role
    forged_rec = UnderSpecifiedIntakeRecord(
        case_id="FORGED-001",
        tender_id="T002",
        source_document="tenders/raw/eProcurement System Government of India3.pdf",
        source_page=1,
        raw_excerpt_text="Supply of low-voltage distribution panels without breaking capacity",
        procurement_sector="PROVISIONAL:ELECTRICAL",
        procurement_object="switchgear",
        missing_dimensions=["electrical_or_mechanical_ratings"],
        missing_details_narrative="Lacks kA breaking capacity and IP protection ingress rating.",
        is_expert_adjudicated=True,
        adjudicator_role="UNACCREDITED_INTERN", # Unapproved role
        adjudicated_at="2026-10-18T10:00:00Z"
    )
    assert forged_rec.validate() is False
    assert any("adjudicator_role" in err for err in forged_rec.validation_errors)

    # Valid expert sign-off
    valid_expert_rec = UnderSpecifiedIntakeRecord(
        case_id="VALID-EXPERT-001",
        tender_id="T002",
        source_document="tenders/raw/eProcurement System Government of India3.pdf",
        source_page=1,
        raw_excerpt_text="Supply of low-voltage distribution panels without breaking capacity",
        procurement_sector="PROVISIONAL:ELECTRICAL",
        procurement_object="switchgear",
        missing_dimensions=["electrical_or_mechanical_ratings"],
        missing_details_narrative="Lacks kA breaking capacity and IP protection ingress rating.",
        is_expert_adjudicated=True,
        adjudicator_role="CPWD_EXECUTIVE_ENGINEER",
        adjudicated_at="2026-10-18T10:00:00Z"
    )
    assert valid_expert_rec.validate() is True


def test_corpus_inventory_generation():
    inv = CorpusInventoryGenerator.generate_full_inventory()
    summary = inv["summary"]
    cases = inv["cases"]

    assert summary["total_inventory_cases"] == 41
    assert summary["expert_verified_cases"] == 0 # Safety Boundary Enforced
    assert summary["adjudication_readiness_status"] == "NOT_READY_FOR_CALIBRATION"
    assert len(summary["adjudication_blockers"]) >= 4

    # Check cases integrity
    case_ids = {c["case_id"] for c in cases}
    assert "T001-R002" in case_ids
    assert "T002-R002" in case_ids
    assert "PROV-ELEC-NEG002" in case_ids

    # Verify physical file linking
    t001_r002 = next(c for c in cases if c["case_id"] == "T001-R002")
    assert t001_r002["is_source_physically_available"] is True
    assert len(t001_r002["source_document_sha256"]) == 64


def test_tender_splitter_near_duplicate_leakage_warning():
    # Create artificial cases where two different tenders contain overlapping requirement text
    leaky_cases = [
        {"tender_id": "TENDER_A", "requirement_id": "A1", "requirement_text": "Supply and installation of 25mm hubless cast iron soil piping systems with mechanical elastomeric couplings"},
        {"tender_id": "TENDER_B", "requirement_id": "B1", "requirement_text": "Supply and installation of 25mm hubless cast iron soil piping systems with mechanical elastomeric couplings"},
        {"tender_id": "TENDER_C", "requirement_id": "C1", "requirement_text": "Supply of pressed ceramic tiles for toilet walls"},
    ]
    split_res = TenderSplitter.split(leaky_cases, train_ratio=0.34, val_ratio=0.33, test_ratio=0.33, seed=42)
    audit = split_res["leakage_audit"]
    # Even though tenders are disjoint, the text is a duplicate across splits
    if audit["train_tenders"] and (audit["val_tenders"] or audit["test_tenders"]):
        assert audit["is_tender_disjoint"] is True
        # If A and B fall into different splits, warning is triggered
        if ("TENDER_A" in audit["train_tenders"] and "TENDER_B" in audit["val_tenders"]) or \
           ("TENDER_A" in audit["train_tenders"] and "TENDER_B" in audit["test_tenders"]):
            assert len(audit["text_leakage_warnings"]) > 0
            assert audit["is_leakage_free"] is False
