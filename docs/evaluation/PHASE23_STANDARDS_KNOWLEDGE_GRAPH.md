# Phase 23 Evaluation: Interactive Standards Knowledge Graph

**Status:** Implementation & Verification Complete  
**Branch:** `main`  
**Date:** 2026-10-18  
**Ground-Truth Checksum (SHA-256):** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Unmodified)

---

## 1. Executive Summary

Phase 23 implemented a dedicated, interactive **Standards Knowledge Graph** page for Tender Saathi, providing engineering and procurement teams with a focused, readable standards relationship explorer.

Crucially, this implementation strictly avoids the catastrophic visual failure modes common to naive graph visualizers:
1. **Zero global hairballs:** The system does not dump thousands of interconnected nodes onto the canvas at once. Instead, it utilizes a **Focused Hub Explorer** paradigm, opening on a chosen engineering standard and rendering its bounded direct neighborhood (`depth=1`).
2. **Zero overlapping label collisions:** Integrated collision physics (`d3.forceCollide(75)`) ensures minimum spatial clearance between pill nodes, guaranteeing crisp legibility at all zoom levels.
3. **Strict evidentiary discipline:** Curated and manually verified BSB Edge portal relationships are distinguished without fabrication. Inferred edges and speculative multi-hop traversals are strictly prohibited.
4. **Prominent Legal Disclaimer:** Every graph view and API payload carries the mandatory caveat:
   > *"Graph relationships represent technical references and lifecycle links in the BIS catalogue; they do not independently establish legal applicability or procurement compliance for any specific tender."*

---

## 2. Implemented Architecture

### A. Read-Only Backend Endpoints (`api/server.py`)

All endpoints are strictly read-only, bounded, and decoupled from the tender recommendation decision pipeline:

1. **`GET /api/standards/search?q=<query>&limit=<limit>`**
   - Performs ranked prefix and substring search across standard numbers, identifiers, and titles.
   - Bounded with strict input validation and clamping (`1 <= limit <= 50`).
2. **`GET /api/standards/graph/hubs`**
   - Returns prominent entry-point hubs across engineering domains (Plumbing & Piping, Electrical & Cables, Power Transformers, Valves, Pumps, Civil Concrete Pipes, Alloy Fittings, Motors).
   - Serves immediate metadata, relationship counts, and domain classifications.
3. **`GET /api/standards/<path:standard_id>/neighbors?depth=1`**
   - Strictly enforces `depth=1` traversal. Queries with `depth > 1` or invalid formats are rejected with HTTP 400.
   - Resolves focal standard, direct incoming/outgoing explicit edges, citing clauses, verbatim evidence snippets, confidence, and provenance (`VERIFIED` vs `CURATED`).
   - Missing standards cleanly return HTTP 404 with structured JSON.
4. **`GET /api/standards/graph/overview`**
   - Provides a bounded network summary and relationship distribution stats across the BIS standards database without hairball congestion.

### B. Interactive Frontend Network Explorer (`frontend/src/pages/StandardsGraph.tsx`)

Built using custom React SVG rendering powered by `d3-force` and `d3-zoom`:
- **Canvas Physics & Layout:** Force-directed simulation with charge repulsion (`-450`), link constraints (`150px`), and collision radii (`75px`) preventing node collisions.
- **Node Design:** Padded pill nodes displaying standard number, publication year, lifecycle status indicator (green halo for `Active`, red dashed border for `Withdrawn`/`Superseded`), and distinct orange halo for the focal node.
- **Edge Taxonomy:** Color-coded directional edges with arrowheads:
  - `NORMATIVE_REFERENCE` / `REFERENCES`: Sky Blue (`#0284c7`)
  - `INSTALLATION_CODE` / `CODE_OF_PRACTICE`: Emerald Green (`#10b981`)
  - `TEST_METHOD`: Purple (`#8b5cf6`)
  - `SUPERSEDES`: Amber / Red (`#f59e0b`)
  - `ALLIED_STANDARD`: Indigo / Blue (`#3b82f6`)
  - `SAFETY_STANDARD`: Rose (`#f43f5e`)
- **Inspector Drawer:** Clicking any node reveals full official title, technical committee, lifecycle status, provenance badge, and scope notes. Clicking any edge reveals the exact citing clause, verbatim evidence text, and provenance source.
- **Dynamic Pivot Exploration:** Clicking any connected neighbor in the inspector drawer allows single-click graph re-centering to explore that standard's direct neighborhood.
- **Interactive Controls:** Zoom in, zoom out, reset view, and smooth pan.
- **Instant Search:** Debounced autocomplete dropdown allowing immediate jumping to any standard in the catalogue.

---

## 3. Verification & Safety Audit Results

### A. Graph API Contract Tests (`tests/test_graph_api.py`)
- `TestStandardsSearchAPI`:
  - `test_search_by_standard_number`: PASSED
  - `test_search_by_title_keyword`: PASSED
  - `test_search_empty_query`: PASSED
  - `test_search_limit_clamping`: PASSED
- `TestStandardsHubsAPI`:
  - `test_get_graph_hubs`: PASSED
- `TestStandardsNeighborsAPI`:
  - `test_get_neighbors_valid_standard`: PASSED
  - `test_get_neighbors_by_standard_number_with_spaces`: PASSED
  - `test_depth_greater_than_one_strictly_rejected`: PASSED (HTTP 400)
  - `test_invalid_depth_format_rejected`: PASSED (HTTP 400)
  - `test_missing_standard_returns_404`: PASSED (HTTP 404)
  - `test_provenance_strictly_preserved_no_inferred`: PASSED (Strict invariant: zero INFERRED)
- `TestStandardsOverviewAPI`:
  - `test_get_graph_overview`: PASSED (Bounded node count <= 60)

**Result:** 12 passed in 0.53s.

### B. Existing Graph & Relationship Test Suites
- `tests/test_milestone5_graph.py` (14/14 passed)
- `tests/test_phase9_relationships_regulatory.py` (21/21 passed)
- `tests/test_phase9_taxonomy_schema.py` (9/9 passed)
- `tests/test_milestone10_dependencies.py` (8/8 passed)

**Result:** 52 passed in 6.07s.

### C. Full Backend Test Suite
```bash
pytest -q
674 passed in 65.74s (0:01:05)
```
**Result:** 100% passing across all 674 backend tests with zero regressions.

### D. Frontend Production Bundle Build
```bash
npm run build --prefix frontend
✓ 620 modules transformed.
dist/index.html                   2.36 kB │ gzip:  0.98 kB
dist/assets/index-9XDKK3rN.css   55.07 kB │ gzip: 10.21 kB
dist/assets/index-cjVd7Em_.js   335.34 kB │ gzip: 96.88 kB
✓ built in 2.02s
```
**Result:** Clean TypeScript compilation and Vite production build in 2.02s.

### E. Authoritative Dataset Invariant Check
```bash
sha256sum dataset/ground_truth/ground_truth.csv
8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc  dataset/ground_truth/ground_truth.csv
```
**Result:** Ground truth invariant preserved exactly.

---

## 4. Modified & Added Files

- `api/server.py` — Added graph singletons and 4 read-only REST endpoints (`/api/standards/search`, `/api/standards/graph/hubs`, `/api/standards/<path:standard_id>/neighbors`, `/api/standards/graph/overview`).
- `tests/test_graph_api.py` — Comprehensive API contract and safety test suite.
- `frontend/package.json` — Added `d3` and `@types/d3` dependencies.
- `frontend/src/types.ts` — Added `GraphNode`, `GraphEdge`, `GraphHub`, `StandardsSearchResponse`, `StandardsNeighborsResponse`, and `StandardsGraphOverviewResponse`.
- `frontend/src/api.ts` — Added graph client API methods.
- `frontend/src/pages/StandardsGraph.tsx` — Full interactive knowledge graph page.
- `frontend/src/pages/StandardsGraph.css` — High-contrast dark theme styling and responsive layout.
- `frontend/src/components/Header.tsx` — Added navigation tab to open the Standards Graph.
- `frontend/src/pages/Home.tsx` — Passed graph navigation callback.
- `frontend/src/App.tsx` — View routing between Tender Audit and Standards Knowledge Graph.
- `.planning/phases/23-standards-knowledge-graph/` — Planning and context artifacts.
- `docs/evaluation/PHASE23_STANDARDS_KNOWLEDGE_GRAPH.md` — This evaluation report.

---

## 5. Working Rules Compliance

- No git commit, push, stash, or reset was executed.
- Read-only graph exploration maintained without altering recommendation, scoring, or audit logic.
- Depth boundary strictly enforced at `depth=1`.
- Verified vs Curated provenance distinction strictly preserved with full verbatim evidence.
