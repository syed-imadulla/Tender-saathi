"""
tests/test_e2e_pipeline_validation.py — Phase 29 End-to-End Deterministic Pipeline Validation

Validates the real end-to-end tender-analysis pipeline across the 8 required deterministic test fixtures:
- E2E-01: M25 concrete with IS 456 (Authentic normative evidence verification)
- E2E-02: HDPE water pipe with IS 4984 (Clause-grounded verification vs unverified parameters)
- E2E-03: Catalogue-only candidate (Candidate discovered from national catalogue without clause verification)
- E2E-04: EMD / GST / Bank guarantee (Commercial condition safe abstention)
- E2E-05: Underspecified technical requirement (Mandatory clarification / review)
- E2E-06: Withdrawn/superseded standard reference (IS 8112 -> lifecycle warning, safe abstention from endorsing withdrawn)
- E2E-07: Multi-package tender with Civil, Piping, and Commercial packages
- E2E-08: Valve procurement intentionally citing pipe standard (Applicability mismatch guard)
"""

import pytest
import json
from api.server import app
from src.recommend import StandardsRecommender
from src.extract import Requirement, extract_packages_and_requirements


@pytest.fixture(scope="module")
def api_client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="module")
def recommender():
    return StandardsRecommender()


# ---------------------------------------------------------------------------
# E2E-01: M25 Concrete with IS 456
# ---------------------------------------------------------------------------

def test_e2e_01_m25_concrete_is456_verified(api_client):
    """
    E2E-01: Verify that M25 design-mix concrete conforming to IS 456 is verified
    against authentic local normative evidence in corpus.db (Clause 8.2 / Table 5 & Clause 6.1).
    """
    payload = {
        "text": "Supply of M25 grade design mix concrete conforming to IS 456."
    }
    resp = api_client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    reqs = data.get("requirements", [])
    assert len(reqs) >= 1
    req = reqs[0]

    # Candidate and verification tier assertions
    assert req.get("candidate_standard") is not None
    assert "456" in req["candidate_standard"]
    assert req.get("verification_tier") == "CLAUSE_VERIFIED"
    assert req.get("passage_id") is not None
    assert req.get("clause_number") in ["8.2", "6.1", "1.1", "5.1"]
    assert int(req.get("edition_year")) == 2000

    # Ensure authentic clause evidence is present
    clause_ev = req.get("clause_evidence")
    assert clause_ev is not None
    assert clause_ev.get("is_grounded") is True
    assert clause_ev.get("document_id") == "DOC-IS-456-2000"
    assert "m25" in clause_ev.get("passage_text", "").lower()


# ---------------------------------------------------------------------------
# E2E-02: HDPE Water Pipe with IS 4984
# ---------------------------------------------------------------------------

def test_e2e_02_hdpe_pipe_is4984_verified(api_client):
    """
    E2E-02: Verify that HDPE pipe with matching parameters (PN 10, PE 100)
    achieves CLAUSE_VERIFIED through authentic passages in DOC-IS-4984-2016.
    """
    payload = {
        "text": "Supply of HDPE pipes for water supply conforming to IS 4984 PN 10 PE 100 DN 110 mm."
    }
    resp = api_client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    reqs = data.get("requirements", [])
    assert len(reqs) >= 1
    req = reqs[0]

    assert req.get("candidate_standard") is not None
    assert "4984" in req["candidate_standard"]
    assert req.get("verification_tier") == "CLAUSE_VERIFIED"
    assert req.get("passage_id") is not None
    assert int(req.get("edition_year")) == 2016

    clause_ev = req.get("clause_evidence")
    assert clause_ev is not None
    assert clause_ev.get("is_grounded") is True
    assert clause_ev.get("document_id") == "DOC-IS-4984-2016"


# ---------------------------------------------------------------------------
# E2E-03: Catalogue-Only Candidate
# ---------------------------------------------------------------------------

def test_e2e_03_catalogue_only_candidate_not_verified(api_client):
    """
    E2E-03: Candidate present in national BIS catalogue metadata but lacking
    local normative passages must remain CATALOGUE_DISCOVERED, never CLAUSE_VERIFIED.
    """
    payload = {
        "text": "Procurement of marine propulsion diesel engines for coastal patrol vessels."
    }
    resp = api_client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    reqs = data.get("requirements", [])
    assert len(reqs) >= 1
    req = reqs[0]

    assert req.get("candidate_standard") is not None
    # Invariant: Must NOT imply clause verification
    assert req.get("verification_tier") != "CLAUSE_VERIFIED"
    assert req.get("verification_tier") == "CATALOGUE_DISCOVERED"
    assert req.get("passage_id") is None
    assert req.get("clause_number") is None
    assert req.get("human_review_required") is True
    assert req.get("clause_evidence", {}).get("outcome") == "CORPUS_DOCUMENT_NOT_ELIGIBLE"


# ---------------------------------------------------------------------------
# E2E-04: Commercial / Administrative Safe Abstention
# ---------------------------------------------------------------------------

def test_e2e_04_commercial_condition_safe_abstention(api_client):
    """
    E2E-04: Non-engineering administrative conditions (EMD, bank guarantee, GST)
    must cleanly abstain without spurious engineering standard recommendations.
    """
    payload = {
        "text": "Bidder must submit Earnest Money Deposit (EMD) of Rs. 2,00,000 as bank guarantee and valid GST registration."
    }
    resp = api_client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    reqs = data.get("requirements", [])
    assert len(reqs) >= 1
    req = reqs[0]

    # Invariant: Safe abstention
    assert req.get("verification_tier") == "SAFE_ABSTENTION"
    assert req.get("candidate_standard") in [None, "NONE", "INSUFFICIENT_INFORMATION"]
    assert req.get("passage_id") is None
    assert req.get("clause_number") is None


# ---------------------------------------------------------------------------
# E2E-05: Underspecified Technical Requirement
# ---------------------------------------------------------------------------

def test_e2e_05_underspecified_technical_requirement(recommender):
    """
    E2E-05: Requirement lacking critical engineering parameters must require
    review / clarification and must not be falsely upgraded to verified.
    """
    req = Requirement(
        requirement_id="REQ-UNDERSPEC",
        requirement_text="Supply and installation of water utility pumps for general fluid transfer.",
        category="product_equipment",
        domain="PUMPS_AND_ROTATING"
    )
    res = recommender.recommend_for_requirement(req)

    # Must require human review or clarification
    assert res.human_review_required is True or res.decision in ["REVIEW_REQUIRED", "INSUFFICIENT_EVIDENCE", "NO_RELIABLE_MATCH"]
    assert res.verification_tier != "CLAUSE_VERIFIED"


# ---------------------------------------------------------------------------
# E2E-06: Withdrawn / Superseded Standard Handling
# ---------------------------------------------------------------------------

def test_e2e_06_withdrawn_standard_successor_handling(api_client):
    """
    E2E-06: Withdrawn standard citation (IS 8112) must trigger lifecycle warnings
    and safe abstention from endorsing withdrawn standards, never silently claim active.
    """
    payload = {
        "text": "Supply of 43 Grade Ordinary Portland Cement conforming to IS 8112 for masonry construction."
    }
    resp = api_client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    reqs = data.get("requirements", [])
    assert len(reqs) >= 1
    req = reqs[0]

    # Invariants: Must NOT silently claim active; human review mandated
    assert req.get("human_review_required") is True
    assert req.get("verification_tier") != "CLAUSE_VERIFIED"
    assert any("8112" in str(s) for s in req.get("explicit_standards_found", []))
    # Must not falsely endorse a withdrawn standard as an autonomous recommendation
    assert req.get("candidate_standard") is None or "269" in str(req.get("candidate_standard"))


# ---------------------------------------------------------------------------
# E2E-07: Multi-Package Tender with Diverse Domains
# ---------------------------------------------------------------------------

def test_e2e_07_multi_package_tender_audit(api_client):
    """
    E2E-07: Multi-package tender containing Civil, Piping, and Commercial scopes
    must produce clean package grouping, exact domain assignment, and stable findings.
    """
    payload = {
        "text": """PACKAGE 1: Civil Works
Supply of M25 grade design mix concrete conforming to IS 456.

PACKAGE 2: Water Supply Piping
High density polyethylene HDPE pipes conforming to IS 4984 PN 10 PE 100.

PACKAGE 3: Commercial Terms
Earnest money deposit of Rs. 1,00,000 shall be submitted as a bank guarantee."""
    }
    resp = api_client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    reqs = data.get("requirements", [])
    assert len(reqs) == 3

    # Package 1: Civil Works
    pkg1 = next(r for r in reqs if r.get("package_id") == "PKG-01")
    assert pkg1.get("domain") == "CIVIL_AND_STRUCTURAL"
    assert pkg1.get("verification_tier") == "CLAUSE_VERIFIED"
    assert "456" in (pkg1.get("candidate_standard") or "")

    # Package 2: Piping Works
    pkg2 = next(r for r in reqs if r.get("package_id") == "PKG-02")
    assert pkg2.get("domain") == "PIPES_AND_FITTINGS"
    assert pkg2.get("verification_tier") == "CLAUSE_VERIFIED"
    assert "4984" in (pkg2.get("candidate_standard") or "")

    # Package 3: Commercial Terms
    pkg3 = next(r for r in reqs if r.get("package_id") == "PKG-03")
    assert pkg3.get("domain") == "GENERAL_AND_ADMINISTRATIVE"
    assert pkg3.get("verification_tier") == "SAFE_ABSTENTION"
    assert pkg3.get("candidate_standard") in [None, "NONE", "INSUFFICIENT_INFORMATION"]


# ---------------------------------------------------------------------------
# E2E-08: Industrial Valve with Intentionally Mismatched Pipe Standard
# ---------------------------------------------------------------------------

def test_e2e_08_valve_procurement_mismatched_pipe_standard_rejected(recommender):
    """
    E2E-08: Tender specifying valve procurement citing pipe standard IS 4984
    must trigger applicability rejection / conflict guard, preventing unsupported match.
    """
    req = Requirement(
        requirement_id="REQ-VALVE-CONFLICT",
        requirement_text="Supply of double flanged cast iron sluice valves for isolation conforming to IS 4984.",
        category="product_equipment",
        domain="VALVES_AND_FLOW"
    )
    res = recommender.recommend_for_requirement(req)

    # Invariant: IS 4984 (pipe standard) must NOT be verified as matching a valve requirement
    if res.candidate_standard and "4984" in res.candidate_standard:
        assert res.verification_tier != "CLAUSE_VERIFIED"
        assert res.human_review_required is True
    else:
        # Correctly rejected or abstained
        assert res.verification_tier in ["SAFE_ABSTENTION", "CATALOGUE_DISCOVERED"]
