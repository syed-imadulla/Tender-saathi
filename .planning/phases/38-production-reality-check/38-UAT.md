# Phase 38 — User Acceptance Testing (UAT) & Production Reality Check

## Phase Objective
Perform an evidence-based production reality check of the complete Tender Saathi application across container deployment, the 12 canonical user scenarios, database boundary verification, security hardening, and end-to-end integration stability.

---

## Acceptance Criteria & Test Results

### 1. Docker Multi-Container Deployment Verification
- [x] **Backend Container (`tendersaathi-backend:smoke`)**:
  - Optimized with CPU-only PyTorch (`--extra-index-url https://download.pytorch.org/whl/cpu`) and `--default-timeout=120`, cutting build time and eliminating >1.2GB of unused CUDA wheels.
  - Successfully built and tested (`docker run` on port 5055 returning HTTP 200 `{"status": "ok"}` on `/api/health`).
- [x] **Frontend Container (`tendersaathi-frontend:smoke`)**:
  - Multi-stage Node.js builder + Nginx Alpine runtime successfully compiled and verified (exit 0).
  - Reverse proxy routing `/api/` to `backend:5000/api/` with 180s timeout and 30MB payload capacity.
- [x] **Docker Compose Configuration (`docker-compose.yml`)**:
  - `docker compose config` structurally validated with persistent volume `reports_data` and healthcheck dependency.

### 2. The 12 Canonical User Scenarios (`tests/test_phase38_production_reality.py`)
- [x] **Scenario 1 (Supported CPVC Pipe)**: CPVC pipe query yields `IS 15778 : 2007` grounded with authentic gazette passages and `CLAUSE_VERIFIED` tier.
- [x] **Scenario 2 (Mixed Technical & Commercial)**: Isolates technical cables (`IS 694 : 2010`) while safely abstaining on commercial EMD / bank guarantee clauses (0 hallucinated standards).
- [x] **Scenario 3 (Catalogue-Discovered Item)**: Correctly identifies `IS 10245` breathing apparatus in catalogue search index while transparently flagging `CATALOGUE_DISCOVERED` and `human_review_required=True`.
- [x] **Scenario 4 (Withdrawn/Superseded Warnings)**: Exposes recorded lifecycle status accurately via `/api/standards/search?q=IS 4984`.
- [x] **Scenario 5 (Underspecified Requirements)**: Vague pipe query lacking engineering parameters flags review/ambiguity without silent guessing.
- [x] **Scenario 6 (Physically Incompatible Parameters)**: Impossible parameters (PVC pipes for superheated steam at 220°C) triggers safe engineering applicability rejection.
- [x] **Scenario 7 (Digital PDF Ingestion)**: Native PDF ingestion (`tests/fixtures/sample_tender.pdf`) extracts requirements cleanly via PyMuPDF without OCR noise.
- [x] **Scenario 8 (Corrupted / Scanned File Handling)**: Invalid or corrupted binary files return clean HTTP 400 Client Error instead of crashing the server with HTTP 500.
- [x] **Scenario 9 (Human Review Persistence)**: Officer decisions (`ACCEPT`/`EDIT`/`DISMISS`) submitted via `/api/tender/<id>/review` persist in report cache and appear in Section 8 Markdown review trails.
- [x] **Scenario 10 (CSV Export & Formula Injection Defense)**: CSV export properly escapes formula trigger characters (`=`, `+`, `-`, `@`) with a leading single quote (`'`), preventing spreadsheet formula execution.
- [x] **Scenario 11 (Standards Graph Traversal)**: Traverses depth-1 normative relationships (`IS 1255`) without ungrounded elevation of secondary standards to primary recommendations.
- [x] **Scenario 12 (Boundary & Error Handling)**: Gracefully handles empty payloads, invalid JSON, and non-existent IDs with appropriate HTTP 400/404/422 status codes.

### 3. Direct Database Record Boundary Verification
- [x] `data/catalogue/bis_catalogue.db`: **35,208 total catalogue records**
  - ACTIVE: 10,828
  - UNKNOWN: 13,024
  - WITHDRAWN: 11,340
  - SUPERSEDED: 16
- [x] `data/catalogue/catalogue_search_index.db`: **23,510 active FTS5 BM25 records**
- [x] `data/standards/corpus.db`: **13 registered standards** with **53 authentic normative passages**
- [x] `data/standards/standards.db`: **99 curated core standards**, **60 references**, **197 relationships**

### 4. Integrity & Benchmark Checksums
- [x] `dataset/ground_truth/ground_truth.csv` SHA-256: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Invariant).
- [x] Zero synthetic clause fabrication.
- [x] Zero silent promotion of catalogue metadata to clause-verified status.

---

## Executive Verdict
🟢 **GO — PRODUCTION REALITY CHECK PASSED & SIH DEMO READY**
