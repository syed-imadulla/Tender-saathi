# Phase 28 Execution Plan: Interactive Multi-Package Audit UI & Verification Tier Drilldown

**Phase**: 28 — Interactive Multi-Package Audit UI & Verification Tier Drilldown  
**Dependencies**: Phase 27 (Multi-Package Tender Auditing & Heterogeneous Scope Verification)  
**Primary Goal**: Build an interactive, government-officer-grade frontend UI for reviewing multi-package tender audits with package filtering, explicit verification-tier badges, clause evidence drilldown, complementary standards suites, and tender-wide uncovered dependencies.

---

## Task Breakdown

### Task 1: TypeScript Types & Schema Alignment
- **Target File**: `frontend/src/types.ts`
- **Scope**:
  - Add `PackageSummary`, `ComplementaryStandardSuite`, and `UncoveredTenderDependency` interfaces.
  - Extend `Requirement` interface with `package_id`, `package_name`, `domain`, `verification_tier`, `passage_id`, `clause_number`, and `edition_year`.
  - Extend `AnalysisSummary` interface with `clause_verified_count`, `catalogue_discovered_count`, `safe_abstention_count`, `package_summaries`, `domain_distribution`, `complementary_standards`, and `uncovered_tender_dependencies`.
  - Export type guards and tier enum helper types.

### Task 2: Verification Tier Badges Component
- **Target File**: `frontend/src/components/RequirementCard.tsx`, `frontend/src/components/RequirementCard.css`
- **Scope**:
  - Create `VerificationTierBadge` component with accessible tooltips/descriptions:
    - `CLAUSE_VERIFIED` (Green): Clause verified with authentic indexed passage.
    - `CATALOGUE_DISCOVERED` (Amber/Blue): Discovered in national catalogue; pending technical evaluation.
    - `SAFE_ABSTENTION` (Slate): Intentionally abstained without candidate standard.
    - Safe fallback for unknown/missing tier.
  - Integrate `VerificationTierBadge` into `RecommendationCard`, `AttentionCard`, and `UpdateCard`.
  - Display package ID/name tag (`PKG-01: Civil Works`) and domain tag on cards.

### Task 3: Multi-Package Navigation & Filtering in Results Page
- **Target File**: `frontend/src/pages/Results.tsx`, `frontend/src/pages/Results.css`
- **Scope**:
  - Add Package Selector tabs (`All Packages (N)`, `Package 1: Civil Works (M)`, etc.).
  - Display Package Context Banner when a specific package is selected (showing package name, domains, requirement count, verified vs catalogue vs abstained distribution).
  - Implement requirement filtering by package without mutating or hiding tender-wide summary metrics.
  - Support single-package and multi-package tenders gracefully.

### Task 4: Tender-Wide Findings Sections
- **Target File**: `frontend/src/pages/Results.tsx`, `frontend/src/pages/Results.css`
- **Scope**:
  - **Complementary Engineering Suites Card**: Render detected suites (`SUITE-CIVIL-CONCRETE`, `SUITE-WATER-PIPING`, `SUITE-ELECTRICAL-POWER`) showing primary standard, allied companion standards, packages involved, and non-mandatory engineering review notice.
  - **Uncovered Tender Dependencies Card**: Render callout for tender-wide omitted companion standards (e.g. `IS 456` without `IS 1786`), displaying affected packages and recommended review actions.
  - **Administrative & Commercial Conditions Card**: Dedicated section or filtered sub-view displaying safely abstained administrative items with backend rationale.

### Task 5: Clause-Level Evidence Inspection Drilldown
- **Target File**: `frontend/src/components/EvidenceDrawer.tsx`, `frontend/src/components/EvidenceDrawer.css`
- **Scope**:
  - Enhance `EvidenceDrawer` with a dedicated "Verification & Traceability Tier" banner:
    - For `CLAUSE_VERIFIED`: Render exact passage ID, document ID, clause number, edition year, passage excerpt, and support status.
    - For `CATALOGUE_DISCOVERED`: Clearly communicate that candidate is discovered from official catalogue metadata and has unindexed clause text pending technical evaluation. Never confuse catalogue scope description with a normative clause.
    - For `SAFE_ABSTENTION`: Clearly explain that recommendation was deliberately withheld for administrative/out-of-scope reasons.

### Task 6: Unit Testing & Verification
- **Target File**: `frontend/src/pages/Results.test.ts`
- **Scope**:
  - Test package filtering logic (preserves tender-wide findings while filtering requirements).
  - Test verification tier badge assignments and fallbacks.
  - Test complementary standards and uncovered dependencies rendering helpers.
  - Test safe abstention detection and presentation.
  - Verify `vitest run`, full backend `pytest -q` (725 tests), and `npm run build`.

---

## Acceptance Criteria
1. Multi-package tenders render a clear package navigation bar with "All Packages" and individual package tabs.
2. Requirement cards display accurate `verification_tier` badges (`CLAUSE_VERIFIED`, `CATALOGUE_DISCOVERED`, `SAFE_ABSTENTION`).
3. Clause evidence drilldown displays exact passage ID, document ID, clause number, and edition year.
4. Catalogue discoveries are never presented as clause-verified.
5. Complementary engineering suites and uncovered dependencies render prominently.
6. Safe abstentions display backend explanations clearly.
7. Frontend tests pass via `vitest run`.
8. Backend tests pass (725/725 tests, 0 regressions).
9. Frontend production build passes (`tsc && vite build`).
10. Ground-truth dataset SHA-256 (`8bcc9bc5...`) remains unchanged.
