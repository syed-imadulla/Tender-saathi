# Tender Saathi

**Evidence-Backed Indian Standards Intelligence & Tender Specification Audit Engine**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Pytest-503%20Passed-brightgreen.svg)]()
[![BIS Catalogue](https://img.shields.io/badge/BIS%20Catalogue-35%2C208%20Standards-blue.svg)]()
[![Benchmark Top-1](https://img.shields.io/badge/Benchmark%20Top--1-90.0%25-success.svg)]()
[![Adversarial Safety](https://img.shields.io/badge/Adversarial%20Safety-98.57%25%20(69%2F70)-brightgreen.svg)]()
[![SIH Problem](https://img.shields.io/badge/SIH-SIH26108-orange.svg)]()

> **"AI interprets. Rules validate. Evidence supports. Humans decide."**

---

## 1. What is Tender Saathi?

**Tender Saathi** is an evidence-backed technical specification review and audit system designed for Indian public procurement (CPPP, GeM, CPWD, MES, Railways, and state authorities). It automates the technical verification of tender documents against authoritative Bureau of Indian Standards (BIS) codes and line-ministry statutory regulations.

### What Tender Saathi Does
- **Extracts Technical Requirements**: Strips procurement boilerplate (EMD, payment terms, turnover criteria) from PDFs and text to isolate genuine technical engineering clauses.
- **Performs Hybrid Standards Retrieval**: Matches requirements across **35,208 BIS catalogue records** using pure-Python Okapi BM25 and dense semantic embeddings.
- **Enforces Engineering Boundary Gates**: Evaluates temperature, pressure, medium, and material conditions to prevent dangerous cross-domain mismatches.
- **Traverses Relationship Graphs**: Identifies 8 canonical relationship types (normative references, test methods, installation codes, safety standards) to bundle complete engineering specifications.
- **Surfaces Regulatory Disclosures**: Ingests advisory mandates from external authorities (FSSAI, CEA, CPWD) and gazetted Quality Control Orders (QCOs).
- **Routes to Prioritized Human Review**: Flags under-specified clauses, missing parameters, and superseded citations into an actionable review queue.
- **Generates Evidence-Grounded Audit Trails**: Exports downloadable JSON and Markdown audit reports with verbatim standard citations and human sign-offs.

### What Tender Saathi Does NOT Do
- It does **not** generate ungrounded recommendations; every candidate must resolve to a verified catalogue standard.
- It does **not** certify legal or structural safety guarantees; it serves as a decision-support advisory system.
- It does **not** silently guess missing engineering parameters; it abstains and asks the technical officer for missing inputs.

---

## 2. System Architecture

Tender Saathi implements a deterministic 10-stage decision-safety pipeline:

```text
  [ Tender PDF / Scanned Image / Plain Text ]
                       │
                       ▼
 1. Document Extraction & Clause Segmentation
                       │
                       ▼
 2. Normalization & Parameter Decomposition
                       │
                       ▼
 3. Hybrid Retrieval (Pure-Python BM25 + NumPy Embeddings)
                       │
                       ▼
 4. Cross-Encoder Reranking & Normalization
                       │
                       ▼
 5. Engineering Applicability & Contradiction Gates
                       │
                       ▼
 6. Ambiguity Detection & Completeness Checking
                       │
                       ▼
 7. Verbatim Evidence Grounding Critic
                       │
                       ▼
 8. Lifecycle & Supersedence Traversal
                       │
                       ▼
 9. Standards Relationship Graph (Depth-1 Horizon)
                       │
                       ▼
10. Regulatory Signals & Human Review Queue Routing
                       │
                       ▼
      [ Interactive UI / JSON & Markdown Reports ]
```

*For detailed component architecture and module references, see [Architecture Overview](docs/architecture/overview.md) and [Module Reference](docs/architecture/modules.md).*

---

## 3. Verified System Performance

Every metric reported below is independently reproducible using the evaluation commands in this repository:

| Metric Category | Verified Performance | Evaluation Reference |
| :--- | :--- | :--- |
| **Unit & Integration Suite** | **503 / 503 Passed (100%)** | `python3 -m pytest -q` |
| **Full BIS Catalogue** | **35,208 standards** indexed | `data/catalogue/bis_catalogue.db` |
| **Curated Core Standards** | **90 standards**, 72 verified relationships | `data/standards/standards.db` |
| **Benchmark Top-1 Accuracy** | **90.0% (18/20)** | `python3 -m src.evaluate` |
| **Mean Reciprocal Rank (MRR)** | **0.900** | `python3 -m src.evaluate` |
| **Negative Control Rejection** | **100.0% (5/5 safe rejections)** | `python3 -m src.evaluate` |
| **Adversarial Safety Pass Rate**| **98.57% (69/70 probes passed)** | `python3 -m src.eval_adversarial` |
| **Ambiguity Detection Recall** | **100.0%** (All under-specified queries caught) | `python3 -m src.eval_adversarial` |
| **Evidence Grounding Invariant**| **100.0%** (Zero hallucinated citations) | `python3 -m src.eval_adversarial` |
| **Prompt Injection Defense** | **100.0% (5/5 contained)** | `python3 -m src.eval_adversarial` |

*For complete evaluation details, see [Benchmark Evaluation](docs/evaluation/benchmark.md) and [Adversarial Suite](docs/evaluation/adversarial_suite.md).*

---

## 4. Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm 9+
- *(Optional)* `tesseract-ocr` and `poppler-utils` for scanned PDF ingestion

### Step 1: Install Python Backend
```bash
git clone <repo-url> sih26108-feasibility
cd sih26108-feasibility

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Install Frontend
```bash
cd frontend
npm install
cd ..
```

### Step 3: Run the Application
In Terminal 1 (Backend REST API):
```bash
python3 -u api/server.py
```
*API running on `http://127.0.0.1:5000`*

In Terminal 2 (Frontend Interface):
```bash
cd frontend
npm run dev
```
*UI accessible at `http://localhost:5173`*

*For complete configuration options, see [Installation Guide](docs/getting-started/installation.md) and [Configuration Guide](docs/getting-started/configuration.md).*

---

## 5. Demos, Tests & Reproducibility

Tender Saathi provides standalone CLI utilities to run demonstrations and evaluations:

```bash
# 1. Interactive CLI Demonstration (Requirement extraction to report generation)
python3 demo.py

# 2. End-to-End Tender PDF Validation
python3 validate_e2e.py

# 3. Run Complete 503-Test Verification Suite
python3 -m pytest -q

# 4. Run Retrieval Ablation Benchmark (20-row standard dataset + 5 negative controls)
python3 -m src.evaluate

# 5. Run 70-Probe Adversarial Stress Test (14 categories × 5 probes)
python3 -m src.eval_adversarial
```

*For execution procedures and test flags, see [Run Guide](docs/getting-started/run_guide.md).*

---

## 6. REST API Overview

The Flask API (`api/server.py`) provides 12 endpoints for headless integration:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Backend status, engine health, and OCR readiness |
| `GET` | `/api/capabilities` | Catalogue size, curated counts, and offline status |
| `POST` | `/api/analyze/text` | Submit plain-text tender specifications |
| `POST` | `/api/analyze/pdf` | Upload native or scanned multi-page tender PDF |
| `POST` | `/api/analyze/image` | Upload scanned tender page image for OCR analysis |
| `GET` | `/api/analyze/sample/<demo>` | Run pre-configured demo (`cpvc`, `valve`, `superseded`) |
| `POST` | `/api/tender/<tender_id>/review` | Submit human reviewer decisions (`ACCEPT`/`EDIT`/`DISMISS`) |
| `GET` | `/api/tender/<tender_id>/review` | Get human review decisions and completion status |
| `GET` | `/api/report/<tender_id>/json` | Download tender audit report in JSON format |
| `GET` | `/api/report/<tender_id>/markdown` | Download tender audit report in Markdown format |
| `GET` | `/api/report/json` | Fetch latest active audit report (JSON) |
| `GET` | `/api/report/markdown` | Fetch latest active audit report (Markdown) |

*For complete request schemas and response examples, see [REST API Reference](docs/api/rest_api.md).*

---

## 7. Standards Relationships & Regulatory Intelligence

In public procurement, specifying an isolated product standard is rarely sufficient. A compliant tender must cite companion test methods, installation codes, and statutory safety regulations.

### 8 Canonical Relationship Types
Tender Saathi models relationships explicitly using a typed directed graph:
- `NORMATIVE_REFERENCE`: Mandatory companion standards cited within the text.
- `TEST_METHOD`: Laboratory and field testing standards (e.g. hydrostatic pressure tests).
- `INSTALLATION_CODE`: Codes of practice for handling, laying, jointing, and commissioning.
- `SAFETY_STANDARD`: Occupational, fire, and structural safety mandates.
- `TERMINOLOGY_STANDARD`: Formal technical glossaries and nomenclature definitions.
- `ALLIED_STANDARD`: Standards covering compatible sister materials or fittings.
- `SUPERSEDES`: Historical lifecycle transitions where an active standard replaces an older code.
- `AMENDS`: Formal corrigenda and addenda issued by BIS sectional committees.

### Statutory Regulatory Boundaries
Tender Saathi incorporates advisory regulatory metadata from external Indian statutory authorities:
- **FSSAI**: Food Safety and Standards Authority of India (e.g. Schedule 4 catering hygiene).
- **CEA**: Central Electricity Authority (e.g. Grid safety and insulation standards).
- **CPWD**: Central Public Works Department (e.g. Works specifications and material codes).

*For architecture details, see [Relationship Graph Documentation](docs/architecture/relationship_graph.md) and [Statutory Boundaries](docs/safety/statutory_boundaries.md).*

---

## 8. Known Limitations & Boundary Disclosures

In accordance with transparent engineering principles, all operational limits are documented:

- **Accepted Catalogue Boundary (`ADV-MUL-005`)**: When composite queries blend equipment appliance manufacturing with mandatory kitchen hygiene regulations, the engine surfaces statutory hygiene codes (`FSSAI Schedule 4`) with `Low` confidence, routing the case to technical review rather than forcing an ungrounded BIS match.
- **Safety Metric Limitation (Lifecycle Traps)**: Evaluated across 14 failure categories and 8 safety metrics (69/70 probes passed = 98.57%). While 7 of 8 metrics met target thresholds, the Lifecycle Trap Catch Rate scored 60.0% (3/5) because under-determined legacy queries routed to human review (`REVIEW_REQUIRED`) rather than asserting automated replacement codes.
- **Scanned Document OCR**: Degraded documents (<150 DPI), skewed scans, or handwritten notes will reduce parameter extraction recall.
- **Strict Depth-1 Traversal**: Relationship graph queries are capped at a depth of 1 to prevent transitive association drift across unverified edges.
- **Decision-Support Scope**: Recommendations do not replace statutory certification by chartered engineers or legal authorities.

*For full disclosure, see [Limitations & Boundary Conditions](docs/evaluation/limitations.md).*

---

## 9. Documentation Sitemap

| Category | Document | Description |
| :--- | :--- | :--- |
| **Getting Started** | [Installation Guide](docs/getting-started/installation.md) | Environment setup, virtualenv, dependencies, verification |
| | [Configuration Guide](docs/getting-started/configuration.md) | Environment variables, offline vs online modes, database paths |
| | [Run Guide](docs/getting-started/run_guide.md) | Web UI, CLI demos, pytest flags, evaluation commands |
| **Architecture** | [Architecture Overview](docs/architecture/overview.md) | 10-stage pipeline, ASCII data flows, design invariants |
| | [Module Reference](docs/architecture/modules.md) | 29 modules in `src/`, pure-Python BM25, embeddings, reranker |
| | [Relationship Graph](docs/architecture/relationship_graph.md) | 8 relationship types, depth=1 horizon, multi-component bundles |
| **Data & Ground Truth** | [Catalogue Reference](docs/data/catalogue.md) | 35,208 BIS records, database schema, change tracking |
| | [Relationships Reference](docs/data/relationships.md) | 72 verified relationships across 5 demonstration domains |
| | [Ground Truth Dataset](docs/data/ground_truth.md) | 20-row frozen benchmark, candidate sets, 5 negative controls |
| **Safety & Guardrails** | [Safety Principles](docs/safety/principles.md) | 4 core principles, 2 invariants, statutory disclaimer |
| | [Safety Guardrails](docs/safety/guardrails.md) | Operating condition gates, contradiction filters, injection defense |
| | [Statutory Boundaries](docs/safety/statutory_boundaries.md) | FSSAI, CEA, CPWD decoupled advisory layer |
| **Evaluation & Quality** | [Benchmark Evaluation](docs/evaluation/benchmark.md) | 20-row benchmark, ablation results, negative control suite |
| | [Adversarial Suite](docs/evaluation/adversarial_suite.md) | 70 probes, 14 categories, 8 metrics, ADV-MUL-005 analysis |
| | [System Limitations](docs/evaluation/limitations.md) | Operational boundaries, OCR limits, conservative bias |
| **API** | [REST API Reference](docs/api/rest_api.md) | 12 active endpoints, schemas, request/response formats |
| **Archive** | [Historical Audits & Presentations](docs/archive/) | Milestone audit trails, frozen records, presentation decks |

---

## License & Attribution

Developed for **Smart India Hackathon (SIH) — Problem Statement SIH26108**.
Authoritative standards metadata derived from the **Bureau of Indian Standards (BIS)** open public catalogue.
