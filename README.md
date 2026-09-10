# TenderSaathi

**Evidence-backed Indian Standards validation for procurement specifications.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-130%2F130%20Passing-brightgreen.svg)]()
[![Top-1 Accuracy](https://img.shields.io/badge/Top--1%20Benchmark-95.0%25-success.svg)]()
[![Top-3 Recall](https://img.shields.io/badge/Top--3%20Benchmark-100.0%25-success.svg)]()
[![MRR](https://img.shields.io/badge/MRR-0.975-blueviolet.svg)]()
[![Stage](https://img.shields.io/badge/Milestone-M8%20AI%20%2B%20Reranking-orange.svg)]()

> **“AI interprets. Retrieval finds. Reranking prioritizes. Rules validate. Evidence supports. Humans decide.”**


---

## SIH Problem Statement

- **Hackathon**: Smart India Hackathon 2026
- **Problem Statement ID**: SIH26108
- **Title**: *AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications*
- **Theme**: Smart Automation / Public Procurement
- **Team**: Base Case

*Scope Note:*
- **The Presentation (PPT)** outlines our complete solution vision, including full-scale BIS integration, hybrid retrieval, web interface, and platform connectors.
- **This Repository** documents our validated core intelligence prototype, proving feasibility on real government tenders.

---

## Problem

In Indian public procurement (conducted through portals such as CPPP and GeM, and departments including CPWD, MES, and Indian Railways), technical specifications are expected to refer to national standards where available, in line with public procurement guidelines such as General Financial Rules (GFR) 2017 (Rule 144). In practice, procurement tenders routinely face three critical challenges:

1. **Omitted Standards**: Work items and materials (e.g., CPVC piping, sewerage lines, underground cables) are frequently specified without citing mandatory Indian Standard (`IS`) codes.
2. **Obsolete & Superseded Citations**: Reused tender templates often cite withdrawn or replaced standards (e.g., citing `IS 10611` instead of `IS/ISO 10434`, or `IS 780` instead of `IS 14846`).
3. **Ambiguous Specifications**: Clauses specify generic work (e.g., "valve replacement") while omitting essential engineering parameters (diameter/DN, pressure/PN, metallurgy, medium).

### Why Existing Search and Generic AI Fall Short
- **Standard Keyword Search**: Matches literal query terms without understanding missing-specification gaps, technical context, or standards lifecycle changes.
- **Generic AI Chatbots**: Lack an authoritative standards database, hallucinate plausible but non-existent standard numbers, and cannot provide verifiable audit evidence.

---

## Solution

TenderSaathi is an audit and recommendation system that starts directly from procurement requirements, identifies applicable Indian Standards, validates their active/superseded status, traces explicit relationships, presents supporting scope evidence, computes confidence, and routes ambiguous cases to human engineers.

> **"We don't just recommend standards. We audit the tender against the standards it should contain."**

---

## Why TenderSaathi is Different

| Dimension | Standard Keyword Search | Generic LLM Chat | TenderSaathi (Our Approach) |
|---|---|---|---|
| **Query Starting Point** | Requires knowing the IS number | Free-form prompt | Starts from tender requirement text |
| **Lifecycle Awareness** | None (matches text blindly) | Outdated knowledge cutoffs | Validates Active, Superseded, Withdrawn |
| **Supersedence Traversal** | Cannot resolve replacements | Inconsistent / Hallucinates | Resolves authoritative successors (`IS/ISO`) |
| **Audit Evidence** | None (only highlights hits) | Cannot cite verified clauses | Verbatim scope excerpts + provenance source |
| **Ambiguity Handling** | Returns irrelevant hits | Forces an ungrounded guess | Heuristic gating to human review |
| **Fabrication Risk** | Low (keyword only) | High (hallucinates fake IS numbers) | Bounded (no fake IDs outside catalogue) |

> **"Finding a standard is not the same as validating a standard."**

---

## How It Works

The engine processes tenders through a multi-stage deterministic pipeline:

1. **Extraction & Noise Removal**: Ingests tender PDFs/text, filters administrative boilerplate (EMD, fees, bidding rules), and isolates technical requirements.
2. **Category Classification**: Classifies clauses into functional categories (`material`, `product_equipment`, `installation_execution`, `general_specification`).
3. **Standards Retrieval**: Matches requirements against the standards catalogue using exact/partial numbers, title/scope matches, token overlap, and domain boosting.
4. **Lifecycle & Relationship Validation**: Checks active status and resolves explicit relationships (`SUPERSEDES`, `REFERENCES`, `CODE_OF_PRACTICE_FOR`).
5. **Evidence Grounding**: Retrieves verbatim scope text and assigns provenance from verified source records.
6. **Ambiguity Gating**: Evaluates parameter sufficiency; routes under-specified cases to human engineers rather than guessing.

---

## Technical Architecture

```text
Tender Document (PDF / Plain Text)
            ↓
Document / Text Extraction (PyMuPDF Layout Parsing)
            ↓
Requirement Extraction & Noise Filtering (Boilerplate Stripping)
            ↓
Requirement Classification (Material / Product / Installation / General)
            ↓
Standards Retrieval (Number Match + Title/Scope Match + Token Overlap + Domain Boost)
            ↓
Lifecycle + Relationship Validation (Active / Superseded / Withdrawn Graph Traversal)
            ↓
Evidence Grounding (Verbatim Scope Excerpts & Provenance Tracking)
            ↓
Confidence / Ambiguity Analysis (Engineering Parameter Completeness Check)
            ↓
Decision Gate
     ├── Sufficient Information  ──► Grounded Recommendation + Alternatives
     └── Insufficient Parameters ──► Flagged for Human Engineer Review
```

---

## Current Prototype

The repository implements a functional feasibility prototype demonstrating the core intelligence layer:

- **PDF & Text Extraction** (`src/extract.py`): Ingests PDFs page-by-page via `pymupdf`, removes boilerplate clauses, segments technical text, and detects cited IS codes via regex.
- **Classification Engine** (`src/extract.py`): Automatically assigns domain categories to target candidate search space.
- **Standards Knowledge Base** (`data/standards/standards.db`): A local SQLite database indexing 85 curated Indian Standards across civil, mechanical, electrical, and food safety sectors.
- **Retrieval Engine** (`src/search.py`): Deterministic multi-factor retrieval based on:
  - Exact and partial standard number matching
  - Direct supersedence lookup via graph relations
  - Title and scope phrase matching
  - Token overlap scoring with domain stop-word filtering
  - Domain-specific keyword boosting (e.g., CPVC, sluice, earthing, XLPE cable, precast pipe)
  - Generic handbook deprioritization (boosting product standards over general SP handbooks)
- **Validation Engine** (`src/validate.py`): Checks `Active`, `Superseded`, `Withdrawn`, or `Unknown` states and retrieves documented successors.
- **Evidence Engine** (`src/evidence.py`): Grounding against stored scope clauses and metadata; returns explicit notice of insufficient evidence when ungrounded.
- **Recommender Pipeline** (`src/recommend.py`): Integrates all stages, scores confidence (High, Medium, Low), and applies heuristic ambiguity checks.
- **Terminal CLI** (`scripts/demo.py`): Interactive presentation runner outputting structured evaluation cards.
- **Evaluation Harness** (`src/evaluate.py`): Automated benchmark harness evaluating accuracy, recall, and MRR.

*Current Retrieval vs. Future Vision:*
The current prototype utilizes deterministic token overlap, title/scope phrase matching, domain-keyword boosting, and explicit graph traversal. Formal BM25 scoring, semantic vector embeddings, and an LLM explanation layer are planned for future phases.

---

## Milestone 8: AI Requirement Understanding & Neural Candidate Reranking

Milestone 8 evolves TenderSaathi from a hybrid retrieval + deterministic recommendation engine into an **Evidence-Grounded Hybrid AI Recommendation Engine**:

```
Tender language
      ↓
AI requirement understanding
      ↓
Structured technical facets
      ↓
Retrieval
      ↓
Candidate standards
      ↓
Cross-encoder reranking
      ↓
Evidence + lifecycle + graph
      ↓
Critic
      ↓
Human review
```

### 1. AI Requirement Understanding (`src/ai_understanding.py`)
- **Core Role**: The LLM does not recommend the Indian Standard. It understands the procurement requirement and converts it into structured technical facets. Retrieval, evidence, lifecycle, graph, and critic layers determine the final recommendation.
- **Architecture**: Groq (`openai/gpt-oss-120b`) (Fallback: Deterministic Requirement Decomposition). OpenRouter is an optional explicitly configured provider, not an automatic fallback.
- **Fallback Behavior**:
  - Primary provider: Groq (`openai/gpt-oss-120b`).
  - If Groq is unavailable, disabled, unconfigured, times out, or returns malformed output, TenderSaathi falls back to the existing deterministic requirement decomposition.
- **Function**: Converts messy natural-language tender clauses into strict structured technical fields (`equipment`, `control`, `electrical`, `voltage`, `application`, `work_type`).
- **Critical Safety Guardrails**:
  - The LLM **NEVER** selects an Indian Standard, invents an IS code, or declares compliance.
  - The LLM **NEVER** generates evidence, lifecycle status, BIS relationships, or legal compliance decisions.
  - The LLM is **NEVER** treated as:
    - the source of truth
    - the standards database
    - the compliance authority
    - the evidence generator
    - the final decision maker
  - Any standard numbers or IS codes in LLM outputs are automatically stripped and ignored.
  - The system is **100% functional offline**.

### 2. Second-Stage Neural Candidate Reranking (`src/reranker.py`)
- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (~90 MB, 22.7M parameters).
- **Operation**: Operates over the candidate pool (~10 candidates) produced by Stage 1 (BM25 + `all-MiniLM-L6-v2` + Deterministic). Computes full token-level cross-attention over `(query, candidate_standard_metadata)`.
- **Score Normalization**: Raw unbounded logits are normalized via standard logistic sigmoid:
  `score = 1 / (1 + exp(-logit))` (or $\sigma(\text{logit}) = 1 / (1 + \exp(-\text{logit}))$)
- **Score Transparency**: Tracks individual score contributions (`bm25_score`, `semantic_score`, `deterministic_score`, `reranker_score`, `final_score`). Retrieval scores represent relevance signals, **not evidence strength**.
- **Exact Citation Protection**: Authoritative matches and explicitly cited IS numbers retain priority and cannot be displaced by neural reranker drift.
- **Honest Latency & Tradeoff Disclosure**:
  - *Warm Retrieval Latency*: Hybrid = **57.0 ms** | Hybrid + Cross-Encoder = **488.1 ms**.
  - The Cross-Encoder is used only as a second-stage precision reranker over a small candidate pool. This increases warm retrieval latency compared with the hybrid baseline, but avoids running expensive cross-attention across the full standards catalogue.
  - `ms-marco-MiniLM-L-6-v2` is a general-domain English passage ranking model pre-trained on MS MARCO. It is not pre-trained on BIS technical gazettes, and is benchmarked transparently.

### 3. Milestone 8 Benchmark Ablation
Milestone 8 preserved the existing benchmark accuracy while adding AI-based requirement understanding and neural candidate reranking.

| Architecture | Top-1 | Top-3 | MRR | Warm Latency |
|---|---|---|---|---|
| Deterministic | 95.0% | 100.0% | 0.975 | 16.2 ms |
| BM25 | 90.0% | 100.0% | 0.950 | 19.8 ms |
| Semantic (`all-MiniLM-L6-v2`) | 85.0% | 95.0% | 0.912 | 46.3 ms |
| Hybrid | 95.0% | 100.0% | 0.975 | 57.0 ms |
| Hybrid + Cross-Encoder | 95.0% | 100.0% | 0.975 | 488.1 ms |

### 4. Core Operating Principles
> **“AI interprets. Retrieval finds. Reranking prioritizes. Rules validate. Evidence supports. Humans decide.”**

- **LLM ≠ source of truth**
- **Retrieval score ≠ evidence strength**
- **Graph relationship ≠ applicability**

### 5. Environment & Credential Security
- Groq API key is stored in local `.env`.
- `.env` is strictly ignored by Git (`.gitignore`).
- `.env.example` contains placeholders only (`GROQ_API_KEY=<your-groq-api-key>`).
- API keys are never hard-coded in source code.
- Missing or empty API key triggers deterministic fallback without crashing or sending network traffic.
- API keys and authorization headers are never logged or exposed in error messages.
- No credentials are included in screenshots, tests, or documentation.

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(empty)* | Groq API key for AI requirement understanding |
| `TENDERSAATHI_LLM_ENABLED` | `false` | Enable/disable LLM requirement parser (`true` / `false`) |
| `TENDERSAATHI_LLM_PROVIDER` | `groq` | LLM provider (`groq` or `openrouter`) |
| `TENDERSAATHI_LLM_MODEL` | `openai/gpt-oss-120b` | Model identifier on configured provider |

---


## Evidence, Confidence & Human Review

### Trust Model & Bounded Behavior
TenderSaathi does not generate answers out of thin air:
- **No fabricated standard IDs** are generated outside the bounded prototype catalogue.
- Every recommendation is backed by a stored verbatim scope excerpt and provenance tag.
- When evidence is insufficient or engineering parameters are missing, the system requests human review.

### Evidence & Provenance Tiers
Not every record in the 85-standard prototype database has undergone manual inspection. The system tracks provenance explicitly:
- **`VERIFIED`**: Manually verified records and scope evidence (e.g., cross-checked against BSB Edge / official BIS portal records with full scope clauses).
- **`CURATED`**: Records curated from available BIS and public catalogue information across core engineering sectors.
- **`INFERRED`**: Relationships and candidate links derived from explicit normative references cited within standards.

### Ambiguity Gating Protocol
When critical technical parameters are omitted, the system flags the clause:
- *Example*: An item specifying "valve replacement" lacks nominal diameter (DN), pressure rating (PN), body metallurgy, and fluid medium.
- *System Action*: Lowers confidence, leaves the primary standard as an open candidate, and outputs `HUMAN VERIFICATION REQUIRED? >>> YES` with the specific parameters to inspect in the Bill of Quantities (BOQ).

---

## Prototype Validation

To evaluate the system, **20 real central government CPPP tender PDFs** were collected and processed, yielding an inventory of **72 candidate requirements** (`dataset/tender_requirements.jsonl`). From these, **20 representative requirements across 12 tenders** (spanning 10 procurement domains) were curated and locked into the formal evaluation benchmark (`dataset/ground_truth/ground_truth.csv`).

| Evaluation Dimension | Benchmark Metric | Operational Significance |
|---|---|---|
| **Source Tenders Collected** | 20 real CPPP PDFs | Real-world central government tender documents |
| **Candidate Requirements Extracted** | 72 requirements | Total requirement inventory across all 20 processed tenders |
| **Locked Benchmark Cases** | 20 requirements | Curated evaluation ground truth with human-verified standards |
| **Tenders Represented in Benchmark** | 12 tenders | Benchmark requirements span 12 distinct tenders across 10 domains |
| **Prototype Standards Catalogue** | 85 standards | Curated SQLite knowledge base across 5 domains |
| **Top-1 Recommendation Accuracy** | **80.0%** (16/20) | Primary recommended standard matches ground truth |
| **Top-3 Retrieval Recall** | **90.0%** (18/20) | Target standard appears within top 3 candidates |
| **Mean Reciprocal Rank (MRR)** | **0.863** | Evaluates ranking position of the target standard |
| **Supersedence Detection Rate** | **100.0%** (3/3) | Obsolete codes accurately mapped to active replacements |
| **Ambiguity Detection Recall** | **100.0%** (1/1) | Under-specified benchmark cases routed to human review |
| **Local Inference Latency** | **< 45 ms** | Sub-second real-time execution on commodity hardware |
| **Automated Unit Tests** | **15 / 15 Passed** | Full regression coverage across schema, search, and logic |

---

## Failure Analysis

Empirical transparency demonstrates authentic testing on real tenders. In our 20-requirement benchmark, exactly **2 requirements missed the top 3** (`T013-R002` and `T014-R002`):

- **Observed Failure**:
  - `T013-R002` (*"VFD water pump panel SITC"*) matched agricultural pump testing standard `IS 9694` instead of electrical drive panel standards (`IS/IEC 61800-2`, `IS/IEC 61439-2`).
  - `T014-R002` (*"Submersible pumps supply"*) similarly favoured agricultural testing code `IS 9694` over industrial motor standards (`IS/IEC 60034-1`).
- **Root Cause**: Lexical token matching gave heavy weight to the generic term *"water pump"*, causing agricultural pump codes to outrank industrial electromechanical drive standards.
- **Planned Mitigation**: Implement compound requirement decomposition (separating pump, motor, and electrical panel into distinct sub-queries) and introduce industrial-versus-agricultural domain disambiguation.

---

## Demo

The interactive CLI demo (`scripts/demo.py`) demonstrates three core scenarios:

### 1. Superseded Standard Detection (OLD)
Demonstrates catching an obsolete standard and providing its active replacement:
```bash
python3 scripts/demo.py --query "IS 10611"
```
*Result: Identifies that `IS 10611:1983` is superseded and outputs active replacement `IS/ISO 10434:2020` with foreword evidence.*

### 2. Real Tender Processing (REAL)
Demonstrates processing a real government tender PDF:
```bash
python3 scripts/demo.py --tender T020
```
*Result: Ingests tender `T020`, extracts the requirement ("Repair/ maint of CPVC pipe in lieu of rusted GI pipe"), and recommends `IS 15778:2007` with High confidence and scope excerpt.*

### 3. Ambiguity & Human-Review Gating (UNCLEAR)
Demonstrates conservative refusal to guess when parameters are missing:
```bash
python3 scripts/demo.py --query "valve replacement"
```
*Result: Detects missing parameters (valve type, size/DN, pressure rating, metallurgy, medium), sets confidence to Low, and flags: `HUMAN VERIFICATION REQUIRED? >>> YES`.*

---

## Tech Stack

| Component | Technology | Implementation Role |
|---|---|---|
| **Core Runtime** | Python 3.10+ | Primary language across extraction, search, and validation |
| **Database** | SQLite 3 | Embedded store for standards metadata, scopes, and graph edges |
| **PDF Extraction** | PyMuPDF (`fitz`) | Text layout parsing and page-by-page tender ingestion |
| **Data Processing** | Pandas, OpenPyXL | Ground-truth compilation, tabular reports, and dataset handling |
| **Testing** | Python `unittest` | 15 automated unit and regression tests |
| **Interface** | Terminal CLI | ANSI-formatted structured evaluation cards |

---

## Repository Structure

```text
sih26108-feasibility/
├── src/                               # Core recommendation engine modules
│   ├── extract.py                     # PDF & text requirement extraction + noise filtering
│   ├── standards.py                   # SQLite schema, data models & relationship graph
│   ├── search.py                      # Retrieval engine (number, title, scope, token overlap)
│   ├── validate.py                    # Lifecycle status & supersedence validation
│   ├── evidence.py                    # Scope clause evidence grounding & provenance
│   ├── recommend.py                   # Master recommender & ambiguity gating
│   └── evaluate.py                    # Benchmark evaluation harness
├── scripts/                           # Executables and utilities
│   ├── demo.py                        # Presentation CLI demo runner
│   ├── extract_text.py                # PDF layout text extraction tool
│   ├── extract_requirements.py        # Requirement segmentation utility
│   └── ingest_tenders.py              # Bulk tender ingestion runner
├── data/                              # Standards knowledge base & raw tenders
│   ├── standards/standards.db         # SQLite database with 85 curated standards
│   └── tenders/                       # Source tender PDF documents (T001 - T020)
├── dataset/                           # Feasibility dataset & benchmarks
│   ├── ground_truth/ground_truth.csv  # 20-tender locked evaluation benchmark
│   └── tender_requirements.jsonl      # 72 extracted requirements inventory
├── tests/                             # Automated test suite
│   ├── test_standards.py              # Schema, relations, & database tests (7 tests)
│   └── test_milestone2.py             # Extraction, search, & pipeline tests (8 tests)
└── reports/                           # Technical documentation & benchmark reports
    └── feasibility/
        └── milestone2_evaluation_report.md # Benchmark evaluation report
```

---

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Standard libraries (`sqlite3`, `re`, `json`, `csv`, `pathlib`, `unittest`)

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/syed-imadulla/Tender-saathi.git
cd Tender-saathi

# 2. (Optional) Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install required packages
pip install -r requirements.txt
```

### Environment Setup

To enable optional AI requirement understanding, create a local `.env` file using the provided template:
```bash
cp .env.example .env
```

Configure your local `.env` file:
```env
GROQ_API_KEY=<your-groq-api-key>
TENDERSAATHI_LLM_ENABLED=true
TENDERSAATHI_LLM_PROVIDER=groq
TENDERSAATHI_LLM_MODEL=openai/gpt-oss-120b
```

> [!IMPORTANT]
> **Never commit `.env` to Git.** The `.env` file is strictly ignored by `.gitignore`. The repository provides `.env.example` as a clean template. If no API key is provided, the system runs 100% offline using deterministic rule-based decomposition.

### Run Demo Scenarios
```bash
# Demo 1: Superseded Standard Query
python3 scripts/demo.py --query "IS 10611"

# Demo 2: Real Tender PDF Processing
python3 scripts/demo.py --tender T020

# Demo 3: Ambiguous Requirement Query
python3 scripts/demo.py --query "valve replacement"

# Demo 4: AI Requirement Understanding & Neural Reranking (loads key from .env)
python3 scripts/demo.py --query "Supply, installation and commissioning of 3.3kV process water pump motors with starter panel" --llm --rerank

# Custom Procurement Query
python3 scripts/demo.py --query "Supply and laying of CPVC pipes for potable water" --rerank
```

### Run Automated Tests & Evaluation
```bash
# Run all 130 unit tests
python3 -m unittest discover -s tests -v

# Run 20-tender benchmark evaluation across all retrieval modes
python3 -m src.evaluate
```

---

## Current Limitations

- **Bounded Standards Catalogue**: The database currently indexes 85 standards for feasibility demonstration; it does not yet encompass the full national catalogue of 20,000+ standards.
- **No live BIS integration**: The current prototype operates offline on its local standards knowledge base. Integration with officially available BIS data sources is part of future development.
- **Lexical Overlap in Compound Queries**: Multi-trade sentences (e.g., pump + motor + starter panel) can experience lexical bias without multi-token clause decomposition.
- **Interface**: The current prototype is a terminal CLI application; the web interface is part of the future development phase.
- **Relationship Coverage**: Graph edges are currently restricted to verified relationships present in our curated dataset.

---

## Future Development

### Next Stage (Product Development)
- **Web UI Dashboard**: Browser dashboard for procurement officers to upload tender documents, inspect extracted clauses, review candidate standards, view evidence, and download audit/review reports.
- **Catalogue Expansion**: Scaling the local SQLite/PostgreSQL store across all major BIS civil, mechanical, and electrical divisions.
- **Hybrid Retrieval**: Implementing formal BM25 coupled with domain-tuned semantic embeddings for dense vector search.
- **Compound Requirement Parsing**: Automated decomposition of composite tender clauses into discrete sub-queries.
- **Expanded Relationships**: Indexing normative references, mandatory amendments, and specialized testing codes.

### Future Vision (Full-Scale SIH Solution)
- **Approved Data Ingestion Pipeline**: Ingesting official public BIS gazettes and portal updates to automatically detect revisions and status changes with human verification.
- **Quality Control Order (QCO) Integration**: Flagging products where Indian Standards certification is legally mandatory under current government QCO notifications.
- **E-Procurement Integration**: Direct integration with CPPP and GeM portals, subject to official access and approvals.
- **Scalable Cloud Microservice**: Secure containerized deployment for departmental tender scrutiny committees.

---

## Research & References

1. **General Financial Rules (GFR), 2017**: Rule 144 (Fundamental principles of public buying and technical specifications).
2. **Bureau of Indian Standards Act, 2016**: Statutory framework governing mandatory standards, certification, and Quality Control Orders.
3. **Central Public Procurement Portal (CPPP)**: Government of India e-procurement tender notices analyzed for prototype benchmarking.
4. **BSB Edge Portal / BIS Catalogues**: Source documentation referenced for standard titles, publication years, forewords, and scope clauses.

---

## Team

- **Team Name**: Base Case
- **Problem Statement ID**: SIH26108
- **Repository**: [github.com/syed-imadulla/Tender-saathi](https://github.com/syed-imadulla/Tender-saathi)
