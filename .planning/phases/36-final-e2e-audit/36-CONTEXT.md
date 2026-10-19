# Phase 36 Context: Final End-to-End Recommendation Audit & SIH Demo Hardening

**Phase:** 36 (`36-final-e2e-audit`)  
**Repository Branch:** `main`  
**Execution Context:** Evidence-first, safety-critical end-to-end user journey validation and SIH demo hardening.  
**Baseline State:** 788/788 backend pytest tests passing, 12/12 frontend vitest tests passing, Vite production build clean, ground truth SHA-256 strictly preserved (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).

---

## 1. Locked Decisions & Core Objectives

1. **User Journey Verification (10 Scenarios)**:
   - Provide deterministic automated validation for the 10 core user journeys:
     1. Valid engineering tender with supported requirements (e.g. CPVC pipe -> IS 15778).
     2. Multi-requirement tender (e.g. civil pipes + electrical cables + substation transformers).
     3. Catalogue-discovered standard lacking normative corpus passages (e.g. IS 10245 breathing apparatus -> `CATALOGUE_DISCOVERED`, `human_review_required=True`).
     4. Withdrawn or superseded standard (e.g. IS 10611 superseded by IS 14846, or withdrawn IS 4985:1988 -> active successor warning).
     5. Underspecified technical requirement (e.g. pumps without head/flow -> `AMBIGUOUS_UNDER_SPECIFIED`).
     6. Conflicting specifications (e.g. HDPE for 250°C superheated steam, or IS 694 for 33 kV -> `APPLICATION_CONFLICT`).
     7. Commercial / non-standardized requirement (e.g. mobilization advance, EMD, stationery -> `SAFE_ABSTENTION`, `candidate_standard=None`).
     8. Normative cross-reference traversal (e.g. IS 456 referencing IS 1786 rebar or IS 1239 Part 2 referencing Part 1).
     9. Digital PDF tender upload using standard extraction fixtures (`/api/analyze/pdf`).
     10. Mixed tender containing supported engineering clauses and unsupported commercial/administrative clauses.

2. **Honest Standards Coverage Reporting**:
   - Zero inflation of standards coverage or synthetic evidence.
   - Audit and document exact database metrics:
     - 35,208 total records in `bis_catalogue.db` (23,510 Active, 11,340 Withdrawn, 342 Unknown, 16 Superseded).
     - 23,510 active records indexed in FTS5 `catalogue_search_index.db`.
     - 98 curated standards in `standards.db`.
     - 13 standards with authentic statutory gazette passages in `corpus.db` (53 verified passages).
     - Only those 13 eligible for `CLAUSE_VERIFIED`; all other 35,195 standards restricted to `CATALOGUE_DISCOVERED` or `SAFE_ABSTENTION`.
     - Explicit documentation of blockers: `IS 2062` and `IS 1538` remain restricted on official BIS portals.

3. **Safety Invariants**:
   - Non-elevation invariant: Traversed cross-references cannot be promoted to primary recommendations without direct requirement matching.
   - Ingestion trust boundary: Prompt injection attempts and instruction overrides are neutralized and flagged for mandatory human review.
   - Ground-truth checksum immutability: `dataset/ground_truth/ground_truth.csv` must remain bit-for-bit unchanged (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).

4. **SIH Demonstration Experience Hardening**:
   - Verify upload, processing, results display, evidence inspection, and report export end-to-end.
   - Ensure clear distinction in UI between `CLAUSE_VERIFIED` (statutory passage evidence), `CATALOGUE_DISCOVERED` (national catalogue entry), and `SAFE_ABSTENTION`.
   - Provide clean empty states and graceful error handling on invalid / unparseable inputs.

---

## 2. Deliverables Checklist

- [ ] `.planning/phases/36-final-e2e-audit/36-CONTEXT.md` (this file)
- [ ] `.planning/phases/36-final-e2e-audit/36-PLAN.md`
- [ ] `tests/test_phase36_e2e_user_journeys.py` (comprehensive 10-journey test suite)
- [ ] Hardened UI/API edge cases in `api/server.py`, `frontend/src/pages/Results.tsx`, and `frontend/src/components/EvidenceDrawer.tsx`
- [ ] Full test execution (788+ backend pytest, 12+ frontend vitest, Vite production build)
- [ ] `docs/evaluation/PHASE36_FINAL_E2E_AUDIT.md` (comprehensive audit, P0-P3 gap classification, SIH demo Go/No-Go verdict)
- [ ] `.planning/phases/36-final-e2e-audit/36-UAT.md`
- [ ] Updated `.planning/STATE.md` and `ROADMAP.md`
- [ ] Knowledge graph synchronization via `graphify update .`
