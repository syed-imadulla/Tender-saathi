# Phase 28 Context: Interactive Multi-Package Audit UI & Verification Tier Drilldown

**Phase**: 28 — Interactive Multi-Package Audit UI & Verification Tier Drilldown  
**Dependencies**: Phase 27 (Multi-Package Tender Auditing & Heterogeneous Scope Verification)  
**Primary Goal**: Provide a government-officer-grade, production-quality frontend experience for reviewing multi-package tender audits, with package navigation, explicit verification-tier indicators, clause-level evidence inspection, complementary standards, and tender-wide uncovered dependencies.

---

## 1. Context & Available Backend Data

Phase 27 updated the backend engine and REST API (`/api/analyze/text`, `/api/analyze/tender`, `/api/analyze/pdf`, `/api/analyze/image`) to provide structured multi-package audit payloads.

### Confirmed Available API Fields:
On each requirement (`Requirement`):
- `package_id: string` (e.g., `"PKG-01"`, `"PKG-02"`, `"PKG-GEN"`)
- `package_name: string` (e.g., `"Civil Works"`, `"Transmission Mains"`, `"General Terms and Conditions"`)
- `domain: string` (e.g., `"CIVIL_AND_STRUCTURAL"`, `"PIPES_AND_FITTINGS"`, `"VALVES_AND_FLOW"`, `"ELECTRICAL_AND_POWER"`, `"PUMPS_AND_ROTATING"`, `"MECHANICAL_AND_MACHINERY"`, `"GENERAL_AND_ADMINISTRATIVE"`)
- `verification_tier: "CLAUSE_VERIFIED" | "CATALOGUE_DISCOVERED" | "SAFE_ABSTENTION"`
- `passage_id: string | null` (e.g. `"PS-IS456_cl5.1"`, SHA-256 slice, or document clause anchor)
- `clause_number: string | null` (e.g., `"5.1"`, `"4.1"`)
- `edition_year: string | null` (e.g., `"2000"`, `"2016"`)
- `clause_evidence: ClauseEvidenceData | null`
- `trace_record: TraceRecord | null`

On `summary` (`AnalysisSummary`):
- `clause_verified_count: number`
- `catalogue_discovered_count: number`
- `safe_abstention_count: number`
- `package_summaries: PackageSummary[]`:
  - `package_id: string`
  - `package_name: string`
  - `requirement_count: number`
  - `clause_verified_count: number`
  - `catalogue_discovered_count: number`
  - `safe_abstention_count: number`
  - `human_review_count: number`
  - `domains: string[]`
  - `standards: string[]`
- `domain_distribution: Record<string, number>`
- `complementary_standards: ComplementarySuite[]`:
  - `suite_id: string`
  - `suite_name: string`
  - `domain: string`
  - `primary_standard: string`
  - `allied_standards: string[]`
  - `packages_involved: string[]`
  - `status: string`
  - `description: string`
- `uncovered_tender_dependencies: UncoveredDependency[]`:
  - `primary_standard: string`
  - `missing_dependency: string`
  - `dependency_title: string`
  - `domain: string`
  - `severity: string`
  - `finding_type: string`
  - `message: string`

---

## 2. User & Engineering Requirements

1. **Package Navigation**:
   - Filter bar with tabs for "All Packages" and each detected package (`PKG-01: Civil Works`, `PKG-02: Water Supply`, `PKG-GEN: General Terms`).
   - Selected package banner displaying package metadata: title, primary domain badge, requirement count, verified/catalogue/abstained tier distribution.
   - Requirement filtering by selected package without altering tender-wide findings.
   - Single-package or no-package tenders render seamlessly without broken tab controls.

2. **Verification Tier Badges**:
   - `CLAUSE_VERIFIED` (Green): "Supporting local normative evidence is available for the identified standard and edition."
   - `CATALOGUE_DISCOVERED` (Amber/Blue): "Candidate discovered in catalogue metadata, but technical applicability has not been verified by local normative evidence. Pending technical evaluation."
   - `SAFE_ABSTENTION` (Neutral Slate): "Deliberately withheld recommendation (administrative, underspecified, or unsupported). Displays backend explanation."
   - Fallback for missing/unknown tier.
   - Accessible descriptions and clear distinction so catalogue discoveries are never confused with verified standards.

3. **Clause Evidence Drilldown**:
   - Expandable drawer or panel rendering exact passage ID, document ID, clause number, edition year, passage text, and support assessment.
   - Clear visual differentiation between clause-grounded excerpts and catalogue metadata scope notes.

4. **Tender-Wide Findings Sections**:
   - **Cross-Package Complementary Engineering Suites**: Visual cards/tables showing interrelated standards suites across packages, with explanatory notice that they require engineering review.
   - **Tender-Wide Uncovered Dependencies**: Dedicated warning callouts showing omitted companion standards across packages (e.g. `IS 456` without `IS 1786`).
   - **Administrative & Commercial Conditions**: Separate section or filtered tab for safely abstained clauses.

5. **Type Safety & Testing**:
   - Fully typed TypeScript definitions in `types.ts`.
   - Comprehensive test suite in `Results.test.ts` executed via `vitest run`.
   - Clean production build (`tsc && vite build`).
   - Bit-for-bit unchanged ground-truth dataset (`8bcc9bc5...`).
