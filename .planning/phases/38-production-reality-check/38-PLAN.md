# Phase 38 — Tender Saathi Production Reality Check & End-to-End Demo Validation: Plan

## Executive Plan

Execute a comprehensive, evidence-based reality check of the complete Tender Saathi application running in production and containerized environments.

---

## Work Breakdown

### Task 1: Dockerfile CPU Optimization & Clean Container Launch
- Update `Dockerfile` to install CPU-only PyTorch (`--extra-index-url https://download.pytorch.org/whl/cpu`) prior to `requirements.txt`.
- Build the backend container and frontend container via `docker compose build`.
- Spin up `docker compose up -d` and verify:
  - Backend health check at `http://localhost:5000/api/health`
  - Frontend serving at `http://localhost:3000`
  - Nginx `/api/` reverse proxy connectivity
  - Report directory mount and persistent storage
- Test offline behavior (confirm that containers do not make external calls once launched).

### Task 2: Live Integration Testing of 12 Canonical User Scenarios
- Write and run an end-to-end integration suite `tests/test_phase38_production_reality.py` executing all 12 user scenarios:
  1. CPVC pipe recommendation (`IS 15778 : 2007`, `CLAUSE_VERIFIED`, verbatim gazette clause).
  2. Multi-requirement tender (pump + commercial bank guarantee/delay penalty, safe exclusion).
  3. Catalogue-discovered standard (`IS 10245` breathing apparatus, `CATALOGUE_DISCOVERED` badge, review required).
  4. Withdrawn/superseded standard warning check.
  5. Underspecified requirement ambiguity handling.
  6. Physically incompatible engineering parameters rejection.
  7. Digital PDF upload (`tests/fixtures/sample_tender.pdf`).
  8. Scanned PDF fallback & OCR verification.
  9. Human review persistence across page reloads and report updates.
  10. Markdown and CSV report generation & formula injection safety.
  11. Standards graph traversal (`IS 1255`) depth-1 non-elevation.
  12. Boundary, malformed JSON, and oversized upload error handling.

### Task 3: Security & Operational Audit
- Verify that CSV exports properly escape leading formula trigger characters (`=`, `+`, `-`, `@`).
- Verify upload size limits (30MB in Nginx, MAX_CONTENT_LENGTH in Flask).
- Verify CORS configuration and production debug flags (`FLASK_DEBUG=false`).
- Confirm zero secret leaks in logs, error payloads, or public endpoints.

### Task 4: Full Verification, Documentation & UAT Sign-Off
- Run full pytest test suite (including new Phase 38 reality check tests).
- Run frontend Vitest suite and production build (`npm run build`).
- Verify benchmark SHA-256 invariance (`dataset/ground_truth/ground_truth.csv`).
- Generate `docs/evaluation/PHASE38_PRODUCTION_REALITY_CHECK.md`.
- Produce `38-UAT.md` with line-by-line acceptance outcomes.
- Update `.planning/STATE.md` and `.planning/ROADMAP.md`.
