# Tender Saathi — Phase 19: Safe Clause-Level Evidence Integration Audit

**Audit Date**: October 18, 2026  
**Auditor**: Antigravity Automated Verification Subsystem (Pair Programming Mode)  
**Corpus State**: Local Relational Corpus Database (`data/standards/corpus.db`)  
**Active Ground Truth**: `dataset/ground_truth/ground_truth.csv`  
**Dataset SHA-256**: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (strictly immutable)  
**Test Suite Result**: 617 / 617 passed offline in 59.64s  
**Frontend Production Build**: Vite v5.4.21 bundle built in 974ms  

---

## Executive Summary

Phase 19 integrates the offline clause-retrieval subsystem (`src/corpus/retriever.py`) into Tender Saathi's core recommendation and evidence presentation paths (`src/recommend.py`, `src/traceability.py`, `api/server.py`, and `frontend/src/components/EvidenceDrawer.tsx`).

The integration achieves **zero recommendation-ranking changes, zero decision-state regressions, and complete preservation of anti-falsification verification boundaries**:
- **Candidate Standard Stability**: 0 / 25 candidate standard changes across the comprehensive benchmark suite.
- **Decision State Invariance**: 0 / 25 decision status changes (e.g., `RECOMMEND`, `REVIEW_REQUIRED`, `RECOMMEND_WITH_REVIEW`, `WITHHELD_INSUFFICIENT_EVIDENCE`).
- **Selective Classification Invariance**: In-domain coverage remains 70.0% (14 / 20) with 0.0% selective risk (0 / 14 wrong recommendations).
- **Negative Control Safety**: 0.0% false recommendation rate (0 / 5) on synthetic negative controls; 100.0% rejection rate preserved.
- **Verification Integrity**: Live BIS portal authentication (`is_official_source_authenticated = False`) and human expert adjudication (`is_human_verified = False`) remain strictly false across all automated retrieval pathways.

---

## 1. Files Changed and End-to-End Architecture Path

### 1.1 Changed Files

| File | Subsystem | Modifications |
| :--- | :--- | :--- |
| `src/corpus/semantics.py` | Corpus Semantics | Added `ClauseEvidenceOutcome` enum (5 explicit outcomes) and human-readable descriptions in `OUTCOME_DESCRIPTIONS`. |
| `src/corpus/storage.py` | Relational Storage | Added `get_document_by_id`, `get_documents_by_standard`, and `get_document_by_standard` query helpers with strict edition year filtering. |
| `src/corpus/retriever.py` | Clause Retrieval | Added `ClauseEvidenceResult` dataclass with serialization; added `extract_clause_hint` static parser; implemented `retrieve_clause_evidence` with 5 discrete outcomes, base standard number normalization, and strict edition matching. |
| `src/traceability.py` | Evidence Traceability | Added 8 clause evidence fields to `TraceableEvidenceRecord`; updated `build_trace_record` to accept `clause_evidence` dict and gate `is_normative_clause_verified`. |
| `src/recommend.py` | Recommendation Engine | Attached `CorpusStorage` and `ClauseRetriever` to `StandardsRecommender`; integrated clause retrieval in `_evaluate_component_recommendations`, single-requirement recommendations, and abstentions. |
| `api/server.py` | REST API Adapter | Serialized `clause_evidence` in requirement objects within `/api/analyze/text`, `/api/analyze/pdf`, `/api/analyze/sample`, and `/api/analyze/image`. |
| `frontend/src/types.ts` | Frontend Contract | Added `ClauseEvidenceData` interface; added `clause_evidence` to `Requirement` and `TraceRecord`. |
| `frontend/src/components/EvidenceDrawer.tsx` | Evidence Presentation | Enhanced Section 14 with a dedicated Normative Clause Evidence card displaying clause identifier, page number, document ID, file SHA-256, passage SHA-256, authentic passage blockquote, extraction quality badge, and explicit boundary disclaimers. |
| `tests/test_clause_evidence_integration.py` | Test Suite | Added 13 deterministic offline integration tests covering exact standard/edition matching, edition isolation, not-found states, unavailable storage, corrupt database, non-fuzzy clause identifiers, unknown clause rejection, recommender integration, compound decomposed components, abstention preservation, anti-falsification guarantees, and API serialization. |

### 1.2 End-to-End Recommendation Path

```mermaid
flowchart TD
    A["Tender Requirement Text"] --> B["Multilingual Normalizer (src/recommend.py)"]
    B --> C["Candidate Generation & Hybrid Search (Catalogue BM25 + Embeddings)"]
    C --> D["Applicability Gate & Critic Evaluation (src/critic.py)"]
    D --> E["Safety Gates: Ambiguity, Dependency & Lifecycle Checks"]
    E --> F["Candidate Standard Selected or Abstention Decided"]
    F --> G{"Eligible Ingested Corpus Doc Available?"}
    G -- "No / Not Ingested" --> H["Outcome: CORPUS_DOCUMENT_NOT_ELIGIBLE<br/>Fallback to Local Catalogue Scope Evidence"]
    G -- "DB Missing / Corrupt" --> I["Outcome: CORPUS_NOT_AVAILABLE<br/>Fallback to Local Catalogue Scope Evidence"]
    G -- "Yes" --> J{"Explicit Clause Cited?"}
    J -- "Yes (e.g. Clause 4.2)" --> K["Exact Structural Match in CorpusStorage"]
    J -- "No" --> L["Exact Lexical Search Match (Grounded = False)"]
    K -- "Match Found" --> M["Outcome: CLAUSE_EVIDENCE_FOUND<br/>is_grounded = True<br/>is_normative_clause_verified = True"]
    K -- "Match Absent" --> N["Outcome: CLAUSE_EVIDENCE_NOT_FOUND<br/>is_grounded = False"]
    M --> O["Build TraceableEvidenceRecord (src/traceability.py)"]
    N --> O
    H --> O
    I --> O
    L --> O
    O --> P["API Serialization (api/server.py)"]
    P --> Q["EvidenceDrawer UI Presentation (frontend)"]
```

---

## 2. Before / After Ranking and Decision-State Comparison

A full before/after evaluation was run against the benchmark dataset (`dataset/ground_truth/ground_truth.csv` and synthetic negative controls).

| Metric | Phase 18 Baseline | Phase 19 Integrated | Delta | Regression? |
| :--- | :--- | :--- | :--- | :--- |
| **Active Dataset SHA-256** | `8bcc...3cfc` | `8bcc...3cfc` | 0 | None (Immutable) |
| **Total Evaluated Cases** | 25 | 25 | 0 | None |
| **Top-1 Retrieval Accuracy** (Answerable) | 89.5% (17 / 19) | 89.5% (17 / 19) | 0.0% | None |
| **Top-3 Retrieval Accuracy** (Answerable) | 89.5% (17 / 19) | 89.5% (17 / 19) | 0.0% | None |
| **Mean Reciprocal Rank (MRR)** | 0.895 | 0.895 | 0.000 | None |
| **In-Domain Procurement Coverage** | 70.0% (14 / 20) | 70.0% (14 / 20) | 0.0% | None |
| **In-Domain Selective Risk** | 0.0% (0 / 14) | 0.0% (0 / 14) | 0.0% | None |
| **Pooled Recommendation Coverage** | 60.0% (15 / 25) | 60.0% (15 / 25) | 0.0% | None |
| **Pooled Selective Risk** | 6.7% (1 / 15) | 6.7% (1 / 15) | 0.0% | None |
| **Under-Specified Abstention Recall** | 100.0% (1 / 1) | 100.0% (1 / 1) | 0.0% | None |
| **Negative Control False Rec Rate** | 0.0% (0 / 5) | 0.0% (0 / 5) | 0.0% | None |
| **Negative Control Rejection Rate** | 100.0% | 100.0% | 0.0% | None |
| **Catalogue Status Match Rate** | 100.0% | 100.0% | 0.0% | None |
| **Candidate Standard Changes** | — | 0 / 25 | 0 | None |
| **Decision State Changes** | — | 0 / 25 | 0 | None |

---

## 3. Clause Evidence Coverage Analysis

### 3.1 Coverage by Outcome Category

Across all 25 benchmark requirements:

| Outcome State | Count | Percentage | Explanation |
| :--- | :---: | :---: | :--- |
| `CORPUS_DOCUMENT_NOT_ELIGIBLE` | 19 | 76.0% | Candidate standard recommended, but no authentic full-text normative BIS PDF exists in local `data/standards/corpus.db`. System seamlessly fell back to catalogue-level scope evidence. |
| `NO_EVIDENCE_OBJECT` (Safe Abstention) | 6 | 24.0% | System withheld recommendation (`candidate_standard = None`) due to ambiguity, under-specification, or negative control rejection. Preserved safety withholding. |
| `CLAUSE_EVIDENCE_FOUND` | 0 | 0.0% | Zero cases in default production repository, as proprietary copyrighted BIS documents are not bundled in repository storage. |
| `CLAUSE_EVIDENCE_NOT_FOUND` | 0 | 0.0% | Standard was not present in eligible corpus. |
| `CORPUS_NOT_AVAILABLE` | 0 | 0.0% | Database file was present and accessible. |
| `CORPUS_LOOKUP_ERROR` | 0 | 0.0% | Zero SQL or retrieval runtime exceptions. |

### 3.2 Explicit Numerator and Denominator

- **Clause Grounding Coverage across Answerable Reqs**: `0 / 19` (`0.0%`).
- **Clause Grounding Coverage across All Benchmark Cases**: `0 / 25` (`0.0%`).
- **Catalogue Scope Fallback Coverage**: `19 / 19` (`100.0%`) for all generated recommendations.
- **Corpus Status in Production Database**: `0` documents currently registered in `data/standards/corpus.db`.

> [!IMPORTANT]
> **Anti-Falsification Finding**: The 0.0% clause grounding coverage on the baseline repository reflects authentic reality: no full normative BIS standard PDFs have been illicitly scraped, downloaded, or bundled into the Git repository. The integration successfully provides the architecture, verified pipelines, and safety guards so that when authorized, authentic standards documents are ingested locally by an organization, clause evidence automatically lights up without requiring code changes.

---

## 4. Verification Invariants and Test Results

### 4.1 Invariants Enforced

1. **Exact Standard and Edition Matching**: Documents and passages are isolated strictly by standard number and publication year. Passages from an older edition (e.g., 1989) are never surfaced as evidence for a requirement mandating a newer edition (e.g., 2014).
2. **Structural Grounding Verification**: `is_grounded` is set to `True` if and only if an explicit clause identifier was structurally extracted and matched against an authentic passage. Passages from unknown sections (`CLAUSE_UNKNOWN`) or general lexical similarity matches have `is_grounded = False`.
3. **No Semantic Hallucination**: No clause identifier is ever inferred, invented, or hallucinated using vector similarity or LLM completion.
4. **Negative Decision Priority**: Clause lookup failures or unavailable storage do not modify critic decisions, selective risk gating, or human review flags.
5. **No False Authentication Claims**:
   - `is_official_source_authenticated`: Permanently `False` for local corpus files.
   - `is_human_verified`: Permanently `False` until qualified human adjudication consensus is recorded.
   - `is_local_catalogue_verified`: Set to `True` when catalogue match exists.
   - `is_normative_clause_verified`: Set to `True` only when `CLAUSE_EVIDENCE_FOUND` with verified structural grounding.

### 4.2 Test Suite Breakdown

All 13 new integration tests in `tests/test_clause_evidence_integration.py` pass offline:

1. `test_1_exact_standard_and_edition_matching`: Verifies exact edition matching and document linkage.
2. `test_2_multiple_editions_isolation`: Verifies that distinct editions of the same standard (2014 vs 1989) do not cross-contaminate passages.
3. `test_3_clause_not_found_in_eligible_corpus`: Verifies `CLAUSE_EVIDENCE_NOT_FOUND` when a clause does not exist in an ingested standard.
4. `test_4_no_corpus_document_available`: Verifies `CORPUS_DOCUMENT_NOT_ELIGIBLE` when a standard has no registered corpus document.
5. `test_5_ineligible_document_ocr_required`: Verifies `CORPUS_DOCUMENT_NOT_ELIGIBLE` when document ingestion status is `OCR_REQUIRED`.
6. `test_6_corrupt_or_unavailable_corpus_database`: Verifies `CORPUS_NOT_AVAILABLE` when the database is missing, deleted, corrupt, or unconfigured.
7. `test_7_similar_clause_identifiers_no_fuzzy_match`: Verifies that similar clause IDs (e.g. `4.2.1` vs `4.2`) are never fuzzy-matched.
8. `test_8_unknown_clause_identifiers_not_grounded`: Verifies that `CLAUSE_UNKNOWN` passages are returned without grounding (`is_grounded = False`).
9. `test_9_recommender_integration_end_to_end`: Verifies end-to-end integration into `StandardsRecommender` and `trace_record`.
10. `test_10_compound_requirements_per_component_clause_evidence`: Verifies that decomposed compound requirements retain per-component clause evidence.
11. `test_11_abstention_and_review_decisions_preserved`: Verifies that abstentions and negative control rejections remain completely intact.
12. `test_12_anti_falsification_boundaries`: Verifies that `is_official_source_authenticated` and `is_human_verified` cannot be set to `True` by automated retrieval.
13. `test_13_api_serialization`: Verifies `/api/analyze/text` REST API serialization of `clause_evidence` and `trace_record`.

**Full Backend Suite**: 617 passed in 59.64s.  
**Frontend Production Build**: Clean build in 974ms (`tsc && vite build`).

---

## 5. Known Limitations and Next Evidence-Backed Step

### 5.1 Known Limitations

1. **Empty Production Document Store**: The default local database `data/standards/corpus.db` contains 0 full-text normative standards due to BIS copyright protection. Clause evidence is currently demonstratable exclusively via synthetic fixtures and offline test environments.
2. **Lexical / Structural Retrieval Only**: Complex engineering tables spanning multiple pages with nested merged cells currently generate table warnings (`has_table = True`) and may require specialized tabular representation in future phases.
3. **Absence of Live Portal Sync**: Because Tender Saathi operates strictly offline without unauthorized web scraping, live amendment notices or corrigenda issued after publication year must be ingested via explicit versioned files.

### 5.2 Next Evidence-Backed Step

The immediate logical progression following Phase 19 is **Phase 20: Authorized Standards Ingestion & Clause Evidence Validation**:
1. Implement a controlled workflow allowing authorized end-users to securely ingest licensed BIS standard PDFs into their local `data/standards/corpus.db`.
2. Measure real clause-evidence coverage on authorized domain-specific standards (e.g., civil works and distribution transformers).
3. Connect expert adjudication packets (`reports/adjudication_packets/`) to display clause evidence alongside scope excerpts for qualified human reviewers.
