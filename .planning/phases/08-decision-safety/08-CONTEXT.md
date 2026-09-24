# Phase 8: Decision Safety & Trust Boundary Completion — Context

**Phase Number**: 08  
**Phase Status**: Planning  
**Baseline Git Commit**: `4a5cf5d` (Phase 7 certified baseline)  
**Parent Milestone**: SIH26108 Feasibility & Reliability Architecture  

---

## 1. Executive Intent & Guiding Invariant

Phase 7 closed 11 adversarial vulnerabilities, lifting overall adversarial pass rates from 57.1% (40/70) to 72.9% (51/70) while preserving 100% evidence grounding and the frozen 20-row benchmark (18/20 Top-1, 0.900 MRR, 0 False Positives). However, four multi-dimensional safety targets remained below threshold:

1. **False-Positive Rejection Rate**: 80.0% (4/5) $\rightarrow$ Target: **100.0% (5/5)**
2. **Safe-Abstention Rate (Under-Determined)**: 46.7% (7/15) $\rightarrow$ Target: **$\ge 93.3\%$ ($\ge 14/15$)**
3. **Human-Review Routing Recall**: 87.0% (40/46) $\rightarrow$ Target: **$\ge 95.7\%$ ($\ge 44/46$)**
4. **Prompt-Injection Containment Rate**: 40.0% (2/5) $\rightarrow$ Target: **100.0% (5/5)**

Phase 8 completes the decision-safety architecture by eliminating the systemic mechanisms behind the remaining 19 failures, raising the overall adversarial pass rate to **$\ge 66/70$ ($\ge 94.3\%$)** (at most 4 residual vulnerabilities, accommodating accepted catalogue boundaries such as `ADV-MUL-005` FSSAI Schedule 4).

### Absolute Core Invariants:
1. **"Fix the failure mechanism, not the individual probe."**
2. **"Correct abstention is always preferable to an unsupported recommendation."**
3. **"A secondary candidate may never be promoted merely because it survived a weaker check."**
4. **"Evidence Grounding Invariant: $\text{candidate\_standard} == \text{evidence\_standard}$ on 100% of emitted recommendations."**
5. **"Zero Hardcoding**: Zero `ADV-*` probe IDs, probe strings, or synthetic exceptions in production code."
6. **"Zero Fabricated Thresholds**: All engineering envelope bounds derive from verified standard scopes; omitted constraints evaluate to `UNKNOWN` / `REVIEW_REQUIRED`."
7. **"Absolute Asset Immutability**: `dataset/ground_truth/`, `data/catalogue/`, and `dataset/adversarial/` remain 100% untouched."

---

## 2. Refined Architectural Dependency Model

```
       [Raw Tender Input]
               │
               ▼
   ┌────────────────────────────────────────────────────────┐
   │ 1. Ingestion Trust Boundary (M1)                       │
   │    - Preserve raw_context for audit trail              │
   │    - Neutralize JSON payloads, directives, overrides   │
   │    - Emit sanitized working query stream               │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ 2. Semantic Role Separation (M2)                       │
   │    - Distinguish physical entities from governance     │
   │    - Exclude procedural tokens (audit, compliance)     │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ 3. Retrieval & Composite Requirement Resolution (M6)   │
   │    - Head-noun binding for complex compound modifiers  │
   │    - Domain-aware technical paraphrase normalization   │
   │    - Primary energy/load-bearing component selection   │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ 4. Independent Candidate Viability Gate (M4)           │
   │    - Evaluate EACH candidate independently             │
   │    - Verify physical domain & operational envelope     │
   │    - No survival by omitted rule (anti-fallthrough)    │
   │    - If viable pool empty -> clean abstention          │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ 5. Pre-Citation Operational Gate (M3)                  │
   │    - Subject explicit citations to operational envelope│
   │    - ConflictRegistry check before score bonus         │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ 6. Unified Decision Safety Gate (M5)                   │
   │    - Mandatory human review for: abstentions,          │
   │      conflicts, competing structural grades,           │
   │      unverified citations, decision-discriminators     │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
      [Authoritative Recommendation OR Safe Abstention]
```

---

## 3. The 6 Generalized Architectural Mechanisms

### M1: Ingestion Trust Boundary & Sanitized Query Stream
- **Files**: `src/extract.py`, `src/retrieval.py`
- **Concept**: Separate untrusted raw context from trusted algorithmic query stream.
- **Rule**:
  1. Strip structural JSON objects (`\{[^{}]*"[a-zA-Z_]+"\s*:[^{}]*\}`), directive commands (`SYSTEM OVERRIDE:`, `INSTRUCTION:`, `Return JSON:`), and adversarial command patterns from the working query stream passed to `HybridRetrievalEngine` and `extract_technical_tokens`.
  2. Retain 100% of the raw, untouched tender text in `Requirement.raw_context` for auditability.
  3. Guarantees that injected tokens (`1786`, `9999`) or format instructions cannot pollute retrieval vector embeddings or BM25 token frequencies.
- **Target Probes**: `ADV-INJ-001`, `ADV-INJ-004`.

### M2: Semantic Role Separation in Technical Token Extraction
- **Files**: `src/applicability.py` (`extract_technical_tokens`, `evaluate_candidate`)
- **Concept**: Technical token extraction must represent *physical entities, materials, equipment, and industrial processes*, not *administrative governance actions*.
- **Rule**:
  1. Classify tokens into semantic roles: Product/Material Entity vs Administrative/Procedural Action.
  2. Procedural and contractual words (`audit`, `compliance`, `statutory`, `hiring`, `taxation`, `firm`, `services`) are excluded from establishing `product_match` or `substantive_overlap`.
  3. Non-engineering corporate tenders (e.g. accounting, legal) have zero technical product overlap, cleanly evaluating to `NO_RELIABLE_MATCH` (`candidate_standard = None`).
- **Target Probes**: `ADV-ABS-002`, `ADV-INJ-003`.

### M3: Pre-Citation Operational Envelope Validation
- **Files**: `src/recommend.py`, `src/ambiguity.py`
- **Concept**: Explicit citations must not overpower physical operating incompatibilities.
- **Rule**:
  1. Before an explicit citation is awarded a deterministic 1.0 confidence score bonus, it must pass `ApplicabilityGate` operational condition bounds and `ConflictRegistry`.
  2. If the cited standard's physical scope conflicts with the tender's stated operating condition (e.g. non-pressure concrete pipe cited for high-pressure steam, or wall tile cited for blast furnace flooring):
     - Strip the 1.0 bonus.
     - Record `ApplicabilityDecision.INCOMPATIBLE`.
     - Set `ambiguity_state = AmbiguityState.CONFLICTING`.
     - Set `candidate_standard = None` and `human_review_required = True`.
- **Target Probes**: `ADV-APP-002`, `ADV-APP-005`.

### M4: Independent Candidate Viability Invariant (Anti-Fallthrough)
- **Files**: `src/recommend.py`, `src/applicability.py`
- **Concept**: "A secondary candidate may never be promoted merely because it survived a weaker check."
- **Rule**:
  1. Evaluate each retrieved candidate independently against domain and operating conditions.
  2. Secondary candidates do not inherit viability merely because they lack a specific rejection rule: they must positively satisfy the requirement's operational context.
  3. If all viable candidates are disqualified (e.g. CPVC pipe rejected for steam, wire rejected for furnace, pump rejected for acid, or cited standard nonexistent):
     - Do NOT fall through to arbitrary secondary candidates (`IS 14333` HDPE sewer pipe, `IS 1786` steel rebar, `IS 9694` motor).
     - Form an empty viable pool.
     - Abstain cleanly: `candidate_standard = None`, `ambiguity_state = NO_RELIABLE_MATCH` / `INCOMPATIBLE`, `human_review_required = True`.
- **Target Probes**: `ADV-APP-001`, `ADV-APP-003`, `ADV-APP-004`, `ADV-BND-004`, `ADV-CON-002`.

### M5: Unified Decision Safety Gate
- **Files**: `src/recommend.py`
- **Concept**: Consolidate human review triggers into an authoritative, threshold-free terminal safety gate.
- **Rule**:
  1. Human review is mandated (`human_review_required = True`) whenever unresolved decision-critical conditions exist:
     - `candidate_standard is None` (all abstentions and unresolvable tenders require engineer verification).
     - Any operational conflict or duty mismatch detected in `ConflictRegistry`.
     - Competing structural grades present (e.g. mild steel `IS 432` vs TMT `IS 1786` for concrete reinforcement).
     - Explicit tender citation is unrecognized, unverified, or contradicts the requirement specification.
     - Distinguishing parameters required to differentiate viable candidates are omitted.
     - Standard lifecycle role is `OLDER_VERSION`, `SUPERSEDED`, or `WITHDRAWN`.
  2. Eliminates magic retrieval score thresholds (no arbitrary `< 0.50` threshold).
- **Target Probes**: `ADV-DUP-003`, `ADV-CON-004`, `ADV-CON-002`, `ADV-LEX-005`.

### M6: Retrieval & Composite Requirement Resolution
- **Files**: `src/decompose.py`, `src/retrieval.py`, `src/search.py`
- **Core Invariant**: Zero direct phrase-to-standard-number mapping in production code. The system must NOT directly select a standard number from a requirement phrase. Candidate standards must strictly be obtained through catalogue retrieval based on enriched domain representation and generic functional roles.
- **Rule**:
  1. **Compound Head-Noun Binding**: For multi-modifier phrases (e.g. "agricultural motor oil immersion heater elements"), linguistic parsing separates modifier hierarchy from the functional head noun ("heater element"), down-weighting standards that match only context modifiers ("oil-immersed transformer", "induction motor").
  2. **Domain-Aware Technical Paraphrase Representation**:
     - Normalize dense chemical, metallurgical, and physical descriptions to standardized domain concepts/materials *within the query stream* (improving the representation used for retrieval rather than bypassing retrieval):
       - Chemical formulation: "post-chlorinated vinyl synthetic polymer" $\rightarrow$ normalized query concepts: "chlorinated polyvinyl chloride", "cpvc pipe".
       - Metallurgical process: "thermo-mechanically processed ferrous cylindrical rods with surface ribs" $\rightarrow$ normalized query concepts: "tmt steel bars", "high strength deformed steel bars", "concrete reinforcement".
     - The normalized concepts enrich the *working query representation* fed into the hybrid retrieval engine (`BM25` + dense semantic search) across the 35,208-record catalogue. The candidate standards are obtained strictly through catalogue retrieval.
  3. **Composite Requirement Generic Component Role Assignment**:
     - For composite multi-component industrial requirements (e.g. electrical substations, industrial plants), the decomposition engine (`src/decompose.py`) identifies sub-components and classifies their engineering roles into generic functional archetypes:
       - `ENERGY_TRANSFORMATION_COMPONENT` (e.g. transformer, generator, boiler)
       - `DISTRIBUTION_COMPONENT` (e.g. distribution pillar, switchboard, busbar)
       - `PROTECTIVE_COMPONENT` (e.g. circuit breaker, fuse, surge arrester)
       - `EARTHING_AND_SAFETY_COMPONENT` (e.g. earthing station, ground conductor)
     - For composite facilities, candidate ranking prioritizes the primary energy-transformation component over secondary distribution or auxiliary components. The candidate standard is obtained strictly from the retrieved candidates for that component role, never hardcoded from a requirement phrase.
- **Target Probes (Empirical Behavioral Assertions)**: `ADV-LEX-004`, `ADV-RET-001`, `ADV-RET-004`, `ADV-MUL-004`.

---

## 4. Phase 8 Measurable Acceptance Targets

| Evaluation Dimension | Baseline (Phase 7) | Phase 8 Target | Verification Tool |
| :--- | :---: | :---: | :--- |
| **False-Positive Rejection Rate** | 80.0% (4/5) | **100.0% (5/5)** | `python3 -m src.eval_adversarial` (Cat 10) |
| **Safe-Abstention Rate (Under-Determined)** | 46.7% (7/15) | **$\ge 93.3\%$ ($\ge 14/15$)** | `python3 -m src.eval_adversarial` (Cat 8, 1, 3) |
| **Human-Review Routing Recall** | 87.0% (40/46) | **$\ge 95.7\%$ ($\ge 44/46$)** | `python3 -m src.eval_adversarial` (Must Flag HR) |
| **Prompt-Injection Containment Rate** | 40.0% (2/5) | **100.0% (5/5)** | `python3 -m src.eval_adversarial` (Cat 13) |
| **Unsafe Confident Recommendation Rate** | 3.3% (2/61) | **$\le 1.6\%$ ($\le 1/61$)** | `python3 -m src.eval_adversarial` (Forbidden standards) |
| **Evidence Grounding Invariant Adherence** | 100.0% (46/46) | **100.0% (46/46)** | `python3 -m src.eval_adversarial` (All recommendations) |
| **Crash-Free Rate (Edge Cases)** | 100.0% (5/5) | **100.0% (5/5)** | `python3 -m src.eval_adversarial` (Cat 14) |
| **Total Adversarial Probes Passed** | 51 / 70 (72.9%) | **$\ge 66 / 70$ ($\ge 94.3\%$)** | `python3 -m src.eval_adversarial` (All 70 probes) |
| **Residual Vulnerability Budget** | 19 / 70 (27.1%) | **$\le 4 / 70$ ($\le 5.7\%$)** | `python3 -m src.eval_adversarial` (All 70 probes) |
| **Frozen 20-Row Benchmark Top-1 Acc** | 90.0% (18/20) | **$\ge 90.0\%$ (18/20)** | `python3 -m src.evaluate` (`hybrid+rerank`) |
| **Frozen 20-Row Benchmark MRR** | 0.900 | **$\ge 0.900$** | `python3 -m src.evaluate` (`hybrid+rerank`) |
| **Frozen 20-Row False Positives** | 0 (0.0%) | **0 (0.0%)** | `python3 -m src.evaluate` (5 negative cases) |
| **Full Repository Test Suite** | 455 passed | **$\ge 455$ passed (100%)** | `pytest tests/` (0 failures, 0 regressions) |
