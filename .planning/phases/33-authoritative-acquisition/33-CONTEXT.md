# Phase 33: Authoritative BIS Document Acquisition, Ingestion & Evidence-Grounded Cross-Reference Traversal — Context

**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Date:** 2026-10-19  

---

## 1. Baseline Audit Prior to Implementation

Direct SQLite baseline audit executed on active databases:

### A. National BIS Catalogue (`data/catalogue/bis_catalogue.db`)
- **Total Records:** 35,208 records
- **Lifecycle Distribution:**
  - `ACTIVE`: 10,828 records
  - `WITHDRAWN`: 11,340 records
  - `UNKNOWN`: 13,024 records (due to historical portal scraping artifacts)
  - `SUPERSEDED`: 16 records
- **Active Standards in Corpus:** 4 active catalogue standards (`IS 4984`, `IS 1489 (Part 1)`, `IS 383`, `IS 269`)
- **Active Catalogue Evidence Gap:** 10,824 standards (10,828 active - 4)

### B. Curated Standards Repository (`data/standards/standards.db`)
- **Total Curated Standards:** 96 records
- **Status Counts:**
  - `Active`: 80 records
  - `Withdrawn`: 16 records
- **Active Standards with Normative Corpus Passages:** 7 standards (`IS 456`, `IS 4984`, `IS 1489 (Part 1)`, `IS 383`, `IS 269`, `IS 1786`, `IS 1239 (Part 1)`)
- **Curated Evidence Gap:** 73 active standards awaiting normative passages (80 - 7)

### C. Normative Evidence Corpus (`data/standards/corpus.db`)
- **Ingested Documents:** 8 documents (`DOC-IS-456-2000`, `DOC-IS-4984-2016`, `DOC-IS-1489-Part-1-2015`, `DOC-IS-8112-2013`, `DOC-IS-383-2016`, `DOC-IS-269-2015`, `DOC-IS-1786-2008`, `DOC-IS-1239-Part-1-2004`)
- **Total Normative Passages:** 31 passages
- **Target Candidates Checked:**
  - `IS 1239 (Part 2)`: 0 passages currently in `corpus.db`
  - `IS 14846`: 0 passages currently in `corpus.db`
  - `IS 800`: 0 passages currently in `corpus.db`

### D. Catalogue Search Index (`data/catalogue/catalogue_search_index.db`)
- **Total Indexed:** 10,828 records (100% synchronized with active catalogue records).

---

## 2. Source Acquisition Target Assessment

We prioritize 3 critical Indian public procurement infrastructure standards:
1. **IS 1239 (Part 2) : 2011** — *Steel Tubes, Tubulars and Other Steel Fittings - Part 2: Steel Pipe Fittings (Fifth Revision)*.
   - Public Gazette URL: `https://archive.org/details/gov.in.is.1239.2.2011`
   - Technical Committee: CED 54 (Pipe and Pipe Fittings)
   - Scope: Mild steel sockets, tubulars, and other wrought steel pipe fittings DN 6 to 150 mm for water, gas, steam.
   - Normative References: `IS 1239 (Part 1)`, `IS 554`.
2. **IS 14846 : 2000** — *Sluice Valve for Water Works Purposes (50 to 1200 mm Size) - Specification*.
   - Public Gazette URL: `https://archive.org/details/gov.in.is.14846.2000`
   - Technical Committee: CED 3 (Sanitary Installation and Water Works)
   - Scope: Non-rising stem sluice valves for water supply up to 45°C, sizes DN 50 to 1200 mm, double-flanged.
   - Pressure Ratings: PN 1.0 (1.0 MPa), PN 1.6 (1.6 MPa).
   - Normative References: `IS 210` (Grey Iron Castings FG 200), `IS 1538` (Cast iron fittings & flanges).
3. **IS 800 : 2007** — *General Construction in Steel - Code of Practice (Third Revision)*.
   - Public Gazette URL: `https://archive.org/details/gov.in.is.800.2007`
   - Technical Committee: CED 7 (Structural Engineering and Structural Sections)
   - Scope: Design of general steel structures using hot-rolled sections joined by bolting, riveting, welding.
   - Normative References: `IS 2062` (Structural steel materials), `IS 875` (Design loads), `IS 1893` (Earthquake).

---

## 3. Evidence-Grounded Cross-Reference Traversal Requirements

- **Origin Grounding**: Traversal starts from a specific primary standard and its grounded clause (e.g. `IS 456 Clause 5.1`, `IS 800 Clause 2.2`, `IS 14846 Clause 6.1`).
- **Edge Taxonomy & Provenance**:
  - `NORMATIVE_REFERENCE`: Mandatory material / design standard cited in operative clauses.
  - `TEST_METHOD`: Standard specifying testing methods.
  - `CODE_OF_PRACTICE` / `INSTALLATION_CODE`: Structural or installation code.
  - `INFORMATIVE_REFERENCE`: General guidance or bibliographic references.
- **Cycle Prevention & Bounded Depth**:
  - Path memoization to prevent infinite loops (e.g. `IS 269` <-> `IS 8112`).
  - Configurable `max_depth` (default 1, max 2).
  - Maximum results ceiling to prevent explosion.
- **Safety Invariant**:
  - Discovered related standards are returned as `RELATED_FOR_REVIEW` or `CATALOGUE_DISCOVERED`.
  - A graph relationship alone NEVER proves that tender requirements are satisfied; missing clause evidence is never converted to `CLAUSE_VERIFIED`.
