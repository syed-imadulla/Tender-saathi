# Tender Saathi — Phase 31 Evidence Integrity, Compound Requirement Adjudication & Coverage Reconciliation Report

**Audit Date:** 2026-10-19T07:35:00+00:00  
**Repository:** `Tender_Saathi`  
**Phase:** 31 (Evidence Integrity, Compound Requirement Adjudication & Coverage Reconciliation)  
**Evaluator:** Antigravity AI  

---

## 1. Executive Summary & Core Architectural Invariants

Phase 31 conducts an empirical, evidence-backed audit of Tender Saathi's normative evidence corpus and verification gates following Phase 30 expansion. The directive of this phase is uncompromising: **to ensure that every `CLAUSE_VERIFIED` result is supported by authentic, correctly identified normative evidence that covers the specific technical requirement being verified, and not to inflate coverage numbers artificially.**

### Key Findings & Enforced Invariants:
1. **Passage Hashes are Integrity Checks, Not Authenticity Proofs:**
   - In `scripts/ingest_normative_standards.py`, `file_sha256` represents a deterministic SHA-256 hash of the extracted gazette clause text. It provides internal storage integrity (detecting accidental mutation or drift in SQLite), but does **NOT** constitute a cryptographic digital signature issued by the Bureau of Indian Standards.
   - Physical BIS PDFs for Indian Standards are not stored as standalone files on disk; instead, operative extracts are recorded in `scripts/ingest_normative_standards.py`.
2. **Reconciliation of Coverage Across Databases (Why Reports Differ):**
   - In `bis_catalogue.db` (35,208 national records): Only **4** corpus standards hold `ACTIVE` status (`IS 4984`, `IS 1489 Part 1`, `IS 383`, `IS 269`). Three standards (`IS 456`, `IS 1786`, `IS 1239 Part 1`) hold `UNKNOWN` status in the raw scrape dump due to BIS portal scrape gaps, and `IS 8112` is `WITHDRAWN`.
   - In `standards.db` (curated standards, 96 records): Manual engineering curation verified active reaffirmed status for all 7 active standards (`IS 456`, `IS 1786`, `IS 1239 Part 1`, `IS 383`, `IS 269`, `IS 4984`, `IS 1489 Part 1`), while recording `IS 8112` as `Withdrawn`.
   - **True active national catalogue evidence gap:** $10,828 - 4 = \mathbf{10,824} \text{ standards}$.
   - **Curated active evidence gap:** $80 - 7 = \mathbf{73} \text{ standards}$.
3. **Compound & Out-of-Scope Requirement Gate Enforcement:**
   - A requirement whose evidence covers the product scope but NOT the specified parameter (e.g. 5500 mm HDPE pipe per IS 4984, where max diameter is 2000 mm) is strictly barred from `CLAUSE_VERIFIED` and assigned `PARTIALLY_SUPPORTED` / `CATALOGUE_DISCOVERED`.
   - An unsupported material grade (e.g. `grade Fe 750` per IS 1786, where maximum standard grade is Fe 600) is barred from `CLAUSE_VERIFIED` and assigned `SAFE_ABSTENTION` / `PARTIALLY_SUPPORTED`.
   - Multi-component bundles with review-required subcomponents (e.g. M25 concrete bundle with cement, aggregates, and reinforcement) do not receive unconditional `CLAUSE_VERIFIED` status.
4. **Source Eligibility & Acquisition Blockers for New Candidates:**
   - `IS 1239 (Part 2)` (mild steel tubular pipe fittings) and `IS 2062` (hot-rolled structural steel plates/beams) exist only as metadata entries in `data/catalogue/normalized/`. Authoritative full-text source documents with authentic operative clauses are unavailable locally.
   - Per zero-fabrication rules, they remain **un-ingested** with formal acquisition blockers recorded.

---

## 2. Reconciled Quantitative Coverage Matrix

| Coverage Dimension | Count | Data Source & Table | SQL Calculation Method |
|---|---|---|---|
| **Total National BIS Catalogue Records** | **35,208** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*)` |
| **Distinct Base Standard Numbers** | **29,735** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(DISTINCT base_standard_number)` |
| **Active Catalogue Records** | **10,828** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'ACTIVE'` |
| **Withdrawn Catalogue Records** | **11,340** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'WITHDRAWN'` |
| **Unresolved Lifecycle Records** | **13,024** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'UNKNOWN'` |
| **Superseded Catalogue Records** | **16** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'SUPERSEDED'` |
| **Catalogue Records Missing Year** | **2** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE year IS NULL OR year = '' OR year = 0` |
| **Quarantined Records During Scrape** | **391** | `bis_catalogue.db` (`quarantine_records`) | `SELECT COUNT(*)` |
| **Curated Standards Total** | **96** | `standards.db` (`standards`) | `SELECT COUNT(*)` |
| — Curated Active Standards | **80** | `standards.db` (`standards`) | `SELECT COUNT(*) WHERE status = 'Active'` |
| — Curated Withdrawn Standards | **16** | `standards.db` (`standards`) | `SELECT COUNT(*) WHERE status = 'Withdrawn'` |
| **Unique Standards with Normative Passages** | **8** | `corpus.db` (`corpus_passages`) | `SELECT COUNT(DISTINCT standard_number)` |
| — Active Standards with Passages in Curated DB | **7** | `standards.db` $\cap$ `corpus.db` | IS 456, IS 4984, IS 1489 (Part 1), IS 383, IS 269, IS 1786, IS 1239 (Part 1) |
| — Active Standards with Passages in Catalogue DB | **4** | `bis_catalogue.db` $\cap$ `corpus.db` | IS 4984, IS 1489 (Part 1), IS 383, IS 269 |
| **Total Ingested Normative Passages** | **31** | `corpus.db` (`corpus_passages`) | `SELECT COUNT(*)` |
| **True Active Catalogue Normative Gap** | **10,824** | Catalogue `active_records` - Active in Catalogue with Passages | 10,828 - 4 = **10,824** |
| **Curated Active Normative Gap** | **73** | Curated `active_records` - Active Curated with Passages | 80 - 7 = **73** |

---

## 3. Normative Evidence Integrity & Provenance Audit

| Document ID | Canonical Standard | Edition Year | Provenance Type | Integrity Checksum | Clause Boundary Quality | Unresolved Limitations |
|---|---|---|---|---|---|---|
| `DOC-IS-456-2000` | IS 456 | 2000 (Rev 4) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1, 5.1, 6.1, 8.2 (Table 5) | Physical BIS PDF not stored on disk; relies on gazette extract |
| `DOC-IS-4984-2016` | IS 4984 | 2016 (Rev 5) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1, 4.2, 5.1 (Table 1), 7.1 | Covers sizes DN 16 to DN 2000 mm; larger sizes unindexed |
| `DOC-IS-1489-Part-1-2015` | IS 1489 (Part 1) | 2015 (Rev 4) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1, 5.2, 7.2, 7.3 | Part 2 (calcined clay pozzolana) not ingested |
| `DOC-IS-8112-2013` | IS 8112 | 2013 (Rev 2) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1 | Withdrawn standard; superseded by IS 269:2015 |
| `DOC-IS-383-2016` | IS 383 | 2016 (Rev 3) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1, 4.1, 5.1, 6.2 | Coarse & fine aggregate grading boundaries verified |
| `DOC-IS-269-2015` | IS 269 | 2015 (Rev 6) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1, 5.1, 6.1, 6.2 | Consolidated 33, 43, 53 grade OPC; physical strength tables |
| `DOC-IS-1786-2008` | IS 1786 | 2008 (Rev 4) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1, 4.1, 5.1, 8.1 | Covers Fe 415 to Fe 600; Fe 750 uncodified in standard |
| `DOC-IS-1239-Part-1-2004` | IS 1239 (Part 1) | 2004 (Rev 6) | Gazette Extract | SHA-256 (64 hex) | Cl 1.1, 5.1, 8.1, 9.1 | Part 1 (tubes) ingested; Part 2 (fittings) un-ingested |

---

## 4. Compound Requirement Adjudication Matrix (8 Deterministic Fixtures)

All 8 fixtures were tested through the real application pipeline with the following expected vs verified outcomes:

| Fixture Description | Input Tender Requirement Text | Expected Tier | Actual Verified Tier | Support State | Evidence Traceability & Grounding Behavior |
|---|---|---|---|---|---|
| **1. M25 Concrete Compound** | "M25 grade design-mix concrete conforming to IS 456, using 43 grade OPC cement conforming to IS 269, coarse aggregates conforming to IS 383, and high strength deformed steel bars conforming to IS 1786." | `CATALOGUE_DISCOVERED` | `CATALOGUE_DISCOVERED` | `PARTIALLY_SUPPORTED` | Decomposed into 4 subcomponents. Review required due to composite engineering scope; blocked from unconditional CLAUSE_VERIFIED. |
| **2. TMT Fe 500D (Supported Parameter)** | "High strength deformed steel bars for concrete reinforcement conforming to IS 1786 grade Fe 500D." | `CLAUSE_VERIFIED` | `CLAUSE_VERIFIED` | `FULLY_SUPPORTED` | Fe 500D matched in IS 1786:2008 Clause 1.1/5.1; authentic passage grounded; zero conflicts. |
| **3. Steel Tubes Part Disambiguation** | "Mild steel tubular pipes conforming to IS 1239 Part 1 Medium class." | `CATALOGUE_DISCOVERED` | `CATALOGUE_DISCOVERED` | `UNSUPPORTED` (Class) | Selects `IS 1239 (Part 1) : 2004` (not Part 2!). Class parameter ungrounded in passage 9.1, safely preventing auto-verification. |
| **4. Compound Piping Manifold** | "Piping manifold assembly comprising mild steel tubes to IS 1239 (Part 1) and sluice valves for water works to IS 14846." | `CATALOGUE_DISCOVERED` | `CATALOGUE_DISCOVERED` | `UNVERIFIED_COVERAGE` | Multiple standards identified across piping and valve domains. `human_review_required = True`. |
| **5. Unsupported Steel Grade (Fe 750)** | "High strength deformed steel bars conforming to IS 1786 grade Fe 750 Super." | `SAFE_ABSTENTION` | `SAFE_ABSTENTION` | `PARTIALLY_SUPPORTED` | Scope matched, but Fe 750 is uncodified in standard. Barred from `CLAUSE_VERIFIED`; `is_grounded = False`. |
| **6. Withdrawn Citation (IS 8112)** | "43-grade ordinary portland cement conforming to IS 8112:2013." | `CATALOGUE_DISCOVERED` | `CATALOGUE_DISCOVERED` | `FULLY_SUPPORTED` (Successor) | Cites withdrawn standard. Supersession gate blocks `CLAUSE_VERIFIED` despite active successor (IS 269) presence. |
| **7. Conflicting Editions** | "Polyethylene pipes for water supply conforming to IS 4984:1995 and IS 4984:2016 simultaneously." | `CATALOGUE_DISCOVERED` | `CATALOGUE_DISCOVERED` | `FULLY_SUPPORTED` | Edition conflict detected; review warning emitted; barred from `CLAUSE_VERIFIED`. |
| **8. Scope Without Parameter (5500 mm)** | "Polyethylene pipes for water supply conforming to IS 4984 with nominal outside diameter 5500 mm." | `CATALOGUE_DISCOVERED` | `CATALOGUE_DISCOVERED` | `PARTIALLY_SUPPORTED` | 5500 mm exceeds standard scope (max 2000 mm). Barred from `CLAUSE_VERIFIED`; `is_grounded = False`. |

---

## 5. Demonstrated Defects & Applied Corrections

### Defect 1: Scope-Covered Parameter Leak
- **Root Cause**: `evaluate_requirement_support` only evaluated electrical units (`W, kW, V, kV, kVA, A`) for parameter mismatch. Dimensional parameters (`mm`), steel grades (`Fe ...`), and concrete grades (`M...`) were ignored, allowing out-of-scope parameters (e.g. `5500 mm` for IS 4984 or `Fe 750` for IS 1786) to pass as `FULLY_SUPPORTED` and receive `CLAUSE_VERIFIED`.
- **Correction**: Extended parameter checking in `src/corpus/retriever.py` to evaluate steel grades (`Fe 415-600`), concrete grades (`M10-M80`), and dimensional size ranges. If an exact parameter is requested but missing from the passage, it returns `PARTIALLY_SUPPORTED`. If out-of-scope, it returns `UNSUPPORTED`.

### Defect 2: Case A Grounding Bypass
- **Root Cause**: In `ClauseRetriever.retrieve_clause_evidence` (Case A), `is_grounded` was assigned `(p.clause_identifier != 'CLAUSE_UNKNOWN')` without checking whether `support_state == FULLY_SUPPORTED`. An explicit clause citation with unsupported parameters could thus declare `is_grounded = True`.
- **Correction**: In `src/corpus/retriever.py` line 417, updated Case A to strictly require `(p.clause_identifier != "CLAUSE_UNKNOWN" and support_state == RequirementEvidenceSupportState.FULLY_SUPPORTED.value)`.

### Defect 3: Loose Standard Part Matching in Validator
- **Root Cause**: In `src/validate.py` line 106, querying `standard_number LIKE '%1239%'` matched `IS 1239 (Part 2)` before `IS 1239 (Part 1)` because Part 2 was inserted first. An explicit tender citation for `IS 1239 Part 1` was erroneously resolved to Part 2.
- **Correction**: In `src/validate.py` and `src/recommend.py`, integrated `StandardIdentifierNormalizer.parse(std_clean)` to parse and preserve Part numbers, querying exact canonical IDs (`norm_id%`) and filtering fallbacks by part number.

### Defect 4: Compound Requirement Verification Leak
- **Root Cause**: In `src/recommend.py` line 1219, `verification_tier = "CLAUSE_VERIFIED"` did not verify `not human_review_required` or `requirement_evidence_support == "FULLY_SUPPORTED"`. A compound requirement with unverified or review-required subcomponents could still be assigned `CLAUSE_VERIFIED` if the primary standard passage was grounded.
- **Correction**: In `src/recommend.py` line 1225, added strict conditions `and not human_review_required and getattr(top_clause_ev, "requirement_evidence_support", "") == "FULLY_SUPPORTED"`.

---

## 6. Acquisition Blockers for Un-ingested Candidates

1. **IS 1239 (Part 2) : 2011 — Mild Steel Tubular Pipe Fittings**:
   - *Status*: Metadata only in `data/catalogue/normalized/IS-1239-Part-2-1992.json`.
   - *Blocker*: Authentic BIS standard text containing dimensional fitting tables and pressure testing requirements is unavailable locally. Ingestion deferred until authentic gazette PDF is acquired.
2. **IS 2062 : 2011 — Hot Rolled Medium and High Tensile Structural Steel**:
   - *Status*: Metadata only in `data/catalogue/normalized/IS-2062-2011.json`.
   - *Blocker*: Primary BIS publication containing chemical composition tolerances, impact test temperature criteria (Grade E 250 to E 450), and bend test requirements is not present in local storage. Ingestion deferred.

---

## 7. Automated Test Verification Summary

- `pytest tests/test_phase31_evidence_integrity.py`: **12/12 passed in 8.01s** (100%).
- `pytest tests/test_phase30_corpus_expansion.py`: **14/14 passed in 1.83s** (100%).
- `pytest tests/test_targeted_normative_ingestion.py`: **9/9 passed in 0.95s** (100%).
- `pytest tests/test_e2e_pipeline_validation.py`: **8/8 passed in 2.11s** (100%).
- `npx --prefix frontend vitest run`: **9/9 passed in 243ms** (100%).
- `npm --prefix frontend run build`: **Clean build (dist created)** in 1.99s.
- `sha256sum dataset/ground_truth/ground_truth.csv`: **Bit-for-bit match (`8bcc...3cfc`)**.
- `graphify update .`: **Knowledge graph AST synchronized**.
