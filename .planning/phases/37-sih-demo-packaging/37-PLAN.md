# Phase 37 — Execution Plan: SIH Demo Packaging, Deployment Readiness & Judge Presentation

**Repository:** `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Branch:** `main`

---

## Plan Structure

### Task 1: Deployment Packaging (Docker & Docker Compose)
- Audit backend `Dockerfile` to ensure all necessary directories (`data/`, `api/`, `src/`, `reports/`) and system libraries are included.
- Create `frontend/Dockerfile` (multi-stage build with Node 20 builder and Nginx Alpine server) and `frontend/nginx.conf` (routing `/api/` to backend and handling SPA history routing).
- Create root `docker-compose.yml` linking `backend` and `frontend` services with network isolation, healthchecks, environment injection, and volume mounts.
- Update `.dockerignore` and `.env.example`.
- Document both Docker and local developer setup in `README.md`.

### Task 2: Targeted Demonstration & Configuration Test Suite
- Create `tests/test_phase37_demo_packaging.py`:
  - Validate Docker Compose file syntax and required services/ports.
  - Validate `frontend/nginx.conf` proxy pass and SPA fallback directives.
  - Validate `.env.example` contains all required keys and zero actual secret values.
  - Test live demo scenario payloads directly against API endpoints (`/api/analyze/text`, `/api/analyze/pdf`, `/api/report/<id>/csv`, `/api/report/<id>/markdown`).
  - Verify that demo fixtures match the 3-stage presentation narrative accurately.

### Task 3: Five-Minute Live Demo Package
- Create `docs/demo/SIH_LIVE_DEMO.md`:
  - Click-by-click presenter script timed to 5 minutes.
  - Stage 1: Problem statement & single-requirement civil tender (IS 15778 CPVC pipe).
  - Stage 2: Multi-package electrical/plumbing tender with commercial clauses (IS 694 + safe abstention on bank guarantee / penalty).
  - Stage 3: Catalogue-discovered item lacking normative passages (IS 10245) + Human Review Decision queue (`ACCEPT`, `EDIT`, `DISMISS`).
  - Fallback contingency protocol (pre-cached reports, local offline fallback, network isolation procedures).

### Task 4: Judge Q&A & Technical Differentiation Guide
- Create `docs/demo/JUDGE_QA.md`:
  - Provide concise, rigorous, evidence-backed answers to the 10 canonical hackathon judge questions.
  - Differentiate clearly between implemented features, verified benchmark results, and future roadmap phases.
  - Clarify statutory authority, provenance tiers (`VERIFIED` vs `CURATED` vs `INFERRED`), and non-elevation traversal rules.

### Task 5: Final System Verification & Audit Report
- Run backend pytest tests, frontend vitest tests, and production build.
- Verify ground-truth SHA-256 integrity (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).
- Create `docs/evaluation/PHASE37_DEMO_DEPLOYMENT_AUDIT.md`.
- Create `.planning/phases/37-sih-demo-packaging/37-UAT.md`.
- Update `.planning/STATE.md` and `.planning/ROADMAP.md`.
- Run `graphify update .`.
