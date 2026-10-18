# Phase 20: Evidence-to-Requirement Validation Audit — Implementation Plan

**Phase**: 20  
**Phase Name**: `20-evidence-to-requirement-validation`  
**Status**: Plan Formulated (Plan Phase)  
**Deliverable**: `docs/evaluation/PHASE20_EVIDENCE_VALIDATION_AUDIT.md`  

---

## Task 1: Semantics & Requirement Support Evaluation Subsystem
- **Files**: `src/corpus/semantics.py`, `src/corpus/retriever.py`
- **Actions**:
  1. Add `RequirementEvidenceSupportState` enum to `src/corpus/semantics.py`:
     - `FULLY_SUPPORTED`
     - `PARTIALLY_SUPPORTED`
     - `UNSUPPORTED`
     - `CONFLICTING`
     - `UNVERIFIED_COVERAGE`
  2. Implement `evaluate_requirement_support(requirement_text, passage_text, clause_identifier, components=None)` in `ClauseRetriever`:
     - Check for keyword/subject relevance between requirement and passage (rejection of irrelevant passages sharing clause numbers).
     - Extract technical parameters/ratings (e.g. kVA, W, voltage, temperature, material constraints) and check for direct numerical/envelope contradictions.
     - For compound requirements with component lists, check component-level support and assign `PARTIALLY_SUPPORTED` if not all material components are covered.
     - If no passage exists, return `UNVERIFIED_COVERAGE`.

---

## Task 2: Traceability & Cryptographic Integrity Hardening
- **Files**: `src/traceability.py`
- **Actions**:
  1. Add `requirement_evidence_support: str` to `TraceableEvidenceRecord`.
  2. In `build_trace_record`, compute or accept `requirement_evidence_support`.
  3. In `validate_record`, if `self.corpus_storage` is configured:
     - Verify `corpus_document_id` exists in `corpus_documents`.
     - Verify `corpus_file_sha256` matches the stored document file SHA-256.
     - Verify `clause_passage_hash` matches stored passage `content_hash`.
     - If extraction status is `QUALITY_FAILED` or `OCR_REQUIRED`, invalidate `is_normative_clause_verified = False` and add validation error.
     - If hash mismatch detected, invalidate `is_normative_clause_verified = False` and add validation error.

---

## Task 3: End-to-End Recommender, API & Frontend Integration
- **Files**: `src/recommend.py`, `api/server.py`, `frontend/src/types.ts`, `frontend/src/components/EvidenceDrawer.tsx`
- **Actions**:
  1. In `StandardsRecommender`, pass requirement text and component breakdown to evaluate requirement support state.
  2. Populate `clause_evidence["requirement_evidence_support"]` and `trace_record.requirement_evidence_support`.
  3. In `api/server.py`, serialize `requirement_evidence_support` in requirement and trace payloads.
  4. In `frontend/src/types.ts`, add `requirement_evidence_support?: string` to `ClauseEvidenceData` and `TraceRecord`.
  5. In `frontend/src/components/EvidenceDrawer.tsx`, add Requirement Coverage Badge in Section 14 with distinct visual styles (Supported = green, Partial = amber, Conflicting = red, Unverified = neutral).

---

## Task 4: Adversarial Test Suite, Regression Verification & Audit Report
- **Files**: `tests/test_evidence_validation_audit.py`, `docs/evaluation/PHASE20_EVIDENCE_VALIDATION_AUDIT.md`, `.planning/STATE.md`
- **Actions**:
  1. Create `tests/test_evidence_validation_audit.py` with 12 deterministic offline tests:
     - Correct standard/edition/clause, but irrelevant passage (`UNSUPPORTED`).
     - Incomplete support for compound requirement (`PARTIALLY_SUPPORTED`).
     - Conflicting rating/parameter in passage (`CONFLICTING`).
     - Missing clause identifier in eligible corpus (`UNVERIFIED_COVERAGE`).
     - Correct clause number in wrong edition (edition mismatch handling).
     - Similar clause numbers rejected without fuzzy matching.
     - Unknown clause identifier rejected without grounding.
     - Corrupted/failed extraction quality (`QUALITY_FAILED`) rejected.
     - Hash mismatch between trace record and corpus storage detected and rejected.
     - Storage unavailable or lookup failure cleanly handled without false claims.
     - Strict preservation of `is_official_source_authenticated = False` and `is_human_verified = False`.
     - Abstention and review-required decision preservation.
  2. Run full backend test suite (`pytest -q`).
  3. Run frontend production build (`npm run build --prefix frontend`).
  4. Run benchmark evaluation (`python3 scripts/evaluate_milestone12.py`) and verify ground-truth SHA-256 is unchanged.
  5. Generate comprehensive audit deliverable `docs/evaluation/PHASE20_EVIDENCE_VALIDATION_AUDIT.md`.
  6. Update `.planning/STATE.md` and refresh knowledge graph with `graphify update .`.
