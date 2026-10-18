# Tender Saathi — Project Overview & GSD Planning Baseline

**Repository**: `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Current Milestone**: Phase 12 — Benchmark Transparency, Ground-Truth Quality & Source Provenance  
**Architecture**: Python/Flask Backend + Vite/React Frontend + SQLite BIS Catalogue + Hybrid Retrieval (Okapi BM25 + Dense Embeddings + Cross-Encoder) + Evidence-Aware Decision Safety Pipeline.

---

## 1. Project Context & Objectives

Tender Saathi is an AI-powered standards-recommendation system designed to assist procurement officers across Indian public works organizations (CPWD, MES, Railways, Heavy Water Board, Municipal Corporations) in identifying, verifying, and citing applicable Indian Standards (BIS/IS).

The system addresses three critical failure modes in public procurement:
1. **Citation of Superseded or Withdrawn Standards**: Prevents legal challenges by automatically mapping outdated standards (e.g. `IS 10611`) to active replacements (`IS/ISO 10434`).
2. **Missing Engineering Parameters**: Detects under-specified requirements (e.g., pumps without discharge/head specifications) and flags them as `INCOMPLETE` with actionable clarification questions.
3. **Competing Standards & Ambiguity**: Detects ambiguous specifications where multiple standards could apply (e.g., sluice valves vs. gate valves) and flags them as `AMBIGUOUS`.

---

## 2. Milestone History & Current Baseline

| Phase / Milestone | Focus | Key Deliverables & Outcome | Status |
|---|---|---|---|
| **Phases 01–04** | Core Engine & Catalogue Ingestion | Deterministic search, Okapi BM25, BIS catalogue SQLite database (35k+ records), embeddings. | Completed |
| **Phase 05** | Human Review Workflow | Decision audit trail, reviewer notes (`ACCEPT`, `EDIT`, `DISMISS`), exportable reports. | Completed |
| **Phase 06** | Adversarial Evaluation | Rejection of nonsensical distractor tokens, anti-hallucination gates. | Completed |
| **Phase 07** | Remediation & Hardening | Multilingual technical normalization (Indic/Hinglish to canonical engineering concepts). | Completed |
| **Phase 08** | Decision Safety Gates | 10-stage decision safety pipeline, Operational Envelope checks, Conflict Registry. | Completed |
| **Phase 09** | Standards Relationships & Regulatory | Normative references, QCO mandatory certification, CRS, Hallmarking intelligence. | Completed |
| **Phase 10** | Docs & Developer Experience | Architecture documentation, API contracts, local development guides. | Completed |
| **Phase 11** | Production Deployment Prep | Decoupled architecture design (Vercel frontend + dedicated container backend). | Completed |
| **Phase 1 Remediation** | Recommendation Traceability Remediation | Remediated AUDIT-01 (subcomponent review rollup), AUDIT-02 (frontend recommendation list filtering), and AUDIT-04 (`ReviewStatus` canonical enum). | **Verified & Committed (`898a6e8`)** |
| **Phase 2A** | Deterministic Offline Testing | Session network blocker in `conftest.py`, offline HuggingFace environment, deterministic fixtures for `test_05` and `test_05b`. Full suite runs offline in 58s with 516/516 passed. | **Verified & Active** |
| **Phase 12 (Phase 2B)** | **Benchmark Transparency & Ground-Truth Provenance** | Audit and expand ground truth, separate machine vs expert labels, multi-metric evaluation harness, source document binding. | **Active (Planning)** |

---

## 3. Technology Stack & Key Constraints

- **Backend**: Python 3.10+ (Flask, PyTorch, SentenceTransformers, SQLite, pdfplumber).
- **Frontend**: React 18, TypeScript, Vite 5, Tailwind-free Vanilla CSS.
- **Knowledge Graph**: Graphify AST knowledge graph (`graphify-out/`).
- **Core Invariant**: Zero changes to recommendation scoring, ranking weights, or threshold constants without demonstrated defects and explicit user sign-off.
- **Data Integrity Invariant**: Machine-generated labels must never be conflated with expert-adjudicated labels. Never invent reviewer identities, signatures, or synthetic `human_verified: TRUE` flags.
