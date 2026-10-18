# Ground Truth Benchmark Provenance & Schema Audit

## Overview

This document records the provenance audit and schema extension of [`dataset/ground_truth/ground_truth.csv`](file:///home/syed-imadulla/Desktop/Tender_Saathi/dataset/ground_truth/ground_truth.csv) conducted under **Phase 12 / Plan 12-01**.

The benchmark dataset provides a frozen reference set of 20 real tender requirements extracted from Government of India Central Public Procurement Portal (CPPP) documents.

## Schema Definition

The schema comprises exactly 24 columns: 18 legacy core columns preserved in their original order, followed by 6 appended provenance and adjudication columns.

### 18 Core Columns (Preserved In Original Order)
1. `tender_id`: CPPP tender identifier (`T001`–`T020`).
2. `requirement_id`: Requirement clause identifier (e.g. `T001-R002`).
3. `requirement_text`: Verbatim text snippet from tender scope.
4. `category`: Engineering category (`material`, `product_equipment`, `installation_execution`, `general_specification`).
5. `source_page`: Legacy page index.
6. `explicit_standard`: Any standard explicitly cited in the tender notice.
7. `applicable_standard`: Bureau of Indian Standards (BIS) code(s).
8. `standard_title`: Official title in the BIS catalogue.
9. `standard_status`: Legal status (`Active`, `Superseded`).
10. `verification_outcome`: Benchmark categorization outcome (`STANDARD_MISSING`, `NEEDS_EXPERT_VERIFICATION`).
11. `verification_method`: Ground truth source (`BIS_CATALOGUE`, `BIS_METADATA`, `UNVERIFIED`).
12. `evidence_source`: Sectional committee or QCO regulation.
13. `evidence_reference`: Scope clause or regulatory citation.
14. `evidence_snippet`: Relevant excerpt from BIS specification.
15. `reasoning`: Technical justification for standard applicability.
16. `confidence`: Ground truth confidence rating (`High`, `Medium`, `Low`).
17. `human_verified`: Boolean review flag (`FALSE` on all unadjudicated rows).
18. `reviewer_notes`: Scope boundaries, QCO citations, or engineering notes.

### 6 Appended Provenance & Adjudication Columns
19. `source_document`: Relative path to raw tender document (e.g. `tenders/raw/eProcurement System Government of India2.pdf`).
20. `procurement_sector`: Domain sector tag. Explicitly prefixed with `PROVISIONAL:` (e.g. `PROVISIONAL:CIVIL_WORKS`) when inferred from tender metadata rather than expert taxonomy.
21. `expected_decision`: Target decision in canonical vocabulary (`RECOMMEND`, `ABSTAIN_UNDER_SPECIFIED`, `ABSTAIN_AMBIGUOUS`, `ABSTAIN_CONFLICTING`, `REJECT_INELIGIBLE`).
22. `adjudication_status`: Lifecycle status (`UNVERIFIED_BASELINE`, `MACHINE_PREDICTED`, `EXPERT_VERIFIED`).
23. `reviewer_role`: Domain expert professional qualification. Empty for unadjudicated rows.
24. `reviewed_at`: ISO 8601 adjudication timestamp. Empty for unadjudicated rows.

## Provenance Audit Results (Plan 12-01)

An automated audit was conducted using [`scripts/audit_ground_truth_provenance.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/scripts/audit_ground_truth_provenance.py).

- **Total Rows**: 20
- **Verified Defensible**: 20 / 20 (100%)
  - Every linked document exists in `tenders/raw/`.
  - Every requirement text was located verbatim in the extracted page text of that document.
  - Actual document pages: 18 on page 1, 2 on page 2 (`T005-R001`, `T011-R001`).
- **Unresolved Rows**: 0
- **Anti-Falsification Enforcement**:
  - `human_verified` is `FALSE` across all 20 rows.
  - `adjudication_status` is `UNVERIFIED_BASELINE` across all 20 rows.
  - `reviewer_role` and `reviewed_at` are empty across all 20 rows.
  - No synthetic expert credentials, signatures, or dates were introduced.

Detailed case-by-case mappings are documented in [`reports/evaluation/ground_truth_provenance_audit.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/reports/evaluation/ground_truth_provenance_audit.md).
Automated regression tests are maintained in [`tests/test_ground_truth_integrity.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/tests/test_ground_truth_integrity.py).
