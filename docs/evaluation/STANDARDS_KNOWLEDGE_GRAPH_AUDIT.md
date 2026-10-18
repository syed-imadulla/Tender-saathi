# Standards Knowledge Graph Capability Audit

**Document:** `docs/evaluation/STANDARDS_KNOWLEDGE_GRAPH_AUDIT.md`  
**Date:** 2026-10-18  
**Audit Type:** Read-Only Architectural & Empirical Capability Audit  
**Target:** Tender Saathi Local Repository (`/home/syed-imadulla/Desktop/Tender_Saathi`)  
**Status:** Complete

---

## Executive Summary

A comprehensive read-only audit of the Tender Saathi codebase was performed to evaluate whether the application possesses a **Standards Knowledge Graph** comparable to a web interface displaying Indian Standards as nodes and relationships as edges, with search, node selection, and graph navigation.

### Key Finding

| Capability Dimension | Current Status | Description |
| :--- | :--- | :--- |
| **A. Standards Relationship Data** | **EXISTS (Curated Subgraph)** | 72 verified relationships in `data/standards/relationships.json`, 16 relationships + 60 normative references in `data/standards/standards.db` across 146 unique standard nodes in 5 demonstration domains. 0 `INFERRED` edges. |
| **B. Backend Graph Traversal / API** | **PARTIAL (Backend Logic Exists, No Dedicated API)** | `src/graph.py` (`StandardsGraph`) and `src/dependencies.py` provide deterministic depth=1 relationship queries and evidence grounding. However, **no dedicated REST endpoint exists** in `api/server.py` to serve graph data, node lookups, or neighbor subgraphs directly to a client. Graph data is only exposed as embedded `related_standards` lists inside tender requirement analysis results. |
| **C. User-Facing Interactive Graph Page** | **DOES NOT EXIST** | The frontend (`frontend/src/`) contains only 3 pages (`Home.tsx`, `Analyzing.tsx`, `Results.tsx`). In `Results.tsx`, related standards are rendered as flat, non-interactive text cards (`RelatedCard`). There are **no graph visualization libraries installed** (0 references to React Flow, Cytoscape.js, D3, Vis.js, or Canvas/SVG network viewers in `package.json`). No search-and-explore graph page exists. |

> [!NOTE]
> **Disambiguation:** The repository contains a Graphify code-architecture knowledge graph located at `graphify-out/` and configured under `.agents/skills/graphify/`. That graph models repository source code (modules, functions, classes) for development agents, and must **not** be confused with an Indian Standards domain knowledge graph.

---

## 1. Inspection of Existing Implementation

### 1.1 Frontend Structure & Visualisation Capabilities
- **Routes & Pages (`frontend/src/App.tsx`, `frontend/src/pages/`):**
  - Only three pages exist:
    1. [`Home.tsx`](../../frontend/src/pages/Home.tsx): Document input (paste text, upload PDF, upload image, or select demo).
    2. [`Analyzing.tsx`](../../frontend/src/pages/Analyzing.tsx): Stepped progress indicator during ingestion/analysis.
    3. [`Results.tsx`](../../frontend/src/pages/Results.tsx): Multi-section requirement recommendation dashboard.
  - **No router** (e.g. `react-router-dom`) is installed. State navigation is managed via a simple local union state: `type AppState = 'home' | 'analyzing' | 'results'`.
- **Dependencies (`frontend/package.json`):**
  - Dependencies: Only `"react": "^18.3.1"` and `"react-dom": "^18.3.1"`.
  - Visualization packages: **None**. Neither `react-flow-renderer`, `@xyflow/react`, `cytoscape`, `d3`, `vis-network`, `sigma.js`, nor any canvas graph library are present.
- **Related Standards Display (`frontend/src/components/RequirementCard.tsx`):**
  - Section 4 of `Results.tsx` renders `relatedStandardsList` using [`RelatedCard`](../../frontend/src/components/RequirementCard.tsx#L483-L525).
  - This is a flat card showing standard number, relationship type label (e.g. *"Normative reference from IS 15000"*), and a *"See why \u2192"* button opening the requirement evidence drawer. It does **not** provide node-edge visualization, panning, zooming, or graph topology navigation.

### 1.2 Backend Routes & APIs (`api/server.py`)
Inspecting all 12 registered route decorators in [`api/server.py`](../../api/server.py):
- System: `GET /api/health`, `GET /api/capabilities`
- Intake & Analysis: `POST /api/analyze/text`, `POST /api/analyze/pdf`, `POST /api/analyze/image`, `GET /api/analyze/sample/<demo>`
- Reports: `GET /api/report/<tender_id>/json`, `GET /api/report/<tender_id>/markdown`, `GET /api/report/json`, `GET /api/report/markdown`
- Human Review: `POST /api/tender/<tender_id>/review`, `GET /api/tender/<tender_id>/review`

**Finding:** There are **zero** API endpoints dedicated to querying the standards graph (e.g. `GET /api/standards`, `GET /api/standards/<id>/graph`, `GET /api/standards/<id>/neighbors`, or `GET /api/standards/search`). The frontend cannot query standards or inspect graph neighbors without submitting an entire tender document for recommendation.

### 1.3 Core Graph & Precedence Modules
- **`src/graph.py` (`StandardsGraph`):**
  - Implements [`StandardsGraph`](../../src/graph.py#L147-L512), backed by `StandardsDatabase` and `data/standards/relationships.json`.
  - Methods:
    - [`get_direct_relationships(standard_identifier, depth=1)`](../../src/graph.py#L186-L355): Queries both SQLite tables (`standard_relationships`, `standard_references`) and JSON file relationships for incoming and outgoing edges. Strictly enforces `depth=1` (raises `ValueError` if `depth != 1`).
    - [`get_related_standards(standard_identifier, limit=10)`](../../src/graph.py#L357-L452): Discovers direct neighbors, resolves metadata and lifecycle status via [`_resolve_standard_info`](../../src/graph.py#L454-L490), sets evidence strength (`STRONG`, `MODERATE`, `WEAK`), and assigns advisory review notes.
    - [`explain_relationship(source_identifier, target_identifier)`](../../src/graph.py#L491-L511): Returns a human-readable evidence explanation between two standards.
- **`src/standards.py`:**
  - Defines the canonical taxonomy:
    ```python
    CANONICAL_RELATIONSHIP_TYPES = {
        "NORMATIVE_REFERENCE",
        "TEST_METHOD",
        "INSTALLATION_CODE",
        "SAFETY_STANDARD",
        "TERMINOLOGY_STANDARD",
        "ALLIED_STANDARD",
        "SUPERSEDES",
        "AMENDS",
    }
    ```
  - Defines legacy aliases (`LEGACY_RELATIONSHIP_ALIASES`) mapping `CODE_OF_PRACTICE`, `INSTALLATION_STANDARD`, `REFERENCES`, `SUPERSEDED_BY`, `IDENTICAL_ADOPTION`, etc., to canonical types.
  - Enforces provenance invariants: `ALLOWED_PROVENANCE_LEVELS = {"VERIFIED", "CURATED"}`. Rejects `INFERRED` with `ValueError`.
  - Schema defines SQLite tables: `standards`, `standard_references`, `standard_relationships`.
- **`src/dependencies.py` (`StandardsDependencyEngine`):**
  - Uses `StandardsGraph` to analyze primary requirement candidates against the standards ecosystem, evaluating whether linked test methods, installation codes, and normative dependencies are contextually applicable or require review.
- **`src/precedence/conflict_engine.py` (`CrossRequirementConflictEngine`):**
  - Evaluates pairwise cross-requirement systemic interactions (shared equipment contradictions, parameter overrides, edition divergences, product vs. installation co-applicability) across multiple tender requirements.

---

## 2. Verification of Catalogue & Relationship Completeness

### 2.1 Database & Catalogue Inventory

| Data Store | Path | Record Count | Full Text Available | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Curated Standards DB** | `data/standards/standards.db` | **90** standards | **0** full text (90 have Scope text) | Active working database used by recommender and graph engine. 75 Active, 15 Withdrawn. 13 VERIFIED, 77 CURATED. |
| **BIS Bulk Catalogue DB** | `data/catalogue/bis_catalogue.db` | **35,208** standards | **0** full text | Ingested BIS catalogue snapshot containing metadata (standard number, title, committee, year, status). **Contains zero relationship tables or edge data.** |
| **Intermediate Catalogue DB** | `data/catalogue/catalogue.db` | 502 standards | 0 full text | Snapshot table; relationship and reference tables have 0 rows. |
| **Corpus Database** | `data/standards/corpus.db` | **0** documents | 0 | `corpus_documents`, `corpus_pages`, and `corpus_passages` tables all contain 0 records. |
| **Tender PDFs** | `data/tenders/`, `tenders/raw/` | 20 tender PDFs | 20 tenders (T001\u2013T020) | Only tender solicitation documents have full text in repository. No standards PDFs exist. |

### 2.2 Relationship Dataset Counts & Breakdown

#### Source 1: `data/standards/relationships.json` (72 Edges)
- **Total relationships:** 72
- **Provenance:** 56 `VERIFIED` (77.8%), 16 `CURATED` (22.2%), 0 `INFERRED` (0.0%).
- **Sources:** 56 `BSB_EDGE_MANUALLY_VERIFIED`, 16 `CURATED_STANDARDS_DOC`.
- **Breakdown by Relationship Type:**
  - `NORMATIVE_REFERENCE`: 22
  - `ALLIED_STANDARD`: 17
  - `TEST_METHOD`: 13
  - `SUPERSEDES`: 8
  - `INSTALLATION_CODE`: 4
  - `CODE_OF_PRACTICE`: 2
  - `INSTALLATION_STANDARD`: 2
  - `REFERENCES`: 2
  - `SAFETY_STANDARD`: 1
  - `TERMINOLOGY_STANDARD`: 1

#### Source 2: `data/standards/standards.db` (16 Explicit Edges + 60 References)
- **`standard_relationships` table (16 rows):**
  - `SUPERSEDES`: 7
  - `SUPERSEDED_BY`: 3
  - `REFERENCES`: 3
  - `CODE_OF_PRACTICE_FOR`: 2
  - `IDENTICAL_ADOPTION`: 1
- **`standard_references` table (60 rows):**
  - 60 normative references, all linked to source standards with `citing_clause = 'Clause 2 References'`.

#### Unified Graph Scope:
- **Total unique standard nodes involved in relationships:** **146** standards.
- **Demonstration Domains Covered:**
  1. *Civil & Water Distribution* (IS 15778, IS 4985, IS 7634, IS 12235, IS 458, IS 783, IS 8329, IS 1239)
  2. *Electrical Systems* (IS 7098, IS 694, IS 1554, IS 1255, IS 732, IS 3043)
  3. *Mechanical & Fluid Control* (IS 778, IS 14846, IS 10434, IS 10611, IS 13095)
  4. *Pumping Machinery* (IS 8034, IS 9079, IS 14220, IS 9283, IS 5120)
  5. *Food & Canteen Hygiene* (IS 15000 / HACCP, IS 2491, IS 10146, IS 10171)

### 2.3 Quality, Provenance & Trustworthiness Assessment

1. **Are relationships verified, inferred, or merely imported?**
   - They are strictly **`VERIFIED`** or **`CURATED`**.
   - No edges are synthetically generated or LLM-hallucinated. `StandardRelationship.__post_init__` actively rejects `INFERRED` provenance with a `ValueError`.
   - Verified edges derive from manual verification of BIS gazettes, BSB Edge portal data, and official Foreword/Scope clauses.
2. **Is relationship provenance and source clause stored?**
   - **Yes.** Every edge in `relationships.json` and `standards.db` has an `evidence` text string.
   - For example:
     - `IS 15000 : 2024` $\rightarrow$ `IS 2491 : 2024`: *"Clause 2 Normative References explicitly cites IS 2491 for Food Hygiene - General Principles."*
     - `IS/ISO 10434 : 2020` $\rightarrow$ `IS 10611 : 1983`: *"National Foreword explicitly states: 'This standard supersedes IS 10611 : 1983 Steel gate valves...'"*
   - In `src/graph.py` (line 102), `evidence_clause` is parsed dynamically from evidence text (`Clause \d+`, `Foreword`, `Section \d+`, `Annex [A-Z]`).
3. **Are supersession and edition relationships trustworthy?**
   - **Yes, highly trustworthy.** Supersession edges directly link withdrawn standards to active replacements with explicit foreword citations.
   - The engine correctly reverses `SUPERSEDED_BY` into `SUPERSEDES` with inverted direction, so querying either the obsolete standard or the new standard correctly identifies the replacement.
4. **Can the graph search a standard and isolate direct neighbors?**
   - **Yes, in Python code.** Calling `StandardsGraph.get_direct_relationships("IS 15778", depth=1)` reliably returns its 4 direct neighbors (IS 12235, IS 7634, IS 4985, etc.).
   - However, **no user or web client can currently do this**, because no API endpoint or frontend search UI exists for it.

---

## 3. Capabilities Gap Matrix

| Functional Requirement | Backend Status | API Status | Frontend UI Status | Gap Severity |
| :--- | :--- | :--- | :--- | :--- |
| **Store Standards & Metadata** | Complete (90 curated in `standards.db`, 35,208 in `bis_catalogue.db`) | None (no standalone catalogue endpoint) | None | Medium |
| **Store Typed Relationships & Clauses** | Complete (8 canonical types, 146 unique nodes, 72 file edges + 76 DB edges) | None | None | Low (data exists) |
| **Strict Depth=1 Graph Traversal** | Complete (`StandardsGraph.get_direct_relationships`) | None | None | Low (logic exists) |
| **Search Standard in Graph** | Complete in Python (`_normalize_id`, digit extraction) | None (`api/server.py` lacks `/api/standards/search`) | None | High |
| **Isolate Direct Neighbors Subgraph** | Complete in Python (`get_direct_relationships`) | None (`api/server.py` lacks `/api/standards/<id>/graph`) | None | High |
| **Graph Visualization Canvas** | N/A | N/A | **Missing** (0 graph rendering packages, no SVG/Canvas network) | Critical |
| **Node Inspection Drawer / Details** | Backend has `explain_relationship` & `_resolve_standard_info` | None | Only flat `RelatedCard` in tender results | High |
| **Evidence / Provenance Display** | Stored in edge data (`evidence`, `provenance`, `confidence`) | Only inside tender requirement payload | Embedded in modal only | Medium |

---

## 4. Recommendation: Feasibility of Building an Interactive Graph

### Can an interactive Standards Graph be built safely with existing data?
**YES.** The repository already possesses high-quality, verified relationship data and robust traversal logic. Building an interactive web interface is feasible and safe, provided strict architectural guardrails are respected.

### Recommended Architectural Plan

1. **Backend Layer (`api/server.py`):**
   - Expose read-only graph endpoints wrapping existing `StandardsGraph` methods without altering any scoring or recommendation logic:
     - `GET /api/standards/graph`: Returns the full curated graph (nodes, edges, categories) for visual overview.
     - `GET /api/standards/<standard_id>/neighbors`: Returns direct (depth=1) incoming and outgoing neighbors for a selected node.
     - `GET /api/standards/search?q=...`: Searches standards by number or title in `standards.db`.
2. **Frontend Layer (`frontend/`):**
   - Add a dedicated navigation tab or page: e.g., `/graph` or a **"Standards Graph"** view in the header alongside "Check Tender".
   - Implement an interactive canvas/SVG graph component (e.g. using a lightweight, performant library or standard SVG force layout) supporting:
     - Search bar with autocomplete for standard numbers (e.g. "IS 15778", "IS 7098", "IS 10434").
     - Node selection highlighting the focal standard and its immediate depth=1 neighbors.
     - Edge badges displaying typed relationships (`SUPERSEDES`, `NORMATIVE_REFERENCE`, `TEST_METHOD`, `INSTALLATION_CODE`, etc.).
     - Side drawer showing node metadata (title, status, year, committee) and edge evidence (verbatim clause, provenance, confidence).
3. **Mandatory Safety & Governance Guardrails:**
   - **Enforce Depth=1 Boundary:** Do not allow multi-hop speculative pathing in production.
   - **Preserve Non-Applicability Disclaimer:** Visualizing an edge must **never** imply that the related standard is automatically required in a tender. Clear labels must specify: *"Related standard in BIS knowledge graph for engineering co-application review"*.
   - **Read-Only / No Pipeline Interference:** The graph viewer must read directly from `StandardsGraph` / `StandardsDatabase` without touching benchmark datasets, evaluation scripts, or recommendation thresholds.

---

## 5. Summary & Verdict

The Tender Saathi repository contains **the complete foundational knowledge graph data and backend traversal logic** (`src/graph.py`, `src/dependencies.py`, `data/standards/relationships.json`, `data/standards/standards.db`). 

However, **it completely lacks the web presentation layer**: there are no backend graph API routes, no frontend graph visualization dependencies, and no interactive graph explorer page.

An interactive Standards Knowledge Graph can be developed straightforwardly on top of the existing backend without modifying any existing recommendation logic, ground truth benchmarks, or safety gates.
