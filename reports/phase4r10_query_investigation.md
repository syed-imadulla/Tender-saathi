# Phase 4R10 — Technical Query Construction Investigation Report

**Investigation Target:** Determine whether better generic technical-intent query construction can improve retrieval recall without benchmark-specific rules or IS-number injection.  
**Production Code Status:** Zero production code modified. RRF, K, arbitration, applicability, terminology map, reranker, lifecycle, and explicit citation resolution remain strictly frozen.

---

## Executive Summary of Findings

1. **Current Pipeline Anchor is Fragile to Token Removal:**  
   The current terminology normalizer matches multi-token phrases (e.g. `"electrical and mechanical services"`, `"cable connection"`, `"providing and laying"`). Removing administrative contract terms (Variant D) or isolating components (Variant B/F) destroys these phrases before the normalizer can match them, causing Recall@15 across the benchmark to collapse from **89.5% down to 31.6%**.
2. **Dense Semantic Retrieval Requires Sentence Context:**  
   Dense embedding models (`all-MiniLM-L6-v2`) perform poorly on keyword-only queries (`"electrical mechanical fsd"`). Stripping procurement syntax degrades semantic similarity, eliminating semantic hits entirely.
3. **Structured Term Weighting (Variant G) Solves T009-R001 but Degrades Benchmark Precision:**  
   Weighting technical domain tokens at 2x in BM25 while keeping natural query phrasing for dense semantics:
   - For `T009-R001`: `SP 30 : 2023` enters the pool at **Rank 9** (up from 16/23), `IS 732 : 2019` improves to **Rank 5** (up from 9/10), and chief distractor `IS 12457` collapses from **Rank 3 to Rank 31** (evicted from K=15).
   - Zero cases drop out of K=15 across the entire 19-query benchmark.
   - **However:** Hit@1 drops from **63.2% (12/19) to 52.6% (10/19)** and MRR drops from **0.699 to 0.626** due to rank perturbations among tied top-1 candidates (`T001-R002`, `T002-R003`, `T020-R001`).
4. **Decision Classification:** **Option 4: Query construction is not the dominant bottleneck** (with elements of Option 2: Useful but insufficient evidence). The fundamental bottleneck is multi-channel fusion asymmetry (dense semantics failing on national code handbooks, penalizing single-channel winners under RRF).

---

## Phase A — Current Query Pipeline for T009-R001

1. **Original Requirement Text:**  
   `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"`
2. **Extracted Components (`CompoundRequirementDecomposer`):**
   - `[installation]` text: `"Repairs"` (attributes: `{'action': 'repairs'}`)
   - `[installation]` text: `"Maintenance"` (attributes: `{'action': 'maintenance'}`)
   - `[application]` text: `"FSD"` (attributes: `{'facility_type': 'fsd'}`)
3. **Technical Tokens (`ApplicabilityGate.extract_technical_tokens`):**  
   `['alongwith', 'annual', 'contract', 'electrical', 'fsd', 'mechanical', 'repairs', 'requisite']`
4. **Detected Domains (`ApplicabilityGate.detect_domains`):**  
   `[]` *(Empty: `DOMAINS["ELECTRICAL_AND_POWER"]` matches specific equipment terms like 'cable', 'transformer', 'vfd', but lacks standalone 'electrical' or 'mechanical')*
5. **Terminology Expansion (`TechnicalTerminologyNormalizer`):**  
   - Matches phrase: `"electrical and mechanical services"`
   - Dictionary expansions: `["electrical installations", "national electrical code", "electrical wiring"]`
   - Filtered unique words added (max 2 expansions): `"installations"`, `"national"`, `"code"`
   - Resulting clause: `"(installations national code)"`
6. **Final BM25 Query:**  
   `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD (installations national code)"`
7. **Final Semantic Query:**  
   `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD (installations national code)"`

---

## Phase B & C — Query Variants and Retrieval Measurement on T009-R001

### 1. Controlled Generic Variants Tested
- **Variant A (Current Production):** Production expanded query via normalizer.
- **Variant B (Technical-Domain):** Non-administrative technical tokens + domain keywords (`"electrical mechanical fsd"`).
- **Variant C (Domain + Technical-Context):** Non-admin tokens + component texts & attributes (`"electrical mechanical fsd Repairs Maintenance"`).
- **Variant D (Admin Terms Removed):** Original query with administrative contract stopwords (`annual, contract, repairs, maintenance, services, requisite, materials, alongwith`) removed.
- **Variant E (Original + Domain Expansion):** Original query augmented with detected domain terms.
- **Variant F (Components + Expansion):** Component texts + terminology expansions.
- **Variant G (Structured Weighted Query):** BM25 receives technical tokens repeated at 2x weight while administrative tokens stay at 1x; Semantic receives natural expanded query.

### 2. Retrieval Measurement on T009-R001

| Variant | Description | SP 30 Rank | IS 732 Rank | IS 12457 Rank | IS 4051 Rank | Recall@15 | Recall@30 | Recall@50 | Recall@100 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** | Current production expanded query | 16 | 9 | 3 | 2 | 1 | 1 | 1 | 1 |
| **B** | Technical-domain query | >100 | >100 | 31 | >100 | 0 | 0 | 0 | 0 |
| **C** | Domain + technical-context query | >100 | >100 | 30 | >100 | 0 | 0 | 0 | 0 |
| **D** | Admin contract terms removed | >100 | >100 | 31 | >100 | 0 | 0 | 0 | 0 |
| **E** | Original + domain expansion | 16 | 9 | 3 | 2 | 1 | 1 | 1 | 1 |
| **F** | Components + domain expansion | >100 | >100 | 17 | >100 | 0 | 0 | 0 | 0 |
| **G** | Structured weighted query (2x tech) | **9** | **5** | **31** | **2** | **1** | **1** | **1** | **1** |

### 3. Individual Channel Ranks on T009-R001

```
--- Variant A: Current production expanded query ---
  SP 30 : 2023    | BM25:     2 | Sem:  None | Det:  None | Fused:   16 (raw RRF: 19)
  IS 732 : 2019   | BM25:     4 | Sem:    71 | Det:  None | Fused:    9 (raw RRF:  9)
  IS 12457 : 1988 | BM25:     8 | Sem:  None | Det:    11 | Fused:    3 (raw RRF:  3)
  IS 4051         | BM25:     7 | Sem:     6 | Det:  None | Fused:    2 (raw RRF:  2)

--- Variant B: Technical-domain query ("electrical fsd mechanical") ---
  SP 30 : 2023    | BM25:  None | Sem:  None | Det:  None | Fused: None
  IS 732 : 2019   | BM25:  None | Sem:  None | Det:  None | Fused: None
  IS 12457 : 1988 | BM25:  None | Sem:  None | Det:    11 | Fused:   31
  IS 4051         | BM25:  None | Sem:  None | Det:  None | Fused: None

--- Variant D: Admin terms removed ("electrical and mechanical services at FSD") ---
  SP 30 : 2023    | BM25:  None | Sem:  None | Det:  None | Fused: None
  IS 732 : 2019   | BM25:  None | Sem:  None | Det:  None | Fused: None
  IS 12457 : 1988 | BM25:  None | Sem:  None | Det:    11 | Fused:   31
  IS 4051         | BM25:  None | Sem:  None | Det:  None | Fused: None

--- Variant G: Structured weighted query (2x technical token weight in BM25) ---
  SP 30 : 2023    | BM25:     2 | Sem:  None | Det:  None | Fused:    9 (raw RRF: 11)
  IS 732 : 2019   | BM25:     4 | Sem:    71 | Det:  None | Fused:    5 (raw RRF:  5)
  IS 12457 : 1988 | BM25:  None | Sem:  None | Det:    11 | Fused:   31 (raw RRF: 31)
  IS 4051         | BM25:    27 | Sem:     6 | Det:  None | Fused:    2 (raw RRF:  2)
```

**Key Insight:** Under Variant G, downweighting administrative terms while doubling technical domain tokens completely evicts `IS 12457` from BM25 (moving it from Rank 8 to unretrieved, and fused Rank 3 $\to$ 31), allowing `SP 30` to enter the K=15 candidate pool at **Rank 9** and `IS 732` to rise to **Rank 5**.

---

## Phase D — Full 19-Query Benchmark Test

| Variant | Hit@1 | Recall@10 | Recall@15 | Recall@30 | Recall@50 | Recall@100 | MRR | Candidate Survival | Final Rec Accuracy | Latency P50/P95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A (Base)** | **63.2%** (12) | **89.5%** (17) | **89.5%** (17) | **89.5%** (17) | **94.7%** (18) | **94.7%** (18) | **0.699** | **15/19** (78.9%) | **7/19** (36.8%) | 374.5ms / 1364.9ms |
| **B** | 21.1% (4) | 31.6% (6) | 31.6% (6) | 52.6% (10) | 52.6% (10) | 78.9% (15) | 0.246 | 15/19 (78.9%) | 8/19 (42.1%) | 342.0ms / 518.3ms |
| **C** | 42.1% (8) | 63.2% (12) | 63.2% (12) | 73.7% (14) | 84.2% (16) | 84.2% (16) | 0.459 | 15/19 (78.9%) | 8/19 (42.1%) | 342.3ms / 1710.5ms |
| **D** | 10.5% (2) | 31.6% (6) | 31.6% (6) | 42.1% (8) | 47.4% (9) | 68.4% (13) | 0.169 | 15/19 (78.9%) | 8/19 (42.1%) | 278.0ms / 1366.2ms |
| **E** | 52.6% (10) | 73.7% (14) | 73.7% (14) | 84.2% (16) | 89.5% (17) | 94.7% (18) | 0.607 | 15/19 (78.9%) | 8/19 (42.1%) | 302.4ms / 1440.3ms |
| **F** | 47.4% (9) | 68.4% (13) | 68.4% (13) | 73.7% (14) | 84.2% (16) | 89.5% (17) | 0.544 | 15/19 (78.9%) | 8/19 (42.1%) | 349.2ms / 489.4ms |
| **G** | 52.6% (10) | **89.5%** (17) | **89.5%** (17) | **89.5%** (17) | **94.7%** (18) | **94.7%** (18) | 0.626 | **15/19** (78.9%) | **8/19** (42.1%) | 332.4ms / 1590.2ms |

---

## Phase E — Regression Analysis on 19 Queries

### 1. Per-Query First-Hit Rank Comparison Table

| Requirement ID | Base (Var A) | Var B | Var C | Var D | Var E | Var F | Var G |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **T001-R002** | **1** | 8 | 8 | 8 | 1 | 32 (Reg) | 3 |
| **T001-R003** | **7** | 30 (Reg) | 9 | 68 (Reg) | 16 (Reg) | 7 | 8 |
| **T001-R004** | **1** | 72 (Reg) | 4 | 3 | 2 | 1 | 1 |
| **T002-R003** | **2** | 59 (Reg) | 27 (Reg) | 59 (Reg) | 2 | 59 (Reg) | 4 |
| **T003-R001** | **1** | 3 | 1 | 3 | 1 | 1 | 1 |
| **T004-R002** | **1** | 1 | 1 | 1 | 1 | 1 | 1 |
| **T004-R005** | **1** | 27 (Reg) | 1 | 75 (Reg) | 1 | 1 | 1 |
| **T005-R001** | **1** | 57 (Reg) | 32 (Reg) | None (Reg)| 1 | None (Reg) | 1 |
| **T006-R001** | **None** | None | None | None | None | 25 | None |
| **T007-R003** | **1** | 1 | 1 | None (Reg)| 1 | 3 | 1 |
| **T009-R001** | **9** | None (Reg) | None (Reg) | None (Reg)| 9 | None (Reg) | **5 (Imp)** |
| **T010-R001** | **1** | 1 | 1 | 1 | 1 | 1 | 1 |
| **T011-R001** | **4** | 68 (Reg) | 22 (Reg) | 72 (Reg) | 4 | 2 | 5 |
| **T012-R002** | **1** | 28 (Reg) | 1 | 28 (Reg) | 1 | 1 | 1 |
| **T012-R003** | **1** | None (Reg) | None (Reg) | 40 (Reg) | 16 (Reg) | 1 | 1 |
| **T013-R002** | **4** | None (Reg) | 10 | None (Reg)| 38 (Reg) | 4 | 4 |
| **T013-R003** | **1** | 30 (Reg) | 1 | 24 (Reg) | 1 | 1 | 1 |
| **T014-R002** | **39** | 92 | 42 | None | 72 | 39 | 37 |
| **T020-R001** | **1** | 1 | 1 | 4 | 1 | 1 | 2 |

### 2. Cases Dropping Out of K=15 Relative to Base Production (Variant A)
- **Variant B:** 11 severe regressions (`T001-R003`, `T001-R004`, `T002-R003`, `T004-R005`, `T005-R001`, `T009-R001`, `T011-R001`, `T012-R002`, `T012-R003`, `T013-R002`, `T013-R003`).
- **Variant C:** 5 regressions (`T002-R003`, `T005-R001`, `T009-R001`, `T011-R001`, `T012-R003`).
- **Variant D:** 11 severe regressions (`T001-R003`, `T002-R003`, `T004-R005`, `T005-R001`, `T007-R003`, `T009-R001`, `T011-R001`, `T012-R002`, `T012-R003`, `T013-R002`, `T013-R003`).
- **Variant E:** 3 regressions (`T001-R003`, `T012-R003`, `T013-R002`).
- **Variant F:** 4 regressions (`T001-R002`, `T002-R003`, `T005-R001`, `T009-R001`).
- **Variant G:** **ZERO regressions out of K=15.** All 17 candidates in K=15 under base remain in K=15.

---

## Phase F — Determine the Best Query Representation

Comparing all representations against benchmark criteria:
1. **Variants B, C, D, E, F are firmly disqualified:** Stripping administrative words or relying purely on isolated components destroys semantic sentence embeddings and breaks multi-token terminology triggers (dropping Recall@15 to 31.6%–73.7%).
2. **Variant G demonstrates targeted effectiveness on T009-R001:**
   - Moves `SP 30 : 2023` from Rank 16/23 into K=15 at **Rank 9**.
   - Moves `IS 732 : 2019` from Rank 9/10 to **Rank 5**.
   - Successfully evicts distractor `IS 12457 : 1988` from Rank 3 to **Rank 31**.
   - Maintains 100% K=15 candidate survival (0 regressions out of K=15).
   - Improves Final Recommendation Accuracy to 8/19 (42.1%).
3. **However, Variant G introduces precision regressions on other queries:**
   - Hit@1 drops from **63.2% (12/19) to 52.6% (10/19)**.
   - MRR drops from **0.699 to 0.626**.
   - Queries like `T001-R002` (Rank 1 $\to$ 3), `T002-R003` (Rank 2 $\to$ 4), and `T020-R001` (Rank 1 $\to$ 2) suffer from term-weighting skewing BM25 tie-breaking.
4. **Current Production (Variant A) remains the superior overall representation:**
   - Highest overall Hit@1 (63.2%).
   - Highest overall MRR (0.699).
   - Stable Recall@15 (89.5%).

---

## Phase G — Decision Classification

**Classification: Option 4 — Query construction is not the dominant bottleneck.**

### Rationale:
1. The low fused ranking of `SP 30` in `T009-R001` is not caused by missing query terms in BM25 (BM25 already retrieves `SP 30` at **Rank 2**).
2. It is caused by **dense semantic retrieval failing to retrieve national codes / handbook standards** from high-level procurement text, resulting in a **single-channel RRF penalty** where multi-channel candidates (`IS 4051`, `IS 12457`) outscore it.
3. While artificial term repetition (Variant G) can force BM25 to override the semantic deficit on `T009-R001`, it alters term balance across the broader benchmark, reducing Hit@1 from 63.2% to 52.6% and MRR from 0.699 to 0.626.
4. Therefore, query construction alone cannot solve retrieval failures without regressing broader ranking quality.

**No production modifications have been made or are recommended.** Investigation complete.
