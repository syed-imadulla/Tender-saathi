# Phase 5 Context — Human Review & Decision Workflow

## Executive Summary
TenderSaathi has successfully completed Phases 1 through 4:
- **Phase 1**: Generalized Applicability Engine & False-Positive Protection
- **Phase 2**: Ambiguity Engine Calibration & Multi-Standard Decision Quality
- **Phase 3**: Evidence-First Standards Intelligence
- **Phase 4**: Tender Audit & Standards Gap Intelligence

The intelligence pipeline is:
$$\text{RETRIEVE} \rightarrow \text{APPLY} \rightarrow \text{DECIDE} \rightarrow \text{EXPLAIN} \rightarrow \text{AUDIT}$$

While the system reliably isolates ambiguous requirements, missing technical parameters, potential gaps, and lifecycle concerns, the user interface currently only **displays** these findings (in the "Needs Attention" card list and the "Evidence Drawer"). It does not provide an actionable human decision workflow.

Phase 5 introduces the human-in-the-loop operational layer:
$$\text{REVIEW} \rightarrow \text{INSPECT EVIDENCE} \rightarrow \text{DECIDE} \rightarrow \text{RECORD} \rightarrow \text{REPORT}$$

---

## 1. Current Baseline Architecture & Existing Assets

### A. Backend Pipeline & Contracts
- **`src/recommend.py`**:
  `RequirementRecommendationResult` with `candidate_standard`, `evidence_standard`, `why_it_matches`, `ambiguity_state`, `missing_information`, `competing_interpretations`, `suggested_clarification_question`, `human_review_required`.
- **`src/audit.py`**:
  `TenderAuditEngine`, `TenderAuditResult`, `CoverageState` (`COVERED`, `PARTIAL`, `REVIEW_REQUIRED`, `POTENTIAL_GAP`, `UNKNOWN`), `ReviewQueueCategory` (`HIGH_PRIORITY_REVIEW`, `CLARIFICATION_REQUIRED`, `LIFECYCLE_REVIEW`, `POTENTIAL_COVERAGE_GAP`, `EVIDENCE_INSUFFICIENT`), `AuditFinding`, `RequirementCoverageItem`, `ReviewQueueItem`.
- **`src/report.py`**:
  `ReportGenerator`, `TenderReviewReport`, `RequirementReviewSection`, generating structured reports, Markdown (`.md`), and JSON (`.json`).
- **`api/server.py`**:
  Normalizes analysis results to JSON; stores report artifacts in `_report_cache[tender_id]`; exposes `/api/analyze/text`, `/api/analyze/pdf`, `/api/analyze/sample/<demo>`, `/api/report/<tender_id>/<format>`.

### B. Frontend Architecture & Existing Assets
- **`frontend/src/types.ts`**:
  `Requirement`, `AnalysisSummary`, `AnalysisResult`, `StandardsCoverage`, `GapItem`, `AmbiguityState`.
- **`frontend/src/pages/Results.tsx`**:
  Renders tender header, publication readiness banner, ambiguity summary bar, 4 result sections (`RecommendedList`, `AttentionList`, `UpdateList`, `RelatedStandardsList`), and modal/drawer triggers.
- **`frontend/src/components/RequirementCard.tsx`**:
  Cards for each section (`RecommendationCard`, `AttentionCard`, `UpdateCard`, `RelatedCard`) with "See why" button opening the evidence drawer.
- **`frontend/src/components/EvidenceDrawer.tsx`**:
  Slide-out drawer presenting progressive disclosure: Requirement text, Indian Standard & Grounding Integrity, Lifecycle & Relationships, Applicability Analysis, Evidence & Provenance, Ambiguity & Uncertainty, and Verification Scores.

---

## 2. The Exact Phase 5 Gap

1. **Passive vs. Active Review**:
   - Currently, if a requirement is flagged as `REVIEW_REQUIRED`, `AMBIGUOUS`, or having a `LIFECYCLE_CONCERN`, the user can only view the card and open the `EvidenceDrawer`.
   - There is no mechanism to mark the requirement as **Accepted**, **Edited** (with an alternative standard), or **Dismissed**.
2. **Missing Decision State & Traceability**:
   - No human review decision object exists to record what the human reviewer decided, why they decided it, or who made the decision.
3. **Absence of Reviewer Notes**:
   - Procurement technical officers cannot enter rationale notes (e.g. *"Verified CPVC Class 1 pipe suitable for hot water line"*).
4. **Lack of Review Progress Tracking**:
   - The UI does not track how many flagged items have been reviewed vs. pending (e.g., *"3 / 7 reviewed: 2 Accepted, 1 Edited, 0 Dismissed, 4 Pending"*).
5. **Report Disconnect**:
   - Downloaded audit reports (`.md` and `.json`) only contain the automated system findings; they do not include the recorded human decisions or reviewer notes.

---

## 3. Scope & Objectives

### In-Scope (Phase 5):
1. **Human Decision Model**:
   - Explicit decision states: `PENDING`, `ACCEPT`, `EDIT`, `DISMISS`.
   - Separate human decision fields: `decision`, `reviewer_standard` (for EDIT), `reviewer_note`, `reviewed_at`.
2. **Actionable Review Queue UI**:
   - Dedicated Review Workflow view / mode on the Results page grouping flagged items by category (`HIGH_PRIORITY_REVIEW`, `CLARIFICATION_REQUIRED`, `LIFECYCLE_REVIEW`, `POTENTIAL_COVERAGE_GAP`, `EVIDENCE_INSUFFICIENT`).
   - Clean, professional procurement UX with badges, review status indicators, and quick filters (`All`, `Pending`, `Reviewed`).
3. **Review Detail & Decision Controls**:
   - Interactive decision controls integrated into the review experience (integrated with or complementary to `EvidenceDrawer`).
   - Clear side-by-side presentation: System Finding vs. Human Decision.
   - Standard input field with autocomplete/validation when `EDIT` is chosen.
   - Text area for Reviewer Notes with quick rationale chips.
4. **Tender-Level Review Progress**:
   - Review progress indicator showing total flagged items, reviewed count, and breakdown by status (`Accepted`, `Edited`, `Dismissed`, `Pending`).
   - Overall tender review lifecycle state: `Review Required` $\rightarrow$ `Review in Progress` $\rightarrow$ `Review Complete`.
5. **Report Integration**:
   - Backend endpoint / handler to update tender report cache with human review decisions.
   - `TenderReviewReport` Markdown and JSON export updated to include a dedicated **Human Review & Decision Trail** section.
6. **Safety & Guardrails**:
   - Strict separation: Human decisions NEVER overwrite original `candidate_standard`, `applicability`, `evidence`, or system recommendations.
   - Zero hallucinated evidence.
   - Zero hardcoding of benchmark numbers or test cases.

### Non-Goals (Out-of-Scope for Phase 5):
- No modifications to BM25, semantic retrieval, embeddings, cross-encoder reranker, or applicability filtering.
- No user authentication, multi-tenant databases, or complex persistent user accounts (session / in-memory cache is sufficient for SIH hackathon scope).
- No arbitrary "compliance score" or claims of legal/statutory certification.
- No automatic replacement of withdrawn standards without catalogue evidence.

---

## 4. Architectural Invariants

1. **System Analyzes, Human Decides**:
   The system recommendation is immutable. If the reviewer chooses `EDIT` and specifies `IS 4985`, the system records:
   $$\text{Candidate Standard (System): } \text{IS 15778}$$
   $$\text{Human Decision: } \text{EDIT} \rightarrow \text{Reviewer Standard: } \text{IS 4985}$$
2. **Evidence Invariant**:
   `candidate_standard == evidence_standard` invariant is strictly preserved. A human decision does not fabricate evidence for the edited standard.
3. **Zero Benchmark Drift**:
   Frozen 20-row benchmark must remain 18/20 Top-1, 17/17 direct recommendations, 2 safe abstentions, 0 incorrect Top-1, MRR 0.9000.
4. **All 403 Tests Must Pass**:
   The full test suite (388 baseline + 15 Phase 4) must pass with zero regressions.

---

## 5. Acceptance Criteria

- [ ] **Review Queue**: All requirements requiring human review are accessible in an organized, categorized review queue.
- [ ] **Review Detail**: Reviewer can inspect why the item was flagged, missing parameters, evidence, and uncertainty before deciding.
- [ ] **Decision Actions**: Reviewer can mark items as `ACCEPT`, `EDIT`, or `DISMISS`.
- [ ] **Notes**: Reviewer can attach justification notes to any reviewed requirement.
- [ ] **Progress Tracking**: Real-time counter tracks progress (`X / Y reviewed`, breakdown of states).
- [ ] **Traceable Report**: Downloaded Markdown and JSON reports clearly display the Human Decision Trail alongside System Findings.
- [ ] **Separation**: System recommendations are never mutated or overwritten by human actions.
- [ ] **Zero Regressions**: 403+ repository tests pass; frozen benchmark metrics are identical.
