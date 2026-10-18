# Tender Saathi — Evaluation Metric Definitions & Mathematical Semantics

## 1. Overview & Core Philosophy

Tender Saathi assists procurement officers in identifying applicable Indian Standards (BIS) from tender specifications. In high-stakes public procurement, **recommending an incorrect standard is worse than safely requesting human review**. 

Legacy hackathon evaluation suffered from metric conflation: when a tender requirement was under-specified or ambiguous, a system abstention was counted as a "Top-1 Retrieval Hit", inflating accuracy numbers and obscuring true selective classification capability.

Phase 12 (Plan 12-02) introduces a **strictly decoupled, multi-metric evaluation harness**.

---

## 2. Mathematical Metric Definitions

### A. Retrieval Quality on Answerable Cases

Only test cases with a verified, defensible positive standard target belong in retrieval metrics.

#### 1. Top-1 Accuracy ($\text{Acc}_1$)
- **Formula**:
  $$\text{Top-1 Accuracy} = \frac{\sum_{i \in \mathcal{A}} \mathbb{I}(\text{Top-1}(\hat{y}_i) \in \mathcal{Y}_i)}{|\mathcal{A}|} \times 100\%$$
- **Eligibility ($\mathcal{A}$)**: Cases where `expected_decision == 'RECOMMEND'` and $\mathcal{Y}_i \neq \emptyset$.
- **Denominator**: Total answerable cases ($|\mathcal{A}|$).
- **Missing Predictions**: If the system abstains or returns `None`/`INSUFFICIENT_INFORMATION` for an answerable case, $\mathbb{I} = 0$.
- **Critical Non-Conflation Guarantee**: An abstention is **never** counted as a retrieval hit.

#### 2. Top-3 Recall / Accuracy ($\text{Rec}_3$)
- **Formula**:
  $$\text{Top-3 Accuracy} = \frac{\sum_{i \in \mathcal{A}} \mathbb{I}(\exists s \in \text{Top-3}(\hat{y}_i) \text{ s.t. } s \in \mathcal{Y}_i)}{|\mathcal{A}|} \times 100\%$$
- **Eligibility**: Same as Top-1.
- **Interpretation**: Measures whether the true standard is surfaced in the primary 3 recommendations.

#### 3. Mean Reciprocal Rank ($\text{MRR}$)
- **Formula**:
  $$\text{MRR} = \frac{1}{|\mathcal{A}|} \sum_{i \in \mathcal{A}} \frac{1}{\text{rank}_i}$$
  where $\text{rank}_i$ is the 1-indexed position of the first matching gold standard among primary recommendations, or $\frac{1}{\text{rank}_i} = 0$ if no match exists in recommendations.

---

### B. Selective Classification (Coverage & Risk)

Selective classification models the system's ability to refrain from predicting when confidence is insufficient.

#### 4. Recommendation Coverage ($\mathcal{C}$)
- **Formula**:
  $$\text{Coverage} = \frac{|\mathcal{D}|}{|\mathcal{E}|} \times 100\%$$
- **Eligibility ($\mathcal{E}$)**: All eligible evaluation queries ($N_{\text{total}}$).
- **Definitive Predictions ($\mathcal{D}$)**: Queries where the engine produced a definitive recommendation (`decision in ('RECOMMEND', 'RECOMMEND_WITH_REVIEW')` and `predicted_top1` is not empty or `INSUFFICIENT_INFORMATION`).
- **Interpretation**: Percentage of total queries the system accepts for autonomous recommendation without forcing manual review.

#### 5. Selective Risk / Recommendation Error ($\mathcal{R}$)
- **Formula**:
  $$\text{Selective Risk} = \frac{\sum_{i \in \mathcal{D}} \mathbb{I}(\text{Top-1}(\hat{y}_i) \notin \mathcal{Y}_i)}{|\mathcal{D}|} \times 100\%$$
- **Denominator**: Total covered cases ($|\mathcal{D}|$). If $|\mathcal{D}| = 0$, $\mathcal{R} = 0.0\%$.
- **Interpretation**: The empirical error rate among recommendations presented to the procurement officer. Optimal systems achieve high coverage with near-zero selective risk.

---

### C. Abstention & Rejection Quality

#### 6. Under-Specification Abstention Recall ($\text{Recall}_{\text{abstain}}$)
- **Formula**:
  $$\text{Recall}_{\text{abstain}} = \frac{\sum_{i \in \mathcal{U}} \mathbb{I}(\text{is\_safe\_abstention}_i)}{|\mathcal{U}|} \times 100\%$$
- **Eligibility ($\mathcal{U}$)**: Cases where `expected_decision == 'ABSTAIN_UNDER_SPECIFIED'`.
- **Criterion**: The engine returned `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`, `NO_RELIABLE_MATCH`, or flagged `human_review_required: True` without assigning an ungrounded standard.
- **Interpretation**: Measures whether the engine reliably catches vague, incomplete requirements (e.g. "Valve Replacement" without line size/pressure).

#### 7. Negative-Control False Recommendation Rate ($\text{FPR}_{\text{neg}}$)
- **Formula**:
  $$\text{False Recommendation Rate} = \frac{\sum_{i \in \mathcal{N}} \mathbb{I}(\text{decision}_i \in \text{Definitive})}{|\mathcal{N}|} \times 100\%$$
- **Eligibility ($\mathcal{N}$)**: Negative controls where `expected_decision in ('REJECT_INELIGIBLE', 'NEGATIVE_CONTROL')` or domain-mismatched requirements.
- **Interpretation**: Rate of dangerous hallucinations where an irrelevant standard is recommended. Optimal target is 0.0%.

---

### D. Evidence Grounding & Disclosures

#### 8. Catalogue Status Consistency
- **Formula**:
  $$\text{Consistency} = \frac{\sum_{i \in \mathcal{H}} \mathbb{I}(\text{status}(\hat{y}_i) == \text{status}(y_i))}{|\mathcal{H}|} \times 100\%$$
- **Eligibility ($\mathcal{H}$)**: Correct Top-1 hits.
- **Interpretation**: Confirms that recommended standards reflect active legal status and match gold catalogue currency.

#### 9. Clause-Level Grounding Status
- **Status**: `NOT_EVALUABLE_NO_FULL_TEXT_CORPUS`
- **Technical Limitation Disclosure**:
  > *Tender Saathi's catalogue database (`standards.db`) stores standard numbers, titles, scopes, and committee metadata, but does not index full digital clause-by-clause standard texts for all 19,000+ BIS standards. Full clause-level grounding precision cannot be claimed as an absolute metric without a certified clause text corpus.*
- **Transparent Proxy**: A lexical overlap score between recommendation rationale and ground-truth `evidence_reference` is provided as `proxy_evidence_reference_overlap_percent`.

---

### E. Sector Stratification

Metrics ($\text{Acc}_1$, $\text{Rec}_3$, $\text{MRR}$) are stratified by `procurement_sector` (e.g., `PROVISIONAL:CIVIL_WORKS`, `PROVISIONAL:ELECTRICAL`, `PROVISIONAL:MECHANICAL`, `PROVISIONAL:CATERING`).

- **Constraint**: Sector tags derived from tender metadata rather than expert taxonomy are visibly tagged with `PROVISIONAL:`.
- **Sample Size Reporting**: Sample size $n$ is reported for every sub-group.
