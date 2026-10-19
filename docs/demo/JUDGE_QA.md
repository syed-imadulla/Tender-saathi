# Smart India Hackathon — Judge Q&A & Technical Differentiation Guide

**Project:** Tender Saathi  
**Theme:** AI & Smart Governance / Standards Procurement Compliance  
**Audience:** Technical & Domain Evaluation Panel

---

### Q1: How is Tender Saathi different from simply searching the BIS Portal or 'Know Your Standards'?

**Answer:**
A keyword search on the BIS portal only looks up titles. In real public procurement:
1. **Tenders use domain jargon and compound language**, not official BIS standard titles (e.g. *"providing 25mm CPVC water lines for residential quarters"* vs *"IS 15778 : 2007 Chlorinated Polyvinyl Chloride Pipes for Potable Hot and Cold Water Supplies"*).
2. The BIS portal **cannot ingest unstructured 50-page tender PDFs**, decompose multiple technical scopes, or distinguish technical specifications from commercial payment terms.
3. Tender Saathi provides **multi-stage decision safety**: hybrid lexical (BM25) and dense semantic retrieval (all-MiniLM-L6-v2), physical applicability checks (temperature/pressure constraints), mandatory statutory Quality Control Order (QCO) cross-referencing, and normative relationship graph traversal.

---

### Q2: How does the system handle tenders with multiple distinct requirements?

**Answer:**
Tender Saathi uses a deterministic requirement decomposition pipeline (`src/extract.py` and `src/decompose.py`):
1. It partitions incoming tender documents into numbered packages and requirements using structural headings, lists, and domain shifts.
2. It classifies each extracted clause into technical categories (e.g., `MATERIAL`, `PRODUCT`, `ELECTRICAL`, `INSTALLATION`) vs non-standardizable clauses (e.g., `COMMERCIAL_TERMS`, `LIQUIDATED_DAMAGES`, `EMD`).
3. Each technical requirement is evaluated independently against the standards ecosystem without cross-requirement suppression or contamination.
4. An end-to-end multi-requirement audit engine (`src/audit.py`) aggregates requirement-level scores into an overall tender publication readiness verdict (`READY_FOR_REVIEW`, `CONDITIONAL_REVIEW_REQUIRED`, or `NOT_RECOMMENDED`).

---

### Q3: How are recommendations grounded in actual standards clauses?

**Answer:**
Tender Saathi enforces a **three-tier evidence hierarchy**:
1. **Tier 1: CLAUSE_VERIFIED (`STATUTORY_PUBLIC_GAZETTE`)**: The standard's authentic statutory gazette passages are indexed in our local semantic corpus (`data/standards/corpus.db`). The engine links exact clause numbers (e.g., Clause 1 Scope, Clause 8 Hydrostatic Pressure) and verbatim citations.
2. **Tier 2: CATALOGUE_DISCOVERED**: The standard is authenticated in the official BIS National Catalogue (35,208 records, 23,510 active), but its full-text normative passages are not yet indexed. It is transparently labeled as `CATALOGUE_DISCOVERED` with an explicit human-review requirement flag.
3. **Tier 3: SAFE_ABSTENTION**: Non-technical clauses (e.g. bank guarantee terms) or uncorroborated matches produce a safe abstention (`candidate_standard=None`), preventing clause fabrication.

---

### Q4: What happens when a tender cites a withdrawn or superseded standard?

**Answer:**
Tender Saathi maintains a verified lifecycle database:
1. When an obsolete standard is cited (e.g. `IS 10611` for sluice valves), the engine flags it as `SUPERSEDED` or `WITHDRAWN`.
2. It alerts the procurement officer that citing this standard invites tender challenges or non-compliant bids.
3. If an authoritative successor standard is registered in the BIS catalogue (e.g. `IS 14846` replacing `IS 10611`), Tender Saathi recommends the active successor while routing the case to the Prioritized Human Review Queue.
4. Withdrawn standards without successors trigger `DO_NOT_RECOMMEND` or `REVIEW_REQUIRED`.

---

### Q5: How does the system handle underspecified requirements and physical conflicts?

**Answer:**
1. **Underspecified Requirements**: If a requirement specifies *"water pump"* without stating head (meters), discharge (litres/min), or fluid type, our completeness analyzer (`src/completeness.py`) flags missing engineering parameters, designates the ambiguity state as `AMBIGUOUS_UNDER_SPECIFIED`, and generates a targeted clarification question for the drafting officer.
2. **Physical / Engineering Conflicts**: Our applicability gate (`src/applicability.py`) evaluates physical rules. For example, if a tender specifies *"High Density Polyethylene (HDPE) pipes for 250°C superheated steam"*, the engine detects a temperature conflict (HDPE has a maximum operating temperature of ~60°C–80°C) and flags `APPLICATION_CONFLICT`, issuing a `DO_NOT_RECOMMEND` verdict.

---

### Q6: Does Tender Saathi cover every single BIS standard?

**Answer:**
We are completely transparent on coverage:
- **Broad National Search**: Our catalogue database contains **35,208 BIS catalogue records**, of which **23,510 active standards** are fully indexed for fast lexical search.
- **Deep Clause Evidence**: Deep statutory clause extraction is currently indexed for **13 high-priority core engineering standards** (covering pipes, electrical cables, transformers, concrete, and structural steel) with **53 verified statutory gazette passages**.
- For standards outside these 13, the system surfaces the active catalogue record under the `CATALOGUE_DISCOVERED` tier and warns that clause-level indexing is pending. We **never hallucinate or invent clauses**.

---

### Q7: How does Tender Saathi eliminate the hallucination risks common to generative LLMs?

**Answer:**
1. **Deterministic Core**: Retrieval, lifecycle validation, physical applicability checks, and confidence scoring are executed entirely in deterministic Python code without LLM prompting.
2. **Strict Grounding Contract**: A candidate standard can never be recommended unless backed by an authentic catalogue ID or verified corpus passage.
3. **Offline Reliability**: Even if external LLM APIs (Groq, OpenAI) are completely disabled (`TENDERSAATHI_LLM_ENABLED=false`), 100% of the test suite (799/799 tests) passes and recommendations remain accurate.
4. **Frozen Ground-Truth**: Our benchmark dataset is cryptographically hashed with SHA-256 (`8bcc9bc5...`). Any deviation in expected behavior immediately fails the test pipeline.

---

### Q8: What is the role of human experts in Tender Saathi?

**Answer:**
Tender Saathi is designed as an **officer-in-the-loop decision aid**, not an autonomous legal authority.
1. Any requirement with medium confidence, ambiguous parameters, superseded citations, or catalogue-only status is placed in the **Prioritized Human Review Queue**.
2. Officers can review the system finding and record **ACCEPT**, **EDIT**, or **DISMISS** decisions with written justifications.
3. Every decision is immutably logged with the reviewer's ID and timestamp, and compiled into the final audit report trail.

---

### Q9: How are source provenance and reproducibility ensured?

**Answer:**
Every standard and relationship in Tender Saathi tracks its official source:
- `STATUTORY_PUBLIC_GAZETTE`: Official Gazette of India notifications (e.g., S.O. orders published under the BIS Act, 2016).
- `BIS_CATALOGUE`: Official Bureau of Indian Standards master portal indices.
- `BSB_EDGE`: Verified Bureau of Indian Standards cross-references.
- Graph traversal edges preserve originating clause numbers and evidence citations.
- The test suite includes 799 automated tests that reproduce identical results across different runs.

---

### Q10: What are the current limitations, and how would Tender Saathi scale to production?

**Answer:**
- **Current Limitations**:
  1. Semantic clause extraction is limited to 13 core engineering standards; expanding to all 23,510 standards requires ingestion of digitized BIS documents.
  2. Scanned image OCR accuracy depends on document scan DPI and system OCR libraries (Tesseract).
- **Scale Roadmap**:
  1. Ingest official open-access gazette PDFs and public domain BIS codes at scale into the chunked `CorpusStorage` engine.
  2. Implement an automated BIS Gazette crawler to ingest Quality Control Orders as soon as they are notified by DPIIT and line ministries.
  3. Deploy as a centralized microservice for government e-Procurement portals (GeM, Central Public Procurement Portal - CPPP).
