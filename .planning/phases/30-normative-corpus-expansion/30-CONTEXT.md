# Phase 30 Context: Prioritized Normative Corpus Expansion & Evidence Integrity

**Phase:** 30  
**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Execution Date:** 2026-10-19  
**Status:** In Progress (Discussion & Planning Complete)  

---

## 1. Phase Objective & Guiding Mandate

The primary goal of Phase 30 is **to expand Tender Saathi's locally available normative evidence corpus in a controlled, auditable way, prioritizing high-value standards for Indian public works procurement**.

### Core Quality Principle:
**Improve the number of standards that can be safely evaluated using authentic, traceable normative evidence—not merely increase document or passage counts.**
Arbitrary volume metrics (such as "50 documents / 500 passages") are rejected in favor of:
1. Practical procurement relevance in real Indian tenders.
2. Verified statutory public gazette provenance.
3. Rigorous edition and lifecycle currency matching.
4. Operative clause-level technical thresholds (tolerances, material grades, testing protocols, acceptance criteria).

---

## 2. Ingestion Candidates & Source Eligibility Audit

Based on empirical frequency in Indian public tenders (`dataset/ground_truth/ground_truth.csv`), existing catalogue metadata (`data/catalogue/normalized/`), and the discussion alignment, candidate standards are classified into a 5-tier backlog:

### Backlog Classification

| Standard Number | Edition / Year | Committee | Status in `bis_catalogue.db` | Status in `standards.db` | Procurement Frequency & Justification | Eligibility Decision |
|---|---|---|---|---|---|---|
| **IS 383** | **2016** | CED 2 | `ACTIVE` | Pending Ingestion | Direct companion to `IS 456` in all concrete work; specifies coarse/fine aggregates, grading zones I-IV. | **Tier 1: Ready for Ingestion** |
| **IS 269** | **2015** | CED 2 | `ACTIVE` | `Active` (Curated) | Master cement standard consolidating 33, 43, 53 grade OPC; direct successor to withdrawn `IS 8112`; cited in GT T012-R002. | **Tier 1: Ready for Ingestion** |
| **IS 1786** | **2008** | CED 54 | `UNKNOWN` | `Active` (Curated) | Mandatory Steel QCO; universal standard for TMT reinforcement rebars (Fe 415, Fe 500, Fe 500D) in RCC structures. | **Tier 2: High-Frequency Procurement** |
| **IS 1239 (Part 1)** | **2004** | CED 54 | `UNKNOWN` | Pending Ingestion | Mandatory Steel Pipes QCO; primary standard for GI/mild steel water distribution piping; cited in 3 GT cases (T001, T012, T020). | **Tier 2: High-Frequency Procurement** |
| **IS 2062** | 2011 | MTD 4 | `WITHDRAWN` | Pending Ingestion | Structural steel standard (E250, E350); 2011 edition superseded/withdrawn. Requires successor handling before positive recommendation. | **Tier 4: Lifecycle/Edition Unresolved (Deferred)** |
| **IS 694** | 2010 | ETD 9 | `UNKNOWN` | Pending Ingestion | PVC insulated cables; candidate for subsequent electrical domain expansion phase. | **Tier 5: Out of Scope for Phase 30** |

---

## 3. Scope of Operative Clauses to Ingest

For each of the 4 prioritized standards (`IS 383 : 2016`, `IS 269 : 2015`, `IS 1786 : 2008`, `IS 1239 (Part 1) : 2004`), ingestion will capture the critical operative clauses:

1. **`IS 383 : 2016` (Coarse and Fine Aggregates):**
   - **Clause 1.1:** Scope (Coarse and fine aggregates from natural sources, manufactured, and recycled sources for concrete).
   - **Clause 4.1 / 4.2:** Classification of Aggregates (Coarse aggregate nominal sizes 40 mm, 20 mm, 12.5 mm, 10 mm; Fine aggregate).
   - **Clause 5.1 / 5.2:** Physical and Chemical Requirements (Aggregate crushing value $\le 30\%$, impact value $\le 30\%$, flakiness/elongation index $\le 35\%$).
   - **Clause 6.2 / Table 4:** Grading of Fine Aggregate (Grading Zones I, II, III, and IV limits for concrete mix designs).
2. **`IS 269 : 2015` (Ordinary Portland Cement):**
   - **Clause 1.1:** Scope & Consolidation (Manufacture, chemical and physical requirements of 33, 43, and 53 grade Ordinary Portland Cement).
   - **Clause 5.1:** Chemical Requirements (Lime saturation factor 0.66 to 1.02, insoluble residue $\le 5.0\%$, magnesia $\le 6.0\%$).
   - **Clause 6.1 / Table 2:** Physical Requirements & Compressive Strength:
     - 33 Grade: 16 MPa (3d), 22 MPa (7d), 33 MPa (28d).
     - 43 Grade: 23 MPa (3d), 33 MPa (7d), 43 MPa (28d).
     - 53 Grade: 27 MPa (3d), 37 MPa (7d), 53 MPa (28d).
   - **Clause 6.2:** Setting Time and Soundness (Initial setting time $\ge 30$ min, final $\le 600$ min, Le-Chatelier expansion $\le 10$ mm).
3. **`IS 1786 : 2008` (High Strength Deformed Steel Bars / TMT):**
   - **Clause 1.1:** Scope (Requirements for deformed steel bars and wires for concrete reinforcement in sizes 4 mm to 40 mm).
   - **Clause 4.1:** Steel Manufacture & De-oxidation (Killed steel produced by electric furnace, basic oxygen, or continuous casting).
   - **Clause 5.1:** Grades of Steel (Fe 415, Fe 415D, Fe 500, Fe 500D, Fe 550, Fe 550D, Fe 600).
   - **Clause 8.1 / Table 3:** Mechanical Properties:
     - Fe 415: Min yield stress 415 N/mm², elongation 14.5%.
     - Fe 500: Min yield stress 500 N/mm², elongation 12.0%.
     - Fe 500D: Min yield stress 500 N/mm², elongation 16.0% (enhanced ductility for seismic zones).
4. **`IS 1239 (Part 1) : 2004` (Steel Tubes / GI Pipes):**
   - **Clause 1.1:** Scope (Butt-welded and seamless screwed and socketed steel tubes and plain end steel tubes for water and non-hazardous gas).
   - **Clause 5.1:** Steel Grade and Material (Tensile strength min 320 N/mm², elongation min 20%).
   - **Clause 8.1 / Table 1:** Classes and Dimensions (Light, Medium, Heavy classes; nominal bore 15 mm to 150 mm; galvanized coating requirements).
   - **Clause 9.1:** Hydrostatic Test (Each tube shall withstand hydrostatic test pressure of 5.0 MPa without leakage).

---

## 4. Architectural Invariants to Maintain

1. **Ingestion $\neq$ Verification:** Ingesting passages into `corpus_passages` creates qualified evidence candidates; runtime verification (`CLAUSE_VERIFIED`) requires exact matching of standard number, edition year, applicable part, and parameter-level support.
2. **Zero Clause Fabrication:** All text must be verbatim statutory public gazette language. No LLM hallucination, synthetic clause completion, or extrapolation.
3. **Traceable SHA-256 Provenance:** Every document record in `corpus_documents` and passage in `corpus_passages` must compute and store its canonical SHA-256 content hash.
4. **Offline & Deterministic:** No live BIS network dependencies; all tests and scripts must run 100% offline.
5. **Frozen Ground-Truth Integrity:** `dataset/ground_truth/ground_truth.csv` (SHA-256: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`) must remain completely untouched.
