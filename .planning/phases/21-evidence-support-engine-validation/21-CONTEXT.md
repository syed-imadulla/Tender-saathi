# Phase 21 Context: Evidence Support Engine Validation

## Phase Goal
Independently audit and validate the Phase 20 requirement-to-evidence support engine (`evaluate_requirement_support`, `TraceableEvidenceValidator`, `ClauseRetriever`, `recommend_for_requirement`) before extending the system with standards precedence or additional recommendation logic.

## Key Audit Questions & Discoveries

### 1. Keyword Overlap vs Technical Support
- **Issue**: `evaluate_requirement_support()` currently uses a permissive fallback: if there is no direct operating contradiction, no numerical limit contradiction, and at least 1 keyword overlaps with the passage, it returns `FULLY_SUPPORTED`.
- **Finding**: Having a single keyword overlap (e.g. "cable" or "loss") does NOT constitute full technical support. If technical parameters (voltage, temperature, rating, conductor type) are present in the requirement, they must not be assumed satisfied simply because a word matched.
- **Resolution**:
  - Add explicit parameter parsing and verification.
  - Where a requirement specifies technical parameters that the passage does not mention or confirm, return `PARTIALLY_SUPPORTED` or `UNSUPPORTED` (or `EXPERT_REVIEW_REQUIRED` if ambiguous).
  - Never default to `FULLY_SUPPORTED` on mere keyword presence.

### 2. Unit Conversion (W vs kW, kV vs V, etc.)
- **Issue**: The current regex in line 132 `re.findall(r'(\d+(?:\.\d+)?)\s*(kva|mva|kv|kw|amp|a\b)', req_clean)` only matches identical units. If requirement says `0.475 kW` and passage says `475 W`, it fails to recognize equivalence and may even miss a contradiction if units differ (e.g., requirement `1000 kW` vs passage `500 W` or vice versa).
- **Resolution**: Implement normalized unit conversion for common power (W, kW, MW), voltage (V, kV), and capacity (kVA, MVA) comparisons.

### 3. Inequality Direction & Comparison Semantics
- **Issue**: Currently checks only:
  - requirement > passage max limit -> CONFLICTING
  - requirement < passage min limit -> CONFLICTING
- But what if requirement specifies "shall be at least X" (minimum requirement) vs passage saying "maximum permissible is Y"? If X > Y, conflict!
- What if requirement specifies a ceiling "losses shall not exceed 475 W" vs passage saying "losses shall not exceed 500 W"? 475 W is within 500 W limit, which is consistent. But if requirement says "losses shall not exceed 600 W" and standard mandates "shall not exceed 500 W", the tender is allowing looser losses than standard, which is a compliance warning/conflict!

### 4. Tolerances & Operating Envelopes
- Missing or differing tolerances (e.g. ±5% vs ±10%).
- Negation ("shall not be", "excluding", "without") must be handled to prevent inverted support claims.

### 5. Clause Identifier Discrimination
- Ensure structural matching does not match sub-clauses or sibling clauses (`4.2` vs `4.20`, `4.2` vs `4.2.1`).

### 6. Two Passages with Conflicting Evidence
- If candidate standard has conflicting passages for the same requirement, escalate to `CONFLICTING` and `ASSISTED_REVIEW_REQUIRED`.

## Ground Truth Invariance
- `dataset/ground_truth/ground_truth.csv` SHA-256 (`8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`) must remain strictly immutable.
