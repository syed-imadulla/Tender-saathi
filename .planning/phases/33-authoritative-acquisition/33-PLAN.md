# Phase 33: Authoritative BIS Document Acquisition, Ingestion & Evidence-Grounded Cross-Reference Traversal — Plan

**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Date:** 2026-10-19  

---

## Plan Structure

### Task 1: Audit & Source Acquisition Validation
- Audit current baseline across `bis_catalogue.db`, `standards.db`, `corpus.db`, and `relationships.json`.
- Validate authenticity and accessibility of public gazette extracts for `IS 1239 (Part 2) : 2011`, `IS 14846 : 2000`, and `IS 800 : 2007`.
- Record document metadata, source URLs, licensing status (`STATUTORY_PUBLIC_GAZETTE`), and compute SHA-256 integrity hashes.

### Task 2: Safe, Idempotent Document & Passage Ingestion
- Extend `scripts/ingest_normative_standards.py` to ingest:
  - `DOC-IS-1239-Part-2-2011`: Scope (Cl 1.1), Material (Cl 4.1), Testing (Cl 8.1), Dimensions (Cl 7.1).
  - `DOC-IS-14846-2000`: Scope (Cl 1.1), Ratings (Cl 4.1), Materials (Cl 6.1 / Table 1), Testing (Cl 10.1 / Table 5).
  - `DOC-IS-800-2007`: Scope (Cl 1.1), Structural Steel (Cl 2.2), Section Classification (Cl 3.7 / Table 2).
- Update `data/standards/standards.db` with verified metadata and committees (CED 54, CED 3, CED 7).
- Update `data/standards/relationships.json` and `standard_relationships` with verified normative references.
- Verify idempotency: running ingestion repeatedly must never produce duplicate documents or duplicate passages.

### Task 3: Evidence-Grounded Cross-Reference Traversal
- Create or enhance `CrossReferenceTraverser` (in `src/graph.py` / `src/dependencies.py`):
  - Traversal rooted at `(start_standard, grounded_clause)`.
  - Extract normative references from both `corpus_passages` and `standard_relationships`.
  - Cycle detection and depth bounding (`max_depth=1` default, up to `max_depth=2`).
  - Classify relationship types (`NORMATIVE_REFERENCE`, `TEST_METHOD`, `CODE_OF_PRACTICE`, `SUPERSEDES`).
  - Check lifecycle status of target standards (alert on `WITHDRAWN` or `SUPERSEDED`).
  - Relevance filtering against requirement context.
  - Preserve originating standard, originating clause, citation text, and provenance.
  - Enforce safety invariant: graph relationship alone never elevates a standard to `CLAUSE_VERIFIED`.

### Task 4: Regression Tests & Verification
- Create `tests/test_phase33_authoritative_acquisition.py` testing:
  - Idempotent ingestion of the 3 new standards.
  - Document and passage schema validity.
  - Cross-reference traversal from grounded clauses (e.g. `IS 456 Cl 5.1`, `IS 800 Cl 2.2`, `IS 14846 Cl 6.1`).
  - Cycle prevention (e.g. `IS 269` <-> `IS 8112`).
  - Depth bound limits.
  - Withdrawn dependency lifecycle warning (e.g. `IS 800` referencing `IS 2062:2011`).
  - Rejection of synthetic elevation to `CLAUSE_VERIFIED` on graph edge alone.
- Run complete test verification:
  - `pytest tests/test_phase33_authoritative_acquisition.py -v`
  - `pytest -q` (full backend test suite)
  - `npx --prefix frontend vitest run`
  - `npm --prefix frontend run build`
  - `sha256sum dataset/ground_truth/ground_truth.csv`
  - `graphify update .`

### Task 5: Reporting & Planning State Updates
- Create `docs/evaluation/PHASE33_AUTHORITATIVE_ACQUISITION_REPORT.md`.
- Create `.planning/phases/33-authoritative-acquisition/33-UAT.md`.
- Update `.planning/STATE.md`.
