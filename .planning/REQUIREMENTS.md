# Tender Saathi — Phase 12 Requirements Document

**Milestone**: Phase 12 — Benchmark Transparency, Ground-Truth Quality, and Source Provenance  
**Document**: `REQUIREMENTS.md`  
**Governing Principle**: *"Data integrity precedes model tuning. Never fabricate evaluation claims or expert verification."*

---

## 1. Requirements Overview & Traceability Matrix

| Req ID | Category | Description | Primary Target | Plan ID |
|---|---|---|---|---|
| **BENCH-01** | Schema | Extend `dataset/ground_truth/ground_truth.csv` schema with non-breaking optional fields (`source_document`, `procurement_sector`, `expected_decision`, `adjudication_status`, `reviewer_role`, `reviewed_at`) preserving all existing 18 columns. | `dataset/ground_truth/ground_truth.csv` | 12-01 |
| **BENCH-02** | Provenance | Bind every benchmark test case to its verifiable source document path (e.g. `tenders/raw/*.pdf`), page number, and original extract snippet. | `dataset/ground_truth/ground_truth.csv` | 12-01 |
| **BENCH-03** | Label Integrity | Enforce strict segregation between `MACHINE_PREDICTED`, `UNADJUDICATED`, and `EXPERT_VERIFIED`. All existing 20 rows explicitly retained as unadjudicated / non-expert-verified. | `dataset/ground_truth/ground_truth.csv` | 12-01 |
| **EVAL-01** | Evaluation | De-conflate selective abstention (`candidate=None` on unresolvable tenders) from Top-1 retrieval accuracy in `src/evaluate.py`. Compute distinct `Precision@Coverage` and `Selective Classification Risk`. | `src/evaluate.py` | 12-02 |
| **EVAL-02** | Evaluation | Introduce Evidence Grounding Score checking whether retrieved recommendations match authoritative clause references (`evidence_reference`) and legal status (`standard_status`). | `src/evaluate.py` | 12-02 |
| **EVAL-03** | Evaluation | Add Sector Coverage breakdown across public procurement domains (CPWD Civil, Electrical Works, Nuclear/Process Piping, Water Supply & Sewerage, Sports Infrastructure). | `src/evaluate.py` | 12-02 |
| **EXP-01** | Expansion | Build candidate expansion pipeline ingesting raw procurement tenders from `tenders/raw/`, auto-generating candidate evaluation rows labeled `MACHINE_PREDICTED` with `human_verified=FALSE`. | `scripts/expand_ground_truth.py` | 12-03 |
| **GATE-01** | Governance | Automated regression test asserting that no ground-truth row can have `human_verified: TRUE` without genuine reviewer metadata (`reviewer_role`, `reviewed_at`, and `evidence_reference`). | `tests/test_ground_truth_integrity.py` | 12-03 |

---

## 2. Invariants & Scope Fences

1. **Zero Scoring Changes**: Do NOT alter BM25 parameters, dense embedding models (`all-MiniLM-L6-v2`), cross-encoder reranker weights, successor standard scoring heuristics (`AUDIT-03`), or ambiguity margins (`AUDIT-05`) in this milestone.
2. **Zero Falsification**: Never mark any test case as `human_verified: TRUE` without genuine domain expert review.
3. **Backward Compatibility**: Any script or test reading `dataset/ground_truth/ground_truth.csv` using the original 18-column format must continue to function without modification.
4. **Deterministic Testing**: All new evaluation scripts, verification tests, and expansion tools must operate 100% offline under the network isolation guard established in Phase 2A.
