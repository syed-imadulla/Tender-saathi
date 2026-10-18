# Tender Saathi — Active Planning State

**Active Milestone**: Milestone: Expert Ground-Truth Adjudication & Evaluation Calibration  
**Current Phase**: Phase 17 (`17-evidence-integrity-verification-semantics-audit`)  
**Phase Position**: Verification Semantics Clarified, Defect Reconciled, Adversarial Suite Added — Phase Completed  
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

---

## Active Phase Overview: Phase 17

| Plan ID | Title | Scope & Target Files | Deliverable | Status |
|---|---|---|---|---|
| **17-AUDIT** | Evidence Integrity & Verification Semantics Audit | `src/traceability.py`, `src/recommend.py`, `frontend/src/components/EvidenceDrawer.tsx`, `frontend/src/types.ts`, `tests/test_evidence_integrity_audit.py`, `docs/evaluation/PHASE17_EVIDENCE_INTEGRITY_AUDIT.md` | Verification claim semantics, defect remediation, adversarial regression tests, reconciled benchmark metrics, audit report. | **Complete** |

---

## Next Steps (Human Boundary)

1. Qualified external domain engineers (CPWD, BIS, MES) review the 41 packets in `reports/adjudication_packets/packets/`.
2. Secure two-party consensus on at least 5 real under-specified requirements to satisfy the abstention threshold calibration gate.
3. Ingest signed packets via `python3 scripts/ingest_adjudication.py --promote`.
4. Ingest full-text normative standards text into `data/standards/corpus/` to unlock clause-level grounding verification.


