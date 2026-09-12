# TenderSaathi

**Evidence-backed Indian Standards validation for procurement specifications.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-319%2F319%20Passing-brightgreen.svg)]()
[![SIH Problem](https://img.shields.io/badge/SIH%202026-SIH26108-orange.svg)]()
[![Status](https://img.shields.io/badge/Status-Freeze%20Locked-success.svg)]()

> **"AI interprets. Rules validate. Evidence supports. Humans decide."**

---

## Problem

In Indian public procurement (conducted through portals such as CPPP and GeM, and departments including CPWD, MES, and Indian Railways), technical specifications are required to cite applicable national standards where available, in line with General Financial Rules (GFR) 2017 (Rule 144).

In practice, tender specifications routinely encounter significant quality and compliance hurdles:

- **Omitted Standards**: Work items and materials (e.g., CPVC piping, sewerage lines, underground cables) are frequently specified without citing mandatory Indian Standard (`IS`) codes.
- **Obsolete & Superseded Citations**: Reused tender templates often cite withdrawn or replaced standards (e.g., citing `IS 10611` instead of `IS/ISO 10434`, or `IS 780` instead of `IS 14846`).
- **Incomplete Technical Parameters**: Clauses specify generic items (e.g., "valve replacement") while omitting essential engineering parameters (diameter/DN, pressure/PN, metallurgy, medium).
- **Missing Related Standards & Dependencies**: Primary items are cited without cross-referencing necessary material test methods, installation codes of practice, or jointing guidelines.
- **Regulatory & Certification Uncertainty**: Tender drafters often lack immediate clarity on whether cited products are governed by mandatory Quality Control Orders (QCOs) issued by line ministries.

Manually verifying these requirements across tens of thousands of pages of BIS documentation and shifting gazette notifications is tedious, error-prone, and inconsistently performed.

---

## What TenderSaathi Does

TenderSaathi is an intelligent technical specification review system that starts directly from procurement text or tender documents:

1. **Extracts technical requirements** from text or uploaded tender PDFs, stripping administrative boilerplate.
2. **Understands & decomposes** complex, compound requirements into structured engineering facets.
3. **Searches the available Indian Standards catalogue** using hybrid lexical and semantic retrieval.
4. **Checks applicability & domain boundaries** to prevent off-target recommendations.
5. **Detects ambiguity & missing parameters**, identifying gaps in engineering specifications.
6. **Grounds recommendations in verifiable evidence**, linking verbatim scope excerpts to each candidate standard.
7. **Checks lifecycle status**, identifying active, superseded, or withdrawn standards and surfacing successors.
8. **Surfaces related & dependency standards** via an explicit standards relationship graph.
9. **Checks available regulatory information**, highlighting Quality Control Order (QCO) requirements where indexed.
10. **Routes uncertain cases to human review**, categorizing findings into prioritized readiness states.
11. **Produces structured audit reports** in clean interactive UI, JSON, and Markdown formats.

> **"We don't just recommend standards. We audit the tender against the standards it should contain."**

---

## Trust Model

TenderSaathi is engineered around a strict decision-safety principle:

> **AI interprets. Rules validate. Evidence supports. Humans decide.**

- **The LLM is NOT the source of truth.** It optionally assists with natural language requirement parsing, but never selects standards, invents standard numbers, or declares legal compliance.
- **Standards are selected strictly from the verified catalogue.** The system cannot recommend fabricated or hallucinated standard numbers.
- **Deterministic gates enforce domain boundaries.** Hard negative rules prevent cross-domain mismatch (e.g., preventing surface pump queries from matching borehole submersible standards).
- **Evidence is strictly tied to the recommended standard.** Every positive recommendation is verified against authoritative scope text.
- **Safe abstention over guessing.** When supporting evidence is insufficient or requirements are under-specified, the engine deliberately abstains rather than making an ungrounded guess.
- **Human review is prioritized.** Complex, ambiguous, or superseded citations are routed to procurement engineers with targeted clarification questions.

### Core Invariants

For every positive recommendation:
```text
candidate_standard == evidence_standard
```

For every abstention:
```text
candidate_standard = null
evidence_standard = null
human_review_required = true
```

*Evidence-grounded recommendations with safe abstention when supporting evidence is insufficient.*

---

## How It Works

```text
               Tender / PDF / Text
                        ↓
               Document Extraction
                        ↓
            Requirement Understanding
                        ↓
           Requirement Decomposition
                        ↓
                Hybrid Retrieval
            (BM25 + Semantic Search)
                        ↓
         Applicability & Boundary Gates
                        ↓
        Ambiguity / Completeness Checks
                        ↓
               Evidence Grounding
                        ↓
           Standards Dependency Graph
                        ↓
                Lifecycle Checks
                        ↓
       Regulatory / Certification Checks
                        ↓
                  Human Review
                        ↓
             Tender Readiness Report
```

1. **Extraction**: Ingests tender PDFs via PyMuPDF or plain text clauses, isolating technical requirements from bidding rules.
2. **Decomposition**: Identifies equipment type, medium, pressure, diameter, and execution scope.
3. **Retrieval**: Combines BM25 Okapi lexical matching with dense vector embeddings (`all-MiniLM-L6-v2`) via Reciprocal Rank Fusion.
4. **Applicability Gating**: Filters candidates against deterministic engineering boundary rules.
5. **Ambiguity Analysis**: Checks requirements against 5 essential parameters (type, size, rating, metallurgy, medium).
6. **Evidence Critic**: Verifies clause-level text support, enforcing candidate-evidence consistency.
7. **Graph Traversal**: Traverses normative references, testing codes, and installation standards.
8. **Lifecycle & Regulatory**: Maps superseded standards to current active successors and checks QCO certification schedules.
9. **Readiness Report**: Synthesizes the findings into clear states (`READY_FOR_REVIEW`, `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`).

---

## Technical Stack

All listed technologies are actively implemented in the repository:

| Layer | Component | Verified Implementation |
|---|---|---|
| **Core Runtime** | Python 3.10+ | Complete engine, extraction, search, and audit pipelines |
| **Web API** | Flask 3.0+ & Flask-CORS | REST API serving analysis, PDF uploads, reports, and health checks |
| **Frontend UI** | React 18, TypeScript, Vite | Modern web application with real-time audit cards and evidence drawer |
| **Database** | SQLite 3 | Embedded store for standards metadata, scopes, relations, and catalogue |
| **Lexical Retrieval** | BM25 Okapi (`rank_bm25`) | Tokenized exact/partial number and keyword matching |
| **Semantic Retrieval** | Sentence-Transformers | Dense vector embeddings using `all-MiniLM-L6-v2` (384-dimensional) |
| **Neural Reranking** | Cross-Encoder | Optional candidate reranking using `ms-marco-MiniLM-L-6-v2` |
| **PDF Extraction** | PyMuPDF (`fitz`) | Multi-column layout text extraction and page segmentation |
| **AI Parsing (Optional)** | Groq API | Optional LLM requirement understanding with 100% offline rule fallback |
| **Test Suite** | Pytest | 319 automated unit, integration, contract, and safety tests |

---

## Key Features

- **Evidence-Grounded Recommendations**: Every positive recommendation is validated against verified scope clauses.
- **Safe Abstention**: Refuses to guess when requirements lack technical basis or supporting evidence.
- **Applicability Gates**: Deterministic boundary rules prevent cross-domain mismatch.
- **Ambiguity & Parameter Gap Detection**: Flags missing engineering attributes (DN, PN, metallurgy, medium).
- **Candidate/Evidence Invariant**: Enforces `candidate_standard == evidence_standard` on all recommendations.
- **Superseded Standard Detection**: Flags withdrawn or replaced standards from previous years.
- **Successor Standard Surfacing**: Recommends the authoritative active replacement (e.g. `IS/ISO` standards).
- **Standards Knowledge Graph**: Traces normative references, allied testing codes, and installation guidelines.
- **Regulatory / QCO Intelligence**: Flags products requiring mandatory ISI certification under current government orders.
- **Multilingual Technical Normalization**: Normalizes Hindi, Tamil, and English technical terms to canonical identifiers.
- **Prioritized Human Review Queue**: Categorizes tender clauses into actionable readiness tiers.
- **Multi-Format Reporting**: Generates interactive web dashboard summaries, structured JSON, and Markdown reports.
- **Multi-Item Tender Handling**: Processes complete tender documents containing multiple distinct technical items.

---

## Current Prototype Scope

The repository implements a fully validated, reproducible feasibility prototype:

- **502 Catalogue Records**: Official Bureau of Indian Standards records indexed in `data/catalogue/catalogue.db`.
- **90 Core Standards**: Deep clause-level scope text and relationship graphs indexed in `data/standards/standards.db` (90 distinct IDs, 0 duplicates).
- **20 Real Government Tender PDFs**: Collected from central procurement portals and audited end-to-end (`tenders/T001.pdf` – `tenders/T020.pdf`).
- **25 Extracted & Analyzed Requirements**: Detailed in representative multi-item end-to-end evaluation reports.
- **40-Case Multilingual Benchmark**: Frozen benchmark dataset (`dataset/ground_truth/multilingual_benchmark.json`, SHA-256: `db62e0367ea2983dab49a9ac8a98958efb0c17882df86f131ecfa6b04903690b`).
- **100% Candidate/Evidence Parity**: Verified across all recommendation pathways.
- **319 / 319 Passing Automated Tests**: Full test suite passing with zero failures at final freeze audit.

---

## Demo Scenarios

The web interface and API provide three verified demonstration scenarios:

### 1. Clear Recommendation (Happy Path)
- **Input**: *"Supply and installation of CPVC pipes and fittings for domestic hot and cold water distribution system, conforming to IS 15778."*
- **Recommendation**: `IS 15778 : 2007` (Chlorinated Polyvinyl Chloride Pipes for Potable Hot and Cold Water Distribution Supplies).
- **Evidence**: Verbatim scope clause matches pipe specification.
- **Dependencies**: Surfaced related testing standards (IS 4985, IS 12235 series).
- **Parity**: `candidate == evidence` (`IS 15778 : 2007`).
- **Readiness**: `READY_FOR_REVIEW`.

### 2. Safe Abstention & Parameter Ambiguity
- **Input (Real Tender T002)**: *"Annual Rate Contract for Execution of Mechanical Maintenance Works including Pumps, Valve Replacement at Heavy Water Board Facilities."*
- **Behavior**: System identifies that "valve replacement" lacks valve type, nominal diameter (DN), pressure class (PN), body metallurgy, and fluid medium.
- **Recommendation**: `candidate = null`, `evidence = null`, `human_review_required = true`.
- **Action**: Emits targeted clarification questions for procurement officers rather than guessing an arbitrary valve standard.
- **Readiness**: `INSUFFICIENT_EVIDENCE` / `REVIEW_REQUIRED`.

### 3. Superseded Standard Detection
- **Input**: *"Procurement of bolted bonnet steel gate valves conforming to IS 10611 : 1983."*
- **Detection**: `IS 10611 : 1983` is identified as `SUPERSEDED`.
- **Successor Surfaced**: Recommends current active successor `IS/ISO 10434 : 2020` (Bolted bonnet steel gate valves for petroleum, petrochemical and allied industries).
- **Evidence**: Foreword and replacement clause from `IS/ISO 10434 : 2020`.
- **Parity**: `candidate == evidence` (`IS/ISO 10434 : 2020`).
- **Readiness**: `REVIEW_REQUIRED` (officer sign-off on code transition).

---

## Run Locally

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18 or higher (with `npm`)

### 1. Installation

Clone the repository and set up the Python environment:
```bash
# Clone the repository
git clone https://github.com/syed-imadulla/Tender-saathi.git
cd Tender-saathi

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt
```

Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

### 2. Start the Backend API Server

```bash
python3 -u api/server.py
```
The Flask API starts at `http://localhost:5000/`.

### 3. Start the Frontend Development Server

In a separate terminal:
```bash
cd frontend
npm run dev
```
The React + Vite application will open at `http://localhost:5173/`.

### 4. Interactive CLI Demo (Optional)

You can also run demo scenarios directly from the command line:
```bash
# Demo 1: Clear CPVC query
python3 scripts/demo.py --query "Supply and laying of CPVC pipes for potable water"

# Demo 2: Superseded standard query
python3 scripts/demo.py --query "IS 10611"

# Demo 3: Ambiguous requirement query
python3 scripts/demo.py --query "valve replacement"

# Real tender PDF processing
python3 scripts/demo.py --tender T020
```

### 5. Run the Automated Test Suite

```bash
# Run the complete test suite (319 tests)
pytest tests/ -q
```

---

## API Endpoints

The Flask server provides the following endpoints (confirmed in `api/server.py`):

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health, model status, and indexed catalogue counts |
| `POST` | `/api/analyze/text` | Audits plain text tender requirements (JSON body: `{"text": "..."}`) |
| `POST` | `/api/analyze/pdf` | Audits an uploaded tender PDF file (`multipart/form-data`) |
| `GET` | `/api/analyze/sample/<demo>` | Audits built-in demo cases: `cpvc`, `valve`, or `superseded` |
| `GET` | `/api/report/<tender_id>/json` | Downloads structured JSON audit report for a given tender session |
| `GET` | `/api/report/<tender_id>/markdown` | Downloads formatted Markdown audit report for a given tender session |
| `GET` | `/api/report/json` | Downloads latest generated audit report as JSON |
| `GET` | `/api/report/markdown` | Downloads latest generated audit report as Markdown |

---

## Project Structure

```text
.
├── api/                  # Flask REST API server and endpoints
│   └── server.py         # Main API server implementation
├── src/                  # Core intelligence, retrieval, audit, and validation engine
│   ├── ai_understanding.py # LLM requirement understanding (optional Groq / offline fallback)
│   ├── applicability.py    # Deterministic boundary gates & applicability checks
│   ├── audit.py            # Master TenderAuditEngine coordinating the multi-stage pipeline
│   ├── evaluate.py         # Benchmark evaluation harness
│   ├── evidence.py         # Scope clause evidence grounding & provenance
│   ├── extract.py          # PDF layout extraction and requirement parsing
│   ├── recommend.py        # StandardsRecommender combining search, graph, and gates
│   ├── reranker.py         # Neural Cross-Encoder candidate reranker
│   ├── search.py           # Hybrid BM25 + dense vector retrieval
│   ├── standards.py        # SQLite schema, data models & relationship graph
│   └── validate.py         # Lifecycle status & supersedence validation
├── frontend/             # React + TypeScript + Vite web interface
│   ├── src/              # UI components, audit cards, evidence drawer
│   └── package.json      # Frontend dependencies and build scripts
├── data/
│   ├── standards/        # Working standards database (90 core standards) and vector indices
│   ├── catalogue/        # Official BIS metadata catalogue (502 records)
│   └── regulatory/       # Quality Control Orders (QCOs) and regulatory schedules
├── dataset/
│   └── ground_truth/     # Multilingual benchmark (40 cases) and test ground truth
├── tenders/              # Real public procurement tender PDFs (T001 - T020)
├── tests/                # Automated test suite (319 pytest tests)
├── reports/              # Generated audit reports and E2E evaluation summaries
│   ├── e2e/              # 20-tender end-to-end evaluation reports
│   └── generated/        # Runtime session audit reports
├── docs/                 # SIH presentation deck, audits, and technical specifications
└── README.md             # Repository documentation
```

---

## Validation

The system has undergone systematic, independent audit verification:

- **Automated Regression Suite**: **319 / 319 tests passing** across schema, search, applicability gates, evidence chains, adversarial safety, API-UI contracts, and failure states (`pytest tests/`).
- **Real Tender E2E Validation**: **20 out of 20 real government tender PDFs** processed through the complete extraction, audit, and report generation pipeline with zero unhandled exceptions.
- **Frontend Production Build**: The React + TypeScript web application compiles cleanly with zero TypeScript errors (`npm --prefix frontend run build`).
- **Candidate-Evidence Parity**: 100% verified compliance with the invariant `candidate_standard == evidence_standard` across all positive recommendations.
- **Adversarial Safety Testing**: Exhaustive tests confirm resistance to prompt injection, off-domain queries, malformed inputs, and non-submersible pump boundary conditions.
- **Multilingual Benchmark**: 40 frozen cases across English, Hindi, and Tamil evaluated for language-invariant parity and abstention behavior.
- **Database Integrity**: Exactly 90 rows, 90 distinct IDs, and 0 duplicates confirmed in `data/standards/standards.db`; 502 records confirmed in `data/catalogue/catalogue.db`.

---

## Current Limitations

To maintain technical honesty and defensibility during judging and review:

1. **Catalogue Boundaries**: Deep clause-level verification is currently populated for 90 core electromechanical, civil, and piping standards; catalogue metadata covers 502 official BIS records. Full 20,000+ BIS coverage is a roadmap ingestion phase.
2. **Decision-Support Scope**: TenderSaathi is an assistive technical review and audit tool, not a statutory legal certification or autonomous procurement approval system.
3. **Human Review Requirement**: Ambiguous, under-specified, or uncertain cases are intentionally routed to technical officers for human adjudication.
4. **Scanned Documents**: The system directly processes text-based PDFs; scanned or degraded documents require OCR preprocessing whose accuracy depends on scan legibility.
5. **Regulatory Scope**: Quality Control Order (QCO) verification covers sectors currently indexed in our regulatory database; unindexed sectors require officer verification.
6. **E-Procurement Integration**: Direct API connectors to CPPP or GeM portals are architectural roadmap concepts requiring official government access and credentials.

---

## Roadmap

Planned future developments building on the current verified architecture:

- **Catalogue Expansion**: Ingesting additional BIS engineering divisions into the SQLite + BM25 + vector index.
- **Deeper Scope Ingestion**: Expanding clause-level scope text across the broader metadata catalogue.
- **Comprehensive QCO Gazette Tracking**: Expanding automated mappings to Ministry Quality Control Order schedules.
- **Enhanced OCR Preprocessing**: Integrating specialized layout-aware OCR for scanned and physical paper tenders.
- **Broadened Multilingual Coverage**: Expanding technical normalizers to additional Indian regional languages.
- **Containerized On-Premise Deployment**: Packaging Docker microservice containers for secure departmental intranet deployment.
- **E-Procurement Workflow Integration**: Integrating with tender drafting workflows to assist technical officers prior to tender publishing.

---

## Why TenderSaathi?

> **"We don't just recommend standards. We audit the tender against the standards it should contain."**

Existing search tools require the user to already know the exact standard number, while generic AI tools lack authoritative grounding, risk hallucinating plausible codes, and cannot produce verifiable evidence.

TenderSaathi is unique in delivering an integrated **decision-safety workflow**:

```text
Requirement Understanding
         ↓
Hybrid Retrieval
         ↓
Applicability Boundary Gates
         ↓
Ambiguity & Parameter Gap Detection
         ↓
Evidence Grounding Critic
         ↓
Lifecycle & Supersedence Traversal
         ↓
Dependency Graph Traversal
         ↓
Regulatory QCO Signals
         ↓
Prioritized Human Review
```

By placing deterministic validation and evidence grounding between AI interpretation and procurement decisions, TenderSaathi enables transparent, trustworthy, and auditable procurement review.

---

## Documentation

- [SIH Presentation Deck](docs/SIH_PRESENTATION_DECK.md) — Complete 10-slide competitive pitch deck
- [Final SIH Freeze Audit](docs/FINAL_SIH_FREEZE_AUDIT.md) — Final claim integrity and repository freeze report
- [Priority 7 Product Final Audit](docs/PRIORITY_7_PRODUCT_FINAL_AUDIT.md) — Verification of API, UI contracts, and E2E tenders
- [Priority 8 Readiness Audit](docs/PRIORITY_8_FINAL_SIH_READINESS_AUDIT.md) — Demo readiness and presentation alignment audit
- [Priority 6F Remediation Audit](docs/PRIORITY_6F_REMEDIATION_AUDIT.md) — Independent benchmark and engine audit
- [E2E Evaluation Summary](reports/e2e/e2e_summary.md) — Summary of 20 real government tender audits

---

## Project Status

- **Hackathon**: Smart India Hackathon 2026
- **Problem Statement**: SIH26108 (*AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications*)
- **Status**: Verified SIH demo-ready prototype (Freeze Locked)
