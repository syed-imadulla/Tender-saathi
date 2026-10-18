# Phase 12: Benchmark Transparency, Ground-Truth Quality, and Source Provenance (CONTEXT.md)

**Phase**: 12  
**Baseline**: Phase 1 Remediation (`898a6e8`) + Phase 2A Deterministic Offline Tests (`conftest.py`)  
**Context Type**: Evaluation Audit, Schema Design & Benchmark Integrity

---

## 1. Background & Problem Statement

In hackathon development, evaluation metrics are often reported as static numbers (e.g., "90% Top-1 Accuracy, 100% Ambiguity Recall") without rigorous data provenance. Phase 1 Production-Readiness Audit and Phase 2A revealed several key vulnerabilities in Tender Saathi's benchmark infrastructure:

1. **Unverified Benchmark Baseline**: All 20 rows in `dataset/ground_truth/ground_truth.csv` have `human_verified: FALSE` and `STANDARD_MISSING` in the raw CSV, indicating they were generated during early catalogue construction rather than signed off by certified procurement engineers.
2. **Metric Conflation in Abstention**: In `src/evaluate.py`, when a requirement is under-specified (e.g. T002-R002 "Valve Replacement") and the recommender correctly flags human review, it is counted as a `TOP1_HIT`! This artificially inflates retrieval accuracy by blending selective abstention with positive standard retrieval.
3. **Hardcoded Negative Controls**: Out-of-domain distractor rejection (e.g., NEG-001 crane rail track vs. valves) is hardcoded inside `src/evaluate.py` rather than managed in a transparent, versioned dataset.
4. **Missing Evidence & Sector Auditing**: The benchmark checks if the predicted standard number matches the ground truth standard string, but does not verify whether the cited clause, normative scope, or Quality Control Order (QCO) was correctly surfaced.

---

## 2. Technical Decisions & Scope Boundaries

### Decision 1: Non-Breaking Ground-Truth Schema Extension
- Retain all 18 existing columns in `dataset/ground_truth/ground_truth.csv` to ensure zero breakage of existing pandas/csv readers.
- Append 6 optional metadata columns:
  - `source_document`: File path relative to repository (e.g., `tenders/raw/eProcurement System Government of India3.pdf`).
  - `procurement_sector`: Categorical tag (`CPWD_CIVIL`, `ELECTRICAL_SUBSTATION`, `NUCLEAR_PROCESS_PIPING`, `SANITARY_SEWERAGE`, `FOOD_COMMISSARY`, `SPORTS_INFRASTRUCTURE`).
  - `expected_decision`: Explicit target decision (`RECOMMEND`, `REVIEW_REQUIRED`, `SAFE_ABSTENTION`).
  - `adjudication_status`: Lifecycle status of the ground truth row (`UNADJUDICATED`, `MACHINE_PREDICTED`, `EXPERT_VERIFIED`).
  - `reviewer_role`: Professional role (`UNASSIGNED`, `CPWD_EXECUTIVE_ENGINEER`, `BIS_OFFICER`, etc.).
  - `reviewed_at`: ISO 8601 timestamp of verified adjudication or empty.

### Decision 2: Multi-Dimensional Evaluation Metrics
- **Retrieval Accuracy on Answerable Cases**: Accuracy strictly on requirements where a definitive BIS standard exists.
- **Selective Classification Coverage & Risk**: How often the system abstains on ambiguous/incomplete requirements vs. risks making an ungrounded recommendation.
- **Evidence Grounding Match Rate**: Percentage of recommendations where the returned scope/clause aligns with the ground truth evidence reference.
- **Sector Coverage**: Evaluation sliced across the 6 procurement sectors.

### Decision 3: Machine vs. Expert Label Segregation
- The initial 20 rows remain explicitly marked as `adjudication_status: UNADJUDICATED` and `human_verified: FALSE`.
- When new candidate cases are extracted from raw tenders in `tenders/raw/`, they are labeled `adjudication_status: MACHINE_PREDICTED`.
- Only actual domain expert review can transition a row to `EXPERT_VERIFIED` and `human_verified: TRUE`.
