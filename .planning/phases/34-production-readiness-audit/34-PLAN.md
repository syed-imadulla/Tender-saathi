# Phase 34: Production Readiness & Coverage Audit — Plan

**Phase:** Phase 34 (`34-production-readiness-audit`)  
**Objective:** Comprehensive read-first audit of Tender Saathi post-Phase 33, evaluating end-to-end functionality, standards coverage, safety safeguards, evaluation benchmark quality, actual product tests, and delivering a prioritized gap report (P0-P3).

---

## Plan Structure

### Task 1: Complete Pipeline & User Journey Trace
- Audit the end-to-end user journey across all functional layers:
  1. Intake layer (`src/intake.py`, `src/extract.py`, `api/ingestion/`).
  2. Requirement decomposition (`src/decompose.py`).
  3. BIS catalogue search & hybrid candidate retrieval (`src/catalogue/search.py`, `src/bm25_search.py`, `src/semantic_search.py`, `src/retrieval.py`).
  4. Applicability evaluation & boundary checking (`src/applicability.py`).
  5. Evidence verification against normative corpus (`src/corpus/retriever.py`, `src/corpus/storage.py`).
  6. Ambiguity evaluation & discretionary specification gating (`src/ambiguity.py`).
  7. Cross-requirement conflict detection (`src/precedence/conflict_engine.py`, `src/critic.py`).
  8. Cross-reference traversal (`src/graph.py`, `src/dependencies.py`).
  9. Human review audit trail & report generation (`src/audit.py`, `src/report.py`, `api/server.py`, `frontend/src/`).
- Document what is genuinely working end-to-end, what is partially integrated, and where manual human steps are required.

### Task 2: Standards Coverage & Tier Distribution Verification
- Extract and verify exact metrics directly from active SQLite databases:
  1. National BIS Catalogue: Total records and distribution across `ACTIVE`, `WITHDRAWN`, `UNKNOWN`, `SUPERSEDED` statuses in `data/catalogue/bis_catalogue.db`.
  2. Searchable catalogue records: Count and index state in `data/catalogue/catalogue_search_index.db` (FTS5).
  3. Curated standards repository: Total records and status distribution in `data/standards/standards.db`.
  4. Authentic normative passage corpus: Document count, edition years, publication details, and passage distribution across standards in `data/standards/corpus.db`.
  5. Verification tier capability breakdown: Exactly which standards qualify for `CLAUSE_VERIFIED`, which for `CATALOGUE_DISCOVERED`, and which require `SAFE_ABSTENTION`.
  6. Document known acquisition blockers (e.g., paywalled/restricted standards like `IS 2062`, `IS 1538`).

### Task 3: Reliability, Safety & Edge State Audit
- Inspect safeguarding mechanisms against critical procurement failure modes:
  1. Ambiguity detection and calibration for underspecified requirements.
  2. Multi-part standard disambiguation (e.g. `IS 1239 Part 1` vs `Part 2`, `IS 1489 Part 1` vs `Part 2`).
  3. Withdrawn and superseded standards handling, active replacement routing, and warning clarity.
  4. Defensive behavior when encountering 13,024 `UNKNOWN` lifecycle catalogue records.
  5. Dimension ceiling and boundary enforcement (pressure ratings, pipe diameters, voltage classes).
  6. Compound requirement handling (multi-component specification isolation).
  7. Cross-reference traversal safety: depth bounds (max depth 2), cycle detection, non-elevation invariant.
  8. Discretionary specification guard: Stage 1.5 enforcement on vague site engineer discretion clauses.
  9. Abstention behavior on commercial, non-technical, or out-of-scope clauses.

### Task 4: Evaluation Benchmark & Ground-Truth Quality Audit
- Audit the ground-truth benchmark and evaluation methodology:
  1. Benchmark scale: 20 requirements in `dataset/ground_truth/ground_truth.csv`.
  2. Ground-truth label provenance: verify values of `human_verified` and `adjudication_status`.
  3. Sector categorization: review `PROVISIONAL:` taxonomy tags.
  4. Negative controls: verify proportion of negative control requirements and safe abstention cases.
  5. Evaluation metrics vs genuine recommendation quality: distinction between retrieval precision and true clause-level validity.
  6. Ground-truth checksum verification: ensure SHA-256 remains strictly `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.

### Task 5: Live Product Testing Execution & Verification
- Execute live tests and record verified execution metrics:
  1. Full backend test suite (`pytest -q`): 778 tests.
  2. Targeted end-to-end and Phase 33 regression suite: 27 tests.
  3. Frontend test suite (`vitest run`): 9 tests.
  4. Frontend production bundle build (`tsc && vite build`).
  5. API contract and UI state alignment verification.

### Task 6: Deliver Prioritized Gap Report & Roadmap
- Compile comprehensive audit report into `docs/evaluation/PHASE34_PRODUCTION_READINESS_AUDIT.md`.
- Categorize every identified gap into P0, P1, P2, and P3 with:
  - Specific evidence from code/data/tests.
  - Procurement & operational impact.
  - Proposed architectural / code fix.
  - Prerequisites and dependencies.
  - Concrete acceptance criteria.
- Produce `34-UAT.md` and update `.planning/STATE.md`.
- Present clear summary distinguishing completed, partially completed, blocked, and pending work, with a recommended Phase 35 focus.
