# Phase 31: Evidence Integrity, Compound Requirement Adjudication & Coverage Reconciliation — Plan

**Phase:** 31  
**Milestone:** National BIS Catalogue Integration & Multi-Package Tender Auditing  
**Status:** In Progress (Plan Phase)  
**Evaluator:** Antigravity AI  
**Repository:** `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Execution Date:** 2026-10-19  

---

## 1. Objectives

1. **Audit Normative Evidence Integrity**:
   - Trace stored document IDs in `corpus.db` to their origin in `scripts/ingest_normative_standards.py`.
   - Distinguish content integrity hashes from external authenticity proofs.
   - Audit `IS 1239 (Part 2)` and `IS 2062` availability; record formal acquisition blockers.
2. **Reconcile Cross-Database Coverage Metrics**:
   - Define exact SQL queries across `bis_catalogue.db`, `standards.db`, and `corpus.db`.
   - Explain why `bis_catalogue.db` has 4 active corpus standards (10,824 gap) while `standards.db` has 7 active corpus standards (73 gap).
   - Update `COVERAGE_GAP_METRICS.json` and generate `PHASE31_EVIDENCE_INTEGRITY_REPORT.md`.
3. **Hardened Compound Requirement Adjudication**:
   - Fix Case A grounding in `src/corpus/retriever.py` to require `support_state == FULLY_SUPPORTED`.
   - Extend `evaluate_requirement_support` to detect out-of-scope physical dimensions (e.g. `5500 mm` for `IS 4984`) and out-of-scope material grades (e.g. `Fe 750` for `IS 1786`).
   - Fix explicit part disambiguation in `src/recommend.py` so explicit citations of `IS 1239 Part 1` strictly prioritize Part 1 over Part 2.
   - Enforce that composite requirements with `human_review_required=True` (due to unverified subcomponents) cannot receive unconditional `CLAUSE_VERIFIED` tier.
4. **Deterministic Testing & Automated Verification**:
   - Add comprehensive tests in `tests/test_phase31_evidence_integrity.py` covering all 8 fixtures.
   - Run `pytest -q` (all 747+ tests passing).
   - Run `npx --prefix frontend vitest run`.
   - Run `npm --prefix frontend run build`.
   - Verify ground-truth checksum: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.
   - Run `graphify update .`.
5. **Documentation & Sign-off**:
   - Create `.planning/phases/31-evidence-integrity/31-UAT.md`.
   - Update `.planning/STATE.md`.

---

## 2. Execution Tasks

### Task 1: Audit Ingested Evidence & Trace Provenance
- Inspect `data/standards/corpus.db` rows against `scripts/ingest_normative_standards.py`.
- Formulate precise findings regarding string-based SHA-256 vs external PDF signatures.
- Formally document the unavailability of full-text source PDFs for `IS 1239 (Part 2)` and `IS 2062`.

### Task 2: Coverage Metric Calculations & Reconciliation
- Audit exact database counts with SQL queries.
- Update `scripts/generate_coverage_gap_report.py` if needed to output Phase 31 metrics.
- Reconcile the discrepancy: raw scrape metadata vs curated standards.

### Task 3: Defect Corrections in `retriever.py` & `recommend.py`
- **Defect 1**: Out-of-scope grades (e.g. `Fe 750` in `IS 1786`) and out-of-scope dimensions (e.g. `5500 mm` in `IS 4984`) incorrectly return `FULLY_SUPPORTED`.
  - *Fix*: In `src/corpus/retriever.py`, add parameter validation for diameter/size limits and steel grades. Return `UNSUPPORTED` or `PARTIALLY_SUPPORTED`.
- **Defect 2**: Explicit clause Case A in `src/corpus/retriever.py` line 379 sets `is_grounded = True` even when `support_state != FULLY_SUPPORTED`.
  - *Fix*: Require `is_grounded = (p.clause_identifier != "CLAUSE_UNKNOWN" and support_state == RequirementEvidenceSupportState.FULLY_SUPPORTED.value)`.
- **Defect 3**: Explicit Part matching: In `src/recommend.py`, when a tender explicitly cites a standard with a Part (e.g. `IS 1239 Part 1`), candidate ranking must prefer the exact part over neighboring parts (e.g. `IS 1239 (Part 2)`).
- **Defect 4**: Compound review leak: If `human_review_required` is True (due to review-required subcomponents), `verification_tier` must not be `CLAUSE_VERIFIED`.

### Task 4: Comprehensive Test Suite
- Write `tests/test_phase31_evidence_integrity.py` covering:
  - 8 core compound fixtures.
  - Grade bounds verification (`Fe 500D` supported vs `Fe 750` unsupported).
  - Dimensional bounds verification (`DN 110 mm` supported vs `5500 mm` unsupported).
  - Explicit Part preference (`IS 1239 Part 1` over Part 2).
  - Withdrawn successor gate (`IS 8112`).
  - Conflicting editions gate (`IS 4984:1995` vs `2016`).

### Task 5: Verification & Deliverables
- Execute full test suite, frontend vitest, frontend build, checksum check, and graphify update.
- Create UAT document and audit report.
- Update `STATE.md`.
