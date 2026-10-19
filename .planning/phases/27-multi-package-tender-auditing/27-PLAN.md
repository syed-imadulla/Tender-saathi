# Phase 27 Execution Plan: Multi-Package Tender Auditing & Heterogeneous Scope Verification

**Phase**: 27 — Multi-Package Tender Auditing & Heterogeneous Scope Verification  
**Dependencies**: Phase 24 (National BIS Catalogue), Phase 25 (Catalogue Metadata Retrieval), Phase 26 (Targeted Normative Ingestion)  
**Primary Goal**: Equip Tender Saathi with robust, end-to-end multi-package tender auditing that groups requirements by engineering domain, distinguishes clause-grounded recommendations from catalogue-only discoveries, identifies cross-package complementary standards, and outputs officer-ready audit reports.

---

## Task Breakdown

### Task 1: Package & Technical Domain Classification in Intake / Extraction
- **Files**: `src/extract.py`, `src/intake.py`
- **Scope**:
  - Add package parsing to detect package/lot delimiters in tender text (`Package 1:`, `Lot A:`, `Part I:`, or multi-line item blocks).
  - Add standardized domain tagging: `CIVIL_AND_STRUCTURAL`, `PIPES_AND_FITTINGS`, `VALVES_AND_FLOW`, `ELECTRICAL_AND_POWER`, `PUMPS_AND_ROTATING`, `GENERAL_AND_ADMINISTRATIVE`.
  - Add `package_id` and `domain` attributes to `Requirement` data model with non-breaking defaults.

### Task 2: Standards Verification Tier & Traceability Enrichment
- **Files**: `src/recommend.py`, `src/traceability.py`
- **Scope**:
  - Assign explicit `verification_tier`:
    - `CLAUSE_VERIFIED`: Candidate matched and grounded by authentic normative passage in `corpus.db`.
    - `CATALOGUE_DISCOVERED`: Candidate found via national catalogue metadata, pending local clause extraction.
    - `SAFE_ABSTENTION`: Requirement abstained (commercial/administrative, incomplete, or out of scope).
  - Surface exact `passage_id`, `clause_number`, and `edition_year` on `RequirementRecommendationResult`.

### Task 3: Multi-Package & Complementary Standards Auditing in `TenderAuditEngine`
- **Files**: `src/audit.py`
- **Scope**:
  - Add package-level grouping and domain distribution (`package_summaries`).
  - Calculate distinct verification metrics: `clause_verified_count`, `catalogue_discovered_count`, `safe_abstention_count`.
  - Implement complementary standards recognition: correlate allied and co-occurring standards across requirements in the same tender (e.g., Civil package RCC `IS 456` + rebar `IS 1786` + cement `IS 269`/`IS 1489`; Water package HDPE `IS 4984` + valves `IS 14846`/`IS 778`).
  - Detect tender-wide unaddressed normative dependencies (mandatory testing or installation standards omitted across all tender packages).
  - Update `TenderAuditResult` and `StructuredTenderAuditReport` schemas with package intelligence.

### Task 4: Dynamic Multi-Package Markdown & JSON Audit Report Generation
- **Files**: `src/report.py`
- **Scope**:
  - Update `TenderReviewReport` and `to_markdown()` to render:
    1. Package & Technical Domain Breakdown table.
    2. Verification Tiers summary (Clause-Verified vs Catalogue-Discovered vs Safe Abstentions).
    3. Complementary Standards & Cross-Package Synergy section.
    4. Detailed Requirement Review grouped by Package/Domain with exact passage IDs and clause references.

### Task 5: API Multi-Package / Multi-Requirement Ingestion Support
- **Files**: `api/server.py`
- **Scope**:
  - Enhance `/api/analyze/text` to support multi-line / multi-requirement tender text blocks.
  - Add support for structured `packages` or `requirements` lists in `/api/analyze/text` and `/api/analyze/tender`.

### Task 6: Deterministic Verification Suite & Regression Testing
- **Files**: `tests/test_multi_package_tender_auditing.py`
- **Scope**:
  - Multi-package tender fixture with Civil, Piping, Electrical, and Administrative packages.
  - Verification tier separation (Clause-Verified vs Catalogue-Discovered vs Abstained).
  - Complementary standards co-occurrence and dependency gap detection.
  - Requirement-to-evidence passage and clause-level traceability.
  - Withdrawn standard citation with successor replacement in a multi-package context.
  - Markdown and JSON report rendering validation.
  - Zero regressions across the full 717-test backend suite.
  - Clean frontend production build.

---

## Acceptance Criteria
1. Multi-package tender audits cleanly segment and summarize requirements across packages and engineering domains.
2. Reports clearly distinguish clause-verified standards from national catalogue metadata discoveries.
3. Complementary standards sets (e.g. concrete + rebar + cement) are recognized and reported.
4. Passage ID and clause number are traceable for all clause-verified recommendations.
5. All newly added deterministic tests pass 100%.
6. Full test suite passes with 0 regressions.
7. Ground-truth dataset hash (`8bcc9bc5...`) remains unchanged.
