# Phase 37 — Context & Decision Record: SIH Demo Packaging, Deployment Readiness & Judge Presentation

**Repository:** `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Branch:** `main`  
**Date:** October 20, 2026  
**Status:** In Progress

---

## 1. Locked Decisions & Core Objectives

From user alignment and Phase 36 audit baseline:

1. **Docker Deployment Architecture**:
   - Multi-container `docker-compose.yml` defining:
     - `backend`: Flask API serving production WSGI (`gunicorn`), listening on port 5000, running on Python 3.11-slim with system OCR dependencies (`tesseract-ocr`, `poppler-utils`). Healthcheck against `/api/health`.
     - `frontend`: High-performance Nginx Alpine container serving production Vite/TypeScript static build on port 3000 (or 5173), reverse-proxying `/api/` calls seamlessly to `backend:5000`.
     - Volume-mounted persistent directory for generated reports (`reports/generated`).
   - Pure environment variable configuration via `.env.example` with zero hardcoded credentials or machine-specific paths.
   - Documented dual execution path: Turnkey Docker Compose vs Standard local developer setup (`python3 api/server.py` + `npm run dev`).

2. **SIH Live Demo Narrative (5-Minute Package)**:
   - Three-stage clear progression documented in `docs/demo/SIH_LIVE_DEMO.md`:
     1. **Stage 1 (Clause-Verified Recommendation)**: Civil engineering CPVC pipe procurement (`IS 15778 : 2007`). Shows exact clause grounding (Clause 1 Scope, Clause 8 Hydrostatic Pressure), active QCO mandate, Scheme-I certification, and publication readiness score.
     2. **Stage 2 (Multi-Requirement Partitioning & Commercial Abstention)**: Mixed tender featuring electrical wiring (`IS 694 : 2010`) alongside commercial payment clauses (advance bank guarantee, delay liquidated damages). Demonstrates clean requirement decomposition and safe abstention on financial terms without fabricating engineering standards.
     3. **Stage 3 (Catalogue Discovery & Human Review Queue)**: Breathing apparatus (`IS 10245`) or underspecified pump. Demonstrates honest `CATALOGUE_DISCOVERED` verification tier ("Pending technical clause indexing in local semantic corpus; manual engineering review required") and human review decision workflow (`ACCEPT` / `EDIT` / `DISMISS`).
   - Fallback contingency protocols for network interruption, model timeout, or scan anomalies.

3. **Judge Q&A & Technical Differentiation (`docs/demo/JUDGE_QA.md`)**:
   - Defensible, evidence-backed answers addressing:
     - Architectural difference from standard BIS keyword search.
     - Multi-package requirement partitioning.
     - Clause-level evidence grounding vs LLM hallucination.
     - Lifecycle governance (withdrawn/superseded standards and successor mapping).
     - Missing parameter detection and physical conflict prevention (e.g. HDPE 250°C thermal violation).
     - Scope boundaries (13 standards with authentic statutory passages vs 23,510 active catalogue records).
     - Deterministic safety gates and human-in-the-loop audit trail.
     - Concrete future scaling roadmap.

4. **Strict Invariants**:
   - Benchmark ground truth checksum must remain invariant: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.
   - Zero fabrication of unauthenticated standards, clauses, or performance statistics.
   - Non-elevation safety invariant for traversed cross-references.
