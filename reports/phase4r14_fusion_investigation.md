# Phase 4R14 — Asymmetric / Candidate-Preserving Fusion Investigation

**Investigation Status**: COMPLETED (Investigation Only — Zero Production Changes)  
**Date**: September 2026  
**Scope**: Multi-Channel Candidate Preservation, Union Candidate Ceiling, Asymmetric Fusion, and Recommender Pipeline Evaluation across Frozen 19-Query Benchmark  
**Raw Data Artifact**: [`reports/phase4r14_fusion_investigation_data.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/reports/phase4r14_fusion_investigation_data.json)  
**Experiment Script**: [`scratch/phase4r14_fusion_investigation.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/scratch/phase4r14_fusion_investigation.py)  

---

## 1. Objective

Phase 4R12 demonstrated that enriching the BIS catalogue with authoritative administrative metadata regresses retrieval and fails to recover missing standards.  
Phase 4R13 demonstrated that generic query-side technical intent construction causes severe query drift and regressions across the benchmark.

Phase 4R14 investigated the remaining retrieval hypothesis:
> **Can the fusion layer preserve strong single-channel candidates, especially high-confidence BM25 candidates, without degrading the current production RRF baseline?**

The objective is **not** to replace RRF prematurely, but to determine empirically whether candidate-preserving or asymmetric fusion provides any measurable benefit over the frozen production baseline.

### Investigation Constraints:
- **ZERO production code changes**.
- Exact current production query Variant A used (no query rewriting, no synonyms, no administrative stripping).
- Frozen BIS catalogue (`data/catalogue/bis_catalogue.db`).
- Frozen embeddings (`bis_semantic_embeddings.npy`, `all-MiniLM-L6-v2`).
- Frozen BM25 index, candidate pool $K=15$, RRF $k=60$, terminology normalizer (Phase 4R8 Fix 1), and arbitration (Phase 4R8 Fix 2A).

---

## 2. Frozen Production Baseline (Variant A — Control)

The baseline configuration consists of:
- **Candidate Pool**: $K = 15$
- **RRF Constant**: $k = 60$
- **Retrieval Channels**: BM25 (expanded query), Semantic (`all-MiniLM-L6-v2`), Deterministic/Exact Citation
- **Downstream Arbitration**: Phase 4R8 Fix 2A (Technical Role Priority)

### Baseline Performance Metrics ($N = 19$):
- **Candidate Survival @15 (RRF Recall@15)**: **17 / 19 (89.5%)**
- **Recall@30**: **17 / 19 (89.5%)**
- **Recall@50**: **18 / 19 (94.7%)**
- **Recall@100**: **18 / 19 (94.7%)**
- **RRF Hit@1**: **12 / 19 (63.2%)**
- **RRF MRR**: **0.6852**
- **BM25 Recall@15**: **16 / 19 (84.2%)** | **BM25 Hit@1**: **7 / 19 (36.8%)** | **BM25 MRR**: **0.5330**
- **Semantic Recall@15**: **13 / 19 (68.4%)** | **Semantic Hit@1**: **7 / 19 (36.8%)** | **Semantic MRR**: **0.4634**
- **Final Recommendation Accuracy**: **8 / 19 (42.1%)** (or 9/19 under single-candidate tie-breaks)
- **Human-Review Required Rate**: **3 / 19 (15.8%)**
- **Abstention Count**: **1 / 19 (5.3%)**
- **False-Confident Count**: **1 / 19 (5.3%)**
- **Regressions**: **0** (Authoritative control)

---

## 3. Union Candidate Ceiling (Variant B)

To determine the theoretical upper bound of candidate recall before any fusion or ranking occurs, the pure set union of the top $K$ candidates from BM25 and Semantic retrieval ($BM25[:K] \cup Semantic[:K]$) was evaluated across $K \in \{10, 15, 30, 50, 100\}$:

| Pool Size ($K$) | Union Candidates Hit | Candidate Recall | Missing Queries |
|---|:---:|:---:|---|
| **$K = 10$** | 16 / 19 | **84.2%** | `T004-R002`, `T006-R001`, `T014-R002` |
| **$K = 15$** | 16 / 19 | **84.2%** | `T004-R002`, `T006-R001`, `T014-R002` |
| **$K = 30$** | 18 / 19 | **94.7%** | `T006-R001` |
| **$K = 50$** | 18 / 19 | **94.7%** | `T006-R001` |
| **$K = 100$** | 19 / 19 | **100.0%** | *None (All 19 recovered)* |

### Critical Observations on Union Ceiling:
1. **At $K = 15$, pure Union (84.2%) is actually WORSE than Baseline RRF (89.5%)!**  
   In Baseline RRF, `T004-R002` is ranked **1** because deterministic search / exact citation resolves it immediately, whereas in pure lexical + semantic channels without deterministic integration, it sits at BM25 Rank 69 and Semantic Rank 25.
2. **`T014-R002` Enters at $K = 30$**: In the dense semantic channel, `IS/IEC 60034-1` appears at **Rank 24**. At $K \ge 30$, it enters the union pool.
3. **`T006-R001` Enters at $K = 100$**: In BM25, `IS 16088` appears at **Rank 51**. It is completely absent from the Semantic top 150. Only at $K \ge 51$ does it enter the union pool.
4. **Theoretical Limit**: The theoretical maximum candidate ceiling achievable within a candidate pool of $K=15$ without changing the underlying retrievers is **17 / 19 (89.5%)**.

---

## 4. Fusion Experiments

Six distinct fusion architectures and 14 specific configurations were systematically evaluated across the full 19-query benchmark:

- **Variant A**: Current Production RRF ($k=60, K=15$) [Control].
- **Variant B**: Union Candidate Ceiling (described in Section 3).
- **Variant C**: **BM25-Preserving Fusion**: Candidates in BM25 top $N \in \{1, 2, 3, 5\}$ are guaranteed inclusion in the top-15 candidate pool before final truncation.
- **Variant D**: **Semantic-Preserving Fusion**: Candidates in Semantic top $N \in \{1, 2, 3, 5\}$ are guaranteed inclusion in the top-15 candidate pool.
- **Variant E**: **Dual-Channel Candidate Preservation**: Candidates in top $N$ of either channel are preserved ($N \in \{(1,1), (2,2), (3,3), (5,5)\}$).
- **Variant F**: **Score-Gated Preservation**: Candidates with BM25 normalized score $\ge 0.85$ or Semantic similarity score $\ge 0.55$ are preserved.

---

## 5. Per-Query Diagnostic Results

The table below details the individual channel ranks and fused candidate pool positions across all 19 queries:

| Query ID | Expected Standard | BM25 Rank | Sem Rank | Base RRF Rank | BM25 Pres (N=5) | Sem Pres (N=5) | Dual Pres (5,5) | In Pool @15? |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **T001-R002** | IS 15905 / IS 1239-1 | **3** | 48 | **1** | **1** | **1** | **1** | **YES** |
| **T001-R003** | IS 15622 | **1** | 9 | **7** | **7** | **7** | **7** | **YES** |
| **T001-R004** | IS 2556 / IS 781 / IS 774 | **1** | **1** | **1** | **1** | **1** | **1** | **YES** |
| **T002-R003** | IS 6392 / IS 2712 | **2** | **1** | **4** | **4** | **4** | **4** | **YES** |
| **T003-R001** | IS/IEC 61439-3 | **1** | 4 | **1** | **1** | **1** | **1** | **YES** |
| **T004-R002** | IS 7098-1 / IS 1255 | 69 | 25 | **1** (Det) | **1** | **1** | **1** | **YES** |
| **T004-R005** | IS 5039 / IS/IEC 61439-5 | **1** | **1** | **1** | **1** | **1** | **1** | **YES** |
| **T005-R001** | IS 3043 / IS 7098-1 | **2** | **2** | **1** | **1** | **1** | **1** | **YES** |
| **T006-R001** | IS 16088 | 51 | None | None | None | None | None | **NO** |
| **T007-R003** | IS 2491 / IS 15000 | 8 | **2** | **1** | **1** | **1** | **1** | **YES** |
| **T009-R001** | SP 30 / IS 732 | **1** | 71 | **10** | **10** | **10** | **9** | **YES** |
| **T010-R001** | IS 458 / IS 783 / IS 14333 | 4 | **1** | **1** | **1** | **1** | **1** | **YES** |
| **T011-R001** | IS 7098-1 / IS 1255 | **2** | 9 | **4** | **4** | **4** | **4** | **YES** |
| **T012-R002** | IS 1661 / IS 269 | **1** | **1** | **1** | **1** | **1** | **1** | **YES** |
| **T012-R003** | IS 1239-2 / IS 778 | **1** | 6 | **1** | **1** | **1** | **1** | **YES** |
| **T013-R002** | IS/IEC 61800-2 | **3** | 20 | **4** | **4** | **4** | **4** | **YES** |
| **T013-R003** | IS 14164 / IS 8183 | **3** | **1** | **1** | **1** | **1** | **1** | **YES** |
| **T014-R002** | IS/IEC 60034-1 / IS 5120 | 55 | 24 | **39** | **39** | 40 | 40 | **NO** |
| **T020-R001** | IS 15778 / IS 1239-1 | 5 | **1** | **1** | **1** | **1** | **1** | **YES** |

---

## 6. Detailed Analysis of Key Queries

### 6.1. T009-R001 (Electrical & Mechanical AMC)
- **Requirement**: *"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"*
- **Expected Standards**: `SP 30 : 2023` (National Electrical Code) / `IS 732 : 2019` (Electrical Wiring Installations)
- **Channel Ranks**: BM25: **Rank 1** (`SP 30`), Semantic: **Rank 71** (`IS 732`)
- **Baseline RRF Rank**: **Rank 10** (`IS 732`)
- **Findings**:
  1. `IS 732` is **ALREADY in the top-15 candidate pool** at Rank 10 under baseline RRF!
  2. RRF did **not** drop or lose the candidate.
  3. Downstream in arbitration, `IS 12457` (Code of practice for concrete batching plants) was selected because of a domain mismatch in arbitration logic, **not** because `IS 732` was missing from retrieval.
  4. Candidate preservation variants do not change this outcome: `IS 732` was already preserved, and downstream arbitration still selects `IS 12457`.

### 6.2. T005-R001 (DG Set Cable Connection)
- **Requirement**: *"Cable connection of DG Set in Newly constructed building of the Dept. of Molecular , Human Genetics"*
- **Expected Standards**: `IS 3043 : 2018` (Earthing) / `IS 7098 (Part 1) : 1988` (XLPE Cables)
- **Channel Ranks**: BM25: **Rank 2**, Semantic: **Rank 2**
- **Baseline RRF Rank**: **Rank 1**
- **Findings**:
  1. This query was catastrophically destroyed in Phase 4R13 by query expansion (`Rank 1 → None`).
  2. Under all fusion preservation variants (C, D, E, F), `T005-R001` **correctly remains at Rank 1**.
  3. Candidate-preserving fusion preserves this high-performing result safely.

### 6.3. T011-R001 (HT Cable Fault Finding & Jointing)
- **Requirement**: *"HT Cable fault finding and cable jointing..."*
- **Expected Standards**: `IS 7098 (Part 1) : 1988` / `IS 1255 : 1983`
- **Channel Ranks**: BM25: **Rank 2**, Semantic: **Rank 9**
- **Baseline RRF Rank**: **Rank 4**
- **Findings**:
  1. `IS 7098 (Part 1)` is already securely positioned in the top-5 pool.
  2. Candidate preservation leaves its position unchanged across all variants.

### 6.4. T001-R003 (Wall Tiles)
- **Requirement**: *"wall tiles"*
- **Expected Standard**: `IS 15622 : 2017` (Ceramic Tiles)
- **Channel Ranks**: BM25: **Rank 1**, Semantic: **Rank 9**
- **Baseline RRF Rank**: **Rank 7**
- **Findings**:
  1. Even though the query is only two words, both channels identify `IS 15622` in their top 10.
  2. Baseline RRF places it at Rank 7 (inside the $K=15$ candidate pool).
  3. Preserving BM25 top 1 does not alter its rank because it was already present in the candidate pool.

### 6.5. T013-R002 (VFD Panel for AHU Fans)
- **Requirement**: *"VFD panel for AHU fans..."*
- **Expected Standard**: `IS/IEC 61800-2 : 2015` (Adjustable speed electrical power drive systems)
- **Channel Ranks**: BM25: **Rank 3**, Semantic: **Rank 20**
- **Baseline RRF Rank**: **Rank 4**
- **Findings**:
  1. Despite Semantic ranking it at Rank 20, the high BM25 rank (Rank 3) pulls it up to **Fused Rank 4** in standard RRF.
  2. This confirms that standard RRF already possesses strong asymmetric single-channel elevation capability.

### 6.6. T014-R002 (Pump Motor Rewinding & Overhauling)
- **Requirement**: *"Rewinding and overhauling of pump motor sets..."*
- **Expected Standards**: `IS/IEC 60034-1 : 2014` (Rotating Electrical Machines) / `IS 5120 : 1977`
- **Channel Ranks**: BM25: **Rank 55**, Semantic: **Rank 24**
- **Baseline RRF Rank**: **Rank 39**
- **Findings**:
  1. **The candidate is absent from the top tier of BOTH channels**. Neither channel ranks it in the top 20.
  2. Candidate preservation at $N \in \{1, 2, 3, 5\}$ cannot recover `T014-R002` because neither retriever surfaces it as a top candidate.
  3. In Semantic-preserving and Dual-preserving variants ($N=5$), `T014-R002` regresses slightly from Rank 39 to Rank 40 because top-5 semantic distractors displace it further down the fused list.
  4. **Conclusion**: Fusion did **not** cause the failure in `T014-R002`; the failure originates upstream in the individual retrieval channels.

---

## 7. Full Benchmark Metrics Summary

```
========================================================================================================================
PHASE 4R14 BENCHMARK RESULTS: ASYMMETRIC / CANDIDATE-PRESERVING FUSION (N = 19 QUERIES)
========================================================================================================================
Variant         Hit@1   R@10    R@15(Surv) R@30    R@50    R@100   MRR     FR-Acc  Regs  Imps  Unch  P50 Lat   P95 Lat
------------------------------------------------------------------------------------------------------------------------
A_Base (RRF)    12      17      17 (89.5%) 17      18      18      0.6852  8/9*    0     0     19    308.2 ms  485.2 ms
C_BM25_top1     12      17      17 (89.5%) 17      18      18      0.6852  8       0     0     19    308.2 ms  485.2 ms
C_BM25_top2     12      17      17 (89.5%) 17      18      18      0.6852  9       0     0     19    308.2 ms  485.2 ms
C_BM25_top3     12      17      17 (89.5%) 17      18      18      0.6852  9       0     0     19    308.2 ms  485.2 ms
C_BM25_top5     12      17      17 (89.5%) 17      18      18      0.6852  8       0     0     19    309.6 ms  488.1 ms
D_Sem_top1      12      17      17 (89.5%) 17      18      18      0.6852  8       0     0     19    309.7 ms  485.7 ms
D_Sem_top2      12      17      17 (89.5%) 17      18      18      0.6852  7       0     0     19    310.0 ms  490.8 ms
D_Sem_top3      12      17      17 (89.5%) 17      18      18      0.6852  7       1     0     18    308.2 ms  485.2 ms
D_Sem_top5      12      17      17 (89.5%) 17      18      18      0.6852  7       1     0     18    308.3 ms  485.2 ms
E_Dual_top1     12      17      17 (89.5%) 17      18      18      0.6852  8       0     0     19    308.2 ms  485.2 ms
E_Dual_top2     12      17      17 (89.5%) 17      18      18      0.6852  8       0     0     19    308.2 ms  485.2 ms
E_Dual_top3     12      17      17 (89.5%) 17      18      18      0.6852  8       1     0     18    308.2 ms  485.2 ms
E_Dual_top5     12      17      17 (89.5%) 17      18      18      0.6857  8       1     1     17    308.3 ms  485.2 ms
F_ScoreGated    12      17      17 (89.5%) 17      18      18      0.6852  7       1     0     18    308.2 ms  485.2 ms
========================================================================================================================
*Note: FR-Acc shows 8 or 9 depending on tie-break resolution in T001-R002 between IS 15905:2024 vs IS 15905:2011.
```

---

## 8. Regression & Candidate Preservation Analysis

### 8.1. Why Did Candidate Survival Not Change?
Every single candidate preservation variant (C1–C4, D1–D4, E1–E4, F) achieved exactly **17 / 19 (89.5%)** Candidate Survival @ 15.
- The 17 queries that were already in the top 15 under Baseline RRF remained in the top 15.
- The 2 queries outside the top 15 (`T006-R001` at BM25 Rank 51; `T014-R002` at BM25 Rank 55 and Sem Rank 24) could **not** be preserved because neither channel ranked them within $N \le 5$ or above the score gating threshold.
- Therefore, candidate preservation provides **zero net improvement in Candidate Survival @ 15**.

### 8.2. Introduction of Semantic Distractors
When semantic candidates from Rank 3 to Rank 5 were forcibly preserved into the $K=15$ candidate pool (Variants D3, D5, E3, E5, and F):
- They displaced valid secondary candidates that had consensus support.
- In `T014-R002`, the expected candidate dropped from Rank 39 to Rank 40 (retrieval regression).
- Downstream FR-Accuracy **decreased** from 8/9 down to **7 / 19** because preserved semantic distractors with generic titles confused the downstream Critic and Applicability Gate.

---

## 9. Latency Analysis

| Variant Group | P50 Latency (ms) | P95 Latency (ms) | Overhead vs Baseline |
|---|:---:|:---:|:---:|
| **A_Base (Control)** | 308.2 ms | 485.2 ms | — |
| **C (BM25-Preserving)** | 308.2 – 309.6 ms | 485.2 – 488.1 ms | +0.0% to +0.4% |
| **D (Semantic-Preserving)** | 308.2 – 310.0 ms | 485.2 – 490.8 ms | +0.0% to +0.6% |
| **E (Dual-Channel Preserving)**| 308.2 – 308.3 ms | 485.2 ms | +0.0% |
| **F (Score-Gated Preserving)** | 308.2 ms | 485.2 ms | +0.0% |

All preservation logic operates as an $O(K)$ array transformation on pre-ranked hits, adding negligible overhead ($\le 2$ ms). Latency is not an impediment, but neither does it justify adoption without accuracy gains.

---

## 10. Production Safety Assessment

1. **Standard-Agnostic Character**: The preservation rules evaluated were entirely generic (rank-threshold based) and contained no hardcoded standard identifiers.
2. **Benchmark Inefficacy**: Because 17 of 19 queries already have their expected standards within the top 15, and the remaining 2 queries have ranks $\ge 24$, rank-gated preservation at $N \le 5$ produces no new candidate recoveries.
3. **Downstream Safety Risk**: Forcibly inserting low-consensus semantic candidates into the candidate pool increases distractor density, reducing downstream recommendation accuracy from 8/9 to 7.

---

## 11. Final Decision

In accordance with the Phase 4R14 protocol, the decision is:

### **OPTION 3**
> **"Fusion is not the primary bottleneck; candidate preservation does not materially improve the benchmark."**

### Architectural Rationale & Next Investigation Directive:
1. **RRF is Already Robust**: The current production Reciprocal Rank Fusion ($k=60$) already elevates strong single-channel candidates effectively (e.g. `T001-R002`, `T009-R001`, `T013-R002` all reach the top 10 despite low semantic scores).
2. **The Real Bottlenecks are Upstream and Downstream**:
   - **Upstream (Retrieval Missing Ranks)**: In `T006-R001` (BM25: 51) and `T014-R002` (BM25: 55, Sem: 24), the expected standards are simply ranked too low by both individual retrievers. Fusion cannot rescue candidates that neither retriever finds.
   - **Downstream (Arbitration / Domain-Scope Conflict)**: In `T009-R001`, `IS 732` is already at Fused Rank 10 in the candidate pool. It fails to be recommended solely because downstream arbitration allows a domain-mismatched standard (`IS 12457`) to win.
3. **Recommended Next Phase**: Investigate **Downstream Domain-Scope Conflict Arbitration** to resolve the known misclassifications (e.g. `T009-R001`, `T001-R002`, `T002-R003`) where the correct standard is already present in the candidate pool.

---

## 12. Reproducibility & Environment Manifest

- **Git Commit Hash**: `e0d3fbcf0a82b653dfa22d2764c9cc8351fb1bcf`
- **Catalogue Database**: `data/catalogue/bis_catalogue.db` (SHA256: `bd04dab6f7d5cd4ea58fa69c917b1fa5d375f721ee4ec03691dfc7eb1b0850b3`)
- **Semantic Embeddings**: `data/catalogue/bis_semantic_embeddings.npy` (SHA256: `216c40ac0ac8a685c44a55dfb07fc46354eb7d14d10acfb3e5514979c9dc41be`)
- **Benchmark Dataset**: `dataset/ground_truth/ground_truth.csv` (SHA256: `cfcbca27a729bd0619886be9128cfba272b912bd21115604b45af7eb59fa404b`)
- **Candidate Pool Size ($K$)**: 15
- **RRF Parameter ($k$)**: 60
- **Neural Reranker**: Disabled in baseline hybrid search
- **AI / LLM Understanding**: Disabled (Deterministic offline evaluation)
- **Zero Production Modifications Certified**.
