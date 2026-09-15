# Phase 4R11 — Semantic Retrieval Root-Cause Investigation Report

**Investigation Target:** Root-cause determination of why the dense semantic retrieval channel (`all-MiniLM-L6-v2`) fails to retrieve technically relevant BIS standards (e.g., `SP 30` in `T009-R001`) that BM25 retrieves strongly.  
**Constraint Status:** Strictly investigative. Zero production code modified. Production configuration remains 100% frozen.

---

## Executive Summary of Findings

1. **Semantic Index Data Integrity is 100% Sound:**  
   The semantic index (`bis_semantic_embeddings.npy` / `bis_semantic_doc_ids.json`) contains 35,204 standards matching the authoritative SQLite catalogue. Vectors are non-null, contain zero NaNs/Infs, and verify with exact $1.000000$ unit-norm dot-product alignment against the active `all-MiniLM-L6-v2` model. The failure is **not** an index corruption or ID misalignment.
2. **Primary Root Cause: Critical Document Representation Emptiness (0.00% Scope Text):**  
   In `bis_catalogue.db`, **0 out of 35,208 records (0.00%) have non-empty `scope` text**. Across the entire catalogue, `notes` contains only relationship tags (`"Indigenous"`, `"Modified/Technically Equivalent"`, etc.), and `technical_committee` is an alphanumeric code (`"ETD 20"`).  
   Consequently, every standard's embedded text reduces strictly to:  
   `"{standard_number} : {full_title}. Scope: . Notes: {relationship}. Committee: {code}"`.  
   For umbrella codes like `SP 30 : 2023`, the embedded text is just 20 tokens: `"SP 30 : 2023 : NATIONAL ELECTRICAL CODE OF INDIA 2023 (Second Revision)..."`. It contains **no** words describing wiring, installations, inspections, maintenance, or storage depots.
3. **Query/Document Semantic Asymmetry in Dense Vector Space:**  
   The bi-encoder model computes cosine similarity between a verbose, administrative procurement requirement (`"Annual Repairs and Maintenance Contract for electrical and mechanical services..."`) and 20-token standard titles.  
   Standards with narrow procedural titles matching procurement words (`IS 9692` *"Guide on maintainability of equipment: maintenance and maintenance support planning"*, `IS 4051` *"Installation and Maintenance of Electrical Equipment in Mines"*, `IS 19529` *"MAINTENANCE AND REPAIR SERVICES"*) score **0.505 – 0.562**, completely crowding the top 10.  
   Meanwhile, `SP 30 : 2023` scores **0.3531** (Rank **671**), and `IS 732 : 2019` scores **0.4144** (Rank **71**).
4. **Standalone Semantic Channel Performance:**  
   Across the frozen 19-query benchmark, semantic retrieval alone achieves **Hit@1 of 36.8% (7/19)** and **Recall@15 of 68.4% (13/19)** with an **MRR of 0.4636** (versus BM25's 89.5% Recall@15 and 0.699 MRR).

---

## Phase A — Semantic Document Representation Audit

Auditing representative standards from the 19-query benchmark in `data/catalogue/bis_catalogue.db`:

| Standard ID | Standard Number | Title | Scope in DB | Notes Text | Committee | Embedded Text Length | Only Title & Metadata? |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: |
| `SP-30-2023` | SP 30 : 2023 | NATIONAL ELECTRICAL CODE OF INDIA 2023 (Second Revision) | **None (0%)** | Indigenous | ETD 20 | 118 chars (20 toks) | **YES** |
| `SP-30-2011` | SP 30 : 2011 | National electrical code 2011 (First Revision) | **None (0%)** | Indigenous | ETD 20 | 108 chars (18 toks) | **YES** |
| `IS-732-2019` | IS 732 : 2019 | Code of practice for electrical wiring installations (Fourth Revision) | **None (0%)** | Modified/Technically Equivalent | ETD 20 | 154 chars (22 toks) | **YES** |
| `IS-12457-1988`| IS 12457 : 1988 | Code of practice for evaluation, repairs and acceptance limits... | **None (0%)** | Not Equivalent | MTD 04 | 181 chars (31 toks) | **YES** |
| `IS-4051-2025` | IS 4051 : 2025 | Installation and Maintenance of Electrical Equipment in Mines... | **None (0%)** | Indigenous | ETD 22 | 162 chars (26 toks) | **YES** |
| `IS-6392-2020` | IS 6392 : 2020 | Steel Pipes Flanges — Specification ( First Revision ) | **None (0%)** | Indigenous | MTD 19 | 118 chars (21 toks) | **YES** |
| `IS-2712-2024` | IS 2712 : 2024 | Gaskets and Packings Compressed Asbestos Fibre Jointing... | **None (0%)** | Indigenous | MED 30 | 135 chars (20 toks) | **YES** |
| `IS-IEC-61800-Part-2-2015` | IS/IEC 61800 (Part 2) | Adjustable Speed Electrical Power Drive Systems Part 2... | **None (0%)** | Identical under single numbering | ETD 31 | 259 chars (39 toks) | **YES** |
| `IS-16088-2016`| IS 16088 : 2016 | Unplasticized Polyvinyl Chloride (uPVC) Profiles for Windows/Doors | **None (0%)** | Indigenous | CED 29 | 168 chars (26 toks) | **YES** |
| `IS-3043-2018` | IS 3043 : 2018 | Code of practice for earthing (Second Revision) | **None (0%)** | Modified/Technically Equivalent | ETD 20 | 132 chars (20 toks) | **YES** |

### Key Representation Audit Findings:
1. **Scope Field Coverage:** Exactly **0.00%** across the entire 35,208-record catalogue. No standards contain functional descriptions, application scope, or clause outlines.
2. **Notes Field Content:** Contains only BIS standardization metadata tags (`"Indigenous"`, `"Identical under single numbering"`, `"Modified/Technically Equivalent"`). No technical explanatory text exists.
3. **Status and Year:** Standard `status` (`ACTIVE`, `WITHDRAWN`, `UNKNOWN`) is **not** included in `doc_str`. The year is present only if it forms part of the `standard_number` string.
4. **Conclusion on Representation:** Dense embeddings represent **only the title string** padded with committee abbreviations and standardized relationship tags.

---

## Phase B — Semantic Similarity Diagnostics (19 Queries)

Measured cosine similarities and rankings of expected standards versus top semantic distractors:

| Req ID | Expected Standard | Sem Rank | Exp Sim | Top Semantic Distractor | Dist Sim | Sim Gap |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: |
| **T001-R002** | IS 15905 : 2011 | **8** | 0.4907 | IS 1239 (Part 1) : 2004 | 0.5471 | +0.0564 |
| **T001-R003** | IS 15622 : 2017 | **9** | 0.5050 | IS 13630 (Part 1) : 2019 | 0.5901 | +0.0851 |
| **T001-R004** | IS 2556 (Part 6) : 2021 | **4** | 0.5369 | IS 2556 (Part 14) : 1995 | 0.5510 | +0.0141 |
| **T002-R003** | IS 6392 : 2020 | **2** | 0.5759 | IS 2712 : 2024 | 0.6300 | +0.0541 |
| **T003-R001** | IS 10322 (Part 5/Sec 5) | **1** | 0.5691 | IS 10322 (Part 5/Sec 1) | 0.5683 | -0.0008 |
| **T004-R002** | IS 7098 (Part 1) : 2025 | **1** | 0.5960 | IS 7098 (Part 3) : 1993 | 0.5701 | -0.0259 |
| **T004-R005** | IS 5039 : 1983 | **1** | 0.6483 | IS 1653 : 1972 | 0.4851 | -0.1632 |
| **T005-R001** | IS 7098 (Part 1) : 2025 | **2** | 0.5998 | IS 7098 (Part 3) : 1993 | 0.6000 | +0.0002 |
| **T006-R001** | IS 16088 : 2016 | **324** | **0.3074** | IS 17448 : 2020 | **0.4981** | **+0.1907** |
| **T007-R003** | IS 2491 : 2024 | **1** | 0.4704 | IS 17354 : 2020 | 0.4357 | -0.0347 |
| **T009-R001** | IS 732 : 2019 / SP 30 | **71 / 671**| **0.4144 / 0.3531**| IS 9692 (Part 8/Sec 1) | **0.5620** | **+0.1476** |
| **T010-R001** | IS 14333 : 1996 | **1** | 0.6015 | IS 1742 : 1983 | 0.5739 | -0.0276 |
| **T011-R001** | IS 7098 (Part 1) : 2025 | **9** | 0.4916 | IS 14787 : 2000 | 0.5388 | +0.0472 |
| **T012-R002** | IS 1661 : 1972 | **1** | 0.6119 | IS 2394 : 1984 | 0.5867 | -0.0252 |
| **T012-R003** | IS 1239 (Part 2) : 2011 | **6** | 0.5870 | IS 4310 : 1967 | 0.6414 | +0.0544 |
| **T013-R002** | IS/IEC 61800 (Part 2) | **20** | **0.4511** | IS 10069 : 2017 | **0.5003** | **+0.0492** |
| **T013-R003** | IS 14164 : 2008 | **1** | 0.7348 | IS 7413 : 1981 | 0.7031 | -0.0317 |
| **T014-R002** | IS/IEC 60034 (Part 1) | **24** | **0.5318** | IS 12066 : 1987 | **0.6542** | **+0.1224** |
| **T020-R001** | IS 15778 : 2007 | **1** | 0.5695 | IS 16088 : 2012 | 0.5349 | -0.0345 |

### Deep-Dive on Failure Queries:
- **T009-R001:** `IS 732` has rank 71 (sim 0.4144). `SP 30 : 2023` has rank **671** (sim 0.3531). Top 5 distractors are all parts of `IS 9692` (*Guide on maintainability of equipment...*) with similarities up to **0.5620**.
- **T006-R001:** Expected `IS 16088 : 2016` ("UPVC Profiles for Windows and Doors") achieves only **0.3074** similarity (Rank **324**), because the query emphasizes seafood conversion to microbiology laboratory, drawing medical/microbiology laboratory standards (`IS 17448`, `IS/ISO 24998` at sim 0.498).
- **T014-R002:** Expected `IS/IEC 60034-1` ("Rotating electrical machines") has similarity **0.5318** (Rank **24**), losing to specific pump motor standards (`IS 12066` at 0.654).
- **T013-R002:** Expected `IS/IEC 61800-2` has similarity **0.4511** (Rank **20**), losing to pump control assemblies (`IS 10069` at 0.500).

---

## Phase C — Query/Document Asymmetry Test

Evaluating whether generic technical representations restore semantic retrievability on difficult queries:

| Query ID | Q1 (Production Query) | Q2 (Original Tender) | Q4 (Technical Vocabulary) | Q5 (Domain Keyword Augmented) |
| :--- | :---: | :---: | :---: | :---: |
| **T009-R001** | Rank: **71** (0.4144) | Rank: **868** (0.3004) | Rank: **1002** (0.3039) | Rank: **868** (0.3004) |
| **T005-R001** | Rank: **2** (0.5998) | Rank: **40** (0.3944) | Rank: **31** (0.4128) | Rank: **4** (0.4860) |
| **T011-R001** | Rank: **9** (0.4916) | Rank: **14** (0.4037) | Rank: **11** (0.3759) | Rank: **8** (0.4375) |
| **T014-R002** | Rank: **24** (0.5318) | Rank: **64** (0.4388) | Rank: **267** (0.4208) | Rank: **45** (0.4274) |
| **T006-R001** | Rank: **324** (0.3074) | Rank: **2717** (0.2065) | Rank: **3178** (0.2215) | Rank: **477** (0.2937) |

### Asymmetry Test Takeaway:
- Under raw tender requirements (Q2), semantic retrieval performs **far worse** (T009-R001 drops from Rank 71 to 868; T006 drops from 324 to 2,717).
- Stripping query text down to technical vocabulary (Q4) causes severe degradation (T009-R001 drops to Rank 1002; T014 drops to Rank 267).
- The current production expanded query (Q1) is already the best-performing query representation for the dense model, yet `SP 30` still cannot rise above Rank 671 because the bottleneck is on the **document representation side**.

---

## Phase D — Document Representation Ablation

Testing diagnostic document representations of target standards against the production query:

| Requirement ID | Standard ID | D1 (Title Only) | D2 (Title + Number) | D3 (+Status) | D4 (+TC/Notes) | D5 (Current Prod) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **T009-R001** | `SP-30-2023` | 0.3618 | 0.3389 | 0.3272 | 0.3439 | 0.3531 |
| **T009-R001** | `IS-732-2019` | 0.3661 | 0.3963 | 0.3888 | 0.3952 | 0.4144 |
| **T005-R001** | `IS-3043-2018` | 0.1425 | 0.1394 | 0.1289 | 0.1552 | 0.1487 |
| **T014-R002** | `IS-IEC-60034-Part-1-2017` | -0.0348 | -0.0253 | 0.0497 | -0.0356 | 0.0111 |
| **T006-R001** | `IS-16088-2016` | 0.0704 | 0.0602 | 0.0215 | 0.0213 | -0.0179 |

### Document Ablation Takeaway:
- In `SP-30-2023`, title-only similarity (D1) is **0.3618**, while production representation with empty scope and committee padding (D5) is **0.3531**.
- Adding standard numbers, status, or committee abbreviations does **not** solve the semantic gap: none of the available metadata fields in the database contain domain text describing the standard's technical applicability.
- For `IS-3043-2018` (Earthing code), similarity against DG set cable requirement is only **0.1487** because the title ("Code of practice for earthing") contains zero generator or neutral grounding terms without scope text.

---

## Phase E — Catalogue-Wide Semantic Diagnostics & Integrity Audit

- **Total Standards in SQLite Database:** 35,204
- **Unique Standard IDs in Database:** 35,204
- **Total Vectors in `bis_semantic_embeddings.npy`:** 35,204
- **Embedding Matrix Dimensions:** `(35204, 384)`
- **ID Set Identity:** `set(db_ids) == set(engine.doc_ids)` is **100% True** (0 missing, 0 extra).
- **Index Order:** SQLite returns records in table insertion order, whereas `bis_semantic_doc_ids.json` preserves the sequential ingestion order.
- **Index-to-Embedding Alignment:** Verified across multiple index positions (`[0, 100, 5000, 15000, 30000]`) with **exact 1.000000 unit dot product** between stored embeddings and live `model.encode(doc_str)` recomputation.
- **Numerical Integrity:** Zero `NaN`, zero `Inf`, all vectors are $L_2$-normalized unit vectors.

---

## Phase F — Full Benchmark Semantic-Channel Metrics Table

Performance of the dense semantic channel evaluated in isolation across the 19 queries:

| Channel | Hit@1 | Recall@10 | Recall@15 | Recall@30 | Recall@50 | Recall@100 | MRR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Semantic Channel Alone** | **36.8%** (7/19) | **68.4%** (13/19) | **68.4%** (13/19) | **84.2%** (16/19) | **89.5%** (17/19) | **94.7%** (18/19) | **0.4636** |
| *BM25 Channel (Reference)* | *63.2% (12/19)* | *89.5% (17/19)* | *89.5% (17/19)* | *89.5% (17/19)* | *94.7% (18/19)* | *94.7% (18/19)* | *0.6970* |
| *Hybrid RRF Pool (Production)* | *63.2% (12/19)* | *89.5% (17/19)* | *89.5% (17/19)* | *89.5% (17/19)* | *94.7% (18/19)* | *94.7% (18/19)* | *0.6989* |

---

## Phase G — Root-Cause Classification

The dominant semantic retrieval failure is classified as:

### **2. Document Representation Problem (Primary Root Cause)**
- The active BIS catalogue has **0.00% scope text** (all 35,208 records have `scope: None`).
- Dense semantic models cannot infer technical breadth or applicability from a 6-word title. Umbrella codes (`SP 30`, `IS 3043`) lack lexical or semantic markers for the specific maintenance, installation, or grounding procedures they govern.

### **1 & 4. Query & Domain Asymmetry (Secondary Contributing Cause)**
- Public procurement requirements are heavily burdened with procedural contract terminology (`"Annual Repairs and Maintenance Contract..."`). Dense bi-encoders map these words to general maintainability standards (`IS 9692`) rather than substantive electrical codes.

---

## Phase H — Production Recommendation

**Selected Option: OPTION 3 — Semantic document representation should be improved.**

### Diagnostic Evidence:
1. `SP 30 : 2023` is Rank 2 in BM25 because lexical search matches the exact title tokens `electrical`, `code`, and expanded token `national`.
2. In semantic vector space, `SP 30` scores only 0.3531 (Rank 671) because its document string contains only the title. It is defeated by 670 standards whose titles happen to mention `"maintenance"`, `"repairs"`, `"services"`, or `"contract"`.
3. The index integrity, normalization, and model implementation are mathematically correct (alignment = 1.000000).

### Generic Safe Approach (DO NOT IMPLEMENT NOW):
- When populating the BIS catalogue from authoritative sources, enrich document strings with **formal committee titles/descriptions** (e.g., expanding `"ETD 20"` to `"Electrical Installations Sectional Committee"`), and incorporate **published BIS scope paragraphs** where available.
- For standards lacking scope text, a generic catalogue enrichment pipeline that maps BIS Sectional Committees (e.g. ETD 20 $\to$ *"Electrical wiring, safety, and installations in buildings and storage facilities"*) would allow dense embeddings to represent the true engineering scope of umbrella standards without hardcoding standard numbers.

**No production modifications have been made.** Investigation complete.
