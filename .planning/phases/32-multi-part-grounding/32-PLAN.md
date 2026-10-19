# Phase 32 Plan: Multi-Part Standard Grounding & Physical Source Acquisition Readiness

**Plan ID**: `32-MULTI-PART-GROUNDING`  
**Phase**: 32  
**Target Repository**: `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Branch**: `main`  

---

## Plan Overview

Phase 32 strengthens multi-part standard disambiguation, normative cross-reference grounding, and formalizes source acquisition readiness. It addresses the architectural vulnerability where bare standard numbers (e.g., "IS 1239" or "IS 1489") cross-match incorrect parts, resolves compound prefix corruption (`IS/IEC`, `IS/ISO`), audits physical source blockers for `IS 1239 (Part 2)` and `IS 2062`, and validates the end-to-end pipeline across 7 distinct procurement scenarios.

---

## Tasks Breakdown

### Task 1: Database Baseline & Index Audit
- Verify exact row counts, lifecycle distributions, and multi-part presence across `bis_catalogue.db`, `standards.db`, and `corpus.db`.
- Verify synchronization between FTS5 search index (`catalogue_search_index.db`) and `ACTIVE` catalogue standards.
- Reconcile and record metrics in `docs/evaluation/COVERAGE_GAP_METRICS.json`.

### Task 2: Multi-Part Extraction & Normalization Hardening
- Update `src/extract.py` to route detected mentions through `StandardIdentifierNormalizer.parse`.
- Preserve compound prefixes (`IS/IEC`, `IS/ISO`, `SP`), exact part numbers (`(Part 1)`, `(Part 2)`), and section identifiers during extraction.
- Ensure `normalize_standard_mention` does not strip slashes or convert part hyphens into colons.

### Task 3: Multi-Part Disambiguation & Ambiguity Detection
- Harden `src/ambiguity.py` and `src/recommend.py` for multi-part families:
  - `IS 1239`: Disambiguate Part 1 (tubes) vs Part 2 (fittings). If bare `IS 1239` is cited without product specification or discriminator, emit `AmbiguityState.REVIEW_REQUIRED`.
  - `IS 1489`: Disambiguate Part 1 (fly ash based) vs Part 2 (calcined clay based). If bare `IS 1489` is cited without fly ash specification, trigger review requirement and bar unconditional `CLAUSE_VERIFIED`.
  - `IS 7098`: Ensure existing voltage-level discrimination (Part 1 LT vs Part 2 MV/HV) remains robust.
  - `IS 2062`: Handle single-part legacy (`IS 2062:2011`, Withdrawn) vs multi-part current (`IS 2062 (Part 1):2025`, `IS 2062 (Part 2):2026`).

### Task 4: Physical Source Acquisition Audit (IS 1239 Part 2 and IS 2062)
- Re-verify repository for any authentic full-text PDFs or official gazette prints.
- Confirm zero-fabrication stance: retain formal acquisition blockers without fabricating clause text, content hashes, or mock records.
- Document exact missing clauses and parameters needed before future ingestion.

### Task 5: Deterministic Fixtures & End-to-End Validation
- Implement deterministic regression test suite in `tests/test_phase32_multi_part_grounding.py` covering:
  1. Exact single-part standard reference (`IS 1239 (Part 1)` -> Part 1 candidate, `CLAUSE_VERIFIED`).
  2. Ambiguous multi-part reference (`IS 1239` bare with ambiguous scope -> `REVIEW_REQUIRED`).
  3. Product-directed multi-part resolution ("mild steel tubes per IS 1239" -> correctly selects Part 1 over Part 2).
  4. Compound multi-standard requirement (`IS 1239 (Part 1)` tubes + `IS 14846` valves).
  5. Catalogue-only multi-part standard with no corpus passages (`IS 1239 (Part 2)` -> `CATALOGUE_DISCOVERED`).
  6. Withdrawn/superseded multi-part standard (`IS 2062:2011` -> `SAFE_ABSTENTION` / review required).
  7. Unsupported grade or parameter in multi-part standard (e.g. out-of-scope tube diameter or grade).

### Task 6: Full Verification & Deliverables
- Execute full regression suites:
  - `pytest -q`
  - `npx --prefix frontend vitest run`
  - `npm --prefix frontend run build`
  - `sha256sum dataset/ground_truth/ground_truth.csv`
  - `graphify update .`
- Produce `docs/evaluation/PHASE32_MULTI_PART_GROUNDING_REPORT.md` and `.planning/phases/32-multi-part-grounding/32-UAT.md`.
- Update `.planning/STATE.md`.
