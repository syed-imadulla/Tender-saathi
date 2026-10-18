# Phase 21 Plan: Evidence Support Engine Validation

## Goal
Audit, rigorously stress-test, and harden the requirement-to-evidence support engine (`evaluate_requirement_support`, `TraceableEvidenceValidator`, `ClauseRetriever`, `recommend_for_requirement`) across 18 independent adversarial scenarios. Ensure conservative boundaries, unit-conversions, inequality directions, tolerance/negation awareness, and multi-passage conflict handling.

## Tasks

### Task 1: Audit Implementation & Identify Edge-Case Defects
- Trace `evaluate_requirement_support()` in `src/corpus/retriever.py`.
- Trace `validate_record()` in `src/traceability.py`.
- Identify vulnerabilities:
  - Unit normalization gaps (kW vs W, kV vs V, kVA vs MVA).
  - Inequality direction (at least / minimum vs at most / maximum / shall not exceed).
  - Negation words (e.g. "without", "shall not be", "excluding").
  - Superficial clause similarity (`4.2` vs `4.20`).
  - Permissive keyword-only fallback to `FULLY_SUPPORTED`.

### Task 2: Implement Conservative Support Safeguards
- Update `evaluate_requirement_support()` in `src/corpus/retriever.py`:
  - Unit conversion utility for electrical & power ratings.
  - Inequality direction matching (min req vs max passage, max req vs max passage).
  - Explicit negation and exclusion detection.
  - Conservative support assignment: If technical parameters are specified in requirement but absent from passage, classify as `PARTIALLY_SUPPORTED` or flag for review, rather than assuming full compliance.
- Update `TraceableEvidenceValidator` in `src/traceability.py`:
  - Ensure missing metadata, unknown extraction status, or corrupted files cannot bypass validation.
  - Multiple candidate passages with conflicting indications escalate to `CONFLICTING`.
- Update `ClauseRetriever`:
  - Enforce strict clause identifier discrimination (`4.2` != `4.20` != `4.2.1`).

### Task 3: Build Independent 18-Case Adversarial Validation Matrix
- Create `tests/test_evidence_support_validation.py` testing:
  1. Irrelevant technical subject despite matching clause ID -> `UNSUPPORTED`.
  2. Matching subject but unsupported operating conditions -> `CONFLICTING`.
  3. Exact numeric match -> `FULLY_SUPPORTED`.
  4. Conflicting numeric rating -> `CONFLICTING`.
  5. Equivalent units (kW vs W) with valid conversion -> properly compared without false conflict.
  6. Inequality direction mismatch ("at least" vs "at most") -> `CONFLICTING` or review required.
  7. Tolerance and range mismatch -> detected.
  8. Negation and exclusions ("shall not have X" vs "shall have X") -> `CONFLICTING`.
  9. Indoor vs outdoor conditions -> `CONFLICTING`.
  10. Compound requirement with 1 supported and 1 unsupported -> `PARTIALLY_SUPPORTED`.
  11. Conflicting evidence across two passages -> escalated to `CONFLICTING`.
  12. Correct clause number in wrong edition -> `CORPUS_DOCUMENT_NOT_ELIGIBLE` & `UNVERIFIED_COVERAGE`.
  13. Missing or unverified extraction quality metadata -> `CORPUS_DOCUMENT_NOT_ELIGIBLE`.
  14. OCR-required or quality-failed source -> ineligible.
  15. Missing corpus storage / DB lookup failures -> handled gracefully as unverified.
  16. Tampered document or passage hashes -> rejected in trace validator.
  17. Superficially similar clause IDs (`4.2` vs `4.20`) -> strict rejection.
  18. Unparseable technical parameters -> conservative fallback (`UNVERIFIED_COVERAGE` or review required).

### Task 4: Full Verification & Report
- Run `pytest tests/test_evidence_support_validation.py -v`.
- Run Phase 18, 19, 20 evidence suites.
- Run complete test suite (`pytest -q`).
- Run frontend build (`npm run build --prefix frontend`).
- Run benchmark evaluation (`python3 scripts/evaluate_milestone12.py`) and verify active ground truth hash.
- Write `docs/evaluation/PHASE21_EVIDENCE_SUPPORT_VALIDATION.md` and update `.planning/STATE.md`.
