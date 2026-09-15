# Phase 4R9 — Retrieval Failure Investigation Report

**Investigation Target:** Root-cause analysis of retrieval failures and low candidate ranking for expected standards, focusing on `T009-R001` (Expected: `SP 30 : 2023`, `IS 732 : 2019`) and full 19-query benchmark behavior.  
**Constraint Status:** Fix 2A frozen. Fix 2B closed with no production changes. Fix 2C not implemented. Zero production code modified.

---

## Executive Summary of Findings

1. **For `T009-R001`, `IS 732 : 2019` is already inside the candidate pool (Rank 10 raw fused, Rank 6 in K=15 pool).** The failure of `T009-R001` in production is that `IS 12457 : 1988` beats both `IS 732` and `SP 30` in arbitration and fusion.
2. **`SP 30 : 2023` ranks high in BM25 (Rank 2) but drops to Rank 23 raw fused.** The root cause is **Multi-Channel Fusion Asymmetry**: `SP 30` is completely absent from the top 150 of Semantic Retrieval, receiving score from only 1 of 3 channels in Reciprocal Rank Fusion (RRF). Distractor candidates (`IS 4051`, `IS 12457`, `IS/IEC 60079-17`) appear in multiple channels (BM25 + Semantic or BM25 + Deterministic) and accumulate nearly double the RRF score.
3. **Lexical IDF Distortion:** Administrative tender terms (`repairs` IDF 9.55, `annual` IDF 10.06, `contract` IDF 8.76) dramatically outweigh core engineering terms (`electrical` IDF 3.45, `code` IDF 3.03), pulling niche standards mentioning "repairs" to the top.
4. **Candidate Pool Truncation is NOT the primary bottleneck for benchmark accuracy:**
   - Expanding K from 15 to 50/100 increases retrieval recall by only 1 query (`T014-R002` enters at Rank 39).
   - However, candidate survival through arbitration **drops** from 78.9% (15/19 at K=15) to 68.4% (13/19 at K=50/100) because larger pools introduce distractor candidates that trigger human review or arbitration misclassifications.

---

## Phase A — Query Representation for T009-R001

### 1. Representation Breakdown
- **Original Requirement Text:**  
  `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"`
- **Extracted Components:**
  - `[installation]` text: `"Repairs"` (attributes: `{'action': 'repairs'}`)
  - `[installation]` text: `"Maintenance"` (attributes: `{'action': 'maintenance'}`)
  - `[application]` text: `"FSD"` (attributes: `{'facility_type': 'fsd'}`)
- **Constructed Retrieval Query (via `TechnicalTerminologyNormalizer`):**  
  `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD (installations national code)"`
- **Technical Tokens Extracted:**  
  `['alongwith', 'annual', 'contract', 'electrical', 'fsd', 'mechanical', 'repairs', 'requisite']`
- **Domain Tokens / Detected Domains:**  
  `[]` *(Empty: no explicit match in `gate.detect_domains`)*
- **Deterministic Citations:**  
  *None cited in text.*
- **BM25 Query Terms:**  
  `['annual', 'repairs', 'maintenance', 'contract', 'electrical', 'mechanical', 'services', 'alongwith', 'requisite', 'materials', 'fsd', 'installations', 'national', 'code']`
- **Semantic Query Input:**  
  `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD (installations national code)"`

### 2. BM25 Term Frequency and IDF Analysis
Catalogue Document Count $N = 7097$. Term Document Frequencies (DF) and Inverse Document Frequencies (IDF):

| Term | Document Frequency (DF) | IDF Weight | Contribution Significance |
| :--- | :---: | :---: | :--- |
| `alongwith` | 0 | 11.1621 | Out-of-vocabulary stopword / administrative artifact |
| `requisite` | 0 | 11.1621 | Out-of-vocabulary stopword / administrative artifact |
| `fsd` | 0 | 11.1621 | Site abbreviation, unindexed |
| **`annual`** | 1 | **10.0635** | Extremely high IDF; administrative contract noise |
| **`repairs`** | 2 | **9.5527** | Extremely high IDF; heavily amplifies standards mentioning "repairs" |
| **`contract`** | 5 | **8.7642** | Extremely high IDF; procurement noise |
| `national` | 47 | 6.6082 | Moderate; from terminology normalizer expansion |
| `installations`| 142 | 5.5096 | Moderate; from terminology normalizer expansion |
| `services` | 263 | 4.8949 | Generic service term |
| `maintenance` | 278 | 4.8395 | Generic service term |
| `mechanical` | 425 | 4.4157 | Engineering domain |
| `materials` | 1027 | 3.5341 | Generic noun |
| **`electrical`**| 1121 | **3.4465** | **Low IDF due to high catalogue frequency** |
| **`code`** | 1709 | **3.0250** | **Low IDF due to high catalogue frequency** |

**Observation:** The terms `repairs`, `annual`, and `contract` have 2.5x to 3x higher IDF weights than `electrical` and `code`. Consequently, BM25 heavily favors standards that mention "repairs" or "contract" over overarching codes like the National Electrical Code.

---

## Phase B — Component Ablation on T009-R001

Ablation across 7 controlled query variants without modifying production code:

| Variant | SP 30 Rank | IS 732 Rank | IS 12457 Rank | IS 4051 Rank | Recall@15 | Recall@30 | Recall@50 | Recall@100 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Original requirement text** | 20 | 10 | 3 | 2 | 1 | 1 | 1 | 1 |
| **2. Components only** (`"Repairs Maintenance FSD"`) | >100 | >100 | 1 | 39 | 0 | 0 | 0 | 0 |
| **3. Technical terms only** (`"repairs maintenance electrical mechanical"`) | >100 | >100 | 2 | 53 | 0 | 0 | 0 | 0 |
| **4. Domain terms only** (`"electrical mechanical installations national electrical code"`) | **1** | **6** | >100 | 14 | 1 | 1 | 1 | 1 |
| **5. Original text + components** | 79 | 53 | 2 | 4 | 0 | 0 | 0 | 1 |
| **6. Text with generic service terms removed** | >100 | >100 | >100 | >100 | 0 | 0 | 0 | 0 |
| **7. Production expanded query** | **4** | **11** | 7 | 3 | 1 | 1 | 1 | 1 |

### Key Ablation Insights:
1. **Domain Terms Only (Variant 4)** places `SP 30` at **Rank 1** and `IS 732` at **Rank 6**, while eliminating distractor `IS 12457` entirely from the top 100.
2. **Components Only (Variant 2)** isolates `"Repairs"` and `"Maintenance"`, which immediately catapults `IS 12457` to **Rank 1**, proving that component extraction currently extracts administrative actions rather than the technical subject.
3. **Production Expanded Query (Variant 7)** succeeds in retrieving both `SP 30` (Rank 4) and `IS 732` (Rank 11) inside Recall@15 because of the normalizer's `(installations national code)` expansion.

---

## Phase C — Fusion Source Analysis

Measured individual engine rankings versus fused RRF rankings for key candidates on `T009-R001`:

| Candidate Standard | BM25 Rank | Semantic Rank | Deterministic Rank | Fused Rank | RRF Score | Status / Note |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **SP 30 : 2023** (Expected) | **2** | **>150** | **None** | **23** | **0.3280** | Fails due to semantic absence |
| SP 30 : 2011 | 1 | >150 | None | 20 | 0.3333 | Single-channel BM25 |
| **IS 732 : 2019** (Expected) | **4** | **71** | **None** | **10** | **0.4729** | In K=15 pool |
| **IS 12457 : 1988** (Distractor) | 8 | >150 | 11 | **3** | **0.5854** | Multi-channel (BM25 + Det) |
| **IS 4051 : 2025** (Distractor) | 13 | 9 | None | **4** | **0.5732** | Multi-channel (BM25 + Sem) |
| **IS 4051 : 1967** (Distractor) | 7 | 6 | None | **2** | **0.6116** | Strong dual-channel alignment |
| **IS/IEC 60079-17** | 5 | 25 | None | **7** | **0.4946** | Dual-channel alignment |
| **IS/IEC 60034-23** | >150 | 15 | None | **47** | **0.2711** | Single-channel Semantic |

### Failure Source Identification:
- **BM25:** **NOT the bottleneck.** BM25 retrieves `SP 30 : 2011` at Rank 1, `SP 30 : 2023` at Rank 2, and `IS 732` at Rank 4.
- **Deterministic:** Non-factor for un-cited queries. However, `IS 12457` matches deterministic component search at Rank 11.
- **Semantic Retrieval:** **PRIMARY BOTTLENECK.** Semantic retrieval completely fails on `SP 30` (not in top 150). The bi-encoder dense representation maps procurement phrasing to equipment maintenance (`IS 4051`, `IS/IEC 60034-23`), ignoring high-level code standards.
- **RRF Fusion:** **MULTIPLYING BOTTLENECK.** Because RRF uses sum of reciprocal ranks ($1/(60+r)$), any candidate present in two channels (e.g. BM25 Rank 8 + Det Rank 11) gets $\approx 0.029$, easily beating a candidate with BM25 Rank 2 but no second channel ($1/62 \approx 0.016$).

---

## Phase D — Top-K Ablation Across 19-Query Benchmark

Evaluated current retrieval implementation with explicit parameter propagation across K = 10, 15, 30, 50, 100:

| K | Hit@1 | Recall@K | MRR | Candidate Survival | Latency P50 | Latency P95 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **K = 10** | 63.2% (12/19) | 89.5% (17/19) | 0.697 | 14 / 19 (73.7%) | 337.3 ms | 829.5 ms |
| **K = 15** | 63.2% (12/19) | 89.5% (17/19) | 0.697 | **15 / 19 (78.9%)** | 316.9 ms | 1119.5 ms |
| **K = 30** | 63.2% (12/19) | 89.5% (17/19) | 0.697 | 14 / 19 (73.7%) | 355.1 ms | 1173.9 ms |
| **K = 50** | 63.2% (12/19) | **94.7% (18/19)** | 0.698 | 13 / 19 (68.4%) | 260.6 ms | 651.6 ms |
| **K = 100** | 63.2% (12/19) | **94.7% (18/19)** | 0.698 | 13 / 19 (68.4%) | 395.2 ms | 1034.2 ms |

### Key Findings:
1. **Recall Ceiling:** Recall is flat at 89.5% from K=10 to K=30, and rises to 94.7% at K=50 solely due to `T014-R002` (which sits at Rank 39).
2. **Survival Degradation at Higher K:** While Recall increases at K=50 and K=100, **Candidate Survival drops from 15/19 (78.9%) to 13/19 (68.4%)**. Larger candidate pools admit weak distractors that dilutes confidence and triggers human review or mis-arbitration.
3. **K=15 is the Optimal Balance Point** in the current architecture for candidate survival.

---

## Phase E — Full 19-Query Retrieval Rank Table

| Requirement ID | Expected Standard(s) | Raw Rank | K=15 | K=30 | K=50 | K=100 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **T001-R002** | IS 15905 : 2011, IS 1239 (Part 1) : 2004 | 1 | YES | YES | YES | YES |
| **T001-R003** | IS 15622 : 2017 | 7 | YES | YES | YES | YES |
| **T001-R004** | IS 2556 (Part 1 to 17), IS 781, IS 774 | 1 | YES | YES | YES | YES |
| **T002-R003** | IS 6392 : 1971, IS 2712 : 2020 | 2 | YES | YES | YES | YES |
| **T003-R001** | IS/IEC 61439-3 : 2012, IS 10322 | 1 | YES | YES | YES | YES |
| **T004-R002** | IS 7098 (Part 1) : 1988, IS 1255 : 1983 | 1 | YES | YES | YES | YES |
| **T004-R005** | IS 5039 : 1983, IS/IEC 61439-5 : 2014 | 1 | YES | YES | YES | YES |
| **T005-R001** | IS 3043 : 2018, IS 7098 (Part 1), IS 1293 | 1 | YES | YES | YES | YES |
| **T006-R001** | IS 16088 : 2016 | **None** | **NO** | **NO** | **NO** | **NO** |
| **T007-R003** | IS 2491 : 2013, IS 15000 : 2013 | 1 | YES | YES | YES | YES |
| **T009-R001** | SP 30 : 2023, IS 732 : 2019 | **10** (IS 732) / **23** (SP 30) | **YES** | **YES** | **YES** | **YES** |
| **T010-R001** | IS 458 : 2021, IS 783 : 1985, IS 14333 | 1 | YES | YES | YES | YES |
| **T011-R001** | IS 7098 (Part 1) : 1988, IS 1255 : 1983 | 4 | YES | YES | YES | YES |
| **T012-R002** | IS 1661 : 1972, IS 269 : 2015 | 1 | YES | YES | YES | YES |
| **T012-R003** | IS 1239 (Part 2) : 1992, IS 778 : 1984 | 1 | YES | YES | YES | YES |
| **T013-R002** | IS/IEC 61800-2 : 2015, IS/IEC 61439-2 | 4 | YES | YES | YES | YES |
| **T013-R003** | IS 14164 : 2008, IS 8183 : 1993 | 1 | YES | YES | YES | YES |
| **T014-R002** | IS/IEC 60034-1 : 2017, IS 5120 : 1977 | **39** | **NO** | **NO** | **YES** | **YES** |
| **T020-R001** | IS 15778 : 2007, IS 1239 (Part 1) : 2004 | 1 | YES | YES | YES | YES |

### Query Categorization:
1. **Expected standard outside K=15:**
   - `T006-R001`: `IS 16088 : 2016` (Rank = None, vocabulary mismatch)
   - `T014-R002`: `IS/IEC 60034-1 : 2017` (Rank 39)
   - *(Note for `T009-R001`: `IS 732` is inside at Rank 10, but `SP 30` is outside at Rank 23)*
2. **Expected standard enters at K=30:**
   - None.
3. **Expected standard enters at K=50:**
   - `T014-R002` (enters at Rank 39).
4. **Expected standard remains outside K=100:**
   - `T006-R001` (remains unretrieved in top 150).

---

## Phase F — Conclusion & Dominant Bottlenecks

Based on measured ranks across all 19 queries and deep ablation of `T009-R001`, the retrieval bottleneck is driven by **three interacting mechanisms**:

1. **Multi-Channel Fusion Asymmetry (Primary Bottleneck for SP 30):**
   `SP 30` achieves **Rank 2 in BM25**, but receives zero contribution from dense semantic retrieval. Under RRF, a candidate with a top BM25 rank but no semantic hit is heavily outscored by distractor candidates appearing moderately in both channels (e.g. `IS 4051` at BM25 Rank 7 and Semantic Rank 6).
2. **Semantic Representation Mismatch on High-Level Codes:**
   Dense semantic retrieval aligns strongly with narrow equipment actions (e.g., motor overhaul, pump repair) rather than overarching national codes or wiring practices when given administrative maintenance text.
3. **Lexical IDF Inversion:**
   Administrative procurement tokens (`repairs`, `contract`, `annual`) have DF < 5 and IDF > 8.7, dominating the BM25 scoring over domain terms (`electrical`, `code`, DF > 1000, IDF < 3.5).
4. **Candidate-Pool Truncation Trade-off:**
   While expanding K from 15 to 50 admits `T014-R002` (Rank 39), it harms overall candidate survival (dropping 78.9% $\to$ 68.4%) due to downstream arbitration susceptibility to distractor candidates.
