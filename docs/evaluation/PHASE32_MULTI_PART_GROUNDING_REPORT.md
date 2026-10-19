# Phase 32 — Multi-Part Standard Grounding & Physical Source Acquisition Readiness Report

**Repository:** `Tender_Saathi`  
**Branch:** `main`  
**Execution Date:** 2026-10-19  
**Phase Status:** Complete  

---

## 1. Baseline and Final Coverage Figures

Recomputed directly via SQLite queries on active databases:

| Dimension | Initial Baseline (Phase 31) | Post-Phase 32 Baseline | Discrepancies / Notes |
|---|---|---|---|
| **National BIS Catalogue** (`bis_catalogue.db`) | 35,208 total records<br>10,828 confirmed `ACTIVE`<br>11,340 `WITHDRAWN`<br>13,024 `UNKNOWN`<br>16 `SUPERSEDED` | 35,208 total records<br>10,828 confirmed `ACTIVE`<br>11,340 `WITHDRAWN`<br>13,024 `UNKNOWN`<br>16 `SUPERSEDED` | Identical; no unverified record inflation. |
| **Active Catalogue Gap** | 10,824 standards (10,828 active - 4 active in corpus) | 10,824 standards (10,828 active - 4 active in corpus) | Stable; standards with `UNKNOWN` portal tags (e.g. IS 456, IS 1786, IS 1239 Part 1) are active in real world but tagged UNKNOWN in raw catalogue dump. |
| **Curated Standards Repository** (`standards.db`) | 96 total records<br>80 active<br>16 withdrawn<br>7 active with corpus passages | 96 total records<br>80 active<br>16 withdrawn<br>7 active with corpus passages | Zero synthetic records added. |
| **Curated Evidence Gap** | 73 active standards awaiting normative passages (80 - 7) | 73 active standards awaiting normative passages (80 - 7) | Maintained without synthetic text injection. |
| **Normative Evidence Corpus** (`corpus.db`) | 8 documents<br>31 normative passages | 8 documents<br>31 normative passages | Verified integrity; no fabricated passages for IS 1239 Part 2 or IS 2062. |
| **Catalogue Search Index** (`catalogue_search_index.db`) | 10,828 records | 10,828 records | 100% synchronized with active BIS catalogue records. |

---

## 2. Exact Files Changed and Reasons

1. `src/extract.py`:
   - **Reason**: Standard extraction regex failed to recognize multi-part standards where `Part` or `Section` was specified without spaces, or with complex prefixes (`IS/ISO`, `IS/IEC`, `SP`).
   - **Change**: Upgraded `STANDARD_REGEX` and routed `normalize_standard_mention` through `StandardIdentifierNormalizer.parse` to produce canonical standard identifiers.
2. `src/recommend.py`:
   - **Reason**: Bare citations to multi-part standards (e.g. `IS 1239`, `IS 7098`, `IS 1489`) arbitrarily picked a single part or misdirected tube citations to Part 2 (fittings). In compound decomposition, component recommendations matched Part 2 on tube mentions due to series title overlap. Withdrawn standards citations generated generic messages without explicitly naming the catalogue status.
   - **Change**:
     - Hardened multi-part disambiguation logic: checks for discriminating keywords (`tubes`/`pipes` -> Part 1; `fittings`/`elbows` -> Part 2; `LT`/`1.1 kV` -> Part 1; `HT`/`11 kV` -> Part 2; `fly ash` -> Part 1; `clay` -> Part 2).
     - Bare multi-part citations without discriminating context flag `AMBIGUOUS_MULTI_PART_CITATION` and enforce `human_review_required=True`.
     - In `_evaluate_component_recommendations`, added keyword guards ensuring Part 2 cannot match tube requirements, and deduplicated identical standards across overlapping component spans.
     - Hardened user-facing explanations for superseded/withdrawn standards: explicitly surfaces `Standard {std} has status '{status}' in the national BIS catalogue.`.
3. `src/corpus/retriever.py`:
   - **Reason**: Ceiling dimensional scope limits ("up to and including X mm") were not parsed, allowing out-of-scope sizes to pass boundary checks.
   - **Change**: Added ceiling regex matching (`\bup\s+to\s+(?:and\s+including\s+)?(\d+)\s*mm\b`). If a tender specifies a size exceeding this ceiling (e.g. 400 mm for `IS 1239 (Part 1)` which caps at 150 mm), it is marked `UNSUPPORTED`.
4. `tests/test_phase32_multi_part_grounding.py`:
   - **Reason**: Dedicated regression test suite implementing the 7 representative fixtures and the source acquisition integrity invariant.
5. `.planning/phases/32-multi-part-grounding/32-CONTEXT.md` & `32-PLAN.md` & `32-UAT.md`:
   - **Reason**: GSD phase documentation recording context, execution plan, and acceptance testing.

---

## 3. Multi-Part and Cross-Reference Improvements

- **Canonical Identity Preservation**: Exact part numbers, sections, and reaffirmation dates are preserved from raw tender text into canonical recommendation objects.
- **Cross-Match Prevention**: Strict separation ensures `IS 1239 (Part 1)` (tubes) and `IS 1239 (Part 2)` (fittings) are never conflated or cross-matched.
- **Ambiguity Abstention**: If a tender mentions `IS 1239` without specifying whether it seeks tubes or fittings, the system abstains from `CLAUSE_VERIFIED` and requests engineering clarification with the reason `AMBIGUOUS_MULTI_PART_CITATION`.
- **Component Evidence Isolation**: Compound requirements citing multiple standards (e.g. `IS 1239 (Part 1)` tubes and `IS 14846` sluice valves) isolate evidence per component bundle without cross-contaminating normative passages.

---

## 4. Source Acquisition Findings & Unresolved Blockers

A strict audit of physical sources was performed for `IS 1239 (Part 2)` and `IS 2062`:

- **Audit Findings**:
  - Neither `IS 1239 (Part 2)` nor `IS 2062` exists as a local PDF document on the filesystem.
  - In `data/standards/corpus.db`, exactly 0 passages exist for either standard.
  - In `data/catalogue/bis_catalogue.db`:
    - `IS 2062:2011` is officially marked `WITHDRAWN`.
    - Successor multi-part standards `IS 2062 (Part 1) : 2025` and `IS 2062 (Part 2) : 2026` have `UNKNOWN` lifecycle status in the portal scrape.
    - `IS 1239 (Part 2) : 1992` is marked `ACTIVE` (Reaffirmed 2019).
- **Blocker Status**:
  - **BLOCKER RETAINED**: In accordance with Phase 32 safety invariants, zero synthetic clauses, simulated hashes, or unverified secondary summaries were created.
  - Both standards remain purely `CATALOGUE_DISCOVERED` or `SAFE_ABSTENTION` until official, authentic public BIS documents are acquired.

---

## 5. End-to-End Validation (7 Representative Fixtures)

All 7 representative fixtures were evaluated through the actual pipeline:

| Fixture | Requirement Input | Retrieved Candidate | Verification Tier | Review Required | Result |
|---|---|---|---|---|---|
| **1. Exact Single-Part** | "Mild steel tubes conforming to IS 1239 (Part 1) with nominal bore 50 mm medium grade." | `IS 1239 (Part 1) : 2004` | `CLAUSE_VERIFIED` | `False` | **PASSED** — Grounded in Clause 1.1; passage `6ede1b129dcef1ca`. |
| **2. Ambiguous Bare Multi-Part** | "Supplied structural and piping material conforming to IS 1239 strictly as per tender specs." | `IS 1239 (Part 2) : 1992` | `CATALOGUE_DISCOVERED` | `True` | **PASSED** — `AMBIGUOUS_MULTI_PART_CITATION` emitted. |
| **3. Product-Directed Resolution** | 3a: Tubes to IS 1239<br>3b: Pipe fittings to IS 1239 | 3a: `IS 1239 (Part 1)`<br>3b: `IS 1239 (Part 2)` | 3a: `CLAUSE_VERIFIED`<br>3b: `CATALOGUE_DISCOVERED` | 3a: `False`<br>3b: `True` | **PASSED** — Correct part resolved based on product type. |
| **4. Compound Multi-Standard** | Tubes to IS 1239 (Part 1) + Valves to IS 14846 | Both isolated | `CATALOGUE_DISCOVERED` (compound) | `True` | **PASSED** — Component isolation without evidence bleeding. |
| **5. Catalogue-Only Standard** | Pipe fittings conforming to IS 1239 (Part 2) : 1992 | `IS 1239 (Part 2) : 1992` | `CATALOGUE_DISCOVERED` | `True` | **PASSED** — Unindexed scope; `clause_number=None`. |
| **6. Withdrawn Citation** | Structural steel sections to IS 2062:2011 | None | `SAFE_ABSTENTION` | `True` | **PASSED** — Explicit notice: `Standard IS 2062 : 2011 has status 'WITHDRAWN'...`. |
| **7. Out-of-Scope Ceiling** | Mild steel tubes to IS 1239 (Part 1) bore 400 mm | `IS 1239 (Part 1) : 2004` | `CATALOGUE_DISCOVERED` | `False` | **PASSED** — Scope ceiling (150 mm) violated; marked `UNSUPPORTED`. |

---

## 6. Ground-Truth Checksum Comparison

- Pre-Phase 32 Checksum: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- Post-Phase 32 Checksum: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`
- **Result:** Bit-for-bit identical. Frozen ground-truth dataset was preserved without modification.

---

## 7. Remaining Risks and Recommended Next Phase

### Remaining Risks:
1. **Physical Standard Acquisition**: `IS 1239 (Part 2)` (pipe fittings) and `IS 2062` (structural steel) are critical procurement standards in India, but lack authentic, publicly accessible full-text PDFs in the repository. They will remain at `CATALOGUE_DISCOVERED` / `SAFE_ABSTENTION` until physical sources are legally acquired.
2. **BIS Portal Scraping Inconsistencies**: The national catalogue database has 13,024 standards labeled `UNKNOWN` due to historical scraping dropouts. While curated standards in `standards.db` have verified statuses, scaling to full national catalogue grounding requires a robust portal reconciliation pipeline.

### Recommended Next Phase (Phase 33):
**Phase 33 — Authoritative PDF Ingestion & Normative Cross-Reference Graph Traversal**
- Acquire and authenticate verified public PDFs for high-impact infrastructure standards (`IS 1239 (Part 2)`, `IS 14846`, `IS 800`).
- Expand the normative dependency graph to trace cross-referenced testing methods and codes of practice dynamically during recommendation adjudication.
- Run real-world tender validation on full tender documents from GeM (Government e-Marketplace).
