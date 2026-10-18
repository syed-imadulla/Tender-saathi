# Tender Saathi — Phase 18: Controlled Normative Standards Corpus Ingestion Report

## 1. Executive Summary

Phase 18 introduces the first production-oriented, auditable full-text standards ingestion pipeline for Tender Saathi. 

Prior to Phase 18, Tender Saathi relied exclusively on a catalogue database of 90 Indian Standards with scope-level evidence traceability. Full normative standard texts were not indexed, and clause-level grounding remained unavailable. Phase 18 closes this architectural gap for a controlled pilot corpus while strictly enforcing anti-falsification boundaries:
- Machine extraction never implies official BIS statutory authentication.
- Clause identification is structural; semantic similarity is never used to infer clause numbers.
- Unidentified clauses are explicitly tagged as `CLAUSE_UNKNOWN`.
- Machine parsing never claims human expert adjudication (`is_human_verified` strictly requires genuine human sign-off).
- All operations run 100% offline with zero live LLM dependencies and zero network egress in tests.
- Ground-truth evaluation files remain strictly immutable (active ground-truth SHA-256: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).

---

## 2. Architecture & Subsystem Components

The ingestion pipeline is implemented under `src/corpus/` as a modular subsystem:

```
src/corpus/
├── __init__.py           # Subsystem package exports
├── manifest.py           # CorpusDocumentRecord & CorpusManifest with duplicate-hash rejection
├── semantics.py          # 7-tier verification state machine & transition rules
├── extractor.py          # PDFExtractor with layout preservation, OCR detection, table warnings
├── chunker.py            # ClauseAwareChunker with page/edition isolation & canonical SHA-256
├── storage.py            # CorpusStorage (SQLite: corpus_documents, corpus_pages, corpus_passages)
└── retriever.py          # ClauseRetriever with edition-isolated query & grounding verification
```

### A. Corpus Manifest & Provenance (`src/corpus/manifest.py`)
- Tracks: `doc_id`, `standard_number`, `edition_year`, `document_title`, `source_url` (http/https only), `source_citation` (documentary/gazette citations kept separate), `acquisition_date`, `source_name`, `file_sha256`, `file_size_bytes`, `licensing_status`, `usage_restrictions`, `extraction_method`, and `ingestion_status`.
- Enforces SHA-256 uniqueness across documents: duplicate file hashes for distinct document IDs are rejected.

### B. PDF Text Extraction & Quality Diagnostics (`src/corpus/extractor.py`)
- Fast, deterministic page-level extraction using PyMuPDF (`pymupdf`) with fallback to `pypdf`.
- Detects scanned / image-only PDFs: documents with character density < 50 or empty page ratio > 80% are explicitly assigned `IngestionStatus.OCR_REQUIRED` rather than pretending empty text is valid.
- Flags suspicious character corruption: replacement character ratio > 5% triggers `IngestionStatus.QUALITY_FAILED`.
- Table detection: identifies tabular formatting, gridlines, and table labels, emitting explicit warnings (`table_warnings`) without hallucinating missing tabular structure.

### C. Clause-Aware Representation & Hashing (`src/corpus/chunker.py`)
- Segments pages into `ClausePassage` objects.
- **Strict Boundary Isolation**: Passages strictly never cross page boundaries (`page_start == page_end`) and never cross edition or document boundaries.
- **Clause Detection**: Structural regex extracts clause numbering (`1.1`, `4.2`, `Table 1`, `Foreword`).
- **Anti-Hallucination Rule**: If a clause cannot be structurally recognized, it is assigned `clause_identifier = "CLAUSE_UNKNOWN"`. Clause identifiers are never inferred via semantic embeddings or LLM similarity.
- **Stable IDs & Canonical Hashing**: Stable identifier format `{doc_id}_p{page}_c{clause_slug}_{index}` and canonical SHA-256 computed over whitespace-normalized text (`re.sub(r'\s+', ' ', text.strip())`).

### D. SQLite Corpus Storage (`src/corpus/storage.py`)
- Persistent tables in `data/standards/corpus.db`:
  - `corpus_documents`: Complete provenance, metadata, licensing, and diagnostics.
  - `corpus_pages`: 1-indexed page text, text density, empty flags, and warnings.
  - `corpus_passages`: Auditable clause passages indexed by standard number, edition year, clause identifier, and content hash.

### E. Evidence Verification Semantics (`src/corpus/semantics.py`)
Defines 7 progressive verification states:
1. `DOCUMENT_SOURCE_RECORDED`: Document acquisition provenance, source citation/URL, and raw file SHA-256 recorded. Does NOT mean text is validated or authentic.
2. `PDF_TEXT_EXTRACTED`: Text stream extracted without parser crash. Does NOT mean quality was checked or OCR errors are absent.
3. `EXTRACTION_QUALITY_CHECKED`: Text density, empty page ratio, and replacement character rates verified. Does NOT mean clause boundaries are correct or text is legally in force.
4. `PASSAGE_MATCHES_STORED_DOCUMENT`: Canonical SHA-256 matches stored database passage. Does NOT imply official statutory authentication or applicability to a tender.
5. `CLAUSE_IDENTIFIER_VERIFIED`: Clause heading structurally identified in text layout. Does NOT mean the clause applies to any specific procurement requirement.
6. `ENGINEERING_APPLICABILITY_REVIEWED`: Automated domain logic or specification criteria reviewed requirement-to-clause applicability. Does NOT mean a human expert signed off.
7. `HUMAN_EXPERT_ADJUDICATED`: Qualified professional engineer or standards officer signed off with an immutable adjudication record. Must NEVER be set automatically by machines.

---

## 3. Evaluation Metrics

Evaluated via `scripts/evaluate_phase18_ingestion.py` against a controlled pilot corpus containing text-based standards, scanned orders, corrupt files, and duplicate hash injection:

| Category | Metric | Result | Notes |
|:---|:---|:---:|:---|
| **Documents** | Attempted | 6 | 5 pilot fixtures + 1 duplicate hash attempt |
| | Registered | 5 / 6 (83.3%) | 1 duplicate file rejected |
| | Extracted Successfully | 3 / 5 (60.0%) | Valid text PDFs (IS 1180, IS 732, IS 2062) |
| | Requiring OCR | 1 / 5 (20.0%) | Scanned Gazette order correctly flagged |
| | Failed or Corrupt | 1 / 5 (20.0%) | Invalid PDF header correctly rejected |
| | Duplicate Documents Rejected | 1 / 1 (100.0%) | SHA-256 hash collision protection verified |
| **Pages & Tables** | Total Pages Extracted | 7 | 2 + 2 + 2 + 1 pages |
| | Pages Flagged | 4 / 7 (57.1%) | Flagged for tables, empty status, or diagnostic warnings |
| | Table Warnings Issued | 2 | IS 1180 Table 1 and IS 2062 Table 1 flagged |
| **Passages** | Created Total | 15 | Clause-grounded passages |
| | Detected Clause Identifier | 12 / 15 (80.0%) | Structurally parsed clauses (e.g. 1, 4.2, 5.1, Table 1) |
| | Unresolved Clause Identifier | 3 / 15 (20.0%) | Explicitly tagged as `CLAUSE_UNKNOWN` |
| | Unresolved Provenance | 0 / 15 (0.0%) | 100% of passages linked to file hash & edition |
| | Inferred Semantically | 0 (0.0%) | Strictly prohibited by design |
| **Semantics & Safety** | Statutory Portal Authentication | `False` | Offline cache cannot claim live BIS authentication |
| | Human Expert Adjudication | `False` | Machine extraction cannot claim human approval |
| | Cross-Edition Isolation | `True` | 1989 vs 2014 passages strictly segregated |
| | Machine Recommendation Accuracy | `N/A` | Extraction coverage is not recommendation accuracy |

---

## 4. Test Verification

Comprehensive test suite in `tests/test_corpus_ingestion.py` validates all 15 acceptance criteria:

```bash
pytest tests/test_corpus_ingestion.py -v
============================== 15 passed in 0.54s ==============================
```

Full repository test suite run:
```bash
pytest -q
604 passed in 60.84s (0:01:00)
```

Frontend production build:
```bash
npm run build --prefix frontend
✓ built in 1.09s
```

Ground-truth immutability check:
```bash
sha256sum dataset/ground_truth/ground_truth.csv
8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc  dataset/ground_truth/ground_truth.csv
```

---

## 5. Licensing Assumptions & Governance

1. **Permitted Test Fixtures**: Synthetic test fixtures conforming to public structural standards schemas were used for automated testing.
2. **Statutory Public Gazette Orders**: Government notifications and Quality Control Orders published in the Gazette of India are statutory public domain records under Indian copyright jurisprudence.
3. **Restricted Standards Copyright**: Full normative Indian Standards under BIS copyright are not redistributed or committed to Git. The ingestion pipeline accepts lawful local copies on user systems without bundling proprietary texts into the codebase.

---

## 6. Known Limitations & Next Justified Step

### Known Limitations
1. **OCR Subsystem**: Scanned documents are reliably detected and marked `OCR_REQUIRED`, but local OCR engines (e.g. Tesseract) are not invoked in this pilot to maintain zero native binary dependencies.
2. **Complex Embedded Tables**: Tabular data is flagged with explicit warnings, but nested multi-row header cell parsing is reserved for future table-specific extractors.
3. **Pilot Scope**: Clause grounding is verified on pilot documents; production recommendation workflows default to catalogue-level scope evidence unless local full-text corpus storage is initialized.

### Next Smallest Justified Step (Phase 19)
Connect the clause retrieval subsystem into the production recommendation feedback loop (`src/recommend.py`) exclusively for standards with active full-text corpus records, enabling clause-level evidence presentation in the UI without altering baseline retrieval weights.
