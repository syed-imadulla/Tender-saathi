# Phase 4 Retrieval Repair Plan (R1)

## A. Latency Bottleneck
- **Deterministic Search (`src/search.py`)**: Currently performs an O(N) scan using Python string loops (`in title_lower`) over all 35,208 records per query. This blocks execution for ~5 seconds. We will refactor this to use native SQLite parameterized queries (`LIKE`, `GLOB`, or FTS if configured) to push the filtering workload down to the database engine.
- **Model / Data Loading**: We will ensure that the 35,208-record BM25 inverted index and Semantic embeddings matrix are loaded once per session and cached, preventing repeated disk I/O overhead.
- **Query Processing**: The downstream pipeline will only load and process database records for the limited Top-K candidates, rather than loading the entire catalogue into Python memory.

## B. First-Stage Retrieval Bottleneck (Candidate Recall)
- The current Top-K limits (e.g., K=5 or K=8) in `search.py`, `bm25_search.py`, and `semantic_search.py` are too tight for a 35,208-record database. True positives are being squeezed out by noise.
- **Action**: We will expand the first-stage candidate retrieval pool (e.g., K=20 or K=30) before passing them to the Applicability Gate or Cross-Encoder. This ensures that the expected standards actually enter the candidate pool.

## C. Ranking Bottleneck
- Pure keyword (BM25) and Semantic scores are heavily diluted by similar terminology across 35k records (e.g., "wall tiles" hits hundreds of obsolete or unrelated tile standards). 
- **Action**: The Hybrid Retrieval Engine (`src/retrieval.py`) must be modified to apply a **status penalty** to WITHDRAWN/UNKNOWN standards, or a **status boost** to ACTIVE standards during the score normalization and merging phase, *before* handing candidates to the downstream gates.

## D. Lifecycle/Status Problem
- We cannot delete withdrawn standards because explicit citations in legacy tenders (e.g., citing a 1980s standard) still need to be resolved to their current active successors.
- **Action**: Retrieval will remain open to all lifecycle statuses to preserve explicit citation provenance, but the *ranking* math will heavily prioritize ACTIVE standards when relevance scores are tied or close. The final `StandardRecommendation` output will continue to surface the `warning_message` if a withdrawn standard is explicitly matched.

## E. Downstream ApplicabilityGate Interaction
- The `ApplicabilityGate` (`src/applicability.py`) currently abstains ("NO_RELIABLE_MATCH") because the small candidate pool provided to it consists entirely of noise, and the gate strictly enforces domain boundaries.
- **Action**: By fixing Candidate Recall (B) and Ranking (C), the Applicability Gate will receive higher-quality candidates. We will not loosen the gate's strictness; we will simply feed it better upstream candidates.

## Implementation Plan

1. **Diagnostic Instrumentation (Part 4)**: Implement a diagnostic mode in `evaluate_phase4_retrieval.py` to measure Recall@100 for each retrieval mode without breaking the main benchmark scoring.
2. **Refactor `src/search.py`**: Replace Python dictionary iteration with parameterized SQLite queries for exact matches, superseded queries, and partial title hits.
3. **Refactor Index Caching**: Verify/fix caching in `src/bm25_search.py` and `src/semantic_search.py`.
4. **Lifecycle Ranking Boost**: Update `src/retrieval.py` to boost `ACTIVE` standards during the final hybrid score combination.
5. **Adjust K Thresholds**: Increase candidate pool sizes fed into the `HybridRetrievalEngine` and `CrossEncoder`.
6. **Testing**: Run the updated retrieval tests and the 20-query benchmark. Verify against acceptance targets (< 600ms latency, ~95% accuracy).

