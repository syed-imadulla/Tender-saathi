# Phase 23 Plan: Interactive Standards Knowledge Graph

## Tasks

### Task 1: Read-Only Graph API Endpoints in Backend (`api/server.py`)
- Implement `GET /api/standards/search` supporting prefix and substring search on standard number, title, and domain.
- Implement `GET /api/standards/graph/hubs` returning curated prominent domain hubs with quick metadata.
- Implement `GET /api/standards/<standard_id>/neighbors` calling `StandardsGraph.get_direct_relationships()` with `depth=1` enforcement, returning node metadata, edges, evidence, citing clauses, and provenance.
- Implement `GET /api/standards/graph/overview` returning bounded curated graph topology.
- Add input validation and error handling for missing standards and invalid parameters.

### Task 2: Backend API Contract & Safety Tests (`tests/test_graph_api.py`)
- Test search endpoint for standard numbers and titles.
- Test hub endpoint for domain representation.
- Test neighbors endpoint for depth=1 boundary, provenance preservation, directionality, and missing standards handling (404/empty).
- Test that read-only endpoints do not alter recommendation pipeline state.

### Task 3: Interactive Frontend Graph Explorer (`frontend/`)
- Install `d3-force`, `d3-zoom`, `@types/d3-force`, `@types/d3-zoom` in `frontend/`.
- Update `frontend/src/types.ts` with graph node, edge, and response types.
- Create `frontend/src/pages/StandardsGraph.tsx` and `frontend/src/pages/StandardsGraph.css`:
  - Search / Autocomplete bar with instant lookup and domain quick-jump pills.
  - Interactive SVG canvas with collision-avoiding D3-force simulation.
  - Smooth pan/zoom controls (+, -, reset, fit).
  - Clean pill nodes with lifecycle status indicators (Active vs Withdrawn).
  - Color-coded directional edges with relationship badges.
  - Click-to-select node / edge inspector drawer showing title, year, committee, scope, relationship type, direction, provenance, and verbatim evidence clause.
  - Prominent non-applicability advisory disclaimer.
- Update `frontend/src/App.tsx` with header navigation tab between "Tender Audit" and "Standards Graph".

### Task 4: Full System Verification
- Run `pytest tests/test_graph_api.py -v`.
- Run full backend suite `pytest -q`.
- Run frontend build `npm run build --prefix frontend`.
- Verify ground truth `sha256sum dataset/ground_truth/ground_truth.csv`.
- Run `graphify update .`.
- Document results in `docs/evaluation/PHASE23_STANDARDS_KNOWLEDGE_GRAPH.md`.
