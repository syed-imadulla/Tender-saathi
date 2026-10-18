# Phase 23.1 Evaluation: Browser Acceptance & Graph Evidence Audit

**Status:** Complete  
**Branch:** `main`  
**Date:** 2026-10-18  
**Ground-Truth Checksum (SHA-256):** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Unmodified)

---

## 1. Executive Summary

Phase 23.1 conducted an independent, rigorous validation of the newly implemented **Standards Knowledge Graph** in both the backend API layer and the running browser frontend.

All audit dimensions were validated:
1. **Live Browser End-to-End Acceptance:** Fully automated browser verification confirmed seamless navigation, interactive canvas physics, search autocomplete, node inspection, single-click focal standard pivoting (`depth=1`), edge evidence inspection, zoom/pan controls, and responsive layout.
2. **Backend Contract Robustness:** Expanded contract tests covering boundary limits, isolated standards (0 relationships), URL-encoded slashes (`IS/IEC 60034-1`), and depth restrictions.
3. **Graph Coverage & Evidence Quality Audit:** Detailed inventory of graph data sources, relationship distributions, and citing clause extraction rates.
4. **Safety Boundaries:** Ground truth dataset (`8bcc9bc5...`), ranking algorithms, and tender recommendation decisions remain strictly untouched.

---

## 2. Browser Verification Findings

The live application was verified in Chrome via `browser_subagent` (Recording: `standards_graph_test_1792338869925.webp`).

| Interaction / Feature | Observed Behavior | Status |
| :--- | :--- | :--- |
| **Top Navigation Entry** | Clicking "Standards Graph" in header seamlessly switches views from Tender Audit to the dedicated graph explorer without page reload. | **PASS** |
| **Mandatory Disclaimer Strip** | Prominent amber advisory banner visible at top of viewport: *"Graph relationships represent technical references and lifecycle links in the BIS catalogue; they do not independently establish legal applicability or procurement compliance for any specific tender."* | **PASS** |
| **Canvas Rendering & Layout** | SVG canvas renders bounded force simulation with pill nodes and color-coded directional edges. Labels are readable without overlapping. | **PASS** |
| **Search Autocomplete** | Typing `"cable"` instantly displayed debounced autocomplete dropdown showing matching standards (e.g. `IS 7098 (Part 1)`, `IS 1255`). Selecting an item centered the graph. | **PASS** |
| **Domain Hub Selection** | Clicking `"Electrical & Cables"` or `"Water Works & Valves"` immediately re-centered the graph on the hub with its direct neighborhood. | **PASS** |
| **Node Inspection** | Clicking `IS 7098 (Part 1)` opened the right-side Inspector drawer displaying Standard Number, Official Title, Status (`Active`), Committee (`ETD 9`), and Provenance (`VERIFIED`). | **PASS** |
| **Neighborhood Pivot** | Clicking `"Explore Direct Neighborhood (depth=1)"` in the inspector re-centered the graph around the selected standard as the new focal hub. | **PASS** |
| **Edge & Evidence Inspection** | Clicking an edge revealed the exact Relationship Type (`NORMATIVE_REFERENCE`), Citing Clause (`Clause 2 References`), and verbatim quotation from the document. | **PASS** |
| **Canvas Controls** | Zoom In (+), Zoom Out (-), and Reset view buttons adjusted SVG transform matrix smoothly. | **PASS** |
| **Mobile / Responsive Layout** | Drawer slides over canvas neatly and legend hides automatically on constrained viewports. | **PASS** |

---

## 3. Backend API Contract Stress Audit

The backend contract was subjected to edge-case and boundary testing:

1. **Limit Clamping & Malformed Limits (`/api/standards/search`):**
   - Negative limits (`limit=-10`) are safely clamped to `1`.
   - String limits (`limit=invalid`) fall back to default `15` without HTTP 500 crashes.
   - Max limits (`limit=500`) are safely clamped to `50`.
2. **Isolated Standards with Zero Relationships (`/api/standards/<id>/neighbors`):**
   - Standards present in the catalogue but lacking explicit edges (e.g., `IS-15328-2003`) return HTTP 200 with `nodes=[focal_node]` and `edges=[]` instead of throwing 404 or unhandled errors.
3. **International Slashes in Identifiers:**
   - Standards containing slashes (e.g. `IS/IEC 60034-1` and URL-encoded `IS%2FIEC%2060034-1`) resolve accurately.
4. **Strict Depth=1 Enforcement:**
   - `depth=2` and invalid depth strings return structured HTTP 400 with explicit explanatory error.

---

## 4. Graph Coverage & Evidence Quality Inventory

A comprehensive script-based audit of all repository graph data sources (`data/standards/standards.db`, `data/standards/relationships.json`, `data/standards/verified_standards.json`) produced the following metrics:

| Metric | Count | Description |
| :--- | :--- | :--- |
| **Curated Standards in SQLite Database** | **90** | Primary standards with metadata, scope, and technical committee info. |
| **Verified Standards Records** | **8** | Standards with full BSB Edge manually verified portal data. |
| **Relationships in `relationships.json`** | **72** | Curated and verified explicit relationships. |
| **SQLite Explicit Relationships** | **16** | Explicit relationships stored in SQLite `standard_relationships`. |
| **SQLite Normative References** | **60** | Direct normative citations stored in `standard_references`. |
| **Unique Standards Across Graph Sources** | **128** | Total distinct standard identifiers participating in the graph topology. |
| **Standards in DB with >= 1 Direct Relationship** | **37** | 41.1% of curated catalogue standards have direct relationships. |
| **Relationships Missing Evidence** | **0 (0.0%)** | 100% of graph relationships have stored verbatim evidence snippets. |
| **Relationships with Explicit Extracted Clauses** | **128 (85.9%)** | Clause/section references (e.g. Clause 2, Foreword, Section 6) extracted. |

### Relationship Type Distribution
- `NORMATIVE_REFERENCE` / `REFERENCES`: 24 (33.3%)
- `ALLIED_STANDARD`: 17 (23.6%)
- `TEST_METHOD`: 13 (18.1%)
- `SUPERSEDES`: 8 (11.1%)
- `INSTALLATION_CODE` / `CODE_OF_PRACTICE`: 8 (11.1%)
- `SAFETY_STANDARD`: 1 (1.4%)
- `TERMINOLOGY_STANDARD`: 1 (1.4%)

### Provenance Distribution
- `VERIFIED` (BSB Edge portal / official foreword): 56 (77.8%)
- `CURATED` (Engineering research / gazette cross-reference): 16 (22.2%)
- `INFERRED`: 0 (0.0% — strictly prohibited by schema)

### Explicit Dataset Limitations
1. **Catalogue Scope:** The current graph encompasses 128 unique standards across high-frequency tender domains (Civil, Electrical, Valves, Pumps, Food Hygiene). It does not yet encompass all ~35,000 standards in the full national catalogue.
2. **Depth Scope:** Traversal is intentionally bounded to `depth=1` direct connections to maintain strict evidentiary grounding and prevent speculative multi-hop fallacies.

---

## 5. Verification Commands & Test Results

```bash
# 1. Graph API Contract Tests (15/15 passed)
pytest tests/test_graph_api.py -v

# 2. Existing Graph & Relationship Suites (52/52 passed)
pytest tests/test_milestone5_graph.py tests/test_phase9_relationships_regulatory.py tests/test_phase9_taxonomy_schema.py tests/test_milestone10_dependencies.py -q

# 3. Full Backend Suite (677/677 passed)
pytest -q

# 4. Frontend Production Build (Clean compilation in 1.78s)
npm run build --prefix frontend

# 5. Authoritative Ground Truth Checksum (Bit-for-bit unchanged)
sha256sum dataset/ground_truth/ground_truth.csv
8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc
```

---

## 6. Summary of Changes

- Updated `tests/test_graph_api.py` with 3 additional boundary tests:
  - `test_search_extreme_and_negative_limits`
  - `test_get_neighbors_zero_relationship_isolated_standard`
  - `test_get_neighbors_url_encoded_slash_standard`
- Created planning artifacts in `.planning/phases/23.1-browser-acceptance-and-evidence-audit/`.
- Zero alterations to recommendation scoring, audit engine logic, or ground truth data.
