# Phase 36 Plan: Final End-to-End Recommendation Audit & SIH Demo Hardening

**Phase:** 36 (`36-final-e2e-audit`)  
**Objective:** Prepare Tender Saathi for a reliable, honest, and impressive Smart India Hackathon demonstration through complete 10-journey user testing, safety invariant validation, UI edge-state hardening, and comprehensive evaluation documentation.

---

## Task Breakdown

### Task 1: Comprehensive 10-Journey End-to-End Test Suite
- **Target File:** `tests/test_phase36_e2e_user_journeys.py`
- **Scope:**
  1. *Journey 1 (Supported Engineering Requirement)*: Valid single requirement (e.g. CPVC pipes conforming to IS 15778) maps to active standard with HIGH confidence and verified clause evidence.
  2. *Journey 2 (Multi-Requirement Tender)*: Multiple distinct requirements (pipes, cables, transformers) cleanly decomposed into separate packages with isolated candidate standards and no cross-component pollution.
  3. *Journey 3 (Catalogue-Discovered Standard)*: Valid requirement matching active catalogue standard lacking normative corpus passages (e.g. IS 10245) returns `CATALOGUE_DISCOVERED` with `human_review_required=True` and clear scope disclaimer.
  4. *Journey 4 (Withdrawn/Superseded Standard)*: Requirement citing outdated standard (e.g. IS 10611 or withdrawn IS 4985:1988) returns authoritative active successor standard with explicit lifecycle warning.
  5. *Journey 5 (Underspecified Requirement)*: Technical requirement lacking discriminating parameters (e.g. water pumps without head/discharge rate) returns `AMBIGUOUS_UNDER_SPECIFIED` with structured missing parameters.
  6. *Journey 6 (Conflicting Requirements)*: Engineering requirement specifying incompatible material/application (e.g. HDPE for 250°C superheated steam, or IS 694 for 33 kV) triggers `APPLICATION_CONFLICT` / `CONF-04`.
  7. *Journey 7 (Commercial / Non-Standardized Clause)*: Commercial conditions (mobilization advance, EMD, liquidated damages, copier paper) cleanly trigger `SAFE_ABSTENTION` with `candidate_standard=None` and zero false recommendations.
  8. *Journey 8 (Normative Cross-Reference Traversal)*: Recommendation exposes structured traversed cross-references (depth 1–2) with hop depth, citing clause, and non-elevation invariant.
  9. *Journey 9 (Digital PDF Upload)*: Standard digital text-based PDF upload via `/api/analyze/pdf` processes successfully, extracts requirements, and generates evidence-grounded recommendations.
  10. *Journey 10 (Mixed Scope Tender)*: Single tender containing a mixture of supported engineering specifications and unsupported commercial/administrative clauses correctly separates valid recommendations from safe abstentions.

### Task 2: UI & API Demonstration Hardening
- **Target Files:** `api/server.py`, `frontend/src/pages/Results.tsx`, `frontend/src/components/EvidenceDrawer.tsx`, `frontend/src/pages/StandardsGraph.tsx`
- **Scope:**
  - Verify `/api/analyze/pdf`, `/api/analyze/text`, `/api/report/export`, and `/api/standards/<id>/traversal`.
  - Ensure clear visual distinction between `CLAUSE_VERIFIED` (green badge, full text excerpt), `CATALOGUE_DISCOVERED` (blue badge, catalogue metadata), and `SAFE_ABSTENTION` / `REVIEW_REQUIRED` (amber badge, reason).
  - Harden empty states, upload error alerts, and export file sanity (JSON, PDF, Markdown).

### Task 3: Standards Coverage & Safety Invariant Audit
- **Target Files:** `docs/evaluation/PHASE36_FINAL_E2E_AUDIT.md`, `tests/test_ground_truth_integrity.py`
- **Scope:**
  - Audit exact verified counts across `bis_catalogue.db`, `catalogue_search_index.db`, `standards.db`, and `corpus.db`.
  - Validate safety invariants: Non-elevation rule, zero synthetic clause fabrication, and ground-truth checksum invariance (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).

### Task 4: Complete System Verification & Build
- **Target Files:** Entire repository
- **Scope:**
  - Run full backend pytest test suite (788+ tests).
  - Run frontend vitest test suite (12+ tests).
  - Execute frontend production build (`npm --prefix frontend run build`).

### Task 5: Evaluation Report, UAT & State Updates
- **Target Files:** `docs/evaluation/PHASE36_FINAL_E2E_AUDIT.md`, `.planning/phases/36-final-e2e-audit/36-UAT.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`
- **Scope:**
  - Document complete test and fix findings, actual test outputs, gap matrix (P0–P3), and an evidence-backed Go/No-Go decision for SIH.
  - Synchronize AST knowledge graph using `graphify update .`.

---

## Verification Criteria
- 10/10 user journeys in `test_phase36_e2e_user_journeys.py` pass cleanly.
- 0 false recommendations on non-engineering / commercial / conflicting queries.
- Zero fabricated passages or inflated coverage metrics.
- Ground truth SHA-256 strictly preserved.
- 100% backend and frontend test pass rate.
