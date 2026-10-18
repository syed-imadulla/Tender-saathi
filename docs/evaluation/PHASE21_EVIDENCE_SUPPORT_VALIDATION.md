# Tender Saathi — Phase 21: Evidence Support Engine Validation Audit Report

**Date**: 2026-10-18  
**Scope**: Independent Validation, Adversarial Matrix Auditing, and Boundary Hardening of Requirement-to-Evidence Support Engine  
**Phase State**: Completed  
**Status**: All 647 backend tests passing (including 18 deterministic offline adversarial validation tests), frontend production build cleanly verified, zero regression on active benchmark metrics, and bit-for-bit invariance of the active ground truth.

---

## 1. Executive Summary & Recovery Audit

Following an abrupt termination of the previous session caused by an operating system restart, an immediate recovery audit was performed to establish the ground state:

- **Recovery Findings**:
  - The previous session had completed Phase 20 and transitioned to Phase 21.
  - Phase 21 context (`.planning/phases/21-evidence-support-engine-validation/21-CONTEXT.md`) and plan (`.planning/phases/21-evidence-support-engine-validation/21-PLAN.md`) were fully articulated.
  - Core hardening edits were in progress across `src/corpus/retriever.py` and `src/traceability.py`, alongside an untracked 18-case adversarial test suite `tests/test_evidence_support_validation.py`.
  - The interruption occurred precisely after implementing the hardening logic and writing the 18-case matrix, before executing the full cross-system regression suite, generating the Phase 21 formal audit report, and updating roadmap tracking.
  - All existing working-tree modifications and untracked files were preserved without resets or stashes.

- **Objective of Phase 21**:
  Independently stress-test, audit, and harden the requirement-to-evidence support engine before expanding into standards precedence or additional recommendation logic.

---

## 2. Systematic Audit of Support Classification Logic

An in-depth code audit of `evaluate_requirement_support()` (`src/corpus/retriever.py`) and `TraceableEvidenceValidator` (`src/traceability.py`) revealed several critical defect surfaces that required deterministic hardening:

### A. Permissive Keyword-Only Matching
- **Vulnerability**: Previously, if a passage contained at least 1 keyword overlap with the requirement and had no direct envelope contradiction, it defaulted to `FULLY_SUPPORTED`.
- **Defect Impact**: A requirement demanding "11 kV dry-type transformer with 475 W maximum load losses" matched against a passage that only discussed "11 kV insulation levels" would be erroneously marked `FULLY_SUPPORTED` simply because "transformer" or "11 kV" matched, despite completely omitting loss verification.
- **Remediation**: Implemented **Conservative Technical Parameter Verification**. If a requirement specifies numerical physical parameters (power, voltage, apparent power, current), but the retrieved passage does not contain statements in that physical dimension, the engine conservatively returns `PARTIALLY_SUPPORTED` instead of over-claiming full support.

### B. Unit Conversion and Dimension Normalization
- **Vulnerability**: Lexical comparison previously looked for exact unit strings (e.g. `500 W` vs `500 W`).
- **Defect Impact**: If a tender specified `0.5 kW` and the standard mandated `500 W`, the system either failed to recognize the numeric equivalence or risked false conflict. Conversely, a requirement of `1000 kW` vs a standard ceiling of `500 W` was completely missed.
- **Remediation**: Implemented a normalized dimensional scale mapping power (`W`, `kW`, `MW`), voltage (`V`, `kV`), apparent power (`VA`, `kVA`, `MVA`), and current (`A`, `mA`) to their base SI units before conducting numeric boundary evaluations.

### C. Inequality Direction Semantics
- **Vulnerability**: Inequality checking assumed simplistic ceiling comparisons.
- **Defect Impact**: Did not discriminate between a tender specifying a minimum capability floor (e.g., "shall be at least 100 kVA") versus a standard specifying a maximum permissible threshold (e.g., "losses shall not exceed 500 W").
- **Remediation**: Added directional parsing:
  - If a tender specifies a minimum requirement ("at least", "minimum", "shall be at least") and the standard imposes a lower maximum ceiling, it is flagged as `CONFLICTING`.
  - If a tender permits an upper ceiling looser than the standard's strict ceiling (e.g. tender specifies max 600 W, standard specifies max 500 W), it is flagged as `CONFLICTING`.
  - If a tender rating falls below a standard's mandatory floor, it is flagged as `CONFLICTING`.

### D. Tolerance and Range Precision
- **Vulnerability**: Missing tolerance comparison.
- **Defect Impact**: If a tender requires tighter measurement tolerances than the standard provides (e.g. tender requires $\pm 2\%$ while standard specifies $\pm 5\%$), declaring full support is unsafe.
- **Remediation**: Added regex detection for percentage tolerances (`±`, `+/-`, `within X %`). When a tender demands stricter tolerance than the standard permits, support is conservative (`PARTIALLY_SUPPORTED`).

### E. Negation and Structural Exclusions
- **Vulnerability**: Negative phrases like "without conservator tank" or "excluding auxiliary cooling" could match positive clauses "shall have conservator tank".
- **Defect Impact**: Opposite engineering intents could be falsely marked as supported.
- **Remediation**: Added bidirectional negation scanning (`without`, `excluding`, `shall not have`, `shall not contain`, `prohibited`). If either requirement or passage negates an element that the other mandates, the state is flagged as `CONFLICTING`.

### F. Multi-Passage Contradiction Escalation
- **Vulnerability**: Lexical retrieval previously checked only the top-1 matching passage.
- **Defect Impact**: If multiple candidate passages for the same requirement presented conflicting normative statements, a single passage could mask the conflict.
- **Remediation**: Expanded candidate passage evaluation (`top_k=2`) in `ClauseRetriever`. If secondary candidate passages indicate `CONFLICTING` evidence, the overall outcome escalates to `CONFLICTING`.

### G. Strict Ingestion and Extraction Metadata Validation
- **Vulnerability**: Records with missing or unspecified extraction quality could pass through without scrutiny if not explicitly in `("QUALITY_FAILED", "OCR_REQUIRED", "CORRUPT")`.
- **Defect Impact**: Unvalidated or corrupted files with blank status could bypass validation.
- **Remediation**: Updated `TraceableEvidenceValidator.validate_record()` to reject any document where `ingestion_status` is missing, blank, or `FAILED`.

---

## 2. The 18-Case Independent Adversarial Validation Matrix

The 18 deterministic offline test cases implemented in `tests/test_evidence_support_validation.py` test all required failure modes without network egress or live LLM reliance:

| # | Adversarial Scenario | Test Description & Inputs | Expected Outcome | Actual Result |
|---|---|---|---|---|
| 1 | **Irrelevant Technical Subject** | Correct clause ID (`4.20`) about auxiliary wiring queried for RCC transformer foundation raft | `UNSUPPORTED` | **PASSED** |
| 2 | **Unsupported Operating Conditions** | Clause `6.1` (Indoor dry-type apparatus) queried for outdoor pole-mounted transformer | `CONFLICTING` | **PASSED** |
| 3 | **Exact Numeric Match** | 100 kVA transformer, 500 W losses at 50% load matching Clause `4.2` exactly | `FULLY_SUPPORTED` | **PASSED** |
| 4 | **Conflicting Numeric Rating** | Tender allows 600 W losses; standard mandates max permissible 500 W | `CONFLICTING` | **PASSED** |
| 5 | **Equivalent Units Conversion** | Tender specifies 0.5 kW; standard specifies 500 W (valid conversion) | `FULLY_SUPPORTED` | **PASSED** |
| 6 | **Inequality Direction Mismatch** | Tender demands "at least 600 W" rating where standard ceiling is 500 W | `CONFLICTING` | **PASSED** |
| 7 | **Tolerance and Range Mismatch** | Tender demands $\pm 2\%$ tolerance; standard specifies $\pm 5\%$ | `PARTIALLY_SUPPORTED` | **PASSED** |
| 8 | **Negation / Exclusion Conflict** | Tender demands "without conservator tank"; standard mandates conservator tank | `CONFLICTING` | **PASSED** |
| 9 | **Indoor vs Outdoor Conflict** | Outdoor yard installation requirement tested against indoor-only passage | `CONFLICTING` | **PASSED** |
| 10 | **Compound Requirement Partial Coverage** | Compound req (Losses + Nitrogen fire fighting); passage only covers Losses | `PARTIALLY_SUPPORTED` | **PASSED** |
| 11 | **Contradictory Evidence Across Passages** | Two candidate passages in search; secondary passage contains contradiction | `CONFLICTING` | **PASSED** |
| 12 | **Wrong Edition Isolation** | Valid clause queried against 1979 edition instead of 2014 edition | `CORPUS_DOCUMENT_NOT_ELIGIBLE` & `UNVERIFIED_COVERAGE` | **PASSED** |
| 13 | **Missing Extraction Quality Metadata** | Document record with empty/unspecified `ingestion_status` | Rejected in `TraceableEvidenceValidator` | **PASSED** |
| 14 | **OCR-Required / Quality-Failed Source** | Ingestion status `OCR_REQUIRED` | `CORPUS_DOCUMENT_NOT_ELIGIBLE` | **PASSED** |
| 15 | **Missing Corpus Storage / DB Failure** | SQLite storage unavailable (`storage=None`) | `CORPUS_NOT_AVAILABLE` & `UNVERIFIED_COVERAGE` | **PASSED** |
| 16 | **Tampered Document Hashes** | Forged file SHA-256 injected into evidence trace | `is_normative_clause_verified = False` | **PASSED** |
| 17 | **Superficial Clause Discrimination** | Clause `4.2` (Losses) vs Clause `4.20` (Auxiliary Wiring) strictly isolated | Exact match only; no false cross-talk | **PASSED** |
| 18 | **Unparseable Technical Parameters** | Tender has complex rating/insulation parameter absent from passage | Conservative fallback to `PARTIALLY_SUPPORTED` | **PASSED** |

---

## 3. Verification and Benchmark Integrity

### A. Test Execution Summary

1. **Phase 21 Focused Adversarial Matrix**:
   ```bash
   pytest tests/test_evidence_support_validation.py -v
   # 18 passed in 0.63s
   ```

2. **Combined Evidence Ingestion & Traceability Suites (Phases 18–21)**:
   ```bash
   pytest tests/test_corpus_ingestion.py tests/test_clause_evidence_integration.py tests/test_evidence_validation_audit.py tests/test_evidence_support_validation.py -v
   # 58 passed in 7.44s
   ```

3. **Complete Backend Regression Suite**:
   ```bash
   pytest -q
   # 647 passed in 63.15s (0:01:03)
   ```
   *Historical baseline from Phase 20 was 629 passing tests. With the 18 new adversarial tests, all 647/647 pass cleanly with zero regressions.*

4. **Frontend Production Build**:
   ```bash
   npm run build --prefix frontend
   # ✓ built in 1.04s (zero TypeScript compilation errors, zero bundler warnings)
   ```

5. **Decoupled Benchmark Evaluation**:
   ```bash
   python3 scripts/evaluate_milestone12.py
   ```
   - **Active Ground Truth SHA-256**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Bit-for-bit unchanged before and after execution)
   - **Top-1 Accuracy**: `89.5%` (17 / 19 answerable)
   - **Top-3 Accuracy**: `89.5%` (17 / 19 answerable)
   - **Mean Reciprocal Rank (MRR)**: `0.895`
   - **In-Domain Selective Risk**: `0.0%` (0 / 13 incorrect recommendations)
   - **Under-Specification Abstention Recall**: `100.0%` (1 / 1)
   - **Negative False Recommendation Rate**: `0.0%` (0 / 5)
   - **Negative Rejection Rate**: `100.0%` (5 / 5)

---

## 4. Anti-Falsification Invariants & Operational Boundaries

Throughout Phase 21, the system's strict anti-falsification barriers were maintained:

1. **Authentication Guard**: `is_official_source_authenticated` remains strictly hardcoded to `False` across all machine-automated flows. Automated ingestion never claims live portal authentication with the Bureau of Indian Standards.
2. **Human Adjudication Boundary**: `is_human_verified` remains strictly hardcoded to `False` unless a signed human expert packet is processed through the consensus CLI.
3. **Conservative Defaulting**: The absence of technical evidence or absence of parsable parameters never defaults to positive evidence. When evidence cannot confirm a parameter, the engine conservative defaults to `PARTIALLY_SUPPORTED` or `UNVERIFIED_COVERAGE`.
4. **Edition Isolation**: Different editions of the same standard (e.g. IS 1180 : 1979 vs IS 1180 (Part 1) : 2014) remain strictly partitioned by edition year in SQLite schemas and chunk identifiers.

---

## 5. Deliverable Artifacts

- `.planning/phases/21-evidence-support-engine-validation/21-CONTEXT.md`: Audit context and discoveries.
- `.planning/phases/21-evidence-support-engine-validation/21-PLAN.md`: Phase execution plan.
- `src/corpus/retriever.py`: Hardened unit normalization, inequality checks, tolerance checking, negation handling, multi-passage contradiction evaluation, and conservative parameter verification.
- `src/traceability.py`: Strict ingestion status validation.
- `tests/test_evidence_support_validation.py`: 18-case independent adversarial test suite.
- `docs/evaluation/PHASE21_EVIDENCE_SUPPORT_VALIDATION.md`: This comprehensive audit report.

---

## 6. Next Justified Phase

With the requirement-to-evidence support engine independently verified, stress-tested against 18 adversarial scenarios, and free of false-support leaks:

**Recommended Next Phase**: **Phase 22 — Multi-Requirement Systemic Conflict Resolution & Standards Precedence Engine**
- Formulate precedence graphs between general product specifications (e.g., general switchgear IS 13947 / IS/IEC 60947) and specialized application codes (e.g., lift/escalator safety IS 14665 or mining installations).
- Resolve cross-requirement standard conflicts deterministically.
