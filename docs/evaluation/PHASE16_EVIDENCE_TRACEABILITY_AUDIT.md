# Tender Saathi — Phase 16: Evidence Traceability & Recommendation Verification Audit

**Status**: COMPLETED  
**Date**: 2026-10-18  
**Scope**: Standards Recommendation Traceability, Stored Passage Verification, Operational Decision Tracking, and Ground-Truth Integrity  
**Target Benchmark**: 20 Active Ground Truth Cases (`dataset/ground_truth/ground_truth.csv`)  
**Standards Catalogue**: 90 Registered Indian Standards (`data/standards/standards.db`)  
**Active Ground Truth SHA-256**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Unmodified)  

---

## 1. Executive Summary

Phase 16 establishes an end-to-end, deterministic evidence chain connecting every standards recommendation to:
1. The original procurement tender requirement (and decomposed sub-requirements).
2. The retrieved Indian Standard identity and official BIS catalogue metadata.
3. The exact supporting source passage and its cryptographic content hash (SHA-256).
4. The operational decisions across retrieval, applicability gates, ambiguity detection, and critic review.
5. An explicit evidence completeness and human verification status.

The phase enforces strict non-negotiable safeguards:
- **No Ranking Changes**: Retrieval weights, confidence thresholds, and abstention rules remain 100% unchanged.
- **No Ground Truth Mutations**: Active ground truth labels and files remain untouched.
- **Anti-Falsification Invariant**: Machine-generated similarity scores and LLM rationales are explicitly distinguished from exact source passages and human verification. No machine-generated field is ever silently upgraded to human-verified.
- **Safety Gate Precedence**: Ineligible/rejected candidates are permanently marked as ineligible. Recommendations requiring human review cannot masquerade as fully verified standards.

---

## 2. Evidence Traceability Architecture

The traceability framework is implemented in `src/traceability.py` and integrated into `src/recommend.py`, `api/server.py`, and the frontend web UI.

### 2.1 Core Distinctions
The framework cleanly delineates evidence into distinct, strictly typed categories (`EvidenceType`):
1. **`EXACT_SOURCE_PASSAGE`**: Grounded, verifiable text from the stored official scope or foreword in `data/standards/standards.db`, verified via substring matching and SHA-256 hashing.
2. **`CATALOGUE_METADATA`**: High-level catalogue attributes (standard title, department, publication year, lifecycle status) without clause-level text.
3. **`RETRIEVAL_DERIVED_SIGNAL`**: BM25 scores, semantic embedding similarity, cross-encoder reranker scores, and rank positions.
4. **`MODEL_EXPLANATION`**: Synthesized LLM explanations and reasoning paragraphs.
5. **`HUMAN_VERIFIED_EXPERT`**: Qualified human engineer adjudication (currently 0/20 in the unadjudicated benchmark).
6. **`UNAVAILABLE`**: Explicit missing state when no supporting evidence exists.

### 2.2 Traceable Record Schema (`TraceableEvidenceRecord`)
Every recommendation carries a frozen, backward-compatible record containing:
- **Requirement Linkage**: `requirement_id`, `requirement_text`, `sub_requirement_id`, `sub_requirement_text`.
- **Standard Details**: `standard_number`, `official_title`, `standard_year`, `lifecycle_status`.
- **Retrieval Metrics**: `retrieval_method`, `relevance_score`, `rank_position`.
- **Source Passage Provenance**: `supporting_passage`, `evidence_type`, `evidence_source`, `document_id`, `source_url`, `content_hash`.
- **Operational Decisions**: `applicability_decision`, `applicability_rejection_reasons`, `ambiguity_state`, `competing_standards`, `critic_decision`, `final_system_decision`, `human_review_required`.
- **Deterministic Flags**: `catalogue_entry_exists`, `passage_text_verified`, `lifecycle_verified`, `evidence_completeness`.

---

## 3. Measured Audit Metrics

The metrics below were computed directly against the active SQLite standards catalogue (`data/standards/standards.db`) and the 20 benchmark test cases in `dataset/ground_truth/ground_truth.csv`.

### 3.1 Standards Catalogue Baseline
| Metric | Count | Total Eligible (Denominator) | Percentage / Status |
| :--- | :---: | :---: | :---: |
| Registered Catalogue Standards | 90 | 90 | 100.0% |
| Catalogue Entries with Usable Scope Evidence | 90 | 90 | 100.0% |
| Catalogue Entries with Source Provenance Recorded | 90 | 90 | 100.0% |
| Catalogue Entries with Recorded Source URL | 39 | 90 | 43.3% |
| Active Standards in Catalogue | 75 | 90 | 83.3% |
| Withdrawn / Superseded Standards in Catalogue | 15 | 90 | 16.7% |
| Catalogue Entries with Missing Scope | 0 | 90 | 0.0% |

### 3.2 Recommendation Traceability Audit (20 Benchmark Cases)
| Audit Metric | Count | Total Evaluated (Denominator) | Percentage / Status |
| :--- | :---: | :---: | :---: |
| Recommendations with Traceable Source Passages | 17 | 20 | 85.0% |
| Recommendations Relying on Catalogue Metadata Alone | 0 | 20 | 0.0% |
| Recommendations with Missing or Unresolved Provenance | 0 | 20 | 0.0% |
| Recommendations Requiring Human Review | 20 | 20 | 100.0% |
| Positive Cases with Validated Stored Scope Passages | 17 | 17 | 100.0% |
| Negative Controls Correctly Refraining from Stored Passages | 3 | 3 | 100.0% |
| Compound Requirements in Benchmark | 17 | 20 | 85.0% |
| Compound Cases with Incomplete Component Evidence | 3 | 20 | 15.0% |
| Records whose Evidence or Lifecycle Cannot be Verified | 0 | 20 | 0.0% |
| Recommendations Falsely Marked as Human-Verified | 0 | 20 | 0.0% (Zero Tolerance) |

---

## 4. Analysis of Audit Findings

### 4.1 Traceable Scope vs. Clause-Level Text
- **What is operational**: All 90 standards in `data/standards/standards.db` store authoritative scope passages extracted during BIS catalogue ingestion. For all 17 positive recommendations, the top recommended standard's scope text was located in the database, cryptographically hashed via SHA-256, and attached to the trace record.
- **What is NOT yet operational (Honest Limitation)**: Full-text standards documents (PDF bodies, individual clauses, sub-clause numbers, and test tables) are not stored in `standards.db`. The system does **not** manufacture clause numbers or quote unrecorded paragraphs. Where clause-level text is absent, the evidence type is accurately documented as catalogue-scope rather than full-text grounded.

### 4.2 Why 100% of Benchmark Recommendations Require Human Review
- **Negative Controls (3 cases: T002-R002, T004-R002, T010-R001)**: The system correctly abstained (`NO_RELIABLE_MATCH` / `UNKNOWN_STANDARD`), appropriately flagging `human_review_required = True`.
- **Positive Recommendations (17 cases)**: 100% of the positive benchmark cases represent complex real-world tender specifications with multiple subcomponents (e.g., HT XLPE cables, distribution transformers, DG sets, centrifugal pumps). Under Phase 9 decomposition, when subcomponents carry technical constraints (such as installation codes, testing requirements, or specialized accessories), the safety gate designates `human_review_required = True`.
- **Safety Invariant**: Under Section 3 rules, `TraceableEvidenceValidator` enforces that any recommendation where `human_review_required = True` must have `evidence_completeness = HUMAN_REVIEW_REQUIRED`, preventing automated systems from claiming unassisted certification.

### 4.3 Missing Provenance and Source URLs
- Out of 90 catalogue entries, 39 entries (43.3%) record an explicit BIS portal or official URL. The remaining 51 entries (56.7%) originate from authoritative offline BIS gazette/standards compendia where no online URL was logged during initial ingestion.
- The system leaves `source_url = None` for these 51 entries without fabricating web addresses.

---

## 5. Regression & Integration Testing Verification

### 5.1 Unit & Deterministic Regression Tests
Added test suite: `tests/test_evidence_traceability.py`
- Test 1: Recommendation with valid stored scope passage (Passage verified, SHA-256 hash valid, completeness set to `SUPPORTING_EVIDENCE_AVAILABLE`).
- Test 2: Recommendation with missing supporting passage (Correctly transitions to `CATALOGUE_METADATA_ONLY`).
- Test 3: Recommendation with fabricated/mismatched passage text (Correctly caught by validator; passage flagged unverified).
- Test 4: Recommendation referencing unknown standard identifier (Correctly marked `UNKNOWN_STANDARD`, passage unverified).
- Test 5: Missing or unverified edition/lifecycle status (Flagged with warning, lifecycle marked unverified).
- Test 6: Compound requirement with incomplete component evidence (Flagged with warning).
- Test 7: Recommendation requiring human review (Completeness strictly overridden to `HUMAN_REVIEW_REQUIRED`).
- Test 8: Rejected candidate incorrectly represented as selected (Completeness strictly overridden to `REJECTED_INELIGIBLE`).
- Test 9: Anti-falsification guard (Failsafe prevents machine-generated evidence from claiming human verification).
- Test 10: Backward compatibility with existing API response schemas (Preserves all legacy fields while exposing `trace_record` and `component_trace_records`).

### 5.2 Test Execution Results
- `pytest tests/test_evidence_traceability.py`: **10 passed** in 4.64s.
- `pytest tests/`: **578 passed** in 37.19s (100% offline, zero network calls, zero external API dependencies).
- Frontend Build: `npm run build` completed cleanly in 978ms (`dist/index.html` built without errors).

---

## 6. Ground-Truth Governance Assertion

- **Active Ground Truth File**: `dataset/ground_truth/ground_truth.csv`
- **Pre-Phase SHA-256**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Post-Phase SHA-256**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Status**: **IDENTICAL / UNTOUCHED**. Zero ground-truth records were modified or promoted to expert-verified.

---

## 7. Recommended Next Step

**Milestone 17 Prerequisite**: Ingest full-text PDF standards and test protocols for high-priority electrical and civil standards into `data/standards/corpus/` to enable authentic clause-level and sub-clause passage grounding prior to expert adjudication.
