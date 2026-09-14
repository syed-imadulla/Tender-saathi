# Phase 4: Connect BIS Catalogue to TenderSaathi Retrieval Report

**Date**: 2026-09-14T08:33:17.542182+00:00  
**Status**: COMPLETE & VERIFIED  
**Authoritative Standards Source**: `data/catalogue/bis_catalogue.db`  

---

## 1. Executive Summary

Phase 4 connected the authoritative Phase 2 BIS catalogue containing **35,208 canonical standards** to TenderSaathi's multi-stage retrieval and recommendation pipeline. The static 502-record catalogue was replaced as the active recommendation source while strictly preserving legacy database counts, raw data files, and the M8 AI architecture.

| Metric | Measured Value | Requirement / Target | Status |
|---|---|---|---|
| **Active Standards Source** | `bis_catalogue.db` | `data/catalogue/bis_catalogue.db` | **PASS** |
| **BIS Catalogue Count** | **35,208** | 35,208 canonical standards | **PASS** |
| **Legacy DB (`catalogue.db`)** | **502** | Exactly 502 records (UNTOUCHED) | **PASS** |
| **Duplicate Canonical IDs** | **0** | 0 | **PASS** |
| **Fabricated Identifiers / Metadata** | **0** | 0 | **PASS** |
| **Stale 502 Index Usage** | **0** | 0 (Isolated versioned indexes) | **PASS** |
| **Fake Compatibility Tables** | **0** | 0 (Dynamic query handling) | **PASS** |

---

## 2. Catalogue Distribution & Lifecycle

All records originate from Phase 2 normalized BIS data. Zero lifecycle inference was applied.

| Lifecycle Status | Record Count | Percentage |
|---|---|---|
| **ACTIVE** | 10,828 | 30.75% |
| **WITHDRAWN** | 11,340 | 32.21% |
| **SUPERSEDED** | 16 | 0.05% |
| **UNKNOWN** | 13,024 | 36.99% |
| **Total Canonical Records** | **35,208** | 100.0% |

- `UNKNOWN` is never treated as `ACTIVE` automatically.
- `WITHDRAWN` standards remain in the catalogue for historical provenance and are flagged accordingly.
- `SUPERSEDED` standards preserve explicit BIS supersession records without inventing replacements.

---

## 3. Retrieval Ablation Performance

Evaluated against the untouched ground truth dataset (`dataset/ground_truth/ground_truth.csv`, 20 requirements) across all 35,208 BIS standards:

| Retrieval Architecture | Top-1 Accuracy | Top-3 Recall | MRR | Latency (Avg) | Latency (Cold) |
|---|---|---|---|---|---|
| **Deterministic** | 10.0% | 15.0% | 0.125 | 1387.5 ms | 2845.2 ms |
| **BM25** | 5.0% | 5.0% | 0.060 | 1012.8 ms | 1141.1 ms |
| **Semantic (`all-MiniLM-L6-v2`)** | 15.0% | 20.0% | 0.179 | 785.4 ms | 1606.4 ms |
| **Hybrid Ensemble** | **10.0%** | **15.0%** | **0.125** | **655.9 ms** | **1062.5 ms** |
| **Hybrid + Cross-Encoder** | **5.0%** | **20.0%** | **0.125** | **2438.0 ms** | **9460.6 ms** |

---

## 4. Provenance & Traceability

Every recommendation produced by the pipeline is traceable directly to the BIS source:

| Provenance Attribute | Total Populated | Coverage |
|---|---|---|
| **Source (`source`)** | 35,208 | 100.0% |
| **Source URL (`source_url`)** | 35,208 | 100.0% |
| **Raw Record Reference (`raw_record_ref`)** | 35,208 | 100.0% |

---

## 5. End-to-End Representative Test Cases

Validation of 8 representative procurement requirements:

| ID | Domain / Case | Predicted Top Standard | Human Review | Relevance Score | Match Explanation / Notes |
|---|---|---|---|---|---|
| **CASE-1** | CPVC pipe | `IS 15778 : 2007` | FLAGGED | 1.00 | Tender explicitly requires compliance with IS 15778 : 2007. |
| **CASE-2** | Valve replacement | `IS 9739 : 1981` | FLAGGED | 0.05 | Catalogue Record: Sectional Committee CED 03, Title: Specifi... |
| **CASE-3** | 3.3 kV motor | `IS 4029 : 2010` | FLAGGED | 0.14 | Catalogue Record: Sectional Committee ETD 15, Title: Guide f... |
| **CASE-4** | Explicit IS reference | `None` | FLAGGED | 0.00 | No reliable Indian Standard match found in the available cat... |
| **CASE-5** | Compound ISO/IEC standard | `None` | FLAGGED | 0.00 | No reliable Indian Standard match found in the available cat... |
| **CASE-6** | Part-specific standard | `IS 1554 (Part 1) : 1988` | FLAGGED | 1.00 | Tender explicitly requires compliance with IS 1554 (Part 1) ... |
| **CASE-7** | Ambiguous requirement | `None` | FLAGGED | 0.00 | No reliable Indian Standard match found in the available cat... |
| **CASE-8** | Missing technical parameters | `IS/ISO 10434 : 2020` | FLAGGED | 0.28 | Identical under single numbering |

---

## 6. Architecture & System Invariants

1. **Database Isolation**:
   - `data/catalogue/catalogue.db`: Exactly 502 records verified before and after.
   - `data/catalogue/bis_catalogue.db`: Exactly 35,208 records verified before and after.
   - `data/raw/bis/run_20260914_042545/`: 186 page files intact and unchanged.
2. **Index Isolation**:
   - BM25 index: `data/catalogue/bis_bm25_index.json`
   - Semantic index: `data/catalogue/bis_semantic_embeddings.npy` + `bis_index_manifest.json`
   - Stale 502 index usage: 0.
3. **No Phase 5 Functionality**:
   - Zero scheduling, cron, GitHub actions, or automatic synchronization implemented.
