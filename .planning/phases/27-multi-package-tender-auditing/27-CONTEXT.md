# Phase 27 Context: Multi-Package Tender Auditing & Heterogeneous Scope Verification

## Background & Objective
Through Phases 24 to 26, Tender Saathi achieved two foundational milestones:
1. Universal discovery across 35,208 records in the National BIS Catalogue (Phase 24 & 25).
2. Targeted normative clause ingestion for high-frequency infrastructure standards (`IS 456`, `IS 4984`, `IS 1489 Part 1`, `IS 269` / `IS 8112`), establishing verifiable clause-level grounding (Phase 26).

However, real-world procurement tenders (e.g., water supply schemes, industrial plants, hospital campuses, substation construction) are rarely single-requirement queries. They are **multi-package tenders** containing heterogeneous engineering disciplines:
- Package 1 (Civil/Structural): Concrete structures, foundation rebar, cement mortar, structural steel framing.
- Package 2 (Piping & Mechanical): HDPE/DI transmission pipelines, sluice valves, check valves, pumps.
- Package 3 (Electrical & Automation): Substation HT/LT power cables, earthing grids, control panels, switchgear.
- Package 4 (Services & Administrative): Canteen operations, site security, facility maintenance.

**Phase 27 Objective**: Upgrade the end-to-end tender audit engine (`TenderAuditEngine`) and report generator (`TenderReviewReportGenerator`) to natively audit multi-package tenders with:
- Requirement-by-requirement clause-level traceability.
- Package-level and domain-level rollup (Civil, Piping, Electrical, Mechanical, General/Administrative).
- Strict separation between **Clause-Verified Recommendations**, **Catalogue-Discovered Standards** (`PENDING_TECHNICAL_EVALUATION`), and **Safe Abstentions**.
- Cross-package complementary standards recognition alongside cross-requirement conflict detection.
- Human-readable officer audit report in Markdown and structured JSON.

---

## Architectural Decisions & Scope Boundary

### 1. Multi-Package & Technical Domain Structure
Requirements will be tagged with a `package_id` / `package_name` and classified into standardized technical domains:
- `CIVIL_AND_STRUCTURAL`: Concrete, cement, rebar, structural steel, brickwork, masonry.
- `PIPES_AND_FITTINGS`: Polyethylene pipes, CPVC/UPVC, ductile iron, plumbing distribution.
- `VALVES_AND_FLOW`: Sluice/gate valves, globe/check valves, butterfly valves.
- `ELECTRICAL_AND_POWER`: Power/control cables, switchgear, transformers, earthing, substation.
- `PUMPS_AND_ROTATING`: Centrifugal, submersible, openwell pumps, motors.
- `GENERAL_AND_ADMINISTRATIVE`: Non-engineering administrative, catering, cleaning, security services (targeted for clean safe abstention).

### 2. Standards Verification Tiers (Conservation of Truth)
Every candidate standard identified across the tender must be assigned an immutable verification tier:
1. `CLAUSE_VERIFIED`:
   - Match supported by authentic normative clauses in `corpus.db`.
   - Exact edition and part matched.
   - Verified technical parameters (e.g. pressure rating PN, strength grade M25, fly ash %).
2. `CATALOGUE_DISCOVERED`:
   - Identified in national catalogue metadata (`bis_catalogue.db` / `catalogue_search_index.db`).
   - Local normative clauses not yet ingested.
   - Status strictly locked to `PENDING_TECHNICAL_EVALUATION` with `human_review_required = True`.
3. `SAFE_ABSTENTION`:
   - Requirement is administrative, commercial, out-of-catalogue, or lacks discriminating parameters.
   - Candidate standard is `None`, decision is `NO_RELIABLE_MATCH` or `AMBIGUOUS`.

### 3. Complementary Standards vs. Cross-Requirement Conflicts
- **Cross-Requirement Conflicts** (Phase 22): Contradictions in voltage rating, incompatible equipment standards, edition divergence.
- **Complementary Standards** (Phase 27): Recognize synergistic co-occurrence:
  - `IS 456` (concrete code) + `IS 1786` (rebar) + `IS 269`/`IS 1489` (cement) form a complete civil package.
  - `IS 4984` (HDPE pipe) + `IS 14846`/`IS 778` (valves) form a complete water conveyance package.
- **Omitted Critical Package Dependencies**: Alert when a primary package standard is specified without mandatory jointing/testing/installation dependencies across the entire tender.

### 4. End-to-End Requirement Traceability Model
Each audited requirement in `TenderAuditResult` and `StructuredTenderAuditReport` must expose:
- `requirement_id` and `package_id`
- `domain`
- `tender_text`
- `candidate_standard` & `evidence_standard`
- `verification_tier` (`CLAUSE_VERIFIED`, `CATALOGUE_DISCOVERED`, `SAFE_ABSTENTION`)
- `passage_id` and `clause_number` (when clause-verified)
- `edition_year`, `reaffirmation_year`, and `lifecycle_status`
- `decision` and `human_review_required`
- `traceability_status` (`GROUNDED`, `METADATA_ONLY`, `ABSTAINED`)

### 5. Invariants & Guardrails
- **Zero Hallucination**: Never invent clauses, passage IDs, or ratings.
- **Catalogue Integrity**: National catalogue remains 100% read-only.
- **Frozen Ground Truth**: `dataset/ground_truth/ground_truth.csv` SHA-256 (`8bcc9bc5...`) remains untouched.
- **Zero Regression**: All existing 717 unit and integration tests must pass.
