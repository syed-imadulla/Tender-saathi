# Phase 35 UAT: Demonstration Readiness, Negative-Control Evaluation & Catalogue Hygiene

**Phase:** 35  
**Date:** October 19, 2026  
**Status:** COMPLETE (All Criteria Verified)  
**Ground-Truth Checksum:** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`  

---

## Acceptance Criteria & Verification Matrix

| ID | Criterion | Target Requirement | Verification Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **UAT-35-01** | Interactive Traversal API | Endpoints `/api/standards/<id>/traversal` and `/api/graph/traverse` return structured cross-references with bounded depth ($\le 2$), origin clause, and target status. | Tested via `tests/test_phase35_demonstration_readiness.py::test_02_traversal_api_depth_1_and_2`. Verified depth 1 and 2 traversals for IS 456 and IS 7098. | **PASSED** |
| **UAT-35-02** | Non-Elevation Safety Invariant | Traversed references must never be elevated to primary candidate or claim false passage grounding without direct clause support. | Tested via `tests/test_phase35_demonstration_readiness.py::test_03_traversal_non_elevation_invariant` and `frontend/src/pages/StandardsGraph.test.ts`. | **PASSED** |
| **UAT-35-03** | Frontend Traversal UI | Standards graph drawer and evidence drawer display hop badges, citing clauses, verbatim snippets, and interactive graph pivot. | Verified via frontend Vitest tests and production build. Tested interactively in StandardsGraph and EvidenceDrawer. | **PASSED** |
| **UAT-35-04** | Negative-Control Suite | $\ge 10$ negative-control probes covering commercial, vague, conflicting, and foreign specs in `dataset/evaluation/phase35_negative_controls.json`. | 12 probes implemented across 6 distinct risk categories. Verified in `tests/test_phase35_negative_controls.py`. | **PASSED** |
| **UAT-35-05** | Zero False Recommendations | Zero `RECOMMEND` decisions on negative-control probes without engineering review. | 0 false recommendations across all 12 negative controls. Verified in `tests/test_phase35_negative_controls.py::test_02_negative_controls_zero_false_recommendations`. | **PASSED** |
| **UAT-35-06** | Catalogue Lifecycle Hygiene | Deterministically reconcile the 13,024 `UNKNOWN` catalogue records where raw portal data had shifted `(Active)` into `iso_equivalence`. | Reconciled 12,682 records to `ACTIVE` with full provenance; active standards increased to 23,510; `UNKNOWN` records reduced to 342. Verified via `tests/test_phase35_demonstration_readiness.py::test_04_catalogue_hygiene_post_reconciliation_counts`. | **PASSED** |
| **UAT-35-07** | FTS5 Index Regeneration | Rebuild full-text search index `data/catalogue/catalogue_search_index.db` with reconciled active standards. | 23,510 active records indexed in 0.30s. Verified via `scripts/reconcile_catalogue_lifecycle.py`. | **PASSED** |
| **UAT-35-08** | Authentic Normative Standards | Ingest authentic statutory public gazette extracts for `IS 694 : 2010` and `IS 1180 (Part 1) : 2014` into corpus and standards DBs. | Ingested into `corpus.db` (13 documents, 53 passages). Verified via `tests/test_phase35_demonstration_readiness.py::test_05_authentic_standards_ingested_in_corpus`. | **PASSED** |
| **UAT-35-09** | Ground-Truth Immutability | `dataset/ground_truth/ground_truth.csv` must remain bit-for-bit identical (`8bcc9bc5...`). | SHA-256 confirmed invariant: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`. | **PASSED** |
| **UAT-35-10** | Comprehensive Test Suite | 100% pass rate on full backend and frontend test suites. | Backend: 788 / 788 tests passed (0 failures). Frontend: 12 / 12 Vitest tests passed. Production build clean. | **PASSED** |

---

## Sign-Off Summary
All 10 Phase 35 acceptance criteria have been verified with complete test coverage, preserved provenance, zero fabricated claims, and an invariant evaluation benchmark checksum.
