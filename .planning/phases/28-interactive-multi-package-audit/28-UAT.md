# Phase 28 — UAT & Verification Report
# Interactive Multi-Package Audit UI & Verification Tier Drilldown

**Phase ID:** 28  
**Status:** Completed & Verified  
**Date:** 2026-10-19  
**Execution Context:** Production Frontend Integration & Evidence-Review UX  

---

## 1. Implemented UI Features

### A. Multi-Package Navigation
1. **Package Selector Tab Bar (`Results.tsx`)**:
   - Dynamic tab per detected package: `All Packages (total count)` followed by individual package tabs (`PKG-01: Civil Works (count)`, `PKG-02: Transmission Mains (count)`, etc.).
   - General and commercial conditions package (`PKG-GEN`) cleanly identified with clipboard icon `📋` and distinct styling.
   - Accessible keyboard-friendly tablist navigation with `role="tab"` and `aria-selected`.
2. **Selected Package Summary Banner**:
   - Displays package name, primary technical domains, total requirement count, active standards count.
   - Dynamic verification-tier badge breakdown for the active package: Clause-Verified count (green), Catalogue-Discovered count (blue), and Safe Abstentions count (slate).
3. **Strict Requirement-Level Isolation**:
   - When a specific package is selected, requirement lists (`Indian Standards to Consider`, `Needs Your Attention`, `Standards That Need an Update`, and `Related Standards`) filter to requirements belonging to that package.
   - Tender-wide findings (Executive summary tier counts, Complementary engineering suites, Uncovered tender dependencies, and publication readiness) remain visible and invariant regardless of package tab selection.

### B. Explicit Verification Tier Indicators (`RequirementCard.tsx`)
1. **Tier Badges**:
   - `CLAUSE_VERIFIED`: Green badge (`.rec-badge--tier-verified`), checkmark dot, clear accessible tooltip: *"Supporting local normative evidence is available for the identified standard and edition."*
   - `CATALOGUE_DISCOVERED`: Blue/amber badge (`.rec-badge--tier-catalogue`), blue dot, clear accessible tooltip: *"A candidate was discovered in catalogue metadata, but technical evaluation remains pending. Not verified by local normative evidence."*
   - `SAFE_ABSTENTION`: Neutral slate badge (`.rec-badge--tier-abstain`), slate dot, clear accessible tooltip: *"Deliberately withheld because requirement is non-engineering or unsupported."*
   - Safe Fallback: Unknown or missing tiers render neutral unverified fallback; never infer verification status.
2. **Package & Domain Tags**:
   - `PackageDomainBadge` renders package tag (e.g. `📦 PKG-01`) and technical domain tag (e.g. `🏷️ Civil`) directly on recommendation, attention, and update cards.
3. **Safe Abstention Treatment**:
   - Administrative and commercial requirements with `SAFE_ABSTENTION` tier are rendered with a shield/neutral icon and explicitly titled *"Administrative or Commercial Scope — Safe Abstention"*, showing the backend's actual reason rather than treating it as a system error.

### C. Exact Clause Evidence Drilldown (`EvidenceDrawer.tsx`)
1. **Verification Tier & Package Provenance Banner**:
   - Top banner in drawer showing tier badge, package name, technical domain, and edition year.
   - Explains the exact grounding status of the requirement.
2. **Normative Clause Evidence Card**:
   - For `CLAUSE_VERIFIED`: Displays exact `clause_number` (or `clause_identifier`), `passage_id`, and `edition_year`.
   - Distinct from catalogue scope: Catalogue-discovered candidate cards display an explicit informational disclaimer stating that the quote is from the national BIS catalogue scope description and that local clause-level evidence is unindexed in the repository.
   - Safe abstentions explain why the recommendation was deliberately withheld.

### D. Dedicated Tender-Wide Findings Sections
1. **Executive Verification Tier Summary Bar**:
   - Tender-wide counts for Clause-Verified, Catalogue-Discovered, and Safe Abstentions with clear semantic definitions.
2. **Complementary Engineering Suites**:
   - Displays detected cross-discipline engineering suites (e.g., Water Supply, Electrical Transmission).
   - Lists primary trigger standard, allied standards, affected packages, and explicit advisory noting that these are potential cross-scope dependencies requiring engineering review.
3. **Uncovered Tender Dependencies**:
   - Displays identified dependencies between primary standards and allied codes of practice.
   - Shows affected package, primary standard, missing dependency, and advisory stating that the dependency is not automatically mandatory unless verified by returned tender specifications.
4. **Safely Abstained Administrative and Commercial Conditions**:
   - Explains the deliberate withholding of recommendations for non-engineering clauses (EMD, penalty terms, delivery timelines, etc.).

---

## 2. Files Created or Modified

| File | Change Summary |
|---|---|
| `frontend/src/types.ts` | Added `VerificationTier`, `PackageSummary`, `ComplementaryStandardSuite`, `UncoveredTenderDependency` interfaces; added Phase 28 fields to `Requirement` and `AnalysisSummary`. |
| `frontend/src/components/RequirementCard.tsx` | Added `VerificationTierBadge`, `PackageDomainBadge`; integrated tier badges and safe abstention handling into `RecommendationCard`, `AttentionCard`, and `UpdateCard`. |
| `frontend/src/components/RequirementCard.css` | Added styling for `.rec-badge--tier-verified`, `.rec-badge--tier-catalogue`, `.rec-badge--tier-abstain`, `.rec-badge--package`, `.rec-badge--domain`, and `.tier-dot`. |
| `frontend/src/components/EvidenceDrawer.tsx` | Added top Verification Tier & Package Banner; differentiated normative clause evidence (`clause_number`, `passage_id`, `edition_year`) from catalogue scope summaries. |
| `frontend/src/components/EvidenceDrawer.css` | Added `.drawer-tier-banner` styles for verified, catalogue, and abstention tiers. |
| `frontend/src/pages/Results.tsx` | Added package navigation state (`selectedPackage`), package summaries derivation, displayed requirements filtering, Executive Tier Summary bar, Complementary Suites card, Uncovered Dependencies card, and Safe Abstention section. |
| `frontend/src/pages/Results.css` | Added styles for `.package-nav-section`, `.package-tab`, `.package-summary-banner`, `.verification-tiers-bar`, `.tender-wide-card`, `.complementary-suite-item`, and `.uncovered-dep-item`. |
| `frontend/src/pages/Results.test.ts` | Added comprehensive Vitest tests verifying package filtering, tier badge mappings, safe abstentions handling, and catalogue non-fabrication. |
| `.planning/phases/28-interactive-multi-package-audit/28-CONTEXT.md` | Context specification document. |
| `.planning/phases/28-interactive-multi-package-audit/28-PLAN.md` | Execution plan document. |
| `.planning/phases/28-interactive-multi-package-audit/28-UAT.md` | Acceptance and verification report. |

---

## 3. Actual API Fields Consumed

The frontend consumes fields returned by the Phase 27 backend (`api/server.py` and `src/audit.py`):

- **Requirement-Level**:
  - `req.package_id`: Identifier for the tender package (e.g., `"PKG-01"`, `"PKG-GEN"`).
  - `req.package_name`: Human-readable package title (e.g., `"Civil Works"`, `"General / Commercial Conditions"`).
  - `req.domain`: Technical discipline (e.g., `"Civil"`, `"Piping"`, `"Electrical"`, `"Commercial"`).
  - `req.verification_tier`: Explicit tier: `"CLAUSE_VERIFIED"`, `"CATALOGUE_DISCOVERED"`, or `"SAFE_ABSTENTION"`.
  - `req.passage_id`: Exact corpus passage ID (e.g., `"IS_456_2000_SEC_5_CLAUSE_5_1"`).
  - `req.clause_number`: Normative clause number (e.g., `"5.1"`, `"4.2"`).
  - `req.edition_year`: Publication or revision edition year (e.g., `"2000"`, `"2018"`).
  - `req.clause_evidence`: Structured clause outcome, page number, document ID, and passage hash.
  - `req.why_flagged`: Explicit safe abstention or review reason.

- **Summary-Level (`result.summary`)**:
  - `summary.package_summaries`: Array of `PackageSummary` records with package name, domain, counts, and active standards.
  - `summary.clause_verified_count`: Total clause-verified count.
  - `summary.catalogue_discovered_count`: Total catalogue-discovered count.
  - `summary.safe_abstention_count`: Total safe abstention count.
  - `summary.complementary_standards`: Array of `ComplementaryStandardSuite` records with suite name, primary standard, allied standards, and involved packages.
  - `summary.uncovered_tender_dependencies`: Array of `UncoveredTenderDependency` records with primary standard, missing dependency, title, and advisory message.

---

## 4. Test Commands and Genuine Results

### Frontend Unit Tests (Vitest)
```bash
npx --prefix frontend vitest run src/pages/Results.test.ts
```
**Output:**
```text
 ✓ frontend/src/pages/Results.test.ts (8 tests) 8ms
   ✓ Results page recommendation filtering (AUDIT-02) (4)
     ✓ includes clear RECOMMEND items with human_review_required=false in recommendedList 2ms
     ✓ strictly excludes REVIEW_REQUIRED items from recommendedList and keeps them in attentionList 1ms
     ✓ excludes RECOMMEND_WITH_REVIEW items with human_review_required=true from pure recommendations 0ms
     ✓ excludes INSUFFICIENT_EVIDENCE and abstained candidate=null from recommendedList 0ms
   ✓ Phase 28 — Multi-Package Audit & Verification Tiers Filtering (4)
     ✓ filters requirements by package_id without mutating the full list 1ms
     ✓ correctly maps verification tiers across package requirements 1ms
     ✓ handles safe abstentions in attention requirements without treating them as system errors 0ms
     ✓ preserves catalogue-discovered candidate without implying clause-level verification 0ms

 Test Files  1 passed (1)
      Tests  8 passed (8)
   Duration  401ms
```

### Full Backend Pytest Suite
```bash
python3 -m pytest -q
```
**Output:**
```text
725 passed in 137.80s (0:02:17)
```
- Total test count: 725 passed (0 failed, 0 errors, 0 regressions).

### Frontend Production Build
```bash
npm --prefix frontend run build
```
**Output:**
```text
> tendersaathi-ui@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
✓ 620 modules transformed.
dist/index.html                   2.36 kB │ gzip:   0.98 kB
dist/assets/index-1G51X-l_.css   61.01 kB │ gzip:  11.14 kB
dist/assets/index-Yi7Bq5E0.js   352.97 kB │ gzip: 100.82 kB
✓ built in 1.71s
```
- TypeScript check passed with 0 errors.
- Vite production build finished with 0 warnings.

---

## 5. Ground Truth Dataset Integrity

The ground-truth dataset SHA-256 checksum was checked before and after implementation:
- **Baseline SHA-256:** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Post-Implementation SHA-256:** `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Result:** Exact match. Zero modifications or drift to ground truth labels.

---

## 6. Reproducible Verification Steps

To manually inspect and verify the Phase 28 UI:
1. Start the API server: `python3 -m api.server`
2. Start the frontend dev server: `npm --prefix frontend run dev`
3. Upload a multi-package tender file (or paste multi-package tender specifications).
4. On the Results page:
   - Verify the **Verification Tier Distribution** executive summary bar displays counts for Clause-Verified, Catalogue-Discovered, and Safe Abstentions.
   - Verify the **Package-Level Navigation** tab bar shows "All Packages" plus individual package tabs.
   - Click a package tab: verify requirement cards filter strictly to that package, showing the package domain and tier breakdown banner.
   - Verify the **Complementary Engineering Suites** and **Uncovered Tender Dependencies** sections remain visible at the bottom of the page across package tab switches.
   - Click "See why →" on a clause-verified card: verify the drawer displays the green tier banner, passage ID, clause reference, and edition year.
   - Click "See why →" on a catalogue-discovered card: verify the drawer displays the catalogue scope disclaimer without fabricating clause numbers.
   - Click "Audit Details →" on a safe abstention card: verify the drawer explains the deliberate abstention reason.

---

## 7. Remaining Limitations and Known Issues

1. **Unindexed BIS Standards**: When a recommended standard exists only in the national BIS catalogue (and not yet ingested into the local normative clause corpus), the frontend accurately identifies it as `CATALOGUE_DISCOVERED` with an informational disclaimer. Technical clause inspection for these standards requires future corpus expansion phases.
2. **Offline Local Cache**: The frontend displays official gazette / BIS provenance metadata from local database records; it does not perform live BIS portal authentication during user audit sessions.
