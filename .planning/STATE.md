# Tender Saathi — Active Planning State

**Active Milestone**: Milestone: Benchmark Transparency, Ground-Truth Quality, and Source Provenance  
**Current Phase**: Phase 12 (`12-benchmark-transparency`)  
**Phase Position**: Planning Complete — Ready for Review & Implementation Approval  
**Working Directory**: `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Git Head**: `898a6e8` (`main`)

---

## Current Situation

1. **Phase 1 Remediation**: Complete. AUDIT-01 (subcomponent review rollup), AUDIT-02 (frontend list filtering), and AUDIT-04 (API `ReviewStatus` enum consistency) were verified and committed.
2. **Phase 2A Deterministic Testing**: Complete. `tests/conftest.py` enforces session network isolation and HuggingFace offline mode. `test_05` and `test_05b` pass deterministically. Test suite runtime dropped from 3m 41s to 58s with 516/516 tests passing offline.
3. **Phase 12 (Phase 2B) Planning**: Detailed requirements and three implementation plans (`12-01-PLAN.md`, `12-02-PLAN.md`, `12-03-PLAN.md`) created for benchmark transparency, evaluation harness de-conflation, and provenance tracking.

---

## Active Phase Overview: Phase 12

| Plan ID | Title | Scope & Target Files | Deliverable | Status |
|---|---|---|---|---|
| **12-01** | Ground-Truth Schema & Provenance Audit | `dataset/ground_truth/ground_truth.csv`, `scripts/audit_ground_truth_provenance.py`, `tests/test_ground_truth_integrity.py` | Extended 24-column CSV schema, 20/20 defensible provenance verified, 0 unbacked human approvals, 8/8 integrity tests passing. | **Complete** |
| **12-02** | Multi-Metric Reproducible Evaluation Harness | `src/evaluate.py`, `scripts/evaluate_milestone12.py`, `tests/test_evaluation_metrics.py` | Decoupled metrics: Top-1 89.5% (17/19), Coverage 60.0%, Selective Risk 13.3%, Under-Spec Abstain 100.0%, Evidence disclosure, 8/8 synthetic tests passing. | **Complete** |
| **12-03** | Ground-Truth Expansion & Review Gating | `scripts/expand_ground_truth.py`, `tests/test_ground_truth_integrity.py`, `docs/data/GROUND_TRUTH_GOVERNANCE.md` | Staging pipeline for candidate extraction (`candidates_staging.csv`), CI governance gate (`GATE-01`), 11/11 integrity tests passing. | **Complete** |

---

## Phase 12 Milestone Completion Summary

- **Phase Status**: **100% Complete** (All 3 plans executed and verified).
- **Plan 12-01 (Schema & Provenance)**: Appended 6 non-breaking columns (`source_document`, `procurement_sector`, `expected_decision`, `adjudication_status`, `reviewer_role`, `reviewed_at`) preserving 18 core columns and all 20 rows. 20/20 cases verified defensible against physical PDFs in `tenders/raw/`.
- **Plan 12-02 (Evaluation De-conflation)**: Decoupled positive standard retrieval from selective abstention. Answerable Top-1 accuracy is 89.5% (17/19), Coverage is 60.0%, Selective Risk is 13.3%, and Under-Specification Abstention Recall is 100.0%. Evidence grounding limitations formally disclosed.
- **Plan 12-03 (Expansion & Governance Gate)**: Built `scripts/expand_ground_truth.py` outputting staged candidates to `candidates_staging.csv` with strict `MACHINE_PREDICTED` tagging. Installed automated CI governance gate in `tests/test_ground_truth_integrity.py` (`test_09`, `test_10`, `test_11`) preventing any unverified human verification claims.
- **Test Suite Health**: 535/535 backend tests passing in 58.10s (100% offline). Frontend build passes in 1.02s.

---

## Next Steps

Phase 12 is complete. Proceed to **Phase 13: Expert Ground-Truth Adjudication & Calibration** or review milestone summary via:
```bash
/gsd-complete-milestone
```
