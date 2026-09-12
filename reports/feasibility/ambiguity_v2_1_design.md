# Ambiguity V2.1 Design Document

## A. Current Execution Flow
The `AmbiguityEngine` operates on an 8-stage pipeline:
1. Conflict Detection (hardcoded `ConflictRegistry`).
2. Catalogue Retrieval (evaluates if `retrieved_candidates` is empty).
3. Candidate Applicability Gate (filters out incompatible domains/products).
4. Candidate Competition (Ambiguity) — **Top-1 anchored, delta-gated (0.12), hardcoded rules**.
5. Specification Completeness (Incomplete) — domain-specific missing parameter checks.
6. Evidence Trust Validation.
7. Lifecycle & Regulatory Review.
8. Final Resolution (CLEAR).

## B. Current Candidate Pool Generation
The pool is currently generated from `search_results` that pass the `ApplicabilityGate` (resulting in `applicable_candidates`). 
However, for competition, the engine **only** compares Candidate #1 against Candidate #2, #3, and #4, and **only** if the score delta is <= 0.12.

## C. Current Ambiguity Gate
The ambiguity gate is defined in `is_true_competing_interpretation()`. It verifies if two candidates are competing by passing them through a rigid sequence of if/else rules:
1. Standard Role Gate (must be same role).
2. Complementary Assembly Parts Gate.
3. Equipment Family Scope Gate (e.g. VFD vs Switchgear).
4. Domain Matching.
5. Specific hardcoded standard comparisons (Food Safety).

## D. Every Hardcoded Standard-Number-Specific Rule
The following rules rely directly on IS numbers in `is_true_competing_interpretation`:
- Flange: `6392`
- Gasket: `2712`
- Bib tap: `781`
- Cistern: `774`
- Vitreous sanitary: `2556`
- Luminaire: `10322`
- Distribution board: `61439-3`, `5039`
- Power Drive (VFD): `61800`
- Switchgear: `61439`
- Refinery: `10434`, `10611`
- Food Safety: `2491` vs `15000`

## E. Every Domain-Specific Rule
In Stage 5 (Specification Completeness), the following domain checks are hardcoded:
- `cable`: checks for voltage_rating, insulation_type.
- `valve`: checks for valve_type, body_material.
- `pipe`: checks for material.
- `pump`: checks for pump_type, motor_details.
- `motor`: checks for voltage_rating, power_rating.
- `panel` / `switchgear`: checks for ampere/fault rating/ip.
- `cement`: checks for grade/type.

## F. Which Rules are Retained
- The **Conflict Registry** rules (CONF-01 through CONF-05) are retained as safety overrides.
- The concept of **Standard Role Classification** (Product vs Installation vs Testing).
- The general **Applicability Gate** that filters out candidates completely unsuited for the domain.

## G. Which Rules are Removed
- The **score delta gate** (`delta <= self.separation_threshold`).
- **All standard-number specific matching** in `is_true_competing_interpretation` (e.g., 61800 vs 61439, 2491 vs 15000, 6392 vs 2712).
- The rigid top-1 vs runner-up loop.

## H. Proposed Generalized Architecture
1. **Retrieval**: Run vector + lexical search to get Top N results to form the base pool.
2. **Pool Bounding**: Filter the pool using `ApplicabilityGate` and `classify_standard_role()`. Retain candidates that match the desired role (`PRIMARY_PRODUCT` usually). 
3. **Attribute Derivation**: Normalize each candidate into a standard attribute dictionary: `product_family`, `object_type`, `material`, `voltage_range`, etc.
4. **All-Pairs Competition (Bounded)**: Compare the top candidate against other candidates in the pool. Use `same_procurement_object(c1, c2, req)` to filter out non-competitors.
5. **Discriminator Detection**: Use `find_discriminators(c1, c2)` to isolate differences (e.g., c1.material == PVC, c2.material == XLPE).
6. **Requirement Resolution**: Extract attributes from the tender text. If the tender specifies the discriminator (e.g. "XLPE"), the candidate lacking it (PVC) is eliminated from competition. If not specified, the state is `AMBIGUOUS`.
