# Phase 34: Production Readiness & Coverage Audit — Context

**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Date:** 2026-10-19  

---

## 1. Audit Scope & Context

This phase executes a comprehensive, read-first production readiness and coverage audit of Tender Saathi after the completion of Phase 33. The objective is to determine what is genuinely complete, what works end-to-end, what remains incomplete or unverified, and what must be addressed before a credible Smart India Hackathon (SIH) demonstration or production deployment.

### Audit Invariants
1. **Read-First & Evidence-Based**: No speculative assertions or assumptions; all claims backed by source code, database contents, test executions, and SHA-256 digests.
2. **Zero Fabrication**: No fabricated BIS standards, simulated clause passages, ungrounded benchmark labels, or artificial test passes.
3. **Ground-Truth Invariance**: The benchmark dataset (`dataset/ground_truth/ground_truth.csv`) with SHA-256 `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` remains strictly read-only and unmutated.
4. **Honest Boundary Demarcation**: Complete separation of national catalogue presence (metadata) from actual normative clause coverage (full text), and unverified labels from expert-validated ground truth.

---

## 2. Core Audit Dimensions

1. **Complete Application User Journey**:
   - Trace intake and multi-modal upload (PDF, text, image/OCR).
   - Trace requirement decomposition into atomic specifications.
   - Trace BIS catalogue search, candidate retrieval, hybrid BM25 + dense semantic scoring.
   - Trace applicability checks, parameter bounds, and dimension ceilings.
   - Trace evidence verification against normative clause database.
   - Trace ambiguity detection and discretionary specification gating.
   - Trace cross-requirement conflict detection and standards precedence.
   - Trace evidence-grounded cross-reference traversal.
   - Trace audit trail, human review workflows (`ACCEPT`, `EDIT`, `DISMISS`), and report generation (JSON, Markdown, PDF).

2. **Standards Coverage & Verification Hierarchy**:
   - National BIS Catalogue: total records and lifecycle-status distribution (`ACTIVE`, `WITHDRAWN`, `UNKNOWN`, `SUPERSEDED`).
   - Searchable Records: curated database (`standards.db`) vs catalogue FTS5 index (`catalogue_search_index.db`).
   - Curated Metadata Standards: standards with curated titles, scopes, keywords, and explicit relationships.
   - Authentic Normative Passages: documents and passages in `corpus.db` with exact clause identifiers, page numbers, and SHA-256 digests.
   - Clause-Verified Eligibility: precise enumeration of standards capable of achieving `CLAUSE_VERIFIED` status vs those limited to `CATALOGUE_DISCOVERED` or `SAFE_ABSTENTION`.

3. **Reliability, Safety & Failure Modes**:
   - Ambiguous requirements handling and calibration.
   - Multi-part standard disambiguation (e.g. `IS 1239 Part 1` vs `Part 2`).
   - Withdrawn and superseded standards handling, active successor recommendation.
   - Handling of 13,024 catalogue records with `UNKNOWN` status.
   - Unsupported engineering dimensions and out-of-scope parameters.
   - Compound requirements isolation and decomposition.
   - Cross-reference graph traversal depth bounds, cycle prevention, and non-elevation invariant.
   - Discretionary specification gating ("at engineer's discretion", "as directed").
   - Insufficient evidence and safe abstention behavior.

4. **Evaluation Quality & Ground-Truth Rigor**:
   - Benchmark size and representative breadth.
   - Label provenance and human verification status (current status of `human_verified` and `adjudication_status`).
   - Sector categorization (`PROVISIONAL:` tags vs verified taxonomy).
   - Negative control presence and distribution.
   - Abstention evaluation metrics vs recommendation accuracy metrics.
   - Gap between adjudication packet generation (Phase 13) and final ground-truth signoff.

5. **Actual Product Testing & Execution**:
   - Full backend test suite (`pytest -q`): 778 tests.
   - Targeted end-to-end and Phase 33 regression suite: 27 tests.
   - Frontend component and filtering test suite (`vitest run`): 9 tests.
   - Frontend production bundle build (`tsc && vite build`).
   - Verification of frozen ground-truth SHA-256 digest.

6. **Prioritized Gap Report (P0 - P3)**:
   - P0: Safety or correctness blockers.
   - P1: SIH demonstration requirements (high visibility, jury credibility).
   - P2: Production readiness requirements (scalability, operational safety).
   - P3: Long-term enhancements (continuous BIS synchronization, extended domains).
