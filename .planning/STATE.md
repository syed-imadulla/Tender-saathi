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
| **12-02** | Multi-Metric Reproducible Evaluation Harness | `src/evaluate.py`, `tests/test_evaluation_metrics.py` | De-conflated metrics: Precision@Coverage, Safe Abstention Rate, Evidence Grounding Score, Sector-Stratified Recall. | Ready |
| **12-03** | Ground-Truth Expansion & Review Gating | `scripts/expand_ground_truth.py`, `tests/test_ground_truth_integrity.py` | Script to propose candidate cases from `tenders/raw/` labeled `MACHINE_PREDICTED`, and an integrity gate preventing synthetic `human_verified: TRUE` flags. | Planned |

---

## Plan 12-01 Execution Summary

- **Ground Truth Extension**: Appended 6 columns (`source_document`, `procurement_sector`, `expected_decision`, `adjudication_status`, `reviewer_role`, `reviewed_at`) preserving 18 core columns and all 20 rows.
- **Defensibility Verification**: 20/20 rows bound to physical PDF documents in `tenders/raw/` with verbatim text matches.
- **Anti-Falsification**: 0 fabricated expert claims. All 20 baseline rows have `human_verified: FALSE`, `adjudication_status: UNVERIFIED_BASELINE`, and empty reviewer fields.
- **Test Suite Health**: 524/524 backend tests passing in 58.74s (100% offline). Frontend build passing.

---

## Next Steps
Run `/gsd-execute-phase 12 12-02` (or execute Plan 12-02: Multi-Metric Reproducible Evaluation Harness).
