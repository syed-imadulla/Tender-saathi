# Phase 25 Plan: National BIS Catalogue Metadata Retrieval

## Objectives
Enable natural-language tender requirements to retrieve and recommend relevant Indian Standards from the 10,828 active standards in the national BIS catalogue (`data/catalogue/bis_catalogue.db`), breaking free from the 90-standard boundary while enforcing strict evidence boundaries (`PENDING_TECHNICAL_EVALUATION`).

---

## Tasks

### Task 1: Offline FTS5 Index Generator (`scripts/build_catalogue_search_index.py`)
- Query all active records (`status = 'ACTIVE'`) from `data/catalogue/bis_catalogue.db` (`catalogue_standards` table).
- Create `data/catalogue/catalogue_search_index.db` with SQLite FTS5 table `catalogue_fts`:
  - Columns: `canonical_id UNINDEXED`, `standard_number`, `title`, `technical_committee`, `department`, `year UNINDEXED`, `iso_equivalence`, `status UNINDEXED`.
  - Tokenizer: `porter unicode61` or standard unicode61 tokenizer for robust stemming and prefix queries.
- Populate index with compound metadata.
- Measure build time, index file size, and verify query latency under 5ms.

### Task 2: Search Layer Implementation (`src/catalogue/search.py`)
- Implement `NationalCatalogueSearchEngine`:
  - Thread-safe, read-only connection to `catalogue_search_index.db`.
  - Query sanitizer: strip dangerous FTS5 operators (e.g. mismatched quotes, raw boolean errors), split query into terms, support prefix matching (`term*`).
  - Method `search(query: str, top_k: int = 5, min_score: float = 0.0) -> List[CatalogueSearchResult]`.
  - BM25 rank score normalization into a calibrated [0.0, 1.0] scale.
  - Return rich provenance metadata: standard number, title, committee, department, year, status, search score.
  - Graceful degradation if index file is missing.

### Task 3: Two-Tier Cascading Integration (`src/retrieval.py` & `src/recommend.py`)
- In `src/retrieval.py`:
  - Add optional `catalogue_search_engine` parameter to `HybridRetrievalEngine`.
  - In `search()`:
    - First execute curated search.
    - Check cascade condition: if top curated score < 0.65 or 0 results or domain mismatch, execute catalogue search.
    - Merge and deduplicate candidates: if a catalogue candidate matches a curated standard by `canonical_id` or normalized standard number, favor the curated candidate.
- In `src/recommend.py`:
  - Map catalogue-only search results into `TenderRecommendationCandidate` with:
    - `source = "NATIONAL_CATALOGUE_DISCOVERY"`
    - `verification_status = "CATALOGUE_VERIFIED"`
    - `applicability = {"decision": "PENDING_TECHNICAL_EVALUATION", "notes": "Discovered via national catalogue metadata. Full technical clauses not indexed."}`
    - `clause_evidence = None`
    - `human_review_required = True`
  - Safeguard: never fabricate clause text or parameter limits.
  - Reject non-technical / service-only queries cleanly.

### Task 4: API & Frontend Data Contract Compatibility
- Verify `api/server.py` serializes catalogue-discovered candidates properly with standard number, title, committee, lifecycle status, review notice, and confidence.
- Ensure frontend `EvidenceDrawer` and recommendation tables handle `clause_evidence = None` and `PENDING_TECHNICAL_EVALUATION` gracefully with informative badges rather than errors.

### Task 5: Comprehensive Deterministic Test Matrix (`tests/test_national_catalogue_retrieval.py`)
- Test cases:
  1. Discovery of non-curated active standards (e.g., diesel engines `IS 10000`, respiratory equipment `IS 10245`, textile uniforms, cement `IS 8112`).
  2. Multi-part and edition accuracy (exact part numbers preserved).
  3. Deduplication against curated standards (e.g., transformer query prefers curated `IS 1180` over raw catalogue entry).
  4. Withdrawn/superseded standards excluded from proactive NL candidate list.
  5. Weak-match fallback behavior (high confidence curated matches do not unnecessarily dilute with catalogue results; low confidence triggers cascade).
  6. Service-only query handling (abstention/rejection for tenders without product/material standards).
  7. Empty/malformed query safety.
  8. Evidence boundary assurance (no fabricated clause text).
  9. Retrieval latency benchmark (sub-10ms lexical query time).

### Task 6: End-to-End Suite Verification & Graph Update
- Run `pytest -v tests/test_national_catalogue_retrieval.py`.
- Run full repository test suite (`pytest -q`).
- Verify bit-for-bit SHA-256 of `dataset/ground_truth/ground_truth.csv` (`8bcc9bc5...`).
- Run `graphify update .`.
- Produce Phase 25 Verification & Audit Report.
