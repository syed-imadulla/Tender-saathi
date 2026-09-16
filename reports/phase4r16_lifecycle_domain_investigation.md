# Phase 4R16 — Lifecycle Calibration + Domain-Scope Conflict Investigation

**Investigation Status**: COMPLETED (Investigation Only — Zero Production Changes)  
**Date**: September 2026  
**Scope**: Deep Diagnostic Traces for T002-R003 (Lifecycle Calibration) and T009-R001 (Domain-Scope Conflict), 5 Isolated Lifecycle Simulations, 8 Isolated Domain/Context Simulations, Full Multi-Depth Retrieval Metrics, and Safety Audits across the Frozen 19-Query Benchmark  
**Raw Data Artifact**: [`reports/phase4r16_lifecycle_domain_investigation_data.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/reports/phase4r16_lifecycle_domain_investigation_data.json)  
**Experiment Script**: [`scratch/phase4r16_lifecycle_domain_investigation.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/scratch/phase4r16_lifecycle_domain_investigation.py)

---

## 1. Executive Summary & Objective

Phase 4R15 established that out of 10 non-correct benchmark queries:
- 5 queries are **safe, intentional abstentions** mandated by the Ambiguity Gate (`T001-R003`, `T004-R005`, `T005-R001`, `T007-R003`, `T011-R001`).
- 2 queries are **upstream retrieval failures** (`T006-R001`, `T014-R002`).
- 1 query is an **applicability gate technical vocabulary omission** (`T013-R002` where "VFD" is not mapped).
- Exactly 2 queries represent downstream arbitration anomalies:
  1. **`T002-R003`**: Lifecycle status demoting authoritative product standards (`IS 6392`).
  2. **`T009-R001`**: Lexically matched niche industrial standards (`IS 12457` / `IS 4051`) displacing broad foundational standards (`IS 732` / `SP 30`).

Phase 4R16 investigated whether:
1. Lifecycle status can be safely decoupled from relevance ranking without compromising user safety.
2. A generic engineering domain-scope conflict mechanism can be derived to prevent niche process standards from displacing foundational building/electrical standards.

### Strict Protocol Constraints
- **ZERO production code modifications**.
- All retrieval models (all-MiniLM-L6-v2, Okapi BM25, RRF $k=60$, $K=15$), database records, terminology maps, and decision logic remained frozen.
- All metrics recomputed directly against [`dataset/ground_truth/ground_truth.csv`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/dataset/ground_truth/ground_truth.csv) using canonical `StandardIdentifierNormalizer` matching.

---

## 2. Frozen Production Baseline Benchmark Audit ($N = 19$)

Evaluating the frozen production pipeline yields:

```
====================================================================================================
FROZEN PRODUCTION BENCHMARK AUDIT (N = 19 Evaluated Queries)
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
T009-R001  WRONG       IS 4051 : 2025                        SP 30 : 2023; IS 732 : 2019
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

### Retrieval Depth Metrics across Benchmark ($N = 19$)
- **Hit@1**: 11 / 19 (57.9%)
- **Recall@15**: 17 / 19 (89.5%)
- **Recall@30**: 17 / 19 (89.5%)
- **Recall@50**: 18 / 19 (94.7%) *(Recovers T006-R001)*
- **Recall@100**: 18 / 19 (94.7%)
- **Mean Reciprocal Rank (MRR)**: 0.6496

---

## 3. Part A — Lifecycle Calibration Deep Trace & Simulations

### 3.1. Deep Trace: `T002-R003` (Flange Joint Maintenance)
- **Requirement**: *"Flange Joint Maintenance"*
- **Expected**: `IS 6392 : 1971` (Specification for steel pipe flanges) / `IS 2712 : 2020` (Gaskets)
- **Current Winner**: `IS 13257 : 1992` (*"Ring type joint gaskets and grooves for pipe flanges - Specification"*)

#### Complete $K=15$ Candidate Pool Audit for `T002-R003`:
| RRF Rank | Standard Number | Status | Title | Role | App Decision | Conf | Stage 1 Tuple | Stage 2 Tuple | Exp? |
|:---:|---|---|---|---|:---:|:---:|:---:|:---:|:---:|
| 1 | **IS 13257 : 1992** | UNKNOWN | Ring type joint gaskets and grooves for pipe flanges | PRIMARY_PRODUCT | APPLICABLE | High | `(0, -1, 0)` | `(0, 0, 1, 0)` | No |
| 2 | **IS 6392 : 1971** | WITHDRAWN | Specification for steel pipe flanges | PRIMARY_PRODUCT | APPLICABLE | Medium | `(1, -1, 1)` | `(0, 1, 1, 5)` | **Yes** |
| 3 | **IS 10864 : 2013** | WITHDRAWN | Metal jacketed gaskets for pipe flanges | PRIMARY_PRODUCT | APPLICABLE | Medium | `(1, -1, 2)` | `(0, 1, 1, 6)` | No |
| 4 | **IS 10864 : 2024** | UNKNOWN | Metal jacketed gaskets for pipe flanges | PRIMARY_PRODUCT | APPLICABLE | Medium | `(0, -1, 3)` | `(0, 1, 1, 1)` | No |
| 5 | **IS 3516 : 1966** | UNKNOWN | Cast iron pipe flanges and flanged fittings | PRIMARY_PRODUCT | APPLICABLE | Medium | `(0, -1, 4)` | `(0, 1, 1, 2)` | No |
| 6 | **IS 13159 (Part 1) : 1993** | WITHDRAWN | Pipe flanges and flanged fittings | PRIMARY_PRODUCT | APPLICABLE | Low | `(1, -1, 5)` | `(0, 2, 1, 7)` | No |
| 7 | **IS 13159 (Part 1) : 2026** | UNKNOWN | Pipe Flanges and Flanged Fittings — Code of Practice | PRIMARY_PRODUCT | APPLICABLE | Low | `(0, -1, 6)` | `(0, 2, 1, 3)` | No |
| 8 | **IS 4866 : 1968** | WITHDRAWN | Welded shell flanges for carbon steel pressure vessels | PRIMARY_PRODUCT | APPLICABLE | Medium | `(1, 0, 7)` | `(0, 1, 1, 8)` | No |
| 9 | **IS 4868 : 1968** | WITHDRAWN | Welded shell flanges for stainless steel pressure vessels| PRIMARY_PRODUCT | APPLICABLE | Medium | `(1, 0, 8)` | `(0, 1, 1, 9)` | No |
| 10 | **IS 6392 : 2020** | ACTIVE | Steel Pipes Flanges — Specification (First Revision) | PRIMARY_PRODUCT | APPLICABLE | Medium | `(0, 0, 9)` | `(0, 1, 1, 4)` | **Yes** |
| 11 | **IS 4867 : 1968** | WITHDRAWN | Welded neck shell flanges for carbon steel | PRIMARY_PRODUCT | APPLICABLE | Low | `(1, 0, 10)`| `(0, 2, 1, 10)`| No |
| 12 | **IS 4869 : 1968** | WITHDRAWN | Welded shell flanges with hub for stainless steel | PRIMARY_PRODUCT | APPLICABLE | Low | `(1, 0, 11)`| `(0, 2, 1, 11)`| No |
| 13 | **IS 425 : 1953** | WITHDRAWN | Shellac adhesive for steam flange joints | PRIMARY_PRODUCT | APPLICABLE | Medium | `(1, 0, 12)`| `(0, 1, 1, 12)`| No |
| 14 | **IS 10738 (Part 1) : 1983** | WITHDRAWN | Specification for flanges for waveguides | PRIMARY_PRODUCT | APPLICABLE | Medium | `(1, 0, 13)`| `(0, 1, 1, 13)`| No |
| 15 | **IS 10738 (Part 3) : 1991** | WITHDRAWN | Specification for flanges for waveguides | PRIMARY_PRODUCT | APPLICABLE | Medium | `(1, 0, 14)`| `(0, 1, 1, 14)`| No |

#### Diagnostic Findings on `T002-R003`:
1. **The Compounding Failure**:
   - `IS 13257 : 1992` was retrieved at **RRF Rank 1** (BM25 score 1.0, relevance score 0.9477).
   - `IS 6392 : 1971` was retrieved at **RRF Rank 2** (BM25 score 0.9472, relevance score 0.7987).
   - `IS 13257` earned Confidence `High` because its relevance score was 0.9477 with strong lexical grounding, while `IS 6392` earned Confidence `Medium` (score 0.7987).
   - In Stage 1 sorting, `IS 13257` had `lifecycle_status = UNKNOWN`, mapping to `lifecycle_rank = 0`.
   - `IS 6392 : 1971` had `lifecycle_status = WITHDRAWN`, mapping to `lifecycle_rank = 1`.
2. **The Counterfactual Surprise**:
   - If lifecycle ranking is **completely ignored** (setting `lifecycle_rank = 0` for all candidates), `IS 6392 : 1971` **STILL DOES NOT WIN**.
   - Under `lifecycle_rank = 0`, both `IS 13257` and `IS 6392` have identical Stage 1 role priority (`-1`).
   - In Stage 1, `IS 13257` beats `IS 6392` because `orig_rank = 0` vs `orig_rank = 1`.
   - In Stage 2, `IS 13257` has Confidence `High` (`c_rank = 0`) while `IS 6392` has Confidence `Medium` (`c_rank = 1`). Under the general works/maintenance branch (`is_work_or_repair_req = True`), Stage 2 sorts by `(storage_rank, c_rank, r_rank, idx)`.
   - Therefore, `IS 13257` wins on **both retrieval rank AND confidence**!
3. **Conclusion on Lifecycle as a Decisive Factor**:
   - While demoting withdrawn standards in Stage 1 is conceptually problematic, **lifecycle demotion is NOT the sole reason `IS 6392` lost**. `IS 13257` outranks `IS 6392` upstream in retrieval ($0.9477$ vs $0.7987$) and in downstream confidence ($High$ vs $Medium$).

### 3.2. Cross-Benchmark Lifecycle Simulations

Five isolated counterfactual simulations were executed across the entire benchmark:

| Simulation Strategy | Stage 1 Lifecycle Rule | FR-Accuracy | Improvements | Regressions | Analysis |
|---|---|:---:|:---:|:---:|---|
| **A_Current** | Active/Unknown = 0, Withdrawn/Superseded = 1 | **9 / 19 (47.4%)** | Baseline | Baseline | Production baseline |
| **B_Ignore_Lifecycle_Ranking** | All standards = 0 (Lifecycle ignored in ranking) | **9 / 19 (47.4%)** | 0 | 0 | Net zero change across all 19 queries |
| **C_Lifecycle_Warning_Only** | All standards = 0 + Warning retained in output | **9 / 19 (47.4%)** | 0 | 0 | Net zero change across all 19 queries |
| **D_Explicit_Citation_Preserved** | Cited standards preserved; un-cited = 0 | **9 / 19 (47.4%)** | 0 | 0 | Net zero change across all 19 queries |
| **E_Unknown_Separated** | Active = 0, Unknown = 1, Withdrawn = 2 | **6 / 19 (31.6%)** | 0 | **3** | **Severe Regression** (`T004-R002`, `T012-R003`, `T020-R001`) |

#### Critical Findings from Lifecycle Simulations:
1. **Strategies B, C, and D produce ZERO changes across the 19 benchmark queries**:
   - In every case where an inactive standard is in the candidate pool, either an active/unknown replacement standard is already ranked higher by retrieval/confidence (`T001-R002`, `T010-R001`), or the query is safely abstained (`T004-R005`, `T007-R003`).
   - In `T002-R003`, `IS 13257` beats `IS 6392` on retrieval score and confidence regardless of lifecycle status.
2. **Strategy E is Catastrophic**:
   - Penalizing `UNKNOWN` status causes 3 correct recommendations (`T004-R002` IS 1255, `T012-R003` IS 1239-2, `T020-R001` IS 15778) to regress because official BIS catalogue records ingested without explicit `is_active=1` flags are labeled `UNKNOWN` by the database validator.

---

## 4. Part B — Domain-Scope Conflict Deep Trace & Simulations

### 4.1. Deep Trace: `T009-R001` (Electrical & Mechanical AMC)
- **Requirement**: *"Annual Repairs and Maintenance Contract for electrical and mechanical services alongwith requisite materials at FSD"*
- **Expected**: `SP 30 : 2023` / `IS 732 : 2019`
- **Current Winner**: `IS 4051 : 2025` (*"Installation and Maintenance of Electrical Equipment in Mines - Code of Practice"*) / `IS 12457 : 1988` (*"Code of practice for evaluation, repairs and acceptance limits of surface defects in steel plates and wide flats"*)

#### Complete $K=15$ Candidate Pool Audit for `T009-R001`:
| Rank | Standard Number | TC | Aspect | Title | App Decision | Role | Conf | Exp? |
|:---:|---|---|---|---|:---:|:---:|:---:|:---:|
| 1 | **IS 19529 : 2026** | SSD 22 | None | MAINTENANCE AND REPAIR SERVICES REQUIREMENTS | NOT_APPLICABLE | PRIMARY_PRODUCT | High | No |
| 2 | **IS 4051 : 1967** | ETD 22 | Code of Practice | Installation and maintenance of electrical equipment in mines | APPLICABLE | INSTALLATION | Medium | No |
| 3 | **IS 12457 : 1988** | MTD 04 | Code of Practice | Repairs and acceptance limits of surface defects in steel plates | APPLICABLE | CODE_OF_PRACTICE | Medium | No |
| 4 | **IS 4051 : 2025** | ETD 22 | Code of Practice | Installation and Maintenance of Electrical Equipment in Mines | APPLICABLE | INSTALLATION | Medium | No |
| 5 | **IS 13040 : 1991** | PGD 34 | Product Spec | Dolly blocks for use in steel body repairs | APPLICABLE | PRIMARY_PRODUCT | Medium | No |
| 6 | **IS 7733 : 1975** | ETD 20 | None | Electrical wiring installations in hospitals | APPLICABLE | INSTALLATION | Medium | No |
| 7 | **IS/IEC 60079-17 : 2023** | ETD 22 | Code of Practice | Explosive atmospheres: Electrical installations inspection | APPLICABLE | PRIMARY_PRODUCT | Medium | No |
| 8 | **IS 1866 : 2017** | ETD 03 | Code of Practice | Mineral insulating oils in electrical equipment maintenance | APPLICABLE | PRIMARY_PRODUCT | Medium | No |
| 9 | **IS 13408 (Part 1) : 1992** | ETD 22 | None | Electrical apparatus for use in explosive atmospheres | APPLICABLE | INSTALLATION | Medium | No |
| 10 | **IS 732 : 2019** | ETD 20 | Code of Practice | Code of practice for electrical wiring installations | APPLICABLE | INSTALLATION | Medium | **Yes** |
| 11 | **IS 10028 (Part 3) : 1981** | ETD 16 | Code of Practice | Selection, installation and maintenance of transformers | NOT_APPLICABLE | INSTALLATION | Low | No |
| 12 | **IS/IEC 60079-17 : 2013** | ETD 22 | Code of Practice | Explosive atmospheres: Electrical installations inspection | APPLICABLE | PRIMARY_PRODUCT | Medium | No |
| 13 | **IS 13450 (Part 1) : 2024** | MHD 15 | Others | Medical electrical equipment | APPLICABLE | PRIMARY_PRODUCT | Medium | No |
| 14 | **IS 12309 (Part 2) : 1988** | ETD 49 | Code of Practice | Installation and maintenance of aerodrome lighting fittings | NOT_APPLICABLE | INSTALLATION | Low | No |
| 15 | **IS 10386 (Part 5) : 2014** | WRD 21 | Code of Practice | Safety code for river valley projects: electrical aspects | APPLICABLE | SAFETY | Medium | No |

#### Why Wrong Candidates Win over `IS 732`:
1. **The Upstream Retrieval Disadvantage**:
   - `IS 732 : 2019` entered the candidate pool at **Rank 10** (BM25 Rank 4, Semantic Rank >150).
   - `IS 4051 : 1967` entered at **Rank 2** (BM25 Rank 1).
   - `IS 12457 : 1988` entered at **Rank 3** (BM25 Rank 2).
   - `IS 4051 : 2025` was promoted via Step 2.5 active successor injection to **Rank 4**.
2. **Applicability Gate Leakage**:
   - `IS 12457` (MTD 04 - Metallurgical plate repairs) passed the gate because it matched the single procedural word *"repairs"*.
   - `IS 4051` (ETD 22 - Mines electrical maintenance) passed the gate because it matched *"electrical"*, *"installation"*, and *"maintenance"*.
   - The Applicability Gate possesses no model of **facility context** (e.g. distinguishing a general building / food storage depot `FSD` from an underground mine or a metallurgical rolling mill).
3. **Downstream Arbitration Ordering**:
   - In Step 2.5 successor injection, `IS 4051 : 2025` is injected to supersede `IS 4051 : 1967`, receiving its high retrieval rank (`final_score = 0.6116`).
   - In Stage 1 sorting, `IS 4051 : 2025`, `IS 12457 : 1988`, and `IS 732 : 2019` all receive identical role priority (`role_rank = 0`, `lifecycle_rank = 0`).
   - In Stage 2, all three have Confidence `Medium`.
   - The tie is broken strictly by **initial retrieval order**: `IS 4051 : 2025` (idx 1) outranks `IS 12457` (idx 2), which outranks `IS 732` (idx 8).

### 4.2. Isolated Domain & Scope Simulations

Eight isolated domain-scope arbitration strategies were evaluated across the frozen benchmark:

| Sim # | Strategy Description | FR-Accuracy | Improvements | Regressions | Analysis |
|:---:|---|:---:|:---:|:---:|---|
| **1** | Current Arbitration Baseline | **9 / 19 (47.4%)** | Baseline | Baseline | Production baseline |
| **2** | Pure Retrieval Rank + Applicability | **9 / 19 (47.4%)** | 0 | 0 | Ineffective (IS 4051 remains #1) |
| **3** | Technical Role Priority across all queries | **9 / 19 (47.4%)** | 0 | 0 | All top candidates share primary role |
| **4** | Domain Compatibility Bonus (ETD bonus) | **9 / 19 (47.4%)** | 0 | 0 | Both IS 4051 and IS 732 are ETD |
| **5** | Domain Conflict Penalty (MTD penalty) | **9 / 19 (47.4%)** | 0 | 0 | Penalizes IS 12457, but IS 4051 wins |
| **6** | Domain Compat + Role + Retrieval | **9 / 19 (47.4%)** | 0 | 0 | IS 4051 still outranks IS 732 |
| **7** | Strong Negative Conflict Gate (MTD gate) | **9 / 19 (47.4%)** | 0 | 0 | Filters IS 12457; IS 4051 wins |
| **8** | Combined Lifecycle & Domain Calibration | **9 / 19 (47.4%)** | 0 | 0 | IS 4051 : 1967 wins |

#### Critical Discovery on Domain-Scope Arbitration:
Even when heavy metallurgical standards (`IS 12457`, MTD 04) are successfully eliminated by domain filtering, **`IS 732 : 2019` DOES NOT WIN**.  
Instead, **`IS 4051 : 2025`** (*"Electrical Equipment in Mines"*) wins because:
1. `IS 4051` belongs to the exact same authoritative Technical Committee domain (**ETD** — Electrotechnical).
2. `IS 4051` has substantive technical keyword overlap with the tender (*"electrical"*, *"installation"*, *"maintenance"*).
3. `IS 4051` has a significantly higher lexical BM25 retrieval rank (Rank 1 vs Rank 4) than `IS 732` (Rank 10 raw RRF).
4. `IS 732` cannot overtake `IS 4051` through arbitration without an explicit rule stating *"general building wiring beats specialized mining installation codes"*.
5. Introducing a rule that "broad standards always beat niche standards" would severely damage other benchmark queries (e.g. `T012-R003` where specific pipe fittings `IS 1239-2` must beat broad steel codes).

---

## 5. Part C & D — Cross-Benchmark Validation & Safety Checks

### 5.1. Metric Summary Table ($N = 19$)
| Strategy | Final Rec Accuracy | Hit@1 | Recall@15 | Safe Abstentions | Wrong Recs | Regressions |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Frozen Production Baseline** | **9 / 19 (47.4%)** | **11 / 19** | **17 / 19** | **5 / 19** | **5 / 19** | **0** |
| **Sim B (Ignore Lifecycle Rank)**| **9 / 19 (47.4%)** | 11 / 19 | 17 / 19 | 5 / 19 | 5 / 19 | 0 |
| **Sim C (Lifecycle Warning Only)**| **9 / 19 (47.4%)** | 11 / 19 | 17 / 19 | 5 / 19 | 5 / 19 | 0 |
| **Sim E (Penalize Unknown Status)**| **6 / 19 (31.6%)** | 11 / 19 | 17 / 19 | 5 / 19 | 8 / 19 | **3** |
| **Sim 5 (Domain Conflict Penalty)**| **9 / 19 (47.4%)** | 11 / 19 | 17 / 19 | 5 / 19 | 5 / 19 | 0 |
| **Sim 7 (Negative Domain Gate)** | **9 / 19 (47.4%)** | 11 / 19 | 17 / 19 | 5 / 19 | 5 / 19 | 0 |
| **Sim 8 (Combined Calibration)** | **9 / 19 (47.4%)** | 11 / 19 | 17 / 19 | 5 / 19 | 5 / 19 | 0 |

### 5.2. Safety Check Verification
1. **Did any simulation override an intentional ambiguity abstention?**  
   **NO**. Across all tested simulations, the 5 safe abstentions (`T001-R003`, `T004-R005`, `T005-R001`, `T007-R003`, `T011-R001`) remained strictly protected.
2. **Did any simulation make an unverified UNKNOWN standard appear authoritative?**  
   In `T002-R003`, `IS 13257 : 1992` (UNKNOWN) continues to outrank `IS 6392` across all safe simulations because its upstream retrieval score is higher ($0.9477$ vs $0.7987$).
3. **Did any simulation hide withdrawn/superseded status?**  
   **NO**. In all simulations, validation metadata and warnings were preserved.
4. **Did any simulation regress previously correct recommendations?**  
   Simulations B, C, D, 1, 2, 3, 4, 5, 6, 7, and 8 had **0 regressions**. Simulation E had **3 regressions**.

---

## 6. Root-Cause Synthesis: Why Downstream Arbitration Cannot Alone Fix the Remaining Queries

The Phase 4R16 investigation reveals a fundamental structural insight:

1. **`T002-R003` is NOT blocked by downstream lifecycle ranking**:
   - The authoritative flange standard `IS 6392` has BM25 score $0.9472$ and relevance $0.7987$.
   - The gasket standard `IS 13257` has BM25 score $1.0$ and relevance $0.9477$.
   - Even when lifecycle status is completely neutralized, `IS 13257` wins on raw retrieval score and confidence. Fixing `T002-R003` requires recognizing that a tender specifying *"Flange Joint"* seeks a flange specification rather than a gasket specification, which is a **semantic/entity disambiguation** problem, not a lifecycle arbitration problem.

2. **`T009-R001` is NOT blocked by lack of domain penalty**:
   - When the metallurgical candidate `IS 12457` is penalized, `IS 4051 : 2025` (*Mines Electrical Installation*) wins instead of `IS 732 : 2019` (*Building Wiring*).
   - Both `IS 4051` and `IS 732` belong to the Electrotechnical department (**ETD**).
   - `IS 4051` was retrieved at BM25 Rank 1 because its title contains *"installation and maintenance of electrical equipment"*, exactly mirroring the tender words *"repairs and maintenance contract for electrical and mechanical services"*.
   - `IS 732` was retrieved at BM25 Rank 4 and RRF Rank 10.
   - Downstream arbitration cannot safely penalize `IS 4051` without hardcoding application-specific rules (e.g. penalizing the word "mines" when "mines" is not mentioned in the tender), which violates generalization principles.

3. **The 5 Remaining Failures are Upstream / Semantic / Scope Boundary Failures**:
   - `T006-R001`: Upstream retrieval miss (BM25 Rank 51).
   - `T014-R002`: Upstream retrieval miss (BM25 Rank 55, Semantic Rank 24).
   - `T013-R002`: Upstream Applicability Gate rejection ("VFD" acronym missing from vocabulary).
   - `T002-R003`: Upstream lexical bias toward gaskets over flanges.
   - `T009-R001`: Upstream lexical bias toward specialized equipment maintenance codes over foundational wiring codes.

---

## 7. Final Decision & Recommendation

In accordance with the Phase 4R16 investigation protocol, the final decision is:

### **OPTION 4**
> **"Domain-scope signals are useful diagnostically, but no generic safe production rule is demonstrated."**

### Architectural Rationale:
1. **Lifecycle Calibration Findings**:
   - Decoupling lifecycle status from Stage 1 ranking (Strategy B/C) causes **0 regressions**, but also **0 improvements** on the benchmark.
   - Penalizing UNKNOWN status (Strategy E) causes **3 severe regressions**.
   - Lifecycle calibration alone does not fix `T002-R003`.
2. **Domain-Scope Conflict Findings**:
   - Filtering cross-domain standards (e.g. MTD metallurgy in electrical tenders) successfully removes `IS 12457`, but simply exposes `IS 4051` (*Mines Electrical Installation*) as the next winner.
   - Within the same engineering domain (ETD), distinguishing general building wiring (`IS 732`) from specialized mining installation (`IS 4051`) cannot be accomplished by generic downstream arbitration without brittle tender-specific heuristics.
3. **Recommended Next Phase**:
   - **Phase 4R17**: Direct attention to the **Upstream Vocabulary & Semantic Boundary Layer**:
     1. **Acronym & Technical Expansion in Applicability Gate**: Resolve unmapped domain acronyms (e.g. *"VFD"* $\rightarrow$ *"adjustable speed electrical power drive systems"* in `T013-R002`), which directly recovers an expected standard already retrieved in $K=15$.
     2. **Entity Head-Noun Weighting**: Investigate whether the requirement decomposer can weight primary physical nouns (e.g. *"flange"* over *"joint/maintenance"* in `T002-R003`) to ensure the primary product outranks auxiliary jointing materials upstream in retrieval.

---

## 8. Reproducibility & Environment Certification

- **Git Commit Hash**: `e0d3fbcf0a82b653dfa22d2764c9cc8351fb1bcf`
- **Catalogue SHA256**: `bd04dab6f7d5cd4ea58fa69c917b1fa5d375f721ee4ec03691dfc7eb1b0850b3`
- **Semantic Embeddings SHA256**: `216c40ac0ac8a685c44a55dfb07fc46354eb7d14d10acfb3e5514979c9dc41be`
- **Benchmark Ground Truth SHA256**: `cfcbca27a729bd0619886be9128cfba272b912bd21115604b45af7eb59fa404b`
- **ZERO production code changes certified**.
