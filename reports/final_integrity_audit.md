# TenderSaathi — Final Integrity Audit Report
**Audit Timestamp:** 2026-09-11T18:19:12.050728  
**Evaluation As-Of Date:** 2026-09-11  
**Audit Scope:** Full forensic evaluation of Priority 3 (Expanded Standards Catalogue) and Priority 4 (Regulatory Subsystem)

---

## Executive Audit Summary & Verdict Matrix

| # | Audit Area | Verdict | Summary Finding |
|---|---|---|---|
| 1 | **Catalogue Count & Identifiers** | **FAIL** | 486 valid authentic records. **15 records malformed** (`IS--`) due to normalizer regex parsing bug erasing 1900–2099 standard numbers. |
| 2 | **Provenance Claims** | **FAIL** | Claim of '100% OFFICIAL_PRIMARY' was an **overstatement**. Actual: 173 Primary (34.5%), 270 Secondary (53.9%), 52 Curated (10.4%), 6 Verified (1.2%). |
| 3 | **Lifecycle Status Claims** | **WARNING** | 7 SUPERSEDED and 10 WITHDRAWN have explicit evidence. 270 CPWD standards have ACTIVE status assumed from CPWD schedule adoption, not live BIS certificates. |
| 4 | **Regulatory QCO Evaluation** | **PASS** | 8 verified gazette orders. Deterministic temporal logic cleanly separates 7 CURRENT from 1 UPCOMING order as of 2026-09-11. |
| 5 | **Regulatory CRS Evaluation** | **PASS** | 10 product categories mapped to MeitY/MNRE orders. Enforces rule: generic 'electronics' strictly rejected from triggering CRS. |
| 6 | **Regulatory Hallmarking** | **PASS** | Gold $\rightarrow$ APPLICABLE (HUID); Silver $\rightarrow$ REVIEW_REQUIRED; Non-precious goods $\rightarrow$ NOT_APPLICABLE; Ambiguous $\rightarrow$ UNKNOWN. |
| 7 | **Zero-LLM Determinism** | **PASS** | `src/regulatory/` contains 0 LLM calls, 0 prompt strings, and 0 external AI dependencies. 100% deterministic rule/gazette execution. |
| 8 | **Candidate vs Evidence Standard** | **FAIL** | `candidate_standard == evidence_standard` evaluates to **False**. Year is duplicated in candidate (`IS 15778 : 2007 : 2007`) or omitted in evidence. |
| 9 | **50-Query Benchmark** | **WARNING** | Real-world queries, but `catalogue_benchmark_50.json` metadata incorrectly claimed 39 items were in baseline when only 9 were actually present. |
| 10 | **Regression Test Suite** | **PASS** | All 185 tests (167 baseline + 18 new) passed in 52.2s. Zero regressions against baseline. |

---

## 1. Deep Catalogue Audit (`data/catalogue/catalogue.db`)

### Exact Record Counts
- **Total Records in Database:** **501**
- **Valid Canonical IDs:** **486** (97.0%)
- **Malformed Canonical IDs:** **15** (3.0%)
- **Duplicate Canonical IDs:** **0**
- **Duplicate (Base Standard + Year) Combinations:** **0**
- **Missing Titles:** **0**
- **Missing Scopes:** **0**
- **Missing Publication Years:** **2** (`IS-2556`, `IS-4` — inherited from baseline 85 standards)
- **Invalid Future Publication Years (>2026):** **4** (part of the 15 malformed records: `2062`, `2099`, `2074`, `2089`)
- **Missing Source URLs:** **0**
- **Generic Homepage Source URLs (`standardsbis.bsbedge.com`):** **469**
- **Deep Query Source URLs:** **32**

### Root Cause Analysis of the 15 Malformed Records
In `src/catalogue/normalizer.py`, `StandardIdentifierNormalizer.parse()` applied the year extraction pattern:
```python
YEAR_PATTERN = re.compile(r'\b(19\d\d|20\d\d)\b')
```
across the raw standard string *before* extracting the base standard number. When given genuine Indian Standards whose base designation falls in the range 1900–2099 (e.g. `IS 2062 : 2011`, `IS 2016 : 1967`, `IS 1904 : 1986`, `IS 2026 Part 1 : 2011`), the parser:
1. Mistook the standard number (`2062`, `2016`, `1904`, `2026`) for the publication year.
2. Stripped all 4-digit numbers from the remainder, erasing both the standard number and the actual year.
3. Constructed an empty base number, generating `canonical_id = "IS--2062"` and `standard_number = "IS  : 2062"`.

#### Table of All 15 Malformed Records
| Malformed ID | Malformed Standard Number | Erroneously Stored Year | Authentic Indian Standard | Authentic Year | Authentic Standard Title |
|---|---|---|---|---|---|
| `IS--2062` | `IS  : 2062` | 2062 | `IS 2062` | 2011 | Hot Rolled Medium and High Tensile Structural Steel |
| `IS--2016` | `IS  : 2016` | 2016 | `IS 2016` | 1967 | Specification for Plain Washers |
| `IS--1905` | `IS  : 1905` | 1905 | `IS 1905` | 1987 | Code of Practice for Structural Use of Unreinforced Masonry |
| `IS--Part-1-2026` | `IS  (Part 1) : 2026` | 2026 | `IS 2026 (Part 1)` | 2011 | Power Transformers - Part 1: General |
| `IS--Part-2-2026` | `IS  (Part 2) : 2026` | 2026 | `IS 2026 (Part 2)` | 2010 | Power Transformers - Part 2: Temperature Rise |
| `IS--Part-3-2026` | `IS  (Part 3) : 2026` | 2026 | `IS 2026 (Part 3)` | 2009 | Power Transformers - Part 3: Insulation Levels |
| `IS--Part-5-2026` | `IS  (Part 5) : 2026` | 2026 | `IS 2026 (Part 5)` | 2011 | Power Transformers - Part 5: Short Circuit Withstand |
| `IS--1948` | `IS  : 1948` | 1948 | `IS 1948` | 1961 | Specification for Aluminium Doors, Windows and Ventilators |
| `IS--2004` | `IS  : 2004` | 2004 | `IS 2004` | 1991 | Carbon Steel Forgings for General Engineering Purposes |
| `IS--1904` | `IS  : 1904` | 1904 | `IS 1904` | 1986 | Code of Practice for Design and Construction of Foundations in Soils |
| `IS--2099` | `IS  : 2099` | 2099 | `IS 2099` | 1986 | Specification for Bushings for Alternating Voltages Above 1000 V |
| `IS--2074` | `IS  : 2074` | 2074 | `IS 2074` | 1992 | Ready Mixed Paint, Air Drying, Red Oxide-Zinc Chrome Priming |
| `IS--2089` | `IS  : 2089` | 2089 | `IS 2089` | 1977 | Specification for Common Proofed Tarpaulins (Fabric-Cotton Duck) |
| `IS--1978` | `IS  : 1978` | 1978 | `IS 1978` | 1982 | Specification for Line Pipe |
| `IS--1979` | `IS  : 1979` | 1979 | `IS 1979` | 1985 | Specification for High Test Line Pipe |

> **Audit Recommendation:** Per user rule #6 ("DO NOT repair malformed records automatically. First produce an audit report"), these 15 records are reported here without silent in-place overwrite. They must either be quarantined or corrected with an authoritative rebuild script following user approval.

---

## 2. Provenance Hierarchy Audit (Audit of the '100% Primary' Claim)

The claim in the previous turn that the catalogue achieved **'100% OFFICIAL_PRIMARY'** provenance was a **demonstrable overstatement**.

### Verified Provenance Distribution:
- **`OFFICIAL_PRIMARY`**: **173 records** (34.5%)
  - GOI Ministry QCO Gazettes: 145 records
  - BIS Compulsory Registration Scheme (CRS) Registry: 23 records
  - BIS Hallmarking Registry: 5 records
- **`OFFICIAL_SECONDARY`**: **270 records** (53.9%)
  - CPWD Official Specifications (Volume 1 & 2 civil, electrical, sanitary schedules citing Indian Standards).
- **`CURATED`**: **52 records** (10.4%)
  - Inherited from the baseline 85 standards prototype catalogue.
- **`VERIFIED`**: **6 records** (1.2%)
  - Directly verified against live BSB Edge search queries during early prototype milestones.

**Verdict: FAIL (Overstatement Identified)**  
Only 34.5% of records have primary statutory gazette provenance. The remaining 65.5% are authentic government specifications (CPWD) or curated prototype standards.

---

## 3. Lifecycle Status & Supersession Audit

- **`ACTIVE` Standards:** 484
- **`SUPERSEDED` Standards:** 7
- **`WITHDRAWN` Standards:** 10

### Supersession Evidence:
All 7 `SUPERSEDED` standards have explicit, verifiable successor standards populated in `superseded_by_json`:
1. `IS 13753 : 1993` $\rightarrow$ superseded by `IS 15622` (Ceramic Tiles)
2. `IS 13755 : 1993` $\rightarrow$ superseded by `IS 15622` (Ceramic Tiles)
3. `IS 8623 (Part 1) : 1993` $\rightarrow$ superseded by `IS/IEC 61439-1` (Switchgear Assemblies)
4. `IS 8623 (Part 3) : 1993` $\rightarrow$ superseded by `IS/IEC 61439-3` (Distribution Boards)
5. `IS 13947 (Part 1) : 1993` $\rightarrow$ superseded by `IS/IEC 60947-1` (Low Voltage Switchgear)
6. `IS 13947 (Part 2) : 1993` $\rightarrow$ superseded by `IS/IEC 60947-2` (Circuit Breakers)
7. `IS 10611 : 1983` $\rightarrow$ superseded by `IS 778` (Waterworks Valves)

### Unsupported Lifecycle Claims:
For the 270 CPWD standards, their `ACTIVE` status was assigned because they are currently cited in published CPWD specifications. However, this is **secondary adoption evidence**, not a direct query of the live BIS Standards Portal reaffirmation certificates.

**Verdict: WARNING**

---

## 4. 50-Query Benchmark Audit

### Metadata Inconsistency
In `dataset/ground_truth/catalogue_benchmark_50.json`, the field `"in_85_baseline": true` was marked on **39 items**.
However, an audit against `data/standards/standards.db` reveals:
- **Standards actually in 85 DB:** **9**
- **Standards claimed in baseline but missing from DB:** **30**
- **Actual Baseline Catalogue Coverage:** **18.4%** (9 / 49 standard queries).

*Note: The benchmarking script (`scripts/evaluate_catalogue_expansion.py`) dynamically queried SQLite and reported the true 18.4% coverage, but the benchmark JSON file contained misleading metadata.*

### Circularity & Leakage Assessment
- The 50 benchmark queries represent authentic engineering tender phrasing.
- However, some queries closely mirror standard titles (e.g. BENCH-08 quotes *"Hot rolled medium and high tensile structural steel plates and beams grade E 250 quality A"*).
- Because `IS 2062` was malformed as `IS  : 2062` in the catalogue, the expanded catalogue actually failed to match BENCH-08, proving that the evaluation script was not artificially rigged to bypass catalogue flaws.

**Verdict: WARNING (Metadata Mismatch in JSON)**

---

## 5. Regulatory Subsystem Forensic Audit

### A. Quality Control Orders (QCO)
Audit of `data/regulatory/qco/qco_master.json`:
- **Total Orders:** 8
- **CURRENT Orders (as of 2026-09-11):** **7**
  1. CPVC Pipes & Fittings Order, 2024 (S.O. 1205(E), effective 2024-08-25)
  2. Valves Order, 2024 (S.O. 2682(E), effective 2024-06-19)
  3. Steel and Steel Products Order, 2024 (S.O. 325(E), effective 2024-02-01)
  4. Cement Order, 2024 (S.O. 4531(E), effective 2024-11-20)
  5. Wires and Cables Order, 2023 (S.O. 4114(E), effective 2024-03-21)
  6. Electric Motors Order, 2024 (S.O. 2489(E), effective 2024-08-15)
  7. Pipes and Fittings (uPVC/HDPE) Order, 2024 (S.O. 1206(E), effective 2024-08-25)
- **UPCOMING Orders (as of 2026-09-11):** **1**
  1. Smart Meters Order, 2026 (S.O. 4812(E), notified 2026-06-15, effective 2027-04-01)
- **Traceability:** Every order has gazette notification number, notifying ministry, legal basis (Section 16, BIS Act), and e-Gazette PDF reference.
- **Verdict: PASS**

### B. Compulsory Registration Scheme (CRS)
Audit of `data/regulatory/crs/crs_master.json`:
- **Total Product Categories:** 10 (Laptops, POS Terminals, Printers, Lithium Batteries, LED Luminaires, Self-ballasted lamps, LED Drivers, UPS, Smart Watches, Solar PV modules).
- **Enforcement Rule:** The word "electronics" alone returns `NOT_IDENTIFIED` with human review flagged. Requires specific category keyword or standard match.
- **Verdict: PASS**

### C. Hallmarking Intelligence
Audit of `data/regulatory/hallmarking/hallmarking_master.json`:
- **Gold Jewellery / Artefacts:** `APPLICABLE` (Mandatory under S.O. 204(E) with HUID requirement).
- **Silver Jewellery / Artefacts:** `REVIEW_REQUIRED` (Voluntary under 2018 Regulations).
- **Incompatible Domains (cables, pipes, valves, cement, motors, etc.):** `NOT_APPLICABLE`.
- **Ambiguous Precious Items:** `UNKNOWN`.
- **Verdict: PASS**

### D. Zero-LLM Determinism
- Code inspection confirms that `src/regulatory/` makes **zero API calls to Groq, OpenRouter, or any LLM**.
- All decisions are 100% deterministic rule/gazette evaluations.
- **Verdict: PASS**

---

## 6. Candidate Standard vs Evidence Standard Identity Audit

Item 15 of user request: *"Verify candidate_standard == evidence_standard for every recommendation."*

### Audit Findings:
Testing across standard queries revealed that `candidate_standard == evidence_standard` is **`False`**:
1. In `src/recommend.py` line 419:
   ```python
   standard_number = f"{sr.standard_number} : {sr.year}" if sr.year else sr.standard_number
   ```
   In the expanded catalogue, `standards.standard_number` already contained `: 2007`, so this logic produced:
   `candidate_standard = "IS 15778 : 2007 : 2007"`.
2. Meanwhile, `evidence_standard` was extracted from the critic evidence object without the duplicate year:
   `evidence_standard = "IS 15778 : 2007"`.
3. In the baseline database:
   `candidate_standard = "IS 15778 : 2007"`, while `evidence_standard = "IS 15778"`.

While `are_standards_equivalent(candidate, evidence)` returns `True` (because it normalizes both), strict string identity `candidate_standard == evidence_standard` fails.

**Verdict: FAIL**

---

## 7. Regression Test Suite Audit

Running `pytest --tb=short` on the workspace:
- **Total Tests Collected:** 185
- **Tests Passed:** **185**
- **Tests Failed:** **0**
- **Execution Time:** 52.20s
- **Baseline Test Preservation:** All 167 original tests pass with 0 modifications to `data/standards/standards.db`.
- **Verdict: PASS**

---

## 8. Final Audit Recommendations

1. **Quarantine or Correct the 15 Malformed Records:**  
   Update `StandardIdentifierNormalizer.parse` to extract base numbers *before* year stripping, and regenerate `data/catalogue/catalogue.db` with the corrected 15 records (`IS 2062`, `IS 2016`, `IS 1904`, `IS 1905`, `IS 2026`, etc.).
2. **Correct Provenance Reporting:**  
   Report the honest provenance breakdown: 34.5% `OFFICIAL_PRIMARY`, 53.9% `OFFICIAL_SECONDARY` (CPWD), 10.4% `CURATED`, 1.2% `VERIFIED`. Never claim "100% primary".
3. **Fix String Identity in Recommender:**  
   Ensure `StandardRecommendation.standard_number` avoids double-appending the year if it is already present, and ensure `evidence_standard` canonicalization aligns identically with `candidate_standard`.
4. **Update Benchmark Metadata:**  
   Fix `"in_85_baseline": false` for the 30 requirements in `catalogue_benchmark_50.json` that are not present in the 85-standard database.
