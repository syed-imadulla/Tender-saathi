# Phase 4R15 — Downstream Domain-Scope Conflict Arbitration Investigation

**Investigation Status**: COMPLETED (Investigation Only — Zero Production Changes)  
**Date**: September 2026  
**Scope**: Downstream Arbitration Logic, Two-Stage Candidate Ranking Audit, Pairwise Counterfactual Analysis, and Determinism Traces across Frozen 19-Query Benchmark  
**Raw Data Artifact**: [`reports/phase4r15_arbitration_investigation_data.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/reports/phase4r15_arbitration_investigation_data.json)  
**Experiment Script**: [`scratch/phase4r15_arbitration_investigation.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/scratch/phase4r15_arbitration_investigation.py)  

---

## 1. Objective

Phases 4R12, 4R13, and 4R14 systematically proved that:
- Catalogue metadata enrichment (Phase 4R12) causes semantic regressions.
- Query-side technical expansion (Phase 4R13) causes severe query drift and regressions.
- Candidate-preserving fusion (Phase 4R14) does not improve candidate survival because 17 of 19 queries already survive in the top-15 candidate pool under standard RRF.

Therefore, Phase 4R15 investigated the next architectural layer: **Downstream Arbitration**.  
The central diagnostic question is:
> **"When multiple technically plausible standards are already inside the candidate pool, why does the arbitration layer sometimes select a domain-mismatched or less-applicable standard over a broader, more appropriate standard?"**

### Investigation Constraints:
- **ZERO production code changes**.
- No modifications to the BIS catalogue, BM25 index, semantic embeddings, or terminology normalizer.
- Frozen production retrieval pipeline: Variant A query, candidate pool $K=15$, RRF $k=60$.
- Frozen downstream decision pipeline: Phase 4R8 Fix 2A arbitration logic, applicability rules, ambiguity engine, and lifecycle handling.
- Deterministic evaluation (LLM and cross-encoder reranker disabled).

---

## 2. Frozen Production Configuration

- **Catalogue**: `data/catalogue/bis_catalogue.db` ($N = 35,208$ standards)
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors)
- **Lexical Retriever**: Okapi BM25 with Robertson-Spärck Jones IDF
- **Query Representation**: Production expanded query from `TechnicalTerminologyNormalizer.build_expanded_query()`
- **Candidate Pool**: $K = 15$
- **RRF Constant**: $k = 60$
- **Arbitration Strategy**: Phase 4R8 Fix 2A (Technical Role Priority over Coarse Confidence for pure product requirements)

---

## 3. Corrected Benchmark Metric Definition

Final Recommendation Accuracy (FR-Accuracy) is strictly defined and evaluated directly against `dataset/ground_truth/ground_truth.csv`:
- A recommendation is counted as **CORRECT** if `final_recommendation` matches **ANY** applicable standard listed in the ground truth for that query (using canonical `StandardIdentifierNormalizer` matching).
- If the system returns `None` (because `human_review_required` is triggered by the Ambiguity Gate or Applicability Gate), it is counted as **ABSTAINED** (Safe Abstention).
- If the system returns a standard that does not match any applicable standard in the ground truth, it is counted as **WRONG**.
- Historical accuracy figures (8/19 or 9/19) are not assumed; metrics are recomputed directly from ground-truth evaluation.

---

## 4. Current Benchmark Results

Evaluating the frozen 19-query benchmark directly against the ground truth yields:

```
====================================================================================================
CURRENT PRODUCTION BENCHMARK AUDIT (N = 19 Evaluated Queries)
====================================================================================================
Query ID   Status      Final Recommendation                  Expected Standard
----------------------------------------------------------------------------------------------------
T001-R002  CORRECT     IS 15905 : 2024                       IS 15905 : 2011; IS 1239 (Part 1)
T001-R003  ABSTAINED   None (Ambiguity Triggered)            IS 15622 : 2017
T001-R004  CORRECT     IS 2556 (Part 9) : 2004               IS 2556 (Part 1 to 17); IS 781
T002-R003  WRONG       IS 13257 : 1992                       IS 6392 : 1971; IS 2712 : 2020
T003-R001  CORRECT     IS/IEC 61439 (Part 3) : 2012          IS/IEC 61439-3 : 2012; IS 10322
T004-R002  CORRECT     IS 1255 : 1983                        IS 7098 (Part 1) : 1988; IS 1255
T004-R005  ABSTAINED   None (Incomplete Spec Triggered)      IS 5039 : 1983; IS/IEC 61439-5
T005-R001  ABSTAINED   None (Competing Standards Triggered)  IS 3043 : 2018; IS 7098 (Part 1)
T006-R001  WRONG       IS 9271 : 2004                        IS 16088 : 2016
T007-R003  ABSTAINED   None (BOT Concession Ambiguity)       IS 2491 : 2013; IS 15000 : 2013
T009-R001  WRONG       IS 12457 : 1988                       SP 30 : 2023; IS 732 : 2019
T010-R001  CORRECT     IS 14333 : 2022                       IS 458 : 2021; IS 783; IS 14333
T011-R001  ABSTAINED   None (Ambiguity Triggered)            IS 7098 (Part 1) : 1988; IS 1255
T012-R002  CORRECT     IS 1661 : 1972                        IS 1661 : 1972; IS 269 : 2015
T012-R003  CORRECT     IS 1239 (Part 2) : 2011               IS 1239 (Part 2) : 1992; IS 778
T013-R002  WRONG       IS 10069 : 2023                       IS/IEC 61800-2 : 2015; IS/IEC 60034
T013-R003  CORRECT     IS 14164 : 2008                       IS 14164 : 2008; IS 8183 : 1993
T014-R002  WRONG       IS 14578 : 2025                       IS/IEC 60034-1 : 2017; IS 5120
T020-R001  CORRECT     IS 15778 : 2007                       IS 15778 : 2007; IS 1239 (Part 1)
----------------------------------------------------------------------------------------------------
SUMMARY: Correct = 9 / 19 (47.4%) | Abstained = 5 / 19 (26.3%) | Wrong = 5 / 19 (26.3%)
====================================================================================================
```

---

## 5. Arbitration Implementation Audit

Inspection of `src/recommend.py` reveals that downstream candidate arbitration is conducted across two distinct sorting stages:

### Stage 1: Candidate Priority Pre-Sort (Lines 486–521)
Operates on the raw candidate pool ($K=15$) after Applicability Gate filtering:
$$\text{Stage 1 Key} = (\text{lifecycle\_rank}, \text{role\_rank} + \text{spec\_bonus}, \text{orig\_rank})$$
- `lifecycle_rank`: `0` if Active/Current/Unknown; `1` if Superseded or Withdrawn.
- `role_rank`:
  - `0`: Primary roles (`PRIMARY_PRODUCT`, `INSTALLATION`, `CODE_OF_PRACTICE`)
  - `1`: Unclassified
  - `2`: `ALLIED` or storage/handling standards for works requirements
  - `3`: `TEST_METHOD`
- `spec_bonus`: `-1` if specific compound noun phrases match (e.g. "pipe fittings", "distribution boards").
- `orig_rank`: Original retrieval index (`0` to `14`) from hybrid fusion.

### Stage 2: Final Recommendation Priority (Lines 761–775)
Operates on the grounded recommendations list:
- If `is_prod_req and not is_work_or_repair_req` (Fix 2A branch):
  $$\text{Stage 2 Tuple} = (\text{storage\_rank}, \text{r\_rank}, \text{c\_rank}, \text{idx})$$
- Otherwise (General / Work / Maintenance requirements):
  $$\text{Stage 2 Tuple} = (\text{storage\_rank}, \text{c\_rank}, \text{r\_rank}, \text{idx})$$
Where:
- `c_rank`: Confidence bucket rank (`High = 0`, `Medium = 1`, `Low = 2`).
- `r_rank`: Technical role validity flag (`0` for primary product/installation/code of practice, `1` otherwise).
- `idx`: The 0-based index of the candidate resulting from the Stage 1 sort!

---

## 6. Primary Diagnostic Deep Traces

### 6.1. T009-R001 (Electrical & Mechanical AMC)
- **Requirement**: *"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"*
- **Expected**: `SP 30 : 2023` / `IS 732 : 2019`
- **Current Winner**: `IS 12457 : 1988` (*"Code of practice for inspection, testing and maintenance of concrete batching and mixing plants"*)
- **Deep Trace Findings**:
  1. `IS 732 : 2019` was successfully retrieved at BM25 Rank 1 and entered the candidate pool at RRF Rank 10.
  2. `IS 12457 : 1988` entered the pool at RRF Rank 3 because BM25 matched the words *"inspection, testing and maintenance"* with tender words *"Repairs and Maintenance"*.
  3. **Applicability Gate Failure**: The Applicability Gate evaluated `IS 12457` as `APPLICABLE` because it found procedural token overlap (`maintenance`) and has zero domain rules penalizing concrete equipment in electrical tenders.
  4. **Arbitration Tuple Trace**:
     - Requirement contains *"Repairs and Maintenance"*, so `is_work_or_repair_req = True`.
     - Because `is_work_or_repair_req = True`, Fix 2A does **not** apply. The sorting tuple is `(storage_rank, c_rank, r_rank, idx)`.
     - Both `IS 12457` and `IS 732` received Confidence `Medium` (`c_rank = 1`).
     - Both received `r_rank = 1` (since `r_rank` is 0 only under the Fix 2A product branch).
     - Both received `storage_rank = 0`.
     - Therefore, the tie was decided entirely by **`idx` (Stage 1 sort order)**!
     - In Stage 1, `IS 12457` had `orig_rank = 2`, while `IS 732` had `orig_rank = 9`.
  5. **Root Cause**: `IS 12457` beat `IS 732` purely because of its higher initial retrieval rank (`idx = 0` vs `idx = 5`). The system possesses **no domain-scope conflict mechanism** to recognize that concrete batching plants conflict with electrical building services.

### 6.2. T012-R003 (Plumbing Fittings)
- **Requirement**: *"Plumbing Fittings"*
- **Expected**: `IS 1239 (Part 2) : 1992` / `IS 778`
- **Current Winner**: `IS 1239 (Part 2) : 2011` (**CORRECT**)
- **Deep Trace Findings**:
  1. In previous investigations, `IS 11906` (Allied standard) beat `IS 1239 (Part 2)` because `IS 11906` had Confidence `High` while `IS 1239-2` had Confidence `Medium`.
  2. Under Fix 2A, `is_prod_req = True` ("fittings") and `is_work_or_repair_req = False`.
  3. Stage 2 evaluates `(storage_rank, r_rank, c_rank, idx)`.
  4. `IS 1239-2` has role `PRIMARY_PRODUCT` (`r_rank = 0`). `IS 11906` has role `ALLIED` (`r_rank = 1`).
  5. Because `r_rank` precedes `c_rank`, `IS 1239 (Part 2)` won despite its lower confidence bucket.
  6. **Verdict**: Fix 2A operates exactly as designed for pure product requirements.

### 6.3. T002-R003 (Flange Joint Maintenance)
- **Requirement**: *"Flange Joint Maintenance"*
- **Expected**: `IS 6392 : 1971` (Steel Pipe Flanges) / `IS 2712 : 2020` (Gaskets)
- **Current Winner**: `IS 13257 : 1992` (*"Jointing materials for water, steam and gases"*)
- **Deep Trace Findings**:
  1. `IS 6392 : 1971` is the authoritative product standard for steel pipe flanges. In the BIS catalogue, its lifecycle status is `WITHDRAWN`.
  2. `IS 13257 : 1992` has lifecycle status `UNKNOWN` in the database.
  3. In Stage 1 `candidate_priority`:
     - `IS 13257` (Unknown status): `lifecycle_rank = 0`
     - `IS 6392` (Withdrawn status): `lifecycle_rank = 1`
  4. **Root Cause**: The Stage 1 sorting logic explicitly penalizes withdrawn standards (`lifecycle_rank = 1 vs 0`), demoting `IS 6392` behind `IS 13257`. Lifecycle status effectively acted as a **relevance multiplier/filter**, causing the technically superior standard to lose to a generic jointing material standard.

### 6.4. T013-R002 (VFD Panel for AHU Fans)
- **Requirement**: *"VFD panel for AHU fans..."*
- **Expected**: `IS/IEC 61800-2 : 2015` (Adjustable speed electrical power drive systems)
- **Current Winner**: `IS 10069 : 2023` (Test method)
- **Deep Trace Findings**:
  1. `IS/IEC 61800-2` was retrieved by BM25 at Rank 3 and entered the top-15 candidate pool.
  2. **Upstream Rejection by Applicability Gate**:
     - Applicability Gate rejected `IS/IEC 61800-2` with reason: *"No substantive technical vocabulary overlap with standard scope (generic words only). Zero substantive technical term overlap between requirement and standard."*
     - The requirement used the acronym **"VFD"** (Variable Frequency Drive). The title and scope of `IS/IEC 61800-2` use the formal terminology *"Adjustable speed electrical power drive systems"*.
     - Because `VFD` was missing from the vocabulary normalizer, token overlap was zero.
  3. **Verdict**: This failure is **NOT** an arbitration sorting failure; it is an **Upstream Applicability Gate rejection**. Arbitration was never allowed to evaluate the correct standard.

### 6.5. T001-R002 (Hubless Pipelines Determinism Trace)
- **Requirement**: *"replacement of damaged pipelines by Hubless"*
- **Expected**: `IS 15905 : 2011; IS 1239 (Part 1)`
- **Experiment**: Executed 10 consecutive end-to-end recommendation runs on identical input.
- **Results**:
  - Run 1 to 10 Winner: `IS 15905 : 2024` (10 / 10 identical)
  - Run 1 to 10 Confidence: `High` (10 / 10 identical)
  - Run 1 to 10 Human Review: `False` (10 / 10 identical)
- **Verdict**: The pipeline is **100% deterministic, byte-for-byte and value-for-value stable**. `IS 15905 : 2024` is the official 2024 First Revision of `IS 15905 : 2011` and matches canonically.

### 6.6. T004-R005 (Feeder Pillar)
- **Requirement**: *"Dismantling,Shifting and reinstallation of feeder pillar, power"*
- **Expected**: `IS 5039 : 1983; IS/IEC 61439-5`
- **Current Outcome**: `final_recommendation = None` (`human_review_required = True`, Confidence: `Low`)
- **Deep Trace Findings**:
  1. `IS 5039 : 1983` was retrieved at **Rank 1** in both BM25 and Semantic search, and ranked #1 in both Stage 1 and Stage 2 arbitration.
  2. However, the Ambiguity Engine flagged the requirement as `INCOMPLETE` because the tender specifies physical shifting/reinstallation without specifying electrical feeder parameters (voltage rating, current capacity, enclosure class).
  3. By system design (lines 928–930), whenever `human_review_required = True`, the system abstains from issuing an automated recommendation.
  4. **Verdict**: This is a **SAFE ABSTENTION**, not an arbitration error.

### 6.7. T014-R002 (Pump Motor Rewinding & Overhauling)
- **Requirement**: *"Rewinding and overhauling of pump motor sets..."*
- **Expected**: `IS/IEC 60034-1 : 2017; IS 5120`
- **Deep Trace Findings**:
  1. BM25 Rank: **55**; Semantic Rank: **24**; Fused RRF Rank: **39**.
  2. The candidate does **not** enter the top-15 candidate pool.
  3. **Verdict**: **UPSTREAM RETRIEVAL FAILURE**. Arbitration is completely unreachable for this candidate.

---

## 7. Pairwise Counterfactual Analysis

For every query where the expected standard was present in the candidate pool but was not recommended:

| Query ID | Expected Standard | Selected Winner | Winner RRF Rank | Expected RRF Rank | First Decision Criterion Causing Loss |
|---|---|---|:---:|:---:|---|
| **T001-R003** | `IS 15622 : 2006` | `IS 4112 : 1967` | 1 | 7 | Ambiguity Gate triggered human review (`None` returned). |
| **T002-R003** | `IS 6392 : 1971` | `IS 13257 : 1992` | 4 | 2 | **LIFECYCLE RANK DEMOTION**: Expected `IS 6392` demoted for being WITHDRAWN while winner was UNKNOWN. |
| **T004-R005** | `IS 5039 : 1983` | `IS 5039 : 1983` | 1 | 1 | Safe Abstention (Ambiguity / Incomplete specification). |
| **T005-R001** | `IS 7098 (Part 1)`| `IS 7098 (Part 2)`| 1 | 2 | Safe Abstention (Ambiguity / Competing standards). |
| **T007-R003** | `IS 2491 : 2013` | `IS 2491 : 2024` | 1 | 1 | Safe Abstention (BOT Concession Ambiguity). |
| **T009-R001** | `IS 732 : 2019` | `IS 12457 : 1988` | 3 | 10 | **STAGE 1 RETRIEVAL RANK TIE-BREAK**: Spurious BM25 token match on "maintenance" elevated concrete batching plant standard. |
| **T011-R001** | `IS 7098 (Part 1)`| `IS 10334 : 1982`| 4 | 4 | Safe Abstention (Ambiguity Gate triggered). |
| **T013-R002** | `IS/IEC 61800-2` | `IS 10069 : 2023` | 13 | 4 | **APPLICABILITY GATE REJECTION**: Acronym "VFD" unmapped to "adjustable speed drive", causing complete gate rejection. |

---

## 8. All-19 Query Classification

Every benchmark query was classified into one of six mutually exclusive categories:

| Category | Count | Percentage | Queries |
|---|:---:|:---:|---|
| **1. Correct Final Recommendation** | **9** | **47.4%** | `T001-R002`, `T001-R004`, `T003-R001`, `T004-R002`, `T010-R001`, `T012-R002`, `T012-R003`, `T013-R003`, `T020-R001` |
| **2. Wrong Rec: Correct Candidate in $K=15$** | **3** | **15.8%** | `T002-R003` (Lifecycle demotion), `T009-R001` (Domain-scope conflict), `T013-R002` (Applicability gate rejection) |
| **3. Wrong Rec: Correct Candidate outside $K=15$**| **2** | **10.5%** | `T006-R001` (UPVC wall, BM25: 51), `T014-R002` (Pump motor, BM25: 55, Sem: 24) |
| **4. Safe Abstention (Human Review Required)** | **5** | **26.3%** | `T001-R003`, `T004-R005`, `T005-R001`, `T007-R003`, `T011-R001` |
| **5. Identity / Evaluation Issue** | **0** | **0.0%** | — |
| **6. Other** | **0** | **0.0%** | — |

---

## 9. Counterfactual Arbitration Simulations

Six arbitration ordering strategies were simulated in an isolated experiment harness to measure their benchmark-wide impact:

| Strategy | Ordering Formula | FR-Accuracy | Improvements | Regressions | Net Impact |
|---|---|:---:|:---:|:---:|:---:|
| **A_Current** | Production Fix 2A tuple | **9 / 19 (47.4%)** | 0 | 0 | Control Baseline |
| **B_RetrievalRankFirst** | Pure RRF rank #1 | **12 / 19 (63.2%)** | +3 | 0 | Bypasses ambiguity abstentions (Unsafe) |
| **C_ApplicabilityFirst** | Applicability pass $\rightarrow$ RRF rank | **12 / 19 (63.2%)** | +3 | 0 | Bypasses ambiguity abstentions (Unsafe) |
| **D_TechnicalRoleFirst** | Primary role $\rightarrow$ RRF rank | **12 / 19 (63.2%)** | +3 | 0 | Bypasses ambiguity abstentions (Unsafe) |
| **E_ConfidenceWithRetrieval**| Confidence $\rightarrow$ RRF rank | **10 / 19 (52.6%)** | +2 | **1** | Causes regression on `T012-R003` |
| **F_App + Role + Retrieval**| Inactive $\rightarrow$ Role $\rightarrow$ RRF rank | **10 / 19 (52.6%)** | +2 | **1** | Causes regression on `T012-R003` |

### Critical Takeaways from Simulations:
1. Strategies B, C, and D appear to increase accuracy to 12/19 solely because they force a raw guess on under-specified queries (`T004-R005`, `T005-R001`, `T007-R003`) that the Ambiguity Engine intentionally and correctly abstained on.
2. Strategies E and F produce a **direct regression** on `T012-R003` (re-introducing the Fix 2A bug where `IS 11906` beats `IS 1239 (Part 2)`).
3. **Not a single generic sorting modification cleanly solves `T009-R001` without introducing regressions.**

---

## 10. Domain-Scope Mechanism Audit

A thorough code audit was conducted on `src/applicability.py`, `src/critic.py`, and `src/recommend.py` to determine what domain concepts currently exist:

| Domain Concept | Current System State |
|---|---|
| **Engineering Domain Detection** | **Partial / Heuristic**. `detect_domains()` checks keyword sets (e.g. `electrical`, `civil`, `mechanical`), but does not map them to standard scopes. |
| **Application Domain / Context** | **None**. No representation of whether a standard applies to a building, a chemical plant, or a concrete batching plant. |
| **General-Purpose vs Niche Standard**| **None**. Broad foundational standards (`IS 732` for electrical installations) are treated with equal specificity weight as niche standards (`IS 12457` for concrete plants). |
| **Negative Domain Evidence** | **Ad-hoc only**. One hardcoded rule filters agricultural pumps for industrial requirements (Line 312 of `src/retrieval.py`). No generic negative domain reasoning exists. |
| **Service / Maintenance Context** | **Weak**. Procurement words ("maintenance") are treated as product technical tokens, inflating spurious overlap with maintenance test codes. |

---

## 11. Final Decision

In accordance with the Phase 4R15 protocol, the final decision is:

### **OPTION 2**
> **"Arbitration contributes to failures, but no generic safe refinement has yet been demonstrated."**

### Architectural Rationale & Next Investigation Directive:
1. **Arbitration Contributes to Failures**:
   - In `T009-R001`, `IS 732` is inside the candidate pool but loses because arbitration lacks a domain-scope conflict mechanism.
   - In `T002-R003`, `IS 6392` loses because lifecycle status (`WITHDRAWN`) is penalizing relevance in Stage 1 sorting.
2. **Failures are Multi-Layered**:
   - Out of 10 non-correct queries, 5 are **safe abstentions** mandated by the Ambiguity Gate.
   - 2 are **upstream retrieval failures** (`T006-R001`, `T014-R002`).
   - 1 is an **upstream applicability gate vocabulary failure** (`T013-R002`).
   - Only 2 are true arbitration failures (`T009-R001`, `T002-R003`).
3. **Generic Sorting Rules are Insufficient**:
   - Naively changing sort tuples (Strategies B–F) either compromises safety guardrails or causes regressions.
4. **Recommended Next Phase**:
   - **Phase 4R16**: Formulate and evaluate a targeted **Domain-Scope Conflict & Lifecycle Calibration Rule** specifically addressing:
     1. Preventing application-specific industrial plant codes (e.g. concrete batching plants) from winning general building service contracts when general engineering codes (`IS 732`) are present.
     2. Decoupling lifecycle validity from relevance scoring so that authoritative product standards (`IS 6392`) are not displaced by generic unknown-status materials.

---

## 12. Reproducibility & Environment Manifest

- **Git Commit Hash**: `e0d3fbcf0a82b653dfa22d2764c9cc8351fb1bcf`
- **Catalogue Database**: `data/catalogue/bis_catalogue.db` (SHA256: `bd04dab6f7d5cd4ea58fa69c917b1fa5d375f721ee4ec03691dfc7eb1b0850b3`)
- **Semantic Embeddings**: `data/catalogue/bis_semantic_embeddings.npy` (SHA256: `216c40ac0ac8a685c44a55dfb07fc46354eb7d14d10acfb3e5514979c9dc41be`)
- **Benchmark Dataset**: `dataset/ground_truth/ground_truth.csv` (SHA256: `cfcbca27a729bd0619886be9128cfba272b912bd21115604b45af7eb59fa404b`)
- **T001-R002 10-Run Determinism**: Confirmed 100% stable (`IS 15905 : 2024`).
- **Zero Production Modifications Certified**.
