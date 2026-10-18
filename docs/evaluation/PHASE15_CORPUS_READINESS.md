# Tender Saathi — Phase 15: Real-World Evaluation Corpus & Expert-Adjudication Readiness Report

**Document ID:** `DOC-EVAL-PHASE15-CORPUS-READINESS`  
**Date:** 2026-10-18  
**Phase Target:** Data-Quality, Evidence-Readiness & Human Adjudication Infrastructure  
**Governing Standard:** [`docs/data/GROUND_TRUTH_GOVERNANCE.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/data/GROUND_TRUTH_GOVERNANCE.md)  
**Corpus Inventory:** [`reports/corpus_inventory.json`](file:///home/syed-imadulla/Desktop/Tender_Saathi/reports/corpus_inventory.json)  
**Intake Guide & Under-Specification Protocol:** [`docs/data/REAL_SOURCE_INTAKE_GUIDE.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/data/REAL_SOURCE_INTAKE_GUIDE.md)  

---

## Executive Summary & Official Determination

### Official Decision: **NOT READY FOR CALIBRATION (Prerequisites Strictly Enforced)**

Tender Saathi remains intentionally and safely at the **expert-adjudication and corpus-readiness boundary**. All production thresholds, ranking weights, and classification formulas remain **100% frozen** at baseline. Zero synthetic reviewer identities or artificial sign-offs were manufactured.

The active ground truth SHA-256 is strictly preserved:
- **Baseline SHA-256:** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Current SHA-256:** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (100% Unchanged)

---

## 1. Verified Corpus Inventory & Provenance (Workstream A)

A machine-readable corpus audit was executed across all tiers and published to [`reports/corpus_inventory.json`](file:///home/syed-imadulla/Desktop/Tender_Saathi/reports/corpus_inventory.json).

### 1.1 Dataset Tier Counts
- **Tier 3 (Active Ground Truth Benchmark):** 20 cases (`ground_truth.csv`)
  - Status: 20 / 20 (100%) `UNVERIFIED_BASELINE` with `human_verified: FALSE`.
  - Origin: 14 distinct real government tender notices in `tenders/raw/`.
- **Tier 1 (Staged Candidate Pipeline):** 21 cases (`candidates_staging.csv`)
  - Status: 21 / 21 (100%) `MACHINE_PREDICTED` with `human_verified: FALSE`.
  - Origin: 8 distinct real tender notices + 1 historical probe (`PROV-ELEC-NEG002`).
- **Total Catalogued Inventory:** **41 cases**.
- **Expert-Adjudicated Cases:** **0 / 41 (0.0%)**.

### 1.2 Cohort Distribution & Evidence Grounding

| Calibration Cohort | Total Cases | Expert Verified | Physical PDF Linked | Exact Clause Cited | Status / Evaluation Suitability |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Answerable In-Domain (Compound)** | 17 | 0 | 17 / 17 | 17 / 17 | Semicolon-delimited compound requirements; qualitative review only. |
| **Answerable In-Domain (Single)** | 7 | 0 | 6 / 7 | 2 / 7 | Baseline in-domain single-standard cases; requires human sign-off. |
| **Under-Specified Requirements** | 15 | 0 | 15 / 15 | 1 / 15 | **Fatal Gate Failure (0 / 5 verified)**; abstention calibration blocked. |
| **Lifecycle / Edition-Sensitive** | 2 | 0 | 2 / 2 | 2 / 2 | Superseded/amended standards (`IS 15622`, `IS 15000:2024`). |
| **Retrieval Distractor Probes** | 1 | 0 | 0 / 1 (Synthetic) | 1 / 1 | `NEG-002` cable distractor; segregated from open-set rejection. |
| **Genuine Open-Set / Ineligible** | 3 | 0 | 0 / 3 (Synthetic) | 0 / 3 | `NEG-001` (crane rail), `NEG-004` (roof truss), `NEG-005` (gibberish). |

### 1.3 Physical Source Availability & Legal Accessibility
- **40 out of 41 cases (97.6%)** are physically bound to real tender PDFs located in `tenders/raw/`.
- Every source PDF is a public government tender notice downloaded from the Central Public Procurement Portal (`eprocure.gov.in`) or GeM, fully accessible under Indian Right to Information (RTI) guidelines for public procurement transparency.
- 1 case (`PROV-ELEC-NEG002`) represents an in-domain distractor query derived from historical probe records.

---

## 2. Real-Source Acquisition Workflow & Standards Metadata Protocol (Workstream B)

The real-source acquisition workflow has been codified in [`docs/data/REAL_SOURCE_INTAKE_GUIDE.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/data/REAL_SOURCE_INTAKE_GUIDE.md) and programmatically enforced in [`src/intake.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/intake.py):

1. **Intake Validation Checks:**
   - Every source document must record `document_id`, canonical portal `source_url`, `retrieval_date_utc`, `procurement_authority`, and SHA-256 checksum.
   - `SourceDocumentRecord.validate()` computes real-time cryptographic file hashes and asserts that on-disk bytes match recorded hashes.
2. **Copyright & Legal Boundary Protection:**
   - No paywalls are bypassed. Tender Saathi indexes authorized public metadata, official titles, technical committees, Quality Control Orders (QCOs), and published scope clauses.
   - Cases lacking full-text clause access are transparently marked `CLAUSE_CITED_UNVERIFIED_FULLTEXT` or `METADATA_ONLY_NO_CLAUSE`. Machine predictions are never substituted for authoritative text.

---

## 3. Under-Specified Case Collection & Audit (Workstream C)

The mandatory project prerequisite (*"at least five adjudicated under-specified requirements before abstention-threshold calibration"*) was audited with the following findings:

### 3.1 Audit Findings
- **Active Ground Truth:** Exactly 1 under-specified case (`T002-R002`, "Valve Replacement").
- **Candidates Staging:** 14 candidate rows generated by heuristic expansion.
  - Of these 14 rows, several are near-duplicate excerpts from the same tenders (e.g. `T001-R001` vs `T001-R005`; `T002-R001` vs `T002-R004`; `T004-R001` vs `T004-R003`; `T006-R004` vs `T006-R005`).
- **Expert Adjudicated Count:** **0 / 15**.
- **Prerequisite Verdict:** **FAIL (0 / 5 satisfied)**.

### 3.2 Real Candidate Excerpts Ready for Adjudication
To satisfy the 5-case prerequisite without synthetic paraphrases, 5 genuine, non-duplicate tender excerpts have been audited and documented in the intake guide across the 6 canonical dimensions:
1. `T002-R002` (Heavy Water Board): *"Valve Replacement"* (Missing nominal bore, pressure class, metallurgy).
2. `T004-R001` (IIT ISM Dhanbad): *"Dismantling, Shifting and reinstallation of feeder pillar, power cables from outside of electrical room to AMF room"* (Missing voltage rating 1.1 kV vs 11 kV, conductor cross-section).
3. `T004-R006` (IIT ISM Dhanbad): *"replacement of faulty 2x2 celing light of seminar and"* (Missing wattage, efficacy, driver safety class).
4. `T005-R002` (IIT ISM Dhanbad): *"Cable connection of DG Set in Newly constructed building of the dept."* (Missing generator kVA rating, earthing design, FRLS insulation requirement).
5. `T010-R001` (Collection Chamber): *"Electromechanical Works and Sewerage Pipeline works from Collection Chamber to STP"* (Missing pump flow rate/head, drainage pipe metallurgy).

---

## 4. Adjudication Usability & Reviewer Handoff (Workstream D)

### 4.1 Reviewer Packet Improvements
- Fixed `DB_PATH` fallback in [`scripts/generate_adjudication_packets.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/scripts/generate_adjudication_packets.py) to resolve against the active SQLite database (`data/standards/standards.db`, 90 BIS standards).
- Regenerated all **41 adjudication packets** in [`reports/adjudication_packets/packets/`](file:///home/syed-imadulla/Desktop/Tender_Saathi/reports/adjudication_packets/packets/).
- Every packet now provides:
  - Exact source document and page number.
  - Verbatim specification text.
  - Proposed baseline classification with explicit `"Pending Expert Citation"` warnings.
  - Official BIS catalogue metadata (Title, Status, Technical Committee, Official Scope).
  - Clean two-party YAML reply blocks for Reviewer A and Reviewer B.

### 4.2 Expert-Adjudication Handoff Checklist
To ensure frictionless review by external domain engineers:
- [ ] **Step 1: Role Verification**: Verify that Reviewer A and Reviewer B belong to certified engineering cadres (`CPWD_EXECUTIVE_ENGINEER`, `CPWD_ASSISTANT_ENGINEER`, `BIS_STANDARDS_OFFICER`, `MES_MILITARY_ENGINEER`, `PUBLIC_PROCUREMENT_SPECIALIST`).
- [ ] **Step 2: Rubric Adherence**: Evaluate against the 5 canonical outcomes defined in [`docs/data/ADJUDICATION_RUBRIC.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/data/ADJUDICATION_RUBRIC.md).
- [ ] **Step 3: Independent Review**: Reviewer A and Reviewer B independently fill their respective YAML blocks with verified standard numbers, clause citations, and minimum 20-character technical rationales.
- [ ] **Step 4: Deposit Completed Files**: Place completed review packets in `reports/adjudication_packets/completed/`.
- [ ] **Step 5: Automated Ingestion Gate**: Execute `python3 scripts/ingest_adjudication.py --dry-run` to detect two-party consensus and escalate disagreements.

---

## 5. Evaluation Integrity & Leakage Prevention (Workstream E)

### 5.1 Split Partitioning Rules
- Strict tender-level grouping implemented via `TenderSplitter.split()` in [`src/calibrate.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/calibrate.py).
- Requirements derived from the same tender document are mathematically constrained to the same split.
- **Enhanced Near-Duplicate Audit:** Added substring overlap detection across splits. Even if tenders have distinct IDs, requirement texts sharing $\ge 30$ characters of identical procurement language trigger a `text_leakage_warning` and invalidate the split.

### 5.2 Mandatory Evidence Gates Before Calibration
Before any candidate configuration can be adopted:
1. **Adjudication Gate:** Evaluated strictly on $\ge 5$ verified under-specified cases and $\ge 50$ total expert-adjudicated cases.
2. **Negative-Control Floor:** Negative-Control False Recommendation Rate remains strictly **0.0%**.
3. **Lifecycle Zero-Tolerance:** Withdrawn standards receive exactly 0 autonomous recommendations.
4. **Selective Risk Floor:** Selective risk on the validation split is strictly $\le 5.0\%$.

---

## 6. Verification & Test Outcomes

| Test Suite / Command | Scope | Result | Verification Notes |
| :--- | :--- | :--- | :--- |
| `pytest tests/test_intake_validation.py` | Intake validation & anti-falsification | **5 passed in 1.06s** | Verified source validation, 6-dimension schema, anti-falsification role checks, and inventory generation. |
| `pytest tests/test_adjudication_workflow.py` | Adjudication workflow & governance | **8 passed in 0.07s** | Verified rubric completeness, manifest indexing, blank reviewer form guards, and consensus logic. |
| `pytest tests/test_calibration_harness.py` | Calibration runner & leakage checks | **6 passed in 9.95s** | Verified tender split disjointness, Wilson CIs, and safety gate rejection. |
| `pytest tests/` | Full repository offline regression | **568 passed** | 100% offline isolation maintained. Zero regressions across all 568 tests. |
| `npm run build` | Frontend UI production build | **Built in 891ms** | Vite production bundle compiled cleanly with 0 TypeScript/build errors. |

---

## 7. Next Actions Required From a Human

Execution has stopped cleanly at the human-expert boundary. The following manual steps must be undertaken by human coordinators:

1. **Deliver Adjudication Packets:** Distribute the 41 generated case packets in [`reports/adjudication_packets/packets/`](file:///home/syed-imadulla/Desktop/Tender_Saathi/reports/adjudication_packets/packets/) to qualified CPWD, BIS, or MES procurement engineers.
2. **Obtain Two-Party Sign-Off:** Ensure Reviewer A and Reviewer B independently populate and sign their YAML blocks.
3. **Ingest Completed Packets:** Place returned markdown files in `reports/adjudication_packets/completed/` and run `python3 scripts/ingest_adjudication.py --promote`.
4. **Verify Prerequisites:** Confirm that at least 5 under-specified cases have received consensus sign-off before initiating Phase 16 threshold calibration.
