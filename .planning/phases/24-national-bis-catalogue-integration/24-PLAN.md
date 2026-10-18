# Phase 24 Plan: National BIS Catalogue Integration

## Objectives
Connect the 35,208-record national catalogue (`data/catalogue/bis_catalogue.db`) to Tender Saathi's tender recommendation pipeline, eliminating false `NONEXISTENT_CITATION` alerts and recognizing all valid Indian Standards while strictly preserving evidence safeguards.

---

## Tasks

### Task 1: Reusable National Catalogue Access Layer (`src/catalogue/access.py`)
- Implement a thread-safe, read-only data access class `NationalCatalogueDatabase`:
  - Default database path: `data/catalogue/bis_catalogue.db`.
  - Parameterized queries to prevent SQL injection.
  - Lookup methods:
    - `lookup_by_identifier(identifier: str)`: Normalizes identifier, matches `canonical_id`, `standard_number`, or base number + part.
    - `find_all_editions(base_number: str, part: Optional[int] = None)`: Retrieves all historical and current editions.
    - `get_catalogue_metadata(canonical_id: str)`: Returns full record dict.
  - Graceful degradation if database is missing or corrupt.

### Task 2: Refactor Citation Validation Engine (`src/validate.py`)
- Enhance `validate_standard_status(standard_identifier, db)`:
  - First check `standards.db` for existing curated standards and explicit `SUPERSEDES` relationships.
  - Query `NationalCatalogueDatabase` for catalogue existence and official metadata.
  - Classify outcome into four canonical states:
    - `FOUND_ACTIVE`
    - `FOUND_WITHDRAWN_OR_SUPERSEDED`
    - `FOUND_STATUS_UNKNOWN`
    - `NOT_FOUND`
  - Edition Ambiguity Resolution:
    - If multiple editions exist, select latest active edition as primary, but attach `EDITION_AMBIGUITY_REVIEW` notice listing all available editions.
  - Return enriched `StandardValidationResult` with `catalogue_record`, `is_catalogue_verified`, `lifecycle_status`, and `ambiguity_warnings`.

### Task 3: Recommendation Pipeline & API Integration (`src/recommend.py`, `api/server.py`)
- In `StandardsRecommender.recommend_for_requirement()`:
  - When explicit citation is validated in the national catalogue (even if absent from `standards.db`):
    - Do NOT emit `NONEXISTENT_CITATION`.
    - Inject as a `VALIDATED_NATIONAL_CITATION` candidate.
    - Set `applicability = PENDING_TECHNICAL_EVALUATION`, `evidence_completeness = UNINDEXED_IN_SEMANTIC_CORPUS`.
    - Do NOT invent or fabricate clause passages, technical parameters, or normative edges.
  - For genuinely unknown identifiers (`NOT_FOUND`), retain `NONEXISTENT_CITATION` and anti-fallthrough protection.
  - Ensure reports and API responses carry the catalogue metadata and review warnings cleanly.

### Task 4: Comprehensive Test Suite (`tests/test_national_catalogue_validation.py`)
- Implement deterministic unit and API tests:
  1. Valid catalogue-only citations (`IS 8112`, `IS 1489 Part 1`, `IS 10000`, `IS 10245`) verified without nonexistent warnings.
  2. Genuinely fake standards (`IS 999999`, `IS FAKE 1234`) correctly flagged `NONEXISTENT_CITATION`.
  3. Withdrawn and superseded standards receive authoritative warnings and successor links where available.
  4. Edition ambiguity detection across multi-edition standards (`IS 2712`).
  5. Catalogue-only candidates have `UNINDEXED_IN_SEMANTIC_CORPUS` and zero fabricated clause text.
  6. Existing curated standards (`IS 1180`, `IS 778`) continue to receive full clause-level evidence verification.
  7. API integration test via `POST /api/analyze/text` with both curated and catalogue-only inputs.

### Task 5: Safety Verification & Phase Report
- Run `pytest -q` on full test suite to guarantee 0 regressions.
- Verify `dataset/ground_truth/ground_truth.csv` SHA-256 invariant (`8bcc9bc5...`).
- Produce summary report documenting before/after validation flow, test results, and next phase requirements.
