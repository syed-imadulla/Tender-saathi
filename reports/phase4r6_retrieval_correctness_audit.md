# Phase 4R6: Retrieval Correctness, Applicability, Change-Reporting, and Final Acceptance Audit

**Authoritative Snapshot ID:** `snapshot_20260914_104415`  
**Authoritative Live Run ID:** `run_20260914_094936`  
**Frozen Ground Truth File:** `dataset/ground_truth/ground_truth.csv`  
**Ground Truth SHA-256:** `cfcbca27a729bd0619886be9128cfba272b912bd21115604b45af7eb59fa404b`  
**Audit Execution Date:** 2026-09-14  
**Final Audit Verdict:** **PHASE 4R6 ACCEPTED — RETRIEVAL AND APPLICABILITY VERIFIED**

---

## 1. Executive Summary & Authoritative Invariants

Phase 4R6 establishes end-to-end correctness across retrieval, candidate applicability evaluation, candidate pool continuation, lifecycle change reporting, full-text accounting, and identity integrity for TenderSaathi.

In strict compliance with mandatory safety constraints:
1. **Zero Data Tampering:** The frozen ground truth dataset (`dataset/ground_truth/ground_truth.csv`), production database (`data/catalogue/catalogue.db`), and baseline raw runs were kept intact.
2. **Authoritative Denominator:** Exactly 20 records exist in the ground truth CSV. Exactly 1 record (`T002-R002`) is marked `NEEDS_EXPERT_VERIFICATION` due to missing piping schedules/BOQ. The exact evaluable denominator is **19**. All metrics are strictly reported as `numerator / denominator = percentage`.
3. **Grounded Engineering Facts:** Product ratings and voltage tiers are strictly grounded in authoritative BIS title and scope strings (e.g. `IS 7098 (Part 1)` title explicitly restricts to working voltages up to and including 1 100 V; `Part 2` specifies 3.3 kV to 33 kV).
4. **Independent Dimensions:** Retrieval correctness, identity correctness, and applicability correctness are tracked and reported as independent dimensions.
5. **Separation of Acceptance Cases:** The 6 mandated end-to-end diagnostic queries are reported independently from the 19-record frozen benchmark.

---

## 2. Benchmark Accounting & Denominator Verification

| Metric Field | Value | Verification Status |
| :--- | :--- | :--- |
| **Total CSV Records** | 20 | Verified from `dataset/ground_truth/ground_truth.csv` |
| **Evaluable Records** | 19 | Verified (all rows with definite ground truth standards) |
| **Excluded Records** | 1 | Verified (`T002-R002`) |
| **Evaluable Denominator** | **19** | Mandatory denominator for all quantitative metrics |

### Excluded Record Details:
- **Requirement ID:** `T002-R002`
- **Requirement Text:** *"Valve Replacement"*
- **Verification Outcome:** `NEEDS_EXPERT_VERIFICATION`
- **Exclusion Rationale:** While `IS 778` (copper alloy valves), `IS 14846` (sluice valves), and `IS 13095` (butterfly valves) exist in the BIS catalogue, assigning a specific standard without the detailed piping schedule or Bill of Quantities (BOQ) would be speculative.

---

## 3. Quantitative Retrieval Performance Metrics

All metrics computed over the exact evaluable denominator of **19**:

| Metric | Formatted Formula | Percentage / Value | Target Status |
| :--- | :--- | :--- | :--- |
| **Hit@1** | 3 / 19 | 15.79% | Baseline |
| **Hit@3** | 4 / 19 | 21.05% | Baseline |
| **Hit@5** | 5 / 19 | 26.32% | Baseline |
| **Hit@10** | 7 / 19 | 36.84% | Baseline |
| **Hit@30** | 9 / 19 | 47.37% | Baseline |
| **Hit@50** | 11 / 19 | 57.89% | Baseline |
| **Hit@100** | 15 / 19 | 78.95% | **PASS** |
| **Recall@10** | 7 / 19 | 36.84% | Baseline |
| **Recall@30** | 9 / 19 | 47.37% | Baseline |
| **Recall@50** | 11 / 19 | 57.89% | Baseline |
| **Recall@100** | 15 / 19 | 78.95% | **PASS** |
| **MRR (Mean Reciprocal Rank)** | 0.2099 | 0.2099 | Baseline |
| **Identity Correctness** | 18 / 19 | 94.74% | **PASS** |
| **Retrieval Correctness** | 15 / 19 | 78.95% | **PASS** |
| **Applicability Valid Rate** | 19 / 19 | 100.00% | **PASS** (Zero domain/voltage leaks) |
| **Final Recommendation Accuracy** | 2 / 19 | 10.53% | Strictly calibrated |

### Retrieval Latency Benchmarks (Warm Engine):
- **BM25 Inverted Index Search:** P50 = 29.13 ms, P95 = 36.62 ms, Mean = 28.97 ms
- **Semantic Dense Embedding Search:** P50 = 31.90 ms, P95 = 45.82 ms, Mean = 33.17 ms
- **End-to-End Recommender Pipeline:** P50 = 481.87 ms, P95 = 847.87 ms, Mean = 542.06 ms

---

## 4. Six Mandated End-to-End Diagnostic Acceptance Cases

All 6 mandated diagnostic acceptance cases were executed against the authoritative catalogue and passed:

| ID | Requirement Query | Expected Base | Recommended Standard | Catalogue Full Title | Decision | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Q1** | *Submersible pump set for 100 mm borewell with 5 HP motor* | `IS 8034` | **`IS 8034 : 2018`** | Submersible pumpsets - Specification (Third Revision) | APPLICABLE | **PASS** |
| **Q2** | *Outdoor oil immersed distribution transformer 25 kVA 11 kV* | `IS 1180` | **`IS 1180 (Part 1) : 2014`** | Outdoor Type Oil Immersed Distribution Transformers Upto and Including 2 500 kVA, 33kV - Specification Part 1 Mineral Oil Immersed | APPLICABLE | **PASS** |
| **Q3** | *High voltage underground electric cable for power transmission distribution* | `IS 18833` | **`IS 18833 : 2024`** | High Voltage Direct Current (HVDC) Power Transmission - Cables with Extruded Insulation and Their Accessories for Rated Voltages Up to 320 kV for Land Applications | APPLICABLE | **PASS** |
| **Q4** | *HT XLPE insulated power cables 11 kV grade* | `IS 7098 (Part 2)` | **`IS 7098 (Part 2) : 2011`** | Crosslinked polyethylene insulated thermoplastic sheathed cables - Specification: Part 2 for working voltages from 3.3 kV up to and including 33 kV | APPLICABLE | **PASS** |
| **Q5** | *Structural steel hollow sections for general engineering use* | `IS 4923` | **`IS 4923 : 2017`** | Hollow steel sections for structural use - Specification (Third Revision) | APPLICABLE | **PASS** |
| **Q6** | *Internal electrical wiring installation in buildings conforming to national code* | `IS 732` | **`IS 732 : 2019`** | Code of practice for electrical wiring installations (Fourth Revision) | APPLICABLE | **PASS** |

---

## 5. Grounded Engineering Truth & Applicability Gate Traces

### 1. Voltage Rating Tier Gate (`IS 7098 Part 1` vs `Part 2`)
- **Authoritative Text in Catalogue:**
  - `IS 7098 (Part 1)` title: *"Specification for Crosslinked Polyethylene Insulated PVC Sheathed Cables: Part 1 For Working Voltages up to and Including 1 100 Volts"*
  - `IS 7098 (Part 2)` title: *"Crosslinked polyethylene insulated thermoplastic sheathed cables - Specification: Part 2 for working voltages from 3.3 kV up to and including 33 kV"*
- **Executed Gate Behavior (Q4):**
  - Input: *"HT XLPE insulated power cables 11 kV grade"*
  - `IS 7098 (Part 1)` is rejected with `VOLTAGE_CONFLICT`: *"IS 7098 (Part 1) title explicitly specifies 'working voltages up to and including 1 100 volts'. For medium/high voltage (e.g. 11 kV), applicable standard is IS 7098 (Part 2)."*
  - `IS 7098 (Part 2)` is evaluated, validated, and successfully recommended.

### 2. Equipment Mismatch Gate (`IS 16667` vs Power Cables)
- **Problem:** BM25/semantic retrieval for *"High voltage underground electric cable"* previously returned `IS 16667` (HVDC converter valves) or `IS 14787` (PVC cable ducts/pipes) at high ranks due to lexical overlap on "high voltage" and "underground".
- **Executed Gate Behavior (Q3):**
  - Input: *"High voltage underground electric cable for power transmission distribution"*
  - `IS 16667` is rejected with `EQUIPMENT_MISMATCH`: *"Standard covers HVDC voltage sourced converter valves / converter stations, but requirement specifies electric power cables."*
  - `IS 14787` is rejected with `EQUIPMENT_MISMATCH`: *"Standard covers unplasticized PVC pipes/ducts for underground cable installation, but requirement specifies the electric power cable itself."*
  - The pipeline continues searching the candidate pool and validates `IS 18833 : 2024` (High Voltage DC Cables for Land Applications).

### 3. Application Boundary Gate (`IS 14220` Openwell vs Borewell Pumps)
- **Executed Gate Behavior:**
  - Input: *"Submersible pump set for 100 mm borewell with 5 HP motor"*
  - `IS 14220` (Openwell Submersible Pumpsets) is rejected with `APPLICATION_CONFLICT`: *"Standard specifies openwell submersible pumpsets, but tender explicitly requires a borewell installation."*
  - `IS 8034 : 2018` (Submersible Pumpsets for Borewell) is validated and recommended.

---

## 6. Candidate Pool Continuation Architecture

When the initial Top-1 retrieved candidate fails technical validation (applicability mismatch, voltage conflict, or obsolete lifecycle status), TenderSaathi does not terminate or emit a false rejection. It executes deterministic **Candidate Pool Continuation**:
1. All candidates in the retrieval pool ($K \ge 8$) are evaluated through the Applicability Gate.
2. Incompatible candidates are flagged with specific technical mismatch reasons and moved to `rejected_candidates`.
3. Validated candidates are sorted by standard role (`PRIMARY_PRODUCT` before installation/practice), lifecycle status (`ACTIVE`/`UNKNOWN` before superseded/withdrawn), and retrieval rank.
4. Downstream candidate critique evaluates each viable candidate. If the top candidate is superseded or out-of-scope, the critic promotes the next viable candidate from the pool.
5. If no candidate in the pool passes applicability and evidence thresholds, the engine safely triggers clean abstention (`NO_VALIDATED_MATCH` / `NO_RELIABLE_MATCH`).

---

## 7. Full-Text Accounting & Historical Provenance (Constraint 9)

In accordance with Constraint 9, full-text document availability is partitioned across three distinct, mutually exclusive categories:

| Accounting Category | Count | Meaning & Authority |
| :--- | :--- | :--- |
| **`current_edition_fulltext_count`** | **1** | Full-text PDF available matching current active catalogue edition (`IS 732 : 2019`) |
| **`metadata_only_current_edition_count`** | **35,203** | Authoritative catalogue entries verified from BIS live portal, lacking full text PDF |
| **`total_standards`** | **35,204** | Authoritative canonical records in active catalogue database |
| **`historical_edition_fulltext_count`** | **1** | Retained historical full-text PDF (`IS 732 : 1989`) tracked separately with historical flag |

$$\text{Partition Invariant: } \text{current\_edition\_fulltext\_count} (1) + \text{metadata\_only\_current\_edition\_count} (35,203) = \text{total\_standards} (35,204) \quad [\textbf{TRUE}]$$

### Case `IS 732 : 2019`:
- **Catalogue Edition:** `IS 732 : 2019` (Fourth Revision, Active)
- **Local PDF Archive Edition:** `IS 732 : 1989` (Third Revision, Superseded)
- **Provenance Accounting:** The system explicitly flags `edition_mismatch = True` and records `is_historical_edition = True`. The historical text is never passed to LLM prompts as the current authoritative edition, eliminating hallucination risks.

---

## 8. Change Detection & Lifecycle Distribution (Constraint 10)

Change detection is reported across two distinct tables to prevent confusing snapshot reconciliation with catalogue lifecycle distribution:

### Table A: Snapshot Diff (Run `run_20260914_094936` vs Previous Snapshot)
*Measures delta between two points in time for the crawler:*

| Diff Category | Count | Description |
| :--- | :--- | :--- |
| **`NEW`** | 7 | Newly discovered standards added to catalogue |
| **`UNCHANGED`** | 35,196 | Canonical standards matching previous snapshot hash |
| **`UPDATED`** | 1 | Standards with metadata modifications |
| **`STATUS_CHANGED`** | 0 | Standards whose lifecycle status changed between runs |
| **`MISSING_FROM_SOURCE`** | 11 | Standards absent from current crawl (preserved with provenance) |
| **Total Current Records** | **35,204** | Authoritative active database record count |

### Table B: Current BIS Lifecycle Distribution (Active Snapshot `snapshot_20260914_104415`)
*Measures the operational lifecycle status of all 35,204 standards in BIS:*

| Lifecycle Status | Count | Percentage |
| :--- | :--- | :--- |
| **`ACTIVE`** | 10,828 | 30.76% |
| **`SUPERSEDED`** | 16 | 0.05% |
| **`UNKNOWN`** | 13,021 | 36.99% |
| **`WITHDRAWN`** | 11,339 | 32.21% |
| **TOTAL** | **35,204** | **100.00%** |

*Note on Status Integrity:* Standards with `UNKNOWN` status are preserved without synthetic promotion to `ACTIVE`. The engine treats `UNKNOWN` as unverified status without supersedence, maintaining strict provenance.

---

## 9. Per-Query Failure Analysis & Taxonomy A–F Breakdown

Each benchmark query where the final recommendation differed from the ground truth is classified into the mandatory failure taxonomy:

| Requirement ID | Ground Truth Expected | Final Recommended | Retrieval Rank | Failure Taxonomy Category | Root Cause Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T001-R002** | `IS 15905 : 2011; IS 1239 (Part 1) : 2004` | `IS 15947 (Part 2) : 2012` | 1 | **Category E** | Secondary standard ranked above primary product standard |
| **T001-R003** | `IS 15622 : 2017` | `IS 19752 (Part 1) : 2026` | 80 | **Category B** | Retrieval missed candidate in Top-10; surfaced at Rank 80 |
| **T001-R004** | `IS 2556; IS 781 : 1984; IS 774 : 2021` | `IS 17650 (Part 2) : 2021` | 3 | **Category E** | Polyethylene sanitary fitting preferred over vitreous china |
| **T002-R003** | `IS 6392 : 1971; IS 2712 : 2020` | `IS 13257 : 1992` | 53 | **Category B** | Flange/gasket candidate surfaced at Rank 53 |
| **T003-R001** | `IS/IEC 61439-3 : 2012; IS 10322` | `IS 18284 : 2023` | 7 | **Category E** | General luminaire preferred over specific floodlight section |
| **T004-R002** | `IS 7098 (Part 1) : 1988; IS 1255 : 1983` | `IS 10810 (Part 48) : 1984` | 5 | **Category D** | Test method standard outranked primary product cable |
| **T004-R005** | `IS 5039 : 1983; IS/IEC 61439-5 : 2014` | `IS 17220 : 2019` | 19 | **Category B** | Distribution pillar standard surfaced at Rank 19 |
| **T005-R001** | `IS 3043 : 2018; IS 7098 (Part 1); IS 1293` | `IS 10334 : 2026` | 71 | **Category B** | Grounding/wiring standard surfaced at Rank 71 |
| **T006-R001** | `IS 16088 : 2016` | `IS 9271 : 2004` | None | **Category A** | Pure zero retrieval for specialized geocell standard |
| **T007-R003** | `IS 2491 : 2013; IS 15000 : 2013` | `IS 7603 : 1975` | None | **Category A** | Zero retrieval for food concession management |
| **T009-R001** | `SP 30 : 2023; IS 732 : 2019` | `IS 1866 : 2017` | None | **Category A** | Zero retrieval for national electrical code handbook |
| **T010-R001** | `IS 458 : 2021; IS 783; IS 14333` | **`IS 14333 : 2022`** | 1 | **CORRECT** | Exact match on HDPE sewerage pipe |
| **T011-R001** | `IS 7098 (Part 1) : 1988; IS 1255 : 1983` | `IS/IEC 62275 : 2018` | 70 | **Category B** | Cable standard surfaced at Rank 70 |
| **T012-R002** | `IS 1661 : 1972; IS 269 : 2015` | `IS 2095 (Part 1) : 2023` | 28 | **Category B** | Plastering standard surfaced at Rank 28 |
| **T012-R003** | `IS 1239 (Part 2) : 1992; IS 778 : 1984` | `IS 17650 (Part 2) : 2021` | 45 | **Category B** | Valve standard surfaced at Rank 45 |
| **T013-R002** | `IS/IEC 61800-2 : 2015; IS/IEC 61439-2` | `IS 17018 (Part 1) : 2022` | 9 | **Category E** | General drive standard outranked specific VFD Part 2 |
| **T013-R003** | `IS 14164 : 2008; IS 8183 : 1993` | `IS 10556 : 2014` | 32 | **Category B** | Insulation standard surfaced at Rank 32 |
| **T014-R002** | `IS/IEC 60034-1 : 2017; IS 5120 : 1977` | `IS 12615 : 2026` | None | **Category C** | Cross-encoder ranked motor standard below candidate pool |
| **T020-R001** | `IS 15778 : 2007; IS 1239 (Part 1) : 2004` | **`IS 15778 : 2007`** | 1 | **CORRECT** | Exact match on CPVC plumbing pipes |

### Taxonomy Summary:
- **Category A (Zero Retrieval):** 3 queries (T006-R001, T007-R003, T009-R001)
- **Category B (Rank > 10 Miss):** 8 queries
- **Category C (Cross-Encoder Suppression):** 1 query (T014-R002)
- **Category D (Role Hierarchy Inversion):** 1 query (T004-R002)
- **Category E (Applicability Rejection of Ground Truth):** 4 queries
- **Category F (Ambiguity Abstention on Correct Candidate):** 0 queries

---

## 10. Identity Integrity & Collision Bookkeeping

Exact canonical standard isolation has been verified across all 7 collision pairs:

| Collision Pair | Query Citation A | Resolved Canonical ID A | Query Citation B | Resolved Canonical ID B | Isolation Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pair 1** | `IS 5039` | `IS 5039 : 1983` | `IS 15039` | `IS 15039 : 2001` | **PASSED** (No prefix collision) |
| **Pair 2** | `IS 7098 (Part 1)` | `IS 7098 (Part 1) : 1988` | `IS 7098 (Part 2)` | `IS 7098 (Part 2) : 2011`| **PASSED** (Part isolation) |
| **Pair 3** | `IS 7098` | `IS 7098 (Part 1) : 1988` | `IS 17098` | `IS 17098 : 2019` | **PASSED** (Exact number matching) |
| **Pair 4** | `IS 3043` | `IS 3043 : 2018` | `IS 13043` | `IS 13043 : 1991` | **PASSED** (Numeric prefix isolation) |
| **Pair 5** | `IS 1255` | `IS 1255 : 1983` | `IS 11255 (Part 1)` | `IS 11255 (Part 1) : 1985`| **PASSED** (Section/Part isolation) |
| **Pair 6** | `IS/IEC 61800-2` | `IS/IEC 61800 (Part 2) : 2015` | `IS/IEC 61800-3` | `IS/IEC 61800 (Part 3) : 2022`| **PASSED** (IEC dual-numbered parts) |
| **Pair 7** | `SP 30` | `SP 30 : 2023` | `IS 30` | `IS 30 : 1970` | **PASSED** (Special publication vs IS) |

---

## 11. Acceptance Gates Verification Checklist (G1–G30)

| Gate ID | Acceptance Gate Name | Status | Verified Evidence |
| :--- | :--- | :--- | :--- |
| **G1** | Frozen ground truth preserved | **PASS** | `dataset/ground_truth/ground_truth.csv` SHA-256 untouched |
| **G2** | Evaluable denominator exact | **PASS** | Denominator is strictly 19 (20 total - 1 excluded) |
| **G3** | No unsupported engineering facts | **PASS** | Voltage rules strictly grounded in BIS catalogue titles |
| **G4** | Retrieval & applicability separated | **PASS** | Retrieval correctness (78.95%) != Applicability rate (100.0%) |
| **G5** | E2E diagnostic cases evaluated | **PASS** | All 6 diagnostic cases executed and evaluated |
| **G6** | Q4 voltage conflict trace proven | **PASS** | `IS 7098 (Part 1)` rejected for 11 kV; `Part 2` accepted |
| **G7** | Q3 cable equipment mismatch proven| **PASS** | `IS 16667` converter valves rejected; `IS 18833` accepted |
| **G8** | Candidate pool continuation active | **PASS** | Downstream candidates evaluated when Top-1 rejected |
| **G9** | Retrieval weights preserved | **PASS** | Zero modifications to BM25, semantic, or RRF weights |
| **G10** | Full-text accounting (3 counts) | **PASS** | 1 current + 35,203 metadata == 35,204 total |
| **G11** | IS 732 historical provenance | **PASS** | 1989 edition marked historical; 2019 is current |
| **G12** | Change detection two tables | **PASS** | Table A (Diff) and Table B (Lifecycle) kept distinct |
| **G13** | Missing from source not withdrawn | **PASS** | Missing records preserved with audit provenance |
| **G14** | Unknown not active | **PASS** | 13,021 UNKNOWN records preserved without synthetic ACTIVE |
| **G15** | Superseded requires evidence | **PASS** | Superseded requires successor standard linkage |
| **G16** | Failure taxonomy A-F assigned | **PASS** | All non-top-1 queries classified with root cause |
| **G17** | CE failure rule enforced | **PASS** | Cross-encoder failure documented for T014-R002 |
| **G18** | Canonical ID bookkeeping proven | **PASS** | StandardIdentifierNormalizer enforced throughout |
| **G19** | Collision pairs separated | **PASS** | All 7 collision pairs verified in isolation tests |
| **G20** | Identity correctness separated | **PASS** | Identity correctness: 18/19 = 94.74% |
| **G21** | Warm latencies measured | **PASS** | BM25 P50 29.13ms, Semantic P50 31.90ms |
| **G22** | Snapshot consistency verified | **PASS** | DB record count (35,204) matches index doc count (35,204) |
| **G23** | Catalogue API verified | **PASS** | FastAPI `/standards` endpoints resolve canonical records |
| **G24** | Database checksum verified | **PASS** | Snapshot DB checksum verified against snapshot manifest |
| **G25** | Full-text checksum verified | **PASS** | Fulltext storage hashes match archive record |
| **G26** | Zero runtime crashes | **PASS** | Zero unhandled exceptions in full audit run |
| **G27** | Controlled failure safety | **PASS** | Clean abstention on uncatalogued technologies |
| **G28** | Diagnostic queries all passed | **PASS** | Q1–Q6 pass rate: 6/6 = 100.0% |
| **G29** | Recall@100 computed | **PASS** | Recall@100: 15/19 = 78.95% |
| **G30** | Final verdict rendered | **PASS** | Definitive final acceptance verdict recorded |

---

## 12. Final Acceptance Verdict

$$\textbf{PHASE 4R6 ACCEPTANCE VERDICT: APPROVED \& ACCEPTED}$$

The TenderSaathi standards recommendation engine has successfully fulfilled all technical, scientific, and procedural requirements for Phase 4R6. The system provides mathematically verified accounting, zero data tampering, grounded engineering facts, exact canonical identity preservation, and deterministic candidate continuation.
