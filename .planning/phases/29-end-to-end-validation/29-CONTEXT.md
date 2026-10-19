# Phase 29 Context: End-to-End Validation, IS 456 Integration Investigation & Coverage-Gap Audit

## Background & Objective

Tender Saathi has progressed through 28 phases from core Indian Standards recommendation to multi-package tender auditing and rich frontend verification tier drilldowns.
Phase 29 is an **engineering validation and audit phase**, not a feature-building phase.

Its core objectives are:
1. **Investigate the IS 456 integration discrepancy**: In a live request with M25 concrete (`IS 456`), DI pipes (`IS 8329`), and EMD, `IS 456` was returned as `CATALOGUE_DISCOVERED` instead of `CLAUSE_VERIFIED`, and `IS 8329` as `SAFE_ABSTENTION`. Determine whether this is a genuine integration defect, a legitimate evidence mismatch, or an inaccurate earlier claim. Fix only demonstrated defects.
2. **Audit actual end-to-end architecture**: Trace production execution across PDF/text intake, decomposition, retrieval, applicability, verification-tier assignment, API serialization, and frontend rendering.
3. **Build deterministic end-to-end test matrix**: Create reproducible synthetic fixtures (E2E-01 through E2E-08) testing verified recommendations, catalogue-only candidates, safe abstentions, lifecycle warnings, multi-package tenders, and applicability safeguards without live BIS access or network calls.
4. **Quantify actual national catalogue and normative-evidence coverage**: Perform a reproducible database audit reporting exact counts for national BIS catalogue records, active records, withdrawn records, unclassified records, curated standards, and standards with local normative passages.
5. **Enforce verification and safety invariants**: Maintain zero clause fabrication, no false verified claims, and strictly preserve frozen ground truth (`dataset/ground_truth/ground_truth.csv`).

---

## Architectural Analysis & Investigation Findings

### 1. Root Cause Analysis: IS 456 Integration Discrepancy

- **Local Corpus State**:
  - `data/standards/corpus.db` contains document `DOC-IS-456-2000` (Title: *Plain and Reinforced Concrete - Code of Practice (Fourth Revision)*, Edition 2000, Ingestion status `EXTRACTED`).
  - Passages: Clause 1.1 (Scope), Clause 5.1 (Cement), Clause 6.1 (Concrete grades M10–M80, M25 = 25 N/mm²), Clause 8.2 / Table 5 (Exposure limits, minimum cement 300 kg/m³, max w/c ratio 0.50, minimum grade M25), Clause 26.5 (Reinforcement detailing).
- **Execution Trace for "Supply of M25 grade design mix concrete conforming to IS 456."**:
  1. Intake parses standard citation `IS 456` and engineering domain `CIVIL_AND_STRUCTURAL`.
  2. Search identifies `IS 456 : 2000` (`IS-456-2000`).
  3. `ClauseRetriever.retrieve_clause_evidence` is called with `query_text` and `requirement_text`.
  4. In `src/corpus/retriever.py`, because the requirement does not cite an explicit clause number (e.g., "Clause 8.2"), retrieval falls into **Case B (Lexical Search Support)**.
  5. Lexical search locates passage `DOC-IS-456-2000_p20_c8_2` (Clause 8.2 / Table 5, explicitly specifying M25 concrete).
  6. Parameter evaluation marks `requirement_evidence_support: FULLY_SUPPORTED`.
  7. **The Discrepancy Point**: In `src/corpus/retriever.py` line 465, Case B sets:
     `is_grounded = False  # Unverified because clause citation was not explicitly requested`
     `message = "Relevant passage retrieved via lexical search; specific clause citation was not requested so grounding is unverified."`
  8. In `src/recommend.py` line 1213:
     `if top_clause_ev and getattr(top_clause_ev, "is_grounded", False) and getattr(top_clause_ev, "passage_text", None):`
     `    verification_tier = "CLAUSE_VERIFIED"`
     `elif ...: verification_tier = "CATALOGUE_DISCOVERED"`
  9. Because `is_grounded` is hard-coded to `False` in Case B, `verification_tier` evaluates to `CATALOGUE_DISCOVERED`, and `passage_id` / `clause_number` are cleared to `None`!
  10. Conversely, when the query explicitly cites `IS 456 Clause 6.1` or `Clause 8.2` or `Table 5`, Case A executes, setting `is_grounded = True`, and the tier is correctly assigned `CLAUSE_VERIFIED` with passage ID `991f252931d9b39e`!

### 2. Investigation of IS 8329

- **Corpus & Database Inspection**:
  - `data/standards/corpus.db`: `IS 8329` has **0 documents and 0 passages**.
  - `data/standards/standards.db`: `IS 8329` has **0 rows**.
  - `data/catalogue/bis_catalogue.db`: `IS 8329 : 2000` is present in `catalogue_standards` with `status: 'UNKNOWN'`, `technical_committee: 'MTD 06'`.
- **Recommendation Trace**:
  - `validate_standard_status('IS 8329')` returns `is_known = True`, `is_catalogue_only = True`, `status = 'Unknown'`, `is_active = False`.
  - In `src/critic.py`, because `is_active = False` and status is `'Unknown'` (unresolved lifecycle status in the BIS catalogue snapshot), `lifecycle_score` is evaluated as `0.0`.
  - Gate 1 in `src/critic.py` rejects candidates with `lifecycle_score == 0.0`.
  - `AmbiguityEngine` marks `AmbiguityState.NO_RELIABLE_MATCH`.
  - The pipeline correctly abstains with `verification_tier = 'SAFE_ABSTENTION'`.
- **Finding**: The assignment of `SAFE_ABSTENTION` to IS 8329 is **not an integration defect**. It is the legitimate and correct safety behavior of the system:
  1. `IS 8329` lacks local normative clause evidence in `corpus.db`.
  2. Its lifecycle status in the national catalogue snapshot is `UNKNOWN`.
  3. Under zero-fabrication safety invariants, Tender Saathi must not fabricate verification or guess active status for an unindexed standard with unknown lifecycle status.

### 3. Investigation of EMD Requirement

- Input: "Earnest money deposit of Rs. 2,00,000 shall be furnished as BG."
- Classified as `GENERAL_AND_ADMINISTRATIVE`.
- The pipeline correctly abstains with `verification_tier = 'SAFE_ABSTENTION'`, `candidate_standard = None`.
- **Finding**: This is correct, expected behavior preventing spurious engineering standards from being attached to administrative/commercial conditions.

---

## Scope & Target Deliverables for Phase 29

1. **Context & Plan**:
   - `.planning/phases/29-end-to-end-validation/29-CONTEXT.md`
   - `.planning/phases/29-end-to-end-validation/29-PLAN.md`
2. **Defect Correction**:
   - If authentic normative evidence in `corpus.db` genuinely supports the requirement parameters (`requirement_evidence_support == 'FULLY_SUPPORTED'`) and matches standard number, edition, and domain, ensure `verification_tier` correctly reflects clause support without forcing artificial `CATALOGUE_DISCOVERED` downgrades, while strictly preventing false positive verification when evidence is absent, partial, unverified, or conflicting.
3. **Deterministic Test Matrix**:
   - Create `tests/test_e2e_pipeline_validation.py` covering E2E-01 through E2E-08.
4. **Coverage-Gap Audit**:
   - Generate reproducible JSON metrics: `docs/evaluation/COVERAGE_GAP_METRICS.json`.
   - Generate comprehensive human-readable report: `docs/evaluation/FULL_BIS_COVERAGE_GAP_REPORT_PHASE29.md`.
5. **Phase 29 UAT & State Updates**:
   - `.planning/phases/29-end-to-end-validation/29-UAT.md`
   - `.planning/STATE.md`
