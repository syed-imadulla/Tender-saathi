# PHASE 4R5 — LIVE BIS INGESTION EXECUTION AND PROOF

**Final Verdict:** `PHASE 4R5 COMPLETE — LIVE INGESTION VERIFIED`  
**Started At:** `2026-09-14T10:51:20.207929+00:00`  
**Finished At:** `2026-09-14T10:51:46.503735+00:00`  
**Execution Duration:** `26.3s`  
**Live BIS Run ID:** `run_20260914_094936`  
**New Authoritative Snapshot ID:** `snapshot_20260914_104415`  

## 1. Live BIS Acquisition Proof (All 10 Seeds)

| Seed | Total Reported | Total Fetched | Pages Fetched | SUM == Reported | Status |
|---|---|---|---|---|---|
| `0` | 19244 | 19244 | 20 | True | **PASS** |
| `1` | 27301 | 27301 | 28 | True | **PASS** |
| `2` | 20776 | 20776 | 21 | True | **PASS** |
| `3` | 17249 | 17249 | 18 | True | **PASS** |
| `4` | 16415 | 16415 | 17 | True | **PASS** |
| `5` | 16128 | 16128 | 17 | True | **PASS** |
| `6` | 16815 | 16815 | 17 | True | **PASS** |
| `7` | 15766 | 15766 | 16 | True | **PASS** |
| `8` | 15480 | 15480 | 16 | True | **PASS** |
| `9` | 15592 | 15592 | 16 | True | **PASS** |

- **Total Raw Rows Acquired:** `180766`
- **Total Reported in Live BIS Catalogue:** `180766`

## 2. Normalization & Staging Database

- **Accepted Standards in New Database:** `35204`
- **Duplicate Rows Deduplicated:** `145171`
- **Quarantined Rows:** `391`
- **Recovered Standards:** `6`
- **Database Integrity:** `True` (`PRAGMA integrity_check == ok`)
- **Unique Canonical IDs:** `35204` / `35204` (100.0%)

## 3. Snapshot Comparison (Change Detection)

Compared newly generated snapshot `snapshot_20260914_104415` against previous snapshot `snapshot_20260914_094047`:

| Category | Count | Interpretation |
|---|---|---|
| `NEW` | 7 | Authoritative live BIS diff result |
| `UNCHANGED` | 35196 | Authoritative live BIS diff result |
| `UPDATED` | 1 | Authoritative live BIS diff result |
| `STATUS_CHANGED` | 0 | Authoritative live BIS diff result |
| `WITHDRAWN` | 11339 | Authoritative live BIS diff result |
| `SUPERSEDED` | 16 | Authoritative live BIS diff result |
| `MISSING_FROM_SOURCE` | 11 | Authoritative live BIS diff result |

## 4. Live Full-Text Ingestion Coverage & Identity Demarcation

- **Attempted Standards:** `5`
- **Exact Edition Attached:** `2`
- **Historical Edition Attached:** `1`
- **Identity Rejected (Bleed/Collision Prohibited):** `2`
- **Metadata Only Records:** `35202`

### Live Probe Executions
| Target Standard | Archive Identifier | Attached | Historical Edition | Provenance Hash | Result |
|---|---|---|---|---|---|
| `IS 732 : 2019` | `gov.in.is.732.1989` | True | `True` (`IS 732 : 1989`) | `21842508f571c541...` | **ACCEPTED** |
| `IS 104 : 1979` | `gov.in.is.104.1979` | True | `False` (`IS 104 : 1979`) | `8fcfedb94533f40a...` | **ACCEPTED** |
| `IS 7098 (Part 1) : 1988` | `gov.in.is.7098.1.1988` | True | `False` (`IS 7098 (Part 1) : 1988`) | `032f953e2cbeba05...` | **ACCEPTED** |
| `IS 7098 (Part 1) : 1988` | `gov.in.is.7098.2.2011` | False | N/A | N/A | **REJECTED** (Part mismatch (sibling bleed prohibited): archive Part 2 vs target Part 1) |
| `IS 5039` | `gov.in.is.15039.2000` | False | N/A | N/A | **REJECTED** (Base number collision mismatch: archive=15039 vs target=5039) |

## 5. Index Reversibility & Artifact Integrity

- **DB Canonical IDs:** `35204`
- **BM25 Indexed Documents:** `35204`
- **Semantic Indexed Documents:** `35204`
- **Bidirectional Reversibility (DB <-> Index):** `True` (100.0%)

### Snapshot Manifest SHA-256 Hashes
| Artifact | SHA-256 |
|---|---|
| `bis_catalogue.db` | `c61f4718dc60f5c24880aa5b66500a3112b6602442b329bfb4c0454a3800de8a` |
| `bis_bm25_index.json` | `dcd107bbdb72df9546836bef12641d7b18416542d62790c789540a85e83420cb` |
| `bis_semantic_embeddings.npy` | `f099285ced61c7a688171be0395bda52118936a668c85a7fcdaf3f233a893508` |
| `bis_semantic_doc_ids.json` | `88c03b4737a39b0217f19093b4550e24c67983546c24d5d2f9bfb21f00daed95` |
| `bis_semantic_doc_hashes.json` | `d327ede2d57a38497518ee4c1bdaade06798bf9934c5ec3a4ed9dc485e25b9a2` |
| `bis_index_manifest.json` | `5a79fe733bf40cf997c2a82606d673461012b651d940bba0ad349d51133cb984` |

## 6. Real End-to-End Query Verification

| Query Type | Input Requirement Text | Rank | Index Doc ID | Candidate Standard | Status | Title | Identity Chain Verified |
|---|---|---|---|---|---|---|---|
| 1. Explicit standard citation | "Supply and laying of CPVC pipes conformi..." | #1 | `IS-15778-2007` | `IS 15778 : 2007` | `UNKNOWN` | Chlorinated Polyvinyl Chloride (CPV... | **True** |
| 2. Lexical retrieval requirement | "Submersible pump sets for clear, cold wa..." | #1 | `IS-8034-2002` | `IS 8034 : 2002` | `WITHDRAWN` | Submersible Pumpsets - Specificatio... | **True** |
| 3. Semantic retrieval requirement | "High voltage underground electric cable ..." | #1 | `IS-16667-2018` | `IS 16667 : 2018` | `WITHDRAWN` | High - Voltage direct current (Hvdc... | **True** |
| 4. Tender shorthand requirement | "HT XLPE insulated power cables 11 kV gra..." | #1 | `IS-7098-Part-1-2025` | `IS 7098 (Part 1) : 2025` | `UNKNOWN` | Crosslinked Polyethylene Insulated ... | **True** |
| 5. Standard without full text (metadata only) | "Structural steel hollow sections for gen..." | #1 | `IS-4923-1997` | `IS 4923 : 1997` | `WITHDRAWN` | Hollow steel sections for structura... | **True** |
| 6. Standard with historical edition text | "Electrical wiring installations in resid..." | #1 | `IS-732-2019` | `IS 732 : 2019` | `ACTIVE` | Code of practice for electrical wir... | **True** |

## 7. Frozen Files Integrity

- **`ground_truth.csv` SHA-256:** `cfcbca27a729bd0619886be9128cfba272b912bd21115604b45af7eb59fa404b` (**MATCH**)
- **`catalogue.db` SHA-256:** `bbd0b58a112f1755e77dda04fed56e87dff7fe7eb06975491ac4e023ebc35dd1` (**MATCH**)
- **Frozen raw pages count:** `186` (**MATCH**)

## 8. Final Conclusion

### `PHASE 4R5 COMPLETE — LIVE INGESTION VERIFIED`

The complete live pipeline — from real BIS HTTP requests across all 10 seeds to normalization, change detection, full-text ingestion, index construction, atomic promotion, live API status, and end-to-end query verification — has been executed and proven with real evidence.
