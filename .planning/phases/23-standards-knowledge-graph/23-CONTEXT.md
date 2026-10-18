# Phase 23 Context: Interactive Standards Knowledge Graph

## Phase Goal
Build a dedicated, interactive Standards Knowledge Graph page for Tender Saathi, powered by existing curated standards relationship data (`data/standards/relationships.json` and `data/standards/standards.db`) and `StandardsGraph` traversal logic (`src/graph.py`), providing an elegant, searchable network explorer with zero unreadable label collisions.

## Key Decisions & Constraints

### 1. Visualization Technology
- **Choice**: Custom React SVG + D3-Force simulation (`d3-force`, `d3-zoom`, `@types/d3-force`, `@types/d3-zoom`).
- **Rationale**: Complete control over layout, SVG pan/zoom, collision-avoidance forces (`d3.forceCollide`) to prevent overlapping text labels (directly addressing the unreadable text cloud shown in the user's reference screenshots), glassmorphic styling perfectly aligned with Tender Saathi's visual aesthetic, and lightweight footprint.

### 2. Default Initial View
- **Choice**: Focused Hub Explorer.
- **Rationale**: Instead of dumping thousands of nodes into a tangled hairball, the page opens focused on a prominent active standard (e.g. `IS 15778` CPVC pipes or `IS 7098` XLPE cables) with its direct `depth=1` neighborhood, providing domain quick-jump pills (Civil, Electrical, Mechanical, Pumps, Food Hygiene) and instant autocomplete search.

### 3. Read-Only API Endpoints (`api/server.py`)
- `GET /api/standards/search?q=<query>&limit=<limit>`: Autocomplete search over standard number and title.
- `GET /api/standards/graph/hubs`: Curated prominent domain hubs for instant jumping.
- `GET /api/standards/<standard_id>/neighbors?depth=1`: Direct incoming and outgoing relationships with verified evidence.
- `GET /api/standards/graph/overview`: Bounded curated subgraph across demonstration domains.

### 4. Safety & Provenance Invariants
- `depth=1` boundary strictly enforced on neighbor lookups.
- Relationship provenance (`VERIFIED` vs `CURATED`) strictly preserved. No `INFERRED` edges.
- Clear disclaimer that knowledge graph links do not constitute automatic tender applicability or legal compliance.
- Zero modifications to recommendation scores, thresholds, or ground truth `dataset/ground_truth/ground_truth.csv`.
