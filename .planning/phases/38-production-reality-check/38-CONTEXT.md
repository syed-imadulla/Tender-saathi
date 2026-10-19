# Phase 38 — Tender Saathi Production Reality Check & End-to-End Demo Validation: Context & Decisions

## 1. Background & Scope

Phase 38 is an evidence-based production reality check of the complete Tender Saathi stack.
Priority: **working product over more features**.

### Decisions Locked from Discussion:
1. **Docker PyTorch Optimization**:
   - Backend `Dockerfile` will install CPU-only PyTorch (`--extra-index-url https://download.pytorch.org/whl/cpu`) to avoid downloading >1.2GB of unused NVIDIA CUDA dependencies, cutting container build time from 15 minutes to under 1 minute while keeping 100% offline runtime capability.
2. **Full End-to-End Verification Depth**:
   - Build and launch the live application via Docker Compose (and verify native fallback).
   - Test all 12 canonical user workflow scenarios against the live running API/UI.
   - Audit database counts directly from SQLite files rather than relying on prior written reports.
   - Audit security, persistence, and evidence integrity.

---

## 2. The 12 User Scenarios to Validate

1. **Supported CPVC Pipe**: Technical requirement producing grounded, active `IS 15778 : 2007` with `CLAUSE_VERIFIED` badge and verbatim gazette passage.
2. **Mixed Multi-Package Tender**: Technical pump requirement alongside commercial terms (EMD, bank guarantee, delay penalty) with safe commercial exclusion (`candidate_standard=None`).
3. **Catalogue-Discovered Standard**: Underspecified pump / breathing apparatus (`IS 10245`) with `CATALOGUE_DISCOVERED` badge and human review requirement clearly disclosed.
4. **Withdrawn / Superseded Standard**: Citation of obsolete standard (`IS 4984 : 1995` or similar) correctly flagged with warning, never silently promoted to active.
5. **Underspecified Requirement**: Requirement missing critical parameters (e.g. pressure class, medium) safely routed to clarification/review queue.
6. **Physically Incompatible Requirement**: Impossible engineering parameters (e.g. PVC pipes for steam at 180°C) triggering applicability gate rejection.
7. **Digital PDF Upload**: Extraction of digital text PDF (`tests/fixtures/sample_tender.pdf`) through ingestion endpoint without OCR degradation.
8. **Scanned PDF / OCR Distinction**: Clearly distinguish digital PDF extraction from scanned image OCR fallback; test error and fallback handling.
9. **Human Review Decision Persistence**: Log decision (`ACCEPT`/`EDIT`/`DISMISS`), refresh/reload, and verify persistence in cache and report export.
10. **Report Downloads**: Generate and download both Markdown and structured CSV reports, verifying column consistency and formula-injection safety.
11. **Standards Graph Traversal**: Query standard relationships (`IS 1255`), inspecting depth-1 normative references without ungrounded elevation.
12. **Boundary & Malformed Requests**: Upload oversized files, unsupported filetypes, empty payloads, and malformed JSON, verifying graceful HTTP 400/413/422 handling.

---

## 3. Verified Baseline Data Boundary (Direct SQLite Audit)

- `data/catalogue/bis_catalogue.db`: **35,208 total records**
  - Active: 10,828
  - Unknown: 13,024
  - Withdrawn: 11,340
  - Superseded: 16
- `data/catalogue/catalogue_search_index.db`: **23,510 active FTS5 BM25 records** (10,828 Active + 13,024 Unknown - non-indexed/quarantined)
- `data/standards/corpus.db`: **13 registered standards** with **53 authentic normative passages**
- `data/standards/standards.db`: **99 curated standards**, **60 references**, **197 relationships**

---

## 4. Invariants

- `dataset/ground_truth/ground_truth.csv` SHA-256 remains invariant: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.
- Zero fabrication of synthetic clauses.
- Zero silent elevation of catalogue metadata to clause-verified status.
