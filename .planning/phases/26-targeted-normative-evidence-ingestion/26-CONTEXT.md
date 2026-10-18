# Phase 26 Context: Targeted Normative Evidence Ingestion

## Background & Objective
Phase 24 and Phase 25 expanded Tender Saathi from a 90-standard boundary to discovering standards across all 10,828 active standards in the national BIS catalogue (`data/catalogue/bis_catalogue.db`). However, standards discoverable solely through catalogue metadata are appropriately flagged `PENDING_TECHNICAL_EVALUATION` with `human_review_required = True` because their normative clause text is not yet indexed.

Phase 26 implements Phase 3 of `docs/evaluation/FULL_BIS_COVERAGE_GAP_ANALYSIS.md`: ingesting lawfully obtained, authoritative normative clause extracts and parameter tables for a high-value batch of high-frequency procurement standards, transitioning them from metadata-only candidates into clause-grounded, verified standards.

---

## Decisions & Scope Boundary

### 1. Selected Standards Batch
Based on procurement frequency, domain diversity, and authoritative BIS availability, the following standards are selected:
- **`IS 456 : 2000`** — *Plain and Reinforced Concrete - Code of Practice (Fourth Revision)*.
  - Domain: Civil / RCC Structures (Technical Committee: CED 2).
  - Lifecycle: Active (Reaffirmed 2021).
  - Scope: Design and construction of plain and reinforced concrete structures, materials (cement, aggregates, water, admixtures, rebar), characteristic compressive strength grades (M15 to M80), water-cement ratio, durability requirements, and minimum reinforcement.
- **`IS 4984 : 2016`** — *Polyethylene Pipes for Water Supply - Specification (Fifth Revision)*.
  - Domain: Plastic Piping / Municipal Water Supply (Technical Committee: CED 50).
  - Lifecycle: Active (Mandatory QCO under Ministry of Chemicals & Petrochemicals).
  - Scope: High density polyethylene (HDPE) pipes for municipal and industrial water supply, pressure ratings (PN 2.5 to PN 20), material grades (PE 63, PE 80, PE 100), nominal diameters (DN 16 mm to DN 2000 mm).
- **`IS 1489 (Part 1) : 2015`** — *Portland Pozzolana Cement - Specification: Part 1 Fly Ash Based (Fourth Revision)*.
  - Domain: Cement & Concrete Materials (Technical Committee: CED 2).
  - Lifecycle: Active (Mandatory BIS certification).
  - Scope: Manufacture, physical and chemical requirements of fly ash based Portland pozzolana cement (PPC), fly ash blending proportions (15% to 35%), 28-day compressive strength (minimum 33 MPa), setting times, and soundness.
- **`IS 8112 : 2013` & `IS 269 : 2015`** — *Ordinary Portland Cement (43 Grade & Consolidated Specification)*.
  - Domain: Cement & Binding Materials (Technical Committee: CED 2).
  - Lifecycle: `IS 8112 : 2013` is Withdrawn and consolidated into `IS 269 : 2015`.
  - Scope: Supersedence tracking and normative redirection.

### 2. Storage Strategy
- **`data/standards/corpus.db`**: Relational persistence for full document metadata (`corpus_documents`) and clause-level passages (`corpus_passages`) with exact clause identifiers (`1.1`, `4.1`, `5.1`, `Table 2`), content hashes, and licensing provenance (`PERMITTED_PUBLIC_GAZETTE` / `OFFICIAL_PRIMARY`).
- **`data/standards/standards.db`**: Synchronized record in the `standards` table containing official designation, title, scope summary, technical committee, lifecycle status, source URL, and verification status (`VERIFIED`).
- **`data/standards/relationships.json`**: Official normative relationships recorded between allied standards and supersedence links (e.g. `IS 8112 : 2013` -> `IS 269 : 2015`).

### 3. Safety & Verification Invariants
- **Zero Clause Fabrication**: Only authentic, verbatim clauses and parameter limits from official BIS gazettes, specifications, and public standards are stored.
- **Strict Edition & Part Matching**: Passages are indexed by exact standard number and edition year. Mismatched editions cannot falsely ground recommendations.
- **Strict Distinction for Non-Ingested Candidates**: Standards discoverable in the national catalogue that are not in the ingested corpus remain marked `PENDING_TECHNICAL_EVALUATION` with `human_review_required = True`.
- **Benchmark Ground Truth Immutability**: `dataset/ground_truth/ground_truth.csv` checksum (`8bcc9bc5...`) must remain untouched.
- **Safe Abstention**: Non-engineering and administrative service queries must continue to abstain cleanly.
