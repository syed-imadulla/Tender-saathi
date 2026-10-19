# Tender Saathi — Active Planning State

**Active Milestone**: Milestone: National BIS Catalogue Integration & Multi-Package Tender Auditing  
**Current Phase**: Phase 38 (`38-production-reality-check`)  
**Phase Position**: Phase 38 Complete (Tasks 1-5 Verified: CPU-Optimized Backend Dockerfile & Multi-Container Build, 12 Canonical User Scenarios Automated in tests/test_phase38_production_reality.py, CSV Formula Injection Defense, Corrupted PDF HTTP 400 Handling, Direct Database Counts Audited, Backend Test Suite Passed, Frontend Vitest 12/12 Passed, Clean Vite Production Build, Comprehensive Reality Check Report in docs/evaluation/PHASE38_PRODUCTION_REALITY_CHECK.md, UAT Sign-Off in .planning/phases/38-production-reality-check/38-UAT.md, and Ground Truth Baseline SHA-256 Preserved)  
**Working Directory**: `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Git Head**: `main`

---

## Current Situation

1. **Phases 1-37**: Complete and verified across historical milestones.
2. **Phase 38 Tender Saathi Production Reality Check & End-to-End Demo Validation**:
    - **Docker CPU Optimization**: Updated `Dockerfile` to install CPU-only PyTorch (`--extra-index-url https://download.pytorch.org/whl/cpu`) with `--default-timeout=120`, avoiding >1.2GB of unused CUDA wheels and cutting build times dramatically. Both `tendersaathi-backend:smoke` and `tendersaathi-frontend:smoke` build cleanly and pass health checks (`/api/health` returning HTTP 200).
    - **12 Canonical User Scenarios Tested**: Implemented and passed all 12 scenarios in `tests/test_phase38_production_reality.py`:
      1. CPVC pipe grounded recommendation (`IS 15778 : 2007`, `CLAUSE_VERIFIED`).
      2. Mixed multi-package tender (cables `IS 694` + commercial EMD safe abstention).
      3. Catalogue-discovered item (`IS 10245` breathing apparatus with transparent `CATALOGUE_DISCOVERED` tier and `human_review_required=True`).
      4. Withdrawn/superseded lifecycle status exposure.
      5. Underspecified requirements ambiguity handling.
      6. Physically incompatible parameters (PVC pipe at 220°C) rejection.
      7. Native digital PDF upload and requirement parsing (`sample_tender.pdf`).
      8. Scanned / corrupted PDF graceful HTTP 400 Client Error handling.
      9. Human review decision persistence in report cache and Section 8 Markdown trails.
      10. Multi-format report export consistency and CSV formula injection sanitization.
      11. Standards graph traversal (`IS 1255`) depth-1 non-elevation.
      12. Boundary, malformed JSON, and oversized upload error handling.
    - **Security & Integrity Hardening**:
      - Defect Fix 1: Corrupted/invalid PDF uploads now return HTTP 400 Bad Request instead of unhandled HTTP 500 error.
      - Defect Fix 2: Sanitized CSV report cells against formula injection attacks (`=`, `+`, `-`, `@`).
    - **Direct Database Counts Audited**:
      - `data/catalogue/bis_catalogue.db`: 35,208 total catalogue records (10,828 Active, 13,024 Unknown, 11,340 Withdrawn, 16 Superseded).
      - `data/catalogue/catalogue_search_index.db`: 23,510 active FTS5 BM25 records.
      - `data/standards/corpus.db`: 13 registered standards with 53 authentic normative passages.
      - `data/standards/standards.db`: 99 curated core standards, 60 references, 197 relationships.
    - **Benchmark Ground Truth Invariance**: Confirmed bit-for-bit SHA-256 invariance for `dataset/ground_truth/ground_truth.csv` (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).
    - **Verdict**: 🟢 **GO FOR PRODUCTION & LIVE SIH JURY EVALUATION**.

---

## Active Phase Overview: Phase 38

| Plan ID | Title | Scope & Target Files | Deliverable | Status |
|---|---|---|---|---|
| **38-PRODUCTION-REALITY-CHECK** | Tender Saathi Production Reality Check & End-to-End Demo Validation | `Dockerfile`, `api/server.py`, `tests/test_phase38_production_reality.py`, `docs/evaluation/PHASE38_PRODUCTION_REALITY_CHECK.md`, `.planning/phases/38-production-reality-check/38-UAT.md` | CPU-optimized backend container, 12-scenario integration test suite, CSV formula injection defense, PDF error hardening, direct database count audit, and production verification sign-off. | **Complete** |

---

## Next Steps (Human Boundary)

1. Review Phase 38 evaluation audit: `docs/evaluation/PHASE38_PRODUCTION_REALITY_CHECK.md`.
2. Launch live application via Docker Compose (`docker compose up -d`) or local dev (`python3 api/server.py` + `npm run dev`).
3. Rehearse the 5-minute presentation script (`docs/demo/SIH_LIVE_DEMO.md`) and consult `docs/demo/JUDGE_QA.md` for jury defense.
