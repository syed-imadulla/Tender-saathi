# Tender Saathi — Phase 13 Step 1: Metric Audit & Population Grounding Report

**Audit Date**: 2026-10-18  
**Auditor**: GSD Phase 13 Lead Engineer & Evaluation Architect  
**Scope**: `src/evaluate.py`, `scripts/evaluate_milestone12.py`, `docs/evaluation/metric_definitions.md`, `reports/evaluation/evaluation_benchmark_m12.json`, `dataset/ground_truth/ground_truth.csv`.

---

## 1. Executive Summary

This independent audit examined the newly established multi-metric evaluation harness (Plan 12-02) against mathematical definitions, source code implementation, and actual benchmark datasets.

**Key Verdict**:
The multi-metric harness successfully separated retrieval hits from abstentions (eliminating the legacy hackathon flaw where abstentions were counted as Top-1 hits). However, the audit uncovered **5 specific population conflations, metric contradictions, and reporting ambiguities** that must be remediated to ensure that evaluation findings can safely inform future engineering decisions.

---

## 2. Forensic Audit of the 9 Verification Inquiries

### 1. How Answerable Cases are Identified and Counted
- **Current Logic**: `src/evaluate.py` line 517 filters `c.get("expected_decision") == "RECOMMEND"`.
- **Finding**: In the current 20-row `ground_truth.csv`, exactly 19 rows have `expected_decision == "RECOMMEND"`, and all 19 contain valid standard tokens. However, the code did not verify that `ground_truth_standards` is non-empty. If a malformed row claimed `RECOMMEND` without specifying a standard, it would artificially register an uncorrectable miss in the denominator.
- **Remediation**: Eligibility must strictly enforce `expected_decision == "RECOMMEND" and len(extract_standard_tokens(ground_truth_standards)) > 0`.

### 2. Why the Reported Top-1 Denominator is 19/19 While Dataset Contains 20 Rows
- **Finding**: Row 5 of `ground_truth.csv` (`T002-R002`: "Valve Replacement") is deliberately labeled `expected_decision: ABSTAIN_UNDER_SPECIFIED` with no applicable standard (`applicable_standard` is empty).
- **Correctness**: It is mathematically correct to exclude under-specified cases from retrieval accuracy denominators ($|\mathcal{A}| = 19$). Including them would reintroduce metric conflation.
- **Reporting Ambiguity**: The report stated "Total Evaluated Cases: 25" and "Total Answerable: 19" without an explicit bridge explaining the partition ($19 \text{ Answerable} + 1 \text{ Under-specified} + 5 \text{ Negative Controls} = 25$).

### 3 & 4. Population Conflation Between In-Domain Cases and Negative Controls in Coverage & Selective Risk
- **Current Logic**: `total_cases` (25) pools 20 tender cases and 5 synthetic negative controls into `eligible_count` for `coverage_percent` (15/25 = 60.0%) and `selective_risk_percent` (2/15 = 13.33%).
- **Critical Finding**:
  - Out of 15 covered recommendations:
    - 13 are answerable tender requirements (`is_top1_hit: True`, **0 errors**).
    - 2 are synthetic negative controls (`NEG-002`, `NEG-004`, both false recommendations).
  - Therefore, **the 13.33% selective risk was 100% caused by negative controls failing open-set rejection**. Among real in-domain procurement requirements, covered recommendation risk was **0.0%**!
  - Pooling synthetic out-of-domain queries into in-domain coverage distorts both figures.
- **Remediation**: Decouple into:
  1. `in_domain_selective_classification` ($N=20$): In-domain coverage and risk.
  2. `negative_control_rejection` ($N=5$): Out-of-domain false recommendation rate.
  3. `overall_selective_classification` ($N=25$): Pooled composite with explicit disclosure.

### 5. Dual Status Contradiction of `RECOMMEND_WITH_REVIEW`
- **Current Logic**:
  - `evaluate_case()` line 735 set `is_safe_abstention = True` if `rec_res.human_review_required` is True.
  - `compute_deconflated_metrics()` line 544 included `system_decision in ("RECOMMEND", "RECOMMEND_WITH_REVIEW")` in `covered_cases`.
- **Critical Finding**: `T001-R002` was marked with `system_decision: RECOMMEND_WITH_REVIEW`, which resulted in BOTH `is_safe_abstention: True` AND inclusion in `covered_cases`! A recommendation cannot be simultaneously an autonomous recommendation and an abstention.
- **Remediation**:
  - An abstention occurs ONLY when the engine refrains from proposing an ungrounded standard (`system_decision in ('REVIEW_REQUIRED', 'INSUFFICIENT_EVIDENCE', 'NO_RELIABLE_MATCH')` or `predicted_top1` is empty).
  - Stratify coverage into:
    - `autonomous_coverage` (`RECOMMEND`, 0 review flags)
    - `assisted_coverage` (`RECOMMEND_WITH_REVIEW`, candidate proposed with review advisory)
    - `total_coverage` (sum of both).

### 6. Accounting for Unsupported or Missing Candidates in Answerable Cases
- **Finding**: In `retrieval_answerable`, `ans_count` is the denominator ($|\mathcal{A}| = 19$). If an answerable case produces `None` or an irrelevant standard, `is_top1_hit = False` and it contributes $0$ to the numerator. It is therefore strictly penalized as an error in retrieval accuracy. In selective classification, abstaining on an answerable case reduces coverage rather than registering as a false positive recommendation. This is sound selective classification behavior.

### 7. Catalogue Currency Consistency and Evidence Overlap Matching Rules
- **Finding 1 (Status Consistency)**: Line 741 previously checked `if is_top1_hit and rec_res.status:`. If `rec_res.status` was missing or None, `status_consistent` defaulted to `True`. A missing status must register as an inconsistency or unverified status.
- **Finding 2 (Lexical Proxy Overlap)**: Set intersection of raw word tokens included English stop words ("clause", "1", "is", "of"). Removing stop words ensures the proxy measures substantive domain vocabulary overlap.

### 8. Per-Case Output Recomputability
- **Finding**: Verified. `per_case_results` in the JSON report contains 19 granular fields per case (`is_top1_hit`, `is_top3_hit`, `reciprocal_rank`, `system_decision`, `predicted_top1`, `status_consistent`, `evidence_proxy_score`, etc.). Every aggregate metric is 100% deterministically recomputable from this list alone.

### 9. Sector Breakdown Consistency
- **Finding**: Sectors with 0 answerable cases (e.g. `PROVISIONAL:NEGATIVE_CONTROL`) previously reported `top1_accuracy: 0.0%`, which incorrectly looked like a 0% retrieval failure rather than non-applicable. Sectors with 0 answerable cases must output `top1_accuracy: null`.

---

## 3. Confirmed Defects & Fix Plan

| Defect ID | Severity | File | Function | Confirmed Issue | Resolution |
|---|---|---|---|---|---|
| **DEF-01** | High | `src/evaluate.py` | `compute_deconflated_metrics` | Population conflation between in-domain tender cases and negative controls in Selective Classification | Separate in-domain selective classification ($N=20$) from negative-control open-set rejection ($N=5$) |
| **DEF-02** | High | `src/evaluate.py` | `evaluate_case` & `compute_deconflated_metrics` | Contradiction: `RECOMMEND_WITH_REVIEW` simultaneously marked `is_safe_abstention=True` and `covered=True` | Reserve `is_safe_abstention` strictly for withheld recommendations; report autonomous vs assisted coverage |
| **DEF-03** | Medium | `src/evaluate.py` | `evaluate_case` | Silent `status_consistent = True` fallback when recommender status is missing | Require non-empty status matching gold status |
| **DEF-04** | Medium | `src/evaluate.py` | `compute_deconflated_metrics` | Empty answerable sector reporting `0.0%` accuracy instead of `null` | Output `null` for accuracy/MRR when answerable count is 0 |
| **DEF-05** | High | `src/evaluate.py` | Reporting & Metrics | Evaluation claims do not stratify by adjudication status (`UNVERIFIED_BASELINE` vs `EXPERT_VERIFIED`) | Stratify metrics by adjudication status; report "Expert-Validated Accuracy" as N/A (0 verified cases) |

---

## 4. Verification Action
Regression unit tests covering DEF-01 through DEF-05 will be added to `tests/test_evaluation_metrics.py` before modifying `src/evaluate.py`.
