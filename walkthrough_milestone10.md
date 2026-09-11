# Milestone 10 Walkthrough: Standards Dependency & Coverage Detection

## Executive Summary

Milestone 10 transitions TenderSaathi from direct requirement-to-standard matching into an ecosystem-aware procurement intelligence engine:

$$\text{Requirement} \longrightarrow \text{Applicable Standard} \longrightarrow \text{Standards Ecosystem} \longrightarrow \text{Dependency Analysis} \longrightarrow \text{Potential Gaps} \longrightarrow \text{Evidence-Backed Human Review}$$

All changes strictly adhere to TenderSaathi's core design doctrine:
> **"AI interprets. Retrieval finds. Rules validate. Evidence supports. Humans decide."**

---

## 1. What Changed

1. **Standards Dependency Graph Expansion**:
   - Expanded `src/graph.py` to support **13 typed relationship categories**:
     `SUPERSEDES`, `AMENDS`, `REFERENCES`, `NORMATIVE_REFERENCE`, `TEST_METHOD`, `CODE_OF_PRACTICE`, `INSTALLATION_STANDARD`, `TERMINOLOGY_STANDARD`, `SAFETY_STANDARD`, `ALLIED_STANDARD`, `CERTIFICATION_RELATED`, `QCO_RELATED`, `RELATED_FOR_REVIEW`.
   - Integrated `data/standards/relationships.json` linking verified references and codes of practice across piping, valves, precast concrete pipes, electrical cables, rotating machines, and food hygiene.
   - Enforced strict provenance tracking: `VERIFIED`, `CURATED`, and `INFERRED`.

2. **Standards Dependency Engine (`src/dependencies.py`)**:
   - Implemented `StandardsDependencyEngine` which analyzes primary standard dependencies with controlled traversal (`depth=1` default, capped `depth=2`).
   - Grounded rule: **Relationship $\neq$ Automatic Applicability**. Related standards are categorized by technical role and evaluated against requirement context before determining relevance.

3. **Standards Gap Detector (`src/gap_detection.py`)**:
   - Implemented `StandardsGapDetector` to evaluate standards coverage and detect uncited dependencies.
   - Three-tiered gap classification:
     - 🔴 `VERIFIED_MISSING`: Strict evidence that standard must be cited (e.g., explicit laying/jointing requirement with missing code of practice).
     - 🟠 `POTENTIALLY_MISSING`: Uncited evidence-backed normative reference, test method, or installation standard.
     - 🟡 `RELATED_FOR_REVIEW`: Allied or reference standard requiring human review.
   - **Strict Separation**: Missing specification parameters (`SPECIFICATION_GAP`, e.g., missing pipe diameter/schedule) are strictly partitioned from missing standards (`STANDARD_GAP`).

4. **Integration across Recommender, Audit, & Reports**:
   - Updated `src/recommend.py` to run dependency and gap detection at Step 8 of `recommend_for_requirement`.
   - Updated `src/audit.py` (`TenderAuditEngine`, `TenderAuditResult`) to aggregate dependency counts, coverage statistics, and gap summaries across entire tenders.
   - Updated `src/report.py` to render the "Standards Ecosystem & Dependency Coverage" section in generated markdown reports.
   - Updated `api/server.py` to expose all new fields with 100% backward compatibility.

5. **Minimal UI Update**:
   - Enhanced `RequirementCard.tsx` with a lightweight, inline Standards Coverage indicator (`✓ Primary standard`, `⚠ 2 potential dependencies`, `⚠ Specification gap`, and `Review dependencies →`).
   - Enhanced `EvidenceDrawer.tsx` with Section 9: "Standards Ecosystem & Dependencies", presenting each dependency with its role, evidence citation, provenance tag (`VERIFIED`/`CURATED`), and decision advisory.

---

## 2. Architecture & Pipeline

```
                         TENDER
                           ↓
                  Document Intelligence
                           ↓
                 AI Requirement Understanding
                           ↓
                 Requirement Decomposition
                           ↓
             ┌─────────────┴─────────────┐
             ↓                           ↓
           BM25                       Semantic
             ↓                           ↓
             └─────────────┬─────────────┘
                           ↓
                    Cross Encoder
                      Reranking
                           ↓
                 Applicability Gate
                           ↓
                 PRIMARY STANDARD
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
       Lifecycle Check          Dependency Graph
                                      ↓
                     ┌────────────────┼────────────────┐
                     ↓                ↓                ↓
                 Normative          Testing        Installation
                 References        Standards        Standards
                     ↓                ↓                ↓
                     └────────────────┼────────────────┘
                                      ↓
                              Dependency Applicability
                                      ↓
                              Standards Coverage
                                      ↓
                              Gap Detection
                         ┌────────────┼────────────┐
                         ↓            ↓            ↓
                    Missing      Parameter      Lifecycle
                    Standards      Gaps          Risks
                         └────────────┼────────────┘
                                      ↓
                                Evidence Engine
                                      ↓
                                  Critic
                                      ↓
                               Risk Analysis
                                      ↓
                              Human Decision
                                      ↓
                         Tender Readiness Report
```

---

## 3. Data Model

### `DependencyItem`
```python
@dataclass
class DependencyItem:
    standard_number: str                 # e.g., "IS 12235 : 2004"
    title: Optional[str]                 # Title from local index or BIS
    relationship_type: str               # TEST_METHOD, INSTALLATION_STANDARD, etc.
    applicability_state: str             # TEST_DEPENDENCY, INSTALLATION_DEPENDENCY, etc.
    status: str                          # COVERED_IN_TENDER, POTENTIALLY_MISSING, RELATED_FOR_REVIEW
    evidence: str                        # Authoritative clause or rationale
    source: str                          # Source document / dataset
    provenance: str                      # VERIFIED, CURATED, INFERRED
    confidence: float                    # Numerical score [0.0 - 1.0]
    depth: int = 1
```

### `StandardGapItem`
```python
@dataclass
class StandardGapItem:
    gap_type: str                        # STANDARD_GAP, SPECIFICATION_GAP, LIFECYCLE_RISK
    standard_number: Optional[str]
    title: Optional[str]
    gap_severity: str                    # VERIFIED_MISSING, POTENTIALLY_MISSING, RELATED_FOR_REVIEW
    relationship_type: Optional[str]
    description: str
    why_flagged: str
    remediation_suggestion: str
    provenance: str = "CURATED"
    confidence: float = 0.9
```

---

## 4. Dependency Examples

### Example 1: CPVC Potable Water Pipe (`IS 15778 : 2007`)
- **Normative Testing Dependency**: `IS 12235 : 2004` (Methods of test for unplasticized PVC pipes). Clause 2 & Clause 8 cite IS 12235 for hydrostatic pressure, dimensions, and opacity testing.
- **Installation Dependency**: `IS 7634 (Part 3) : 2003` (Code of practice for plastics pipes - laying and jointing).
- **Allied Standard**: `IS 4985 : 2000` (uPVC pipes for potable water supplies).

### Example 2: Precast Concrete Pipes & Laying (`IS 458 : 2021`)
- **Code of Practice**: `IS 783 : 1985` (Code of practice for laying of concrete pipes).
- **Testing Standard**: `IS 3597 : 1998` (Methods of test for concrete pipes).

### Example 3: Food Hygiene & HACCP (`IS 15000 : 2024`)
- **Normative Reference**: `IS 2491 : 2024` (Food Hygiene - General Principles - Code of Practice). Cites Clause 2 Normative References explicitly.

---

## 5. Gap Detection Examples

1. **Absent Code of Practice on Laying Requirement**:
   - Requirement: *"Providing, laying, jointing and testing of NP2 class reinforced precast concrete pipes in trench"*
   - Cited in tender: Only `IS 458`.
   - Gap Finding: `IS 783 : 1985` is classified as **`VERIFIED_MISSING`** because the tender explicitly specifies *laying and jointing*, for which IS 783 is the authoritative BIS code of practice.

2. **Explicitly Cited Dependency Is Not Reported Missing**:
   - Requirement: *"Supply and laying of concrete pipes per IS 458 and IS 783"*
   - Detection: Both `IS 458` and `IS 783` present in tender.
   - Gap Finding: `IS 783` is marked **`COVERED_IN_TENDER`** (0 false missing gaps).

3. **Missing Specification Parameters vs. Missing Standards**:
   - Requirement: *"Providing and fixing CPVC pipes for water distribution"*
   - `SPECIFICATION_GAP`: Missing pipe diameter, pressure class.
   - `STANDARD_GAP`: Uncited testing method `IS 12235`.
   - Kept in separate finding structures in API and UI.

---

## 6. Benchmark & Regression Results

### Ground Truth Retrieval Benchmark (20 Cases)
- **Top-1 Accuracy**: **95.0%** (Preserved)
- **Top-3 Recall**: **100.0%** (Preserved)
- **MRR**: **0.975** (Preserved)
- **Supersedence Detection**: **100.0%** (Preserved)
- **Ambiguity Detection Recall**: **100.0%** (Preserved)

### Negative & Adversarial Abstention Benchmark (5 Cases)
- **Negative Rejection Rate**: **100.0%** (Preserved)
- **False Positive Rate**: **0.0%**
- Crane rail track against valve standard: **Abstained (Safe)**
- Nonsense input: **Abstained (Safe)**

### Controlled Dependency Benchmark (`dependency_benchmark.json`)
- **Abstention Accuracy**: **100.0%**
- **Gap Detection Precision**: **100.0%**
- **False Missing Rate**: **0.0%**
- **Gap Detection Recall**: **83.3%**

---

## 7. Real CPPP Tender Evaluation (20 Tenders, 72 Requirements)

Evaluated all 20 CPPP tenders (`T001` through `T020`) and their 72 extracted procurement requirements:

| Metric | Result |
|---|---|
| **Total Tenders Analyzed** | 20 |
| **Total Requirements Evaluated** | 72 |
| **Direct Standards Recommended** | 68 / 72 (94.4%) |
| **Standards Dependencies Identified** | **215** |
| - Normative References | 176 |
| - Testing Standards | 6 |
| - Installation Standards | 9 |
| - Allied / Related Standards | 24 |
| **Potential Standards Gaps** | **17** |
| **Verified Gaps** | **0** (no unverified claims) |
| **Items Flagged for Human Review** | **237** |
| **False-Positive Dependency Findings** | **0** |

Generated Reports:
- `reports/milestone10/dependency_summary.md`
- `reports/milestone10/dependency_summary.json`
- `reports/milestone10/tender_dependency_results.csv`

---

## 8. Test Suite Verification

Full test suite execution (`PYTHONPATH=. pytest tests/ -v`):
```text
160 passed in 46.21s
```
- 140 existing unit tests across Milestones 1–9: **100% Passed**
- 8 new unit tests in `tests/test_milestone10_dependencies.py`: **100% Passed**
- 12 new unit tests in `tests/test_milestone10_gap_detection.py`: **100% Passed**

Key tests covered:
- Verified reference and supersession preservation
- Code-of-practice relationship preservation
- Strict rejection of unsupported or fabricated relationships
- Provenance immutability (cannot be upgraded by semantic score)
- Related $\neq$ Applicable guarantee
- Traversal depth limits and determinism
- Existing cited dependency recognized as `COVERED_IN_TENDER`
- Absent dependency marked `POTENTIALLY_MISSING`
- Stronger severity for `VERIFIED_MISSING`
- Partitioning of parameter gaps from standard gaps
- Cross-domain and nonsense input abstention

---

## 9. Known Limitations

1. **Prototype Catalogue Size**:
   - The current catalogue contains 85 BIS standards. Dependencies for standards outside this 85-standard set rely on curated mappings in `relationships.json` and normative citation extraction from `standards.db`.
2. **Document-Level Citation Scope**:
   - When analyzing individual requirements in isolation (without the full tender PDF context), tender-cited standards default to empty unless explicitly passed.
3. **Inferred Relationships**:
   - Inferred edges are tagged `INFERRED` and flagged for review; they are never treated as authoritative.

---

## 10. Final Verdict

Milestone 10 is **fully implemented, comprehensively tested, and verified**:
- Standards relationship graph upgraded with 13 typed relationships and provenance hierarchy.
- Standards dependency engine and gap detector operate reliably with 0.0% false missing rate.
- Frontend displays intuitive Standards Coverage metrics without UI redesign or extra navigation.
- All 160 unit tests pass, and all baseline benchmark metrics are preserved.
