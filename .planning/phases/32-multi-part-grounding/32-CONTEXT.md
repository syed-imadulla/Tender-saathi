# Phase 32 Context: Multi-Part Standard Grounding & Physical Source Acquisition Readiness

**Phase**: 32 (`32-multi-part-grounding`)  
**Domain**: Multi-Part Standards Identification, Ambiguity Detection, Normative Cross-References, and Physical Source Acquisition Readiness  
**Target Architecture**: `src/catalogue/normalizer.py`, `src/extract.py`, `src/recommend.py`, `src/ambiguity.py`, `src/validate.py`, `src/corpus/retriever.py`, `data/standards/relationships.json`  

---

## 1. Context & Baseline Assessment

### 1.1 Multi-Database Baseline State (Recomputed Directly from DBs)
Direct SQL audit executed at the start of Phase 32:
- **National BIS Catalogue (`data/catalogue/bis_catalogue.db`)**:
  - Total records: **35,208** (across 29,735 distinct base numbers).
  - Confirmed Active: **10,828**.
  - Withdrawn: **11,340**.
  - Superseded: **16**.
  - Unknown lifecycle status: **13,024**.
  - Active standards with normative passages in corpus: **4** (`IS 4984`, `IS 1489 Part 1`, `IS 383`, `IS 269`).
  - Active catalogue gap: **10,824** standards ($10,828 - 4$).
- **Curated Standards Repository (`data/standards/standards.db`)**:
  - Total curated standards: **96**.
  - Confirmed Active: **80**.
  - Confirmed Withdrawn: **16**.
  - Multi-part standards currently curated: **8** records (`IS 1180 Part 1`, `IS 7098 Part 2`, `IS 2556 Parts 1, 2, 4`, `IS 10322 Part 5 / Sec 5`, `IS 7098 Part 1`, `IS 1239 Part 2`, `IS 1489 Part 1`, `IS 1239 Part 1`).
  - Curated standards with operative passages: **7** (`IS 456`, `IS 4984`, `IS 1489 Part 1`, `IS 383`, `IS 269`, `IS 1786`, `IS 1239 Part 1`).
  - Curated active standards awaiting passages: **73** standards ($80 - 7$).
- **Normative Evidence Corpus (`data/standards/corpus.db`)**:
  - Total ingested documents: **8**.
  - Total normative passages: **31** authentic, checksummed clauses.
- **Search Indexes**:
  - `catalogue_search_index.db`: **10,828** active FTS5 records (synchronized with `ACTIVE` records in `bis_catalogue.db`).
  - `bm25_index.json`: **96** curated records (cached and verified).

---

## 2. Key Decisions & Gray Areas Resolved

### Decision 1: Multi-Part Standard Extraction & Normalization
- **Issue**: `normalize_standard_mention` in `src/extract.py` stripped `/` characters and converted hyphens naively to colons, corrupting compound prefixes (`IS/IEC` -> `IS IEC`, `IS/ISO` -> `IS ISO`) and part/section numbers (`IS/IEC 61439-3` -> `IS IEC 61439 : 3`).
- **Resolution**: Route standard mention normalization through `StandardIdentifierNormalizer.parse`, which deterministically preserves prefix hierarchies (`IS/IEC`, `IS/ISO`, `SP`), exact part designations (`Part 1`, `Part 2`), and section numbers without loss.

### Decision 2: Disambiguation of Bare Multi-Part Citations
- **Issue**: When a requirement specifies bare `IS 1239` (without stating Part 1 or Part 2) for "mild steel tubes", the recommender selected `IS 1239 (Part 2)` with `Ambiguity: CLEAR` because Part 2 was indexed first.
- **Resolution**:
  1. Product scope alignment: "tubes / pipe" maps to Part 1 ("Steel Tubes"), whereas "fittings / tubulars" maps to Part 2 ("Pipe Fittings").
  2. If the product scope is ambiguous or generic ("conforming to IS 1239" or "cement per IS 1489"), trigger `AmbiguityState.REVIEW_REQUIRED` flagging that the tender lacks the required part discriminator.
  3. Bar bare multi-part citations from receiving unconditional `CLAUSE_VERIFIED` unless the specific part is disambiguated and verified.

### Decision 3: Physical Source Acquisition Blockers (IS 1239 Part 2 and IS 2062)
- **Status Audit**:
  - Neither `IS 1239 (Part 2)` nor `IS 2062` has authentic full-text gazette PDFs in the repository.
  - In `bis_catalogue.db`, `IS 2062 : 2011` is recorded as `WITHDRAWN`, and the standard was split into multi-part editions: `IS 2062 (Part 1) : 2025` and `IS 2062 (Part 2) : 2026`, both currently marked `UNKNOWN` lifecycle in the national scrape.
- **Policy**:
  - Uphold zero-fabrication invariant. Do not invent clause text, table values, or mock source files.
  - Retain formal acquisition blockers in `docs/evaluation/PHASE32_MULTI_PART_GROUNDING_REPORT.md`.
  - Maintain these standards at `CATALOGUE_DISCOVERED` or `SAFE_ABSTENTION`, explicitly barring `CLAUSE_VERIFIED`.

### Decision 4: Normative Cross-Reference Provenance
- **Distinction**:
  - Explicit cross-references cite specific normative clauses (e.g., `IS 456` Clause 5.3 explicitly cites `IS 383` for aggregates and Clause 5.1 cites `IS 269` for cement).
  - Inferred associations (e.g., complementary plumbing valves `IS 14846` alongside steel tubes `IS 1239 (Part 1)`) are system dependencies.
  - Provenance must be explicitly recorded (`NORMATIVE_CODE_CLAUSE` vs `HEURISTIC_ASSOCIATION`) in `relationships.json` and trace records.
