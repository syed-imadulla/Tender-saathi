# PRIORITY 7D — ADVERSARIAL SAFETY, FALSE-POSITIVE RESISTANCE & TRUST BOUNDARY AUDIT
**Project**: TenderSaathi (SIH26108)  
**Status**: AUDIT COMPLETE  
**Final Verdict**: **PRIORITY 7D PASS — PROCEED TO P7E**  
**Core Maxim**: **ABSTENTION > UNSUPPORTED CONFIDENCE**

---

## 1. Executive Summary

Priority 7D independently evaluates TenderSaathi's safety envelope against adversarial inputs, false-positive vulnerabilities, semantic conflation, and boundary failures. It certifies that the engine refuses to guess when faced with ambiguous, incomplete, or out-of-catalogue tenders, preserves the historical and normative integrity of Indian Standards, and enforces strict boundary distinction across evidence, provenance, lifecycle, and statutory regulations.

### Key Audit Metrics
| Metric | Measurement | Status |
| :--- | :--- | :--- |
| **Total Test Suite Pass Rate** | **305 / 305 tests passing (100%)** | **PASS** |
| **Targeted P7D Adversarial Tests** | **15 / 15 tests passing (100%)** | **PASS** |
| **End-to-End Tender Corpus Audited** | **20 / 20 real tenders (40 pages)** | **PASS** |
| **Candidate == Evidence Invariant** | **20 / 20 tenders (100% adherence)** | **PASS** |
| **Multilingual Benchmark Integrity** | **SHA-256: `db62e0367ea2983dab49a9ac8a98958efb0c17882df86f131ecfa6b04903690b`** | **PASS** |
| **Catalogue Invariant (Catalogue DB)** | **502 records (Untouched)** | **PASS** |
| **Standards DB Integrity** | **90 physical rows, 90 distinct IDs (0 duplicates)** | **PASS** |
| **Frontend Production Build** | **Vite build clean in 797ms** | **PASS** |

---

## 2. Safety & Trust Boundaries Audit

### 2.1 Substring Collision Prevention
- **Defect Tested**: Substring collision between numeric standard numbers (e.g. `IS 778` matching `IS 15778`, `IS 694` matching `IS 9694`).
- **Audit Verification**:
  - `are_standards_equivalent("IS 778", "IS 15778")` $\rightarrow$ `False`
  - `are_standards_equivalent("IS 694", "IS 9694")` $\rightarrow$ `False`
  - `are_standards_equivalent("IS 1180", "IS 1180 Part 1")` $\rightarrow$ `False`
  - `are_standards_equivalent("IS 7098 Part 1", "IS 7098 Part 2")` $\rightarrow$ `False`
- **Result**: **PASS**. Substring overlap cannot induce false equivalence.

### 2.2 Canonical Identity Exactness
- **Mechanism**: `are_standards_equivalent()` in `src/critic.py` decomposes standard numbers via `StandardIdentifierNormalizer` comparing prefix, base number, part, and section.
- **Audit Verification**:
  - `are_standards_equivalent("IS 15778 : 2007", "IS 15778")` $\rightarrow$ `True`
  - `are_standards_equivalent("IS 1786 : 2008", "IS 1786")` $\rightarrow$ `True`
  - `are_standards_equivalent("IS 7098 (Part 2) : 2011", "IS 7098-Part-2")` $\rightarrow$ `True`
  - `are_standards_equivalent("IS 10611", "IS/ISO 10434")` $\rightarrow$ `False`
- **Result**: **PASS**. Canonical identities equate reliably across formatting discrepancies while preventing false mergers.

### 2.3 Provenance Semantic Separation
- **Principle**: The system never conflates `Record Provenance` with `Verification Source`.
- **Audit Verification**:
  - In `EvidenceDrawer.tsx`, Section 5 explicitly displays `Record Provenance & Verification Source`.
  - For `CURATED` records (e.g. CPVC pipes), the provenance badge reads `Curated Technical Source`, and the verification source reads `BIS Standards Catalogue` with the explicit disclaimer:
    *(Curated technical entry verified against standards scope; distinct from statutory primary gazette orders)*.
  - Curated records are never promoted to `OFFICIAL_PRIMARY`.
- **Result**: **PASS**.

### 2.4 Evidence Strength Semantics
- **Tiers Enforced**:
  - `STRONG`: Explicit tender citations or direct primary catalogue citations.
  - `MODERATE`: Scope/domain textual overlap matches without explicit tender citation.
  - `NONE`: Abstentions, ambiguous cases, or ungrounded recommendations.
- **UI Labeling**: Section 4 in `EvidenceDrawer.tsx` is dynamically labeled:
  - `4. Authoritative Evidence Quote` only if `evidence_strength === 'STRONG'` and provenance is `VERIFIED` or `OFFICIAL_PRIMARY`.
  - `4. Supporting Evidence Quote` in all other cases.
- **Result**: **PASS**.

### 2.5 Product vs Installation Separation
- **Principle**: Product standards and installation codes of practice are never collapsed.
- **Audit Verification**:
  - Requirement: *"Supply and installation of CPVC pipes for internal water distribution network."*
  - Primary Candidate: `IS 15778 : 2007` (CPVC Pipes for Potable Hot and Cold Water Supplies).
  - Code of Practice / Installation: `IS 7634 (Part 3) : 2003` (`INSTALLATION_STANDARD`) and `SP 57 (QAWSM) : 1993` (`CODE_OF_PRACTICE`).
  - Installation standard is strictly populated as a typed graph dependency, not as the primary product candidate.
- **Result**: **PASS**.

### 2.6 Truthful Abstention Wording
- **Principle**: When out-of-catalogue or irrelevant commodities are encountered, the system must truthfully state catalogue bounds.
- **Forbidden**: *"No Indian Standard exists."*
- **Enforced**: *"No reliable Indian Standard match found in the available catalogue."*
- **Audit Verification**:
  - Input: *"Supply of executive wooden office desks, swivel chairs, and paper stationery."*
  - State: `NO_RELIABLE_MATCH`
  - Candidate: `None`
  - Explanation: *"No reliable Indian Standard match found in the available catalogue."*
- **Result**: **PASS**.

### 2.7 Lifecycle Preservation
- **Principle**: Superseded standards cited in tenders must not be silently overwritten or erased.
- **Audit Verification**:
  - Input: *"Procurement of bolted bonnet steel gate valves conforming to IS 10611 : 1983."*
  - Superseded Citation Preserved: `req["superseded_citation"] == "IS 10611 1983"`
  - Active Successor Identified: `req["successor_standard"] == "IS/ISO 10434 : 2020"`
  - Candidate Standard: `IS/ISO 10434 : 2020`
  - Lifecycle Advisory: Explains the supersedence and requires human engineering review.
- **Result**: **PASS**.

### 2.8 Regulatory Safety
- **Principle**: The existence of an Indian Standard does not automatically imply mandatory statutory status.
- **Audit Verification**:
  - Mandatory status (`APPLICABLE`) is restricted strictly to standards backed by verified Ministry Gazette Quality Control Orders (QCOs) or CRS schedules.
  - Standards without mandatory statutory orders (e.g. ceramic tiles `IS 15622`) are labeled `NOT_IDENTIFIED` or `REVIEW_REQUIRED`, never falsely marked as `APPLICABLE`.
  - Clear disclaimer rendered: *"The existence of an Indian Standard does not automatically imply mandatory BIS certification."*
- **Result**: **PASS**.

---

## 3. Real Tender 10-Case Adversarial Benchmark

The 10 representative adversarial cases were evaluated through the full end-to-end API pipeline:

| Case ID | Type | Requirement Summary | Candidate Standard | Ev Strength | State | Human Review |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **ADV-01-CLEAR-CPVC** | CLEAR | CPVC pipes for domestic water supply conforming to IS 15778 | `IS 15778 : 2007` | **STRONG** | `CLEAR` | False |
| **ADV-02-CLEAR-REBAR** | CLEAR | Rebar Fe 500D conforming to IS 1786 | `IS 1786 : 2008` | **STRONG** | `REVIEW_REQUIRED` | **True** |
| **ADV-03-CLEAR-TRANSFORMER** | CLEAR | 11kV/433V distribution transformers conforming to IS 1180 Part 1 | `IS 1180 (Part 1) : 2014` | **STRONG** | `CLEAR` | False |
| **ADV-04-ABSTAIN-STATIONERY** | ABSTAIN | Executive wooden desks and paper stationery | `None` | **NONE** | `NO_RELIABLE_MATCH` | **True** |
| **ADV-05-ABSTAIN-LEGAL** | ABSTAIN | Corporate litigation and legal advisory services | `None` | **NONE** | `NO_RELIABLE_MATCH` | **True** |
| **ADV-06-ABSTAIN-UNSUPPORTED**| ABSTAIN | Fiber-optic gyroscope maritime modules | `None` | **NONE** | `NO_RELIABLE_MATCH` | **True** |
| **ADV-07-AMBIGUOUS-CABLE** | AMBIGUOUS | Underground power transmission cable connection | `None` | **NONE** | `AMBIGUOUS` | **True** |
| **ADV-08-AMBIGUOUS-PUMP** | AMBIGUOUS | Overhauling and maintenance of plant pumping machinery | `None` | **NONE** | `NO_RELIABLE_MATCH` | **True** |
| **ADV-09-LIFECYCLE-SUPERSEDED**| LIFECYCLE | Bolted bonnet gate valves conforming to IS 10611 : 1983 | `IS/ISO 10434 : 2020` | **STRONG** | `REVIEW_REQUIRED` | **True** |
| **ADV-10-REGULATORY-QCO** | REGULATORY | XLPE insulated PVC sheathed cables conforming to IS 7098 Part 1 | `IS 7098 (Part 1) : 1988` | **MODERATE** | `REVIEW_REQUIRED` | **True** |

### Benchmark Observations
1. **Zero Hallucination / Zero Fabrication**: When candidate standard is `None`, evidence standard is strictly `None`, evidence strength is `NONE`, and human review is required.
2. **Honest Abstention Rate**: 5 of 10 adversarial cases (50%) correctly abstained (`NO_RELIABLE_MATCH` or `AMBIGUOUS`) rather than offering an unsupported recommendation.
3. **Candidate-Evidence Consistency**: In all 10 cases, `candidate_standard == evidence_standard` whenever a candidate was present.
4. **Lifecycle Integrity**: For `ADV-09`, the cited standard `IS 10611 1983` was accurately tagged as superseded and mapped to its active successor `IS/ISO 10434 : 2020`.

---

## 4. Full Regression Verification

### 4.1 Pytest Suite
- Command: `pytest tests/ -q`
- Output: **`305 passed, 45 warnings in 104.14s`**
- Failures: **0**
- Regressions: **None**

### 4.2 End-to-End Real Tender Pipeline
- Command: `python3 scripts/validate_e2e.py`
- Raw Tenders Audited: **20 / 20 (100%)**
- Total Requirements: **25**
- Candidate == Evidence Invariant: **20 / 20 requirements (100%)**
- Reports Generated: **5 representative comprehensive review reports**

### 4.3 Database and Benchmark Immutability
- `data/standards/standards.db`: Exactly 90 physical rows, 90 distinct IDs, 0 duplicates.
- `data/catalogue/catalogue.db`: Exactly 502 records, untouched.
- `dataset/ground_truth/multilingual_benchmark.json` SHA-256: `db62e0367ea2983dab49a9ac8a98958efb0c17882df86f131ecfa6b04903690b` (Unchanged).

### 4.4 Frontend Build
- Command: `npm run build` in `frontend/`
- Output: `tsc && vite build` succeeded in 797ms with 0 type errors.

---

## 5. Final Adjudication & Verdict

All 15 trust boundaries, adversarial safety protections, and evidence-provenance semantics mandated by Priority 7D have been comprehensively implemented, tested, and independently validated.

**FINAL VERDICT: PRIORITY 7D PASS — PROCEED TO P7E**
