# PRIORITY 6 FINAL AUDIT & BENCHMARK ADJUDICATION REPORT
## Milestone: Priority 6E — Final Audit Integrity & Benchmark Adjudication
**Date**: 2026-09-12  
**System**: TenderSaathi (SIH26108)  
**Audit Type**: Strict Independent Verification & Ground-Truth Integrity Audit  
**Final Milestone Recommendation**: **DO NOT LOCK PRIORITY 6**

---

## 1. Executive Summary

Priority 6E conducted an exhaustive, independent audit of TenderSaathi's Priority 6 deliverables, focusing on the integrity of reported metrics from Priority 6D, underlying SQLite database storage, index generation, evaluation methodologies, test modifications, and ground-truth benchmark adjudication.

### Core Audit Verdict:
1. **Critical Issue A (90 vs. 92 Records)**: **DATABASE INTEGRITY ISSUE & REPORTING BUG CONFIRMED**.
   - `data/standards/standards.db` contains **92 records**, not 90 as stated in the Priority 6D audit report.
   - Independent SQL analysis identified duplicate entries for two multi-part standards: `IS 1180 (Part 1)` and `IS 7098 (Part 2)`. Each standard exists under two distinct primary keys (`IS-1180-Part-1-2014` vs. `IS-1180-(Part-1)-2014`, and `IS-7098-Part-2-2011` vs. `IS-7098-(Part-2)-2011`) due to inconsistent slug normalization between `standards.xlsx` ingestion and automated catalogue insertion scripts.
2. **Critical Issue B ("21" vs. 23 Affected Cases)**: **REPORTING BUG CONFIRMED**.
   - The Priority 6B authoritative root-cause dataset contains **23 non-SUCCESS cases** (21 classified as `BENCHMARK_GROUND_TRUTH_ISSUE` due to missing catalogue coverage, plus 2 classified as `NORMALIZATION_FAILURE` for `ML-TA-08` and `ML-MX-07`).
   - The Priority 6D audit report table correctly listed all **23 cases**, but descriptive prose incorrectly claimed "21 affected cases".
3. **40-Case Multilingual Benchmark (Fresh Execution)**:
   - Ground-truth file `dataset/ground_truth/multilingual_benchmark.json` remained unmodified (verified by SHA-256: `938260e6386e7574bb647f4e95ea3cc05bc52dc24aa18b5c40ec294e0698e6a0`).
   - Fresh execution demonstrated:
     - **Language Detection Accuracy**: 40/40 (100.0%)
     - **Path A == Path B Agreement**: 40/40 (100.0%)
     - **Candidate == Evidence Invariant**: 40/40 (100.0%)
     - **Expected Standard Match**: 39/40 (97.5%)
     - **Safe Abstention**: 3/4 clean abstentions (75.0%)
4. **Case ML-TA-10 Status**: **BENCHMARK ADJUDICATION REQUIRED**.
   - Tamil input and English reference both recommend `IS 732 : 2019` (*Code of practice for electrical wiring installations*).
   - Ground truth specifies `null` (safe abstention). While `IS 732` is technically valid CPWD grounding, it diverges from the benchmark label. Under strict rules, this requires human panel adjudication before benchmark freezing.
5. **Code & Test Modification Review**:
   - `src/evaluate.py`: **EVALUATION METHODOLOGY CHANGED**. Lines 99–106 were altered to inspect `rec_res.alternatives` for Top-3 recall when `recommendations` are emptied by ambiguity abstention.
   - `tests/test_milestone10_evidence_consistency.py`: Clarification to `"1.1 kV PVC insulated electric cable"` was confirmed legitimate because adding `IS 7098 (Part 2)` caused unrated queries to trigger inter-part voltage ambiguity.
   - `src/applicability.py`: Boundary gates are generic without hardcoded IDs, but a regex limitation was identified where `\b(?:submersible...)\b` matches the hyphenated word `"non-submersible"`, bypassing pump type rejection on hyphenated inputs.
6. **Full Test Suite Regression**:
   - **254 passed, 0 failed, 1 warning in 76.17s**.

**Final Verdict**: **DO NOT LOCK PRIORITY 6** until duplicate primary keys in `standards.db` are normalized via a formal database migration, the evaluation methodology in `src/evaluate.py` is reconciled, the regex boundary for pumps is hardened, and `ML-TA-10` is adjudicated by domain committee.

---

## 2. Exact Git State

The repository was frozen and audited at the following exact git commit state:

| Parameter | Value |
|---|---|
| **Branch** | `main` |
| **HEAD Commit** | `cba2f965c5c1ad8938ce079fb4f6b80924fcec5a` |
| **Commit Message** | `chore: remove generated review reports, update catalogue and benchmark data, and add priority 6d expansion audit artifacts` |
| **Working Tree Status** | Clean (0 modified / 0 untracked files prior to 6E audit execution) |

---

## 3. Database Audit & Critical Issue A: 90 vs. 92 Distinct Records

### Independent SQL Execution:
```sql
SELECT COUNT(*) FROM standards;                     -- 92
SELECT COUNT(DISTINCT standard_id) FROM standards; -- 92
SELECT COUNT(DISTINCT standard_number) FROM standards; -- 63
```

### Duplicate Primary Key Analysis:
`SELECT standard_id, COUNT(*) FROM standards GROUP BY standard_id HAVING COUNT(*) > 1;`
- **Result**: `[]` (0 duplicate primary keys).

### Duplicate Standard Number Analysis:
`SELECT standard_number, COUNT(*) FROM standards GROUP BY standard_number HAVING COUNT(*) > 1;`
- **Multi-Part Standards**: `IS 101` (10), `IS 302` (7), `SP 18` (6), `IS 9694` (3), `IS 404` (2), `IS 6283` (2).
- **Multi-Revision Standards**: `IS 14333` (2: 1996 vs 2022), `IS 2491` (2: 2013 vs 2024), `IS 432` (2: 1982 vs 2026).
- **True Duplicate Records (Slug Mismatches)**:
  1. `IS 1180 (Part 1)`:
     - Record 1: `standard_id = 'IS-1180-Part-1-2014'`, `source = 'BIS_OFFICIAL_CATALOGUE'`, `year = 2014`
     - Record 2: `standard_id = 'IS-1180-(Part-1)-2014'`, `source = 'CURATED_EXCEL_REPO'`, `year = 2014`
  2. `IS 7098 (Part 2)`:
     - Record 1: `standard_id = 'IS-7098-Part-2-2011'`, `source = 'BIS_OFFICIAL_CATALOGUE'`, `year = 2011`
     - Record 2: `standard_id = 'IS-7098-(Part-2)-2011'`, `source = 'CURATED_EXCEL_REPO'`, `year = 2011`

### Root Cause of Issue A:
- `standards.xlsx` ingestion generated slugs containing literal parentheses (e.g. `IS-1180-(Part-1)-2014`).
- Direct catalogue expansion ingestion used `StandardIdentifierNormalizer.parse()`, generating standardized alphanumeric slugs without parentheses (e.g. `IS-1180-Part-1-2014`).
- Because SQLite enforces uniqueness on `standard_id`, both variations were inserted as independent rows.
- The previous audit report stated 90 rows (assuming baseline 85 + 5 = 90) without verifying the physical SQLite row count.
- **Audit Finding**: **DATABASE INTEGRITY ISSUE & REPORTING BUG**. Records must NOT be silently deleted without an audited migration script.

---

## 4. Critical Issue B: "21 Affected Cases" vs. Actual Count

Independent reconstruction from `reports/feasibility/multilingual_root_cause_results.json` (Priority 6B baseline):

| Classification Category | Count | Description |
|---|---|---|
| **SUCCESS** | 17 | Perfect ground-truth and A/B agreement |
| **BENCHMARK_GROUND_TRUTH_ISSUE** | 21 | Target standard missing from prototype catalogue |
| **NORMALIZATION_FAILURE** | 2 | Historic A/B divergences (`ML-TA-08` and `ML-MX-07`) |
| **Total Non-SUCCESS (Affected Cases)** | **23** | Cases requiring remediation in Priority 6D |
| **Total Benchmark Cases** | **40** | Complete multilingual benchmark |

### Finding:
- The exact number of affected cases is **23** (not 21).
- The Priority 6D table correctly displayed 23 rows (`ML-HI-01, 04, 05, 06, 07`; `ML-KN-03, 04, 05, 06, 07`; `ML-TA-03, 04, 05, 06, 08, 09, 10`; `ML-MX-01, 04, 05, 06, 07, 10`).
- The textual heading in Priority 6D was inaccurate in referring to "21 affected cases". This is adjudicated as a **REPORTING BUG**.

---

## 5. Prototype vs. Expanded Catalogue Distinction

| Metric | Prototype Benchmark DB (`standards.db`) | Expanded Production DB (`catalogue.db`) | Audit Parity |
|---|---|---|---|
| **File Path** | `data/standards/standards.db` | `data/catalogue/catalogue.db` | Verified |
| **Physical Row Count** | **92 rows** | **502 rows** | Verified |
| **Distinct `standard_id`** | 92 | 502 | Verified |
| **Distinct `standard_number`** | 63 | 501 | Verified |
| **BM25 Document Count** | 92 documents | 502 documents | Parity PASS |
| **Dense Embedding Shape** | `(92, 384)` | `(502, 384)` | Parity PASS |
| **Target Standards Present** | All 5 present (2 with redundant slugs) | All 5 present (clean single records) | Verified |

---

## 6. Verification of the Five Target Standards

| Standard Number | Year | Canonical Title | Status | In `standards.db` | In `catalogue.db` | Provenance |
|---|---|---|---|---|---|---|
| **IS 1180 (Part 1)** | 2014 | Outdoor Type Oil Immersed Distribution Transformers up to and Including 2500 kVA, 33 kV - Specification - Part 1 Mineral Oil Immersed | Active | 2 records (`IS-1180-Part-1-2014`, `IS-1180-(Part-1)-2014`) | 1 record (`IS-1180-Part-1-2014`) | GOI Ministry QCO Gazette / BIS Official Catalogue |
| **IS 15328** | 2003 | Plastics Piping Systems for Non-Pressure Underground Drainage and Sewerage - Unplasticized Poly(Vinyl Chloride) (PVC-U) Pipes - Specification | Active | 1 record (`IS-15328-2003`) | 1 record (`IS-15328-2003`) | Official GoI Specification / Secondary Provenance |
| **IS 1786** | 2008 | High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - Specification | Active | 1 record (`IS-1786-2008`) | 1 record (`IS-1786-2008`) | GOI Ministry QCO Gazette / Primary Provenance |
| **IS 7098 (Part 2)** | 2011 | Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables - Part 2: For Working Voltages from 3.3 kV up to and Including 33 kV | Active | 2 records (`IS-7098-Part-2-2011`, `IS-7098-(Part-2)-2011`) | 1 record (`IS-7098-Part-2-2011`) | GOI Ministry QCO Gazette / Primary Provenance |
| **IS 8034** | 2018 | Submersible Pumpsets - Specification | Active | 1 record (`IS-8034-2018`) | 1 record (`IS-8034-2018`) | GOI Ministry QCO Gazette / Primary Provenance |

---

## 7. Index Integrity Audit

All 4 search indexes were validated against raw SQLite storage:

1. **`data/standards/bm25_index.json`**:
   - Total Documents: **92**
   - Doc IDs match `standards.db` `standard_id` set: **TRUE (100% parity)**
2. **`data/standards/semantic_embeddings.npy`**:
   - Shape: `(92, 384)`
   - Embedding Model: `all-MiniLM-L6-v2`
   - Doc IDs in `semantic_doc_ids.json`: **92** (Matches BM25 doc IDs in identical order)
3. **`data/catalogue/bm25_index.json`**:
   - Total Documents: **502**
   - Doc IDs match `catalogue.db` `standard_id` set: **TRUE (100% parity)**
4. **`data/catalogue/semantic_embeddings.npy`**:
   - Shape: `(502, 384)`
   - Embedding Model: `all-MiniLM-L6-v2`
   - Doc IDs in `semantic_doc_ids.json`: **502** (Matches BM25 doc IDs in identical order)

---

## 8. Audit of Code Changes Made in Priority 6D

### A. `src/evaluate.py`
- **Diff**:
  ```python
  candidates_to_check = [r.standard_number for r in rec_res.recommendations[:5]]
  if not candidates_to_check and rec_res.alternatives:
      candidates_to_check = rec_res.alternatives[:5]
  ```
- **Audit Findings**:
  1. *Why changed?* To allow evaluation scripts to measure whether the correct standard was present in `alternatives` when ambiguity abstention cleared primary recommendations.
  2. *Was it required?* No, Priority 6D did not require changing evaluator mechanics.
  3. *Impact*: **Evaluation methodology changed**. Ambiguous queries where `recommendations` was intentionally empty now receive positive Top-3 scoring from alternatives. Old and new Top-3 metrics cannot be compared directly.

### B. `tests/test_milestone10_evidence_consistency.py`
- **Diff**:
  ```python
  - text = "PVC insulated electric cable"
  + text = "1.1 kV PVC insulated electric cable"
  ```
- **Audit Findings**:
  1. *Why changed?* Prior to 6D, only Part 1 existed. When Part 2 was added, an unrated query triggered inter-part ambiguity between Part 1 (<= 1100 V) and Part 2 (3.3 kV to 33 kV), resulting in safe abstention (`candidate_standard: None`).
  2. *Legitimacy*: This is a legitimate clarification for `test_04` because `test_04` tests evidence drawer cross-contamination (ensuring cable queries do not mention CPVC or valves). Unrated cable ambiguity is separately and rigorously tested in `tests/test_ambiguity_v2.py`.

### C. `src/applicability.py`
- **Diff**: Added 5 product boundary gates and added `"without"` to `GENERIC_STOPWORDS`.
- **Audit Findings**:
  1. Gates are generic and rely on technical attributes (voltage rating tiers, reinforcement steel grades, fluid applications, transformer equipment types, submersible vs surface pump types).
  2. **No benchmark IDs** (`ML-HI`, `ML-KN`, `ML-TA`, `ML-MX`) exist anywhere in `src/applicability.py`.
  3. **Identified Regex Limitation**: In the pump gate:
     ```python
     has_submersible = bool(re.search(r'\b(?:submersible|borewell|deep\s*well|submerged)\b', req_text_low))
     ```
     Because `\b` considers a hyphen as a boundary, `"non-submersible"` matches `submersible`. Thus, literal `"non-submersible process water pump"` does not trigger pump rejection, whereas descriptive non-submersible queries (e.g. `"horizontal end suction centrifugal pump"`) correctly trigger rejection.

---

## 9. Independent Execution of Section 13 Wrong-Candidate Safety Tests

| Test | Input Requirement | Plausible Wrong Standard | Applicability Gate Result | Final Candidate | Final Evidence | Human Review | Critic Decision | Rejection Reason / Conflict Flag |
|---|---|---|---|---|---|---|---|---|
| **A** | `11 kV XLPE insulated heavy duty power cable` | `IS 7098 (Part 1)` | **NOT_APPLICABLE** | `IS 7098 (Part 2) : 2011` | `IS 7098 (Part 2) : 2011` | False | `RECOMMEND` | `VOLTAGE_CONFLICT: 11 kV / HT cable exceeds IS 7098 Part 1 maximum voltage rating (1.1 kV / 1100 V)` |
| **B** | `High strength Fe 500D TMT reinforcement steel bars` | `IS 432` | **NOT_APPLICABLE** | `IS 1786 : 2008` | `IS 1786 : 2008` | False | `RECOMMEND` | `GRADE_OR_PROCESS_CONFLICT: Fe 500D / TMT vs mild steel IS 432` |
| **C** | `110 mm PVC-U pipe for underground drainage and sewerage system` | `IS 4985` | **NOT_APPLICABLE** | `IS 15328 : 2003` | `IS 15328 : 2003` | False | `RECOMMEND` | `APPLICATION_CONFLICT: underground drainage/sewerage vs potable water supply IS 4985` |
| **D** | `11 kV 500 kVA outdoor oil immersed step-down distribution transformer` | `IS 5039` | **NOT_APPLICABLE** | `IS 1180 (Part 1) : 2014` | `IS 1180 (Part 1) : 2014` | False | `RECOMMEND` | `EQUIPMENT_MISMATCH: distribution transformer vs distribution pillar IS 5039` |
| **E** | `Non-submersible horizontal end suction centrifugal water process pump` | `IS 8034` | **APPLICABLE (Boundary Regex Leak)** | `IS 8034 : 2018` | `IS 8034 : 2018` | True | `REVIEW_REQUIRED` | Input matched `\b(?:submersible)\b` across hyphen. Flagged `REVIEW_REQUIRED` due to missing Head (H) and Flow (Q) engineering parameters. |

---

## 10. Fresh 40-Case Multilingual Benchmark Results

Benchmark file SHA-256 before run: `938260e6386e7574bb647f4e95ea3cc05bc52dc24aa18b5c40ec294e0698e6a0`  
Benchmark file SHA-256 after run: `938260e6386e7574bb647f4e95ea3cc05bc52dc24aa18b5c40ec294e0698e6a0`  
**File integrity: UNCHANGED**.

| Metric | Fresh Execution Count | Fresh Percentage | Status |
|---|---|---|---|
| **Total Test Cases** | 40 | 100.0% | Complete suite |
| **Language Detection Accuracy** | 40/40 | 100.0% | Perfect script identification |
| **Path A == Path B Agreement** | 40/40 | 100.0% | Perfect A/B parity |
| **Expected Standard Match** | 39/40 | 97.5% | 1 ground-truth discrepancy (`ML-TA-10`) |
| **Candidate == Evidence Invariant** | 40/40 | 100.0% | Zero hallucination across all positive cases |
| **Entity Preservation Rate** | 35/36 | 97.2% | High entity retention |
| **Safe Abstention Accuracy** | 3/4 | 75.0% | `ML-HI-10`, `ML-KN-10`, `ML-MX-10` cleanly abstained |

---

## 11. Case ML-TA-10 Adjudication Analysis

- **Tamil Input**: `மின் வயரிங் மற்றும் பாதுகாப்பு சாதனங்கள் பொருத்துதல்`
- **English Reference**: `Installation of electrical wiring and safety equipment without ratings or specifications`
- **Ground Truth Expected**: `null` (Note: "Vague Tamil requirement, safe abstention required")
- **Engine Recommendation (Both Paths)**: `IS 732 : 2019` (*Code of practice for electrical wiring installations*)
- **Technical Analysis**:
  1. *Is IS 732 applicable?* Yes. In CPWD Electrical Specifications (Part I Internal), any general tender for building electrical wiring is governed by `IS 732` for installation code of practice regardless of equipment ratings.
  2. *Is the requirement sufficiently specific?* For product standards (such as wires or switches), it lacks ratings. For code-of-practice installation standards, `IS 732` is directly applicable.
  3. *Adjudication Decision*: **DO NOT MODIFY ENGINE; DO NOT MODIFY BENCHMARK**. Status remains **BENCHMARK ADJUDICATION REQUIRED** pending final review committee consensus.

---

## 12. Analysis of IS 8034 `REVIEW_REQUIRED` Cases

For cases `ML-HI-06`, `ML-KN-05`, `ML-TA-05`, and `ML-MX-05`:
- **Engine Result**: `Candidate: IS 8034 : 2018`, `Decision: REVIEW_REQUIRED`, `human_review_required: True`.
- **Reason**: The Specification Completeness Gate in `src/critic.py` identified that the tender requirement omitted key operational engineering parameters:
  - Discharge / Flow Rate ($Q$)
  - Total Dynamic Head ($H$)
  - Prime Mover / Motor Coupling
- **Audit Conclusion**: This is **EXPECTED ENGINEERING BEHAVIOUR**. Flagging `REVIEW_REQUIRED` protects procurement officers from releasing tenders without critical operating specifications.

---

## 13. Reassessment of Historic A/B Divergences (`ML-TA-08`, `ML-MX-07`)

In Priority 6B, `ML-TA-08` and `ML-MX-07` diverged:
- Path A selected `IS 14333 : 2022` (HDPE sewer pipes).
- Path B selected `IS 15905 : 2011` (Cast iron drainage pipes).

### Safe Audit Finding:
> After `IS 15328 : 2003` was added to `standards.db`, both cases converged to `IS 15328 : 2003` on Path A and Path B without modifying multilingual normalization code.
> We do not claim that catalogue coverage was mathematically proven to be the exclusive causal mechanism in theoretical isolation, but empirically, adding the missing standard was sufficient to achieve 100% A/B agreement.

---

## 14. Full Pytest Regression Breakdown

The full repository test suite was executed:
```
================== 254 passed, 1 warning in 76.17s (0:01:16) ===================
```

| Test Suite File | Test Count | Status | Domain Verified |
|---|---|---|---|
| `tests/test_ambiguity.py` | 19 | PASS | Priority 5 Ambiguity States & Invariants |
| `tests/test_ambiguity_v2.py` | 12 | PASS | Ambiguity V2 Real-world Competitor Rejection |
| `tests/test_ambiguity_v2_1.py` | 4 | PASS | Discriminator Resolution & Unseen Domains |
| `tests/test_decomposition.py` | 7 | PASS | NLP Requirement Decomposition |
| `tests/test_explicit_citation.py` | 2 | PASS | Direct Standard Extraction & Bypass |
| `tests/test_hybrid_retrieval.py` | 9 | PASS | BM25 + Dense Semantic Fusion |
| `tests/test_milestone10_dependencies.py` | 8 | PASS | Cross-standard Normative References |
| `tests/test_milestone10_evidence_consistency.py` | 7 | PASS | Evidence Drawer Invariants & No Cross-Contamination |
| `tests/test_milestone10_gap_detection.py` | 12 | PASS | Missing Standard & Gap Detection |
| `tests/test_milestone11_catalogue.py` | 10 | PASS | Expanded Catalogue Ingestion & Normalization |
| `tests/test_milestone11_regulatory.py` | 8 | PASS | QCO Gazette & CRS Classification |
| `tests/test_milestone2.py` | 7 | PASS | End-to-End Extraction on 20 PDF Tenders |
| `tests/test_milestone3_critic.py` | 14 | PASS | Multi-criteria Critic & Completeness Gates |
| `tests/test_milestone5_graph.py` | 14 | PASS | Knowledge Graph & Relationship Traversal |
| `tests/test_milestone6_audit.py` | 25 | PASS | Decision Audit Logs & Traceability |
| `tests/test_milestone7_report.py` | 20 | PASS | Executive HTML/PDF Report Generation |
| `tests/test_milestone8_ai.py` | 26 | PASS | Gemini AI Provider & Structured Extraction |
| `tests/test_milestone9_applicability.py` | 8 | PASS | Domain Boundary & Applicability Gating |
| `tests/test_multilingual.py` | 34 | PASS | Script Detection, Lexicon Normalization, Latency |
| `tests/test_standards.py` | 8 | PASS | Prototype Standard Repository Queries |
| **Total** | **254** | **100% PASS** | **Zero Failures, 1 Warning (utcnow deprecation)** |

---

## 15. Security & Reproducibility Check

- **Credential Scan**: Verified zero API keys, secrets, tokens, or bearer headers in git diff.
- **Source Reproducibility**: All benchmark files, catalogue artifacts, and database records are deterministically reproducible.

---

## 16. Blocking Issues for Milestone Lock

The following 5 blocking issues prevent locking Priority 6 at this time:

1. **Database Integrity Issue (Slug Redundancy in `standards.db`)**:
   `standards.db` contains 92 rows instead of 90 due to two duplicate records (`IS 1180 (Part 1)` and `IS 7098 (Part 2)`). The slug formatting divergence (`Part-1` vs `(Part-1)`) must be resolved via an audited database migration script.
2. **Reporting Inconsistency in Priority 6D**:
   The Priority 6D report incorrectly claimed 90 rows / 90 vectors, and loosely stated "21 affected cases" when the actual count is 23.
3. **Evaluation Methodology Alteration in `src/evaluate.py`**:
   `src/evaluate.py` altered the definition of Top-3 recall by falling back to `alternatives` for ambiguous/abstained queries.
4. **Boundary Gate Regex Boundary Limitation**:
   In `src/applicability.py`, `\b(?:submersible...)\b` matches `"non-submersible"` on the hyphen boundary, leaking through pump boundary rejection on hyphenated queries.
5. **Pending Adjudication on `ML-TA-10`**:
   Ground truth specifies `null`, while the recommendation engine outputs `IS 732 : 2019`. This requires formal committee resolution.

---

## 17. Final Lock Recommendation

### Decision:
# **DO NOT LOCK PRIORITY 6**

### Condition for Unlocking:
Priority 6 may be locked once:
1. A migration script consolidates duplicate slugs in `data/standards/standards.db` and aligns BM25 and semantic embeddings to exactly 90 clean records.
2. `src/evaluate.py` is reverted or formalized with clear separation between primary recommendation recall and alternative discovery recall.
3. The pump type boundary regex in `src/applicability.py` is patched to handle negative pre-modifiers (e.g. `(?<!non-)submersible`).
4. A formal domain review committee provides written adjudication for case `ML-TA-10`.
