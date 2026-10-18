# Tender Saathi — Recommendation Traceability Audit Findings & Action Checklist

**Audit Scope**: End-to-end Decision Path & Evidence Grounding Verification  
**Repository**: Tender Saathi (`syed-imadulla/Tender-saathi`)  
**Status**: Completed  
**Companion Report**: [`docs/development/RECOMMENDATION_TRACEABILITY_AUDIT.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/development/RECOMMENDATION_TRACEABILITY_AUDIT.md)  
**Date**: October 2026  

---

## 1. Verified Core Architectural Safeguards (Confirmed Intact)

The following safety mechanisms were inspected line-by-line and verified with existing passing tests:

- [x] **SAFEGUARD-01: Candidate vs. Evidence Parity Invariant**
  - *Location*: [`src/critic.py:184-210`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/critic.py#L184-L210), [`src/recommend.py:920-930`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/recommend.py#L920-L930)
  - *Verified*: If candidate standard != evidence standard, result is immediately downgraded to `GROUNDING_FAILED`, score capped at 0.10, and `human_review_required = True`.
  - *Test*: `tests/test_milestone10_evidence_consistency.py` (all tests passing).

- [x] **SAFEGUARD-02: Gate 4 Trust Gate (High Retrieval + Weak Evidence Capping)**
  - *Location*: [`src/critic.py:412-416`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/critic.py#L412-L416)
  - *Verified*: High dense/vector similarity cannot override weak or missing evidence. Decision is capped at `REVIEW_REQUIRED` and high confidence is stripped.
  - *Test*: `tests/test_milestone3_critic.py`.

- [x] **SAFEGUARD-03: Pre-Citation Operational Envelope Validation**
  - *Location*: [`src/recommend.py:414-434`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/recommend.py#L414-L434)
  - *Verified*: Standards explicitly cited in tender text must pass `ApplicabilityGate`. Domain envelope violations strip the bonus (score drops to 0.10) and force human review.
  - *Test*: `tests/test_phase8_decision_safety.py`.

- [x] **SAFEGUARD-04: Deterministic Abstention on Parameter Gaps**
  - *Location*: [`src/recommend.py:586-678`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/recommend.py#L586-L678)
  - *Verified*: If ambiguity state is `INCOMPLETE`, `AMBIGUOUS`, or `CONFLICTING`, `candidate_standard` is forced to `None`, score to 0.0, and `human_review_required = True`.
  - *Test*: `tests/test_ambiguity.py`.

- [x] **SAFEGUARD-05: Non-Engineering Commodity Semantic Filtering**
  - *Location*: [`src/extract.py:280-320`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/extract.py#L280-L320), [`src/decomposition.py:95-120`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/decomposition.py#L95-L120)
  - *Verified*: Financial audits, catering, legal consulting, and administrative services are intercepted before retrieval, returning `NO_RELIABLE_MATCH`.
  - *Test*: `tests/test_phase8_decision_safety.py`.

- [x] **SAFEGUARD-06: Strict Separation of Related Standards from Applicable Standards**
  - *Location*: [`src/graph.py:150-185`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/graph.py#L150-L185), [`frontend/src/pages/Results.tsx:106-129`](file:///home/syed-imadulla/Desktop/Tender_Saathi/frontend/src/pages/Results.tsx#L106-L129)
  - *Verified*: Graph neighbors (depth-1 related standards) are strictly rendered in a dedicated "Related Standards" section with the UX warning banner: *"Related ≠ Applicable"*.

---

## 2. Confirmed Defects & Architecture Inconsistencies

### [P1] AUDIT-01: Composite Requirement Subcomponent Review Masking
- **Type**: Confirmed Design Risk
- **Location**: [`src/recommend.py:240-295`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/recommend.py#L240-L295) (`_evaluate_component_recommendations`)
- **Actual Behavior**: The top-level recommendation selects `top_rec` from the first/highest subcomponent. Secondary subcomponents requiring review or with low confidence do not propagate their review requirement to the parent recommendation decision.
- **Expected Behavior**: If any subcomponent requires human review, the parent composite requirement should reflect `decision = 'REVIEW_REQUIRED'` and `human_review_required = True`.
- **Proposed Fix**: Add an aggregation check in `_evaluate_component_recommendations` to roll up review requirements.
- **Status**: Ready for fix implementation (pending approval).

### [P2] AUDIT-02: Frontend Recommended List Includes `REVIEW_REQUIRED` Items
- **Type**: Confirmed UI Filtering Defect
- **Location**: [`frontend/src/pages/Results.tsx:61-67`](file:///home/syed-imadulla/Desktop/Tender_Saathi/frontend/src/pages/Results.tsx#L61-L67)
- **Actual Behavior**: `recommendedList` filters on `req.candidate_standard && req.status === 'ACTIVE'`, without checking `req.decision === 'RECOMMEND'`. Items with `decision === 'REVIEW_REQUIRED'` appear in both "Recommended Standards" and "Items Requiring Review".
- **Expected Behavior**: "Recommended Standards" should strictly contain items where `req.decision === 'RECOMMEND'` and `!req.human_review_required`.
- **Proposed Fix**: Update filter condition to explicitly require `req.decision === 'RECOMMEND' && !req.human_review_required`.
- **Status**: Ready for fix implementation (pending approval).

### [P2] AUDIT-04: Review Status Enum Drift in API Error Fallbacks
- **Type**: Confirmed Inconsistency
- **Location**: [`api/server.py:260-295`](file:///home/syed-imadulla/Desktop/Tender_Saathi/api/server.py#L260-L295) (`_normalize_result`)
- **Actual Behavior**: Fallback and exception branches populate `review_status = "PENDING"`, while `src/audit.py` uses `"NEEDS_REVIEW"` or `"FLAGGED_FOR_REVIEW"`.
- **Expected Behavior**: Consistent enum strings across `src/audit.py`, `api/server.py`, and `frontend/src/types.ts`.
- **Proposed Fix**: Standardize on `ReviewStatus.NEEDS_REVIEW.value` ("NEEDS_REVIEW").
- **Status**: Ready for fix implementation (pending approval).

---

## 3. Potential Risks & Improvement Opportunities

### [P2] AUDIT-03: Pre-Citation Successor Auto-Bonus (Score 1.0)
- **Type**: Potential Operational Risk
- **Location**: [`src/recommend.py:374-388`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/recommend.py#L374-L388)
- **Description**: An active successor replacing an obsolete citation automatically inherits an initial score of `1.0`. Although validated by `ApplicabilityGate`, it starts with an artificial advantage over organic retrieval candidates before critic 5D evaluation.
- **Proposed Fix**: Use calculated semantic similarity or cap initial successor score at 0.85.

### [P3] AUDIT-05: Fixed Conflict Delta Threshold (0.05) in ConflictRegistry
- **Type**: Improvement Opportunity
- **Location**: [`src/ambiguity.py:322-348`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/ambiguity.py#L322-L348)
- **Description**: A static score difference threshold of 0.05 between top candidates flags `CONFLICTING`. Two close candidates from the same standard family (e.g. `IS 456` Part 1 vs Part 2) might trigger unnecessary domain conflicts.
- **Proposed Fix**: Weight delta threshold by cross-domain semantic distance.

---

## 4. Action Checklist & Regression Tests to Add

- [ ] **Task 1: Implement Parent-Level Subcomponent Rollup (AUDIT-01)**
  - File: [`src/recommend.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/recommend.py)
  - Test to add: `tests/test_decomposition.py::test_composite_subcomponent_review_rollup`

- [ ] **Task 2: Fix Frontend Recommended Tab Filtering (AUDIT-02)**
  - File: [`frontend/src/pages/Results.tsx`](file:///home/syed-imadulla/Desktop/Tender_Saathi/frontend/src/pages/Results.tsx)
  - Test to add: Vitest assertion in `frontend/src/pages/Results.test.tsx` ensuring `recommendedList` excludes `decision === 'REVIEW_REQUIRED'`

- [ ] **Task 3: Harmonize Review Status Enums (AUDIT-04)**
  - File: [`api/server.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/api/server.py)
  - Test to add: `tests/test_p7b_api_ui_contract.py::test_review_status_enum_consistency`

- [ ] **Task 4: Calibrate Successor Retrieval Weight (AUDIT-03)**
  - File: [`src/recommend.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/recommend.py)
  - Test to add: `tests/test_bis_change_detection.py::test_successor_operational_envelope_narrowing`

- [ ] **Task 5: Refine ConflictRegistry Delta Calibration (AUDIT-05)**
  - File: [`src/ambiguity.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/ambiguity.py)
  - Test to add: `tests/test_ambiguity_calibration.py::test_same_family_candidates_avoid_conflict`
