# Phase 33 Evaluation Report: Authoritative BIS Document Acquisition, Ingestion & Evidence-Grounded Cross-Reference Traversal

**Phase:** Phase 33  
**Repository:** `/home/syed-imadulla/Desktop/Tender_Saathi`  
**Branch:** `main`  
**Date:** October 19, 2026  
**Status:** COMPLETE & VERIFIED  

---

## Executive Summary

Phase 33 extended Tender Saathi's verified normative corpus coverage using authentic, publicly accessible Bureau of Indian Standards (BIS) documents from the official Indian Public Safety Codes repository. In addition, an evidence-grounded cross-reference traversal engine was designed and integrated, enabling bounded exploration of normative dependencies, test methods, and codes of practice directly from operative standard clauses without compromising safety invariants or fabricating unsupported recommendations.

Zero synthetic clauses, placeholder texts, or fabricated provenance were introduced. All frozen ground-truth benchmarks remain bit-for-bit invariant.

---

## 1. Baseline and Final Coverage Figures

### Database Inventory Comparison

| Metric | Phase 32 Baseline | Phase 33 Final | Delta / Method of Calculation |
|---|---|---|---|
| **National BIS Catalogue Records** | 35,208 | 35,208 | Unchanged (`bis_catalogue.db` catalogue_standards) |
| Active Catalogue Standards | 10,828 | 10,828 | Unchanged (`status = 'ACTIVE'`) |
| Withdrawn Catalogue Standards | 11,340 | 11,340 | Unchanged (`status = 'WITHDRAWN'`) |
| Unknown Lifecycle Catalogue Standards | 13,024 | 13,024 | Unchanged (`status = 'UNKNOWN'`) |
| Superseded Catalogue Standards | 16 | 16 | Unchanged (`status = 'SUPERSEDED'`) |
| **Curated Standards Records (`standards.db`)** | 96 | 98 | +2 (`IS-14846-2000`, `IS-800-2007` added; `IS-1239-(Part-2)-1992` updated with `2011` edition) |
| Active Curated Standards | 80 | 82 | +2 verified active standards |
| Withdrawn Curated Standards | 16 | 16 | Invariant (preserved for lifecycle warning checks) |
| **Corpus Documents (`corpus.db`)** | 8 | 11 | +3 authentic statutory gazette documents |
| **Corpus Passages (`corpus.db`)** | 31 | 44 | +13 verified normative passages with exact page & clause identifiers |
| Ground-Truth Checksum | `8bcc9bc5...` | `8bcc9bc5...` | SHA-256 bit-for-bit invariant |

### Real End-to-End Tender Coverage Impact

- **Pipe Fittings Coverage:** Bare and part-specific citations for mild steel tubular fittings now resolve to `IS 1239 (Part 2) : 2011` with grounded clauses (Clauses 1.1, 4.1, 7.1, 8.1) covering nominal dimensions (DN 6 to 150 mm), material standards, and hydrostatic testing (5 MPa).
- **Waterworks Valves Coverage:** Sluice valve specifications now ground directly to `IS 14846 : 2000` with authentic ratings (PN 1.0, PN 1.6), body casting materials (IS 210 Grade FG 200), and test pressures (seat test 1.0/1.6 MPa, body test 1.5/2.4 MPa).
- **Structural Steel Framing Coverage:** Industrial sheds, portal frames, trusses, and purlins now ground to `IS 800 : 2007` (Clauses 1.1, 2.2, 3.7, 10.1) without dangerous misrecommendations of concrete rebar (`IS 1786`).

---

## 2. Standards Attempted, Acquired, Ingested, and Blocked

| Standard Identifier | Title / Scope | Acquisition Source | SHA-256 Checksum | Ingestion Status | Outcome |
|---|---|---|---|---|---|
| **IS 1239 (Part 2) : 2011** | Mild Steel Tubes, Tubulars and Other Wrought Steel Fittings — Part 2: Mild Steel Tubulars and Other Wrought Steel Pipe Fittings (Fifth Revision) | Public Gazette / Archive.org | `f2b3d1dd35eb232b58762d1ef8161c3d3dc570f026947756b7840f33b53557ca` | `EXTRACTED` | **SUCCESSFULLY ACQUIRED & INGESTED** (4 passages) |
| **IS 14846 : 2000** | Sluice Valves for Water Works Purposes (50 to 1200 mm Size) — Specification (First Revision) | Public Gazette / Archive.org | `8bf2d8f924d773ec6877a0124431738198019dde287d5c1122779532f1ee9d03` | `EXTRACTED` | **SUCCESSFULLY ACQUIRED & INGESTED** (5 passages) |
| **IS 800 : 2007** | General Construction in Steel — Code of Practice (Third Revision) | Public Gazette / Archive.org | `fdb899a1a7c7a2bd75493a998abda11b5336b637c55302601cfaff7b88fb24df` | `EXTRACTED` | **SUCCESSFULLY ACQUIRED & INGESTED** (4 passages) |
| **IS 2062 : 2011** | Hot Rolled Medium and High Tensile Structural Steel — Specification | Official BIS Portal (Paywalled / Restricted) | N/A | `ACQUISITION_BLOCKED` | **BLOCKED (0 passages in corpus)** — Accurately surfaced as unacquired normative dependency |
| **IS 1538 : 1993** | Cast Iron Fittings for Pressure Pipes for Water, Gas and Sewage | Official BIS Portal (Paywalled / Restricted) | N/A | `ACQUISITION_BLOCKED` | **BLOCKED (0 passages in corpus)** — Surfaced as related flange standard for review |

---

## 3. Acquired Document Provenance & Verification Metadata

All acquired documents were verified under the statutory public domain doctrine governing Indian Public Safety Standards:

1. **`DOC-IS-1239-Part-2-2011`**:
   - Standard Number: `IS 1239 (Part 2)`
   - Edition Year: `2011` (Fifth Revision, Reaffirmed 2019)
   - Source URL: `https://archive.org/details/gov.in.is.1239.2.2011`
   - File SHA-256: `f2b3d1dd35eb232b58762d1ef8161c3d3dc570f026947756b7840f33b53557ca`
   - Licensing Status: `STATUTORY_PUBLIC_GAZETTE`
   - Ingestion Status: `EXTRACTED`
   - Document Title: `Mild Steel Tubes, Tubulars and Other Wrought Steel Fittings - Part 2: Mild Steel Tubulars and Other Wrought Steel Pipe Fittings (Fifth Revision)`

2. **`DOC-IS-14846-2000`**:
   - Standard Number: `IS 14846`
   - Edition Year: `2000` (First Revision, Reaffirmed 2021)
   - Source URL: `https://archive.org/details/gov.in.is.14846.2000`
   - File SHA-256: `8bf2d8f924d773ec6877a0124431738198019dde287d5c1122779532f1ee9d03`
   - Licensing Status: `STATUTORY_PUBLIC_GAZETTE`
   - Ingestion Status: `EXTRACTED`
   - Document Title: `Sluice Valves for Water Works Purposes (50 to 1200 mm Size) - Specification (First Revision)`

3. **`DOC-IS-800-2007`**:
   - Standard Number: `IS 800`
   - Edition Year: `2007` (Third Revision, Reaffirmed 2022)
   - Source URL: `https://archive.org/details/gov.in.is.800.2007`
   - File SHA-256: `fdb899a1a7c7a2bd75493a998abda11b5336b637c55302601cfaff7b88fb24df`
   - Licensing Status: `STATUTORY_PUBLIC_GAZETTE`
   - Ingestion Status: `EXTRACTED`
   - Document Title: `General Construction in Steel - Code of Practice (Third Revision)`

---

## 4. Ingested Passages and Extraction Quality

| Document ID | Clause Identifier | Page Range | Content Hash (SHA-256) | Verification Status | Normative Focus |
|---|---|---|---|---|---|
| `DOC-IS-1239-Part-2-2011` | `1.1` | Page 1 | `72c1c6867e10886c...` | `CLAUSE_IDENTIFIER_VERIFIED` | Scope (mild steel sockets, elbows, tees, unions DN 6 to 150 mm) |
| `DOC-IS-1239-Part-2-2011` | `4.1` | Page 3 | `d8beecbbf571cecf...` | `CLAUSE_IDENTIFIER_VERIFIED` | Material requirements & seamless/welded raw material |
| `DOC-IS-1239-Part-2-2011` | `7.1` | Page 5 | `432d6cebb2f0709b...` | `CLAUSE_IDENTIFIER_VERIFIED` | Nominal dimensions and pipe threads conforming to IS 554 |
| `DOC-IS-1239-Part-2-2011` | `8.1` | Page 8 | `15e47feeb922c262...` | `CLAUSE_IDENTIFIER_VERIFIED` | Hydrostatic pressure testing (5 MPa for 5 seconds without leakage) |
| `DOC-IS-14846-2000` | `1.1` | Page 1 | `f73449cb96f921ea...` | `CLAUSE_IDENTIFIER_VERIFIED` | Scope (non-rising and rising stem sluice valves DN 50 to 1200 mm) |
| `DOC-IS-14846-2000` | `4.1` | Page 2 | `a9f5d14338e553c6...` | `CLAUSE_IDENTIFIER_VERIFIED` | Nominal pressure ratings (PN 1.0 and PN 1.6) |
| `DOC-IS-14846-2000` | `6.1` | Page 4 | `d552cf3a669ff891...` | `CLAUSE_IDENTIFIER_VERIFIED` | Materials: Grey Iron FG 200 (IS 210), Bronze rings (IS 318) |
| `DOC-IS-14846-2000` | `7.1` | Page 6 | `6eefc43666d92550...` | `CLAUSE_IDENTIFIER_VERIFIED` | Flange dimensions and drilling conforming to IS 1538 |
| `DOC-IS-14846-2000` | `10.1` | Page 11 | `b78351b874452097...` | `CLAUSE_IDENTIFIER_VERIFIED` | Hydrostatic test pressures (body test 1.5/2.4 MPa, seat 1.0/1.6 MPa) |
| `DOC-IS-800-2007` | `1.1` | Page 1 | `470ffcd17afbb9e8...` | `CLAUSE_IDENTIFIER_VERIFIED` | Scope: Hot rolled steel framing, beams, columns, trusses, purlins |
| `DOC-IS-800-2007` | `2.2` | Page 11 | `c873f1361530e163...` | `CLAUSE_IDENTIFIER_VERIFIED` | Structural steel materials: E250, E300, E350 per IS 2062 |
| `DOC-IS-800-2007` | `3.7` | Page 17 | `9fc1bba77e6fa0f2...` | `CLAUSE_IDENTIFIER_VERIFIED` | Classification of cross-sections: Class 1 Plastic to Class 4 Slender |
| `DOC-IS-800-2007` | `10.1` | Page 73 | `1b1386d9b4db7d99...` | `CLAUSE_IDENTIFIER_VERIFIED` | Design of connections: Bolting (IS 1363/IS 1367), welding (IS 816) |

---

## 5. Cross-Reference Traversal Behavior and Provenance Preservation

### Traversal Architecture

The `StandardsGraph.traverse_cross_references` method provides bounded, evidence-grounded exploration:
1. **Starting Point:** Originates from an explicitly identified standard and its grounded clause (e.g. `IS 800` Clause `2.2`).
2. **Dual Evidence Sourcing:** Combines exact citations parsed from `corpus_passages` with verified edges in `standard_relationships`.
3. **Reference Typology:** Accurately separates `EXPLICIT_NORMATIVE`, `TEST_METHOD`, `CODE_OF_PRACTICE`, and `INFORMATIVE` references.
4. **Lifecycle & Currency Resolution:** Checks target status (`Active`, `Withdrawn`, `Superseded`) against `standards.db` and `bis_catalogue.db`.
5. **Contextual Relevance:** Flags whether tender requirement context specifically warrants the dependency (e.g. pipe thread specifications activating `IS 554`).
6. **Strict Bounded Depth:** Enforces `depth ∈ {1, 2}` with depth > 2 rejected by `ValueError`.
7. **Cycle Prevention:** Maintains visited canonical standard IDs and digit tokens, preventing infinite loops or self-references.
8. **Safety Preservation:** Discovered graph connections are labeled as `review_note="... for review"`. They are NEVER automatically upgraded to `CLAUSE_VERIFIED` unless authentic local clause evidence exists for that target standard.

### Traversal Examples

```python
# Traversal from IS 800 Clause 2.2 (Structural steel materials)
res = graph.traverse_cross_references("IS 800", grounded_clause="2.2", max_depth=1)
# Returns:
# - Target: IS-2062 | Type: NORMATIVE_REFERENCE | Clause: 2.2 | Lifecycle: Unknown | Active: False
#   Evidence: "Clause 2.2 specifies structural steel plates and sections to conform to IS 2062."
# - Target: IS-875-Part-1-1987 | Type: CODE_OF_PRACTICE | Clause: Clause 1.1.2 | Active: False
# - Target: IS-1893-Part-1-2016 | Type: CODE_OF_PRACTICE | Clause: Clause 1.1.2 | Active: True
```

```python
# Traversal from IS 14846 Clause 6.1 (Materials)
res = graph.traverse_cross_references("IS 14846", grounded_clause="6.1", max_depth=1)
# Returns:
# - Target: IS-210 | Type: NORMATIVE_REFERENCE | Clause: 6.1 | Evidence: Grey Iron FG 200
# - Target: IS-318 | Type: NORMATIVE_REFERENCE | Clause: 6.1 | Evidence: Bronze seat rings LTB 2
# - Target: IS-1538-1993 | Type: NORMATIVE_REFERENCE | Clause: Clause 7.1 | Evidence: Flange drilling
```

---

## 6. Verification and Test Results

All verification suites executed cleanly without failures or regressions:

1. **Phase 33 Dedicated Tests:**
   ```bash
   pytest tests/test_phase33_authoritative_acquisition.py -v
   # Result: 11 passed in 7.93s (Exit Code: 0)
   ```

2. **Phase 32 Grounding Tests:**
   ```bash
   pytest tests/test_phase32_multi_part_grounding.py -v
   # Result: 8 passed in 8.24s (Exit Code: 0)
   ```

3. **Complete Backend Test Suite:**
   ```bash
   pytest -q
   # Result: 778 passed in 173.71s (Exit Code: 0)
   ```

4. **Frontend Unit / Page Tests:**
   ```bash
   npx --prefix frontend vitest run
   # Result: 1 file passed, 9 tests passed in 383ms (Exit Code: 0)
   ```

5. **Production Frontend Build:**
   ```bash
   npm --prefix frontend run build
   # Result: Built in 2.73s (Exit Code: 0)
   ```

6. **Ground Truth Benchmark Integrity:**
   ```bash
   sha256sum dataset/ground_truth/ground_truth.csv
   # Result: 8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc (PASS)
   ```

7. **Knowledge Graph Synchronization:**
   ```bash
   graphify update .
   # Result: Rebuilt: 6,025 nodes, 11,318 edges, 337 communities (Exit Code: 0)
   ```

---

## 7. Remaining Risks & Unresolved Acquisition Blockers

1. **Paywalled / Non-Gazette Standards (`IS 2062`, `IS 1538`, `IS 318`):**
   - While `IS 800`, `IS 14846`, and `IS 1239 (Part 2)` cite `IS 2062` and `IS 1538`, authentic full-text PDFs for these referenced standards remain paywalled under BIS official sales portals.
   - **Mitigation:** In accordance with Tender Saathi's core invariants, these unacquired standards are retained in `relationships.json` as `NORMATIVE_REFERENCE` dependencies with `ACQUISITION_BLOCKED` provenance. They are never given synthetic passages and remain ineligible for `CLAUSE_VERIFIED` status until authenticated full texts are legitimately acquired.

2. **Multi-Part Numbering Variations:**
   - Some tender documents cite `IS 1239` without specifying `Part 1` or `Part 2`.
   - **Mitigation:** Disambiguation logic from Phase 32 reliably directs tube/pipe keywords to Part 1 and fitting/elbow/tee keywords to Part 2; ambiguous citations without keywords safely abstain to `CATALOGUE_DISCOVERED` with `human_review_required = True`.

---

## 8. Exact Files Changed and Reasons

| File Path | Nature of Change | Technical Reason |
|---|---|---|
| `scripts/ingest_normative_standards.py` | Extended | Ingested authentic documents, normative passages, database entries, and verified relationships for `IS 1239 (Part 2)`, `IS 14846`, and `IS 800`. |
| `src/graph.py` | Extended | Implemented `TraversedReference` dataclass and `StandardsGraph.traverse_cross_references` method with cycle prevention, depth bounding, and clause provenance preservation. |
| `src/dependencies.py` | Extended | Added `traversed_cross_references` field to `StandardsDependencyReport` and populated it during `analyze_dependencies`. |
| `src/ambiguity.py` | Hardened | Added Stage 1.5 discretionary specification guard to flag requirements deferring technical choices to field discretion ("as directed by site in-charge"). |
| `tests/test_phase33_authoritative_acquisition.py` | Created | Comprehensive 11-test deterministic regression suite verifying acquisition, ingestion, traversal, and safety gates. |
| `tests/test_phase32_multi_part_grounding.py` | Updated | Updated acquisition readiness assertion to recognize that IS 1239 Part 2 is now legitimately acquired, while unacquired sources (IS 2062) remain 0 passages. |
| `tests/test_phase30_corpus_expansion.py` | Updated | Updated document and passage count assertions to accommodate the 3 authentic Phase 33 documents. |
| `tests/test_phase31_evidence_integrity.py` | Updated | Updated document count and uningested blocker checks to reflect Phase 33 acquisitions. |
| `tests/test_targeted_normative_ingestion.py` | Updated | Added Phase 33 standard numbers to allowed corpus document list. |
| `tests/test_milestone9_applicability.py` | Hardened | Updated structural steel framing negative assertion to allow mapping to authoritative `IS 800 : 2007` while strictly maintaining rejection of concrete rebar (`IS 1786`). |
| `.planning/phases/33-authoritative-acquisition/33-CONTEXT.md` | Created | Baseline audit, database schemas, and acquisition strategy documentation. |
| `.planning/phases/33-authoritative-acquisition/33-PLAN.md` | Created | Phase 33 execution plan and milestone task breakdown. |
| `.planning/phases/33-authoritative-acquisition/33-UAT.md` | Created | User Acceptance Testing verification log. |
| `docs/evaluation/PHASE33_AUTHORITATIVE_ACQUISITION_REPORT.md` | Created | Detailed Phase 33 evaluation report. |
| `.planning/STATE.md` | Updated | Recorded completion of Phase 33. |
