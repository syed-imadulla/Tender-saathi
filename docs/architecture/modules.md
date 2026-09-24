# Tender Saathi Module Reference

This document details the functional responsibilities and design contracts of the core modules in the **Tender Saathi** codebase (`src/` and `api/`).

---

## 1. Module Map

```text
src/
├── standards.py                # Database models, schemas, canonical relationship taxonomy
├── graph.py                    # StandardsGraph, relationship traversal & depth=1 boundary
├── dependencies.py             # Dependency bucketing, successor resolution & amendments
├── bm25_search.py              # Pure-Python Okapi BM25 lexical engine
├── semantic_search.py          # Dense vector semantic retrieval (all-MiniLM-L6-v2 + NumPy)
├── reranker.py                 # Neural cross-encoder reranker (ms-marco-MiniLM-L-6-v2)
├── retrieval.py                # Hybrid weighted score fusion ensemble
├── search.py                   # High-level search interface over SQLite databases
├── applicability.py            # Deterministic boundary gates & operating condition checks
├── ambiguity.py                # Decision-sensitive ambiguity detection & parameter extraction
├── completeness.py             # Specification completeness evaluation
├── attributes.py               # Engineering facet data models (DN, PN, material, fluid)
├── critic.py                   # Grounding verification critic & equivalence checks
├── evidence.py                 # Scope clause models & basic extraction
├── evidence_intelligence.py    # Provenance tracking, clause anchoring & evidence tiers
├── validate.py                 # Lifecycle status validation (ACTIVE, SUPERSEDED, WITHDRAWN)
├── decompose.py                # Compound multi-component requirement decomposition
├── ai_understanding.py         # Optional LLM parser (Groq API) with 100% offline fallback
├── extract.py                  # Layout-aware PDF/text extraction & boilerplate removal
├── gap_detection.py            # Missing standard detection & coverage analysis
├── recommend.py                # StandardsRecommender master engine
├── audit.py                    # TenderAuditEngine orchestrating tender-level audits
├── report.py                   # ReportGenerator for structured JSON and Markdown exports
├── eval_adversarial.py         # 70-probe adversarial evaluation harness & multi-dimensional grader
├── evaluate.py                 # Frozen 20-row benchmark evaluation & ablation harness
├── multilingual/               # Multilingual technical term normalizers (hi, kn, ta, mixed)
├── catalogue/                  # BIS catalogue ingestion, normalization, change detection & manifests
└── regulatory/                 # External statutory advisory layer (FSSAI, CEA, CPWD)
```

---

## 2. Core Retrieval & Search Modules

### `src/bm25_search.py` — Pure-Python Okapi BM25 Lexical Engine
- **Implementation**: Custom, zero-dependency, pure-Python Okapi BM25 formulation. Does **not** use the external `rank_bm25` package.
- **Formulation**:
  - Term frequency (TF) saturation with parameter $k_1 = 1.5$.
  - Document length normalization with parameter $b = 0.75$.
  - Inverse document frequency (IDF) using the Robertson-Spärck Jones formulation:
    $$\text{IDF}(q_i) = \ln\left(\frac{N - n(q_i) + 0.5}{n(q_i) + 0.5} + 1\right)$$
- **Role**: Ensures exact standard numbers (`IS 15778`, `IS/ISO 10434`) and specialized technical materials (`CPVC`, `XLPE`, `HACCP`) receive high lexical weights without semantic drift.

### `src/semantic_search.py` — Dense Semantic Embeddings
- **Model**: `all-MiniLM-L6-v2` from `sentence-transformers` (384-dimensional dense vectors).
- **Execution**: Computes vector cosine similarity directly using NumPy. Does not require heavyweight external vector databases (FAISS is not utilized).
- **Caching**: Embeddings and document hashes are precomputed and cached in `data/standards/semantic_embeddings.npy` for sub-millisecond retrieval latency.

### `src/retrieval.py` — Hybrid Score Fusion
- **Mechanism**: Combines Okapi BM25 lexical scores, dense semantic similarity scores, and deterministic component matches using weighted score fusion:
  $$\text{Score} = w_{\text{bm25}} \cdot S_{\text{bm25}} + w_{\text{sem}} \cdot S_{\text{sem}} + w_{\text{det}} \cdot S_{\text{det}}$$
- **Fallback**: Automatically degrades to pure lexical BM25 matching if dense embedding dependencies or models are unavailable.

### `src/reranker.py` — Cross-Encoder Neural Reranking
- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **Role**: Jointly encodes the query requirement and candidate standard title/scope, computing fine-grained token-level cross-attention for top candidates.

---

## 3. Engineering Safety & Boundary Modules

### `src/applicability.py` — Deterministic Boundary Gates
- **Purpose**: Applies strict engineering rules that veto ungrounded semantic matches.
- **Key Gates**:
  - `OperatingConditionBounds`: Validates thermal limits (steam vs. chilled water), pressure classes (gravity sewer vs. high-pressure main), and chemical environment (acidic slurry vs. potable drinking water).
  - `DutyMode`: Distinguishes submersible borehole pumps (`IS 8034`) from industrial surface centrifugal pumps (`IS 1520`).
  - `ContradictionDetection`: Detects voltage mismatches (e.g. Low Tension 1.1 kV cable paired with High Tension 33 kV specification) and material conflicts.
  - `HeadNounRetrieval`: Isolates the syntactic head noun (e.g., in *"water pump control panel"*, isolates *control panel* as primary item and *water pump* as application context).

### `src/ambiguity.py` — Decision-Sensitive Ambiguity Engine
- **Purpose**: Analyzes requirement completeness before allowing candidate recommendation.
- **Facet Extraction**: Uses pattern-based and syntactic analyzers to extract 5 mandatory dimensions:
  1. Equipment / Product Type
  2. Nominal Diameter (DN)
  3. Pressure Class (PN)
  4. Material / Metallurgy
  5. Fluid Medium / Service
- **Decision States**: Emits `CLEAR`, `AMBIGUOUS_COMPETING`, `INCOMPLETE`, or `NO_RELIABLE_MATCH`.
- **Human Review Routing**: Triggers `human_review_required = True` when critical missing parameters prevent confident selection.

### `src/critic.py` & `src/evidence_intelligence.py` — Grounding Critic
- **Invariant Enforcement**: Validates that every non-null recommendation satisfies:
  $$\text{candidate\_standard} == \text{evidence\_standard}$$
- **Provenance Tiers**: Tracks evidence authenticity (`OFFICIAL_PRIMARY`, `OFFICIAL_SECONDARY`, `VERIFIED`, `CURATED`, `INFERRED`). Inferred data is strictly barred from serving as primary recommendation evidence.
- **Clause Anchoring**: Extracts verbatim scope excerpts and cross-references them against candidate titles.

---

## 4. Standards Intelligence & Regulatory Modules

### `src/standards.py` — Data Models & Canonical Taxonomy
- **Database Schema**: Manages SQLite connections and queries for `data/standards/standards.db` and `data/catalogue/bis_catalogue.db`.
- **Canonical Taxonomy**: Defines the 8 canonical standard relationship types (`CANONICAL_RELATIONSHIP_TYPES`):
  1. `NORMATIVE_REFERENCE`
  2. `TEST_METHOD`
  3. `INSTALLATION_CODE`
  4. `SAFETY_STANDARD`
  5. `TERMINOLOGY_STANDARD`
  6. `ALLIED_STANDARD`
  7. `SUPERSEDES`
  8. `AMENDS`
- **Metadata**: Models `AmendmentMetadata` (number, date, status) and `StandardRelationship` with strict provenance invariants.

### `src/graph.py` — Standards Relationship Graph
- **Class**: `StandardsGraph`.
- **Strict Provenance Invariant**: Loads only `VERIFIED` and `CURATED` relationships. Relationships with provenance `INFERRED` are rejected from production graph traversal.
- **Depth=1 Boundary**: Limits traversal to direct (depth=1) relationships to eliminate cycle traps and runaway transitive over-retrieval.

### `src/dependencies.py` — Dependency Analysis & Successor Resolution
- **Lifecycle Analysis**: Identifies active, superseded, and withdrawn dependencies.
- **Successor Resolution**: When a superseded standard is cited or retrieved, automatically resolves and surfaces the active successor code (e.g. `IS 10611` $\rightarrow$ `IS/ISO 10434`).
- **Dependency Bucketing**: Categorizes companion standards into typed buckets (`normative_references`, `test_methods`, `installation_codes`, `safety_standards`, `companion_standards`).

### `src/regulatory/external_authority.py` — Statutory Advisory Layer
- **Authorities**:
  - `FSSAI` (Food Safety and Standards Authority of India) — *Packaging Regulations, 2018*.
  - `CEA` (Central Electricity Authority) — *Safety and Electric Supply Regulations, 2023*.
  - `CPWD` (Central Public Works Department) — *Works Specifications 2019 / 2023*.
- **Architectural Boundary**: External regulations reside exclusively in this decoupled advisory registry. They are **never** injected into `standards.db` or `bis_catalogue.db`, cannot become candidate standards, and always carry the statutory advisory disclaimer.

---

## 5. Master Engines & Application Surface

### `src/recommend.py` — Master Recommender (`StandardsRecommender`)
- Orchestrates retrieval, applicability checking, ambiguity detection, evidence grounding, relationship traversal, and multi-component bundle recommendation.
- Ensures safe abstention isolation: in multi-component tenders, abstention on one ambiguous component does not discard valid recommendations on an unambiguous companion component.

### `src/audit.py` — Master Audit Engine (`TenderAuditEngine`)
- Coordinates the complete tender-level audit process.
- Populates the Prioritized Human Review Queue across 4 categories:
  1. `UNCONFIRMED_STANDARD`
  2. `MISSING_TECHNICAL_PARAMETERS`
  3. `WITHDRAWN_SUPERSEDED_STANDARD`
  4. `AMBIGUOUS_COMPETING_STANDARDS`
- Computes tender-level operational readiness states (`READY_FOR_REVIEW`, `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`).

### `src/report.py` — Report Generator (`ReportGenerator`)
- Generates comprehensive, timestamped audit reports in structured JSON and formatted Markdown.
- Formats executive summaries, requirement breakdown tables, evidence chains, lifecycle warnings, dependency matrices, and human review queues.

### `api/server.py` — Flask REST API Server
- Thin, secure REST API adapter serving the React frontend.
- Implements 12 active endpoints covering health checks, plain text analysis, PDF audit, image OCR ingestion, sample demo cases, report exports, human review submission, and capability disclosure.
- Restricts CORS to development origins and ensures zero server secrets (`GROQ_API_KEY`) leak to client responses.
