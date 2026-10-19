# Phase 35: Demonstration Readiness, Negative-Control Evaluation & Catalogue Hygiene — Plan

**Phase:** Phase 35 (`35-demonstration-readiness`)  
**Objective:** Deliver interactive normative traversal visualization in the frontend, expand the negative-control test suite with 10+ adversarial/abstention cases, clean the 13,024 UNKNOWN catalogue records via deterministic evidence reconciliation, and ingest authentic safety code passages for IS 694 and IS 1180.

---

## Plan Structure

### Task 1: Catalogue Lifecycle Status Hygiene
- Script: `scripts/reconcile_catalogue_lifecycle.py`
- Inspect `data/catalogue/bis_catalogue.db`:
  - Exactly 12,682 records have `iso_equivalence IN ('(Active)', '(Active,Concurrent Running )', '(Concurrent Running )')`.
  - Update these records to `status = 'ACTIVE'`, `is_active = 1`, `recovery_reason = 'RECONCILED_FROM_RAW_PORTAL_STATUS_COLUMN:iso_equivalence'`, and clear `iso_equivalence` to `NULL`.
  - Retain the remaining 342 records strictly as `UNKNOWN`, recording exact provenance.
  - Synchronize `data/catalogue/catalogue_search_index.db` (FTS5).
  - Verify idempotency and log before/after counts.

### Task 2: Interactive Normative Traversal Journey in Frontend & API
- **Backend API (`api/server.py`):**
  - Add endpoint `GET /api/graph/traverse`:
    - Accepts `standard` (e.g. `IS 800 : 2007`, `IS 14846 : 2000`, `IS 1239 (Part 2) : 2011`) and optional `depth` (1 or 2).
    - Calls `StandardsGraph.traverse_cross_references(start_standard, max_depth, tender_context)`.
    - Returns structured JSON with originating clause, reference kind, evidence snippet, target standard, title, and lifecycle status.
  - Surface `traversed_cross_references` on `RequirementRecommendationResult` and inside `req_dict` in `/api/analyze`.
- **Frontend Types & Client (`frontend/src/types.ts`, `frontend/src/api.ts`):**
  - Add `TraversedReference` interface and `getTraversedReferences` API function.
- **Frontend UI (`frontend/src/pages/StandardsGraph.tsx`, `frontend/src/pages/Results.tsx`):**
  - Add "Normative Traversal Journey" interactive drawer in `StandardsGraph.tsx` showing the chain of evidence from the focal standard to connected standards.
  - Allow users to click connected standards in the traversal drawer to navigate directly to their graph node.
  - Display traversed references in `Results.tsx` / `RequirementCard.tsx` under an expandable "Normative References & Dependencies" section.

### Task 3: Negative-Control Evaluation Expansion
- Fixture: `dataset/evaluation/phase35_negative_controls.json`
- Define 12 diverse negative control requirements:
  - Commercial terms (milestone billing, EMD, liquidated damages).
  - Unstandardized items (generic office stationery, bespoke furniture).
  - Proprietary IT hardware / cloud hosting services.
  - Discretionary specifications ("as directed by site engineer" with no parameters).
  - Impossible/conflicting parameters.
  - Withdrawn standard without replacement.
  - Foreign standard citation without Indian Standard equivalent.
- Automated Test Suite: `tests/test_phase35_negative_controls.py`
  - Verify Tender Saathi safely abstains on 100% of negative controls.
  - Verify zero false-positive recommendations (`RECOMMEND` count = 0).
  - Maintain the checksum of `dataset/ground_truth/ground_truth.csv`.

### Task 4: Authentic Normative Standards Ingestion (IS 694 & IS 1180)
- Sourced Official Documents:
  - `IS 694 : 2010` (PVC Cables for voltages up to 450/750 V) from Indian Public Safety Codes archive (`archive.org/details/gov.in.is.694.2010`).
  - `IS 1180 (Part 1) : 2014` (Distribution Transformers up to 2500 kVA, 33 kV) from Indian Public Safety Codes archive (`archive.org/details/gov.in.is.1180.1.2014`).
- Ingestion (`scripts/ingest_normative_standards.py`):
  - Ingest authentic passages with exact page numbers, clause identifiers, and statutory public gazette licensing into `data/standards/corpus.db`.
  - Expand `corpus_documents` from 11 to 13 and `corpus_passages` from 44 to 53.
  - Add explicit normative relationships (`IS 1180` $\rightarrow$ `IS 335`, `IS 2026`).

### Task 5: Testing, Regression & UAT
- Run `pytest tests/test_phase35_*.py -v`
- Run full backend `pytest -q` (all 778+ tests)
- Run frontend `npx --prefix frontend vitest run`
- Run frontend production build `npm --prefix frontend run build`
- Verify checksum of `dataset/ground_truth/ground_truth.csv`
- Document findings in `docs/evaluation/PHASE35_DEMONSTRATION_READINESS_REPORT.md` and `.planning/phases/35-demonstration-readiness/35-UAT.md`.
- Update `.planning/STATE.md`.
