# Phase 22 Context: Multi-Requirement Systemic Conflict Resolution & Standards Precedence

## Phase Goal
Investigate and design a deterministic, evidence-backed mechanism for resolving conflicts that arise when multiple procurement requirements interact within a tender, or when multiple standards (general product codes, installation codes, safety rules, specialized application standards) appear applicable to the same procurement system.

## Key Audit Discoveries & Architectural Baseline

### 1. Existing System Isolation (Tender-Level Void)
- **Finding**: Currently, `StandardsRecommender.recommend_for_requirement()` operates in complete requirement isolation.
- In `recommend_for_pdf()`, requirements are processed sequentially as independent elements: `results = [self.recommend_for_requirement(r) for r in reqs]`.
- `TenderAuditEngine.audit_tender()` aggregates individual results into summary matrices, counting coverage states and flagging per-requirement gaps or ambiguities.
- **The Gap**: The system currently performs **zero cross-requirement conflict analysis**. If Requirement 1 demands a 100 kVA outdoor oil-immersed transformer (IS 1180) and Requirement 5 in the same tender specifies dry-type cast resin indoor for the same substation unit, both receive isolated recommendations with no cross-requirement inconsistency warning.

### 2. Standards Precedence Fallacy (Anti-Invention Boundary)
- **Principle**: We must **NEVER invent artificial precedence rules** (e.g. arbitrarily declaring "specialized always beats general" or "higher number wins").
- In Indian procurement law (CPWD, MES, Railway, BIS, General Financial Rules 2017):
  - An application code (e.g., IS 14665 for Lifts) does not invalidate a product code (e.g., IS/IEC 60947 for Breakers); they are **co-applicable complementary standards**.
  - A statutory regulation (QCO, Central Electricity Authority regulations) has legal primacy over voluntary standards.
  - An explicit tender specification can be more stringent than a BIS standard, provided it does not violate statutory safety or mandatory QCO orders.
  - Where precedence between two applicable standards is genuinely ambiguous or unaddressed by published clauses, the system **must preserve uncertainty and escalate to expert review**, rather than guessing.

### 3. Seven Conflict Categories to Address Deterministically
1. **Shared-System Contradiction**: Incompatible parameter ratings on the same equipment tag or installation unit.
2. **Requirement Dependency Mismatch**: Requirement A specifies equipment; Requirement B specifies an auxiliary component with incompatible ratings.
3. **Cross-Standard Co-Applicability**: Multiple standards governing different facets (e.g. Product specification + Installation code of practice + Routine test method).
4. **Normative Precedence Question**: Potential conflict between standard clauses where priority is unspecified by source provenance -> routes to `UNRESOLVED_NORMATIVE_PRECEDENCE`.
5. **Edition Divergence Across Tender**: One requirement citing an obsolete 1979 edition while another cites the active 2014 edition for the same equipment scope.
6. **Evidence Insufficiency**: Inability to confirm whether a conflict exists due to missing clause-level passage text.
7. **False Conflicts (Disjoint Scopes)**: Differing requirements that govern different operating zones (outdoor switchyard vs indoor control room) must be recognized as non-conflicting.

### 4. Ground-Truth Invariance
- `dataset/ground_truth/ground_truth.csv` SHA-256 (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`) must remain strictly immutable.
