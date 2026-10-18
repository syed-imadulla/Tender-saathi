# Tender Saathi — Phase 22: Recovery Audit & Standards Precedence Investigation Report

**Date**: 2026-10-18  
**Scope**: Recovery Audit, Current Repository Health Verification, Cross-Requirement Interaction Analysis, and Phase 22 Architectural Design  
**Branch**: `main` | **Git Commit Head**: `5d62261`  
**Phase State**: Implementation & Verification Complete (All 10/10 Adversarial Precedence Tests Passing, 657/657 Full Suite Passing)  

---

## 1. Actual Repository & Git State

A complete read-only audit of `/home/syed-imadulla/Desktop/Tender_Saathi` was conducted prior to making any modifications:

- **Branch**: `main` (in sync with `origin/main`).
- **Commit History**:
  - `5d62261`: `feat: implement evidence support validation engine with conservative parameter checks and negation handling` (Phase 21 completion commit).
  - `117bb2c`: `feat: implement evidence-to-requirement validation engine with support states and audit tests` (Phase 20).
  - `0715d50`: `refactor: integrate offline clause-retrieval subsystem into core recommendation and evidence presentation paths` (Phase 19).
  - `2be9ec7`: `feat: implement standards corpus ingestion, extraction, chunking, storage, and retrieval pipeline` (Phase 18).
- **Working Tree State**:
  - The working tree was completely clean prior to generating the evaluation and planning documents.
  - No stashed, untracked, or discarded user modifications were lost.
  - Active ground-truth file `dataset/ground_truth/ground_truth.csv` is intact and unmodified.

---

## 2. Phase 21 Health Verification Results

To ensure no hidden regressions or silent degradation from previous sessions, all test suites, builds, and evaluations were executed fresh in this session:

| Test Suite / Command | Execution Command | Result | Duration / Latency |
|---|---|---|---|
| **Focused Evidence Suites (Phases 18–21)** | `pytest tests/test_corpus_ingestion.py tests/test_clause_evidence_integration.py tests/test_evidence_validation_audit.py tests/test_evidence_support_validation.py -v` | **58 / 58 PASSED** | 5.60s |
| **Phase 21 Adversarial Matrix Alone** | `pytest tests/test_evidence_support_validation.py -v` | **18 / 18 PASSED** | 0.63s |
| **Complete Backend Test Suite** | `pytest -q` | **647 / 647 PASSED** | 61.73s (0:01:01) |
| **Frontend Production Build** | `npm run build --prefix frontend` | **Clean build** (Zero TS errors, zero bundle errors) | 1.45s |
| **Benchmark Multi-Metric Evaluation** | `python3 scripts/evaluate_milestone12.py` | **89.5% Top-1, 0.0% Selective Risk, 100% Negative Rejection** | ~20s |

All verification passed with zero failures and zero regressions.

---

## 3. Active Ground-Truth Hash Verification

The authoritative ground-truth dataset was verified before and after test execution using `sha256sum`:

- **Expected Target Hash**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Measured Pre-Run Hash**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Measured Post-Run Hash**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Status**: **Bit-for-bit invariant**. No ground-truth modification occurred.

---

## 4. Existing Architecture & Call Paths Relevant to Phase 22

Tracing the execution path of multi-requirement documents in Tender Saathi revealed the following structural pipeline:

1. **Extraction & Decomposition**:
   - `src/extract.py:extract_from_pdf()` extracts a list of `Requirement` objects (`requirement_id`, `requirement_text`, `category`, `components`).
   - Multi-clause statements within a single requirement are split by `CompoundRequirementDecomposer` (`src/decompose.py`), assigning component IDs (e.g. `REQ-001-C1`).

2. **Per-Requirement Recommendation**:
   - `StandardsRecommender.recommend_for_requirement()` runs each requirement in **strict isolation**:
     - `HybridRetrievalEngine` (`src/retrieval.py`): BM25 + dense semantic MiniLM embeddings.
     - `StandardsDatabase` (`src/standards.py`): SQLite metadata lookup.
     - `ApplicabilityGate` (`src/applicability.py`): Domain boundary validation.
     - `AmbiguityEngine` (`src/ambiguity.py`): Detects intra-requirement parameter omissions or competing scores.
     - `EvidenceAwareCritic` (`src/critic.py`): Recommends, rejects, or flags for review.
     - `ClauseRetriever` (`src/corpus/retriever.py`): Deterministically checks passage evidence support state (`FULLY_SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONFLICTING`, `UNVERIFIED_COVERAGE`).
     - `TraceableEvidenceValidator` (`src/traceability.py`): Audits cryptographic hashes and extraction quality.

3. **Parent Recommendation Assembly**:
   - In `StandardsRecommender.recommend_for_pdf()`, requirements are processed independently:
     ```python
     results = [self.recommend_for_requirement(r) for r in reqs]
     return TenderRecommendationReport(tender_id=t_id, total_requirements=len(results), results=results)
     ```
   - Then `audit_tender(results)` passes the list of results to `TenderAuditEngine.audit_tender()` (`src/audit.py`).

4. **Tender-Level Aggregation (`src/audit.py`)**:
   - `TenderAuditEngine` aggregates individual requirement outcomes into `TenderAuditSummary` (counts of `COVERED`, `PARTIAL`, `REVIEW_REQUIRED`, `POTENTIAL_GAP`).
   - **Crucial Finding**: `TenderAuditEngine` currently has **no logic to cross-check requirement $i$ against requirement $j$**.

---

## 5. Demonstrated Gaps vs. Merely Suspected Gaps

### Confirmed Architectural Gaps (Demonstrated by Code Inspection)

1. **Cross-Requirement Blindness**:
   - Two requirements in the same tender specifying conflicting parameters for the same system or equipment are processed independently without cross-referencing.
   - *Example*: Requirement A demands "Transformer: 100 kVA rating outdoor oil-immersed". Requirement B demands "Transformer: dry-type indoor cast resin". Both receive valid recommendations for their respective standards (IS 1180 and IS 11171) with zero indication to the procurement officer that the tender contradicts itself.

2. **Edition Divergence Across Requirements**:
   - If Requirement 1 explicitly cites an obsolete edition `IS 1180 : 1979` and Requirement 3 in the same tender cites the active successor `IS 1180 (Part 1) : 2014`, individual lifecycle warnings are emitted per requirement, but the systemic tender-level divergence is never correlated.

3. **Absence of Cross-Standard Co-Applicability Recognition**:
   - When a tender contains a product specification requirement (e.g., IS 1554 for PVC cables) and an installation requirement (e.g., IS 1255 for cable laying and jointing), the system currently evaluates them as unrelated items rather than recognizing them as complementary co-applicable standards in the same installation.

### Suspected but Unverified Assumptions (To Be Rejected as Anti-Patterns)

1. **"Specialized Standard Always Overrides General Standard"**:
   - *Refutation*: In Indian engineering and procurement practice, this assumption is false. An application code (e.g. IS 14665 for Lifts) specifies application-level safety rules, while general component standards (e.g. IS/IEC 60947 for Breakers or IS 12615 for Motors) govern equipment ratings and test methods. Neither overrides the other; they are co-applicable.
   - *Rule*: We must never arbitrarily assign overriding precedence to one standard over another unless an explicit statutory mandate or standard clause establishes it.

2. **"Higher Standard Number or Later Year Invalides Another Standard"**:
   - *Refutation*: Different product categories and distinct equipment have arbitrary standard numbers and publication years.
   - *Rule*: Precedence must strictly stem from verifiable source provenance (`SUPERSEDES`, statutory QCOs, or explicit tender stipulations).

---

## 6. Proposed Minimal Phase 22 Design

Rather than rewriting the recommendation engine or creating a parallel pipeline, Phase 22 should introduce a clean, decoupled post-processing stage:

```
Tender PDF / Requirements List
   │
   ▼
StandardsRecommender.recommend_for_requirement() (Existing, unchanged)
   │
   ▼
List[RequirementRecommendationResult]
   │
   ▼
CrossRequirementConflictEngine.analyze(results)  <── NEW PHASE 22 ENGINE
   │
   ▼
TenderAuditEngine.audit_tender() (Enriched with cross-requirement findings)
```

### Core Components of `CrossRequirementConflictEngine`:

1. **Shared-System / Equipment Parameter Matcher**:
   - Groups requirements by shared equipment identifiers (e.g., "transformer", "pump", "cable", "switchgear") or explicit equipment tags.
   - Compares physical parameter dimensions (voltage, power, indoor/outdoor mode) across requirements sharing the same equipment context.
   - If values or operating modes contradict (e.g. Indoor vs Outdoor on the same unit tag), flags `CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION`.

2. **Operating Zone & Scope Disambiguator**:
   - Distinguishes disjoint operating zones (e.g. "outdoor switchyard cabling" vs "indoor control room wiring").
   - Prevents false conflicts when requirements describe different components or zones of a larger facility (`NO_CROSS_REQUIREMENT_CONFLICT`).

3. **Tender-Level Edition Divergence Detector**:
   - Scans the recommended and explicit standards across all requirements.
   - If divergent editions of the same standard family appear (e.g. 1979 vs 2014), flags `LIFECYCLE_EDITION_DIVERGENCE` as a high-priority tender review item.

4. **Co-Applicable Complementary Standards Classifier**:
   - Recognizes standard pairs where one standard is `PRIMARY_PRODUCT` and the other is `INSTALLATION_CODE`, `TEST_METHOD`, or `SAFETY_STANDARD`.
   - Labels the relationship as `CO_APPLICABLE_COMPLEMENTARY_STANDARDS` rather than a conflict.

5. **Unresolved Precedence Escalation Gate**:
   - When two overlapping standards are recommended for the same requirement scope and no authoritative clause establishes hierarchy, the engine marks the relationship as `UNRESOLVED_NORMATIVE_PRECEDENCE` and routes to `ASSISTED_REVIEW_REQUIRED`.

---

## 7. Decision Semantics & Safety Invariants

| State Name | Definition & Trigger Condition | Action / Routing |
|---|---|---|
| `NO_CROSS_REQUIREMENT_CONFLICT` | Requirements govern distinct equipment, disjoint zones, or compatible parameters. | Standard review flow; no cross-requirement warning. |
| `CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION` | Two requirements impose mutually exclusive physical ratings or operating envelopes on the same equipment. | Escalate to procurement officer with exact conflicting requirement IDs and values. |
| `POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED` | Possible parameter clash, but requirement text lacks distinguishing details. | Route to clarification queue: "Tender specification unclear on whether items share the same circuit." |
| `CO_APPLICABLE_COMPLEMENTARY_STANDARDS` | Complementary standards (Product specification + Installation code of practice). | Group together as co-applicable in audit report; zero conflict. |
| `LIFECYCLE_EDITION_DIVERGENCE` | Different requirements in the same tender cite active and superseded editions of the same standard. | Tender-level review finding: "Harmonize standards editions across procurement sections." |
| `UNRESOLVED_NORMATIVE_PRECEDENCE` | Overlapping standards where source evidence does not establish priority. | `human_review_required = True`; preserve uncertainty without guessing. |

### Strict Invariants Maintained
- `is_official_source_authenticated = False` strictly preserved.
- `is_human_verified = False` strictly preserved.
- Ground truth `dataset/ground_truth/ground_truth.csv` immutable (`8bcc9bc5...`).
- Zero reliance on external LLM calls or live network egress for regression tests.

---

## 8. Summary of Files Changed & Created

1. **New Package & Implementation**:
   - `src/precedence/__init__.py`: Package initialization exporting engine and models.
   - `src/precedence/conflict_engine.py`: Standalone, deterministic `CrossRequirementConflictEngine`, `CrossRequirementFinding`, and `CrossRequirementAnalysisResult`.
2. **Semantics Data Models**:
   - `src/corpus/semantics.py`: Added `CrossRequirementConflictState` canonical enum and `CROSS_CONFLICT_STATE_DESCRIPTIONS` dictionary.
3. **Audit Integration**:
   - `src/audit.py`: Integrated `CrossRequirementConflictEngine` into `TenderAuditEngine.audit_tender()`, updating `TenderAuditResult` and `StructuredTenderAuditReport`.
4. **Adversarial Test Matrix**:
   - `tests/test_precedence_and_cross_conflicts.py`: 10 comprehensive deterministic test cases validating all 7 conflict categories, tender audit escalation, and anti-falsification invariants.
5. **Evaluation & Planning Artifacts**:
   - `docs/evaluation/PHASE22_RECOVERY_AND_DESIGN_AUDIT.md`: This comprehensive verification audit report.
   - `.planning/phases/22-multi-requirement-conflict-resolution/22-CONTEXT.md`
   - `.planning/phases/22-multi-requirement-conflict-resolution/22-PLAN.md`
6. **Knowledge Graph Synchronized**:
   - `graphify-out/`: Fully synchronized via AST extraction (`graphify update .`).

---

## 9. Verification & Invariant Proof

- **Focused Evidence Test Suite**: 58/58 passed in 5.71s.
- **Precedence & Cross-Requirement Matrix**: 10/10 passed in 0.45s.
- **Tender Audit Suite**: 15/15 passed in 0.45s.
- **Full Backend Test Suite**: 657/657 passed in 64.93s (647 baseline + 10 Phase 22 tests).
- **Frontend Production Build**: Clean build in 1.47s (`npm run build --prefix frontend`).
- **Benchmark Evaluation**: `scripts/evaluate_milestone12.py` maintains 89.5% Top-1, 0.0% Selective Risk, 100% Negative Rejection Rate.
- **Ground-Truth Invariance**: SHA-256 `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` bit-for-bit identical.

Ready to proceed to **Phase 23: Production Containerized Deployment**.
