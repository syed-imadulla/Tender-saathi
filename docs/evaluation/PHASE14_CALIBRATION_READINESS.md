# Tender Saathi — Phase 14 Preparation: Calibration Readiness & Validation Design

**Document ID:** `DOC-EVAL-PHASE14-CALIBRATION-READINESS`  
**Date:** 2026-10-18  
**Evaluation Target:** Threshold-Calibration Experiment Readiness & Protocol Design  
**Repository State:** Offline Isolated, Deterministic, 563 Backend Tests Passing, Frontend Vite Build Passing  

---

## Executive Summary & Official Determination

### Official Decision: **NOT READY FOR CALIBRATION**

Before any broad threshold sweep, grid search, or production parameter tuning can occur, the following critical prerequisite gate failures must be resolved:

1. **Adjudication Gate Failure (Fatal):** Exactly **zero (0 / 40)** cases across active ground truth and candidate staging have been adjudicated by qualified domain reviewers. All rows remain flagged as `UNVERIFIED_BASELINE` or `UNVERIFIED_STAGING`.
2. **Under-Specified Prerequisite Failure (Fatal):** The mandatory project prerequisite (*"at least five adjudicated under-specified requirements before abstention-threshold calibration"*) is **NOT SATISFIED**. Active ground truth contains only 1 under-specified row (`T002-R002`), candidate staging contains 14 unreviewed drafts, and negative controls contain 1 probe (`NEG-003`). None are expert-verified.
3. **Compound Dominance Distortion Risk (Structural):** 17 out of 19 answerable baseline rows (89.5%) are multi-standard compound requirements. Calibrating simple scalar confidence thresholds on multi-standard tenders without component-level decomposition would distort assisted vs. recommended decision boundaries.
4. **Statistical Sample Size Limitation (Fatal):** The current ground-truth dataset contains only 12 unique tenders across 19 answerable queries. Any train/val/test split yields test cohorts of 4–5 cases, producing Wilson 95% confidence intervals wider than $\pm 25\%$, rendering threshold comparisons statistically meaningless.

Production defaults and ranking formulas **MUST REMAIN FROZEN** at their current levels until Phase 13 expert adjudication and Phase 14 data expansion are completed.

---

## 1. Verified Repository and Dataset State

An independent audit of code, datasets, and test harnesses was executed with the following verified outcomes:

### 1.1 Dataset Integrity & Hash Verification
- **Active Ground Truth:** `dataset/ground_truth/ground_truth.csv`
  - **SHA-256:** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
  - **Row Count:** 20 rows total.
  - **Verification Status:** 20 / 20 rows (100%) have `verification_status: UNVERIFIED_BASELINE` and `human_verified: FALSE`.
- **Candidate Staging:** `dataset/ground_truth/candidates_staging.csv`
  - **SHA-256:** `99e829378c2e64caea65b16fbeaf3579be6a86f9f6880026e69cc125c56c204d`
  - **Row Count:** 21 rows total (staged in Phase 13 for expert review).
  - **Verification Status:** 21 / 21 rows (100%) have `verification_status: UNVERIFIED_STAGING`.
- **Adjudication Packets:** `reports/adjudication_packets/packets/`
  - **Packet Count:** 40 draft packets (`PACKET-T001-R001.json` through `PACKET-T012-R002.json`).
  - **Verification Status:** Exactly 0 signed or reviewed packets exist. No adjudications have been recorded.

### 1.2 Negative-Control and Distractor-Probe Provenance & Classification
5 negative-control and distractor probes are evaluated in `scripts/evaluate_milestone12.py`:
- `NEG-001` (Heavy industrial crane rail, ASTM A759 / DIN 536):
  - **Classification:** Genuine open-set / domain mismatch.
  - **Provenance:** Synthetic adversarial probe.
  - **Decision State:** Safely withheld (`WITHHELD_INSUFFICIENT_EVIDENCE`). Domain gate fires properly (`civil_structural` rejected against electrical catalogue).
- `NEG-002` (1.1 kV grade 4-core aluminum conductor LT power cable):
  - **Classification:** In-domain distractor / specification mismatch probe.
  - **Provenance:** Derived from real DISCOM tender syntax; references generic 1.1 kV cable.
  - **Decision State:** Safely assisted (`ASSISTED_REVIEW_REQUIRED`) with `clarification_needed` due to standard separation thresholding.
- `NEG-003` (Supply of electrical equipment for substation, no specs/voltage):
  - **Classification:** Under-specified procurement requirement.
  - **Provenance:** Synthetic under-specification probe.
  - **Decision State:** Safely withheld (`WITHHELD_INSUFFICIENT_EVIDENCE`). Applicability score < 0.35.
- `NEG-004` (Structural steel fabrication for warehouse roof trusses):
  - **Classification:** Out-of-scope / domain mismatch.
  - **Provenance:** Synthetic domain distractor probe.
  - **Decision State:** Safely withheld (`WITHHELD_INSUFFICIENT_EVIDENCE`). Applicability score = 0.00 via electrical exclusion filter.
- `NEG-005` (Gibberish / non-procurement random noise):
  - **Classification:** Adversarial non-procurement text.
  - **Provenance:** Synthetic fuzzing probe.
  - **Decision State:** Safely withheld (`WITHHELD_INSUFFICIENT_EVIDENCE`). Zero keywords matched.

**Current Negative-Control False Recommendation Rate:** **0 / 5 (0.0%)**.

### 1.3 Active Operational Decision States and Thresholds
The production decision thresholds across components are verified as follows:
- **Applicability Gate (`src/applicability.py`):**
  - `applicability_threshold = 0.60` (High applicability for direct recommendation consideration).
  - `review_threshold = 0.35` (Borderline band requiring human assistance / review).
  - `domain_filter`: Mandatory electrical keyword requirement. Exclusion filter blocks civil/structural/fabrication items.
- **Ambiguity Engine (`src/ambiguity.py`):**
  - `separation_threshold = 0.12` (Score gap between Top-1 and Top-2 standards; below 0.12 triggers competing alternative clarification).
- **Critic & Decision Safety Gate (`src/critic.py`):**
  - `critic_recommend_score = 0.70` (Minimum weighted composite score for autonomous `RECOMMENDED`).
  - `critic_assisted_score = 0.55` (Minimum score for `ASSISTED_REVIEW_REQUIRED`).
  - `min_relevance = 0.35` (Hard floor for keyword/semantic overlap).
  - `min_evidence = 0.65` (Hard floor for supporting evidence quality).
  - `lifecycle_score == 0.0` (Hard blocker: withdrawn/superseded standards can NEVER be autonomously recommended).

### 1.4 Test Suite & Build Verification
- **Backend Tests:** **563 passed in 55.65s** (expanded from 557 with 6 new calibration harness unit tests). 100% offline isolation preserved.
- **Frontend Build:** `npm run build` completed cleanly (0 errors, 52 modules transformed, Vite bundle generated in 891ms).

---

## 2. Category-Wise Adjudication Inventory

A rigorous audit of all available cases across the 7 calibration cohorts yields the following inventory:

| Cohort Category | Total Available Cases | Genuinely Adjudicated | Unverified Drafts | Key Evidence Gaps & Label Quality Risks |
| :--- | :---: | :---: | :---: | :--- |
| **1. Answerable In-Domain (Single Standard)** | 2 in GT (`T001-R003`, `T006-R001`) | **0** | 2 | Smallest sample size; `T006-R001` relies on unverified baseline string matching. |
| **2. Answerable In-Domain (Compound / Multi-Std)** | 17 in GT | **0** | 17 | Severe label complexity. Semicolon-delimited standards (e.g. `IS 2026; IS 11171; IS 3639`). Single scalar scores fail to isolate which sub-clauses are matched. |
| **3. Under-Specified Requirements** | 16 (1 GT `T002-R002`, 14 Staged, 1 Probe `NEG-003`) | **0** | 16 | **FATAL PREREQUISITE FAILURE:** Requires $\ge 5$ verified cases. Currently 0 verified. Abstention threshold cannot be calibrated. |
| **4. Ambiguous / Competing Alternatives** | 2 Staged (`T002-R001`, `T002-R004`), 1 Probe (`NEG-002`) | **0** | 3 | Lacks domain expert consensus on acceptable primary vs. secondary standard pairs. |
| **5. Genuine Open-Set / Ineligible** | 3 Probes (`NEG-001`, `NEG-004`, `NEG-005`) | **0** | 3 | Pure synthetic probes; lacks real tender excerpts of out-of-scope non-electrical items. |
| **6. Retrieval Distractor Probes** | 1 Probe (`NEG-002`) | **0** | 1 | Need real DISCOM cable/transformer distractor queries with overlapping voltage ratings. |
| **7. Lifecycle / Edition-Sensitive** | 4 in GT (`IS 15622`, `IS 732`, `IS 3043`, `IS 15000:2024`) | **0** | 4 | No full-text BIS gazette corpus or clause-level change diffs ingested into local catalogue. |

### Adjudication Prerequisite Verification
- **Requirement:** Phase 13 / 14 governance explicitly requires: *"At least five adjudicated under-specified requirements before abstention-threshold calibration."*
- **Current Status:** **0 / 5**.
- **Finding:** **PREREQUISITE NOT SATISFIED.** Calibration of abstention thresholds without verified under-specified cases risks overfitting to synthetic probes and triggering severe false-negative abstentions on legitimate tenders.

---

## 3. Explicit Blockers & Missing Data

To prevent premature calibration and unprincipled tuning, the following blockers are formally documented:

### Blocker 1: Zero Qualified Domain Expert Adjudications
No professional electrical procurement engineer or standards specialist has reviewed the 40 generated adjudication packets. Modifying production thresholds based on unverified labels would optimize against ungrounded assumptions.

### Blocker 2: Absence of Full-Text Standards Corpus
Clause-level grounding cannot be quantitatively evaluated because the repository currently indexes standard metadata (titles, scopes, keywords, editions) rather than full-text normative clauses. Recommender confidence currently reflects metadata alignment, not clause verification.

### Blocker 3: Compound Multi-Standard Dominance
89.5% of answerable cases require multiple standards simultaneously. A single threshold model cannot distinguish whether a score of 0.65 represents a perfect match on one standard of two, or a mediocre match on both. Calibration requires decomposed sub-requirement evaluation.

### Blocker 4: Severe Statistical Underpowering
With only 12 unique tenders across 19 answerable queries:
- **Test Cohort Size:** 4 to 5 cases in a 3-way split.
- **Wilson 95% Confidence Interval for 89.5% (17/19):** **[68.6%, 97.1%]** (span of 28.5 percentage points).
- **Statistical Significance:** A threshold change that improves accuracy from 17/19 to 18/19 is completely indistinguishable from random noise ($p > 0.5$).

---

## 4. Proposed Leakage-Safe Calibration Protocol

When the prerequisite dataset is gathered and adjudicated, the following protocol must govern Phase 14 calibration:

### 4.1 Grouped Partitioning Strategy
- **Grouping Unit:** `tender_id` (Disjoint partition).
- **Rule:** All requirements derived from the same tender document (e.g., `T001-R001`, `T001-R002`, `T001-R003`, `T001-R004`) **MUST** reside exclusively in the same partition. Clause phrasing, boilerplates, and organizational conventions cannot leak across splits.
- **Split Ratios (Target after data expansion to $\ge 80$ tenders):**
  - **Development / Calibration Set:** 60% of tenders.
  - **Validation Set (Tuning & Model Selection):** 20% of tenders.
  - **Held-Out Test Set (Single Final Evaluation):** 20% of tenders.

### 4.2 Target Parameters for Calibration
Only operational decision thresholds may be tuned. Architectural routing and ranking equations remain fixed.
1. `applicability_threshold` (candidate grid: `[0.50, 0.55, 0.60, 0.65, 0.70]`)
2. `review_threshold` (candidate grid: `[0.30, 0.35, 0.40, 0.45]`)
3. `separation_threshold` (candidate grid: `[0.08, 0.10, 0.12, 0.15]`)
4. `critic_recommend_score` (candidate grid: `[0.65, 0.70, 0.75, 0.80]`)
5. `critic_assisted_score` (candidate grid: `[0.50, 0.55, 0.60]`)

### 4.3 Mandatory Fixed Safety Invariants
The following rules are non-negotiable and **CANNOT** be loosened during calibration:
- **Lifecycle Zero-Tolerance:** `lifecycle_score == 0.0` always produces hard disqualification from autonomous recommendation. Superseded or withdrawn standards must never be recommended.
- **Negative-Control Rejection Floor:** False Recommendation Rate on negative-control and out-of-scope probes must remain **strictly 0.0%**. Any configuration yielding > 0% is immediately rejected.
- **Evidence Floor:** `min_evidence >= 0.60` is permanently enforced.

### 4.4 Multi-Dimensional Evaluation Metrics
The calibration runner reports metrics stratified by cohort:
- **Retrieval Accuracy (Top-1, Top-3, Mean Reciprocal Rank):** Evaluated strictly on answerable in-domain cohorts.
- **Autonomous Recommendation Coverage:** Percentage of answerable cases receiving `RECOMMENDED`.
- **Selective Risk:** Percentage of autonomous `RECOMMENDED` decisions that predict an incorrect standard.
- **Safe Abstention Rate:** Proportion of under-specified and out-of-scope requirements receiving `WITHHELD` or `ASSISTED`.
- **Distractor Discrimination Rate:** Proportion of competing distractor queries triggering `clarification_needed`.
- **Wilson 95% Confidence Intervals:** Computed and reported for all proportions.

---

## 5. Acceptance & Rollback Criteria

Before any candidate configuration can be adopted into production defaults:

### 5.1 Acceptance Criteria (All Must Pass)
1. **Adjudication Prerequisite:** Evaluated strictly on a dataset containing $\ge 5$ verified under-specified cases and $\ge 50$ total expert-adjudicated cases.
2. **Zero Safety Regression:** Negative-Control False Recommendation Rate remains exactly **0.0%** (0 false recommendations across all negative probes).
3. **No Lifecycle Drift:** Withdrawn/superseded standards receive 0 autonomous recommendations.
4. **Selective Risk Reduction:** Selective risk on the validation split is strictly $\le 5.0\%$.
5. **Generalization:** Performance delta between Calibration set and Validation set does not exceed 10 percentage points (guard against overfitting).

### 5.2 Rollback Triggers (Any Triggers Immediate Revert)
- Any occurrence of an out-of-scope or synthetic negative requirement receiving an autonomous `RECOMMENDED` decision.
- A drop in Top-1 retrieval accuracy on answerable cases of $\ge 2.0$ percentage points.
- Any attempt by calibration logic to mutate production files or bypass hardcoded safety gates.

---

## 6. Infrastructure Delivered in Phase 14 Preparation

To support rigorous, leakage-safe experimentation when adjudication is complete, the following isolated offline infrastructure was built and verified:

### 6.1 Calibration Harness (`src/calibrate.py`)
- `CalibrationConfig`: Dataclass encapsulating threshold sets with immutability guarantees.
- `TenderSplitter`: Implements tender-level grouped partitioning ensuring zero cross-tender leakage with automatic disjointness assertion.
- `RequirementCategorizer`: Classifies requirements into the 7 standard evaluation cohorts based on domain, completeness, and complexity.
- `calculate_wilson_interval`: Computes Wilson score binomial confidence intervals with small-sample edge-case protection ($n=0$, $p=0$, $p=1$).
- `OfflineCalibrationRunner`: Evaluates candidate configurations against production baselines without modifying production constants, reporting cohort-stratified results, selective risk, and safety gate compliance.

### 6.2 Unit Test Verification (`tests/test_calibration_harness.py`)
6 comprehensive unit tests verifying calibration infrastructure:
1. `test_tender_splitter_disjointness`: Proves zero tender-id overlap across train/val/test splits.
2. `test_requirement_categorization`: Verifies correct assignment of in-domain single, compound, under-specified, and distractor requirements.
3. `test_wilson_score_interval`: Validates mathematical correctness of confidence intervals across small sample sizes.
4. `test_offline_calibration_runner_safety_rejection`: Confirms automatic disqualification of configurations that produce false recommendations on negative controls.
5. `test_runner_does_not_mutate_production_defaults`: Enforces immutability of production defaults during evaluation sweeps.
6. `test_empty_cohort_handling`: Proves graceful handling of empty or missing test cohorts without crashing.

---

## 7. Exact Tests & Commands Executed

| Command Executed | Directory | Outcome | Verification Details |
| :--- | :--- | :--- | :--- |
| `pytest tests/test_calibration_harness.py` | Project Root | **6 passed in 5.84s** | Validated split disjointness, Wilson CIs, and safety rejection logic. |
| `pytest tests/` | Project Root | **563 passed in 55.65s** | Full regression suite passed offline. Zero regressions introduced. |
| `npm run build` | `frontend/` | **Built in 891ms** | Vite production bundle compiled cleanly with 0 TypeScript/build errors. |

---

## 8. Action Plan Before Calibration Can Begin

To reach **READY FOR CALIBRATION** status, the project must execute the following sequential milestones:

```
[Phase 13 Adjudication] ──> [Expert Packets Completed] ──> [$\ge 5$ Under-Specified Verified]
                                                                     │
[Full Corpus Ingestion] ──> [Clause-Level Evidence]    ──────────────┤
                                                                     ▼
[Phase 14 Re-assessment] <── [Tender Data Expansion ($\ge 80$)] <── [Prerequisites Met]
        │
        ▼
[Leakage-Safe Calibration Run]
```

1. **Complete Phase 13 Adjudication:** Engage qualified electrical procurement engineers to review and sign off on the 40 existing draft packets in `reports/adjudication_packets/packets/`.
2. **Gather Under-Specified Requirements:** Collect and adjudicate at least 5 ambiguous/under-specified real-world tender excerpts to satisfy the abstention threshold calibration gate.
3. **Expand Tender Sample Size:** Ingest at least 40–50 additional unique tender specifications across DISCOM, CPWD, and industrial tenders to allow statistically valid 3-way splits.
4. **Ingest Clause-Level Corpus:** Index normative text for core BIS standards (`IS 2026`, `IS 1180`, `IS 694`, `IS 1554`, `IS 7098`, `IS 3043`, `IS 732`) to enable ground-truth clause verification.
5. **Re-run Phase 14 Readiness Audit:** Verify that all 4 blockers are resolved before initiating parameter calibration.
