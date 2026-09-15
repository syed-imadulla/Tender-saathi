# Phase 4R12 — Authoritative BIS Semantic-Enrichment Feasibility Investigation

**Investigation Status**: COMPLETED (Investigation Only — Zero Production Changes)  
**Date**: September 2026  
**Scope**: Bureau of Indian Standards (BIS) Public Metadata, Catalogue Ingestion Schema, Licensing Governance, and Diagnostic Retrieval Simulation  
**Target Dataset**: Frozen 19-Query Benchmark & Complete BIS Master Catalogue ($N = 35,208$)  
**Raw Data Artifact**: [`reports/phase4r12_bis_metadata_feasibility_data.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/reports/phase4r12_bis_metadata_feasibility_data.json)

---

## Executive Summary

Phase 4R11 established that the primary semantic retrieval bottleneck in TenderSaathi is the absence of technical scope and domain context in the standards catalogue, forcing `all-MiniLM-L6-v2` to rely strictly on short standard titles. Phase 4R12 investigated whether **authoritative, publicly published BIS metadata** can safely and legally be ingested to solve this bottleneck without generating synthetic, unverified descriptions.

### Key Conclusions:
1. **Zero Technical Scope Availability**: Across the entire BIS master catalogue of 35,208 standards, **exactly 0 standards (0.00%)** have non-empty `scope`, `abstract`, `keywords`, or `ICS code` fields in the structured public API/database.
2. **Administrative vs. Technical Metadata**: Authoritative metadata fields that do exist—such as Technical Committee names (99.66%) and Document Aspect (89.44%)—reflect **administrative drafting ownership** and **procedural document genre**, not engineering specifications or technical applicability.
3. **Severe Copyright and Licensing Gating**: While metadata (titles, committee designations, years) is open under Government of India website policies, the actual technical text of standard clauses (including Clause 1 "Scope") is strictly copyrighted by BIS under the BIS Act, 2016 and Indian Copyright Act, 1957. Bulk extraction and local redistribution require formal permission via BIS **Form A** from the National Institute of Training for Standardization (NITS).
4. **Diagnostic Retrieval Degradation**: Enriching the standard representations with available authoritative metadata (Aspect + official Sectional Committee Title) **regressed semantic retrieval performance**:
   - **Hit@1**: $5.3\% \rightarrow 5.3\%$ ($+0.0\%$)
   - **Recall@10**: $21.1\% \rightarrow 15.8\%$ ($-5.3\%$)
   - **Recall@50**: $63.2\% \rightarrow 52.6\%$ ($-10.5\%$)
   - **Recall@100**: $73.7\% \rightarrow 68.4\%$ ($-5.3\%$)
   - **MRR**: $0.1207 \rightarrow 0.1050$ ($-0.0157$)
   - Crucially, unretrieved umbrella standards (`SP 30`, `IS 732` for T009-R001; `IS 5039`, `IS 16088`, `IS 2491`, `IS/IEC 61800-2`) remained **completely unretrieved (>150)**.
5. **Final Classification**: **OPTION 4** — *Authoritative technical metadata is not sufficiently available; another retrieval approach must be investigated.*

---

## Section 1: Observed BIS Facts

### Official BIS Architecture & Data Sources
Three authoritative online systems publish Indian Standards metadata:
1. **BIS "Know Your Standards" (services.bis.gov.in)**: A public-facing DataTables-driven search portal providing tabular metadata (`is_no`, `is_title`, `amendments`, `technical_committee`, `aspect`, `referirmatin_year`).
2. **BSB Edge / BIS Standards Portal (standardsbis.bsbedge.com)**: The official digital sales and distribution platform for Indian Standards, providing document view/download links, pricing information, and basic committee/status metadata.
3. **BIS Central Portal (bis.gov.in)**: The institutional portal defining Standardization Technical Departments (CED, ETD, MED, MTD, etc.) and their subordinate Sectional Committees, their titles, and general committee scopes.

### Comprehensive Audit of Requested Metadata Fields (Phase A)

| # | Field Name | Available? | Authoritative Source | Catalogue Coverage | Example for Sampled Standards | Technical Usefulness for Semantic Search | Safe to Ingest? |
|---|---|---|---|---|---|---|---|
| 1 | **Standard Number** | **YES** | BIS Know Your Standards (`is_no`) | 35,208 / 35,208 (100.0%) | `SP 30 : 2023`, `IS 732 : 2019` | High for exact regex/token matching; zero conceptual context | **YES** (In prod) |
| 2 | **Title** | **YES** | BIS Know Your Standards (`is_title`) | 35,208 / 35,208 (100.0%) | `Code of practice for electrical wiring installations` | Primary semantic anchor; often concise, missing domain vocabulary | **YES** (In prod) |
| 3 | **Scope** | **NO** (in DB/API)<br>**YES** (in PDF) | Clause 1 ("Scope") inside individual copyrighted standard PDFs | **0 / 35,208 (0.00%)** | *Empty in catalogue.* Inside PDF: "Covers general principles of electrical wiring..." | Highest possible technical context, but unavailable in structured data | **NO / RESTRICTED** (Requires Form A) |
| 4 | **Abstract** | **NO** | Not published by BIS | **0 / 35,208 (0.00%)** | *None* | N/A | **NO** (Does not exist) |
| 5 | **Subject** | **NO** | Not published as distinct field | **0 / 35,208 (0.00%)** | *None* | N/A | **NO** (Does not exist) |
| 6 | **Keywords** | **NO** | Not indexed per standard | **0 / 35,208 (0.00%)** | *None* (Only site-level SEO meta keywords) | N/A | **NO** (Does not exist) |
| 7 | **Committee Name** | **YES** | BIS Technical Departments Directory | 35,088 / 35,208 (99.66%) | `ETD 20` $\rightarrow$ "Electrical Installations Sectional Committee" | Moderate for high-level domain routing; causes severe semantic clustering | **UNCERTAIN** (Dilutes titles) |
| 8 | **Committee Scope** | **YES** (Committee level) | BIS Sectional Committee Directory | Available at committee level only | ETD 20: "To prepare standards for safety in designing, erection, and maintenance..." | Reflects committee mandate, NOT standard applicability | **NO** (Causes false associations) |
| 9 | **Product Group** | **NO** | Nearest proxy is `aspect` | **0 / 35,208 (0.00%)** | *None* | Low | **NO** (Does not exist) |
| 10 | **Classification / Aspect** | **YES** | BIS Know Your Standards (`aspect`) | 31,490 / 35,208 (89.44%) | `Code of Practice`, `Product Specification`, `Methods of tests` | Identifies normative document genre; lacks domain concepts | **YES** (Metadata only) |
| 11 | **ICS Code** | **NO** (in DB/API) | Present only on select standard PDF covers | **0 / 35,208 (0.00%)** | *Empty in catalogue* | High if available, but completely missing from bulk export | **NO** (Unavailable) |
| 12 | **Amendments** | **YES** | BIS Know Your Standards (`amendments`) | 35,208 / 35,208 (100.0%) | `0`, `1`, `5` | Vital for lifecycle validation; zero semantic relevance | **YES** (Metadata only) |
| 13 | **Related Standards** | **PARTIAL** | BIS Know Your Standards (Segment 2 HTML) | 32,538 / 35,208 (92.42%) | `IEC 60034-1:2022`, `ISO 20283-2:2008` | High for international equivalence; minimal requirement matching | **YES** (Metadata only) |
| 14 | **Superseding / Status** | **YES** | BIS Know Your Standards (`status`) | 35,208 / 35,208 (100.0%) | `ACTIVE`, `WITHDRAWN`, `(Fourth Revision)` | Critical for lifecycle validation; zero technical descriptive value | **YES** (In prod) |
| 15 | **Other Descriptive Fields**| **NO** | Not published in catalogue | **0 / 35,208 (0.00%)** | *None* (No voltage, pressure, material fields) | N/A | **NO** (Does not exist) |

---

## Section 2: Coverage Measurement Across Catalogue ($N = 35,208$)

Measurements were conducted directly on `data/catalogue/bis_catalogue.db` across the master tables `standards` and `catalogue_standards`:

```
========================================================================================
Catalogue-Wide Metadata Coverage Audit (Total Records: 35,208)
========================================================================================
Field Name                       Database Table        Non-Empty Count    Coverage Pct
----------------------------------------------------------------------------------------
standard_number                  standards             35,208             100.00%
full_title                       standards             35,208             100.00%
technical_committee (code)       standards             35,088              99.66%
department (prefix)              catalogue_standards   35,088              99.66%
status (ACTIVE / WITHDRAWN)      standards             35,208             100.00%
amendments_count                 standards             35,208             100.00%
notes (harmonization status)     standards             35,208             100.00%
iso_equivalence (international)  catalogue_standards   32,538              92.42%
aspect (document genre)          catalogue_standards   31,490              89.44%
part (standard part number)      catalogue_standards   12,508              35.53%
section (standard section)       catalogue_standards    1,929               5.48%
scope (technical scope text)     standards                  0               0.00%
abstract (document abstract)     standards                  0               0.00%
keywords (technical terms)       standards                  0               0.00%
ics (ICS classification)         standards                  0               0.00%
udc (Universal Decimal Class)    standards                  0               0.00%
reaffirmed_year                  standards                  0               0.00%
========================================================================================
```

### Breakdown of Key Categorical Fields:
- **Aspect Distribution ($N = 31,490$)**:
  - `Product Specification`: 15,052 (47.8%)
  - `Methods of tests`: 6,668 (21.2%)
  - `Code of Practice`: 3,846 (12.2%)
  - `Others`: 2,707 (8.6%)
  - `Terminology`: 1,200 (3.8%)
  - `Dimensions`: 948 (3.0%)
  - `Safety Standard`: 482 (1.5%)
  - `System Standard`: 262 (0.8%)
  - `Service Specification`: 201 (0.6%)
  - `Process Specification`: 124 (0.4%)
  - *Missing / Null*: 3,718 (10.6% of total catalogue)
- **Technical Committees**:
  - 391 distinct Sectional Committees across 17 Standardization Departments (PGD, FAD, CHD, ETD, LITD, MHD, TXD, CED, MED, MTD, PCD, TED, MSD, WRD, AYD, SSD, EED).

---

## Section 3: Representative Standard Audit (Phase C & D)

An exhaustive audit was conducted for 10 representative standards from the frozen benchmark, focusing particularly on umbrella standards (`SP 30`, `IS 732`, `IS 3043`):

| Standard | Exact Title (Source Text) | Scope in Catalogue | Technical Committee | Official Committee Title | Published Aspect | Other Technical Metadata in Portal |
|---|---|---|---|---|---|---|
| **SP 30 : 2023** | `NATIONAL ELECTRICAL CODE OF INDIA 2023 (Second Revision)` | `None` (0 bytes) | `ETD 20` | Electrical Installations Sectional Committee | `Code of Practice` | Commercial note: "Print price :8330.00 INR (in India)" |
| **IS 732 : 2019** | `Code of practice for electrical wiring installations (Fourth Revision)` | `None` (0 bytes) | `ETD 20` | Electrical Installations Sectional Committee | `Code of Practice` | Equivalence: "Modified/Technically Equivalent" |
| **IS 3043 : 2018** | `Code of practice for earthing (Second Revision)` | `None` (0 bytes) | `ETD 20` | Electrical Installations Sectional Committee | `Code of Practice` | Equivalence: "Modified/Technically Equivalent" |
| **IS/IEC 60034 (Part 1) : 2022** | `Rotating electrical machines - Part 1: Rating and performance` | `None` (0 bytes) | `ETD 15` | Rotating Machinery Sectional Committee | `Code of Practice` | Equivalence: `IEC 60034-1:2022` |
| **IS/IEC 61800 (Part 2) : 2015** | `Adjustable Speed Electrical Power Drive Systems Part 2 General Requirements — Rating Specifications...` | `None` (0 bytes) | `ETD 31` | Power Electronics Sectional Committee | `Product Specification` | Equivalence: `IEC 61800-2 : 2015` |
| **IS 16088 : 2012** | `Chlorinated polyvinyl chloride (CPVC) pipes for automatic sprinkler fire extinguishing system - Specification` | `None` (0 bytes) | `CED 22` | Fire Fighting Sectional Committee | `Product Specification` | Status: `Active`, Indigenous |
| **IS 6392 : 2020** | `Steel Pipes Flanges — Specification ( First Revision )` | `None` (0 bytes) | `MTD 19` | Steel Tubes, Pipes and Fittings Sectional Committee | `Product Specification` | Status: `ACTIVE`, Indigenous |
| **IS 2712 : 2024** | `Gaskets and Packings Compressed Asbestos Fibre Jointing Specification` | `None` (0 bytes) | `MED 30` | Gaskets and Packing Sectional Committee | `Product Specification` | Status: `Active`, Indigenous |
| **IS 7098 (Part 1) : 2025** | `Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables - Specification Part 1 For Working Voltages up to and Including 1 100 Volts` | `None` (0 bytes) | `ETD 09` | Power Cables Sectional Committee | `Product Specification` | Status: `Active`, Indigenous |
| **IS 5039 : 1983** | `Specification for distribution pillars for voltages not exceeding 1000 V AC and 1200 V DC (First Revision)` | `None` (0 bytes) | `ETD 07` | Low Voltage Switchgear and Controlgear Sectional Committee | `Product Specification` | Status: `WITHDRAWN`, Indigenous |

### Deep-Dive: Umbrella Standards (Phase D)
- **SP 30 : 2023 (National Electrical Code of India)**:
  - Practical engineering reality: SP 30 is a massive multi-part standard (over 1,000 pages across 8 parts) governing building wiring, industrial electrical design, earthing, substation maintenance, hazardous location wiring, and hospital electrical installations.
  - Authoritative BIS metadata: The standard record exposes only the title string `"NATIONAL ELECTRICAL CODE OF INDIA 2023"`. There is **zero structured metadata** listing its sections, equipment types, or maintenance guidelines.
  - The BSB Edge portal explicitly hides the document contents behind an 8,330 INR pre-printed book purchase / watermarked login barrier.
- **IS 732 : 2019 (Electrical Wiring Installations)**:
  - Practical engineering reality: Governs selection of cables, conduits, testing of installations, insulation resistance testing, and earth fault protection.
  - Authoritative BIS metadata: Exposes only `"Code of practice for electrical wiring installations"`. No clause summaries, test method keywords, or maintenance guidelines are published in any open metadata feed.
- **IS 3043 : 2018 (Earthing)**:
  - Practical engineering reality: Details soil resistivity, earth pit construction, pipe/plate/rod electrodes, and equipotential bonding.
  - Authoritative BIS metadata: Exposes only `"Code of practice for earthing"`.

**Conclusion on Umbrella Standards**: BIS publishes **no open structured technical scope metadata** explaining the practical engineering applications of umbrella standards. Ingesting their scope requires either extracting full text from copyrighted PDFs or generating synthetic descriptions.

---

## Section 4: Source and Licensing Constraints (Phase E)

| Use Case | Permitted by BIS? | Authoritative Source / Legal Basis | Risk Level / Constraints |
|---|---|---|---|
| **Storing Metadata Locally** | **YES** | National Data Sharing and Accessibility Policy (NDSAP) & BIS Website Terms | **LOW**: Standard numbers, titles, committee codes, and publication years are factual government gazette data. |
| **Storing Scope Text** | **NO / UNCERTAIN** | Bureau of Indian Standards Act, 2016; Indian Copyright Act, 1957; BIS Copyright Policy | **HIGH**: Full standards documents and clause extracts are copyrighted intellectual property. BIS requires formal approval via **"Form – A: Request for Reproducing Extracts from Indian Standards"** directed to the National Institute of Training for Standardization (NITS). |
| **Indexing Metadata for Internal Search** | **YES** | Standard fair use of bibliographic metadata | **LOW**: Permissible for internal query matching. |
| **Indexing Full Scope for Search** | **UNCERTAIN** | Section 52, Indian Copyright Act, 1957 (Fair dealing for research vs commercial use) | **HIGH**: Storing and embedding thousands of extracted clauses without licensing agreements creates copyright infringement exposure. |
| **Periodic Catalogue Synchronization** | **YES** | Publicly accessible DataTables endpoints | **LOW**: Operational rate-limiting applies; no DRM circumvention. |
| **Using Metadata in Semantic Embeddings** | **YES** | Technological processing of legally held metadata | **ZERO LEGAL RISK** for published metadata; however, **TECHNICAL USEFULNESS IS DEGRADED** (see Section 5). |

---

## Section 5: Retrieval Usefulness Simulation (Phase F)

A diagnostic experiment was executed across all 35,208 catalogue standards on the frozen 19-query benchmark to measure the exact impact of enriching document representations with available authoritative metadata.

### Representations Compared:
- **D1 (Current Production Baseline)**:  
  `"{std_num} : {title}. Scope: . Notes: {notes}. Committee: {tech_comm}"`  
  *(where `scope` is empty string; `notes` is e.g. "Indigenous"; `tech_comm` is e.g. "ETD 20")*
- **D2 (Authoritative Metadata Enriched)**:  
  `"{std_num} : {title}. Scope: . Notes: {notes}. Committee: {tech_comm} - {committee_title}. Aspect: {aspect}."`  
  *(Enriched strictly with official Sectional Committee names verified from `bis.gov.in` and authoritative `aspect` classifications from `catalogue_standards`)*

### Comparative Benchmark Metrics ($N = 19$):

```
========================================================================================
COMPARATIVE SEMANTIC RETRIEVAL PERFORMANCE (D1 vs D2)
========================================================================================
Metric         D1 (Baseline)          D2 (Authoritative Enriched)    Net Delta
----------------------------------------------------------------------------------------
Semantic Hit@1       1 / 19 ( 5.3%)         1 / 19 ( 5.3%)             +0.0%
Semantic Recall@10   4 / 19 (21.1%)         3 / 19 (15.8%)             -5.3% (Regression)
Semantic Recall@15   6 / 19 (31.6%)         6 / 19 (31.6%)             +0.0%
Semantic Recall@30   8 / 19 (42.1%)         8 / 19 (42.1%)             +0.0%
Semantic Recall@50  12 / 19 (63.2%)        10 / 19 (52.6%)            -10.5% (Severe Regression)
Semantic Recall@100 14 / 19 (73.7%)        13 / 19 (68.4%)             -5.3% (Regression)
Semantic MRR        0.1207                 0.1050                     -0.0157 (Regression)
========================================================================================
```

### Per-Query Semantic Rank Changes:

| Query ID | Tender Requirement Summary | Expected Standard | D1 Rank | D2 Rank | Delta | Technical Observation |
|---|---|---|---|---|---|---|
| **T001-R002** | Hubless pipeline replacement | IS 15905 / IS 1239-1 | 48 | 96 | **-48 REG** | Diluted by generic MTD committee tokens |
| **T001-R003** | Wall tiles | IS 15622 | 41 | 24 | **+17 IMP** | Benefited slightly from "Flooring, Wall Finishing" |
| **T001-R004** | Sanitary fittings | IS 2556 / IS 781 / IS 774 | 5 | 3 | **+2 IMP** | Minor gain from "Sanitary Appliances" committee |
| **T002-R003** | Flange Joint Maintenance | IS 6392 / IS 2712 | 11 | 20 | **-9 REG** | **Dropped OUT of top-15** candidate pool |
| **T003-R001** | Distribution boards / repair | IS/IEC 61439-3 | 35 | 49 | **-14 REG** | Pushed down by competing electrical committees |
| **T004-R002** | Power cables outside elect. room | IS 7098-1 / IS 1255 | 25 | 60 | **-35 REG** | Pushed down by general power apparatus |
| **T004-R005** | Feeder pillar reinstallation | IS 5039 / IS/IEC 61439-5 | **None** | **None** | **Unchanged** | Completely unretrieved (>150) in both |
| **T005-R001** | Cable connection of DG Set | IS 3043 / IS 7098-1 | 40 | 15 | **+25 IMP** | Reached rank 15 via "Power Cables" committee |
| **T006-R001** | UPVC Partition Wall Work | IS 16088 | **None** | **None** | **Unchanged** | Completely unretrieved (>150) in both |
| **T007-R003** | Low-Oil Food Outlet on BOT | IS 2491 / IS 15000 | **None** | **None** | **Unchanged** | Completely unretrieved (>150) in both |
| **T009-R001** | Annual repairs / electrical services | SP 30 / IS 732 | **None** | **None** | **Unchanged** | **Zero recovery for SP 30 or IS 732** |
| **T010-R001** | Sewerage Pipeline works | IS 458 / IS 783 / IS 14333 | 1 | 4 | **-3 REG** | **Lost Hit@1 position** |
| **T011-R001** | Underground cable for STP | IS 7098-1 / IS 1255 | 14 | 36 | **-22 REG** | **Dropped OUT of top-15** candidate pool |
| **T012-R002** | Plaster Repairing | IS 1661 / IS 269 | 16 | 12 | **+4 IMP** | Minor gain |
| **T012-R003** | Plumbing Fittings | IS 1239-2 / IS 778 | 67 | **None** | **-LOST** | **Completely dropped out of top-150** |
| **T013-R002** | SITC of VFD water pump panel | IS/IEC 61800-2 | **None** | **None** | **Unchanged** | Completely unretrieved (>150) in both |
| **T013-R003** | Thermal Insulation work | IS 14164 / IS 8183 | 5 | 12 | **-7 REG** | Dropped 7 positions |
| **T014-R002** | Process Water Pump motors | IS/IEC 60034-1 / IS 5120 | 64 | 87 | **-23 REG** | Diluted by rotating machinery committee tokens |
| **T020-R001** | CPVC pipe in lieu of GI pipe | IS 15778 / IS 1239-1 | 2 | 1 | **+1 IMP** | Reached Hit@1 |

---

## Section 6: Safety Test & Semantic Contamination Analysis (Phase G)

The diagnostic simulation provides empirical proof that adding administrative metadata fields introduces serious semantic hazards:

1. **Semantic Dilution from Generic Procedural Vocabulary**:
   - The token `"Product Specification"` appears in 15,052 standards (47.8% of all standards with aspect data).
   - The token `"Code of Practice"` appears in 3,846 standards.
   - Appending these broad strings to standard documents reduces the cosine angular distance between completely unrelated standards (e.g. ceramic tile specifications and high-voltage switchgear specifications), washing out distinctive product nouns.
2. **False Clustering Driven by Administrative Committee Titles**:
   - An engineering sectional committee (e.g., `CED 05: Flooring, Wall Finishing and Roofing`) manages dozens of distinct standards covering clay tiles, bitumen felt, linoleum, plastering, and metal roofing sheets.
   - Injecting `"Flooring, Wall Finishing and Roofing"` causes all CED 05 standards to cluster together. When a tender mentions `"roofing"`, plastering standards receive artificially inflated similarity scores.
3. **Severe Regressions in Tightly Scoped Queries**:
   - In `T011-R001` (`"Providing and laying underground cable..."`), the correct standard `IS 1255` dropped from Rank 14 to Rank 36 because scores of competing power apparatus standards under ETD surged due to shared electrotechnical committee vocabulary.
   - In `T012-R003` (`"Plumbing Fittings"`), `IS 1239 (Part 2)` was **completely knocked out of the top-150** (Rank 67 $\rightarrow$ None).
4. **Administrative Ownership vs. Technical Scope**:
   - BIS Technical Committees represent bureaucratic jurisdiction, not technical properties. Treating committee title as technical applicability violates the fundamental principle that metadata must describe *the standard itself*, not its organizational parent.

---

## Section 7: Interpretation & Root-Cause Synthesis

1. **Why D2 Failed to Recover T009-R001 (`SP 30` / `IS 732`)**:
   - The tender query explicitly mentions: `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"`.
   - The title of `SP 30 : 2023` is `"NATIONAL ELECTRICAL CODE OF INDIA 2023"`.
   - Adding `Committee: ETD 20 - Electrical Installations Sectional Committee. Aspect: Code of Practice` provides the terms `"electrical"`, `"installations"`, and `"code"`.
   - However, hundreds of other electrotechnical standards also possess those exact tokens (e.g., `IS 10118 : Code of practice for selection, installation and maintenance of switchgear`, `IS 2082`, `IS 5216`). Because those competing standards also contain `"maintenance"` or `"switchgear"`, they outrank `SP 30`.
   - `SP 30` remains unretrievable by semantic similarity alone because `all-MiniLM-L6-v2` has no access to the 1,000 pages of technical scope showing that Section 3 of SP 30 covers institutional facilities like Food Storage Depots (FSD).
2. **The Fundamental Asymmetry Between Lexical and Semantic Channels**:
   - As demonstrated in Phase 4R9 and 4R11, **BM25 easily retrieves `SP 30` at Rank 2** because BM25 exploits exact and partially matching acronyms/tokens without being misled by generic embedding distributions.
   - Semantic retrieval using dense sentence embeddings fails whenever standard titles are high-level abstractions (`"National Electrical Code"`) that do not lexically overlap with the descriptive work requirements in public tenders.
3. **The Trap of Synthetic Generation**:
   - Generating synthetic scope descriptions using an LLM or scraping unauthorized third-party summaries creates severe hallucination risks, breaks catalogue provenance, and violates strict authoritative data integrity guarantees.

---

## Section 8: Final Classification (Phase H)

Based on the empirical, legal, and architectural findings of this investigation:

### Selected Classification: **OPTION 4**

> **OPTION 4: Authoritative technical metadata is not sufficiently available; another retrieval approach must be investigated.**

### Supporting Justification:
- **0.00% Catalogue Coverage**: Technical scope, abstracts, and engineering keywords do not exist in the structured BIS public database.
- **Copyright Licensing Barrier**: Clause-level scope text is locked inside copyrighted PDFs requiring formal permission under the BIS Act, 2016 and Indian Copyright Act, 1957.
- **Negative Empirical Utility**: Ingesting the metadata that *does* exist (Committee Titles and Document Aspects) regresses semantic retrieval across the benchmark (Recall@50 drops $-10.5\%$, Recall@10 drops $-5.3\%$, MRR drops $-0.0157$), while failing to recover a single unretrieved benchmark failure.

---

## Section 9: Safe Architectural Recommendation

Since modifying standard document representations with BIS administrative metadata is counterproductive and full technical scopes are legally and structurally unavailable, TenderSaathi must **NOT** attempt catalogue-side text enrichment.

Instead, the retrieval recall bottleneck must be solved entirely on the **query and fusion side**:
1. **Preserve Production Catalogue & Embeddings Unchanged**: Keep `bis_catalogue.db` and `bis_semantic_embeddings.npy` in their clean, authoritative, uncorrupted state.
2. **Asymmetric Channel Fusion (Candidate-Preserving RRF)**: Phase 4R9 proved that BM25 already retrieves `SP 30` at Rank 2 and `IS 732` at Rank 4. The failure occurred because multi-channel RRF penalized candidates that appeared only in the BM25 channel. Adjusting candidate selection or channel weighting so strong lexical hits are not discarded by semantic absence is mathematically sound and risk-free.
3. **Targeted Technical Query Normalization (Domain-Intent Expansion)**: Phase 4R10 showed that converting work descriptions into core engineering standards terminology (e.g. mapping `"Annual Repairs and Maintenance Contract for electrical services"` to `"national electrical code electrical installations wiring"`) enables successful retrieval without touching catalogue data.
4. **Enrich Metadata Schema Only for Downstream Filtering**: Store `aspect` (`Product Specification` vs `Code of Practice`) and `technical_committee` as structured database columns used strictly by **Rule-Based Post-Retrieval Arbitration** (e.g., preferring `Code of Practice` for repair tenders), rather than concatenating them into dense embedding strings.

---

*Report certified complete in accordance with Phase 4R12 protocol. Zero production code, indexes, or catalogue databases were modified.*
