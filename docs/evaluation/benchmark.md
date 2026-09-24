# Benchmark Evaluation: 20-Row Standard Dataset

This document details the evaluation protocol, frozen ground truth benchmark, retrieval ablation results, and negative control verification for **Tender Saathi**.

---

## 1. Overview & Evaluation Harness

The benchmark harness is implemented in [`src/evaluate.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/src/evaluate.py). It conducts an automated, objective evaluation of the recommendation pipeline against the frozen benchmark dataset located in [`dataset/ground_truth/ground_truth.csv`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/dataset/ground_truth/ground_truth.csv).

The benchmark verifies:
1. **Retrieval Accuracy**: Whether the correct Indian Standard (IS) is retrieved at Rank 1 (Top-1) and within the Top-3 candidates.
2. **Mean Reciprocal Rank (MRR)**: Average reciprocal rank across all test cases.
3. **Supersedence Detection Rate**: Percentage of superseded citations correctly caught and flagged.
4. **Ambiguity / Review Detection**: Recall and precision in identifying under-specified, ambiguous, or multi-candidate requirements.
5. **Negative Control Rejection Rate**: Verification that unrelated, absurd, or out-of-domain queries do not trigger false-positive recommendations.

---

## 2. Evaluation Results Summary

Results produced by executing `python3 -m src.evaluate` against the frozen ground truth:

| Mode | Top-1 Accuracy | Top-3 Recall | MRR | Avg Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Deterministic Rule-Based** | 85.0% | 90.0% | 0.875 | ~217 ms |
| **Pure-Python BM25** | 90.0% | 95.0% | 0.917 | ~236 ms |
| **Semantic (Dense Embeddings)** | 90.0% | 90.0% | 0.900 | ~214 ms |
| **Hybrid (BM25 + Semantic)** | 90.0% | 90.0% | 0.900 | ~755 ms |
| **Hybrid + Reranker (Production Pipeline)** | **90.0%** (18/20) | **90.0%** (18/20) | **0.900** | ~806 ms |

### Safety & Diagnostic Metrics
- **Supersedence Detection Rate**: **100.0%**
- **Ambiguity Detection Recall**: **100.0%** (All ambiguous or under-specified tender requirements are routed for human review)
- **Ambiguity Precision**: **14.3%** (Conservative safety bias: prefers flagging edge cases rather than silently recommending an ungrounded standard)
- **Candidate Standards Evaluated**: 90 verified BIS standards

---

## 3. Negative Control Benchmark (Out-of-Domain Rejection)

To ensure the recommender does not generate hallucinated matches when presented with out-of-domain, conflicting, or nonsensical input, 5 negative control test cases are evaluated:

| Case ID | Input Description | Observed Behavior | Status |
| :--- | :--- | :--- | :--- |
| `NEG-001` | Crane rail track vs. valve standard specification | Abstained (`None`) | ✅ REJECTED (SAFE) |
| `NEG-002` | Electrical cable vs. food standard requirement | Matched cable standard (`IS 7098 (Part 1) : 1988`), refused food standard | ✅ REJECTED (SAFE) |
| `NEG-003` | Water pump vs. ceramic tile requirement | Matched submersible pump (`IS 8034 : 2018`), refused tile standard | ✅ REJECTED (SAFE) |
| `NEG-004` | Structural steel vs. valve standard specification | Matched TMT rebars (`IS 1786 : 2008`), refused valve standard | ✅ REJECTED (SAFE) |
| `NEG-005` | Random / nonsensical engineering requirement | Abstained (`None`) | ✅ REJECTED (SAFE) |

### Negative Benchmark Metrics
- **Total Negative Cases**: 5
- **False-Positive Count**: 0
- **False-Positive Rate**: **0.0%**
- **Negative Rejection Rate**: **100.0% (5/5)**
- **Strict Abstention Rate**: 40.0% (2 cases where the requirement is completely unresolvable, while 3 cases safely isolated the genuine entity without falling for distractor standards)

---

## 4. How to Reproduce the Benchmark

Run the evaluation script from the repository root:

```bash
python3 -m src.evaluate
```

This runs:
1. Ablation comparison across all 5 retrieval configurations.
2. Ground-truth evaluation across all 20 rows.
3. Negative control suite.
4. Generates an evaluation CSV at `reports/feasibility/milestone2_evaluation.csv` and a markdown summary at `reports/feasibility/milestone2_evaluation_report.md`.
