# Phase 32: Multi-Part Standard Grounding & Physical Source Acquisition Readiness — User Acceptance Testing (UAT)

**Status:** Completed  
**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Execution Date:** 2026-10-19  
**Evaluation Mode:** Strict Read-Only Audit, Multi-Part Disambiguation, Defect Remediation, Deterministic Fixtures, Regression Verification  

---

## 1. Executive Summary & Acceptance Verification

Phase 32 hardened Tender Saathi's multi-part standard parsing, candidate disambiguation, dimensional scope ceiling validation, and authoritative source acquisition auditing:

1. **Multi-Part Normalization & Disambiguation**:
   - `STANDARD_REGEX` in `src/extract.py` and `StandardIdentifierNormalizer.parse` were unified to preserve exact parts, sections, prefixes (`IS`, `IS/ISO`, `IS/IEC`, `SP`), and edition years.
   - Fixed multi-part cross-matching: bare citations to multi-part specifications (e.g. `IS 1239`, `IS 7098`, `IS 1489`) without discriminating product context are flagged with `AMBIGUOUS_MULTI_PART_CITATION` and `human_review_required=True`.
   - When product keywords are present, intelligent disambiguation routes tubes/pipes to `IS 1239 (Part 1)` and pipe fittings/elbows to `IS 1239 (Part 2)` without cross-contamination.
   - Guarded subcomponent recommendations (`_evaluate_component_recommendations`) from inappropriately matching Part 2 when a query mentions tubes, eliminating the compound verification leak.
2. **Ceiling Dimensional Scope Bounds**:
   - Enhanced `evaluate_requirement_support` in `src/corpus/retriever.py` to recognize ceiling boundary statements ("up to and including X mm"). Out-of-scope sizes (such as 400 mm for `IS 1239 (Part 1)`, which caps at 150 mm) are strictly marked `UNSUPPORTED` and barred from `CLAUSE_VERIFIED`.
3. **Explicit Lifecycle Warning Notice**:
   - Superseded and withdrawn standards (e.g. `IS 2062:2011`) now emit an explicit user-facing warning in recommendation explanations: `Standard IS 2062 : 2011 has status 'WITHDRAWN' in the national BIS catalogue.`, preventing silent or generic messaging.
4. **Physical Source Acquisition Readiness Audit**:
   - Audited blockers for `IS 1239 (Part 2)` and `IS 2062`. Verified that zero synthetic or fabricated clauses exist in `corpus.db` for either standard.
   - Retained explicit blockers: authoritative physical BIS PDFs are not present locally; neither standard is ingested into `corpus.db` until authentic public documents are verified.
5. **End-to-End Validation**:
   - 8/8 tests passed in `tests/test_phase32_multi_part_grounding.py` covering the 7 required representative fixtures and the source acquisition invariant.
   - Full Python test suite passed: 767 passed in 155.12s.
   - Frontend Vitest suite passed: 9 passed in 291ms.
   - Frontend production build: clean (built in 2.60s).
   - Bit-for-bit ground-truth integrity preserved: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.

---

## 2. 7 Representative End-to-End Fixtures Results

| # | Fixture Description | Requirement Input Text | Retrieved Candidate | Verification Tier | Lifecycle Status | Review Required | Outcome & Review Reason |
|---|---|---|---|---|---|---|---|
| 1 | **Exact Single-Part Reference** | "Mild steel tubes conforming to IS 1239 (Part 1) with nominal bore 50 mm medium grade." | `IS 1239 (Part 1) : 2004` | `CLAUSE_VERIFIED` | `Active` | `False` | **PASS** — Grounded on Clause 1.1; Passage ID `6ede1b129dcef1ca`. Full support. |
| 2 | **Ambiguous Bare Multi-Part Citation** | "Supplied structural and piping material conforming to IS 1239 strictly as per tender specs." | `IS 1239 (Part 2) : 1992` | `CATALOGUE_DISCOVERED` | `Active` | `True` | **PASS** — `AMBIGUOUS_MULTI_PART_CITATION`: Multi-part specification lacks discriminating product parameters. |
| 3 | **Product-Directed Resolution** | 3a: "Mild steel tubes conforming to IS 1239 with nominal bore 25 mm."<br>3b: "Mild steel pipe fittings and wrought steel elbows conforming to IS 1239." | 3a: `IS 1239 (Part 1) : 2004`<br>3b: `IS 1239 (Part 2) : 1992` | 3a: `CLAUSE_VERIFIED`<br>3b: `CATALOGUE_DISCOVERED` | `Active` | 3a: `False`<br>3b: `True` (scope unindexed) | **PASS** — Tubes accurately routed to Part 1; pipe fittings routed to Part 2. |
| 4 | **Compound Multi-Standard Requirement** | "Piping work requires mild steel tubes conforming to IS 1239 (Part 1) and cast iron sluice valves conforming to IS 14846." | `IS 1239 (Part 1)` & `IS 14846` | Decomposed components isolated | `Active` | `True` | **PASS** — Both standards isolated into component bundles without cross-contamination. |
| 5 | **Catalogue-Only Standard** | "Mild steel pipe fittings conforming to IS 1239 (Part 2) : 1992." | `IS 1239 (Part 2) : 1992` | `CATALOGUE_DISCOVERED` | `Active` | `True` | **PASS** — No corpus passages exist; barred from `CLAUSE_VERIFIED`; `clause_number=None`. |
| 6 | **Withdrawn Standard Citation** | "Structural steel sections conforming to IS 2062:2011." | None | `SAFE_ABSTENTION` | `WITHDRAWN` | `True` | **PASS** — Explicit notice: `Standard IS 2062 : 2011 has status 'WITHDRAWN' in the national BIS catalogue.` |
| 7 | **Out-of-Scope Ceiling Parameter** | "Mild steel tubes conforming to IS 1239 (Part 1) with nominal bore 400 mm." | `IS 1239 (Part 1) : 2004` | `CATALOGUE_DISCOVERED` | `Active` | `False` | **PASS** — 400 mm exceeds 150 mm ceiling; marked `UNSUPPORTED`; barred from `CLAUSE_VERIFIED`. |

---

## 3. Physical Source Acquisition Readiness Audit

```
[ Physical Source Audit: IS 1239 (Part 2) & IS 2062 ]
  • Physical PDFs on Local Filesystem: 0 (No authentic PDFs present in data/standards/ or repository root)
  • Corpus Database (data/standards/corpus.db):
    - Passages for IS 1239 (Part 2): 0 (Zero synthetic/fabricated entries)
    - Passages for IS 2062: 0 (Zero synthetic/fabricated entries)
  • BIS National Catalogue (data/catalogue/bis_catalogue.db):
    - IS 2062:2011: Confirmed 'WITHDRAWN'
    - IS 2062 (Part 1) : 2025: Confirmed 'UNKNOWN'
    - IS 2062 (Part 2) : 2026: Confirmed 'UNKNOWN'
    - IS 1239 (Part 2) : 1992: Confirmed 'ACTIVE' (Reaffirmed 2019)
  • Acquisition Status:
    - BLOCKER RETAINED: Both standards remain un-ingested into corpus.db until authentic, verifiable public sources are acquired.
    - Zero mock text or simulated clause numbers were created.
```

---

## 4. Test & Verification Matrix

| Verification Command | Scope | Result | Status |
|---|---|---|---|
| `pytest tests/test_phase32_multi_part_grounding.py -v` | 7 representative fixtures + 1 acquisition readiness invariant | 8 passed in 7.61s | **PASS** |
| `pytest -q` | Full repository backend test suite | 767 passed in 155.12s | **PASS** |
| `npx --prefix frontend vitest run` | Frontend component & page tests | 9 passed in 291ms | **PASS** |
| `npm --prefix frontend run build` | Frontend production bundle | Clean build in 2.60s | **PASS** |
| `sha256sum dataset/ground_truth/ground_truth.csv` | Benchmark ground truth integrity | Checksum unchanged (`8bcc9bc...`) | **PASS** |
| `python3 scripts/generate_coverage_gap_report.py` | Gap metrics regeneration | Synchronized | **PASS** |
