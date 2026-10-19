# Tender Saathi — Phase 30 Prioritized Normative Corpus Expansion & Evidence Integrity Report

**Audit Date:** 2026-10-19T11:59:05.673808+00:00  
**Repository:** `Tender_Saathi`  
**Phase:** 30 (Prioritized Normative Corpus Expansion & Evidence Integrity)  
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
| **Standards with Curated Metadata** | **96** | `standards.db` (`standards`) | `SELECT COUNT(*)` (78 Active, 15 Withdrawn) |
| **Unique Standards with Ingested Passages** | **8** | `corpus.db` (`corpus_passages`) | `SELECT COUNT(DISTINCT standard_number)` (IS 1239 (Part 1), IS 1489 (Part 1), IS 1786, IS 269, IS 383, IS 456, IS 4984, IS 8112) |
| **Total Ingested Normative Passages** | **31** | `corpus.db` (`corpus_passages`) | `SELECT COUNT(*)` |
| **Corpus Standards with `ACTIVE` Status in National Catalogue** | **4** | `bis_catalogue.db` $\cap$ `corpus.db` | Active in catalogue with corpus passages: IS 4984, IS 1489 (Part 1), IS 383, IS 269 |
| **Active National Catalogue Candidates Lacking Normative Evidence** | **10,824** | `active_records` - `active_in_catalogue_with_passages_count` | 10,828 - 4 = **10,824** |

---

## 3. Critical Verification of Coverage Calculations

### Set Reconciliation Across Databases
A previous preliminary report stated catalogue-only candidates as $10,828 - 3 = 10,825$. That calculation was **invalid** because it conflated distinct lifecycle definitions across separate databases:

1. **Status of Corpus Standards in `bis_catalogue.db` (`catalogue_standards`):**
   - Four standards are verified **`ACTIVE`**: `IS 4984 : 2016`, `IS 1489 (Part 1) : 2015`, `IS 383 : 2016`, and `IS 269 : 2015`.
   - Three standards hold **`UNKNOWN`** status in raw catalogue dump: `IS 456 : 2000`, `IS 1786 : 2008`, and `IS 1239 (Part 1) : 2004`.
   - One standard is **`WITHDRAWN`**: `IS 8112 : 2013` (superseded by active `IS 269 : 2015`).
2. **Correct Set Reconciliation:**
   - The intersection between active national catalogue records (`10,828`) and ingested corpus standards is **4 standards** (IS 4984, IS 1489 (Part 1), IS 383, IS 269).
   - Therefore, the true number of active catalogue records lacking local normative evidence is:
     $$10,828 - 4 = \mathbf{10,824} \text{ records}$$
3. **Curated Metadata Comparison:**
   - In `standards.db` (curated metadata), 7 out of 80 active standards now have normative passages (IS 1239 (Part 1), IS 1489 (Part 1), IS 1786, IS 269, IS 383, IS 456, IS 4984).
   - Curated active standards lacking normative passages: $80 - 7 = \mathbf{73} \text{ standards}$.

---

## 4. Normative Corpus Inventory (`data/standards/corpus.db`)

| Document ID | Standard Number | Edition Year | Title | Ingested Passages | Catalogue Status |
|---|---|---|---|---|---|
| `DOC-IS-456-2000` | **IS 456** | 2000 | Plain and Reinforced Concrete - Code of Practice (Fourth Revision) | 5 | `UNKNOWN` |
| `DOC-IS-4984-2016` | **IS 4984** | 2016 | Polyethylene Pipes for Water Supply - Specification (Fifth Revision) | 5 | `ACTIVE` |
| `DOC-IS-1489-Part-1-2015` | **IS 1489 (Part 1)** | 2015 | Portland Pozzolana Cement - Specification: Part 1 Fly Ash Based (Fourth Revision) | 4 | `ACTIVE` |
| `DOC-IS-8112-2013` | **IS 8112** | 2013 | Ordinary Portland Cement, 43 Grade - Specification (Second Revision) | 1 | `WITHDRAWN` |
| `DOC-IS-383-2016` | **IS 383** | 2016 | Coarse and Fine Aggregate for Concrete - Specification (Third Revision) | 4 | `ACTIVE` |
| `DOC-IS-269-2015` | **IS 269** | 2015 | Ordinary Portland Cement - Specification (Sixth Revision) | 4 | `ACTIVE` |
| `DOC-IS-1786-2008` | **IS 1786** | 2008 | High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - Specification (Fourth Revision) | 4 | `UNKNOWN` |
| `DOC-IS-1239-Part-1-2004` | **IS 1239 (Part 1)** | 2004 | Steel Tubes, Tubulars and Other Wrought Steel Fittings - Part 1: Steel Tubes (Sixth Revision) | 4 | `UNKNOWN` |

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
- `docs/evaluation/PHASE30_CORPUS_EXPANSION_REPORT.md`
