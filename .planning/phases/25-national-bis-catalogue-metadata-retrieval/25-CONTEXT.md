# Phase 25 Context: National BIS Catalogue Metadata Retrieval

## Background & Intent
Phase 25 is Phase 2 of the BIS Coverage Gap Analysis roadmap (`docs/evaluation/FULL_BIS_COVERAGE_GAP_ANALYSIS.md`).
In Phase 24, explicit citation validation was connected to `data/catalogue/bis_catalogue.db` (35,208 records), eliminating false `NONEXISTENT_CITATION` alerts. However, when a tender does *not* explicitly cite a standard number and only provides natural-language requirements (e.g. "supply of diesel generating set", "textile fabric for hospital uniforms", "fire fighting equipment"), retrieval was strictly confined to the 90 curated standards in `data/standards/standards.db`.

This phase enables natural-language tender requirements to discover relevant standards across the national BIS catalogue via deterministic, lexical search over official metadata.

## Locked Architectural Decisions (User Aligned)
1. **Candidate Discovery Pool:**
   - Index all **10,828 ACTIVE** standards in `data/catalogue/bis_catalogue.db` as the primary discovery pool.
   - Withdrawn and superseded records remain available for explicit citation lookup and lifecycle validation, but are filtered out of proactive natural-language recommendation candidate sets.

2. **Index Technology:**
   - Build a dedicated, read-only SQLite database containing an FTS5 virtual table: `data/catalogue/catalogue_search_index.db`.
   - SQLite FTS5 is natively supported in Python's sqlite3 on Linux, provides deterministic BM25 ranking, sub-5ms query times, requires zero heavy external runtime dependencies, and avoids loading 10,000+ records into Python heap memory.
   - Built via reproducible script: `scripts/build_catalogue_search_index.py`.
   - Compounds indexed fields: `standard_number`, `title`, `technical_committee`, `department`, `iso_equivalence`.

3. **Retrieval Integration Strategy (Two-Tier Cascading Hybrid Search):**
   - **Tier 1 (Curated High-Precision First):** When a tender requirement is processed, `HybridRetrievalEngine` searches the curated 90 standards (using lexical + dense semantic embeddings + clause-level verification).
   - If Tier 1 finds strong, applicable matches (top candidate score >= 0.65 with domain match), curated results take precedence.
   - **Tier 2 (Catalogue Fallback & Augmentation):** If Tier 1 returns weak matches (< 0.65), zero candidates, or a domain mismatch, the pipeline cascades to the national catalogue lexical FTS5 index.
   - Merging & Deduplication: If a standard discovered in the catalogue also exists in curated standards, canonical deduplication resolves to the curated record (preserving clause text and full verification).

4. **Safety & Evidence Safeguards:**
   - Catalogue-only candidates have NO full clause text or normative parameter data.
   - Catalogue-only candidates are strictly labeled `verification_status="CATALOGUE_VERIFIED"`, `applicability={"decision": "PENDING_TECHNICAL_EVALUATION"}`, `human_review_required=True`, and `clause_evidence=None`.
   - Never fabricate scope, clause passages, or compliance parameters.
   - Negative control / pure service queries (e.g. "software consulting services", "annual catering service") must cleanly abstain or return below the candidate acceptance threshold.

5. **Invariants:**
   - The frozen ground-truth dataset (`dataset/ground_truth/ground_truth.csv`) SHA-256 (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`) must remain completely untouched and verified bit-for-bit.
   - Existing curated standard tests, ranking weights, and applicability decisions must remain intact.
