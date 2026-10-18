# Phase 25 UAT: National BIS Catalogue Metadata Retrieval

## Executive Verification Summary

Phase 25 successfully integrates the national BIS catalogue (`data/catalogue/bis_catalogue.db`) into natural-language tender retrieval. Tender Saathi can now discover relevant standards across all 10,828 active Indian Standards in the national catalogue, breaking out of the 90-standard boundary while enforcing strict evidence boundaries and safe abstention.

- **FTS5 Index Generated**: `data/catalogue/catalogue_search_index.db` (5.51 MB, builds in ~0.20s, indexes 10,828 active standards with `porter unicode61` stemming).
- **Search Engine**: `src/catalogue/search.py` (`NationalCatalogueSearchEngine`, sub-10ms latency, BM25 rank score normalization, query sanitization).
- **Two-Tier Cascade**: Curated 90 standards are queried first. If matches are weak or unrepresented in the curated pool, catalogue search cascades.
- **Evidence Safeguards**: Catalogue-discovered standards are strictly marked `PENDING_TECHNICAL_EVALUATION`, `human_review_required: True`, with `clause_evidence: None` (zero clause fabrication).
- **Safe Abstention**: Pure service/administrative and non-engineering tenders (audit, catering, cleaning, taxi hiring, software subscriptions) cleanly abstain.
- **Test Suite**: 708/708 tests pass (100% pass rate) across full test suite including 14 Phase 25 tests and 17 Phase 24 tests.
- **Ground Truth Checksum**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (strictly unaltered).
- **Frontend Build**: `npm run build` succeeds cleanly in 1.97s with zero errors or warnings.

---

## Acceptance Criteria Verification Matrix

| Acceptance Criterion | Verification Method | Status | Notes |
|:---|:---|:---|:---|
| 1. NL Discovery Beyond Curated 90 | `test_nl_discovery_marine_diesel_engine`, `test_nl_discovery_respiratory_devices`, `test_nl_discovery_medical_textiles` | PASSED | Retrieves `IS 10000`, `IS 10245`, and medical textile standards from national catalogue. |
| 2. Multi-Part & Edition Preservation | `test_multipart_standard_accuracy` | PASSED | Exact part numbers and edition years are maintained without truncating or corrupting identifiers. |
| 3. Curated Deduplication | `test_curated_deduplication_preserves_clause_rich_standard` | PASSED | When a standard exists in both datasets (e.g. `IS 1180`), the curated version with rich clause text is preserved. |
| 4. Active-Only Pool Safeguard | `test_active_only_discovery_pool` | PASSED | Only active standards are indexed into the proactive FTS5 discovery pool. |
| 5. Weak-Match Cascading | `test_two_tier_cascades_on_unrepresented_domain`, `test_two_tier_preserves_curated_on_high_confidence` | PASSED | High-confidence curated matches do not dilute; low-confidence/unrepresented domains trigger catalogue cascade. |
| 6. Safe Service Abstention | `test_pure_service_audit_clean_abstention`, `test_catering_service_clean_abstention` | PASSED | Non-engineering service tenders cleanly abstain with structured uncertainty. |
| 7. FTS5 Query Robustness | `test_malformed_fts_queries_do_not_crash` | PASSED | Unbalanced quotes, Boolean keywords, and punctuation do not cause SQLite syntax errors. |
| 8. Zero Clause Fabrication | `test_no_fabricated_clause_evidence_for_catalogue_discovery` | PASSED | Catalogue-discovered items have `clause_evidence=None` and decision `PENDING_TECHNICAL_EVALUATION`. |
| 9. Latency Benchmark | `test_catalogue_search_latency_under_10ms` | PASSED | Average lexical query time is ~0.4ms to 1.5ms, well under the 10ms budget. |
| 10. API & Frontend Compatibility | `test_api_text_analysis_with_catalogue_discovery` & `npm run build` | PASSED | API returns valid JSON with `NATIONAL_CATALOGUE_DISCOVERY`, frontend builds and displays `EvidenceDrawer` tags. |
| 11. Full Suite Non-Regression | `pytest -q` (708 passed) | PASSED | Zero regressions across all prior milestones and unit/integration suites. |
| 12. Ground Truth Integrity | `sha256sum dataset/ground_truth/ground_truth.csv` | PASSED | Unchanged: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`. |

---

## Domain Retrieval Evaluation Samples

| Domain / Query | Top Discovered Standard | Title | Status | Review Flag |
|:---|:---|:---|:---|:---|
| Marine propulsion diesel engine | `IS 10000 (Part 1) : 1980` | Methods of tests for internal combustion engines: Part 1 Glossary of terms | Active | Required (`PENDING_TECHNICAL_EVALUATION`) |
| Breathing apparatus for emergency rescue | `IS 10245 (Part 1) : 1996` | Respiratory protective devices: Part 1 Closed circuit breathing apparatus | Active | Required (`PENDING_TECHNICAL_EVALUATION`) |
| Medical surgical dressing textiles | `IS 17354 : 2020` | Medical textiles — Surgical drapes and gowns | Active | Required (`PENDING_TECHNICAL_EVALUATION`) |
| Statutory financial audit services | None (Abstention) | N/A | N/A | Clean abstention, no false positive |
| Catering & meal delivery services | None (Abstention) | N/A | N/A | Clean abstention, no false positive |
| Distribution transformer (Curated domain) | `IS 1180 (Part 1) : 2014` | Outdoor type oil immersed distribution transformers | Active | Full Clause Verification Preserved |
