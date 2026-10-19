# Phase 29 Execution Plan: End-to-End Validation, IS 456 Integration Investigation & Coverage-Gap Audit

**Phase**: 29 — End-to-End Validation, IS 456 Integration Investigation & Coverage-Gap Audit  
**Dependencies**: Phase 26 (Normative Evidence Ingestion), Phase 27 (Multi-Package Tender Auditing), Phase 28 (Interactive Multi-Package Audit UI)  
**Primary Goal**: Thoroughly validate the real end-to-end tender-analysis pipeline, resolve the demonstrated IS 456 evidence-grounding discrepancy without lowering safety thresholds, establish a deterministic test matrix (E2E-01 to E2E-08), and produce an authoritative, reproducible coverage-gap audit of the national BIS catalogue versus local normative evidence.

---

## Task Breakdown

### Task 1: Resolve the IS 456 Evidence Grounding Discrepancy & Enforce Tier Invariants
- **Files**: `src/corpus/retriever.py`, `src/recommend.py`
- **Objective**:
  - In `src/corpus/retriever.py`, when Case B (lexical/semantic passage search) locates an authentic normative passage from an eligible, extracted corpus document matching the candidate standard and edition, evaluate whether `p.clause_identifier != "CLAUSE_UNKNOWN"` and `support_state == RequirementEvidenceSupportState.FULLY_SUPPORTED.value`.
  - When the passage genuinely and fully supports the requirement parameters (e.g. M25 concrete in IS 456 Clause 8.2 / Table 5 and Clause 6.1 / Table 2), set `is_grounded = True` with exact `clause_identifier` and `passage_sha256`.
  - If evidence support is `UNVERIFIED_COVERAGE`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, or `CONFLICTING`, `is_grounded` must remain `False`.
  - In `src/recommend.py`, ensure `top_clause_ev` propagates `verification_tier = 'CLAUSE_VERIFIED'`, `passage_id`, and `clause_number` cleanly to the API response.
  - Verify that uningested standards (`IS 8329`, `IS 10000`) and administrative requirements (`EMD`) strictly retain `CATALOGUE_DISCOVERED` or `SAFE_ABSTENTION`.

### Task 2: Deterministic End-to-End Test Matrix Implementation
- **Files**: `tests/test_e2e_pipeline_validation.py`
- **Objective**: Implement offline, deterministic tests covering the full test matrix:
  - **E2E-01**: M25 concrete with IS 456 -> `CLAUSE_VERIFIED` with authentic passage ID and Clause 8.2 / 6.1.
  - **E2E-02**: HDPE water pipe with IS 4984 -> `CLAUSE_VERIFIED` if matching parameters (e.g. PN 10, PE 100, DN 110 mm), or `CATALOGUE_DISCOVERED` if parameters unindexed.
  - **E2E-03**: Catalogue-only candidate (e.g. IS 10000 or IS 10245) -> `CATALOGUE_DISCOVERED`, never `CLAUSE_VERIFIED`.
  - **E2E-04**: EMD / GST / Bank Guarantee -> `SAFE_ABSTENTION`, candidate `None`, zero engineering recommendation.
  - **E2E-05**: Underspecified technical requirement -> `REVIEW_REQUIRED` / clarification needed.
  - **E2E-06**: Withdrawn/superseded standard reference (IS 8112 -> IS 269) -> lifecycle warning and active successor recommendation.
  - **E2E-07**: Multi-package tender with Civil, Piping, Electrical, and Administrative scopes -> accurate package breakdown and stable tender-wide findings.
  - **E2E-08**: Industrial-valve procurement citing pipe standard -> applicability gate rejection (`INCOMPATIBLE_APPLICATION`), preventing unsupported match.

### Task 3: Trace and Validate End-to-End Architecture & Serialization Consistency
- **Files**: `api/server.py`, `src/audit.py`, `src/report.py`, `frontend/src/types.ts`
- **Objective**:
  - Audit field alignment across:
    - Backend models (`RequirementRecommendationResult`, `TenderAuditResult`).
    - API responses (`/api/analyze/text`, `/api/analyze/pdf`, `/api/analyze/tender`).
    - Frontend TypeScript types (`Requirement`, `PackageAuditSummary`, `ExecutiveTierSummary`).
  - Ensure `passage_id`, `clause_number`, `edition_year`, and `verification_tier` remain consistent and accessible.
  - Confirm package switching in frontend preserves tender-wide totals.

### Task 4: Reproducible National BIS Catalogue & Evidence Coverage Audit
- **Files**: `scripts/generate_coverage_gap_report.py`, `docs/evaluation/COVERAGE_GAP_METRICS.json`, `docs/evaluation/FULL_BIS_COVERAGE_GAP_REPORT_PHASE29.md`
- **Objective**:
  - Query `data/catalogue/bis_catalogue.db`, `data/standards/standards.db`, and `data/standards/corpus.db`.
  - Calculate exact, verifiable counts:
    1. Total national BIS catalogue records (35,208).
    2. Active catalogue records (10,828).
    3. Withdrawn records (11,340).
    4. Unresolved lifecycle records (13,024 UNKNOWN + 16 SUPERSEDED).
    5. Curated standards in `standards.db` (93).
    6. Standards with locally ingested normative passages in `corpus.db` (4 documents, 15 passages).
    7. Standards eligible for clause-grounded verification.
    8. Catalogue-only candidates requiring technical evaluation.
  - Generate machine-readable JSON: `docs/evaluation/COVERAGE_GAP_METRICS.json`.
  - Generate human-readable Markdown: `docs/evaluation/FULL_BIS_COVERAGE_GAP_REPORT_PHASE29.md`.

### Task 5: Full Verification Suite Execution & Phase Deliverables
- **Commands**:
  - `pytest tests/test_e2e_pipeline_validation.py`
  - `python3 -m pytest -q` (all backend tests passing)
  - `npx --prefix frontend vitest run` (frontend unit tests)
  - `npm --prefix frontend run build` (frontend bundle)
  - `sha256sum dataset/ground_truth/ground_truth.csv` (invariant baseline preserved)
  - `graphify update .` (update knowledge graph)
- **Deliverables**:
  - `.planning/phases/29-end-to-end-validation/29-UAT.md`
  - `.planning/STATE.md` update
