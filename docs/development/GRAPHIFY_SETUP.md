# Graphify Setup & Developer Guide for Tender Saathi

## 1. Overview: What is Graphify & Why Tender Saathi Uses It

**Graphify** is an architectural intelligence and knowledge graph tool designed for codebases. It scans a repository to extract entities (classes, functions, methods, routes, concepts) and their relationships (imports, calls, uses, implementations, citations, references), constructs a networked graph, performs community detection (clustering), and generates queryable, interactive outputs.

### Codebase Knowledge Graph vs. Product-Level Standards Graph

It is critical to distinguish between two distinct graph systems in Tender Saathi:

1. **Codebase Knowledge Graph (Developer Tooling — Graphify)**:
   - **Scope**: Internal software architecture of Tender Saathi (`src/`, `api/`, `frontend/`, `tests/`, `docs/`).
   - **Purpose**: Helps AI assistants and human developers navigate module dependencies, verify test coverage, trace failure-propagation paths, and explore cross-cutting concerns across backend and frontend layers.
   - **Outputs**: Stored in `graphify-out/` (`graph.json`, `graph.html`, `GRAPH_REPORT.md`).
   - **Production Isolation**: **Never** invoked during production API requests or user tender audits.

2. **Standards Relationship Graph (Product Feature — Tender Saathi Core)**:
   - **Scope**: Bureau of Indian Standards (BIS) engineering codes (`IS 15778`, `IS 4985`, `IS/IEC 61439`, etc.).
   - **Purpose**: Traverses normative references, test methods, companion codes, and execution specifications at Depth-1 horizon to bundle complete engineering compliance requirements for procurement officers.
   - **Implementation**: Defined in `src/graph.py` and documented in `docs/architecture/relationship_graph.md`.

---

## 2. Installation Prerequisites & Commands

### Prerequisites
- Python 3.10+
- `uv` package and tool runner (recommended) or `pip` / `pipx`
- Git

### Installation Procedure
Install Graphify in an isolated environment using `uv tool`:

```bash
# Install the latest official Graphify CLI
uv tool install graphifyy

# If upgrading an existing installation:
uv tool install --upgrade graphifyy
```

### Verify Installation
```bash
graphify --version
graphify --help
```
*Current verified version: `graphify 0.9.92`.*

---

## 3. Google Antigravity Integration

Tender Saathi uses a project-scoped integration with Google Antigravity to keep developer instructions local to the repository:

```bash
graphify antigravity install --project
```

### Created Configuration Files
- **`.agents/rules/graphify.md`**: An `always_on` rule instructing Antigravity to consult `graphify-out/` before answering architectural or codebase navigation questions.
- **`.agents/workflows/graphify.md`**: Workflow definition for `/graphify`.
- **`.agents/skills/graphify/SKILL.md`**: Project-scoped copy of the full Graphify execution skill and reference manual.

---

## 4. Exclusion Rules & Sensitive File Handling

To prevent large data bloat, secret leakage, or accidental submission of sensitive tender documents, Tender Saathi defines `.graphifyignore` at the repository root.

### Excluded Directories & Patterns:
- **Environment & Secrets**: `.env`, `.env.*`, `*.secret`, `*.key`, `*.pem`
- **Large Databases & Binary Caches**: `data/` (`bis_catalogue.db`, `semantic_embeddings.npy`, `bm25_index.json`, normalized JSON catalogues)
- **Benchmark & Training Data**: `dataset/`
- **User / Sensitive Tender Uploads**: `tenders/` (raw uploaded tender PDFs)
- **Machine-Generated Test Run Reports**: `reports/generated/`, `reports/e2e/`, `scratch/`, `*.log`
- **Virtual Environments & Node Modules**: `.venv/`, `frontend/node_modules/`, `frontend/dist/`, `frontend/public/`
- **Test Caches**: `.pytest_cache/`, `.coverage`, `htmlcov/`

Git is configured via `.gitignore` to keep `graphify-out/` strictly local:
```gitignore
# Graphify local graph output
graphify-out/
```

---

## 5. Building & Updating the Graph

### Full Graph Generation
To generate or perform a fresh build of the knowledge graph:

```bash
# Run headless extraction (local AST on code)
graphify extract . --code-only

# Or run the step-by-step workflow with community labeling:
python3 -c "
from graphify.extract import collect_files, extract
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json
from pathlib import Path
import json

# Full pipeline runs AST extraction, builds graph, clusters communities, and writes graphify-out/
"
```

### Incremental Updates After Code Changes
When modifying application source files, refresh the graph incrementally without token cost:

```bash
graphify update .
```

### HTML Graph Visualization
Generate the standalone interactive browser visualization:

```bash
graphify export html
```
Output: `graphify-out/graph.html` (open directly in any modern browser).

---

## 6. Querying & Explaining the Codebase

Graphify provides fast, structured commands to inspect architecture without loading full files into LLM context:

### 1. Natural Language Traversal (`query`)
```bash
# BFS traversal answering a conceptual architectural question
graphify query "How does a tender requirement move from input to the final recommendation?"

# DFS path tracing with token budget cap
graphify query "Where does hybrid retrieval happen?" --budget 1500
```

### 2. Node Explanation (`explain`)
```bash
# Plain-language breakdown of a specific symbol and its connections
graphify explain "src_retrieval"
graphify explain "src_critic"
graphify explain "src_ai_understanding"
```

### 3. Shortest Relationship Path (`path`)
```bash
# Trace connection hops between two modules or symbols
graphify path "api_server" "src_critic"
graphify path "frontend_src_api_api" "src_audit"
```

### 4. Architectural Hubs (`god-nodes`)
```bash
# List top hub nodes by degree centrality
graphify god-nodes --top 10
```

---

## 7. Generated Output Files & Structure

All generated artifacts reside in `graphify-out/`:

| File | Purpose |
| :--- | :--- |
| `graphify-out/graph.json` | NetworkX-compatible JSON graph containing all nodes, links, and community labels. |
| `graphify-out/graph.html` | Standalone interactive 2D visualization (D3/Canvas) with search, filter, and community colors. |
| `graphify-out/GRAPH_REPORT.md` | Audit report detailing corpus check, summary metrics, God nodes, surprising connections, and questions. |
| `graphify-out/manifest.json` | Hash-based file manifest enabling instant incremental detection of changed source files. |
| `graphify-out/cost.json` | Execution token and cost audit log (0 token cost for local AST mode). |

---

## 8. Verified Architectural Insights

The generated graph (`2,430 nodes`, `5,611 edges`, `109 communities`) answers key architectural questions about Tender Saathi:

1. **Requirement Lifecycle**:
   - `Home.tsx` / `UnifiedInput.tsx` → `api.ts` → `api/server.py` (`/api/analyze`) → `src/audit.py` (`TenderAuditEngine`) → `src/recommend.py` (`StandardsRecommender`) → `src/critic.py` (`EvidenceAwareCritic`) → `Results.tsx` / `RequirementCard.tsx`.
2. **AI Understanding Layer**:
   - `src/ai_understanding.py` (`AIRequirementParser`) is called by `src/audit.py` and `src/decompose.py`, with full offline deterministic fallback if Groq API is unavailable.
3. **Hybrid Retrieval**:
   - `src/retrieval.py` (`HybridRetrievalEngine`) fuses Okapi BM25 (`src/bm25_search.py`), dense semantic embeddings (`src/semantic_search.py`), and Cross-Encoder neural reranking (`src/reranker.py`).
4. **Lifecycle & Supersedence**:
   - `src/validate.py` (`validate_standard_status()`) and `src/dependencies.py` validate `ACTIVE`, `SUPERSEDED`, or `WITHDRAWN` states and resolve active successors (e.g. `IS 10611` → `IS/ISO 10434`).
5. **Evidence Grounding Critic**:
   - `src/critic.py` (`EvidenceAwareCritic`) enforces the strict Candidate-Evidence Parity Invariant (`candidate_standard == evidence_standard`) and trust-gate downgrade when retrieval score is high but evidence is weak.
6. **Ambiguity & Human Review**:
   - `src/ambiguity.py` (`AmbiguityEngine`) classifies clauses into 6 ambiguity states (`CLEAR`, `AMBIGUOUS`, `INCOMPLETE`, `CONFLICTING`, `NO_RELIABLE_MATCH`, `OUT_OF_SCOPE`), and `src/audit.py` routes them into `READY_FOR_REVIEW`, `REVIEW_REQUIRED`, or `INSUFFICIENT_EVIDENCE`.
7. **Test Coverage**:
   - Every engine module has dedicated pytest suites (`tests/test_hybrid_retrieval.py`, `tests/test_milestone3_critic.py`, `tests/test_ambiguity.py`, `tests/test_applicability_multidomain.py`, `tests/test_tender_audit.py`, etc.). 506 / 506 tests passing.

---

## 9. Troubleshooting & FAQ

- **Q: Why does `graphify query` say command not found?**
  - Ensure `~/.local/bin` is in your `PATH` (default for `uv tool` installs). Run `export PATH="$HOME/.local/bin:$PATH"`.
- **Q: How to re-scan after deleting files or major refactoring?**
  - Run `graphify extract . --force --code-only` to bypass the shrink-guard and rebuild cleanly.
- **Q: Are tender documents or credentials uploaded to any cloud service?**
  - No. All code extraction and graph building is performed locally via tree-sitter AST parsing. `.graphifyignore` explicitly bars `.env` and `tenders/` from being processed.
