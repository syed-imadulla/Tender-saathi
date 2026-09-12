# TenderSaathi

**Evidence-backed Indian Standards validation for procurement specifications.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Freeze Validation](https://img.shields.io/badge/Freeze%20Validation-319%2F319%20Passing-brightgreen.svg)]()
[![SIH 2026](https://img.shields.io/badge/SIH%202026-SIH26108-orange.svg)]()
[![Status](https://img.shields.io/badge/Status-Verified%20Prototype-blueviolet.svg)]()

> **AI interprets. Rules validate. Evidence supports. Humans decide.**

- **What is TenderSaathi?** TenderSaathi is an evidence-backed technical specification review and audit engine designed for Indian public procurement. It analyzes tender documents and procurement clauses to identify applicable Indian Standards (BIS codes), verify lifecycle validity, uncover missing engineering parameters, and trace standard dependencies.
- **What problem does it solve?** Public tenders routinely omit standards, cite obsolete or superseded codes, omit critical technical parameters (such as diameter, pressure rating, or metallurgy), or miss required testing and installation standards. TenderSaathi assists procurement teams by automating the technical verification of procurement specifications against authoritative standards documentation.
- **What makes it different?** Rather than acting as a simple keyword search engine or an ungrounded generative chatbot, TenderSaathi implements a deterministic, evidence-grounded decision-safety pipeline that actively audits specifications, surfaces supporting clause excerpts, and safely abstains when evidence is insufficient.

---

## The Problem

In Indian public procurement (conducted through portals such as CPPP and GeM, and departments including CPWD, MES, and Indian Railways), technical specifications are required to cite applicable national standards where available, in line with the principles of public buying set out in General Financial Rules (GFR) 2017 (Rule 144).

In practice, tender specifications routinely encounter significant quality and consistency hurdles:

- **Omitted Standards**: Work items and materials (e.g., CPVC piping, sewerage lines, underground cables) are frequently specified without citing applicable Indian Standard (`IS`) codes.
- **Obsolete & Superseded Citations**: Reused tender templates often cite withdrawn or replaced standards (e.g., citing `IS 10611` instead of `IS/ISO 10434`, or `IS 780` instead of `IS 14846`).
- **Incomplete Technical Parameters**: Clauses specify generic items (e.g., "valve replacement") while omitting essential engineering parameters (nominal diameter/DN, pressure rating/PN, metallurgy, fluid medium).
- **Missing Related Standards & Dependencies**: Primary items are cited without cross-referencing necessary material test methods, installation codes of practice, or jointing guidelines.
- **Regulatory & Certification Uncertainty**: Tender drafters often lack immediate clarity on whether cited products are governed by gazetted Quality Control Orders (QCOs) issued by line ministries.

Manually verifying these requirements across tens of thousands of pages of technical documentation and shifting gazette notifications is time-consuming, complex, and difficult to perform consistently during high-volume tender preparation.

---

## What TenderSaathi Does

TenderSaathi is an intelligent technical specification review system that starts directly from procurement text or tender documents:

1. **Tender / PDF / Text Ingestion**: Ingests multi-page tender PDFs or plain-text tender clauses.
2. **Technical Requirement Extraction**: Segments document text, strips administrative boilerplate (EMD, tender fees, eligibility rules), and isolates technical work items.
3. **Requirement Decomposition**: Parses messy procurement clauses into structured engineering facets (equipment type, application, medium, voltage, pressure, material).
4. **Hybrid Retrieval**: Queries the indexed standards catalogue using weighted score fusion combining Okapi BM25 lexical retrieval, dense semantic embeddings (`all-MiniLM-L6-v2`), and deterministic component matching.
5. **Applicability Checking**: Evaluates candidate standards against deterministic engineering boundary gates to prevent cross-domain mismatch.
6. **Ambiguity & Parameter Completeness Checking**: Evaluates whether essential engineering attributes (type, size, rating, metallurgy, medium) are present or missing.
7. **Evidence Grounding**: Verifies clause-level text support, retrieving verbatim scope excerpts to ground every recommendation.
8. **Lifecycle & Supersedence Checking**: Identifies whether cited or retrieved standards are Active, Superseded, or Withdrawn, and resolves authoritative active successors.
9. **Dependency & Relationship Analysis**: Explores an explicit standards relationship graph to surface companion codes of practice, testing standards, and installation guides.
10. **Regulatory Signals**: Surfaces indexed Quality Control Orders (QCOs) and associated certification signals where available.
11. **Human Review Queue**: Routes ambiguous, unsupported, or superseded cases to technical officers with targeted clarification prompts.
12. **Tender Readiness Report**: Produces structured audit reports in an interactive web UI, downloadable JSON, and Markdown formats.

---

## Why It Matters

TenderSaathi converts standards checking from a manual lookup exercise into an evidence-backed review workflow:

```text
Traditional Manual Workflow:
Tender Clause → Manual Search → Guess Standard → Check Old/New Code → Search Dependencies → Check Gazette → Review Again

TenderSaathi Review Workflow:
Tender Document → Requirement Understanding → Candidate Standards → Boundary & Applicability → Verbatim Evidence → Lifecycle Validation → Dependency Graph → Regulatory Signals → Human Review Queue → Readiness Report
```

This ensures that technical specifications are checked systematically against authoritative standards before publishing, reducing pre-bid queries, specification disputes, and procurement rework.

---

## Core Differentiator / USP

> **"We don't just recommend standards. We audit the tender against the standards it should contain."**

TenderSaathi does not claim that individual retrieval algorithms or language models are individually unique. Its differentiation lies in its **integrated decision-safety pipeline**:

```text
Requirement Understanding
         ↓
Hybrid Retrieval (Weighted Fusion)
         ↓
Applicability Boundary Gates
         ↓
Ambiguity & Parameter Checks
         ↓
Evidence Grounding Critic
         ↓
Lifecycle & Supersedence Traversal
         ↓
Dependency Graph Traversal
         ↓
Regulatory Signals (Indexed QCOs)
         ↓
Prioritized Human Review
         ↓
Tender Readiness Decision
```

Existing tools either rely on basic keyword search (requiring the engineer to already know the exact standard number) or generic LLMs (which lack authoritative grounding and risk hallucinating plausible-sounding codes).

TenderSaathi is designed not merely to find a likely standard, but to **decide whether the evidence is sufficient to recommend one**. If evidence is insufficient, it safely abstains and asks the engineer the exact questions needed to resolve the ambiguity.

---

## Trust & Decision Safety

TenderSaathi is built around four operational principles:

- **AI interprets**: Optional LLM assistance is used strictly for structured natural-language requirement understanding and facet decomposition. The LLM never selects standard codes, invents standard numbers, generates synthetic evidence, or declares legal compliance.
- **Rules validate**: Deterministic rules enforce engineering boundaries, applicability conditions, and safety constraints (e.g., ensuring borehole submersible pump standards do not trigger on non-submersible surface pump queries).
- **Evidence supports**: Recommendations are tied directly to stored standard scope clauses and tracked provenance tiers (`OFFICIAL_PRIMARY`, `OFFICIAL_SECONDARY`, `VERIFIED`, `CURATED`, `INFERRED`). Inferred data is never presented as authoritative fact.
- **Humans decide**: Ambiguous, unsupported, superseded, or uncertain cases are routed to procurement engineers with clear context.

### Engineering Invariants

The core recommendation pipeline enforces two strict structural invariants:

1. **Recommendation Invariant**:
   For non-null recommendations, the system enforces candidate/evidence identity:
   ```text
   candidate_standard == evidence_standard
   ```
   *Every surfaced recommendation must have verbatim evidence belonging strictly to that exact standard.*

2. **Abstention Invariant**:
   When the implemented safety gates determine that available evidence is insufficient or the requirement is unresolved, TenderSaathi abstains and routes the case to human review:
   ```text
   candidate_standard = null
   evidence_standard = null
   human_review_required = true
   ```
   *Rather than guessing an ungrounded standard, the system abstains safely.*

> [!NOTE]
> **Defensible Trust Boundaries**:
> - The recommendation pipeline is catalogue-bounded and evidence-grounded, with safe abstention when supporting evidence is insufficient.
> - These are engineering invariants implemented in the software pipeline, not a statutory legal guarantee.
> - TenderSaathi is a technical decision-support and review system, not a statutory legal certification or autonomous procurement approval system.

---

## What TenderSaathi Does Not Do

- **It does not provide statutory legal certification**: Recommendations and audit findings are advisory engineering inputs for procurement teams.
- **It does not autonomously approve tenders**: Technical officers and competent authorities retain full responsibility for procurement decisions.
- **It does not claim complete BIS catalogue coverage**: The prototype covers 502 indexed catalogue records and 90 core standards with deep clause-level evidence, not the entirety of national standards.
- **It does not replace engineering judgement**: Complex site conditions, domain exceptions, and project-specific requirements require human review.
- **It does not treat an LLM response as authoritative evidence**: All surfaced standards and scope citations originate from the local database.
- **It does not silently convert uncertain cases into confident recommendations**: Ambiguous or incomplete clauses are explicitly flagged for human clarification.

---

## Architecture

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
         (BM25 + Semantic + Deterministic)
                        ↓
         Applicability & Boundary Gates
                        ↓
        Ambiguity / Completeness Checks
                        ↓
               Evidence Grounding
                        ↓
              Lifecycle Validation
                        ↓
           Standards Dependency Graph
                        ↓
            Regulatory QCO Signals
                        ↓
               Human Review Queue
                        ↓
                Tender Readiness
                        ↓
             Markdown / JSON Report
```

- **Document Extraction**: PyMuPDF-based text and layout extraction, removing administrative boilerplate and isolating technical clauses.
- **Requirement Understanding & Decomposition**: Maps requirements into structured technical facets (equipment, medium, pressure, diameter, execution scope).
- **Hybrid Retrieval**: Combines Okapi BM25 lexical scoring, dense vector cosine similarity (`all-MiniLM-L6-v2`), and deterministic component matching via weighted score fusion.
- **Applicability & Boundary Gates**: Deterministic domain boundary filters preventing cross-domain standard mismatch.
- **Ambiguity & Completeness Checks**: Evaluates requirement text against essential technical dimensions (type, size, rating, metallurgy, medium).
- **Evidence Grounding**: Verifies clause-level text support, retrieving verbatim scope excerpts for positive candidates.
- **Lifecycle Validation**: Traverses active, superseded, and withdrawn relationships to identify current authoritative successors.
- **Standards Dependency Graph**: Traces normative references, material testing codes, and installation codes of practice.
- **Regulatory Signals**: Checks indexed Quality Control Orders (QCOs) for mandatory certification requirements where applicable.
- **Human Review Queue**: Surfaces prioritized items requiring engineering review with targeted clarification questions.
- **Tender Readiness**: Classifies overall tender readiness into actionable operational states (`READY_FOR_REVIEW`, `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`).
- **Markdown / JSON Report**: Exports comprehensive audit findings for departmental procurement files.

---

## Technical Stack

Every technology listed below is actively implemented and verified in the codebase:

| Component | Technology | Implementation Role |
|---|---|---|
| **Core Runtime** | Python 3.10+ | Recommendation engine, extraction, search, and audit pipelines |
| **Web API Server** | Flask 3.0+ & Flask-CORS | REST API serving analysis, file uploads, reports, and health checks |
| **Frontend UI** | React 18, TypeScript, Vite | Modern web application with interactive audit cards and evidence drawer |
| **Database Storage** | SQLite 3 | Embedded store for standards metadata, scopes, relations, and catalogue records |
| **Lexical Retrieval** | BM25 Okapi (`rank_bm25`) | Tokenized exact/partial number and technical keyword matching |
| **Semantic Retrieval** | Sentence-Transformers | Dense vector embeddings using `all-MiniLM-L6-v2` (384-dimensional) |
| **Neural Reranking** | Cross-Encoder | Optional candidate reranking using `ms-marco-MiniLM-L-6-v2` |
| **PDF Extraction** | PyMuPDF (`fitz`) | Multi-column layout text extraction and page segmentation |
| **AI Parsing (Optional)** | Groq API | Optional LLM requirement decomposition with 100% offline rule-based fallback |
| **Test Suite** | Pytest | 319 automated unit, integration, contract, and safety tests |

*(Note: Vector similarity is computed directly via NumPy; FAISS is not utilized.)*

---

## Key Features

- **PDF & Plain Text Ingestion**: Ingests full tender PDF documents or individual procurement clause text.
- **Technical Requirement Extraction**: Isolates technical specifications from administrative and bidding boilerplate.
- **Compound Requirement Decomposition**: Decomposes multi-trade sentences into discrete engineering sub-queries.
- **Hybrid Retrieval**: Combines lexical BM25 matching, dense vector semantic embeddings, and deterministic matching.
- **Deterministic Applicability Gates**: Boundary rules block cross-domain mismatches.
- **Ambiguity Detection**: Highlights clauses missing fundamental engineering parameters.
- **Missing Engineering Parameter Detection**: Pinpoints missing DN, PN, metallurgy, and medium parameters.
- **Evidence Grounding Critic**: Verifies clause-level text support before surfacing candidates.
- **Candidate/Evidence Invariant**: Enforces `candidate_standard == evidence_standard` on all recommendations.
- **Safe Abstention**: Deliberately abstains when evidence or technical parameters are insufficient.
- **Superseded Standard Detection**: Identifies withdrawn or replaced standards.
- **Successor Standard Surfacing**: Recommends the authoritative active replacement (e.g. `IS/ISO` standards).
- **Standards Dependency Graph**: Traces normative references, testing codes, and installation guidelines.
- **Lifecycle Validation**: Surfaces active, superseded, or withdrawn status with historical years.
- **Regulatory Signals**: Surfaces indexed Quality Control Orders (QCOs) and associated certification signals where available.
- **Multilingual Technical Normalization**: Normalizes Hindi, Kannada, Tamil, and code-mixed technical terms to canonical identifiers.
- **Prioritized Human Review Queue**: Categorizes tender clauses into actionable readiness tiers.
- **Tender Readiness States**: Computes tender-level readiness (`READY_FOR_REVIEW`, `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`).
- **Structured Report Export**: Generates downloadable JSON and Markdown audit reports.
- **Multi-Item Tender Handling**: Processes tender documents containing multiple distinct technical items.
- **Pre-Packaged Demo Scenarios**: Built-in sample cases for rapid demonstration and testing.

---

## Current Verified Scope

The repository implements a verified, reproducible feasibility prototype:

- **502 Catalogue Records**: Currently indexed in `data/catalogue/catalogue.db` covering broader catalogue metadata across civil, mechanical, electrical, and water supply sectors.
- **90 Core Standards**: Working standards dataset in `data/standards/standards.db` populated with deeper clause-level scope text and relationship graphs (90 distinct IDs, 0 duplicates).
- **20 Real Government Tender PDFs**: Processed end-to-end through document extraction, audit, and reporting without unhandled exceptions (`tenders/` mapped to T001–T020).
- **40-Case Multilingual Benchmark**: Frozen evaluation benchmark across 10 Hindi (`hi`), 10 Kannada (`kn`), 10 Tamil (`ta`), and 10 code-mixed (`mixed`) cases in `dataset/ground_truth/multilingual_benchmark.json`.
- **319 / 319 Tests Passed in Final Freeze Validation**: Verified at final freeze audit with zero failures.

| Dimension | Current Prototype Scope | Future Scale Target |
|---|---|---|
| **Standards Catalogue** | 502 records indexed | 20,000+ national BIS standards |
| **Deep Clause Evidence** | 90 core working standards | Full catalogue clause coverage |
| **Tested Real Tenders** | 20 government PDFs (CPPP/MES/CPWD) | Continuous portal ingestion |
| **Benchmark Suite** | 40 frozen multilingual cases | Expanded multi-sector benchmark |
| **Automated Tests** | 319 unit, integration & safety tests | Expanded CI/CD test harness |

---

## Verified Demo Scenarios

The web interface and API provide three verified demonstration scenarios matching the actual engine outputs:

### Demo 1 — Clear Recommendation (Happy Path)
- **Input**: *"Supply and installation of CPVC pipes and fittings for domestic hot and cold water distribution system, conforming to IS 15778."*
- **Candidate Recommended**: `IS 15778 : 2007` (Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Supplies - Specification).
- **Status & Version Role**: `Active` / `CURRENT_ACTIVE`.
- **Evidence Surfaced**: Verbatim scope clause matches the pipe specification (`evidence_standard == candidate_standard`).
- **Dependencies Surfaced**: `IS 12235 : 2004` (testing methods), `IS 7634 (Part 3) : 2003` (installation code of practice), `IS 4985 : 2000`.
- **Tender Readiness State**: `READY_FOR_REVIEW` (`human_review_required = false`, `ambiguity_state = CLEAR`).

### Demo 2 — Parameter Ambiguity & Safe Review Routing
- **Input**: *"Repair and replacement of valves in the mechanical distribution system."*
- **Outcome**: The engine detects that "valve replacement" lacks essential technical parameters.
- **Missing Parameters Identified**: Valve Type, Nominal Size / Diameter (DN), Pressure Rating (PN / Class), Body Metallurgy / Material, Fluid Medium / Service.
- **Engine Behavior**: Surfaces candidate `IS/ISO 10434 : 2020` with explicit ambiguity warning and routes to human review:
  ```text
  human_review_required = true
  ambiguity_state = REVIEW_REQUIRED
  readiness = REVIEW_REQUIRED
  ```
- **Boundary Abstention Example**: For queries specifying non-submersible surface pumps, the engine's deterministic boundary gates prevent borehole submersible pump standards (`IS 8034`) from matching, safely abstaining:
  ```text
  candidate_standard = null
  evidence_standard = null
  human_review_required = true
  ```

### Demo 3 — Superseded Standard Detection
- **Input**: *"Procurement of bolted bonnet steel gate valves conforming to IS 10611 : 1983."*
- **Outcome**: `IS 10611 : 1983` is identified as superseded.
- **Successor Surfaced**: Recommends the active successor standard `IS/ISO 10434 : 2020` (Bolted Bonnet Steel Gate Valves for the Petroleum, Petrochemical and Allied Industries).
- **Status & Version Role**: `Active` / `CURRENT_ACTIVE`.
- **Human Review**: Routed to technical officers for formal sign-off on the standard code transition (`human_review_required = true`, `readiness = REVIEW_REQUIRED`).

---

## User Workflow

A procurement officer using TenderSaathi follows a clear 10-step review workflow:

1. **Open TenderSaathi**: Access the local web dashboard.
2. **Input Tender Data**: Upload a tender PDF document or paste requirement text clauses.
3. **Start Analysis**: Trigger the automated extraction and audit pipeline.
4. **Review Extracted Requirements**: Inspect segmented clauses and categorized trade items.
5. **Inspect Recommended Standards**: Review recommended Indian Standards with confidence indicators.
6. **Open Evidence Details**: Examine verbatim scope clauses and tracked source provenance.
7. **Review Lifecycle, Dependencies & Regulatory Signals**: Check active/superseded status, companion testing codes, and QCO signals.
8. **Resolve Human Review Items**: Review highlighted parameter gaps (e.g., missing pressure rating or metallurgy).
9. **Check Tender Readiness**: Review overall document readiness status (`READY_FOR_REVIEW`, `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`).
10. **Export Audit Report**: Download complete audit findings as structured JSON or formatted Markdown.

---

## Prototype Preview

The TenderSaathi web interface is structured around operational clarity and defensibility:

- **Tender Requirement Banner**: Displays extracted tender text, requirement ID, and classified engineering category (e.g., `material`, `product_equipment`, `installation_execution`).
- **Candidate Standard Card**: Shows standard number, official title, publication year, and recommendation confidence score.
- **Evidence Drawer**: Expands to display verbatim scope excerpts, relevant section references, and evidentiary provenance (`OFFICIAL_PRIMARY`, `OFFICIAL_SECONDARY`, `VERIFIED`, `CURATED`, `INFERRED`).
- **Lifecycle Indicators**: Color-coded status badges for `Active`, `Superseded`, or `Withdrawn` standards, with direct links to active successor codes.
- **Dependencies List**: Surfaces companion codes of practice, material test methods, and installation standards.
- **Regulatory Alerts**: Displays Quality Control Order (QCO) alerts highlighting certification signals where indexed.
- **Human Review Box**: Pinpoints missing engineering parameters (DN, PN, metallurgy, medium) with targeted clarification guidance.
- **Tender Readiness Indicator**: Displays high-level audit summary badge and export actions for JSON and Markdown reports.

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

# Process a real tender PDF (mapped T001 - T020)
python3 scripts/demo.py --tender T002

# Run full tender audit demo with report generation
python3 scripts/demo.py --audit T001 --report
```

### 5. Run Automated Tests

```bash
# Run the complete test suite (319 tests)
pytest tests/ -q
```

---

## API Endpoints

The Flask server implements the following confirmed REST endpoints (defined in `api/server.py`):

| Method | Endpoint | Purpose | Request Body / Parameters |
|---|---|---|---|
| `GET` | `/api/health` | Health check, service status, and indexed catalogue counts | None |
| `POST` | `/api/analyze/text` | Audits plain text tender requirements | JSON: `{"text": "...", "ai_enabled": false}` |
| `POST` | `/api/analyze/pdf` | Audits an uploaded tender PDF file | `multipart/form-data` with `file` field |
| `GET` | `/api/analyze/sample/<demo>` | Audits pre-packaged demo cases (`cpvc`, `valve`, or `superseded`) | URL path parameter |
| `GET` | `/api/report/<tender_id>/json` | Retrieves structured JSON audit report for a specific tender session | URL path parameter |
| `GET` | `/api/report/<tender_id>/markdown` | Retrieves formatted Markdown audit report for a specific tender session | URL path parameter |
| `GET` | `/api/report/json` | Retrieves latest generated audit report as JSON | None |
| `GET` | `/api/report/markdown` | Retrieves latest generated audit report as Markdown | None |

---

## Project Structure

```text
.
├── api/                  # Flask REST API server and endpoints
│   └── server.py         # REST API server implementation
├── src/                  # Core intelligence, retrieval, audit, and validation engine
│   ├── ai_understanding.py # LLM requirement parsing (optional Groq / offline fallback)
│   ├── applicability.py    # Deterministic boundary gates & applicability checks
│   ├── audit.py            # Master TenderAuditEngine coordinating the pipeline
│   ├── bm25_search.py      # True Okapi BM25 index and retrieval engine
│   ├── catalogue/          # Catalogue provenance models and validation
│   ├── completeness.py     # Specification completeness & missing parameter checks
│   ├── decompose.py        # Compound requirement decomposition
│   ├── dependencies.py     # Standards dependency and normative reference graph
│   ├── evaluate.py         # Benchmark evaluation harness
│   ├── evidence.py         # Scope clause evidence grounding & provenance
│   ├── extract.py          # PDF layout extraction and requirement parsing
│   ├── gap_detection.py    # Missing standard detection & coverage analysis
│   ├── recommend.py        # StandardsRecommender combining search, graph, and gates
│   ├── reranker.py         # Neural Cross-Encoder candidate reranker
│   ├── retrieval.py        # Hybrid weighted score fusion retrieval engine
│   ├── search.py           # Multi-strategy search engine and SQLite queries
│   ├── standards.py        # SQLite schema, data models & relationship graph
│   └── validate.py         # Lifecycle status & supersedence validation
├── frontend/             # React + TypeScript + Vite web interface
│   ├── src/              # UI components, audit cards, evidence drawer
│   └── package.json      # Frontend dependencies and build scripts
├── data/
│   ├── standards/        # Working standards database (90 core standards) and indices
│   ├── catalogue/        # Indexed catalogue database (502 records)
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

## Validation & Testing

The system has undergone systematic automated verification:

- **Automated Regression Suite**: **319 / 319 tests passed in final freeze validation** across schema integrity, retrieval, applicability gates, evidence chains, adversarial safety, API/UI contracts, and failure states (`pytest tests/`).
- **Real Tender E2E Validation**: **20 out of 20 real government tender PDFs** processed through the complete extraction, audit, and report generation pipeline without unhandled exceptions.
- **Frontend Production Build**: The React + TypeScript web application compiles cleanly with zero TypeScript errors (`npm --prefix frontend run build`).
- **Candidate-Evidence Parity**: Verified compliance with the invariant `candidate_standard == evidence_standard` across all non-null recommendations.
- **Adversarial Safety Testing**: Tests verify boundary gates (e.g. non-submersible pump isolation), input injection defense, and safe fallback on missing evidence.
- **API/UI Contract Testing**: Validates end-to-end schema consistency between backend response payloads and frontend card components.
- **Multilingual Benchmark**: Evaluated on 40 frozen cases across 10 Hindi, 10 Kannada, 10 Tamil, and 10 code-mixed requirements; broader language coverage remains future work.
- **Database Integrity**: Exactly 90 rows, 90 distinct IDs, and 0 duplicates confirmed in `data/standards/standards.db`; 502 records confirmed in `data/catalogue/catalogue.db`.

---

## Current Limitations

To maintain technical honesty and defensibility during judging and technical review:

1. **Catalogue Boundaries**: 502 catalogue records are currently indexed, while deeper clause-level evidence is populated for the 90-core working standards set. Full national catalogue coverage across all 20,000+ BIS standards is a roadmap ingestion objective.
2. **Decision-Support Scope**: TenderSaathi is an assistive technical review and audit tool, not a statutory legal certification or autonomous procurement approval system.
3. **Human Review Requirement**: Ambiguous, under-specified, or uncertain clauses are intentionally routed to technical officers for human adjudication.
4. **Scanned Documents**: The system directly processes text-based PDFs; scanned or degraded documents require OCR preprocessing whose accuracy depends on scan legibility.
5. **Regulatory Scope**: Quality Control Order (QCO) verification covers sectors currently indexed in our regulatory database; QCO applicability and enforcement dates require verification against the latest authoritative notification.
6. **E-Procurement Integration**: Direct API connectors to CPPP or GeM portals are architectural roadmap concepts requiring official government access and credentials.

---

## Roadmap

Planned future developments building on the current verified architecture:

- **Expanded Standards Catalogue**: Ingesting additional BIS engineering divisions into the SQLite + BM25 + vector index.
- **Broader Clause-Level Evidence**: Ingesting verified clause-level scope text across the wider catalogue.
- **Wider QCO Gazette Tracking**: Expanding automated mappings to Ministry Quality Control Order notifications across more industries.
- **Enhanced OCR Preprocessing**: Integrating specialized layout-aware OCR for scanned and physical paper tenders.
- **Expanded Multilingual Coverage**: Extending technical normalizers to additional Indian regional languages.
- **Containerized Departmental Deployment**: Packaging Docker microservice containers for secure on-premise deployment.
- **Procurement Workflow Integration**: Integrating with tender drafting workflows to assist technical officers prior to tender publishing.

---

## Documentation

- [SIH Presentation Deck](docs/SIH_PRESENTATION_DECK.md) — 10-slide competitive pitch deck
- [Final SIH Freeze Audit](docs/FINAL_SIH_FREEZE_AUDIT.md) — Final claim integrity and repository freeze report
- [Priority 7 Product Final Audit](docs/PRIORITY_7_PRODUCT_FINAL_AUDIT.md) — Verification of API, UI contracts, and E2E tenders
- [Priority 8 Readiness Audit](docs/PRIORITY_8_FINAL_SIH_READINESS_AUDIT.md) — Demo readiness and presentation alignment audit
- [Priority 6F Remediation Audit](docs/PRIORITY_6F_REMEDIATION_AUDIT.md) — Independent benchmark and engine audit
- [E2E Evaluation Summary](reports/e2e/e2e_summary.md) — Summary of 20 real government tender audits

---

## Project Status

- **Hackathon**: Smart India Hackathon 2026
- **Problem Statement**: SIH26108 (*AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications*)
- **Status**: Verified SIH demo-ready prototype
