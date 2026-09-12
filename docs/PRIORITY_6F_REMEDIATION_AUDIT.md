# PRIORITY 6F — FINAL CONTROLLED REMEDIATION & REPRODUCIBILITY AUDIT

**Project:** TenderSaathi (SIH26108)  
**Milestone:** Priority 6F — Controlled Remediation & Reproducibility Lock  
**Date:** September 12, 2026  
**Auditor:** Independent Antigravity Remediation Agent  
**Reference Artifacts:**
- [`docs/PRIORITY_6_FINAL_AUDIT.md`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/docs/PRIORITY_6_FINAL_AUDIT.md)
- [`docs/PRIORITY_6_FINAL_AUDIT.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/docs/PRIORITY_6_FINAL_AUDIT.json)

---

## 1. Executive Summary & Final Decision

In accordance with the Priority 6E Audit mandate, this milestone addressed **ONLY** the confirmed technical and architectural blockers without adding new features, without altering frozen multilingual ground truth labels, and without benchmark squeezing.

### Final Milestone Decision
# **LOCK PRIORITY 6**

### Remediation Status Matrix

| Blocker | Description | Audit Status | Resolution Summary |
| :--- | :--- | :--- | :--- |
| **Blocker 1** | Duplicate Standard IDs in `standards.db` | **FIXED** | Deduplicated from 92 to exactly 90 canonical physical rows (0 duplicates). All 5 target standards preserved. Regenerated BM25 (90 docs) and semantic index (`(90, 384)`). 100% index-to-DB ID parity verified. 502-record expanded catalogue intact. |
| **Blocker 2** | Evaluator Methodology Separation | **FIXED** | Primary Top-1, Top-3, and MRR metrics strictly evaluate primary recommendations (`rec_res.recommendations`). Alternative standards discovery is segregated into explicit supplementary metrics (`alternative_discovery_recall` and `top3_with_alternatives_recall`). |
| **Blocker 3** | Non-Submersible Pump Boundary Gate | **FIXED** | Generic regex with negative lookbehinds `(?<!\bnon-)(?<!\bnon\s)(?<!\bnot\s)` and explicit non-submersible conflict detection. Rejects surface and non-submersible pumps from IS 8034 applicability. 7/7 pump boundary test cases pass. |
| **Blocker 4** | ML-TA-10 Ground Truth & Engine Discrepancy | **DOCUMENTED UNRESOLVED LIMITATION** | Neither benchmark nor engine modified. Ground truth remains `null`. Engine returns `IS 732 : 2019` on both Path A and Path B (100% cross-lingual agreement). Documented as an accepted domain adjudication discrepancy. |
| **Blocker 5** | Audit & Reporting Count Integrity | **FIXED** | Exact affected case counts recomputed directly from `reports/feasibility/multilingual_root_cause_results.json` (17 SUCCESS + 21 BENCHMARK_GT_ISSUE + 2 NORMALIZATION_FAILURE = 23 non-success cases). 90 database rows empirically validated. |

---

## 2. Detailed Blocker Verifications

### Blocker 1: Standard ID Normalization & Index Parity
- **Root Cause:** Dual ingestion pipelines ingested both hyphenated part strings (e.g. `IS-1180-Part-1-2014`) and parenthesized slugs (`IS-1180-(Part-1)-2014`).
- **Remediation:**
  - Upgraded `src/standards.py` to route all ingestion through `StandardIdentifierNormalizer.parse().canonical_id`.
  - Executed audited script [`scripts/remediate_duplicate_standards.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/scripts/remediate_duplicate_standards.py) retaining authoritative `BIS_OFFICIAL_CATALOGUE` records (`VERIFIED` status).
  - Updated `tests/test_milestone2.py` and `tests/test_decomposition.py` `setUpClass` methods to use pre-built databases rather than mutating production `standards.db`.
- **Integrity Proof:**
  - `data/standards/standards.db` physical row count: **90**
  - Distinct standard IDs: **90**
  - Duplicate standard IDs: **0**
  - Target standards present: `IS-1180-Part-1-2014`, `IS-15328-2003`, `IS-1786-2008`, `IS-7098-Part-2-2011`, `IS-8034-2018`.
  - BM25 documents: **90**
  - Semantic vector IDs: **90**
  - Semantic embeddings shape: **`(90, 384)`**
  - ID set & order parity across DB and indexes: **100.0%**
  - Expanded catalogue `data/catalogue/catalogue.db`: **502 records (intact and unchanged)**.

### Blocker 2: Evaluation Methodology Separation
- **Root Cause:** Prior commits checked `rec_res.alternatives` within `top3_hit` when primary recommendations were empty, changing the classical meaning of Top-3 recall.
- **Remediation:**
  - In `src/evaluate.py`, restored strict evaluation of primary recommendations for `top1_hit`, `top3_hit`, and `rr` (MRR).
  - Created dedicated, transparent supplementary metrics:
    - `alternative_discovery_recall`: Measures when ground truth is surfaced in alternatives despite primary abstention.
    - `top3_with_alternatives_recall`: Composite metric combining primary and alternative discoveries.
  - Adjusted `tests/test_milestone2.py` to assert both the pure primary Top-3 recall ($\ge 80.0\%$) and the composite Top-3 with alternatives ($\ge 85.0\%$).

### Blocker 3: Non-Submersible Pump Boundary Gate
- **Root Cause:** Regex `\b(?:submersible|borewell|deep\s*well|submerged)\b` in `src/applicability.py` treated `-` as a word boundary, incorrectly matching `submersible` inside `non-submersible`.
- **Remediation:**
  - Implemented explicit non-submersible detection: `re.search(r'\b(?:non[-\s]+submersible|not\s+submersible)\b', req_text_low)`.
  - Added negative lookbehinds to positive submersible detection: `(?<!\bnon-)(?<!\bnon\s)(?<!\bnot\s)(?:submersible|borewell|deep\s*well|submerged)`.
  - Raised `APPLICATION_CONFLICT` and rejected IS 8034 whenever non-submersible/surface pump specifications are detected.
- **Test Verification:**
  - 1. `"submersible pump"` $\rightarrow$ **APPLICABLE (True, 0 conflicts)**
  - 2. `"non-submersible pump"` $\rightarrow$ **NOT_APPLICABLE (False, APPLICATION_CONFLICT)**
  - 3. `"non submersible pump"` $\rightarrow$ **NOT_APPLICABLE (False, APPLICATION_CONFLICT)**
  - 4. `"non-submersible horizontal end suction centrifugal pump"` $\rightarrow$ **NOT_APPLICABLE (False, APPLICATION_CONFLICT)**
  - 5. `"borewell submersible pump"` $\rightarrow$ **APPLICABLE (True, 0 conflicts)**
  - 6. `"surface pump"` $\rightarrow$ **NOT_APPLICABLE (False, APPLICATION_CONFLICT)**
  - 7. `"Non-submersible horizontal end suction centrifugal water process pump"` $\rightarrow$ **NOT_APPLICABLE (False, APPLICATION_CONFLICT)**
  - Regression test permanently embedded in `tests/test_milestone9_applicability.py::test_non_submersible_pump_boundary`.

### Blocker 4: ML-TA-10 Benchmark Adjudication
- **Case Details:**
  - ID: `ML-TA-10`
  - Input (Tamil): `பழைய அலுவலக கட்டிடத்தில் பழுதடைந்த மின் வயரிங் மற்றும் எர்த் பிட் அமைப்பை சரிசெய்து ஆய்வு செய்தல்`
  - Canonical: `Inspection and testing of defective electrical wiring and earth pit system in old office building`
  - Ground Truth Label: `null` (Expected Abstention)
  - Engine Path A (Tamil): `IS 732 : 2019`
  - Engine Path B (English Reference): `IS 732 : 2019`
  - Cross-Path Agreement: `True` (100% consistent)
- **Adjudication Finding:**
  - The ground truth expected abstention because no specific product equipment was procured.
  - However, `IS 732:2019` is the mandatory national Code of Practice for Electrical Wiring Installations (including periodic inspection and testing).
  - In accordance with audit rules, **NO benchmark label was altered** and **NO artificial engine bypass was implemented**.
  - The case is formally designated as **BENCHMARK ADJUDICATION REQUIRED (Documented Non-Blocking Limitation)**.

### Blocker 5: Audit & Report Integrity
- Data extracted directly from `reports/feasibility/multilingual_root_cause_results.json`:
  - Total cases: **40**
  - SUCCESS: **17**
  - BENCHMARK_GROUND_TRUTH_ISSUE: **21**
  - NORMALIZATION_FAILURE: **2**
  - **Total Non-Success / Affected Cases: 23**
- The prior prose inconsistency stating "21 affected cases" has been corrected with mathematical and evidentiary proof.

---

## 3. Comprehensive Verification Summary

1. **Frozen Benchmark Invariant:**
   - Benchmark file: `dataset/ground_truth/multilingual_benchmark.json`
   - SHA-256 Hash: `938260e6386e7574bb647f4e95ea3cc05bc52dc24aa18b5c40ec294e0698e6a0` (Identical, unedited).
2. **Multilingual Benchmark Results (40 Cases):**
   - Language Detection Accuracy: **40/40 (100.0%)**
   - Path A == Path B Recommendation Consistency: **40/40 (100.0%)**
   - Top-3 Recommendation Consistency: **40/40 (100.0%)**
   - Abstention Consistency: **39/40 (97.5%)** (1 variance: ML-TA-10)
   - Entity Preservation Rate: **35/36 (97.2%)**
   - Safety Invariant (`candidate_standard == evidence_standard`): **40/40 (100.0%)**
3. **Ambiguity Test Suite:**
   - `pytest tests/test_ambiguity*.py`: **35 passed, 0 failed (100%)**
4. **Evidence Consistency Suite:**
   - `pytest tests/test_milestone10_evidence_consistency.py`: **7 passed, 0 failed (100%)**
5. **Applicability Suite:**
   - `pytest tests/test_milestone9_applicability.py`: **9 passed, 0 failed (100%)**
6. **Full Repository Test Suite:**
   - Command: `pytest tests/ -v`
   - Total Tests: **255**
   - Passed: **255**
   - Failed: **0**
   - Warnings: **1** (DeprecationWarning for `utcnow` in api server)
   - Execution Duration: **67.36s**
7. **Working Tree Status:**
   - `git status --short`: Empty (100% clean and committed).

---

## 4. Final Conclusion

All conditions required by the Final Decision Rule are satisfied:
1. Canonical database integrity passes (90 physical rows, 90 distinct IDs, 0 duplicates).
2. All BM25 and semantic vector indexes match the database in ID set, size, and ordering.
3. Evaluation methodology is strictly separated and frozen.
4. The pump negative-boundary safety gate is verified and protected by regression tests.
5. ML-TA-10 is honestly documented as an accepted non-blocking limitation without benchmark squeezing.
6. The ground truth benchmark remains strictly frozen with verified SHA-256 checksum.
7. Full repository test suite passes with 255/255 successful test executions.
8. Git working tree is completely clean and reproducible.

**FINAL DECISION: LOCK PRIORITY 6**
