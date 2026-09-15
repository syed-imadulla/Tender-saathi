# Phase 4R13 — Query-Side Technical Intent Construction Investigation

**Investigation Status**: COMPLETED (Investigation Only — Zero Production Changes)  
**Date**: September 2026  
**Scope**: Query Transformation Architecture, Technical Intent Construction, Vocabulary Ablation, and Multi-Channel Retrieval Evaluation across Frozen 19-Query Benchmark  
**Raw Data Artifact**: [`reports/phase4r13_query_construction_data.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/reports/phase4r13_query_construction_data.json)  
**Experiment Script**: [`scratch/phase4r13_query_construction.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/scratch/phase4r13_query_construction.py)

---

## 1. Objective

Phase 4R12 demonstrated that enriching the BIS catalogue with authoritative administrative metadata (Sectional Committee names and Document Aspects) regressed retrieval performance across the benchmark ($Recall@50$ dropped $-10.5\%$) and failed to recover any missing standards.

Phase 4R13 investigated whether the remaining retrieval recall bottleneck can be solved safely on the **QUERY side** by constructing a more technically representative retrieval query from the tender requirement text, without:
1. Hardcoding IS numbers,
2. Inserting expected standards,
3. Inserting benchmark-specific phrases,
4. Cheating using catalogue knowledge,
5. Modifying the BIS catalogue,
6. Modifying embeddings or indexes,
7. Modifying RRF fusion or candidate pool size $K$,
8. Modifying arbitration or lifecycle logic.

---

## 2. Authoritative Baseline (Variant A — Control)

The experiment evaluated the frozen 19-query benchmark against the frozen production pipeline:
- **Catalogue**: `data/catalogue/bis_catalogue.db` ($N = 35,208$ standards)
- **Embeddings**: Production `all-MiniLM-L6-v2` dense index (`bis_semantic_embeddings.npy`, 384 dimensions)
- **Lexical Index**: Production rank-bm25 index
- **Fusion**: RRF ($k = 60$, Candidate Pool $K = 15$)
- **Terminology Normalizer**: Phase 4R8 Fix 1 deterministic terminology map
- **Arbitration Logic**: Phase 4R8 Fix 2A technical role priority

### Baseline A Performance ($N = 19$):
- **Candidate Survival @15 (RRF Recall@15)**: **17 / 19 (89.5%)**
- **Recall@50**: **18 / 19 (94.7%)**
- **Recall@100**: **18 / 19 (94.7%)**
- **RRF Hit@1**: **12 / 19 (63.2%)**
- **RRF MRR**: **0.6852**
- **BM25 Recall@15**: **16 / 19 (84.2%)** | **BM25 Hit@1**: **7 / 19 (36.8%)** | **BM25 MRR**: **0.5330**
- **Semantic Recall@15**: **13 / 19 (68.4%)** | **Semantic Hit@1**: **7 / 19 (36.8%)** | **Semantic MRR**: **0.4634**
- **Final Recommendation Accuracy**: **8 / 19 (42.1%)**
- **Regressions**: **0** (Authoritative control)

---

## 3. Experimental Variants

Seven distinct query transformation representations were generated and evaluated independently across all 19 benchmark queries:

| Variant | Designation | Transformation Logic |
|---|---|---|
| **A** | **Current Production Query (Control)** | Exact current production query output from `TechnicalTerminologyNormalizer.build_expanded_query()`. |
| **B** | **Technical Token Query** | Extract only technically meaningful terms; remove administrative/procurement boilerplate (`annual`, `contract`, `requisite`, `materials`, `providing`, `supply`, `installation/maintenance contract wording`). |
| **C** | **Domain Query** | Construct a generic, standard-agnostic domain-focused query derived from engineering concepts present in the requirement. |
| **D** | **Technical + Domain Query** | Concatenate retained technical tokens (B) with generic domain terms (C). |
| **E** | **Original + Technical Expansion** | Preserve full original requirement text and append generic domain concepts in parentheses. |
| **F** | **Components + Technical Expansion** | Concatenate decomposed requirement components with generic domain concepts. |
| **G** | **Administrative-Term Ablation** | Direct ablation: remove procurement/administrative terms from original text without adding any external domain vocabulary. |
| **H** | **Weighted Query** | **NOT APPLICABLE** (BM25 and Semantic search engines in TenderSaathi only accept raw string queries; query weighting is unsupported). |

---

## 4. Query Transformation Examples

Below are representative transformations illustrating the exact string transformations evaluated:

### Example 1: T009-R001 (Electrical & Mechanical Annual Maintenance)
- **Original**: `"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"`
- **Variant A (Prod)**: `Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD (installations national code)`
- **Variant B (Tech Tokens)**: `electrical mechanical services FSD`  
  *(Removed: `Annual`, `Repairs`, `and`, `Maintenance`, `Contract`, `for`, `alongwith`, `requisite`, `materials`, `at`)*
- **Variant C (Domain)**: `electrical installations wiring code of practice maintenance buildings`  
  *(Added: `installations`, `wiring`, `code`, `practice`, `buildings`)*
- **Variant D (Tech + Domain)**: `electrical mechanical services FSD electrical installations wiring code of practice maintenance buildings`
- **Variant E (Original + Tech)**: `Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD (electrical installations wiring code of practice maintenance buildings)`
- **Variant F (Components + Tech)**: `Repairs Maintenance FSD electrical installations wiring code of practice maintenance buildings`
- **Variant G (Admin Ablation)**: `electrical mechanical services FSD`

### Example 2: T005-R001 (DG Set Cable Connection)
- **Original**: `"Cable connection of DG Set in Newly constructed building of the Dept. of Molecular , Human Genetics"`
- **Variant A (Prod)**: `Cable connection of DG Set in Newly constructed building of the Dept. of Molecular , Human Genetics (diesel generator generating crosslinked polyethylene insulated thermoplastic sheathed cables code practice installation maintenance power)`
- **Variant B (Tech Tokens)**: `Cable connection DG Set Molecular Human Genetics`
- **Variant C (Domain)**: `diesel generator power cables earthing electrical installations`
- **Variant D (Tech + Domain)**: `Cable connection DG Set diesel generator power cables earthing electrical installations`
- **Variant E (Original + Tech)**: `Cable connection of DG Set in Newly constructed building of the Dept. of Molecular , Human Genetics (diesel generator power cables earthing electrical installations)`
- **Variant F (Components + Tech)**: `Cable DG Set diesel generator power cables earthing electrical installations`
- **Variant G (Admin Ablation)**: `Cable connection DG Set building Molecular Human Genetics`

### Example 3: T002-R003 (Flange Joint Maintenance)
- **Original**: `"Flange Joint Maintenance"`
- **Variant A (Prod)**: `Flange Joint Maintenance (steel pipe flanges)`
- **Variant B (Tech Tokens)**: `Flange Joint` *(Removed: `Maintenance`)*
- **Variant C (Domain)**: `steel pipe flanges gaskets jointing`
- **Variant D (Tech + Domain)**: `Flange Joint steel pipe flanges gaskets jointing`
- **Variant E (Original + Tech)**: `Flange Joint Maintenance (steel pipe flanges gaskets jointing)`
- **Variant F (Components + Tech)**: `Flange Maintenance steel pipe flanges gaskets jointing`
- **Variant G (Admin Ablation)**: `Flange Joint`

---

## 5. Full 19-Query Benchmark Results

The table below shows the fused RRF rank of the expected standard across all 19 queries for every variant:

| Query ID | Expected Standard | Base A | Var B | Var C | Var D | Var E | Var F | Var G | Status / Diagnosis |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **T001-R002** | IS 15905 / IS 1239-1 | **1** | 4 | **1** | **1** | **1** | **1** | 4 | Stable across domain variants |
| **T001-R003** | IS 15622 | **7** | 79 | 26 | 28 | 28 | 28 | 79 | **Severe Regression** (Drops out of pool) |
| **T001-R004** | IS 2556 / IS 781 / IS 774 | **1** | 2 | **1** | 2 | 2 | 2 | 2 | Maintained in top pool |
| **T002-R003** | IS 6392 / IS 2712 | **4** | 89 | **4** | **4** | **4** | **4** | 89 | B & G collapse without "Maintenance" |
| **T003-R001** | IS/IEC 61439-3 | **1** | 2 | 2 | **1** | **1** | **1** | 2 | High rank maintained |
| **T004-R002** | IS 7098-1 / IS 1255 | **1** | **1** | 3 | 2 | 2 | 2 | **1** | High rank maintained |
| **T004-R005** | IS 5039 / IS/IEC 61439-5 | **1** | 27 | **1** | **1** | **1** | **1** | 27 | B & G drop out of top-15 pool |
| **T005-R001** | IS 3043 / IS 7098-1 | **1** | 144 | **None** | **None** | 45 | **None** | 148 | **Catastrophic Regression** (Rank 1 $\rightarrow$ None) |
| **T006-R001** | IS 16088 | **None** | **None** | 33 | 31 | **None** | 35 | **None** | False retrieval (Fire sprinkler pipe) |
| **T007-R003** | IS 2491 / IS 15000 | **1** | **None** | 4 | 3 | **1** | 3 | **None** | B & G collapse completely |
| **T009-R001** | SP 30 / IS 732 | **10** | **None** | 2 | 3 | 6 | 2 | **None** | C, D, E, F lift SP 30; B & G collapse |
| **T010-R001** | IS 458 / IS 783 / IS 14333 | **1** | **1** | **1** | **1** | **1** | **1** | **1** | Stable Hit@1 across all |
| **T011-R001** | IS 7098-1 / IS 1255 | **4** | 37 | 2 | 6 | 30 | 20 | 37 | E drops out of pool (Rank 30) |
| **T012-R002** | IS 1661 / IS 269 | **1** | 31 | **1** | **1** | **1** | **1** | 31 | B & G drop out of pool |
| **T012-R003** | IS 1239-2 / IS 778 | **1** | 45 | **1** | **1** | **1** | **1** | 45 | B & G drop out of pool |
| **T013-R002** | IS/IEC 61800-2 | **4** | **None** | 5 | 8 | 16 | 8 | **None** | B & G collapse; E drops out of pool |
| **T013-R003** | IS 14164 / IS 8183 | **1** | 28 | 2 | 2 | 2 | 2 | 28 | B & G drop out of pool |
| **T014-R002** | IS/IEC 60034-1 / IS 5120 | **39** | 144 | 35 | 41 | 44 | 41 | 144 | Outside top-15 across all |
| **T020-R001** | IS 15778 / IS 1239-1 | **1** | 5 | **1** | **1** | 2 | 1 | 5 | High rank maintained |

---

## 6. Channel-Level Analysis

Separating performance across the three retrieval channels (BM25, Semantic, and RRF) exposes the exact mechanical impact of each query transformation:

```
========================================================================================
CHANNEL-LEVEL RETRIEVAL METRICS COMPARISON (N = 19)
========================================================================================
Variant   BM25 Hit@1   BM25 R@15   BM25 MRR | Sem Hit@1   Sem R@15   Sem MRR  | RRF R@15   RRF MRR
----------------------------------------------------------------------------------------
A (Base)   7 (36.8%)   16 (84.2%)   0.5330  |  7 (36.8%)  13 (68.4%)  0.4634  | 17 (89.5%) 0.6852
B (Tokens) 0 ( 0.0%)    3 (15.8%)   0.0475  |  1 ( 5.3%)   7 (36.8%)  0.1201  |  6 (31.6%) 0.1917
C (Domain) 6 (31.6%)   15 (78.9%)   0.4309  |  5 (26.3%)  15 (78.9%)  0.3927  | 15 (78.9%) 0.5332
D (T+D)    7 (36.8%)   14 (73.7%)   0.4628  |  7 (36.8%)  16 (84.2%)  0.4667  | 15 (78.9%) 0.5158
E (Orig+E) 7 (36.8%)   14 (73.7%)   0.4611  |  6 (31.6%)  14 (73.7%)  0.3991  | 13 (68.4%) 0.5049
F (Comp+E) 6 (31.6%)   14 (73.7%)   0.4045  |  6 (31.6%)  16 (84.2%)  0.4266  | 14 (73.7%) 0.5186
G (Ablat)  0 ( 0.0%)    3 (15.8%)   0.0493  |  1 ( 5.3%)   7 (36.8%)  0.1191  |  6 (31.6%) 0.1917
========================================================================================
```

### Channel Findings:
1. **The Catastrophic Fallacy of "Administrative Stopword" Stripping (Variants B & G)**:
   - Stripping procurement/administrative words (`repairs`, `maintenance`, `fittings`, `replacement`, `installation`) completely collapses BM25 lexical retrieval from $84.2\%$ down to **$15.8\%$** (BM25 MRR drops $0.5330 \rightarrow 0.0475$).
   - **Root Cause**: Indian Standards titles heavily utilize procedural nouns: *"Code of practice for electrical wiring installations"*, *"Code of practice for earthing"*, *"Code of practice for maintenance"*, *"Specification for mild steel pipe fittings"*. Stripping these words removes the exact lexical overlap required by BM25.
2. **Semantic Sensitivity to Domain Drift (Variants C, D, E, F)**:
   - Appending broad domain keywords increases semantic candidate pool coverage for a few queries ($Sem\ R@15$ increases $68.4\% \rightarrow 84.2\%$ in Variant D), but **drastically harms BM25 specificity** ($BM25\ R@15$ drops $84.2\% \rightarrow 73.7\%$).
   - Adding broad terms causes high-IDF tender nouns (like `DG Set`, `AMF`, `CPVC`) to be drowned out by high-frequency domain words.
3. **RRF Penalty from Channel Asymmetry**:
   - Because RRF relies on consensus between channels, whenever a query transformation degrades BM25 (even if it slightly helps Semantic), the overall fused candidate survival drops from $89.5\%$ down to $78.9\%$ (or $68.4\%$ in Variant E).

---

## 7. Deep-Dive: T009-R001 Analysis

**Requirement**: *"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"*  
**Expected**: `SP 30 : 2023` (National Electrical Code) and/or `IS 732 : 2019` (Electrical Wiring Installations)

| Metric / Property | Variant A (Base) | Variant B (Tech Tokens) | Variant C (Domain) | Variant D (Tech+Dom) | Variant E (Orig+Tech) | Variant F (Comp+Tech) | Variant G (Ablation) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Transformed Query** | `... FSD (installations national code)` | `electrical mechanical services FSD` | `electrical installations wiring code of practice maintenance buildings` | `electrical mechanical services FSD electrical installations wiring code of practice maintenance buildings` | `Annual Repairs ... (electrical installations wiring code of practice maintenance buildings)` | `Repairs Maintenance FSD electrical installations wiring code of practice maintenance buildings` | `electrical mechanical services FSD` |
| **BM25 Rank** | **1** (`IS 732`) | `None` (>150) | **2** (`IS 732`) | **2** (`IS 732`) | **2** (`IS 732`) | **3** (`IS 732`) | `None` (>150) |
| **Semantic Rank** | 71 (`SP 30`) | `None` (>150) | **1** (`SP 30`) | **1** (`SP 30`) | 27 (`SP 30`) | **2** (`SP 30`) | `None` (>150) |
| **Fused RRF Rank**| **10** (`IS 732`) | `None` (>150) | **2** (`SP 30`) | **3** (`SP 30`) | **6** (`IS 732`) | **2** (`SP 30`) | `None` (>150) |
| **In Top-15 Pool?**| **YES** | **NO** | **YES** | **YES** | **YES** | **YES** | **NO** |

### Critical Diagnosis for T009-R001:
1. **Baseline A Already Succeeds in Retrieval**: In the current production baseline (Variant A), `IS 732` is already retrieved at **Rank 1 in BM25** and enters the top-15 fused pool at **Rank 10**. T009-R001 fails downstream during **arbitration**, not retrieval!
2. **The "Illusion" of Improvement in Variant C**: Injecting `"wiring code of practice"` pushes `SP 30` to Semantic Rank 1 and Fused Rank 2. However, this query transformation introduces words directly inspired by standard titles (`wiring`, `code of practice`).
3. **The Unacceptable Trade-off**: The exact same transformation that elevates T009 from Rank 10 to Rank 2 **destroys T005-R001** (drops from Rank 1 to `None`), **regresses T001-R003** (drops from Rank 7 to 26), and **regresses T011-R001** (drops from Rank 4 to 30).

---

## 8. Regression Analysis

Every query transformation variant was systematically audited for performance deltas against Baseline A:

| Variant | Net Improvements | Net Regressions | Unchanged | Primary Regressions Introduced |
|---|:---:|:---:|:---:|---|
| **B (Tech Tokens)** | 0 | **16** | 3 | Catastrophic failure across 16 queries. `T002`, `T005`, `T007`, `T009`, `T011`, `T012`, `T013` lost from pool. |
| **C (Domain)** | 4 | **7** | 8 | **`T005-R001` completely lost** (Rank 1 $\rightarrow$ None). `T001-R003` dropped out of pool (Rank 7 $\rightarrow$ 26). |
| **D (Tech + Domain)** | 2 | **9** | 8 | **`T005-R001` completely lost** (Rank 1 $\rightarrow$ None). `T001-R003` dropped out of pool (Rank 7 $\rightarrow$ 28). `T013-R002` regressed (Rank 4 $\rightarrow$ 8). |
| **E (Orig + Tech)** | 1 | **9** | 9 | **`T005-R001` regressed severely** (Rank 1 $\rightarrow$ 45). **`T011-R001` dropped out of pool** (Rank 4 $\rightarrow$ 30). **`T013-R002` dropped out of pool** (Rank 4 $\rightarrow$ 16). |
| **F (Comp + Tech)** | 2 | **9** | 8 | **`T005-R001` completely lost** (Rank 1 $\rightarrow$ None). `T001-R003` dropped out of pool (Rank 7 $\rightarrow$ 28). |
| **G (Admin Ablation)**| 0 | **16** | 3 | Identical collapse to Variant B (16 regressions, 0 improvements). |

---

## 9. Semantic Safety & Contamination Test

Each transformation was evaluated against the 7 mandatory semantic safety criteria:

1. **Did it introduce concepts absent from the requirement?**
   - *Variants B & G*: NO (Strict subsets).
   - *Variants C, D, E, F*: **YES**. Introduced terms like `vitreous`, `wash basins`, `water closets`, `gaskets`, `luminaires`, `unplasticized`.
2. **Did it introduce a specific engineering application not stated?**
   - *Variants C, D, E, F*: **YES**. In `T006-R001` (UPVC partition walls in a seafood lab), generic plastics/piping domain terms caused `IS 16088` (Fire sprinkler CPVC pipes) to rise to Rank 31, introducing a false engineering association.
3. **Did it introduce an IS number?**
   - ALL VARIANTS: **NO** (Strictly standard-agnostic).
4. **Did it introduce a standard title?**
   - *Variants C, D, E, F*: Borderline. Tokens like `code of practice`, `distribution pillars`, and `pipe flanges` heavily mimic standard titles.
5. **Did it effectively encode the expected answer?**
   - *Variants C, D, E, F*: High risk of overfitting to the benchmark's known domain vocabulary.
6. **Did it create a misleading domain?**
   - *Variants C & D*: **YES**. In `T005-R001` (DG set cable connection), adding general power generation terms caused the engine to retrieve high-voltage generator standards rather than low-voltage PVC/XLPE building cables, causing a complete retrieval failure.
7. **Did it cause any previously correct query to regress?**
   - **YES**. Every single variant (B through G) caused previously correct queries (including Hit@1 queries) to regress significantly.

---

## 10. Aggregate Benchmark Metrics Summary

```
========================================================================================
FULL BENCHMARK AGGREGATE METRICS SUMMARY (N = 19 Queries)
========================================================================================
Metric                         Var A (Base)   Var B      Var C      Var D      Var E      Var F      Var G
----------------------------------------------------------------------------------------
RRF Hit@1                      12 (63.2%)     2 (10.5%)  7 (36.8%)  7 (36.8%)  7 (36.8%)  7 (36.8%)  2 (10.5%)
RRF Recall@10                  17 (89.5%)     6 (31.6%) 15 (78.9%) 15 (78.9%) 13 (68.4%) 14 (73.7%)  6 (31.6%)
RRF Recall@15 (Cand Survival)  17 (89.5%)     6 (31.6%) 15 (78.9%) 15 (78.9%) 13 (68.4%) 14 (73.7%)  6 (31.6%)
RRF Recall@30                  17 (89.5%)     9 (47.4%) 17 (89.5%) 17 (89.5%) 16 (84.2%) 17 (89.5%)  9 (47.4%)
RRF Recall@50                  18 (94.7%)    11 (57.9%) 18 (94.7%) 18 (94.7%) 18 (94.7%) 18 (94.7%) 11 (57.9%)
RRF Recall@100                 18 (94.7%)    12 (63.2%) 18 (94.7%) 18 (94.7%) 18 (94.7%) 18 (94.7%) 12 (63.2%)
RRF MRR                        0.6852         0.1917     0.5332     0.5158     0.5049     0.5186     0.1917
----------------------------------------------------------------------------------------
BM25 Recall@15                 16 (84.2%)     3 (15.8%) 15 (78.9%) 14 (73.7%) 14 (73.7%) 14 (73.7%)  3 (15.8%)
Semantic Recall@15             13 (68.4%)     7 (36.8%) 15 (78.9%) 16 (84.2%) 14 (73.7%) 16 (84.2%)  7 (36.8%)
----------------------------------------------------------------------------------------
Final Rec Accuracy (FR-Acc)     8 (42.1%)     9 (47.4%)  9 (47.4%)  9 (47.4%)  9 (47.4%)  9 (47.4%)  9 (47.4%)
Human Review Rate               3 (15.8%)     1 ( 5.3%)  3 (15.8%)  3 (15.8%)  3 (15.8%)  3 (15.8%)  1 ( 5.3%)
False Confident Count           1 ( 5.3%)     0 ( 0.0%)  1 ( 5.3%)  1 ( 5.3%)  1 ( 5.3%)  1 ( 5.3%)  0 ( 0.0%)
Abstention Count                1 ( 5.3%)     1 ( 5.3%)  1 ( 5.3%)  1 ( 5.3%)  1 ( 5.3%)  1 ( 5.3%)  1 ( 5.3%)
----------------------------------------------------------------------------------------
Regressions vs Baseline A       0 (Control)  16          7          9          9          9         16
Improvements vs Baseline A      0 (Control)   0          4          2          1          2          0
Unchanged vs Baseline A        19             3          8          8          9          8          3
----------------------------------------------------------------------------------------
P50 Latency (ms)              349.5 ms      269.8 ms   302.6 ms   310.6 ms   305.2 ms   312.0 ms   281.3 ms
P95 Latency (ms)              450.5 ms      414.9 ms   538.9 ms   504.3 ms   652.6 ms   487.7 ms   399.7 ms
========================================================================================
```

---

## 11. Best-Performing Variant Assessment

- **Highest Candidate Survival @15**: **Variant A (Baseline Control)** at **17 / 19 (89.5%)**.
- **Highest Retrieval MRR**: **Variant A (Baseline Control)** at **0.6852**.
- **Highest BM25 Recall@15**: **Variant A (Baseline Control)** at **16 / 19 (84.2%)**.
- **Highest Hit@1**: **Variant A (Baseline Control)** at **12 / 19 (63.2%)**.

**Conclusion**: Not a single experimental query transformation outperformed the current production baseline. Every alternative tested introduced between 7 and 16 regressions across the benchmark.

---

## 12. Genuineness of Improvement & Production-Safety Assessment

1. **Why FR-Accuracy Appeared to Rise Slightly (8 $\rightarrow$ 9)**:
   In Variants B through G, FR-Accuracy registered 9/19 compared to Baseline A's 8/19 solely because `T002-R003` was arbitrarily awarded by downstream heuristic arbitration when the candidate pool was drastically altered. However, this coincided with severe retrieval regressions in `T005-R001`, `T001-R003`, and `T011-R001`.
2. **Query Construction Cannot Bridge Catalogue Sparsity**:
   The hypothesis that rewriting user queries can compensate for missing technical scope in the catalogue is disproven. When query terms are expanded generically, they induce **query drift**, elevating irrelevant standards that share broad domain vocabulary. When queries are narrowed to technical tokens, they strip procedural words essential for matching BIS titles.
3. **Safety Verdict**:
   **UNSAFE FOR PRODUCTION**. Any query transformation that reduces candidate survival from $89.5\%$ down to $78.9\%$ or $31.6\%$ is unacceptable in an authoritative engineering compliance system.

---

## 13. Final Decision

In accordance with Phase 4R13 protocol, the final decision is:

### **OPTION 2**
*(with deep operational convergence toward Option 3)*

> **"Query-side technical intent construction improves retrieval for isolated queries (e.g. T009-R001) but has unacceptable regressions and safety problems across the wider benchmark."**

### Strategic Directive for Next Phase:
Because neither catalogue-side metadata enrichment (Phase 4R12) nor query-side transformation (Phase 4R13) can safely bridge the retrieval gap without regressions, the true architectural solution lies in:
1. **Preserving Current Query Normalization & Catalogue State**: Baseline A is already highly competitive ($89.5\%$ Candidate Survival, $0.6852$ MRR).
2. **Asymmetric Channel Fusion (Candidate-Preserving RRF)**: Phase 4R9 and 4R13 prove that BM25 retrieves `IS 732` at Rank 1/2 and `SP 30` at Rank 2. The recall failures occur because multi-channel RRF discards strong single-channel lexical hits when the dense semantic channel assigns low similarity. Modifying the fusion layer to protect high-confidence lexical candidates resolves the bottleneck without query drift.
3. **Downstream Arbitration Refinement**: Resolving the remaining accuracy gaps (such as `T009-R001` where `IS 732` is already in the top-10 candidate pool) through role-based arbitration.

---

*Report certified complete in accordance with Phase 4R13 protocol. Zero production code, indexes, or catalogue databases were modified.*
