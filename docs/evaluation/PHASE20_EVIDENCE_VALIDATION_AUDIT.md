# Tender Saathi — Phase 20: Evidence-to-Requirement Validation Audit Report

**Date**: 2026-10-18  
**Scope**: Evidence Validity, Requirement Coverage, and Verification Boundaries Audit  
**Phase State**: Completed  
**Status**: All 629 backend tests passing (including 12 deterministic adversarial tests), frontend production build cleanly verified, zero-regression on active benchmark metrics.

---

## 1. Executive Summary

Phase 18 built the controlled normative standards corpus ingestion subsystem, and Phase 19 integrated local clause-level passage retrieval into recommendations and trace records. However, an architectural audit revealed a critical semantic conflation:

> **The Conflation**: An authentic passage matching a clause identifier in an eligible corpus document proved only that the passage exists under that clause number (`is_normative_clause_verified = True`). It did **not** prove that the passage supported the specific engineering requirements of the tender, that compound requirement clauses covered all components, or that operating envelope constraints were satisfied.

Phase 20 resolves this gap without arbitrary score-tuning, threshold tweaking, or LLM hallucination:
1. Introduced explicit semantic support states (`RequirementEvidenceSupportState`): `FULLY_SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONFLICTING`, `UNVERIFIED_COVERAGE`.
2. Implemented deterministic requirement-support validation in `src/corpus/retriever.py` detecting operating envelope contradictions, rating parameter violations, compound requirement coverage, and semantic keyword relevance.
3. Hardened `TraceableEvidenceValidator` in `src/traceability.py` to cryptographically audit candidate documents and passages against persisted SQLite storage records, rejecting verification upon hash tampering or quality failure (`QUALITY_FAILED`, `OCR_REQUIRED`).
4. Enforced safety escalation in `src/recommend.py`: detecting `CONFLICTING` evidence immediately forces `human_review_required = True` and transitions recommendations to `ASSISTED_REVIEW_REQUIRED`.
5. Created a 12-case deterministic offline adversarial test suite (`tests/test_evidence_validation_audit.py`) validating every edge case with synthetic fixtures.
6. Updated frontend evidence drawer presentation (`EvidenceDrawer.tsx`) with distinct visual indicators for requirement support.

---

## 2. Systematic Audit of Evidence Claims

| Evidence Claim / Flag | Exact Condition Setting It | Checked Against Persisted DB? | What It Actually Proves | What UI / API Must NOT Claim |
|---|---|---|---|---|
| `is_catalogue_verified` | Matched against `standards.db` | Yes (SQLite) | Standard metadata exists in local catalogue | Does not prove official live BIS endorsement |
| `is_passage_verified_in_source` | Exact substring match in catalogue scope | Yes (SQLite) | Scope text exists in local SQLite entry | Does not prove clause-level mandate |
| `is_normative_clause_verified` | Grounded passage match in `corpus.db` with matching hashes | Yes (SQLite + SHA-256) | Authentic passage exists under that clause | Does not guarantee requirement satisfaction |
| `requirement_evidence_support` | Deterministic parameter & envelope evaluation | Yes (Passage + Tender Req) | Technical alignment & completeness of evidence | Does not substitute human PE approval |
| `is_official_source_authenticated` | Strictly hardcoded `False` | N/A (Guarded) | N/A | Strictly prevented from claiming live portal auth |
| `is_human_verified` | Strictly hardcoded `False` | N/A (Guarded) | N/A | Strictly prevented from claiming human sign-off |

---

## 3. The 5 Evidence Support States

Under `RequirementEvidenceSupportState` (`src/corpus/semantics.py`):

1. **`FULLY_SUPPORTED`**: The retrieved normative passage directly addresses the technical subject of the requirement and satisfies all specified parameter boundaries without operating contradictions.
2. **`PARTIALLY_SUPPORTED`**: For a compound tender requirement comprising multiple technical sub-components, the retrieved passage only covers a subset of components. Full requirement coverage cannot be claimed.
3. **`UNSUPPORTED`**: The clause passage was retrieved from the standard, but contains no substantive parameter or technical overlap with the tender requirement (e.g. Painting clause retrieved for a Transformer Loss requirement).
4. **`CONFLICTING`**: The retrieved normative passage explicitly contradicts the operating envelope (e.g. Indoor apparatus specified for an Outdoor requirement) or rating limits of the tender requirement. Forces `human_review_required = True`.
5. **`UNVERIFIED_COVERAGE`**: No normative clause passage was located in an eligible corpus document, or the standard was matched at catalogue metadata level only.

---

## 4. Deterministic Adversarial Test Suite

Implemented in `tests/test_evidence_validation_audit.py` (12 offline, synthetic tests, 0 live LLM calls, 0 network requests):

1. **Scenario 1 — Irrelevant Passage**: Painting clause (Cl. 10.1) retrieved for Loss requirement -> Grounded, but marked `UNSUPPORTED`.
2. **Scenario 2 — Incomplete Compound Coverage**: Loss clause covers only 1 of 2 compound parts (Losses + Impulse) -> Marked `PARTIALLY_SUPPORTED`.
3. **Scenario 3 — Operating Envelope Conflict**: Indoor-only apparatus clause retrieved for outdoor pole-mounted transformer -> Flagged as `CONFLICTING`.
4. **Scenario 4 — Absent Clause Identifier**: Clause 99.99 missing from corpus -> `CLAUSE_EVIDENCE_NOT_FOUND` & `UNVERIFIED_COVERAGE`.
5. **Scenario 5 — Wrong Edition Isolation**: Querying 1989 edition for 2014 clause -> `CLAUSE_EVIDENCE_NOT_FOUND` & `UNVERIFIED_COVERAGE`.
6. **Scenario 6 — Precision Matching (No Fuzzy Matching)**: Querying Clause 4.2 does not match Clause 4.2.1; querying 4.2.1 does not return 4.2.
7. **Scenario 7 — Unknown Clause Section**: `CLAUSE_UNKNOWN` sections reject structural grounding (`is_grounded = False`).
8. **Scenario 8 — Corrupted Extraction Quality**: Ingestion status `QUALITY_FAILED` or `OCR_REQUIRED` triggers `CORPUS_DOCUMENT_NOT_ELIGIBLE`.
9. **Scenario 9 — Cryptographic Hash Mismatch**: Tampered passage or file SHA-256 is detected in `TraceableEvidenceValidator` and invalidates `is_normative_clause_verified`.
10. **Scenario 10 — Corpus Subsystem Unavailable**: Missing DB or `storage=None` cleanly handled as `CORPUS_NOT_AVAILABLE` without false positives.
11. **Scenario 11 — Anti-Falsification Invariants**: Machine automated recommendations strictly maintain `is_official_source_authenticated = False` and `is_human_verified = False`.
12. **Scenario 12 — Safety Escalation on Conflicting Evidence**: Conflicting evidence forces `human_review_required = True` and demotes decision to `ASSISTED_REVIEW_REQUIRED`.

---

## 5. Verification & Benchmark Results

### A. Test Execution
```bash
pytest tests/test_corpus_ingestion.py tests/test_clause_evidence_integration.py tests/test_evidence_validation_audit.py -v
# 40 passed in 5.93s

pytest -q
# 629 passed in 61.66s
```

### B. Frontend Production Build
```bash
npm run build --prefix frontend
# ✓ built in 1.05s (zero TypeScript errors, zero bundling errors)
```

### C. Benchmark Harness Evaluation
```bash
python3 scripts/evaluate_milestone12.py
```
- **Dataset SHA-256**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Bit-for-bit unchanged)
- **Top-1 Retrieval Accuracy**: `89.5%` (17 / 19 answerable)
- **Top-3 Retrieval Accuracy**: `89.5%` (17 / 19 answerable)
- **Mean Reciprocal Rank (MRR)**: `0.895`
- **In-Domain Selective Risk**: `0.0%` (0 / 13 wrong recommendations)
- **Negative Rejection Rate**: `100.0%` (5 / 5 negative controls rejected)
- **Network Egress**: 0 bytes (Purely local, offline execution)

---

## 6. Changed Files

- `src/corpus/semantics.py`: Added `RequirementEvidenceSupportState` enum and semantic definitions.
- `src/corpus/retriever.py`: Added `evaluate_requirement_support` logic and wired into all retrieval paths.
- `src/traceability.py`: Added `requirement_evidence_support` to `TraceableEvidenceRecord`, added cryptographic & quality verification against SQLite storage, and added safety escalation on `CONFLICTING` evidence.
- `src/recommend.py`: Passed compound component metadata to clause retrieval and escalated `CONFLICTING` evidence to `ASSISTED_REVIEW_REQUIRED`.
- `frontend/src/types.ts`: Added `requirement_evidence_support` field to `ClauseEvidenceData` and `TraceRecord`.
- `frontend/src/components/EvidenceDrawer.tsx`: Rendered color-coded requirement support indicators in the trace record and clause evidence cards.
- `tests/test_evidence_validation_audit.py`: Created 12-case deterministic offline test suite.

---

## 7. Known Limitations & Recommended Next Steps

1. **Lexical Domain Overlap vs Deep Semantic Entailment**: While operating envelope contradictions and numerical ratings are deterministically checked, subtle engineering trade-offs require expert-curated requirement-clause rule mappings or adjudicated evaluation pairs.
2. **Pilot Corpus Coverage**: The full-text corpus currently contains pilot test fixtures. Expanding the corpus to statutory BIS gazette documents in production will require formal licensing and official ingest pipelines.
3. **Next Recommended Phase**: Proceed to **Phase 21: Multi-Requirement Systemic Conflict Resolution & Standards Precedence Engine** to resolve inter-standard precedence (e.g. general product specifications vs specialized application codes).
