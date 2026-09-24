# Safety Principles & Trust Invariants

**Tender Saathi** is built around the fundamental reality that public procurement decisions carry legal, structural, and financial accountability. An ungrounded recommendation or an invented standard number can result in contract litigation, rejected works, or audit objections under General Financial Rules (GFR) 2017.

To prevent ungrounded AI behavior, Tender Saathi implements four core operational principles and two inviolable software engineering invariants.

---

## 1. The Four Foundational Principles

```text
       AI interprets.
            ↓
       Rules validate.
            ↓
      Evidence supports.
            ↓
       Humans decide.
```

### Principle 1: AI Interprets (Optional & Sandboxed)
- Natural language models (LLMs) are used strictly as text parsers for linguistic decomposition and attribute extraction.
- **Strict Limitation**: LLMs are never permitted to:
  - Select standard numbers directly.
  - Invent or hallucinate standard codes.
  - Generate synthetic scope evidence.
  - Declare statutory compliance.
- In 100% offline environments, Tender Saathi automatically falls back to deterministic regex and syntactic chunking without loss of recommendation accuracy.

### Principle 2: Rules Validate (Deterministic Engineering Safety)
- Retrieval scores (lexical or semantic) never have final authority over standard recommendation.
- Deterministic engineering boundary gates have absolute veto power over candidate recommendations:
  - If a dense vector model associates a borehole submersible pump standard (`IS 8034`) with a generic surface pump query, the Duty Mode boundary gate vetoes the candidate.
  - If an operating condition bound is violated (e.g. steam temperature vs. CPVC plastic limits), the candidate is rejected.

### Principle 3: Evidence Supports (Verbatim Scope Grounding)
- Every surfaced recommendation is backed by verbatim text extracted from the official standard's published scope clause.
- Recommendations are tagged with tracked provenance tiers (`OFFICIAL_PRIMARY`, `OFFICIAL_SECONDARY`, `VERIFIED`, `CURATED`). Inferred data is never presented as authoritative evidence.

### Principle 4: Humans Decide (Decision-Support Role)
- Tender Saathi is an **assistive audit tool**, not an autonomous procurement signatory.
- Ambiguous specifications, superseded standards, and uncertain edge cases are routed to procurement engineers via the Prioritized Human Review Queue.

---

## 2. The Two Core Software Engineering Invariants

### Invariant 1: Candidate-Evidence Parity
For any non-null recommendation emitted by the engine, the candidate standard and the evidence standard must be strictly identical:

$$\text{candidate\_standard} == \text{evidence\_standard}$$

*The engine cannot surface Standard A while citing supporting scope text from Standard B.*

### Invariant 2: Safe Abstention Invariant
When available technical parameters are incomplete, ambiguous, or ungrounded in available catalogue evidence, the system safely abstains and routes the case to human review:

$$\begin{aligned}
\text{candidate\_standard} &= \text{None} \\
\text{evidence\_standard} &= \text{None} \\
\text{human\_review\_required} &= \text{True}
\end{aligned}$$

*Rather than guessing an ungrounded standard, the system abstains safely.*

---

## 3. Statutory Boundary & Disclaimer

Tender Saathi provides engineering decision-support findings based on indexed standards documentation and gazette notifications. All reports and API responses carry the mandatory statutory disclaimer:

> **Statutory Disclaimer**: *Outputs and regulatory signals are advisory engineering heuristics based on published technical standards and statutory frameworks. They do not constitute statutory legal certifications or official compliance certificates.*
