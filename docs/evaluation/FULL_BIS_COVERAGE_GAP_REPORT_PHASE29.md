# Tender Saathi — Phase 29 Reproducible Coverage-Gap Audit Report

**Audit Date:** 2026-10-19T06:24:12.835504+00:00  
**Repository:** `Tender_Saathi`  
**Phase:** 29 (End-to-End Validation & Coverage-Gap Audit)  
**Evaluator:** Antigravity AI  

---

## 1. Executive Summary & Core Architectural Invariants

This report establishes the empirical, reproducible coverage statistics across the national BIS catalogue, the curated metadata database, and the normative clause evidence corpus.

### Critical Invariants:
1. **National BIS Catalogue Discovery $\neq$ Clause Verification:**
   - Presence in `data/catalogue/bis_catalogue.db` (title, committee, year, status) permits candidate discovery (`CATALOGUE_DISCOVERED`), but does **NOT** constitute clause-grounded normative evidence.
   - Only standards ingested with authentic clause text in `data/standards/corpus.db` are eligible for `CLAUSE_VERIFIED` status upon matching specific tender requirements.
2. **Evidence Ingestion $\neq$ Evidence Verification:**
   - Extracting a PDF into passages does not automatically make those passages authentic, correctly segmented, or technically sufficient to verify a recommendation.
   - An ingested passage in `corpus.db` is an *evidence candidate*. Verification requires:
     - Validated official provenance (cryptographic SHA-256 matching official BIS gazetted publication).
     - Accurate segmentation (preserving clause hierarchy, conditionality, tables, and notes).
     - Edition and lifecycle validity (matching the tender's applicable edition without silent version drift).
     - Requirement-level semantic and technical sufficiency (`FULLY_SUPPORTED` clause grounding).
3. **Quality & Domain Relevance Over Arbitrary Document Quotas:**
   - Success in standards coverage is not measured by arbitrary targets (e.g. "50 documents / 500 passages").
   - Expansion must prioritize the standards most relevant to actual tender requirements (Civil/Structural, Water/Public Health, Electrical Distribution, Mechanical), backed by verifiable provenance and precise clause-level technical thresholds.

---

## 2. Quantitative Coverage Figures & Cross-Database Lifecycle Reconciliation

| Coverage Dimension | Count | Data Source & Table | Calculation Method |
|---|---|---|---|
| **Total National BIS Catalogue Records** | **35,208** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*)` |
| **Distinct Base Standard Numbers** | **29,735** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(DISTINCT base_standard_number)` |
| **Active Catalogue Records** | **10,828** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'ACTIVE'` |
| **Withdrawn Catalogue Records** | **11,340** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'WITHDRAWN'` |
| **Unresolved Lifecycle Records** | **13,024** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'UNKNOWN'` |
| **Superseded Catalogue Records** | **16** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE status = 'SUPERSEDED'` |
| **Catalogue Records Missing Year** | **2** | `bis_catalogue.db` (`catalogue_standards`) | `SELECT COUNT(*) WHERE year IS NULL OR year = '' OR year = 0` |
| **Quarantined Records During Ingestion** | **391** | `bis_catalogue.db` (`quarantine_records`) | `SELECT COUNT(*)` |
| **Standards with Curated Metadata** | **93** | `standards.db` (`standards`) | `SELECT COUNT(*)` (78 Active, 15 Withdrawn) |
| **Unique Standards with Ingested Passages** | **4** | `corpus.db` (`corpus_passages`) | `SELECT COUNT(DISTINCT standard_number)` (IS 1489 (Part 1), IS 456, IS 4984, IS 8112) |
| **Total Ingested Normative Passages** | **15** | `corpus.db` (`corpus_passages`) | `SELECT COUNT(*)` |
| **Corpus Standards with `ACTIVE` Status in National Catalogue** | **2** | `bis_catalogue.db` $\cap$ `corpus.db` | Active in catalogue with corpus passages: IS 4984, IS 1489 (Part 1) |
| **Active National Catalogue Candidates Lacking Normative Evidence** | **10,826** | `active_records` - `active_in_catalogue_with_passages_count` | 10,828 - 2 = **10,826** |

---

## 3. Critical Verification of Coverage Calculations

### Why `10,828 - 3 = 10,825` Was Incorrect
A previous preliminary report stated catalogue-only candidates as $10,828 - 3 = 10,825$. That calculation was **invalid** because it conflated distinct lifecycle definitions across separate databases:

1. **Status of Corpus Standards in `bis_catalogue.db` (`catalogue_standards`):**
   - `IS 456 : 2000` (`IS-456-2000`): **`status = 'UNKNOWN'`** (one of the 13,024 unverified catalogue records).
   - `IS 4984 : 2016` (`IS-4984-2016`): **`status = 'ACTIVE'`** (one of the 10,828 active catalogue records).
   - `IS 1489 (Part 1) : 2015` (`IS-1489-Part-1-2015`): **`status = 'ACTIVE'`** (one of the 10,828 active catalogue records).
   - `IS 8112 : 2013` (`IS-8112-2013`): **`status = 'WITHDRAWN'`** (one of the 11,340 withdrawn catalogue records).
2. **Correct Set Reconciliation:**
   - The intersection between the active national catalogue records (`10,828`) and the ingested corpus standards is **exactly 2 standards** (`IS 4984` and `IS 1489 (Part 1)`).
   - Therefore, the true number of active catalogue records lacking local normative evidence is:
     $$10,828 - 2 = \mathbf{10,826} \text{ records}$$
3. **Curated Metadata Comparison:**
   - In `standards.db` (curated metadata), `IS 456`, `IS 4984`, and `IS 1489 (Part 1)` are all confirmed active (3 out of 78 active curated standards).
   - Curated active standards lacking normative passages: $78 - 3 = \mathbf{75} \text{ standards}$.

---

## 4. Normative Corpus Inventory (`data/standards/corpus.db`)

| Document ID | Standard Number | Edition Year | Title | Ingested Passages | Catalogue Status |
|---|---|---|---|---|---|
| `DOC-IS-456-2000` | **IS 456** | 2000 | Plain and Reinforced Concrete - Code of Practice (Fourth Revision) | 5 | `UNKNOWN` |
| `DOC-IS-4984-2016` | **IS 4984** | 2016 | Polyethylene Pipes for Water Supply - Specification (Fifth Revision) | 5 | `ACTIVE` |
| `DOC-IS-1489-Part-1-2015` | **IS 1489 (Part 1)** | 2015 | Portland Pozzolana Cement - Specification: Part 1 Fly Ash Based (Fourth Revision) | 4 | `ACTIVE` |
| `DOC-IS-8112-2013` | **IS 8112** | 2013 | Ordinary Portland Cement, 43 Grade - Specification (Second Revision) | 1 | `WITHDRAWN` |

---

## 5. Evidence Ingestion vs. Evidence Verification

It is essential to maintain a strict architectural distinction between **evidence ingestion** and **evidence verification**:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INGESTION PIPELINE (Document & Passage Extraction)       │
│    • Ingest official PDF document                           │
│    • Record document metadata, source citation, SHA-256     │
│    • Extract text and segment into structured passages      │
│    • Assign clause identifier, heading, and text density    │
│    [Result: Candidate Passages in corpus.db]                │
└───────────────────────────┬─────────────────────────────────┘
                            │ (Necessary, but NOT sufficient for verification)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. PASSAGE INTEGRITY & SUFFICIENCY AUDIT                    │
│    • Authentic publication provenance audit                 │
│    • Clause segmentation integrity & boundary check         │
│    • Table, formula, and tolerance retention verification   │
│    • Edition alignment & amendment currency check           │
│    [Result: Qualified Normative Evidence Corpus]            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. REQUIREMENT-SPECIFIC VERIFICATION (Runtime Inference)    │
│    • Deconstruct tender technical parameters                │
│    • Match requirement components against qualified clauses │
│    • Evidence Support Engine evaluation (FULLY_SUPPORTED)   │
│    • Zero clause fabrication / safe abstention on gap       │
│    [Result: CLAUSE_VERIFIED Tier Assignment]                │
└─────────────────────────────────────────────────────────────┘
```

Extracting passages from a PDF does **not** automatically verify a recommendation. A recommendation is only verified when qualified, authentic passages directly support all specified technical parameters of the tender requirement.

---

## 6. Strategic Metrics for Future Corpus Expansion

Rather than adopting arbitrary volume quotas (e.g. "50 documents / 500 passages"), expansion must be guided by:
1. **Procurement Frequency & Practical Relevance:** Focus on the highest-frequency Indian Standards mandated in public works tenders:
   - *Civil & Structural:* `IS 2062` (Structural Steel), `IS 1786` (TMT Rebars), `IS 383` (Aggregates).
   - *Water & Piping:* `IS 1239` (Mild Steel Tubes), `IS 8329` (Ductile Iron Pipes - once active edition lifecycle is verified), `IS 783` (Concrete Pipes).
   - *Electrical & Distribution:* `IS 694` (PVC Cables), `IS 1180` (Distribution Transformers).
2. **Cryptographic Provenance:** Official publication source hash verification for every ingested document.
3. **Rigorous Edition & Succession Handling:** Tracking amendments and successor standards to ensure withdrawn standards (e.g. `IS 8112`) are never endorsed as active.
4. **Clause-Level Technical Precision:** Ingesting specific operative clauses that define acceptance criteria, tolerances, and test methods, rather than general introductory text.

---

## 7. Reproducibility

This audit is 100% deterministic and operates strictly on local offline SQLite databases without network requests.
To reproduce this report:
```bash
python3 scripts/generate_coverage_gap_report.py
```
Outputs are written to:
- `docs/evaluation/COVERAGE_GAP_METRICS.json`
- `docs/evaluation/FULL_BIS_COVERAGE_GAP_REPORT_PHASE29.md`
