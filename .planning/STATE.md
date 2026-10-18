# Tender Saathi — Active Planning State

**Active Milestone**: Milestone: Expert Ground-Truth Adjudication & Evaluation Calibration  
**Current Phase**: Phase 19 (`19-safe-clause-evidence-integration`)  
**Phase Position**: Clause Retrieval Integrated, 13 Tests Passing, Full Suite 617/617 Passing, Audit Complete — Phase Completed  
**Working Directory**: `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Git Head**: `ea95ba4` (`main`)

---

## Current Situation

1. **Phase 1 Remediation**: Complete. AUDIT-01, AUDIT-02, and AUDIT-04 verified.
2. **Phase 2A Deterministic Testing**: Complete. 100% offline test suite passing in 58s.
3. **Phase 12 Benchmark Transparency**: Complete. Extended schema to 24 columns, audited 20/20 physical PDF provenances, built multi-metric evaluation harness, and established staging candidate pipeline (`candidates_staging.csv`).
4. **Phase 13 Metric Audit & Adjudication Framework**: Completed. Resolved metrics defects, built adjudication packet generator, produced 40 draft packets in `reports/adjudication_packets/packets/`, and established two-party consensus ingestion CLI.
5. **Negative-Control Integrity Audit**: Completed in `docs/evaluation/POST_NEGATIVE_CONTROL_INTEGRITY_AUDIT.md`. Fixed NEG-004 structural exclusion, analyzed NEG-002 cable distractor, and confirmed 0/5 false recommendation rate on negative controls.
6. **Phase 14 Calibration Readiness & Protocol Design**: Completed in `docs/evaluation/PHASE14_CALIBRATION_READINESS.md`.
   - Built offline calibration runner and leakage-safe tender-level grouped splitter in `src/calibrate.py`.
   - Added unit test suite in `tests/test_calibration_harness.py` (6 tests).
   - Verdict: NOT READY FOR CALIBRATION due to zero expert-verified cases and sample size limits.
7. **Phase 15 Real-World Evaluation Corpus & Expert-Adjudication Readiness**: Completed in `docs/evaluation/PHASE15_CORPUS_READINESS.md`.
   - Verified 41-case catalogued inventory in `reports/corpus_inventory.json` with 40/41 physical PDF links.
   - Codified public tender intake and BIS metadata protocol in `docs/data/REAL_SOURCE_INTAKE_GUIDE.md`.
   - Enforced 6-dimension schema and anti-falsification validation in `src/intake.py`.
   - Enhanced `TenderSplitter` in `src/calibrate.py` with near-duplicate text leakage detection.
   - Regenerated 41 reviewer packets in `reports/adjudication_packets/packets/`.
8. **Phase 16 Evidence Traceability & Recommendation Verification**: Completed in `docs/evaluation/PHASE16_EVIDENCE_TRACEABILITY_AUDIT.md`.
   - Built deterministic `TraceableEvidenceValidator` and `TraceableEvidenceRecord` in `src/traceability.py`.
   - Connected recommendation engine in `src/recommend.py` to stored catalogue scopes with SHA-256 content hashes.
   - Exposed trace records through `/recommend` and `/analyze` in `api/server.py`.
   - Updated frontend TypeScript models and added Section 14 Traceability UI in `EvidenceDrawer.tsx`.
   - Added offline regression test suite in `tests/test_evidence_traceability.py` (10 tests).
9. **Phase 17 Evidence Integrity and Verification Semantics Audit**: Completed in `docs/evaluation/PHASE17_EVIDENCE_INTEGRITY_AUDIT.md`.
   - Conducted independent audit of verification semantics across catalogue, recommender, API, and frontend.
   - Discovered and fixed SEC-17-01: False universal review requirement where `top_rec` lacked `critic_result`, properly reconciling 12 clean autonomous recommendations (`SUPPORTING_EVIDENCE_AVAILABLE`), 5 review-required cases, and 3 negative control abstentions.
   - Fixed SEC-17-02 (whitespace/trivial passage false positive) and canonicalized SHA-256 whitespace hashing.
   - Fixed SEC-17-03 (source URL scheme vs documentary citation overloading) and SEC-17-04 (edition slug resolution for multi-edition standards).
   - Enhanced frontend UI labels in Section 14 to clarify local database scope vs official live authentication.
   - Added 11 adversarial offline regression tests in `tests/test_evidence_integrity_audit.py`.
   - Full offline suite passing: 589/589 tests in 57s. Frontend build passing in 1.03s.
   - Preserved active ground-truth SHA-256 (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).
   - Verdict: **GO** for normative full-text standard ingestion.
10. **Phase 18 Controlled Normative Standards Corpus Ingestion**: Completed in `docs/evaluation/PHASE18_CORPUS_INGESTION_AUDIT.md`.
   - Designed and implemented full-text standards ingestion pipeline in `src/corpus/` (`manifest.py`, `extractor.py`, `chunker.py`, `storage.py`, `retriever.py`, `semantics.py`).
   - Established versioned JSON manifest (`CorpusManifest`) and SQLite full-text storage (`CorpusStorage`) in `data/standards/corpus.db`.
   - Built deterministic layout-preserving extractor with PyMuPDF/pypdf fallback, empty/scanned document detection (`OCR_REQUIRED`), replacement character checks (`QUALITY_FAILED`), and table warnings.
   - Built clause-aware chunker with strict page/edition isolation, structural clause parsing, and explicit `CLAUSE_UNKNOWN` fallback without semantic guessing.
   - Codified 7 distinct verification states in `src/corpus/semantics.py` with strict transition boundaries.
   - Connected clause verification into `TraceableEvidenceValidator` in `src/traceability.py` with zero backward regressions.
   - Added comprehensive offline test suite in `tests/test_corpus_ingestion.py` covering all 15 acceptance criteria (15/15 passed).
   - Added CLI runner `scripts/ingest_pilot_corpus.py` and evaluation harness `scripts/evaluate_phase18_ingestion.py`.
   - Full test suite passing: 604/604 tests in 60s. Frontend build passing in 1.09s.
   - Preserved active ground-truth SHA-256 (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).
11. **Phase 19 Safe Clause-Level Evidence Integration**: Completed in `docs/evaluation/PHASE19_CLAUSE_INTEGRATION_AUDIT.md`.
   - Safely integrated `src/corpus/retriever.py` into `StandardsRecommender` (`src/recommend.py`), `TraceableEvidenceValidator` (`src/traceability.py`), REST API (`api/server.py`), and frontend UI (`EvidenceDrawer.tsx`).
   - Enforced 5 distinct evidence outcomes (`CLAUSE_EVIDENCE_FOUND`, `CLAUSE_EVIDENCE_NOT_FOUND`, `CORPUS_NOT_AVAILABLE`, `CORPUS_DOCUMENT_NOT_ELIGIBLE`, `CORPUS_LOOKUP_ERROR`).
   - Preserved exact candidate generation and ranking behavior (0 / 25 ranking or decision changes on benchmark).
   - Preserved all anti-falsification verification boundaries: `is_official_source_authenticated = False` and `is_human_verified = False` across all automated retrieval pathways.
   - Added 13 deterministic offline integration tests in `tests/test_clause_evidence_integration.py` (13/13 passed).
   - Full backend test suite passing: 617/617 tests in 59.64s. Frontend build passing in 974ms.
   - Preserved active ground-truth SHA-256 (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).

---

## Active Phase Overview: Phase 19

| Plan ID | Title | Scope & Target Files | Deliverable | Status |
|---|---|---|---|---|
| **19-INTEG** | Safe Clause-Level Evidence Integration | `src/corpus/semantics.py`, `src/corpus/storage.py`, `src/corpus/retriever.py`, `src/traceability.py`, `src/recommend.py`, `api/server.py`, `frontend/src/types.ts`, `frontend/src/components/EvidenceDrawer.tsx`, `tests/test_clause_evidence_integration.py`, `docs/evaluation/PHASE19_CLAUSE_INTEGRATION_AUDIT.md` | Clause retrieval integration, 5-outcome semantics, boundary preservation, 13 integration tests, frontend evidence drawer card, evaluation audit report. | **Complete** |

---

## Next Steps (Human Boundary)

1. Qualified external domain engineers (CPWD, BIS, MES) review the 41 packets in `reports/adjudication_packets/packets/`.
2. Controlled local intake of authorized full normative standards PDFs into `data/standards/corpus.db` for target procurement domains (Phase 20).


