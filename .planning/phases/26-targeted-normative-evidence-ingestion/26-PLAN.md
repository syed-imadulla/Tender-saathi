# Phase 26 Plan: Targeted Normative Evidence Ingestion

## Objectives
Ingest authoritative normative clause passages, parameter constraints, and scope texts for the selected high-frequency procurement standards (`IS 456 : 2000`, `IS 4984 : 2016`, `IS 1489 (Part 1) : 2015`, and supersedence links for `IS 8112 : 2013` -> `IS 269 : 2015`). Elevate these standards from metadata-only catalogue discovery to clause-grounded verified recommendations while keeping un-ingested catalogue candidates strictly flagged as `PENDING_TECHNICAL_EVALUATION`.

---

## Tasks

### Task 1: Ingestion Script & Data Preparation (`scripts/ingest_normative_standards.py`)
- Authoritative Data Ingestion:
  - Prepare authentic normative passages for:
    - `IS 456 : 2000`: Scope (Cl 1.1), Materials (Cl 5.1-5.6), Concrete Grades (Cl 6.1, Table 2: M15 to M80), Durability & Exposure (Cl 8.2, Table 3, Table 5: Min cement & max w/c ratio), Minimum reinforcement (Cl 26.5).
    - `IS 4984 : 2016`: Scope (Cl 1.1), Material Designation (Cl 4.1: PE 63, PE 80, PE 100), Pressure Ratings (Cl 4.2: PN 2.5 to PN 20), Dimensions & Tolerances (Cl 5.1, Table 1: DN 16 mm to DN 2000 mm), Hydrostatic Strength (Cl 7.1).
    - `IS 1489 (Part 1) : 2015`: Scope (Cl 1.1), Fly Ash Blending Ratio (Cl 5.2: 15% to 35%), Compressive Strength (Cl 7.2: Min 33 MPa at 28 days), Initial & Final Setting Times (Cl 7.3: Min 30 min, Max 600 min), Soundness (Cl 7.4).
    - `IS 8112 : 2013` -> `IS 269 : 2015`: Scope notes documenting withdrawal and consolidation into `IS 269 : 2015` (33, 43, and 53 grade OPC).
- Persistence:
  - Store documents and passages into `data/standards/corpus.db` using `CorpusStorage`.
  - Insert / update corresponding records into `data/standards/standards.db` (`standards` table) with official title, scope, year, technical committee, and `verification_status = 'VERIFIED'`.
  - Update `data/standards/relationships.json` with official normative relationships (e.g. `IS 8112 : 2013` `SUPERSEDED_BY` `IS 269 : 2015`).
- Ensure script is fully reproducible and idempotent.

### Task 2: Grounding & Recommendation Pipeline Integration
- In `src/recommend.py` and `src/corpus/retriever.py`:
  - When `ClauseRetriever` queries `IS 456 : 2000`, `IS 4984 : 2016`, or `IS 1489 (Part 1) : 2015`, it finds genuine clause-level passages in `CorpusStorage`.
  - Verify that `top_rec.clause_evidence` is populated with `is_grounded = True` and requirement evidence support state (`FULLY_SUPPORTED` or `PARTIALLY_SUPPORTED`).
  - Ensure `StandardsRecommender` recognizes ingested standards as having verified clause backing, giving them `confidence = "High"` and `applicability_decision = "APPLICABLE"` when tender requirements match their scope and parameters.
  - Safeguard: Catalogue-only candidates NOT in the ingested corpus remain strictly `PENDING_TECHNICAL_EVALUATION` with `human_review_required = True`.
  - Ensure `IS 8112 : 2013` triggers a supersedence alert directing the user to `IS 269 : 2015`.

### Task 3: Comprehensive Test Suite (`tests/test_targeted_normative_ingestion.py`)
- Test cases:
  1. `test_is456_clause_grounding`: Verify `IS 456 : 2000` recommendations produce verified clause passages (e.g. Clause 1.1, Clause 6.1, Table 2).
  2. `test_is4984_hdpe_parameter_support`: Verify `IS 4984 : 2016` verifies HDPE pipe pressure ratings (PN 10, PE 100) and nominal diameters with grounded clause evidence.
  3. `test_is1489_ppc_cement_clause_support`: Verify `IS 1489 (Part 1) : 2015` verifies fly ash PPC cement requirements with clause evidence.
  4. `test_is8112_supersedence_to_is269`: Verify citing withdrawn `IS 8112` emits an authoritative supersedence warning pointing to active `IS 269 : 2015`.
  5. `test_edition_mismatch_prevents_false_grounding`: Verify citing an obsolete edition (e.g. `IS 4984 : 1995`) does not falsely inherit 2016 clause passages without edition mismatch flagging.
  6. `test_non_ingested_catalogue_remains_pending_evaluation`: Verify un-ingested catalogue candidates (e.g. `IS 10000`, `IS 10245`) continue to be strictly flagged `PENDING_TECHNICAL_EVALUATION` with zero fabricated clause text.
  7. `test_safe_abstention_preserved`: Verify service and non-engineering tenders continue to abstain cleanly.
  8. `test_corpus_storage_provenance_and_licensing`: Verify licensing status and file hashes are recorded for every ingested document.

### Task 4: Full Suite Regression & Integrity Verification
- Run `pytest tests/test_targeted_normative_ingestion.py -v`.
- Run Phase 24 (`tests/test_national_catalogue_validation.py`) and Phase 25 (`tests/test_national_catalogue_retrieval.py`).
- Run the complete repository test suite (`pytest -q`).
- Verify `sha256sum dataset/ground_truth/ground_truth.csv` matches `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`.
- Run `graphify update .`.
- Update `.planning/STATE.md` and generate `26-UAT.md`.
