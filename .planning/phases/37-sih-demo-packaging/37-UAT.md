# Phase 37 — User Acceptance Testing (UAT)

## Phase Objective
Prepare Tender Saathi for a professional Smart India Hackathon demonstration by providing turnkey multi-container Docker Compose deployment, end-to-end workflow verification, coverage transparency, a five-minute live demo script, and comprehensive judge Q&A preparation.

---

## Acceptance Criteria & Test Results

### 1. Deployment Packaging & Docker Verification
- [x] **Multi-Container Docker Compose (`docker-compose.yml`)**:
  - `backend` service configured on port 5000 with gunicorn WSGI, healthchecks (`/api/health`), and volume-mounted reports.
  - `frontend` service configured on port 3000 with Nginx Alpine reverse-proxying `/api/` to `backend:5000`.
- [x] **Nginx Production Reverse Proxy (`frontend/nginx.conf`)**:
  - Proxies `/api/` calls seamlessly with 180s timeout and 30 MB body size.
  - Implements SPA history routing fallback (`try_files $uri $uri/ /index.html;`).
  - Sets security headers (`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`).
- [x] **Environment Hygiene (`.env.example`)**:
  - Full variable documentation (`PORT`, `CORS_ORIGINS`, `REPORT_DIR`, `TENDERSAATHI_LLM_ENABLED`, `GROQ_API_KEY`).
  - Zero hardcoded secrets, API keys, or machine-specific paths.
- [x] **Local Development Fallback**:
  - Documented dual execution path in `README.md` (`python3 api/server.py` + `npm run dev`).

### 2. Live Demo Package & Presentation Readiness
- [x] **5-Minute Live Presentation Script (`docs/demo/SIH_LIVE_DEMO.md`)**:
  - Click-by-click presenter guide timed to 5 minutes.
  - **Stage 1 (Clause-Verified Recommendation)**: Civil engineering CPVC pipe (`IS 15778 : 2007`), showing exact clause grounding (Clause 1, Clause 8), active QCO mandate (`S.O. 1205(E)`), and Scheme-I certification.
  - **Stage 2 (Multi-Requirement Partitioning & Commercial Abstention)**: Mixed electrical/plumbing tender (`IS 694 : 2010`) alongside commercial payment clauses (advance bank guarantee, delay penalty) with safe abstention (`candidate_standard=None`, 0 hallucinated standards).
  - **Stage 3 (Catalogue Discovery & Human Review Queue)**: Breathing apparatus (`IS 10245`) with transparent `CATALOGUE_DISCOVERED` tier and interactive officer review recording (`ACCEPT` / `EDIT` / `DISMISS`).
  - Complete contingency plan for network failure or slow inference.
- [x] **Judge Q&A & Technical Differentiation Guide (`docs/demo/JUDGE_QA.md`)**:
  - Rigorous answers addressing 10 canonical judge questions (hallucination defense, multi-package decomposition, lifecycle governance, physical conflict detection, offline reliability, and scaling roadmap).

### 3. Verification & Invariant Sign-Off
- [x] **Phase 37 Demo Packaging Test Suite (`tests/test_phase37_demo_packaging.py`)**: 8 passed / 8 passed (100%).
- [x] **Backend Test Suite (`pytest`)**: 799 passed / 799 total (100% pass rate, 0 regressions).
- [x] **Frontend Vitest Suite (`vitest`)**: 12 passed / 12 total (100% pass rate).
- [x] **Production Bundle Build (`npm run build`)**: Clean build (`dist/index.html` + assets in 1.98s).
- [x] **Benchmark Ground-Truth Integrity**: SHA-256 remains `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.
- [x] **SIH Demo Readiness Verdict**: 🟢 **GO FOR SIH DEMONSTRATION**.
