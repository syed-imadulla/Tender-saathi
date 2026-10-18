# BIS Catalogue vs. Curated Indian Standards Dataset Audit Report

**Date:** 2026-10-18  
**Repository:** `Tender_Saathi`  
**Investigation Mode:** Strict Read-Only Audit (No Code or Database Changes)  
**Evaluator:** Antigravity AI  

---

## Executive Summary

This audit investigates the structural, semantic, and operational relationship between the two standards databases and their associated graph/evidence files in Tender Saathi:
1. `data/catalogue/bis_catalogue.db` (35,208 records in `catalogue_standards` and `standards`)
2. `data/standards/standards.db` (90 records in `standards`, 60 in `standard_references`, 16 in `standard_relationships`)
3. `data/standards/relationships.json` (72 explicit graph edges with evidence and provenance)
4. `data/standards/verified_standards.json` (8 gold-standard BSB Edge verified records)

### Key Verdict
The **35,208 national BIS catalogue records** and the **90 curated standards** do **not** represent disjoint or conflicting bodies of knowledge, nor are they simply identical datasets with superficial metadata differences. Instead, they represent a **two-tier hierarchy**:
- **`bis_catalogue.db` is a national shallow catalog**: High breadth across all 15 BIS Division Councils (Civil, Electrotechnical, Mechanical, Chemical, Food, etc.), but **zero scope text, zero clause breakdown, zero normative citation edges, and no test parameter thresholds**.
- **`standards.db` is a high-enrichment feasibility corpus**: Focused on high-volume public procurement domains (Civil, Piping, Valves, Pumps, Electrical, Food Safety), containing full clause-level scope text, application notes, normative references, and verified relationships.
- **The actual tender-upload recommendation pipeline strictly indexes and queries `data/standards/standards.db`**. Catalogue-only standards (35,118 records) **cannot** become recommendation candidates, and the system **cannot** verify their applicability because `bis_catalogue.db` contains no clause evidence.

---

## 1. Source Schemas, Record Counts & Metadata Fields

### 1.1 `data/catalogue/bis_catalogue.db`
- **File Size:** 37.65 MB SQLite database
- **Tables & Record Counts:**
  - `catalogue_standards`: **35,208 rows** (canonical national catalogue table)
  - `standards`: **35,208 rows** (compatibility table mirroring `standards.db` schema, but with `scope = NULL`)
  - `quarantine_records`: **391 rows** (raw records that failed validation during bulk crawl/scraping)
  - `catalogue_snapshots`: **2 rows** (historical crawl snapshots)
  - `catalogue_change_history`: **42 rows** (tracked modifications across crawl runs)
  - `ingestion_summary`: Ingestion run metadata

#### Schema for `catalogue_standards`:
```sql
CREATE TABLE catalogue_standards (
    canonical_id TEXT PRIMARY KEY,           -- e.g. "IS-778-1984", "IS-1180-Part-1-2014"
    standard_number TEXT NOT NULL,         -- e.g. "IS 778 : 1984"
    base_standard_number TEXT NOT NULL,    -- e.g. "IS 778"
    prefix TEXT NOT NULL,                  -- e.g. "IS", "IS/ISO", "IS/IEC"
    base_number TEXT NOT NULL,             -- e.g. "778"
    part INTEGER,                          -- Part number if applicable
    section INTEGER,                       -- Section number if applicable
    year INTEGER,                          -- Publication/revision year
    amendment INTEGER,                     -- Current amendment number
    title TEXT NOT NULL,                   -- Official standard title
    technical_committee TEXT,              -- e.g. "CED 3", "ETD 16"
    department TEXT,                       -- e.g. "Civil Engineering", "Electrotechnical"
    aspect TEXT,                           -- Product, Code of Practice, Method of Test
    amendments TEXT,                       -- JSON/text list of amendments
    amendment_count INTEGER NOT NULL,      -- Integer count
    status TEXT NOT NULL,                  -- ACTIVE, WITHDRAWN, UNKNOWN
    is_active INTEGER,                     -- Boolean flag (1/0)
    iso_equivalence TEXT,                  -- Equivalent ISO/IEC number
    iso_equivalence_degree TEXT,           -- Identical, Modified, Equivalent
    source TEXT NOT NULL,                  -- "BIS Know Your Standards"
    source_type TEXT NOT NULL,             -- "NATIONAL_BULK_CATALOGUE"
    source_url TEXT,                       -- BIS portal URL
    retrieved_at TEXT NOT NULL,            -- ISO 8601 timestamp
    ingestion_run_id TEXT NOT NULL,        -- UUID
    seeds_observed_json TEXT NOT NULL,     -- Scraper crawl seeds
    times_observed INTEGER NOT NULL,       -- Ingestion frequency count
    first_seen TEXT NOT NULL,              -- First crawl date
    last_seen TEXT NOT NULL,               -- Latest crawl date
    raw_record_ref TEXT NOT NULL,          -- Scraper dump reference
    is_recovered INTEGER NOT NULL DEFAULT 0,
    recovery_reason TEXT
);
```

### 1.2 `data/standards/standards.db`
- **File Size:** 0.11 MB SQLite database
- **Tables & Record Counts:**
  - `standards`: **90 rows** (curated feasibility standards with full technical text)
  - `standard_references`: **60 rows** (normative citations extracted from standard texts)
  - `standard_relationships`: **16 rows** (explicit relationship triples)

#### Schema for `standards`:
```sql
CREATE TABLE standards (
    standard_id TEXT PRIMARY KEY,                    -- e.g. "IS-778-1984"
    standard_number TEXT NOT NULL,                 -- e.g. "IS 778"
    year INTEGER,                                  -- e.g. 1984
    full_title TEXT NOT NULL,                      -- Official title
    status TEXT NOT NULL,                          -- "Active", "Withdrawn"
    reaffirmed_year INTEGER,                       -- e.g. 2020
    amendments_count INTEGER,                      -- e.g. 2
    technical_committee TEXT,                      -- e.g. "CED 3"
    ics TEXT,                                      -- ICS classification
    udc TEXT,                                      -- UDC code
    scope TEXT,                                    -- Full text of Scope Clause 1.x (90/90 populated)
    notes TEXT,                                    -- Technical application/revision notes
    source TEXT NOT NULL,                          -- e.g. "BSB_EDGE_MANUALLY_VERIFIED"
    source_url TEXT,                               -- Verification URL
    retrieved_at TEXT,                             -- Verification date
    original_standard_identifier TEXT NOT NULL,    -- Raw citation
    verification_status TEXT NOT NULL,             -- "VERIFIED"
    evidence TEXT                                  -- Specific clause citation or provenance notes
);
```

#### Schema for `standard_references` & `standard_relationships`:
```sql
CREATE TABLE standard_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_id TEXT NOT NULL,
    referenced_standard_number TEXT NOT NULL,
    referenced_year INTEGER,
    referenced_title TEXT,
    citing_clause TEXT,                            -- e.g. "Clause 2", "Clause 4.1"
    FOREIGN KEY (standard_id) REFERENCES standards(standard_id) ON DELETE CASCADE
);

CREATE TABLE standard_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_standard_id TEXT NOT NULL,
    target_standard TEXT NOT NULL,
    relationship_type TEXT NOT NULL,               -- NORMATIVE_REFERENCE, TEST_METHOD, etc.
    evidence TEXT NOT NULL,                        -- Grounded clause citation
    FOREIGN KEY (source_standard_id) REFERENCES standards(standard_id) ON DELETE CASCADE
);
```

### 1.3 `data/standards/relationships.json`
- **Record Count:** **72 explicit relationship edges**
- **Fields:** `source_standard`, `target_standard`, `relationship_type`, `evidence`, `evidence_source`, `provenance`, `confidence`
- **Provenance Distribution:**
  - `VERIFIED`: 56 edges (supported by BSB Edge portal or clause extracts)
  - `CURATED`: 16 edges (domain expert curated normative links)
  - `INFERRED`: 0 edges (strictly prohibited by project rules)
- **Edge Type Distribution:**
  - `NORMATIVE_REFERENCE`: 48
  - `INSTALLATION_CODE` / `INSTALLATION_STANDARD`: 12
  - `TEST_METHOD`: 6
  - `SAFETY_STANDARD`: 2
  - `ALLIED_STANDARD`: 2
  - `SUPERSEDES`: 1
  - `TERMINOLOGY_STANDARD`: 1

### 1.4 `data/standards/verified_standards.json`
- **Record Count:** **8 gold-standard verified standards**
- **Contents:** Fully audited records with verified clause scopes, embedded references, explicit relationship mappings, and screenshot/portal provenance:
  - `IS-778-1984` (Copper alloy gate, globe and check valves)
  - `IS-1239-Part-1-2004` (Steel tubes for water, gas and sewage)
  - `IS-1538-1993` (Cast iron fittings for pressure pipes)
  - `IS-4984-2016` (HDPE pipes for water supply)
  - `IS-4985-2021` (Unplasticized PVC pipes for potable water)
  - `IS-14846-2000` (Sluice valves for waterworks)
  - `IS-15778-2007` (CPVC pipes for potable hot and cold water)
  - `IS-1255-1983` (Installation and maintenance of power cables up to 33 kV)

---

## 2. Dataset Overlap & Structural Nature

### 2.1 The Nature of the Datasets
The 35,208 BIS catalogue records and the 90 curated standards are **overlapping datasets with fundamentally different roles and coverage depth**:
1. **`bis_catalogue.db` is an exhaustive national registry index**:
   - Represents the complete machine-readable index published by the Bureau of Indian Standards (BIS Know Your Standards portal).
   - Contains national standards across all engineering, agricultural, consumer, and information technology domains.
   - Purpose: Identifier validation, standard existence checks, active/withdrawn lifecycle auditing, technical committee attribution, and ISO/IEC equivalence lookup.
   - Limitation: Has **no technical body text, no scope clause, and no normative reference graph**.
2. **`standards.db` is a specialized, deep-enrichment feasibility engine corpus**:
   - Represents the core procurement corpus developed for Tender Saathi's tender recommendation, clause verification, and semantic search engine.
   - Deeply covers 6 primary infrastructure procurement domains:
     - Water supply & plumbing (PVC, CPVC, HDPE, GI pipes, fittings)
     - Valves (sluice, gate, globe, check, ball valves)
     - Electrical distribution (transformers, conductors, XLPE/PVC cables, switchgear)
     - Pumps (submersible, monobloc, sewage pumps)
     - Civil construction (cement, reinforcement steel, waterproofing)
     - Food processing & hygiene (HACCP, sensory analysis, food hygiene)
   - Purpose: Text-based semantic retrieval, BM25 keyword matching, clause-level compliance verification, and multi-requirement conflict auditing.

### 2.2 Identifier Overlap Calculations

| Overlap Category | Curated Records (`standards.db`) | % of Curated Dataset | Details |
| :--- | :---: | :---: | :--- |
| **Exact Canonical ID Match** | **73** | 81.1% | Identical `canonical_id` string in both databases (e.g. `IS-778-1984`, `IS-4984-2016`). |
| **Parentheses/Formatting Syntax Variant** | **2** | 2.2% | Slug contains parentheses in curated DB (e.g. `IS-7098-(Part-1)-1988` vs `IS-7098-Part-1-1988`; `IS-10322-(Part-5-Sec-5)-2013` vs `IS-10322-Part-5-Sec-5-2013`). |
| **Standard "Part-" Syntax Variant** | **3** | 3.3% | Curated omitted `-Part-` in international adoption slugs (e.g. `IS-IEC-61439-3-2012` vs `IS-IEC-61439-Part-3-2012`; `IS-IEC-61800-2-2015`; `IS-IEC-61439-2-2011`). |
| **Special Publication Slug Variant** | **1** | 1.1% | Special publication slug variation (`SP-57-(QAWSM)-1993` vs `SP-57-1993`). |
| **Edition / Revision Year Delta** | **5** | 5.6% | Standard matches by number and part, but reflects a different publication/reaffirmation year (see Section 2.3). |
| **Composite Handbook Bundles** | **4** | 4.4% | SP 18 multi-part food analysis handbooks (`SP-18-Part-2-to-4-1984`, etc.). |
| **Composite Multi-Part Bundle** | **1** | 1.1% | Grouped standard bundle (`IS-2556-(Parts-1,-2,-4)`). |
| **External Non-BIS Regulation** | **1** | 1.1% | Statutory regulation from FSSAI (`FSSAI-Schedule-4`), correctly not present in BIS catalogue. |
| **Total Curated Standards** | **90** | **100.0%** | **All 83 actual single BIS standards have direct or normalized equivalents in the catalogue.** |

---

## 3. Representative Matched & Unmatched Records Analysis

### 3.1 Representative Exact Matches

| Standard ID | Curated Title (`standards.db`) | Catalogue Title (`bis_catalogue.db`) | Curated Scope Populated? | Catalogue Scope Populated? | Curated Status | Catalogue Status |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **`IS-778-1984`** | Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes | Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes (Fourth Revision) | **Yes** (182 words) | **No** (NULL) | Active (Reaffirmed 2020) | ACTIVE |
| **`IS-1180-Part-1-2014`** | Outdoor Type Oil Immersed Distribution Transformers | Outdoor Type Oil Immersed Distribution Transformers Upto and Including 2500 kVA, 33 kV Specification: Part 1 Mineral Oil Immersed | **Yes** (214 words) | **No** (NULL) | Active | ACTIVE |
| **`IS-4984-2016`** | Polyethylene Pipes for Water Supply — Specification | Polyethylene Pipes for Water Supply - Specification (Fifth Revision) | **Yes** (195 words) | **No** (NULL) | Active | ACTIVE |
| **`IS-15328-2003`** | Unplasticized Non-Pressure Underground Drainage and Sewerage Systems | Plastics piping systems for non-pressure underground drainage and sewerage - Unplasticized poly(vinyl chloride) (PVC-U) | **Yes** (176 words) | **No** (NULL) | Active | ACTIVE |

### 3.2 Representative Formatting & Syntax Variants

1. **`IS-7098-(Part-1)-1988` (Curated) vs `IS-7098-Part-1-1988` (Catalogue)**
   - *Title:* Specification for crosslinked polyethylene insulated PVC sheathed cables: Part 1 for working voltages up to and including 1 100 volts (First Revision)
   - *Cause:* The curated database used parentheses in the standard ID slug (`-(Part-1)-`), whereas the catalogue normalizer strictly uses hyphen separation (`-Part-1-`).
   - *Identity:* 100% identical standard.

2. **`IS-IEC-61439-3-2012` (Curated) vs `IS-IEC-61439-Part-3-2012` (Catalogue)**
   - *Title:* Low - Voltage switchgear and controlgear assemblies: Part 3 distribution boards intended to be operated by ordinary persons (Dbo)
   - *Cause:* Curated record adopted standard IEC notation without the explicit `-Part-` literal token.
   - *Identity:* 100% identical standard.

### 3.3 Representative Edition / Revision Year Deltas

| Standard | Curated Database | National BIS Catalogue | Analysis / Explanation |
| :--- | :--- | :--- | :--- |
| **IS 2712** | `IS-2712-2020` (Status: Active) | `IS-2712-2024` (Status: UNKNOWN)<br>`IS-2712-1998` (Status: WITHDRAWN) | Curated database recorded the 2020 reaffirmation of the standard; the national catalogue was recently updated to reflect the 2024 full revision (`Gaskets and Packings — Compressed Asbestos Fibre Jointing`). |
| **IS 1239 Part 2** | `IS-1239-(Part-2)-1992` (Status: Active) | `IS-1239-Part-2-2011` (Status: UNKNOWN) | Curated database holds the 1992 edition; the national catalogue lists the superseded 2011 revision (`Steel Tubes, Tubulars and Other Wrought Steel Fittings`). |
| **IS 16088** | `IS-16088-2016` (Status: Active) | `IS-16088-2012` (Status: UNKNOWN) | Curated database recorded the 2016 reaffirmation year; the catalogue reflects the original 2012 publication year (`Chlorinated polyvinyl chloride (CPVC) pipes for automatic sprinkler fire extinguishing system`). |
| **IS 101 Part 5 Sec 4** | `IS-101-Part-5-Sec-4-2026` (Status: Active) | `IS-101-Part-5-Sec-4-1988` (Status: UNKNOWN) | Curated database contains an anticipated revision year (2026), whereas the active published standard in the catalogue remains the 1988 edition (`Print free test (Third Revision)`). |
| **IS/IEC 60034 Part 1** | `IS-IEC-60034-1-2017` (Status: Active) | `IS-IEC-60034-Part-1-2022` (Status: ACTIVE) | Curated database has the 2017 adoption; BIS published a revised adoption in 2022. |

### 3.4 Non-Standard Curated Entries (Unmatched in BIS Catalogue)

1. **`FSSAI-Schedule-4`**:
   - *Curated Role:* Food safety statutory regulation (General hygienic and sanitary practices to be followed by food business operators).
   - *Catalogue Presence:* Absent from `bis_catalogue.db` because FSSAI is a statutory regulatory authority under the Ministry of Health and Family Welfare, not a BIS standard.
2. **`SP-18-Part-2-to-4-1984`, `SP-18-Part-5-to-7-1982`, `SP-18-Part-8-to-10-1984`, `SP-18-Part-12-to-15-1984`**:
   - *Curated Role:* Multi-part ISI Handbook of Food Analysis compendia.
   - *Catalogue Presence:* In `bis_catalogue.db`, SP 18 records are indexed under individual part numbers (e.g., `SP-18-Part-1-1980`, `SP-18-Part-810-1984`), not range-bundled slugs.
3. **`IS-2556-(Parts-1,-2,-4)`**:
   - *Curated Role:* Composite procurement bundle for vitreous sanitary appliances.
   - *Catalogue Presence:* Indexed individually in `bis_catalogue.db` (`IS-2556-Part-1-2021`, `IS-2556-Part-2-2004`, `IS-2556-Part-4-1994`).

---

## 4. Tender Recommendation Pipeline Execution Trace

To definitively verify how the system behaves during tender evaluation, we traced the execution flow from tender upload through candidate generation:

```
Tender Document Upload / Requirement Text
                  │
                  ▼
   src/recommend.py: StandardsRecommender
                  │
                  ▼
   src/retrieval.py: HybridRetrievalEngine
                  │
  ┌───────────────┼───────────────┐
  ▼               ▼               ▼
BM25SearchEngine  SemanticSearch  StandardsSearchEngine
(src/bm25_search) (src/semantic)  (src/search.py)
  │               │               │
  └───────────────┼───────────────┘
                  ▼
     StandardsDatabase() default:
     "data/standards/standards.db" (90 records)
```

### Detailed Pipeline Inspection:
1. **Instantiation**: `StandardsRecommender(db=None)` creates `HybridRetrievalEngine(db=None)`.
2. **Database Binding**: `HybridRetrievalEngine` binds to `self.db = db or StandardsDatabase()`.
3. **Default Connection**: `StandardsDatabase.__init__(db_path="data/standards/standards.db")`.
4. **BM25 Ingestion & Caching**:
   - `BM25SearchEngine.build_from_db()` executes `SELECT * FROM standards` on `standards.db`.
   - Concatenates: `standard_number + " " + full_title + " " + scope + " " + notes + " " + tc`.
   - Caches tokenized term frequencies in `data/standards/bm25_index.json` (**strictly 90 documents**).
5. **Dense Semantic Embedding**:
   - `SemanticSearchEngine._build_or_load_index()` executes `SELECT * FROM standards` on `standards.db`.
   - Computes 384-dimensional dense vectors using `all-MiniLM-L6-v2`.
   - Caches embeddings in `data/standards/semantic_embeddings.npy` (**strictly 90 embeddings**).
6. **Candidate Generation**:
   - When a tender requirement is evaluated, `HybridCandidate` instances are generated **only from the 90 indexed records in `standards.db`**.
   - **`bis_catalogue.db` (35,208 records) is never queried during the tender recommendation retrieval phase.**

---

## 5. Feasibility of Recommending & Verifying Catalogue-Only Standards

### 5.1 Can Catalogue-Only Standards Be Recommended?
**Current State: No.**
- The recommendation engine has no access to the 35,118 catalogue-only standards.
- If a tender requires a standard present in `bis_catalogue.db` (e.g. `IS 456 : 2000` Plain and Reinforced Concrete, or `IS 1391` Room Air Conditioners), the hybrid retrieval engine will **fail to surface it** unless it is explicitly present in `standards.db`.

### 5.2 Can the System Verify Their Applicability with Supporting Evidence?
**Current State: No.**
- **Lack of Scope Text:** `bis_catalogue.db` contains titles and committee codes, but `scope` is `NULL` for all 35,208 records. The system cannot perform semantic similarity matching or rule-based clause verification without scope text.
- **Lack of Parameter-Level Evidence:** The evidence support validation engine (`src/audit.py`, `src/precedence/conflict_engine.py`, `src/evidence/support_engine.py`) requires structured technical specifications (e.g., pressure ratings, temperature limits, nominal diameters, voltage grades, test methods). `bis_catalogue.db` contains none of this technical data.
- **Risk of Fabricated Evidence:** If catalogue-only standards were exposed to an LLM or ungrounded heuristic to "guess" applicability based on title alone, it would violate the project's non-negotiable safety invariant: **"Do not mark any record verified without authoritative evidence."**

---

## 6. Knowledge Graph Ingestion Mechanism & Isolated Nodes

### 6.1 How the Graph Obtains Nodes and Edges
In `src/graph.py` and `api/server.py`:
1. **Nodes**:
   - Loaded from `standards.db` via `_resolve_standard_info()`.
   - When `/api/standards/<id>/neighbors` is invoked, the focal node metadata is retrieved directly from `standards.db`.
2. **Edges**:
   - Loaded from `standards.db` (`standard_relationships` and `standard_references` tables).
   - Merged in-memory with `data/standards/relationships.json` (72 curated edges).
   - Deduplicated on `(source_digits, target_digits, relationship_type, direction)`.
   - Only edges with explicit provenance (`VERIFIED` or `CURATED`) are permitted.

### 6.2 Can Catalogue Records Appear as Isolated Nodes?
**Yes, safely and compliantly.**
- If a standard from the national catalogue is ingested into the knowledge graph registry without verified relationships:
  - It resolves as a **valid node** with authoritative metadata (Title, Status, Technical Committee, Year, BIS source URL).
  - Its neighbor list returns `edges = []` (degree 0).
  - In the SVG frontend visualizer, it renders as a single standalone node.
- **Safety Invariant Maintained:** The system **never fabricates edges** based on title similarity, shared committee, or publication date. Showing isolated nodes accurately reflects that the standard exists in the national catalogue, but its normative network has not yet been audited.

---

## 7. Limitations Identified

1. **Retrieval Coverage Blind Spot:** The recommendation engine is strictly limited to 90 curated standards. It cannot recommend standards from the remaining 35,118 BIS standards even if a tender requirement explicitly cites them.
2. **Edition Synchronization Gaps:** 5 of the 90 curated standards have minor edition year drift compared to the national catalogue (e.g., IS 2712:2020 in curated vs IS 2712:2024 in catalogue). The curated database lacks an automated mechanism to refresh reaffirmation/revision statuses from `bis_catalogue.db`.
3. **Identifier Normalization Inconsistencies:** The curated dataset contains minor slug formatting divergences (e.g. `IS-7098-(Part-1)-1988` with parentheses vs `IS-7098-Part-1-1988`). While the API search handles these gracefully via token matching, canonical ID equality joins fail.
4. **Asymmetric Metadata Enrichment:** The national catalogue is 400x larger in record count, but 0% enriched in clause/scope text. Conversely, the curated database is 100% enriched in clause/scope text, but covers only ~0.25% of the national catalogue.

---

## 8. Recommended Target Data Architecture

To bridge the gap between national catalogue breadth and curated semantic depth without violating safety invariants, we recommend a **Two-Tier Federated Standards Architecture**:

```
                              ┌─────────────────────────────────────────┐
                              │           Tender Requirement            │
                              └────────────────────┬────────────────────┘
                                                   │
                         ┌─────────────────────────┴─────────────────────────┐
                         ▼                                                   ▼
            Tier 1: National Registry                           Tier 2: Deep Semantic Corpus
          (data/catalogue/bis_catalogue.db)                     (data/standards/standards.db)
               [35,208 Records]                                       [Curated Records]
                         │                                                   │
         ┌───────────────┴───────────────┐                                   │
         ▼                               ▼                                   ▼
  1. Exact Citation               2. Lifecycle &                    1. Hybrid Retrieval
     Lookup & Validation             Currency Audit                    (BM25 + Dense Vectors)
  • Direct Regex/IS Match         • Active vs Withdrawn             2. Scope Clause Verification
  • Resolves 35k Standards        • Superseded Edition Alert        3. Parameter Evidence Checks
  • Surfaces Isolated Nodes       • Amendment Count Verification    4. Explicit Graph Traversal
         │                               │                                   │
         └───────────────────────────────┼───────────────────────────────────┘
                                         ▼
                     ┌───────────────────────────────────────┐
                     │     Consolidated Recommendation       │
                     │  • Recommendation Candidate (Tier 2)  │
                     │  • Citation Verification (Tier 1)     │
                     │  • Currency/Status Flag (Tier 1)      │
                     │  • Evidence Support Score (Tier 2)    │
                     └───────────────────────────────────────┘
```

### Key Architectural Recommendations:

1. **Two-Stage Retrieval Pipeline**:
   - **Stage 1 (Exact Citation Resolver):** If a tender specification explicitly names a standard (e.g. *"Conforming to IS 456"*), query `bis_catalogue.db` first. If found, surface it immediately as a validated citation candidate with official metadata and currency status, even if scope text is absent.
   - **Stage 2 (Semantic & Parameter Retrieval):** For descriptive, un-cited requirements (e.g. *"Submersible pump for drainage"*), query `standards.db` where rich scope and parameter clauses enable hybrid semantic matching and evidence verification.

2. **Automated Lifecycle & Currency Cross-Auditing**:
   - Implement a read-only cross-referencing task where `standards.db` records query `catalogue_standards` to verify whether their status is `ACTIVE` or `WITHDRAWN`, and flag when a newer edition exists in the national catalogue (e.g. flagging IS 2712:2020 that IS 2712:2024 has been gazetted).

3. **Unified Identifier Normalization Rule**:
   - Enforce `StandardIdentifierNormalizer` (`src/catalogue/normalizer.py`) across both databases:
     - Remove parentheses from part/section designators (`(Part 1)` -> `Part-1`).
     - Standardize international adoption prefixes (`IS/IEC` -> `IS-IEC-Part-X`).
     - Store both `canonical_id` and raw display `standard_number` consistently.

4. **Isolated Node Ingestion for the Knowledge Graph**:
   - Allow national catalogue standards to be queried on the Standards Graph page `/standards-graph`.
   - If a user searches for an unlinked catalogue standard, render it as an **isolated node** (degree 0) with a badge: `Status: National Catalogue Entry (Unlinked - No Normative References Audited)`.
   - This expands the user's exploratory capability across all 35,000 standards without inventing unverified connections.

---

## 9. Conclusion

The audit confirms that the curated dataset and the national catalogue serve complementary, non-competing purposes:
- `bis_catalogue.db` provides the **national ground truth of existence, committee governance, and official publication status**.
- `standards.db` provides the **technical substance, clause-level semantics, parameter thresholds, and explicit relational evidence necessary for AI-driven tender compliance**.

Under current operations, the tender recommendation engine is safely insulated from hallucinations by querying only the verified, scope-bearing records in `standards.db`. The recommended Two-Tier Federated Architecture provides a safe, principled path to scale Tender Saathi's capabilities across the entire national standards repository without compromising evidence integrity.
