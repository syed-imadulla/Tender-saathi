# Tender Saathi — Phase 17: Evidence Integrity and Verification Semantics Audit

**Audit Date**: 2026-10-18  
**Audit Status**: COMPLETE  
**Auditor**: Independent Integrity & Verification Semantics Audit Engine  
**Target Codebase**: `src/traceability.py`, `src/recommend.py`, `src/standards.py`, `src/evidence_intelligence.py`, `api/server.py`, `frontend/src/`  
**Active Ground Truth**: `dataset/ground_truth/ground_truth.csv` (SHA-256: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`, Unmodified)  
**Database**: `data/standards/standards.db` (90 Records)

---

## 1. Findings Classified by Severity

| ID | Severity | Area | Finding Summary | Status |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-17-01** | **HIGH** | `src/recommend.py` & `src/traceability.py` | **False Universal Review Requirement**: `build_trace_record` evaluated `top_rec` without passing the recommender's computed `critic_result` or `human_review_required`. Because `StandardRecommendation` lacks a `critic_result` attribute, `critic_dec` defaulted to `"REVIEW_REQUIRED"`, forcing `final_system_decision = "ASSISTED_REVIEW_REQUIRED"` and masking 12 clean autonomous recommendations as requiring human review. | **FIXED** |
| **SEC-17-02** | **MEDIUM** | `src/traceability.py` | **Trivial / Whitespace Passage Pass**: Verification logic `(record.supporting_passage.strip() in cat_scope)` allowed whitespace or short trivial strings (`"" in cat_scope` is `True` in Python) to pass passage verification, generating empty-string SHA-256 hashes (`e3b0c442...`). | **FIXED** |
| **SEC-17-03** | **MEDIUM** | `src/standards.py` / `standards.db` | **Source URL / Citation Overloading**: The `source_url` database column stores both web URLs (13 entries) and physical document citations (26 entries, e.g. `CPWD Vol 2 Subhead 17`). Strict URL scheme checking previously flagged valid documentary citations as invalid URL schemes. | **FIXED** |
| **SEC-17-04** | **MEDIUM** | `src/traceability.py` | **Edition / Year Slug Lookup Gap**: Standards with multiple editions in `standards.db` (such as `IS 2491:2013` and `IS 2491:2024`) returned the wrong row when queried only by normalized standard number, causing false passage mismatch errors. | **FIXED** |
| **SEC-17-05** | **LOW** | `frontend/src/` | **Visual Overstatement Risk**: UI labels in Section 14 displayed "Verified in Scope" without clarifying that verification confirms consistency with the *local SQLite database snapshot*, not a live cryptographically signed BIS portal handshake. | **FIXED** |

---

## 2. Actual Meaning of Each Verification Status

To prevent conflation between local database consistency, live third-party authentication, and human adjudication, the system enforces the following semantic definitions:

| Verification Claim / Status | Exact System Meaning | What It Does NOT Mean |
| :--- | :--- | :--- |
| **`is_local_catalogue_verified`** (`is_catalogue_verified`) | The normalized standard number or edition slug was found in the local SQLite database (`data/standards/standards.db`). | Does **not** mean the standard was authenticated against the live BIS Manakonline portal or that statutory gazette status was queried at runtime. |
| **`is_passage_verified_in_source`** | The supporting scope excerpt matches the verbatim `scope` column stored in the local SQLite catalogue database (minimum 15 characters, normalized whitespace). | Does **not** mean the standard's full body text was scanned or that specific normative clauses (e.g. Clause 4.2) were grounded. |
| **`is_official_source_authenticated`** | **Strictly `False`** across all records. Indicates whether a live cryptographic or portal session authenticated the record during recommendation. | The system operates 100% offline against a local curated SQLite cache. |
| **`is_normative_clause_verified`** | **Strictly `False`** across all records. Indicates whether specific normative clauses, tables, or test procedures were verified against full standard body text. | Full standard normative PDF text is not yet ingested; only scope and metadata exist in `standards.db`. |
| **`is_lifecycle_verified`** | The standard's lifecycle in the local database matches one of `ACTIVE`, `WITHDRAWN`, or `SUPERSEDED`, and agrees with the recommendation claim. | Does **not** guarantee that BIS has not reaffirmed or superseded the standard after the database snapshot date. |
| **`content_hash`** | A deterministic SHA-256 hash computed over canonicalized passage text (whitespace collapsed to single spaces). | Does **not** imply official endorsement or cryptographic signature by BIS. |
| **`is_human_verified`** | **Strictly `False`** across all machine-generated recommendations. Machine recommendations cannot set this to `True`. | High semantic similarity, high BM25 scores, or LLM explanations are never treated as human expert verification. |

---

## 3. Reproduced Metrics with Numerators and Denominators

### 3.1 Standards Catalogue Baseline (`data/standards/standards.db`)
- **Total Catalogue Entries**: **90 / 90** (100.0%)
- **Entries with Usable Scope Text**: **90 / 90** (100.0%)
- **Entries with Source Provenance Recorded**: **90 / 90** (100.0%)
- **Entries with True Web URLs (`https://...`)**: **13 / 90** (14.4%)
- **Entries with Documentary / Gazette Citations in `source_url`**: **26 / 90** (28.9%)
- **Entries with `source_url = NULL` (Offline Compendia)**: **51 / 90** (56.7%)
- **Entries by Status**: Active: **75 / 90** (83.3%), Withdrawn: **15 / 90** (16.7%), Unknown: **0 / 90** (0.0%)

### 3.2 Evaluation Benchmark Reconciliation (20 Active Ground Truth Cases)
Re-evaluated deterministically against `dataset/ground_truth/ground_truth.csv`:

| Metric Name | Numerator / Denominator | Value | Audit Finding & Reconciliation |
| :--- | :---: | :---: | :--- |
| **Clean Autonomous Recommendations** (`SUPPORTING_EVIDENCE_AVAILABLE`) | **12 / 20** | **60.0%** | Resolved SEC-17-01. These 12 cases have verified local scope text, passed applicability, and require no human intervention. |
| **Recommendations Requiring Human Review** (`HUMAN_REVIEW_REQUIRED`) | **5 / 20** | **25.0%** | T001-R002, T005-R001, T007-R003, T009-R001, T011-R001. Require review due to multi-component ambiguity or missing technical parameters. |
| **Negative-Control Abstentions** (`UNKNOWN_STANDARD`) | **3 / 20** | **15.0%** | T002-R002, T004-R002, T010-R001. Clean abstention with `final_system_decision = "WITHHELD_INSUFFICIENT_EVIDENCE"` and `content_hash = None`. |
| **Traceable Local Scope Passages** | **17 / 20** | **85.0%** | Exactly 17 positive recommendations have verified local scope passages with reproducible SHA-256 hashes (100% of non-abstaining cases). |
| **Catalogue Metadata Only** | **0 / 20** | **0.0%** | No recommendation relied strictly on catalogue title without scope passage. |
| **Evidence Incomplete / Mismatch** | **0 / 20** | **0.0%** | Zero passage mismatches or catalogue lookup failures. |
| **Authentic Clause-Level Normative Evidence** | **0 / 20** | **0.0%** | **N/A** — Full normative body text is not yet stored. Honestly reported as unavailable. |
| **Qualified Human Expert Verification** | **0 / 20** | **0.0%** | **N/A** — Zero cases have been adjudicated by qualified external engineers. |
| **Official Live BIS Authenticated** | **0 / 20** | **0.0%** | **N/A** — Offline local database cache; no live portal authentication claimed. |

---

## 4. Defects Found and Exact Fixes Applied

1. **Fix for False Universal Review Requirement (SEC-17-01)**:
   - Modified `src/recommend.py` to explicitly pass `human_review_required=human_review_required` and `critic_decision=critic_dict.get("decision", "RECOMMEND")` into `self.evidence_validator.build_trace_record(...)`.
   - Updated `TraceableEvidenceValidator.build_trace_record` to accept these explicit flags and only default to `REVIEW_REQUIRED` when `cand_std` is missing or when explicitly requested.
2. **Fix for Trivial/Whitespace Passage Pass (SEC-17-02)**:
   - Enforced minimum 15-character length and whitespace stripping in `TraceableEvidenceValidator`.
   - Normalizes whitespace (`re.sub(r'\s+', ' ', passage)`) prior to SHA-256 hash computation. Whitespace-only passages yield `content_hash = None` and `is_passage_verified_in_source = False`.
3. **Fix for Source URL Citation Validation (SEC-17-03)**:
   - Updated URL validation in `TraceableEvidenceValidator.validate_record` to target forged or dangerous schemes (`javascript:`, `data:`, `file:`, `ftp:`, `chrome:`) and malformed `://` entries, while allowing valid documentary citations (e.g., `CPWD Vol 2 Subhead 17`) to be recorded without generating false validation errors.
4. **Fix for Multi-Edition Standard Resolution (SEC-17-04)**:
   - Updated catalogue lookup order to attempt exact edition slugs (`std_slug`, e.g. `IS-2491-2013`) before normalized standard numbers (`norm_std`, `IS 2491`), preventing older revisions from colliding with newer editions in `standards.db`.
5. **Fix for UI Semantics and Disclaimers (SEC-17-05)**:
   - Updated Section 14 in `frontend/src/components/EvidenceDrawer.tsx` to display explicit semantic labels: "Local Catalogue", "Local Scope Passage", "Official BIS Live Auth: Offline Local Cache", "Clause-Level Grounding: Scope-Level Only", and added an explanatory disclaimer.

---

## 5. Tests Added and Verification Results

### 5.1 Newly Added Adversarial Test Suite
Created [`tests/test_evidence_integrity_audit.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/tests/test_evidence_integrity_audit.py) covering 11 adversarial and boundary scenarios:
- `test_01_scope_text_without_source_url`: Verifies non-URL records remain `source_url = None`.
- `test_02_unknown_lifecycle_state`: Verifies unknown lifecycle states in DB are handled gracefully.
- `test_03_forged_or_invalid_source_url`: Detects and flags `javascript:` and dangerous schemes.
- `test_04_mismatched_passage_fails_verification`: Catches synthetic/mismatched passage text.
- `test_05_canonical_content_hash_reproducibility`: Verifies hash reproducibility across whitespace variations.
- `test_06_local_passage_not_authenticated_against_official_live_source`: Asserts `is_official_source_authenticated == False`.
- `test_07_abstention_trace_record_semantics`: Asserts `standard_number = None`, `content_hash = None`, and `WITHHELD_INSUFFICIENT_EVIDENCE`.
- `test_08_compound_requirement_incomplete_component`: Verifies subcomponent trace completeness.
- `test_09_api_serialization_preserves_unavailable_states`: Asserts API serialization preserves missing fields.
- `test_10_anti_falsification_guard_enforced`: Rejects illegal machine-to-human verification assertions.
- `test_11_whitespace_passage_does_not_pass_verification`: Verifies whitespace passages yield `content_hash = None`.

### 5.2 Test Execution Results
- `pytest tests/test_evidence_traceability.py tests/test_evidence_integrity_audit.py -v`: **21 passed** in 4.63s.
- `pytest tests/`: **589 passed** in 57.16s (100% offline, zero network egress, zero skipped).
- `npm run build --prefix frontend`: Built production bundle in 1.03s without warnings.
- `sha256sum dataset/ground_truth/ground_truth.csv`: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Unchanged).

---

## 6. Remaining Limitations & Evidence Prerequisites

1. **Clause-Level Normative Grounding**: The system verifies scope passages from `data/standards/standards.db`. It cannot ground recommendations against specific numbered clauses (e.g. Clause 5.3, Table 2 test criteria) because the full normative standard texts (PDFs) have not yet been parsed and stored into an indexable corpus.
2. **Human Adjudication Boundary**: All 20 benchmark ground-truth cases remain unverified by external domain experts (`is_human_verified = False`). Threshold calibration cannot proceed until qualified human engineers review the 41 generated adjudication packets.
3. **Database URL Uniformity**: 26 catalogue entries store citation strings in the `source_url` column. Ingesting full normative documents should separate `source_url` (web portal links) from `source_citation` (documentary/gazette citations).

---

## 7. Go / No-Go Decision for Normative Full-Text Ingestion

### Verdict: **GO**

**Rationale**:
1. All verification semantics are now clearly defined and strictly segregated.
2. Local catalogue scope verification is decoupled from live official authentication and human expert adjudication.
3. Deterministic regression suites (589 tests) pass completely offline.
4. The architecture is ready to ingest normative full-text PDF documents into `data/standards/corpus/` without risk of false verification claims.
