# Tender Saathi — Ground Truth Schema & Provenance Audit Report

- **Date**: 2026-10-18
- **Audit Scope**: Phase 12 / Plan 12-01 (Ground-Truth Schema & Provenance Audit)
- **Dataset Path**: `dataset/ground_truth/ground_truth.csv`
- **Total Rows Audited**: 20
- **Column Count**: 24 (18 original + 6 appended)

## 1. Executive Summary

| Metric | Result | Compliance Status |
| :--- | :--- | :--- |
| **Core Columns Preserved** | 18 / 18 original positions intact | PASS |
| **Appended Columns** | 6 columns (`source_document`, `procurement_sector`, `expected_decision`, `adjudication_status`, `reviewer_role`, `reviewed_at`) | PASS |
| **Defensible Source Binding** | 20 / 20 (100.0%) | PASS |
| **Unresolved Provenance** | 0 | NONE |
| **Sector Classifications** | 20 provisional, 0 ungrounded claims | PASS (All explicit `PROVISIONAL:`) |
| **Expert Sign-off Falsification** | 0 fabricated approvals, 0 unbacked `human_verified: TRUE` | PASS (100% UNVERIFIED_BASELINE) |

## 2. Canonical Vocabularies

### `expected_decision`
- `RECOMMEND`: Specific, answerable requirement with applicable Indian Standard(s).
- `ABSTAIN_UNDER_SPECIFIED`: Vague or incomplete requirement lacking critical parameters (e.g., valve without media/pressure).
- `ABSTAIN_AMBIGUOUS`: Conflicting interpretations or indeterminate scope.
- `ABSTAIN_CONFLICTING`: Conflicting standard specifications.
- `REJECT_INELIGIBLE`: Out-of-domain commercial or non-technical requirements.

### `adjudication_status`
- `UNVERIFIED_BASELINE`: Existing legacy baseline cases awaiting formal domain expert panel adjudication.
- `MACHINE_PREDICTED`: Pipeline candidate generation for future review staging.
- `EXPERT_VERIFIED`: Formally reviewed and signed off by qualified domain expert with role and date.

## 3. Case-by-Case Provenance & Audit Log

| ID | Tender | Document | Page (Found/Legacy) | Sector | Expected Decision | Status | Text Match |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `T001-R002` | `T001` | `eProcurement System Government of India2.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T001-R003` | `T001` | `eProcurement System Government of India2.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T001-R004` | `T001` | `eProcurement System Government of India2.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T002-R002` | `T002` | `eProcurement System Government of India3.pdf` | p.1 (orig: p.1) | `PROVISIONAL:MECHANICAL` | `ABSTAIN_UNDER_SPECIFIED` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T002-R003` | `T002` | `eProcurement System Government of India3.pdf` | p.1 (orig: p.1) | `PROVISIONAL:MECHANICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T003-R001` | `T003` | `eProcurement System Government of India4.pdf` | p.1 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T004-R002` | `T004` | `eProcurement System Government of India5.pdf` | p.1 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T004-R005` | `T004` | `eProcurement System Government of India5.pdf` | p.1 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T005-R001` | `T005` | `eProcurement System Government of India6.pdf` | p.2 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T006-R001` | `T006` | `eProcurement System Government of India7.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T007-R003` | `T007` | `eProcurement System Government of India8.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CATERING` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T009-R001` | `T009` | `eProcurement System Government of India10.pdf` | p.1 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T010-R001` | `T010` | `eProcurement System Government of India11.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T011-R001` | `T011` | `eProcurement System Government of India12.pdf` | p.2 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T012-R002` | `T012` | `eProcurement System Government of India13.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T012-R003` | `T012` | `eProcurement System Government of India13.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T013-R002` | `T013` | `eProcurement System Government of India14.pdf` | p.1 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T013-R003` | `T013` | `eProcurement System Government of India14.pdf` | p.1 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T014-R002` | `T014` | `eProcurement System Government of India15.pdf` | p.1 (orig: p.1) | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |
| `T020-R001` | `T020` | `eProcurement System Government of India.pdf` | p.1 (orig: p.1) | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `UNVERIFIED_BASELINE` | `VERIFIED_DEFENSIBLE` |

## 4. Verification Guarantees & Constraints

1. **No Falsification**: All 20 baseline rows maintain `human_verified: FALSE`, `reviewer_role: ""`, and `reviewed_at: ""` until genuine human expert review occurs in Phase 13.
2. **Defensible Evidence**: Every linked PDF physically exists on disk and contains the verbatim requirement text.
3. **Provisional Tagging**: Sector tags are marked `PROVISIONAL:` to distinguish metadata heuristics from certified procurement taxonomy.
4. **Backwards Compatibility**: All legacy consumers querying the 18 core columns via header names or pandas continue uninterrupted.
