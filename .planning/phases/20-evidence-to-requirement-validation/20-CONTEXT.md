# Phase 20: Evidence-to-Requirement Validation Audit — Context & Decisions

**Phase**: 20  
**Phase Name**: `20-evidence-to-requirement-validation`  
**Status**: Context Formulated (Discuss Phase)  
**Objective**: Determine whether retrieved normative standards passages actually support the tender requirements they are presented alongside, distinguishing passage existence from structural clause identity, requirement relevance, compound coverage, and engineering applicability.

---

## 1. Locked Decisions & Core Invariants

### 1.1 Decoupling Verification Claims
We strictly decouple five distinct claims that must never be conflated:
1. **Passage Existence in Corpus**: The raw text exists in an extracted page stored in `data/standards/corpus.db`.
2. **Clause Identity Grounding**: An explicit clause number (e.g. `Clause 4.2`) matches a structurally extracted heading in the correct document and edition (`is_normative_clause_verified = True`).
3. **Requirement Evidence Support**: The passage text substantively supports the technical specifications, ratings, or material conditions of the requirement (`requirement_evidence_support` state).
4. **Compound Requirement Coverage**: In requirements with multiple decomposed components, all components must have supporting evidence for full coverage. If only one component is supported, the top-level status is `PARTIALLY_SUPPORTED`.
5. **Human Expert Adjudication**: Qualified domain engineer sign-off (`is_human_verified`). Must NEVER be inferred or set by automated retrieval.

### 1.2 Five Discrete Requirement Evidence Support States
We introduce an explicit enum `RequirementEvidenceSupportState` in `src/corpus/semantics.py`:
- `FULLY_SUPPORTED`: Authentic normative passage(s) support all material conditions of the requirement (or all components of a compound requirement).
- `PARTIALLY_SUPPORTED`: Authentic passage supports one or more components/conditions, but other material components lack normative clause evidence.
- `UNSUPPORTED`: A clause passage was retrieved (or cited), but its content does not support the requirement's technical conditions.
- `CONFLICTING`: The retrieved normative passage directly contradicts or excludes a material requirement condition (e.g., conflicting rating, phase, or operating envelope).
- `UNVERIFIED_COVERAGE`: No normative clause passage is available in the corpus; requirement relies strictly on catalogue scope/metadata or pending manual review.

### 1.3 Cryptographic Integrity & Quality Gating
In `TraceableEvidenceValidator.validate_record`:
- When `corpus_storage` is present, check `corpus_document_id`, `corpus_file_sha256`, and `clause_passage_hash` against persisted SQLite records.
- If hashes mismatch, or document status is `OCR_REQUIRED` or `QUALITY_FAILED`, invalidate clause verification (`is_normative_clause_verified = False`) and emit a `validation_error`.
- Ensure absent database, corrupt SQLite files, or lookup errors never produce a positive verification claim.

### 1.4 Anti-Falsification Invariants
- `is_official_source_authenticated`: Permanently `False` for all local files.
- `is_human_verified`: Permanently `False` for machine recommendations.
- Zero threshold tuning or weight changes to "game" retrieval benchmarks.
- Ground truth file `dataset/ground_truth/ground_truth.csv` and its SHA-256 (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`) remain strictly immutable.

---

## 2. Target Files & Touchpoints

1. `src/corpus/semantics.py`: Define `RequirementEvidenceSupportState` enum and descriptive mappings.
2. `src/corpus/retriever.py`: Implement deterministic requirement-to-evidence validation (`evaluate_requirement_support`) checking rating/parameter alignment and conflict detection.
3. `src/traceability.py`: Update `TraceableEvidenceRecord` with `requirement_evidence_support` and compound support summary; update `validate_record` with corpus hash and quality verification.
4. `src/recommend.py`: Connect requirement support evaluation to single and compound recommendations.
5. `api/server.py`: Serialize `requirement_evidence_support` in REST responses.
6. `frontend/src/types.ts`: Update TypeScript definitions with `requirement_evidence_support`.
7. `frontend/src/components/EvidenceDrawer.tsx`: Update Section 14 to display requirement support badges and clear disclaimers.
8. `tests/test_evidence_validation_audit.py`: Comprehensive deterministic offline adversarial test suite.
9. `docs/evaluation/PHASE20_EVIDENCE_VALIDATION_AUDIT.md`: Final evaluation audit report.
