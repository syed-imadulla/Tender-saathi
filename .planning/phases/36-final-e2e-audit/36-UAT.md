# Phase 36 — User Acceptance Testing (UAT)

## Phase Objective
Prepare Tender Saathi for a reliable, honest, and impressive Smart India Hackathon demonstration. Audit the complete user journey from uploading a tender to receiving evidence-backed BIS standard recommendations. Fix verified defects without weakening safety rules or overstating standards coverage.

---

## Acceptance Criteria & Test Results

### 1. Ingestion & Extraction Pipeline
- [x] **Plaintext input analysis** via `/api/analyze/text` succeeds with valid `AnalysisResult`.
- [x] **Multi-package / multi-requirement tender decomposition** extracts isolated requirements without cross-contamination.
- [x] **Digital PDF upload** via `/api/analyze/pdf` succeeds with status 200 using PyMuPDF.

### 2. Retrieval, Grounding & Safety Invariants
- [x] **Ground-truth benchmark immutability**: SHA-256 remains `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.
- [x] **Clause-verified standards eligibility**: Strictly restricted to the 13 registered standards with authentic statutory gazette passages in `data/standards/corpus.db`.
- [x] **Catalogue discovery tier**: Standards without indexed full-text passages are designated `CATALOGUE_DISCOVERED` with required review flag, avoiding hallucinated clauses.
- [x] **Non-elevation traversal invariant**: Normative cross-reference traversal at depth 1-2 preserves provenance and never elevates ungrounded standards to `CLAUSE_VERIFIED`.
- [x] **Lifecycle warnings**: Superseded (e.g. IS 10611) and withdrawn standards surface actionable warnings and point to active successors.
- [x] **Controlled abstention**: Commercial clauses (EMD, mobilization advance, payment terms) safely abstain without fabricating engineering standards.
- [x] **Conflict detection**: Physically conflicting requirements (e.g. HDPE for 250°C superheated steam) trigger application conflict warnings or safe abstentions.

### 3. Reporting & User Experience
- [x] **Markdown report export** (`/api/report/<tender_id>/markdown`) returns structured audit report.
- [x] **JSON report export** (`/api/report/<tender_id>/json`) returns comprehensive machine-readable payload.
- [x] **CSV report export** (`/api/report/<tender_id>/csv`) returns tabular comma-separated report.
- [x] **Frontend Download Dropdown** provides `.MD`, `.JSON`, and `.CSV` download options.
- [x] **Publication Readiness Banner** displays backend audit verdict (`READY_FOR_REVIEW`, `CONDITIONAL_REVIEW_REQUIRED`, `NOT_RECOMMENDED`).

---

## Automated Verification Sign-Off

- **Backend Pytest Tests:** 799 passed / 799 total (100%)
- **Frontend Vitest Tests:** 12 passed / 12 total (100%)
- **Production Build:** Clean (`tsc && vite build` built in 1.98s)
- **SIH Demo Readiness Verdict:** 🟢 **GO FOR SIH DEMONSTRATION**
