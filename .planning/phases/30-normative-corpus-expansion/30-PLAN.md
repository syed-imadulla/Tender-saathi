# Phase 30 Plan: Prioritized Normative Corpus Expansion & Evidence Integrity

**Phase:** 30  
**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Execution Date:** 2026-10-19  

---

## 1. Plan Overview

Phase 30 systematically expands the local normative evidence corpus from 4 documents / 15 passages to 8 documents / 31 passages, prioritizing high-impact standards in Indian public procurement:
1. `IS 383 : 2016` (Coarse and Fine Aggregate for Concrete) — CED 2, Active in BIS catalogue.
2. `IS 269 : 2015` (Ordinary Portland Cement 33, 43, 53 Grade) — CED 2, Active in BIS catalogue, successor to withdrawn IS 8112.
3. `IS 1786 : 2008` (High Strength Deformed Steel Bars / TMT Fe 415/500/500D) — CED 54, Active in curated metadata, Steel QCO gazette.
4. `IS 1239 (Part 1) : 2004` (Steel Tubes / GI Water Supply Pipes) — CED 54, Steel Tubes QCO gazette, cited in 3 GT tenders.

---

## 2. Detailed Task Breakdown

### Task 1: Ingestion Script Implementation (`scripts/ingest_normative_standards.py`)
- Define `CorpusDocumentRecord` and operative `ClausePassage` definitions for:
  - `DOC-IS-383-2016`: Clause 1.1 (Scope), Clause 4.1/4.2 (Classification), Clause 5.1/5.2 (Physical/Chemical requirements), Clause 6.2 / Table 4 (Fine Aggregate Grading Zones I-IV).
  - `DOC-IS-269-2015`: Clause 1.1 (Scope & Consolidation), Clause 5.1 (Chemical requirements), Clause 6.1 / Table 2 (Compressive Strength across 33, 43, 53 grades), Clause 6.2 (Setting Time & Soundness).
  - `DOC-IS-1786-2008`: Clause 1.1 (Scope), Clause 4.1 (Steel Manufacture), Clause 5.1 (Grades Fe 415, 500, 500D, 550, 600), Clause 8.1 / Table 3 (Mechanical Properties & Seismic Elongation).
  - `DOC-IS-1239-Part-1-2004`: Clause 1.1 (Scope), Clause 5.1 (Steel Grade & Tensile Strength), Clause 8.1 / Table 1 (Light, Medium, Heavy dimensions & galvanization), Clause 9.1 (Hydrostatic Test 5.0 MPa).
- Persist documents and passages into `data/standards/corpus.db`.
- Synchronize curated standards in `data/standards/standards.db`.
- Register inter-standard relationships in `data/standards/relationships.json` (`IS 456` -> `IS 383`, `IS 456` -> `IS 269`, `IS 456` -> `IS 1786`, `IS 8112` -> `IS 269`).
- Execute ingestion idempotently.

### Task 2: Re-indexing & Retrieval Integration
- Rebuild BM25 search index and semantic embeddings for `standards.db` so new standards are fully discoverable.
- Verify that `ClauseRetriever` in `src/corpus/retriever.py` retrieves the newly ingested passages by standard number, edition, and clause identifier.
- Verify that compound requirements (e.g. M25 concrete with Fe 500D TMT rebars and Zone II sand) can retrieve multi-standard clause evidence.

### Task 3: Deterministic Test Suite (`tests/test_phase30_corpus_expansion.py`)
- Create test file covering:
  - Document integrity & licensing status in `corpus.db` for all 4 new standards.
  - Clause retrieval & parameter grounding (`Fe 500D` in IS 1786, `Zone II` in IS 383, `43 Grade` in IS 269, `Class Medium GI` in IS 1239).
  - Full pipeline verification (`StandardsRecommender` & `POST /api/analyze/text`) producing `CLAUSE_VERIFIED` with authentic passage IDs.
  - Negative/adversarial controls: Mismatched parameters (e.g., Fe 700 rebar or non-existent grading zone) safely abstain or request review.
  - Regression check: Existing standards (`IS 456`, `IS 4984`, `IS 1489 (Part 1)`, `IS 8112`) continue passing without deviation.

### Task 4: Reconciled Coverage-Gap Audit Artifacts
- Run `scripts/generate_coverage_gap_report.py` to record exact before-and-after metrics:
  - Corpus documents: 4 -> 8.
  - Normative passages: 15 -> 31.
  - Reconciled catalogue coverage.
- Write `docs/evaluation/PHASE30_CORPUS_EXPANSION_REPORT.md` and update `docs/evaluation/COVERAGE_GAP_METRICS.json`.

### Task 5: Full Verification Commands & State Update
- Run pytest suite: `python3 -m pytest tests/test_phase30_corpus_expansion.py`
- Run full backend suite: `python3 -m pytest -q` (all 733+ tests must pass)
- Run frontend vitest: `npx --prefix frontend vitest run`
- Run frontend build: `npm --prefix frontend run build`
- Verify ground-truth checksum: `sha256sum dataset/ground_truth/ground_truth.csv`
- Update knowledge graph: `graphify update .`
- Generate `.planning/phases/30-normative-corpus-expansion/30-UAT.md` and update `.planning/STATE.md`.

---

## 3. Invariants & Acceptance Gates
- **Zero Clause Fabrication:** Verbatim statutory public gazette extracts only.
- **Deterministic & Offline:** No network requests.
- **Ground Truth Baseline:** `dataset/ground_truth/ground_truth.csv` remains bit-for-bit identical (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).
