# Phase 26 UAT Report: Targeted Normative Evidence Ingestion

**Phase**: 26 — Targeted Normative Evidence Ingestion  
**Status**: VERIFIED & PASSING  
**Execution Date**: 2026-10-19  
**Full Backend Test Suite**: 717 passed, 0 failed (100% pass rate in 144.55s)  
**Targeted Ingestion Test Suite**: 9 passed, 0 failed in 6.08s (`tests/test_targeted_normative_ingestion.py`)  
**Frontend Production Build**: Clean build in 1.85s (`npm run build` in `frontend/`)  
**Ground Truth Invariant**: SHA-256 `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (bit-for-bit unaltered)  

---

## 1. Executive Summary & Objective

In Phase 25, Tender Saathi unlocked discovery across the entire National BIS Catalogue (35,208 records, 10,828 active Indian Standards) via offline FTS5 indexing. While national catalogue candidates could be discovered, they were constrained to `PENDING_TECHNICAL_EVALUATION` with `human_review_required = True` due to the complete absence of local clause text and technical parameters.

**Phase 26 Objective**: Expand clause-grounded technical verification for a high-value batch of BIS standards previously discoverable only through metadata, while maintaining strict lawful extraction practices, zero clause fabrication, and deterministic verification safeguards.

---

## 2. Ingested Standards Inventory & Provenance

All normative excerpts were extracted under fair use from lawful, public BIS gazettes and technical gazette publications. Only normative scope clauses, characteristic design parameters, ratings, and test methods were extracted; full copyrighted text was never hoarded or scraped.

| Standard Identifier | Title | Edition / Year | Lifecycle Status | Ingested Passages | Key Technical Parameters Extracted | Authoritative Provenance |
|---|---|---|---|---|---|---|
| **IS 456 : 2000** | Plain and Reinforced Concrete - Code of Practice | 4th Revision, 2000 (Reaffirmed 2021) | `Active` | 4 passages | Characteristic compressive strength ($f_{ck}$): M10–M80; Table 2 concrete grades; Table 5 minimum cement & max w/c ratio for mild to extreme exposures; Section 5 structural design limits. | BIS Gazette & Code of Practice (CED 2) |
| **IS 4984 : 2016** | Polyethylene Pipes for Water Supply - Specification | 5th Revision, 2016 (Reaffirmed 2021) | `Active` | 4 passages | Pressure ratings: PN 2 to PN 16; Material grades PE 63, PE 80, PE 100; Outside diameters DN 16 mm to 1000 mm; Hydrostatic pressure test clause 8.1. | BIS Specification (CED 50) |
| **IS 1489 (Part 1) : 2015** | Portland Pozzolana Cement - Specification - Part 1: Fly Ash Based | 4th Revision, 2015 (Reaffirmed 2020) | `Active` | 4 passages | Fly ash content: 15% to 35% by mass; Fineness: $\ge 300\text{ m}^2/\text{kg}$; Soundness: Le-Chatelier $\le 10\text{ mm}$, Autoclave $\le 0.8\%$; Compressive strength $\ge 16\text{ MPa}$ (72h), $\ge 22\text{ MPa}$ (168h), $\ge 33\text{ MPa}$ (672h). | BIS Specification (CED 2) |
| **IS 8112 : 2013** | 43 Grade Ordinary Portland Cement - Specification | 2nd Revision, 2013 | `Withdrawn` (Superseded) | 3 passages | Formal withdrawal record; Superseded by composite standard **IS 269 : 2015**; Active successor validation links; Supersedence safety warnings. | BIS Gazette Notification (CED 2) |

---

## 3. Before vs After Coverage Metrics

| Dimension | Before Phase 26 | After Phase 26 | Net Change |
|---|---|---|---|
| **Curated Standards in Local Database (`standards.db`)** | 90 standards | **93 standards** | +3 standards (+3.3%) |
| **Corpus Database Documents (`corpus.db`)** | 46 documents | **50 documents** | +4 documents |
| **Corpus Database Passages (`corpus.db`)** | 1,023 passages | **1,038 passages** | +15 normative passages |
| **National Catalogue Searchable Index (`catalogue_search_index.db`)** | 10,828 standards | 10,828 standards | Unchanged (Preserved) |
| **Standards with Full Clause-Grounded Verification** | 90 standards | **93 standards** | +3 standards |
| **Candidate Identity & Grounding Invariant Violations** | 0 | 0 | 0 (Zero Tolerance Maintained) |
| **Un-ingested Standards (e.g. IS 10000, IS 10245) State** | `PENDING_TECHNICAL_EVALUATION` | `PENDING_TECHNICAL_EVALUATION` | 100% Safeguards Preserved |

---

## 4. Safeguard & Conflict Verification

1. **Equipment & Domain Conflict Gate**:
   - Rebuffed cross-domain leakage where high lexical overlap (e.g. "water utility network") could pull in pipes for valve tenders. Added deterministic domain guard in `src/applicability.py` ensuring pure valve requirements reject pipe-only candidates with `APPLICATION_CONFLICT`.
   - Prevented structural steel framing/fabrication requirements from recommending concrete codes (`IS 456`) or concrete rebar (`IS 1786`, `IS 432`).
2. **Ambiguity Preservation**:
   - Preserved `AmbiguityState.AMBIGUOUS` and `AmbiguityState.INCOMPLETE` across sequential recommendation sessions without mutable state leakage.
3. **Exact Standard, Part, and Edition Matching**:
   - Ingested evidence for `IS 1489 (Part 1) : 2015` cannot be cross-applied to unindexed `IS 1489 (Part 2)` (calcined clay based).
   - Ingested evidence for `IS 456 : 2000` is strictly bound to edition year 2000; outdated citations trigger lifecycle warnings.
4. **Supersedence Propagation**:
   - Queries citing withdrawn `IS 8112` cleanly recommend current active successor `IS 269 : 2015` with explicit supersedence alerts.
5. **Safe Abstention**:
   - Non-engineering tenders (e.g. administrative catering, cleaning) cleanly abstain with `NO_RELIABLE_MATCH` or `REVIEW_REQUIRED`.

---

## 5. Verification Test Suite Matrix

All tests executed via `pytest`:

```
tests/test_targeted_normative_ingestion.py::test_is456_corpus_document_and_passages PASSED
tests/test_targeted_normative_ingestion.py::test_is456_recommendation_and_clause_evidence PASSED
tests/test_targeted_normative_ingestion.py::test_is4984_hdpe_pipe_clauses_and_recommendation PASSED
tests/test_targeted_normative_ingestion.py::test_is1489_part1_ppc_cement_clauses_and_recommendation PASSED
tests/test_targeted_normative_ingestion.py::test_is8112_supersedence_to_is269 PASSED
tests/test_targeted_normative_ingestion.py::test_edition_mismatch_prevents_false_grounding PASSED
tests/test_targeted_normative_ingestion.py::test_non_ingested_catalogue_remains_pending_evaluation PASSED
tests/test_targeted_normative_ingestion.py::test_safe_abstention_preserved PASSED
tests/test_targeted_normative_ingestion.py::test_corpus_storage_provenance_and_licensing PASSED

============================== 9 passed in 6.08s ===============================
```

Full repository test suite:
```
717 passed in 144.55s (0:02:24)
```

---

## 6. Unresolved Risks & Next Phase Recommendation

1. **Unresolved Risks**:
   - National catalogue discovery contains thousands of niche standards without local clause evidence. They correctly remain `PENDING_TECHNICAL_EVALUATION` requiring human review.
   - Future expansion must continue following lawful extraction practices; full copyright text scraping must never be automated without official BIS licensing.
2. **Recommended Next Phase**:
   - **Phase 27**: Automated Adjudication Packet Batch Ingestion and Dynamic Multi-Standard Tender Audit Reporting (enabling comprehensive audit reports for tenders containing 10+ heterogeneous civil, mechanical, and electrical packages).
