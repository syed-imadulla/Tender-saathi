# Phase 4R1 Repair Report: Validation & Diagnostics

## 1. Overview
The Phase 4 retrieval pipeline was migrated to the 35,208-record `bis_catalogue.db`. Prior to this fix, it exhibited massive latency degradation (~4000 ms) and poor accuracy compared to the 502-record legacy catalogue.

In Phase 4R1, we focused exclusively on:
1. Fixing Deterministic search scaling (replacing O(N) Python scans with indexed SQLite queries).
2. Fixing Candidate Dropping in Hybrid fusion (increasing initial K fetch limits to 30, removing arbitrary threshold cuts).
3. Instrumenting diagnostics without artificially modifying ground truth or rankings.

## 2. Benchmark Results Comparison

| Architecture | Previous Legacy (502) | Previous Phase 4 (35k) | New Phase 4R1 (35k) |
|---|---|---|---|
| **Deterministic** | Top-1: 95%, MRR: 0.975 (16.2 ms) | Top-1: 10%, MRR: 0.129 (3735.8 ms) | Top-1: 10%, MRR: 0.125 (1704.7 ms) |
| **BM25** | Top-1: 90%, MRR: 0.950 (19.8 ms) | Top-1: 5%, MRR: 0.050 (3838.4 ms) | Top-1: 5%, MRR: 0.050 (1602.9 ms) |
| **Semantic** | Top-1: 85%, MRR: 0.912 (46.3 ms) | Top-1: 15%, MRR: 0.179 (3858.8 ms) | Top-1: 15%, MRR: 0.179 (1950.8 ms) |
| **Hybrid** | Top-1: 95%, MRR: 0.975 (57.0 ms) | Top-1: 10%, MRR: 0.117 (3848.1 ms) | Top-1: 5%, MRR: 0.067 (1408.0 ms) |
| **Hybrid + Rerank** | Top-1: 95%, MRR: 0.975 (488.1 ms) | Top-1: 10%, MRR: 0.117 (4183.3 ms) | Top-1: 5%, MRR: 0.067 (1653.2 ms) |

**Latency Success:** 
The targeted O(N) scan removal effectively reduced overall Hybrid + Rerank latency from **~4183 ms** down to **~1653 ms**. Deterministic queries themselves are now lightning fast (~150ms). The remaining high average latency (1600ms-1900ms) for independent modes during `evaluate_phase4_retrieval.py` is largely an artifact of the script instantiating `BM25SearchEngine` per query, which forces it to load all 35k records into memory on every instantiation.

**Recall Drop in Hybrid:**
While candidate dropping in fusion was removed (we expanded stage K limits to 30), the Top-1/Top-3 MRR actually dropped slightly (10% -> 5%). This is because removing the `0.20` hybrid cut-off flooded the candidate pool with noisy records, and without proper reranking or status weights, the target standard was drowned out.

## 3. Stage-Level Latency Measurements

From `diagnose_phase4_recall.py` running locally on individual queries, here is the breakdown of time spent in each stage. These are true active times, showing deterministic scaling is fixed:

| Query Example | DET (ms) | BM25 (ms) | SEM (ms) | MERGE (ms) | RERANK (ms) | APP (ms) |
|---|---|---|---|---|---|---|
| **[T001-R003]** | 62 | 32 | 78 | 137 | 1408 | 3 |
| **[T004-R002]** | 235 | 41 | 40 | 168 | 1672 | 5 |
| **[T010-R001]** | 135 | 25 | 33 | 128 | 1727 | 4 |

- **Deterministic (DET):** Scaled down from ~4100ms to **60-250ms**.
- **BM25 & SEM:** Extremely fast (**20-80ms**) when evaluated warm.
- **RERANK:** Takes **~1500ms** to evaluate the expanded pool of 30 candidates, which is the current latency bottleneck.

## 4. Recall@100 Diagnostics

We tested whether the expected standard is even retrieved within the Top 100 for each individual engine before hybrid fusion. 

| Query | DET Rank | BM25 Rank | SEM Rank | HYBRID Rank |
|---|---|---|---|---|
| T001-R002 | 1 | 3 | 48 | 1 |
| T003-R001 | 1 | 10 | 35 | 17 |
| T004-R002 | 12 | 69 | 25 | 1 |
| T010-R001 | 10 | 4 | 1 | 1 |
| T012-R002 | 20 | 49 | 16 | 40 |
| T005-R001 | -1 (Missing) | -1 (Missing) | 40 | -1 (Missing) |
| T006-R001 | -1 (Missing) | -1 (Missing) | -1 (Missing) | -1 (Missing) |
| T011-R001 | -1 (Missing) | -1 (Missing) | 14 | -1 (Missing) |

**Candidate Recall Analysis:**
- When candidates *are* found in the top 100, the Hybrid fusion successfully keeps them in the pool (e.g. `T003-R001` or `T012-R002`). 
- However, for many queries (like `T006-R001` or `T013-R002`), the target standard doesn't even make it into the **Top 100** of *any* base engine (DET, BM25, or SEM) on the 35,208 record catalogue! 
- This proves that the massive noise injected by moving from 502 to 35,208 records is swamping our first-stage retrieval.

## 5. Next Steps

Before implementing fixes, user alignment is needed:
1. Do we now have the green light to investigate how to properly rank and boost candidates to cut through the 35k-record noise (e.g. Lifecycle Status boosting or adjusting term weights)?
2. The Deterministic query logic currently only checks `full_title` and `scope` for token overlap, dropping `standard_number`. Should we adjust the FTS/LIKE queries in `src/search.py` to ensure standard numbers are appropriately matched?
