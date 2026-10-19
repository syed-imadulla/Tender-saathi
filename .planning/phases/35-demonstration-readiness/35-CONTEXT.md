# Phase 35: Demonstration Readiness, Negative-Control Evaluation & Catalogue Hygiene — Context

**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Date:** 2026-10-19  

---

## 1. Phase Background & Audit Precedents

In the Phase 34 Production Readiness & Coverage Audit ([`PHASE34_PRODUCTION_READINESS_AUDIT.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/evaluation/PHASE34_PRODUCTION_READINESS_AUDIT.md)), four key operational gaps were identified for demonstration and production readiness:

1. **Traversal Visibility:** The backend `StandardsGraph.traverse_cross_references` method traverses grounded normative citations, bounds depth ($\le 2$), and prevents cycles, but the frontend (`StandardsGraph.tsx` and `Results.tsx`) lacked an interactive visualization panel to surface the step-by-step traversal journey to users and evaluators.
2. **Negative-Control Evaluation Rigor:** The frozen ground-truth baseline (`dataset/ground_truth/ground_truth.csv`) contained only 1 negative control (`ABSTAIN_UNDER_SPECIFIED`), preventing adequate measurement of false-positive recommendations on commercial clauses, vague commodities, or unstandardized technologies.
3. **National BIS Catalogue Status Hygiene:** In `data/catalogue/bis_catalogue.db`, 13,024 records had status `UNKNOWN`. Audit investigation revealed that for 12,682 of these records, the raw portal scraping column shifted the status `(Active)` into the `iso_equivalence` column.
4. **Normative Corpus Expansion:** Expanding from 11 standards to include high-frequency electrical procurement standards (`IS 694 : 2010` PVC cables and `IS 1180 (Part 1) : 2014` distribution transformers) with authentic public safety code gazettes under statutory licensing.

---

## 2. Invariants & Guardrails

- **Zero Fabrication:** Passages, clause IDs, pages, and URLs must come strictly from authentic Indian Public Safety Codes published in the Gazette of India.
- **Ground-Truth Benchmark Immutability:** `dataset/ground_truth/ground_truth.csv` with SHA-256 `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` remains strictly read-only and unmutated. New negative-control test fixtures must be stored separately in `dataset/evaluation/phase35_negative_controls.json`.
- **Catalogue Classification Provenance:** Only records with explicit raw evidence of `(Active)` in `iso_equivalence` are reconciled. The remaining 342 records without explicit status evidence strictly remain `UNKNOWN`.
- **Non-Elevation Safety Invariant:** Traversed cross-references must never elevate a standard to `CLAUSE_VERIFIED` unless independent clause evidence exists in `corpus.db`.
