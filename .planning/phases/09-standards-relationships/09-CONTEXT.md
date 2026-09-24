# Phase 9: Standards Relationship & Regulatory Intelligence
## Architecture Context & Strategic Decision Contract

**Phase ID**: `09-standards-relationships`  
**Parent Initiative**: Smart India Hackathon (SIH) Problem Statement 26108  
**Theme**: Standards Relationship, Allied Ecosystem Mapping & Regulatory Intelligence  
**Baseline Commit**: `2bdaa79` (`feat(phase8): complete decision safety, trust boundary hardening, and audit report`)  

---

## 1. Problem Statement Mandate (SIH26108)

The official problem statement for SIH26108 is:
> *“AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications.”*

The problem statement explicitly mandates that the solution must not merely produce a single isolated standard code, but must provide comprehensive, multi-dimensional intelligence across the Indian Standards ecosystem:

1. **Recommending applicable Indian Standards** for general and complex engineering procurement.
2. **Identifying allied standards** that complement the primary standard.
3. **Extracting normative references** cited within the standard clauses.
4. **Distinguishing test methods and sampling standards** required for quality assurance and verification.
5. **Identifying terminology, symbols, and glossary standards** defining technical specifications.
6. **Identifying safety standards and codes** governing hazard mitigation and fire safety.
7. **Identifying installation standards and codes of practice** governing execution, laying, and erection.
8. **Mapping related product standards** that operate in the same engineering system or assembly.
9. **Tracking latest published versions, currency, and amendments** to prevent citing obsolete standards.
10. **Surfacing applicable certification requirements** (BIS Product Certification / ISI Mark, QCOs, CRS).
11. **Handling multilingual input** across Indian regional languages and transliterated procurement text.
12. **Operating via semantic understanding** of engineering concepts rather than naive keyword matching.

### Architectural Evolution

Phases 1 through 8 hardened the core recommendation engine:
$$\text{Requirement} \longrightarrow \text{Applicable Indian Standard (Primary)}$$

Phase 9 completes the mandate by systematically expanding this mapping into a rich, evidence-grounded standards ecosystem:
$$\begin{aligned}
\text{Requirement} \longrightarrow & \textbf{Primary Indian Standard} \\
& \longrightarrow \textbf{Normative References (Clause 2)} \\
& \longrightarrow \textbf{Test Methods \& Sampling Standards} \\
& \longrightarrow \textbf{Installation Codes \& Codes of Practice} \\
& \longrightarrow \textbf{Safety Standards} \\
& \longrightarrow \textbf{Terminology Standards} \\
& \longrightarrow \textbf{Allied Product Standards \& Trim Components} \\
& \longrightarrow \textbf{Lifecycle \& Amendment Currency} \\
& \longrightarrow \textbf{Certification / Regulatory Signals (ISI / QCO / CRS)} \\
& \longrightarrow \textbf{External Authority Advisory Context (FSSAI, CEA, CPWD)} \\
& \longrightarrow \textbf{Evidence \& Provenance Hierarchy} \\
& \longrightarrow \textbf{Human Review \& Audit Reports}
\end{aligned}$$

---

## 2. Benchmark Audit & Evaluator Source of Truth (16/20 vs 18/20 Resolution)

A critical instruction for Phase 9 is to audit the benchmark results and explicitly resolve any internal discrepancies between 16/20 and 18/20:

### Historical Trace
1. **Milestone 2 Baseline**: Established a **90.0% (18/20)** Top-1 accuracy on `dataset/ground_truth/ground_truth.csv` with 2 safe abstentions (`T004-R002` and `T010-R001`).
2. **Mid-Phase 8 Transient Regression**: During the implementation of Task 5 (generic pipe material completeness checks), an unconstrained check on `top_attrs.product_family == 'pipe'` inadvertently triggered on `T001-R002` ("replacement of damaged pipelines by Hubless") and `T012-R003` ("Plumbing Fittings"). This temporarily caused those two rows to abstain, creating an intermediate evaluation of **80.0% (16/20)**.
3. **Phase 8 Remediation Fix**:
   - In [`src/applicability.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/src/applicability.py), `has_sewerage_req` was updated to explicitly recognize sanitary terms (`hubless`, `soil pipe`), allowing `IS 15905` to pass applicability for `T001-R002`.
   - In [`src/ambiguity.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/src/ambiguity.py), `is_generic_pipe` was refined to require explicit pipe nouns (`pipes`, `piping`) while strictly excluding fittings and specialized drainage types (`fittings`, `valves`, `hubless`).
4. **Current Repository Source of Truth**:
   Running `python3 -m src.evaluate` against the frozen ground truth dataset yields:
   - **Top-1 Accuracy**: **90.0% (18/20)**
   - **Top-3 Retrieval Recall**: **90.0% (18/20)**
   - **Mean Reciprocal Rank (MRR)**: **0.900**
   - **Negative Rejection Rate**: **100.0% (5/5)** (0 False Positives, 0.0% FPR)
   - **Supersedence Detection Rate**: **100.0%**
   - **Ambiguity Detection Recall**: **100.0%**
   - Verified in report: [`reports/feasibility/milestone2_evaluation_report.md`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/reports/feasibility/milestone2_evaluation_report.md) and [`reports/feasibility/milestone2_evaluation.csv`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/reports/feasibility/milestone2_evaluation.csv).
5. **Phase 9 Invariant**: The frozen benchmark must remain at $\ge 90.0\%$ (18/20 Top-1, 0 False Positives, 100% Negative Rejection).

---

## 3. Locked Architectural Decisions for Phase 9

### Decision 1: Consolidated 6-Type Relationship Ontology
- Unify standard node roles and edge relationship types across `standards.py`, `graph.py`, `dependencies.py`, and `audit.py`.
- **The Canonical 6 Relationship Types**:
  1. `NORMATIVE_REFERENCE`: Mandatory standards cited in Clause 2 without which the primary standard cannot be implemented.
  2. `TEST_METHOD`: Standards defining test procedures, sampling, chemical analysis, or mechanical testing.
  3. `INSTALLATION_CODE`: Codes of practice defining laying, erection, jointing, safety clearances, or maintenance.
  4. `SAFETY_STANDARD`: Standards specifying protective equipment, fire barriers, insulation ratings, or electrical safety.
  5. `TERMINOLOGY_STANDARD`: Standards specifying glossaries, definitions, symbols, or nomenclature.
  6. `ALLIED_STANDARD`: Standards covering related product sub-assemblies, pipe fittings, flanges, or trim materials.
- In addition, lifecycle edges (`SUPERSEDES`, `AMENDS`) remain strictly tracked.
- **Rule**: Every graph edge must store:
  `(source_standard, target_standard, relationship_type, evidence_clause, provenance, confidence)`
- **Strict Provenance Invariant**: Production graph provenance must strictly be `VERIFIED` or `CURATED`. `INFERRED` is strictly prohibited from entering the production relationship graph.

### Decision 2: Five Demonstration Domains for Verified Relationship Coverage
Rather than claiming false universal coverage of 35,000 standards, Phase 9 systematically expands verified relationship coverage across the **5 core procurement domains** targeted in the SIH demonstration subject to evidence availability:
- **Execution Rule**:
  $$\mathbf{SOURCE\ EVIDENCE \longrightarrow VERIFY\ RELATIONSHIP \longrightarrow ADD\ TO\ GRAPH}$$
  Candidate standards below are treated as **candidate relationships requiring source verification**, not already verified facts. If a relationship cannot be verified from an acceptable official source, it must not be added merely to meet a quota. The actual verified count will be reported upon completion.
1. **Civil & Water Distribution Candidates**: Precast concrete pipes (`IS 458`), CPVC pipes (`IS 15778`), UPVC pipes (`IS 4985`), Steel tubes (`IS 1239 Part 1`), Cast iron hubless (`IS 15905`), DI pipes (`IS 8329`), Laying codes (`IS 783`, `IS 7634`), Testing (`IS 3597`, `IS 12235`).
2. **Electrical Distribution Candidates**: Cross-linked polyethylene XLPE cables (`IS 7098 Part 1 & 2`), PVC cables (`IS 694`, `IS 1554`), Earthing code (`IS 3043`), Electrical wiring installation (`IS 732`), Cable installation (`IS 1255`), Cable test methods (`IS 10810`).
3. **Mechanical & Fluid Control Candidates**: Waterworks sluice valves (`IS 14846`), Copper alloy valves (`IS 778`), Steel gate valves (`IS/ISO 10434`), Pipe flanges (`IS 6392`, `IS 1538`), Jointing sheets (`IS 2712`).
4. **Rotating Machinery & Drives Candidates**: Induction motors (`IS/IEC 60034-1`, `IS 12615`), Borehole submersible pumps (`IS 8034`), Centrifugal water pumps (`IS 5120`, `IS 9079`), VFD drive systems (`IS/IEC 61800-2`).
5. **Substation & Power Equipment Candidates**: Distribution transformers (`IS 1180 Part 1`, `IS 2026`), Low-voltage switchgear assemblies (`IS/IEC 61439-1 & 2`, `IS/IEC 61439-3`).

### Decision 3: Decoupled External Authority Advisory Layer
- **Strict Boundary**: The local catalogue (`data/catalogue/bis_catalogue.json` and `standards.db`) remains **100% BIS Indian Standards**. External statutory regulations (e.g. FSSAI Food Safety regulations, Central Electricity Authority (CEA) Technical Standards, Central Public Works Department (CPWD) Specifications) **NEVER enter `standards.db` as BIS standards**.
- **Pre-Implementation Verification**: Every statutory instrument, scope statement, and related BIS reference must be verified against official notifications prior to integration. Zero hardcoded unverified mappings.
- **Implementation**: Create a dedicated, decoupled `ExternalAuthorityRegistry` and `ExternalAuthoritySignal` dataclass in `src/regulatory/`.
- **Output Representation**: External authority signals are returned in a separate `external_regulations` block in JSON responses, displayed in a distinct *"Statutory & Regulatory Advisory Context"* UI section, and explicitly tagged:
  `[NON-BIS ADVISORY: FSSAI / CEA / CPWD]`.
- **Tamper-Proof Disclaimer**:
  > *"Regulatory signals are advisory engineering heuristics based on published statutory frameworks and gazette notifications. They do not constitute statutory legal certifications or official compliance certificates."*

### Decision 4: Multi-Component Requirement Bundle Resolution
- When a tender requirement is compound (e.g., `T001-R002` requiring both Hubless Cast Iron pipes and GI water pipes; or `T005-R001` requiring DG Set cable connection and earthing), the system decomposes the requirement into independent technical components.
- In addition to the primary `candidate_standard` (top overall), the system surfaces a `component_recommendations` bundle where each independent technical component (e.g. `equipment: cable` $\rightarrow$ `IS 7098`, `installation: earthing` $\rightarrow$ `IS 3043`) is evaluated against its respective standard and allied dependency tree without mutual suppression.

### Decision 5: Lifecycle & Currency Propagation
- When a primary standard is recommended, its dependency tree is evaluated for currency:
  - If a normative reference is superseded, the system flags:
    `"Normative dependency IS XXXX has been superseded by IS YYYY. Review current testing/design alignment."`
  - If the primary standard has published amendments recorded in the catalogue metadata, the system surfaces the amendment count and currency tag.
  - Zero fabricated amendment dates: Only display amendment information supported by verified catalogue records.

---

## 4. Scope Fences & Boundaries

| Category | In Scope for Phase 9 | Out of Scope (Deferred to Future Roadmap) |
|---|---|---|
| **Graph Traversal** | Strictly Depth = 1 deterministic traversal from primary recommendation | Multi-hop recursive graph crawling (causes combinatorial explosion and loose relevance) |
| **Standards Relationships** | Expand verified relationship coverage across the 5 demonstration domains subject to evidence availability (report actual verified count at completion) | Full OCR extraction of all 35,000 PDF standards in the BIS archive |
| **External Authorities** | Static, verified registry of statutory signals for FSSAI, CEA, and CPWD | Live runtime web scraping of government gazette portals |
| **Certification & QCOs** | Deterministic evaluation of BIS Scheme-I (ISI Mark), QCO mandatory orders, and MeitY CRS | Automated statutory legal compliance guarantees |
| **Catalogue Boundary** | 100% immutable BIS standards catalogue (0 diffs) | Ingesting external standards (ISO, IEC, DIN, ASTM) directly into the BIS database |
| **Testing & Quality** | 100% passing pytest suite, 0 regressions, verified benchmark $\ge 90.0\%$, adversarial pass rate $\ge 98.6\%$ | Production Kubernetes deployment |

---

## 5. Risk Assessment & Mitigations

1. **Risk: Relationship Overload / Cluttered UI**
   - *Mitigation*: Categorize dependencies into collapsible, typed groups (Normative, Test Methods, Installation, Safety, Allied). Display only high-confidence dependencies by default.
2. **Risk: Catalogue Contamination by External Authorities**
   - *Mitigation*: Architectural isolation. `ExternalAuthorityRegistry` lives strictly in `src/regulatory/` and uses separate data structures (`ExternalAuthoritySignal`), with no shared database tables with `standards.db`.
3. **Risk: Benchmark or Adversarial Regressions**
   - *Mitigation*: Continuous regression gates. `test_evaluate_benchmark` and `test_eval_adversarial` run before any commit. Zero probe-specific hacks.
4. **Risk: False Relationship Hallucination**
   - *Mitigation*: Zero dynamic LLM relationship generation. All relationships must originate from verified Clause 2 references, forewords, or official BIS committee indices. Zero `INFERRED` provenance in production graph.
