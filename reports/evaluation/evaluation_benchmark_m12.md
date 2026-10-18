# Tender Saathi — Phase 12 Comprehensive Evaluation Report

> [!IMPORTANT]
> **Ground Truth Status Disclosure**: Benchmark ground_truth.csv rows are UNVERIFIED_BASELINE and require formal domain expert panel adjudication (Phase 13).

- **Evaluation Timestamp**: `2026-10-18T13:56:40.023255+00:00`
- **Dataset Path**: `dataset/ground_truth/ground_truth.csv`
- **Dataset SHA-256**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Evaluation Harness**: `TenderSaathi-M12-MultiMetric`

---

## 1. Executive Summary: Decoupled Benchmark Metrics

| Metric Dimension | Measured Value | Denominator | Interpretation |
| :--- | :--- | :--- | :--- |
| **Top-1 Accuracy (Answerable)** | **89.5%** | 17 / 19 | Evaluated strictly on answerable queries. Abstentions are excluded. |
| **Top-3 Accuracy (Answerable)** | **89.5%** | 17 / 19 | Gold standard present in Top-3 primary recommendations. |
| **Mean Reciprocal Rank (MRR)** | **0.895** | 19 queries | Harmonic mean of retrieval ranks on answerable queries. |
| **In-Domain Coverage** | **65.0%** | 13 / 20 | Coverage strictly on in-domain procurement requirements ($N=20$). |
| **In-Domain Selective Risk** | **0.0%** | 0 / 13 | Error rate among in-domain recommendations (0.0% = zero wrong recs). |
| **Pooled Recommendation Coverage** | **56.0%** | 14 / 25 | Overall coverage including synthetic negative controls ($N=25$). |
| **Pooled Selective Risk** | **7.1%** | 1 / 14 | Overall error rate among covered queries (dominated by negative controls). |
| **Under-Spec Abstention Recall** | **100.0%** | 1 / 1 | Vague requirements where system safely abstained/flagged review. |
| **Negative False Rec Rate** | **0.0%** | 0 / 5 | Ineligible/unrelated queries falsely recommended (Safety Target: 0.0%). |
| **Autonomous Recommendations (`RECOMMEND`)** | **44.0%** | 11 / 25 | Queries receiving autonomous recommendation without human review flag. |
| **Assisted Recommendations (`RECOMMEND_WITH_REVIEW`)** | **12.0%** | 3 / 25 | Primary standard recommended, but flagged for engineering review. |
| **Withheld Recommendations (Abstentions)** | **44.0%** | 11 / 25 | Recommendations safely withheld due to incomplete or out-of-domain scope. |

---

## 2. Adjudication Status Stratification (Expert Verification Gate)

> [!NOTE]
> Claims of expert-verified accuracy require formal panel sign-off (human_verified: TRUE). All current baseline cases are UNVERIFIED_BASELINE.

| Adjudication Cohort | Total Sample | Answerable Queries | Top-1 Accuracy | Expert Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **Expert-Verified (`EXPERT_VERIFIED`)** | 0 | 0 | N/A (Awaiting Phase 13) | ⏳ 0% Formally Signed Off |
| **Unverified Baseline (`UNVERIFIED_BASELINE`)** | 20 | 19 | 89.47% | ⚠️ Active Benchmark Baseline |
| **Machine-Predicted Staging (`MACHINE_PREDICTED`)** | 0 | 0 | N/A | 🧪 Staged in `candidates_staging.csv` |

---

## 3. Evidence Grounding & Limitations Disclosure

- **Catalogue Currency Consistency**: **100.0%** (17 Top-1 hits audited against active BIS status).
- **Clause-Level Grounding Status**: `NOT_EVALUABLE_NO_FULL_TEXT_CORPUS`
- **Limitation Note**: Tender Saathi's catalogue database stores standard numbers, titles, scopes, and committee metadata, but does not index full digital clause-by-clause standard texts for all 19,000+ BIS standards. Full clause-level grounding precision cannot be claimed as an absolute metric without a certified clause text corpus.
- **Proxy Reference Overlap**: `53.7%` (lexical overlap against ground-truth evidence snippets).

---

## 4. Sector-Stratified Performance Breakdown

| Sector Tag | Sample Size | Answerable | Top-1 Accuracy | Top-3 Accuracy | MRR |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PROVISIONAL:CATERING` | 1 | 1 | 100.0% | 100.0% | 1.000 |
| `PROVISIONAL:CIVIL_WORKS` | 8 | 8 | 87.5% | 87.5% | 0.875 |
| `PROVISIONAL:ELECTRICAL` | 9 | 9 | 88.9% | 88.9% | 0.889 |
| `PROVISIONAL:MECHANICAL` | 2 | 1 | 100.0% | 100.0% | 1.000 |
| `PROVISIONAL:NEGATIVE_CONTROL` | 5 | 0 | N/A | N/A | N/A |

---

## 5. Case-by-Case Outcome Manifest

| Req ID | Sector | Expected | System Decision | Top-1 Predicted | Hit? | Abstain? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `T001-R002` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `RECOMMEND_WITH_REVIEW` | **IS 15905 : 2011** | ✅ YES | - |
| `T001-R003` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `RECOMMEND` | **IS 15622 : 2017** | ✅ YES | - |
| `T001-R004` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `RECOMMEND` | **IS 781 : 1984** | ✅ YES | - |
| `T002-R002` | `PROVISIONAL:MECHANICAL` | `ABSTAIN_UNDER_SPECIFIED` | `REVIEW_REQUIRED` | **None (Abstained)** | ❌ NO | 🛡️ SAFE |
| `T002-R003` | `PROVISIONAL:MECHANICAL` | `RECOMMEND` | `RECOMMEND` | **IS 6392 : 1971** | ✅ YES | - |
| `T003-R001` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `RECOMMEND` | **IS/IEC 61439-3 : 2012** | ✅ YES | - |
| `T004-R002` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `REVIEW_REQUIRED` | **None (Abstained)** | ❌ NO | 🛡️ SAFE |
| `T004-R005` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `RECOMMEND` | **IS 5039 : 1983** | ✅ YES | - |
| `T005-R001` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `REVIEW_REQUIRED` | **IS 3043 : 2018** | ✅ YES | 🛡️ SAFE |
| `T006-R001` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `RECOMMEND` | **IS 16088 : 2016** | ✅ YES | - |
| `T007-R003` | `PROVISIONAL:CATERING` | `RECOMMEND` | `REVIEW_REQUIRED` | **IS 2491 : 2013** | ✅ YES | 🛡️ SAFE |
| `T009-R001` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `RECOMMEND_WITH_REVIEW` | **IS 732 : 2019** | ✅ YES | - |
| `T010-R001` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `REVIEW_REQUIRED` | **None (Abstained)** | ❌ NO | 🛡️ SAFE |
| `T011-R001` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `REVIEW_REQUIRED` | **IS 7098 (Part 1) : 1988** | ✅ YES | 🛡️ SAFE |
| `T012-R002` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `RECOMMEND` | **IS 1661 : 1972** | ✅ YES | - |
| `T012-R003` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `RECOMMEND` | **IS 1239 (Part 2) : 1992** | ✅ YES | - |
| `T013-R002` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `RECOMMEND` | **IS/IEC 61800-2 : 2015** | ✅ YES | - |
| `T013-R003` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `RECOMMEND` | **IS 14164 : 2008** | ✅ YES | - |
| `T014-R002` | `PROVISIONAL:ELECTRICAL` | `RECOMMEND` | `REVIEW_REQUIRED` | **IS/IEC 60034-1 : 2017** | ✅ YES | 🛡️ SAFE |
| `T020-R001` | `PROVISIONAL:CIVIL_WORKS` | `RECOMMEND` | `RECOMMEND` | **IS 15778 : 2007** | ✅ YES | - |
| `NEG-001` | `PROVISIONAL:NEGATIVE_CONTROL` | `REJECT_INELIGIBLE` | `NO_RELIABLE_MATCH` | **None (Abstained)** | ❌ NO | 🛡️ SAFE |
| `NEG-002` | `PROVISIONAL:NEGATIVE_CONTROL` | `REJECT_INELIGIBLE` | `RECOMMEND_WITH_REVIEW` | **IS 7098 (Part 1) : 1988** | ❌ NO | - |
| `NEG-003` | `PROVISIONAL:NEGATIVE_CONTROL` | `REJECT_INELIGIBLE` | `REVIEW_REQUIRED` | **IS 8034 : 2018** | ❌ NO | 🛡️ SAFE |
| `NEG-004` | `PROVISIONAL:NEGATIVE_CONTROL` | `REJECT_INELIGIBLE` | `NO_RELIABLE_MATCH` | **None (Abstained)** | ❌ NO | 🛡️ SAFE |
| `NEG-005` | `PROVISIONAL:NEGATIVE_CONTROL` | `REJECT_INELIGIBLE` | `NO_RELIABLE_MATCH` | **None (Abstained)** | ❌ NO | 🛡️ SAFE |
