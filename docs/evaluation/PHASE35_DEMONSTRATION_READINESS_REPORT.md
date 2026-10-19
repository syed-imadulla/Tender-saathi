# Phase 35 Evaluation Report: Demonstration Readiness, Negative-Control Evaluation & Catalogue Hygiene

**Execution Date:** October 19, 2026  
**Repository Branch:** `main`  
**Execution Context:** Evidence-first, safety-critical implementation addressing findings from `docs/evaluation/PHASE34_PRODUCTION_READINESS_AUDIT.md`.  
**Ground-Truth Checksum:** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (strictly verified and invariant).

---

## Executive Summary

Phase 35 implements the highest-priority demonstration and audit readiness improvements for Tender Saathi without compromising its evidence-grounding or safety-critical abstention guarantees:

1. **Interactive Normative Traversal Journey**: Fully exposes evidence-backed cross-reference graph traversal in backend endpoints (`/api/standards/<id>/traversal` and `/api/graph/traverse`) and in the frontend (`StandardsGraph.tsx` and `EvidenceDrawer.tsx`). Users can inspect bounded (depth 1–2) citation chains with hop badges, originating clauses, target status, and verbatim citation passages, backed by an explicit non-elevation safety invariant disclaimer.
2. **Negative-Control Suite & Abstention Safeguards**: Implemented `dataset/evaluation/phase35_negative_controls.json` containing 12 negative-control probes spanning commercial terms, vague commodities, missing parameters, conflicting specifications, and unmapped foreign standards. Achieved **0 false recommendations** (0 `RECOMMEND` decisions on negative controls) and 100% safe abstention / review-required handling in `tests/test_phase35_negative_controls.py`.
3. **Catalogue Lifecycle Status Hygiene**: Deterministically reconciled 12,682 previously `UNKNOWN` catalogue records in `data/catalogue/bis_catalogue.db` where raw BIS portal data had shifted lifecycle status `(Active)` into `iso_equivalence`. Active catalogue coverage increased from 10,828 to **23,510** standards, while reducing `UNKNOWN` records from 13,024 to **342** with full provenance tracking. The FTS5 catalogue index `data/catalogue/catalogue_search_index.db` was completely rebuilt.
4. **Authentic Normative Standards Ingestion**: Ingested authentic statutory public gazette extracts for `IS 694 : 2010` (PVC cables) and `IS 1180 (Part 1) : 2014` (outdoor distribution transformers) into `data/standards/corpus.db` and `standards.db`, expanding registered corpus documents from 11 to **13** and normative passages from 44 to **53**.
5. **System-Wide Verification**: All **788 backend pytest tests** and all **12 frontend vitest tests** pass with 100% success rate. The frontend production build (`npm --prefix frontend run build`) compiles cleanly with zero TypeScript errors.

---

## 1. Interactive Normative Traversal Journey

### 1.1 Backend Implementation
- **Data Model**: Added `traversed_cross_references: List[Dict[str, Any]]` to `RequirementRecommendationResult` in `src/recommend.py`.
- **API Server Endpoints**:
  - `@app.route("/api/standards/<path:standard_id>/traversal")`: Returns BFS cross-reference graph traversal starting at `standard_id` with bounded depth (`depth=1` or `depth=2`), filterable by technical context.
  - `@app.route("/api/graph/traverse")`: Generic traversal endpoint queryable by standard number or identifier.
  - Serialization: `_normalize_result` in `api/server.py` serializes `traversed_cross_references` into JSON API payloads for consumption by frontend drawers.
- **Safety Invariant (Non-Elevation Rule)**:
  - Traversed cross-references are recorded strictly as secondary references or dependencies (`version_role="REFERENCE_ONLY"` or `dependency_type="REFERENCED_STANDARD"`).
  - Traversed references are never elevated to replace a primary standard recommendation or claim direct passage grounding without an independent clause match.

### 1.2 Frontend Implementation
- **Types**: Added `TraversedReference` and `StandardsTraversalResponse` to `frontend/src/types.ts`.
- **Client API**: Implemented `getStandardTraversal(standardIdOrNumber, depth, context)` in `frontend/src/api.ts`.
- **StandardsGraph Component (`frontend/src/pages/StandardsGraph.tsx`)**:
  - Added interactive "Normative Traversal Journey" drawer section that activates when a standard node is selected.
  - Bounded Depth Selector: Toggle between Direct (Depth 1) and Transitive (Depth 2).
  - Hop Badges: Displays `Hop 1 (Direct Reference)` or `Hop 2 (Transitive Reference)`.
  - Citation Metadata: Originating clause, relationship type, target standard status, and verbatim citation snippet.
  - Interactive Pivot: "Explore in Graph" button centers and expands the selected target node.
  - Non-Elevation Disclaimer: Explicit alert stating that traversed cross-references are structural references and not automatically elevated to primary standards.
- **EvidenceDrawer Component (`frontend/src/components/EvidenceDrawer.tsx`)**:
  - Added Section 15 ("Normative Traversal Journey") to the tender analysis results drawer displaying traversed cross-references associated with individual requirements.
- **Automated Frontend Tests**: Added unit tests in `frontend/src/pages/StandardsGraph.test.ts` validating traversal mapping and non-elevation rules. All 12 frontend vitest tests pass.

---

## 2. Negative-Control Suite & Abstention Safeguards

### 2.1 Benchmark Dataset (`dataset/evaluation/phase35_negative_controls.json`)
The suite consists of 12 probe cases specifically formulated to evaluate system boundary integrity:
1. `NC-COMM-01`: Commercial advance payment terms ("Mobilization advance of 10% against bank guarantee").
2. `NC-COMM-02`: Penalty / liquidated damages conditions ("Liquidated damages clause: delay in delivery attracts 0.5% per week").
3. `NC-COMM-03`: Tender security / earnest money deposit ("Submission of Earnest Money Deposit (EMD) through demand draft").
4. `NC-VAGUE-01`: Office stationery commodity ("Procurement of 500 reams of A4 75 GSM copier paper").
5. `NC-VAGUE-02`: Commercial office furniture ("Supply of 50 ergonomic high-back mesh executive chairs").
6. `NC-PARAM-01`: Unspecified pump parameters ("Supply of water pumps for civil facility without head or flow rate").
7. `NC-PARAM-02`: Unspecified structural steel shape ("Supply of structural steel material for warehouse construction without grade").
8. `NC-PARAM-03`: Bare electrical cable without voltage/dielectric ("Supply and laying of electrical power cable for lighting circuit").
9. `NC-CONF-01`: Contradictory pipe specifications ("Supply of HDPE pipes for continuous superheated steam distribution at 250°C").
10. `NC-CONF-02`: Contradictory cable voltage tier ("Supply of IS 694 cable for 33 kV substation transmission").
11. `NC-FOR-01`: Unmapped foreign standard ("Supply of structural steel sections conforming to DIN 17100 St 37-2").
12. `NC-IT-01`: Commercial cloud subscription ("Annual subscription for cloud-hosted enterprise resource planning SaaS").

### 2.2 Test Results (`tests/test_phase35_negative_controls.py`)
- **Zero False Recommendations**: 0 out of 12 negative controls received a false `RECOMMEND` decision without review.
- **Safe Abstention Rate**: 100% of out-of-scope probes cleanly abstained (`candidate_standard=None` and `human_review_required=True`).
- **Parameter Deficiency**: Probes with missing discriminating parameters correctly triggered `human_review_required=True` with explicit review notes rather than emitting unjustified high-confidence matches.

---

## 3. Catalogue Lifecycle Status Hygiene

### 3.1 Root Cause & Audit Findings
In the raw BIS web portal scraping output, 12,682 active standards had their lifecycle status parenthetically appended to the `iso_equivalence` column:
- `(Active)`: 12,356 records
- `(Active,Concurrent Running )`: 315 records
- `(Concurrent Running )`: 11 records
This portal anomaly left the primary `status` column populated with `"UNKNOWN"`, causing valid active standards to display as unverified or status unknown during citation analysis.

### 3.2 Reconciliation Pipeline (`scripts/reconcile_catalogue_lifecycle.py`)
A deterministic, audited reconciliation script was executed:
- Evaluated all 13,024 records where `status = 'UNKNOWN'`.
- Reconciled 12,682 records to `status = 'ACTIVE'` with full provenance recorded in `recovery_reason`:
  `RECONCILED_FROM_RAW_PORTAL_STATUS_COLUMN:iso_equivalence=...`
- Cleaned the parenthetical status string from `iso_equivalence` across 21,420 records, leaving only genuine ISO/IEC equivalence data.
- Left the remaining 342 records without verifiable portal status as `UNKNOWN` to avoid fabrication.
- Rebuilt the FTS5 search index `data/catalogue/catalogue_search_index.db` indexing 23,510 active records in 0.30 seconds.

### 3.3 Comparative Summary Table
| Metric | Pre-Phase 35 | Post-Phase 35 | Delta |
| :--- | :---: | :---: | :---: |
| **Total Catalogue Standards** | 35,208 | 35,208 | 0 |
| **ACTIVE Standards** | 10,828 | **23,510** | **+12,682 (+117.1%)** |
| **WITHDRAWN Standards** | 11,340 | 11,340 | 0 |
| **UNKNOWN Standards** | 13,024 | **342** | **-12,682 (-97.4%)** |
| **SUPERSEDED Standards** | 16 | 16 | 0 |
| **FTS5 Indexed Active Standards** | 10,828 | **23,510** | **+12,682** |

---

## 4. Authentic Normative Standards Ingestion

### 4.1 Ingested Standards
In accordance with BIS Gazette public access provisions, authentic documents and clauses were ingested via `scripts/ingest_normative_standards.py`:
1. **`IS 694 : 2010`**: *Polyvinyl Chloride Insulated Unsheathed-and-Sheathed Cables/Cords with Rigid and Flexible Conductors for Working Voltages up to and Including 450/750 V - Specification (Fourth Revision)*.
   - Document ID: `DOC-IS-694-2010`
   - Ingested Passages: 4 verified clauses (Clause 1.1 Scope, Clause 4.1 Conductors, Clause 4.2 Insulation, Clause 16.1 Voltage Tests).
   - Ingested Cross-References: `IS 8130 : 2013` (conductors for insulated cables), `IS 5831 : 1984` (PVC insulation & sheath), `IS 10810 (Part 45) : 1984` (methods of test for cables).
2. **`IS 1180 (Part 1) : 2014`**: *Outdoor Type Oil Immersed Distribution Transformers up to and including 2500 kVA, 33 kV - Specification (Part 1: Mineral Oil Immersed)*.
   - Document ID: `DOC-IS-1180-Part-1-2014`
   - Ingested Passages: 5 verified clauses (Clause 1.1 Scope, Clause 6.1 Standard Ratings, Clause 7.1 Winding Temperature Rise, Clause 15.1 Energy Efficiency Levels, Clause 21.1 Type & Routine Tests).
   - Ingested Cross-References: `IS 2026 (Part 1) : 2011` (power transformers general), `IS 335 : 2018` (new insulating oils), `IS 3043 : 2018` (code of practice for earthing).

### 4.2 Corpus Summary Table
| Metric | Pre-Phase 35 | Post-Phase 35 |
| :--- | :---: | :---: |
| **Corpus Registered Documents** | 11 | **13** |
| **Verified Normative Passages** | 44 | **53** |
| **Licensing Classification** | `STATUTORY_PUBLIC_GAZETTE` | `STATUTORY_PUBLIC_GAZETTE` |
| **Passage Content Hash Verification** | 100% SHA-256 Valid | 100% SHA-256 Valid |

---

## 5. Verification Suite & Test Summary

```
============================= test session starts ==============================
Platform linux -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
Rootdir: /home/syed-imadulla/Desktop/Tender_Saathi
Total test files: 42
======================= 788 passed in 196.38s (0:03:16) ========================
```

- **Backend Pytest**: 788 / 788 tests passed (100%).
- **Frontend Vitest**: 12 / 12 tests passed (100%).
- **Frontend Production Build**: Zero TypeScript errors; Vite assets generated cleanly.
- **Ground-Truth Checksum**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` strictly preserved.

---

## 6. Recommendations & Next Steps

1. **Demonstration Video Recording**: Tender Saathi is now fully demonstration-ready with rich interactive normative traversal journeys, clean negative-control handling, and 23,510 active national catalogue standards.
2. **Production Release**: Proceed with milestone archiving and documentation finalization.
