# Phase 22 Plan: Multi-Requirement Systemic Conflict Resolution & Standards Precedence Engine

## Goal
Design and implement a deterministic, non-speculative cross-requirement conflict and standards precedence engine that operates across all requirements in a tender, detecting shared-system contradictions, edition divergences, co-applicable standards, and unresolved normative precedence questions without inventing unverified hierarchies.

## Tasks

### Task 1: Audit Current Tender-Level Execution Paths & Data Models
- Trace `recommend_for_pdf()`, `TenderRecommendationReport`, and `TenderAuditEngine`.
- Identify integration points where cross-requirement analysis can safely run post-requirement recommendation without altering individual retrieval scores or ground-truth evaluations.

### Task 2: Define Safe Cross-Requirement Conflict Semantics & Data Models
- Introduce canonical outcome enums in `src/corpus/semantics.py` or `src/precedence/` (reusing existing enums where identical):
  - `NO_CROSS_REQUIREMENT_CONFLICT`
  - `CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION`
  - `POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED`
  - `UNRESOLVED_NORMATIVE_PRECEDENCE`
  - `CO_APPLICABLE_COMPLEMENTARY_STANDARDS`
  - `TENDER_SPECIFICATION_OVERRIDE`
- Define data structure `CrossRequirementConflictFinding` with:
  - `finding_id: str`
  - `source_requirement_id: str`
  - `target_requirement_id: str`
  - `conflict_category: str`
  - `conflict_state: str`
  - `equipment_or_parameter: str`
  - `evidence_text: str`
  - `source_provenance: str`
  - `escalation_action: str`

### Task 3: Build Deterministic Cross-Requirement Conflict Engine
- Create `src/precedence/conflict_engine.py`:
  - Parameter conflict detector (incompatible ratings on shared physical parameters or equipment tags).
  - Scope and zone discriminator (preventing false conflicts across disjoint indoor/outdoor zones).
  - Edition divergence analyzer (flagging divergent editions of the same standard across requirements).
  - Co-applicability identifier (recognizing complementary standard pairs like Product + Installation code).
  - Precedence escalator: When two standards have overlapping mandates without an explicit supersession clause, flag as `UNRESOLVED_NORMATIVE_PRECEDENCE` and route to human review.

### Task 4: Integrate into Tender Audit Pipeline
- Extend `TenderAuditEngine.audit_tender()` to execute cross-requirement conflict analysis and populate `cross_requirement_conflicts` in `TenderAuditResult`.
- Ensure single-requirement recommendation paths (`recommend_for_text`, `recommend_for_requirement`) remain completely unaffected and backward-compatible.

### Task 5: Build Deterministic Adversarial Test Suite
- Create `tests/test_precedence_and_cross_conflicts.py` covering:
  1. Direct parameter contradiction on shared equipment tag (e.g., 100 kVA vs 200 kVA for same transformer) -> `CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION`.
  2. Operating envelope clash (indoor vs outdoor on same unit) -> `CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION`.
  3. Disjoint zones (indoor control wiring vs outdoor feeder cable) -> `NO_CROSS_REQUIREMENT_CONFLICT` (False conflict avoided).
  4. Edition divergence across tender (IS 1180:1979 vs IS 1180:2014) -> `LIFECYCLE_EDITION_DIVERGENCE`.
  5. Product vs Installation standard co-applicability (IS 1554 cable + IS 1255 installation) -> `CO_APPLICABLE_COMPLEMENTARY_STANDARDS`.
  6. More stringent buyer tender specification permitted by standard -> `TENDER_SPECIFICATION_OVERRIDE`.
  7. Two overlapping product standards without authoritative precedence clause -> `UNRESOLVED_NORMATIVE_PRECEDENCE`.
  8. Missing evidence for cross-check -> `POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED`.

### Task 6: Verification & Full Regression Audit
- Run `pytest tests/test_precedence_and_cross_conflicts.py -v`.
- Run full backend test suite (`pytest -q`).
- Run frontend production build (`npm run build --prefix frontend`).
- Run benchmark evaluation (`python3 scripts/evaluate_milestone12.py`) and verify ground-truth hash invariance.
- Produce `docs/evaluation/PHASE22_RECOVERY_AND_DESIGN_AUDIT.md`.
