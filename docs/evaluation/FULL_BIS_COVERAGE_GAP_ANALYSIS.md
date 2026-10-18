# Tender Saathi — Full BIS Coverage Gap Analysis

**Date:** 2026-10-18  
**Repository:** `Tender_Saathi`  
**Investigation Mode:** Strict Read-Only Audit & Gap Analysis  
**Evaluator:** Antigravity AI  

---

## Executive Summary & Clear Verdict

### The Verdict
**Tender Saathi’s actual recommendation engine is strictly bounded to an internal feasibility dataset of 90 curated standard records (representing only 63 distinct base standards). It does NOT cover the full relevant BIS catalogue.**

While the repository contains a national catalogue database (`data/catalogue/bis_catalogue.db`) with **35,208 historical records across all 15 BIS Division Councils**, this catalogue is **completely decoupled from the active tender recommendation pipeline**. The actual retrieval pipeline queries exclusively from `data/standards/standards.db` and its cached indexes (`data/standards/bm25_index.json` and `data/standards/semantic_embeddings.npy`), which index strictly 90 documents.

### Key Empirical Findings:
1. **Effective Coverage Ratio:** The recommendation engine covers **0.25%** of the total national catalogue (90 / 35,208) and **0.83%** of active published standards (90 / 10,828).
2. **Domain Bias:** The 90 curated standards cover only 6 infrastructure sectors (Pipes/Fittings, Waterworks Valves, Distribution Transformers, Submersible Pumps, Concrete/Plaster, Food Hygiene). High-volume procurement domains such as **Medical Supplies, Information Technology, Laboratory Equipment, High-Voltage Switchgear, Agriculture Machinery, and Textiles have 0% recommendation coverage**.
3. **The "Nonexistent Citation" False Alert:** When a tender explicitly mandates an authoritative Indian Standard that exists in the official BIS catalogue but is outside the 90 curated records (e.g. `IS 8112` 43-Grade Cement, `IS 1489` Pozzolana Cement, `IS 10000` Diesel Engines, `IS 10245` Sterile Syringes), the engine issues an erroneous warning:  
   `NONEXISTENT_CITATION: Cited standard '<exp>' was not found in the BIS standards catalogue.`  
   This creates an unacceptable false-negative alert for procurement officers.
4. **Isolated Nodes in the Graph:** The knowledge graph visualizer and neighbor API are also bound to `standards.db` and `relationships.json`. The 35,118 catalogue-only standards do not appear in the graph, even though displaying them as verified isolated nodes (degree 0) is technically possible and safe.

---

## Phase A: End-to-End Retrieval Architecture & Execution Trace

### A.1 Architecture Diagram

```
[ Tender Document Upload ]
  ├── Plain Text (POST /api/analyze/text)
  └── PDF Document (POST /api/analyze/pdf)
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Ingestion & Preprocessing (src/extract.py)              │
│    • PDF text extraction via pdfplumber/fitz                │
│    • Prompt-injection directive sanitization                │
│    • Regex extraction of cited IS numbers and parameters    │
│    • Multilingual Hindi/Hinglish normalization (src/multilingual.py) │
│    • AI Facet Extraction & Decomposition (src/decompose.py) │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Citation Status Validation (src/validate.py)            │
│    • Validates explicit standard citations                  │
│    • TARGET DB: data/standards/standards.db ONLY            │
│    • [DEFECT]: Flags valid BIS standards outside curated    │
│      90 as "NONEXISTENT_CITATION"                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Multi-Modal Candidate Retrieval (src/retrieval.py)       │
│    • BM25 Lexical Engine (src/bm25_search.py)               │
│      Index: data/standards/bm25_index.json (90 docs)        │
│    • Dense Semantic Engine (src/semantic_search.py)         │
│      Model: all-MiniLM-L6-v2, 384-d                         │
│      Embeddings: data/standards/semantic_embeddings.npy (90)│
│    • Deterministic Keyword Search (src/search.py)           │
│      Target: data/standards/standards.db (90 rows)          │
│    • Candidate Pool: STRICTLY bounded to <= 90 records      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pre-Ranking, Applicability & Envelope Gating             │
│    • Conflict Registry (src/ambiguity.py)                   │
│    • Applicability Gate (src/gate.py)                       │
│      - Operational envelope checks (pressure, voltage)      │
│      - Role prioritization (PRIMARY_PRODUCT vs INSTALLATION)│
│      - Anti-fallthrough for nonexistent citations           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Critic Verification & Evidence Support Engine            │
│    • Critic Evaluation (src/critic.py)                      │
│    • 8-Stage Ambiguity Engine (src/ambiguity.py)            │
│      - Decides: CLEAR, INCOMPLETE, AMBIGUOUS, NO_MATCH      │
│    • Evidence Support Validation (src/evidence/support_engine.py)│
│      - Checks clause scope & parameter alignment            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Cross-Requirement Audit & Report Generation              │
│    • Conflict Resolution Engine (src/precedence/conflict_engine.py)│
│    • Multi-Requirement Audit (src/audit.py)                 │
│    • Report Generator (src/report.py)                       │
│      - JSON report -> reports/tenders/<tid>.json            │
│      - Markdown report -> reports/tenders/<tid>.md          │
│    • Served via GET /api/report/<tid>/json                  │
└─────────────────────────────────────────────────────────────┘
```

### A.2 Component-by-Component Trace

| Stage | Module | Primary Class / Function | Data Sources / Indexes Used | Fallback Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | `api/server.py`<br>`src/extract.py` | `_run_analysis()`<br>`extract_from_pdf()` | Untrusted input buffer (max 25MB PDF / 10k chars text) | Extracts plain text; sanitizes injection tokens. |
| **Decomposition** | `src/decompose.py`<br>`src/ai_parser.py` | `RequirementDecomposer`<br>`AIRequirementParser` | Rule-based regex dictionaries for materials, parameters, actions | Heuristic fallback when AI parser fails. |
| **Status Check** | `src/validate.py` | `validate_standard_status()` | **`data/standards/standards.db`** | Emits `NONEXISTENT_CITATION` if not in `standards.db`. |
| **Retrieval** | `src/retrieval.py` | `HybridRetrievalEngine.search()` | 1. `data/standards/bm25_index.json`<br>2. `data/standards/semantic_embeddings.npy`<br>3. `data/standards/standards.db` | Runs deterministic search if models are missing. |
| **Reranking** | `src/reranker.py` | `CrossEncoderReranker` | Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` | Skips neural reranker if PyTorch unavailable. |
| **Applicability** | `src/gate.py`<br>`src/ambiguity.py` | `ApplicabilityGate`<br>`AmbiguityEngine` | Scope strings and parameter regex from candidate record | Abstains cleanly if candidate violates envelope. |
| **Evidence** | `src/evidence/support_engine.py` | `EvidenceSupportEngine` | Clause passages in `standards.db` | Tags candidate as `UNVERIFIED_COVERAGE` if no clause text. |
| **Audit** | `src/audit.py` | `TenderAuditEngine` | `src/precedence/conflict_engine.py` | Flags system-level contradictions. |
| **Reporting** | `src/report.py` | `ReportGenerator` | In-memory `TenderAuditResult` | Writes JSON and MD artifacts to `reports/tenders/`. |

---

## Phase B: Dataset Audit & Reconciliation

### B.1 Complete Inventory of Datasets and Indexes

| Asset Path | Records / Size | Nature & Purpose | Direct Retrieval Use? |
| :--- | :---: | :--- | :---: |
| **`data/catalogue/bis_catalogue.db`** | 35,208 records<br>(37.65 MB) | National catalogue crawl snapshot (1949–2026). Schema contains `canonical_id`, `department`, `technical_committee`, `status`, `iso_equivalence`. | **NO** (Not indexed or queried during recommendation) |
| **`data/standards/standards.db`** | 90 records<br>(0.11 MB) | High-enrichment feasibility dataset with full Scope Clause 1.x text, notes, and references. | **YES** (The sole candidate database) |
| **`data/standards/bm25_index.json`** | 90 documents<br>(0.28 MB) | Pre-computed inverted index of term frequencies and document lengths for Okapi BM25 retrieval. | **YES** (Used on every text query) |
| **`data/standards/semantic_embeddings.npy`** | 90 vectors<br>(0.14 MB) | Pre-computed 384-dimensional dense vectors generated by `sentence-transformers/all-MiniLM-L6-v2`. | **YES** (Used on every semantic query) |
| **`data/standards/relationships.json`** | 72 edges<br>(0.02 MB) | Explicit normative and technical relationships (56 `VERIFIED`, 16 `CURATED`, 0 `INFERRED`). | **YES** (Graph traversal and successor resolution) |
| **`data/standards/verified_standards.json`**| 8 standards<br>(0.03 MB) | Gold-standard BSB Edge portal benchmark records with verified clause citations. | **NO** (Used for offline evaluation & testing) |
| **`dataset/ground_truth/ground_truth.csv`** | 100 rows<br>(SHA-256 verified) | Frozen evaluation benchmark dataset for regression and adversary testing. | **NO** (Strictly offline test oracle) |

### B.2 Schema & Field Availability Comparison

| Field Category | `bis_catalogue.db` (35,208 Records) | `standards.db` (90 Records) | Impact on Retrieval & Evidence |
| :--- | :---: | :---: | :--- |
| **Standard Number & Title** | 100% Populated | 100% Populated | Both provide official standard designations. |
| **Scope Clause (Clause 1.x)** | **0% Populated (NULL)** | **100% Populated (90/90)** | Dense semantic embeddings require scope text. Catalogue-only records cannot be matched semantically without scope. |
| **Publication Year** | 100% Populated (1949–2026) | 98.9% Populated (89/90) | Enables edition currency checks. |
| **Lifecycle Status** | ACTIVE: 10,828 (30.8%)<br>WITHDRAWN: 11,340 (32.2%)<br>UNKNOWN: 13,024 (37.0%) | Active: 84 (93.3%)<br>Withdrawn: 6 (6.7%) | Catalogue provides comprehensive withdrawal tracking; curated DB has manual status. |
| **Technical Committee** | 100% Populated (e.g. CED 3, ETD 16) | 97.8% Populated (88/90) | Enables domain categorization. |
| **Amendments Count** | 100% Populated | 85.6% Populated | Tracks active corrigenda. |
| **Official Source URL** | 100% Populated (BIS portal URLs) | 90.0% Populated | Provenance tracking for user inspection. |
| **Full Text / Clauses** | **0% Available** | **Passage excerpts only** | Verifying technical parameters requires clause-level text. |

### B.3 Normalization & Overlap Statistics

Reconciling the 90 curated standards against the 35,208 catalogue standards:
- **Exact Canonical ID Match:** **73 / 90 (81.1%)**
- **Syntactic Normalization Matches:** **6 / 90 (6.7%)**
  - Parentheses differences: 2 (e.g. `IS-7098-(Part-1)-1988` vs `IS-7098-Part-1-1988`)
  - Part notation: 3 (e.g. `IS-IEC-61439-3-2012` vs `IS-IEC-61439-Part-3-2012`)
  - SP slug notation: 1 (`SP-57-(QAWSM)-1993` vs `SP-57-1993`)
- **Edition Drift Deltas:** **5 / 90 (5.6%)** (e.g. `IS 2712:2020` in curated vs `IS 2712:2024` in catalogue)
- **Composite Bundles & Statutory Codes:** **6 / 90 (6.7%)** (SP 18 handbooks, IS 2556 bundle, and `FSSAI-Schedule-4`)
- **Net Distinct Standards in Curated DB:** **63 distinct base standards** out of **20,326 distinct base standards** in the national catalogue.

---

## Phase C: Empirical Multi-Domain Recommendation Coverage Testing

To measure effective coverage empirically, we executed deterministic offline queries across **9 major procurement domains**, testing both requirements that fall within the 90 curated standards and requirements that mandate standard BIS specifications outside the curated 90.

### C.1 Multi-Domain Test Matrix Results

| Domain | Test Query / Requirement | Standard in Curated DB? | Standard in Catalogue DB? | System Recommendation Result | Ambiguity State | System Score | Failure Mode / Analysis |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Construction** | Supply of Ordinary Portland Cement 43 grade conforming to IS 8112 | **No** (Only IS 269 present) | **Yes** (`IS-8112-2013`, ACTIVE) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **False Alert:** Emitted `NONEXISTENT_CITATION` warning for IS 8112. |
| **Construction** | Supply of Portland Pozzolana Cement conforming to IS 1489 Part 1 | **No** | **Yes** (`IS-1489-Part-1-2015`, ACTIVE) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **False Alert:** Emitted `NONEXISTENT_CITATION` warning for IS 1489. |
| **Electrical Equipment** | Supply of outdoor oil immersed distribution transformers 2500 kVA 33 kV conforming to IS 1180 Part 1 | **Yes** (`IS-1180-Part-1-2014`) | **Yes** (`IS-1180-Part-1-2014`, ACTIVE) | **IS 1180 (Part 1) : 2014** | `CLEAR` | **0.98** | **Success:** Grounded match with full clause evidence. |
| **Electrical Equipment** | Procurement of high voltage switchgear and controlgear 33 kV conforming to IS/IEC 62271-200 | **No** | **Yes** (`IS-IEC-62271-Part-200-2011`) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Coverage Blindspot:** High-voltage switchgear unrepresented. |
| **Mechanical Equipment** | Supply of centrifugal pumps for agricultural clean water applications conforming to IS 6595 | **Yes** (`IS-6595-Part-1-1993`) | **Yes** (`IS-6595-Part-1-2002`) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Edition Disconnect:** Curated slug is Part 1 1993; query citing base IS 6595 failed token match. |
| **Mechanical Equipment** | Procurement of industrial diesel engines for stationary power conforming to IS 10000 | **No** | **Yes** (`IS-10000-Part-1-1980` through `Part-12`) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Coverage Blindspot:** Industrial internal combustion engines unrepresented. |
| **Medical Supplies** | Procurement of single-use hypodermic sterile syringes conforming to IS 10245 | **No** | **Yes** (`IS-10245-1996`, ACTIVE) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Coverage Blindspot:** Medical devices (MHD department, 2,718 standards) completely unrepresented. |
| **Information Tech.** | Procurement of biometric fingerprint scanners conforming to IS 16351 and UIDAI | **No** | **Yes** (`IS-16351-2015`, ACTIVE) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Coverage Blindspot:** Electronics & IT (LITD department, 2,998 standards) completely unrepresented. |
| **Laboratory Equip.** | Supply of laboratory glassware graduated measuring cylinders conforming to IS 878 | **No** | **Yes** (`IS-878-2008`, ACTIVE) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Coverage Blindspot:** Laboratory equipment unrepresented. |
| **Agriculture** | Supply of agricultural tractor operated disc harrows conforming to IS 6638 | **No** | **Yes** (`IS-6638-2016`, ACTIVE) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Coverage Blindspot:** Agricultural machinery (FAD department, 3,518 standards) completely unrepresented. |
| **Water Systems** | Supply of HDPE pipes PE 100 PN 10 for drinking water conforming to IS 4984 | **No** (Only IS 14333 sewerage present) | **Yes** (`IS-4984-2016`, ACTIVE) | **NONE (Abstained)** | `NO_RELIABLE_MATCH` | 0.00 | **Severe Blindspot:** The primary national HDPE potable water pipe standard IS 4984 is absent from `standards.db`. Retained `IS 14333` (sewerage) then rejected it for application conflict. |
| **Services (Non-Product)**| Hiring of security services and personnel for facility physical security guarding operations | **No** (Service query) | N/A | **IS 1255 : 1983** *(False Positive)* | `CLEAR` | 0.40 | **False Positive:** Recommends "Underground cable laying" for security guard services due to weak lexical fallthrough when commodity gating is absent. |

### C.2 Analysis of Empirical Findings

1. **True Recommendation Success Rate:** Outside the specifically curated infrastructure items, **the success rate across broader procurement domains is 0.0%**.
2. **Correct Abstentions vs Harmful False Negatives:**
   - The engine correctly abstains when an explicit requirement contradicts standard scope (e.g. rejecting sewerage pipes for drinking water).
   - However, when a tender cites a standard from the remaining 35,118 BIS standards, the engine treats it as **nonexistent** rather than **unindexed**. This is a critical product bug: it misinforms users that valid Indian Standards do not exist.
3. **Services Leakage:** Non-product service requirements (e.g. facility management, security guards) lack an upfront "Service vs Product" classifier, allowing low-scoring civil/electrical codes of practice (e.g. `IS 1255`) to be recommended spuriously.

---

## Phase D: Official BIS Coverage & Legal/Copyright Boundaries

### D.1 National Catalogue Decomposition (35,208 Records)

The 35,208 records in `bis_catalogue.db` span all 15 Division Councils of the Bureau of Indian Standards, dating from 1949 to 2026:

| Division Council | Department Code | Description | Total Standards | Curated in `standards.db` | Coverage % |
| :--- | :---: | :--- | :---: | :---: | :---: |
| Production & General Engineering | **PGD** | Fasteners, bearings, machine tools, metrology | 3,528 | 0 | **0.00%** |
| Food & Agriculture | **FAD** | Food products, agricultural machinery, irrigation | 3,518 | 4 | **0.11%** |
| Chemical | **CHD** | Paints, soaps, plastics, industrial chemicals | 3,188 | 2 | **0.06%** |
| Electrotechnical | **ETD** | Transformers, switchgear, cables, motors, batteries | 3,001 | 38 | **1.27%** |
| Electronics & Information Tech. | **LITD** | Hardware, biometric devices, telecoms, cybersecurity | 2,998 | 0 | **0.00%** |
| Medical Equipment & Hospital | **MHD** | Syringes, surgical instruments, prosthetics, diagnostic | 2,718 | 0 | **0.00%** |
| Textile | **TXD** | Geotextiles, uniforms, protective clothing | 2,706 | 0 | **0.00%** |
| Civil Engineering | **CED** | Cement, concrete, pipes, sanitaryware, valves, timber | 2,469 | 36 | **1.46%** |
| Mechanical Engineering | **MED** | Boilers, pumps, valves, refrigeration, cranes | 2,443 | 10 | **0.41%** |
| Metallurgical Engineering | **MTD** | Steel bars, copper alloys, structural steel | 2,403 | 0 | **0.00%** |
| Petroleum, Coal & Related | **PCD** | Lubricants, fuels, bitumen, polymers | 2,335 | 0 | **0.00%** |
| Transport Engineering | **TED** | Automotive components, railway equipment | 1,792 | 0 | **0.00%** |
| Management & Systems | **MSD** | ISO 9001/14001, quality management, auditing | 748 | 0 | **0.00%** |
| Water Resources | **WRD** | Barrages, dams, canal linings, hydrometry | 578 | 0 | **0.00%** |
| AYUSH | **AYD** | Traditional medicine, herbs, formulations | 237 | 0 | **0.00%** |
| **Total BIS Ecosystem** | — | — | **35,208** | **90** | **0.25%** |

### D.2 Lifecycle Status Distribution
- **ACTIVE:** **10,828 standards (30.8%)** — Published, current standards.
- **WITHDRAWN / SUPERSEDED:** **11,356 standards (32.3%)** — Historical standards replaced by revisions or withdrawn.
- **UNKNOWN:** **13,024 standards (37.0%)** — Scraped entries where the portal omitted explicit status tags.

### D.3 Legal, Copyright & Permitted Access Boundaries
1. **Official BIS Access Controls:** Bureau of Indian Standards standards are proprietary technical documents protected by copyright under the Bureau of Indian Standards Act, 2016.
2. **What Can Be Legally Indexed & Stored:**
   - **Permitted / Public Domain:** Standard designation numbers, official titles, technical committees, publication/reaffirmation years, amendment counts, ISO/IEC equivalence, and active/withdrawn lifecycle status.
   - **Fair Dealing / Technical Extraction:** Technical summaries of Scope Clause 1.x, normative reference citations, and parameter verification ranges (e.g. PN ratings, DN sizes, voltage grades).
   - **Prohibited:** Storing complete, verbatim full-text PDFs of all 35,000 standards without an official enterprise distribution license from the Bureau of Indian Standards.
3. **Strategic Conclusion:** Full coverage must **not** rely on downloading 35,000 full-text PDFs. Instead, it must utilize a **Two-Tier Architecture**:
   - Tier 1: Search and validate across all **10,828 Active Standards** using metadata and title indexing.
   - Tier 2: Perform deep clause-level evidence verification on high-frequency procurement domains using licensed/fair-dealing scope extracts.

---

## Prioritized Implementation Roadmap for Broad BIS Coverage

### Phase 1: National Catalogue Lookup & Citation Resolver (Zero Full-Text Needed)
*Target: Immediate Elimination of False "Nonexistent Citation" Warnings*
1. **Refactor `src/validate.py`:** Update `validate_standard_status()` to query `data/catalogue/bis_catalogue.db` (`catalogue_standards` table) as the primary authority for standard existence and lifecycle status.
2. **Eliminate False Alerts:** When a tender cites a standard present in `bis_catalogue.db` (e.g. `IS 8112`), return `is_known = True`, official title, committee, and status (`ACTIVE` vs `WITHDRAWN`).
3. **Direct Citation Surface:** If a tender explicitly mandates a valid standard found in `bis_catalogue.db`, surface it immediately as a validated recommendation candidate tagged:  
   `[VALIDATED_NATIONAL_CITATION: Standard verified in official BIS catalogue; full clause text pending ingestion]`.

### Phase 2: Metadata-Enriched BM25 Index over all 10,828 Active Standards
*Target: Expanding Lexical Search from 90 to 10,828 Standards*
1. **Catalogue Ingestion Script:** Create a build script (`scripts/build_catalogue_search_index.py`) that exports all `ACTIVE` standards from `catalogue_standards`.
2. **Compound Document Construction:** For each active standard, build a search token document:  
   `doc = standard_number + " " + title + " " + technical_committee + " " + department + " " + iso_equivalence`.
3. **Scalable BM25 Index:** Update `BM25SearchEngine` to index all 10,828 active standards (estimated JSON size: ~8.5 MB, in-memory query time: <15ms).
4. **Immediate Impact:** Enables instant lexical retrieval across all 15 Division Councils (Medical, IT, Agriculture, Transport, Chemicals).

### Phase 3: Scope-Aware Passages & Normative Graph for Critical Blindspots
*Target: Adding Deep Evidence Support to Top-10 Procurement Sectors*
1. **Ingest Key Standard Series:** Ingest Scope Clause 1.x and parameter tables for the top unrepresented tender commodities:
   - Civil: `IS 456` (Concrete), `IS 8112` / `IS 12269` / `IS 1489` (Cements), `IS 4984` (HDPE Water Pipes), `IS 12818` (PVC Casing Pipes).
   - Electrical: `IS/IEC 62271` (High Voltage Switchgear), `IS 694` (PVC Wires), `IS 398` (Aluminium Conductors).
   - Mechanical: `IS 10000` (Diesel Engines), `IS 5120` (Centrifugal Pumps).
   - Medical: `IS 10245` (Syringes), `IS 13422` (Surgical Gloves).
2. **Dense Semantic Embedding Update:** Generate 384-dimensional embeddings for the expanded ~500 priority standards.

### Phase 4: Automated Lifecycle & Currency Synchronization with Manakonline
*Target: Continuous Alignment with Official BIS Revisions*
1. **Change Detector Ingestion:** Operationalize `src/catalogue/change_detector.py` to ingest monthly BIS gazette updates and Manakonline notifications.
2. **Automated Supersession Flagging:** Automatically flag standards in `standards.db` when a new edition or amendment is published in `bis_catalogue.db`.

---

## Explicit Limitations & Acceptance Criteria for Claiming Comprehensive Coverage

### Non-Negotiable Acceptance Criteria
Before any future release may claim "Comprehensive Indian Standards (BIS) Coverage", it must satisfy all 6 criteria:

1. **Existence Verification Rate:** 100% of the 10,828 active BIS standards must resolve successfully in `validate_standard_status()` without generating `NONEXISTENT_CITATION` false positives.
2. **Multi-Domain Retrieval Index:** The lexical retrieval candidate pool must span all 15 BIS Division Councils (minimum 10,000 active records in the index).
3. **Ground Truth Benchmark Integrity:** All modifications must maintain strict invariance on `dataset/ground_truth/ground_truth.csv` (SHA-256: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc`).
4. **No Hallucinated Applicability:** Any recommendation derived from catalogue metadata alone (without scope clause) must be explicitly badged:  
   `Confidence: METADATA_VERIFIED | Applicability Evidence: UNINDEXED_BODY`.  
   The system must never claim parameter-level compliance verification without clause text.
5. **Services Rejection Gate:** A dedicated heuristic must classify and reject pure service procurement (e.g. security guards, housekeeping, software development) before matching against engineering standards.
6. **Isolated Node Integrity in Graph:** The knowledge graph explorer must display unlinked catalogue standards as isolated nodes (degree 0) rather than inventing unverified relationship edges.
