# System Architecture: SIH26108 Recommendation Engine

**Problem Statement**: SIH26108 — *“AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications”*  
**Document**: PPT-Ready Architecture Blueprint & Component Walkthrough  
**Phase**: Milestone 2 Prototype Architecture

---

## 1. End-to-End Workflow Architecture Diagram

```mermaid
flowchart TD
    subgraph INP["Input Tier"]
        A1["Tender PDF Document<br/>(CPPP Notices)"]
        A2["Text Requirement / Clause<br/>(Direct Specification String)"]
    end

    subgraph EXT["Extraction & Classification Tier (src.extract)"]
        B1["PDF / Text Ingestion & Cleaning<br/>(Noise & Boilerplate Removal)"]
        B2["Requirement Extraction<br/>(Clause & Item Segmentation)"]
        B3["Category Classifier<br/>(Material / Equipment / Installation / General)"]
        B4["Explicit Citation Detector<br/>(IS / ISO / IEC / SP Regex Parser)"]
    end

    subgraph RET["Retrieval Tier (src.search)"]
        C1["Exact Standard ID Match<br/>(e.g., IS 15778, IS 15000)"]
        C2["Multi-Modal Lexical Match<br/>(Title & Scope Overlap)"]
        C3["Domain Keyword Match<br/>(Technical Trade Nouns)"]
    end

    subgraph VER["Knowledge & Relationship Tier (src.standards & src.validate)"]
        D1[("BIS Standards SQLite DB<br/>(85 Verified & Curated Standards)")]
        D2["Version & Status Validator<br/>(Active / Superseded / Withdrawn)"]
        D3["Relationship Graph Traversal<br/>(SUPERSEDES, SUPERSEDED_BY, REFERENCES)"]
    end

    subgraph EVI["Evidence Grounding & Gating Tier (src.evidence & src.recommend)"]
        E1["Evidence Grounding Engine<br/>(Scope & Clause Verification)"]
        E2["Source Provenance Engine<br/>(VERIFIED Portal vs CURATED Catalogue)"]
        E3["Confidence Calibration<br/>(High / Medium / Low Score Calculation)"]
        E4{"Ambiguity & Specificity Gate<br/>(Under-specified Parameters?)"}
    end

    subgraph OUT["Decision & Output Tier"]
        F1["Authoritative Recommendation<br/>(Active Standard + Scope Evidence + QCO Info)"]
        F2["Supersedence Warning<br/>(Alerts Obsolete Citation + Recommends Successor)"]
        F3["Human-in-the-Loop Review Queue<br/>(Flags Missing Parameters for Engineer Review)"]
    end

    %% Data Flow Connections
    A1 --> B1
    A2 --> B2
    B1 --> B2
    B2 --> B3
    B2 --> B4

    B3 --> C2
    B4 --> C1
    B2 --> C3

    C1 --> D2
    C2 --> D2
    C3 --> D2
    D1 <--> D2
    D1 <--> D3
    D2 <--> D3

    D2 --> E1
    D3 --> E1
    E1 --> E2
    E2 --> E3
    E3 --> E4

    E4 -- "High/Med Confidence & Parameters Clear" --> F1
    D3 -- "Superseded Citation Detected" --> F2
    E4 -- "Low Conf / Missing Engineering Parameters" --> F3
```

---

## 2. Component Walkthrough & Responsibilities

### Tier 1: Input Ingestion Tier
* **Supported Inputs**: Accepts either multi-page raw tender notice PDFs from Central Government procurement portals (`tenders/raw/` or `data/tenders/`) or arbitrary plain-text specification strings from procurement officers.
* **Boilerplate Stripping**: Systematically discards administrative noise (EMD details, multi-currency bidding rules, tender fees, critical submission dates) to focus strictly on technical work descriptions.

### Tier 2: Requirement Extraction & Classification (`src/extract.py`)
* **Clause Segmentation**: Isolates discrete procurement requirements from multi-item tender summaries.
* **Category Classification**: Classifies each statement into one of four standardized engineering categories:
  - `material`: Raw construction materials, tiles, pipes, chemicals, cables.
  - `product_equipment`: Discrete manufactured machines, valves, pumps, transformers, panels.
  - `installation_execution`: Civil works, laying of concrete pipes, earthing installation, rewiring.
  - `general_specification`: Codes of practice, hygiene guidelines (HACCP), national safety codes.
* **Explicit Citation Detection**: Scans for existing Indian Standard mentions (`IS 1239`, `SP 30`, `IS/IEC 61439`) to verify if the tender cites current or obsolete standards.

### Tier 3: Multi-Modal Standards Retrieval (`src/search.py`)
* **Exact Number Search**: Sub-millisecond lookup on standard numbers and divisional identifiers.
* **Lexical & Semantic Overlap**: BM25-inspired token overlap matching against standard titles and scope clauses, filtered through technical stop-word lists.
* **Domain Keyword Boosting**: High-weight scoring for distinctive technical engineering nouns (e.g. *CPVC*, *hubless*, *sluice*, *precast concrete*, *VFD*, *earthing*).

### Tier 4: Knowledge Graph & Status Validation (`src/standards.py`, `src/validate.py`)
* **Unified SQLite Repository**: Stores normalized metadata, technical committee designations, reaffirmation dates, and verbatim scopes.
* **Explicit Relationship Graph**: Stores directional edges strictly backed by evidence:
  - `SUPERSEDES`: Connects active standards to obsolete standards (e.g. `IS/ISO 10434` $\rightarrow$ `IS 10611`).
  - `REFERENCES`: Connects citing standards to normative references (e.g. `IS 15000` $\rightarrow$ `IS 2491`).
  - `CODE_OF_PRACTICE_FOR`: Connects execution guidelines to product specifications (e.g. `IS 783` $\rightarrow$ `IS 458`).
* **Active Status Checking**: Distinguishes `CURRENT_ACTIVE`, `REPLACED_OR_SUPERSEDED`, and `WITHDRAWN` states.

### Tier 5: Evidence Grounding & Confidence Calibration (`src/evidence.py`, `src/recommend.py`)
* **Evidence Grounding**: Factual claims are mapped directly to verbatim clauses in the Scope or Foreword. If unsupported, the engine yields *"Insufficient evidence"* rather than fabricating technical data.
* **Provenance Tracking**: Maintains full source attribution (`VERIFIED: BSB Edge Portal` vs `CURATED: BIS Catalogue`).
* **Confidence Scoring**: Calibrates confidence as `High` (exact standard / high scope match on active standard), `Medium` (curated standard or partial match), or `Low` (ambiguous scope).

### Tier 6: Decision & Human-in-the-Loop Gate
* **Authoritative Recommendations**: Generates clear, actionable recommendation cards showing standard number, title, active status, scope snippet, and DPIIT Quality Control Order (QCO) mandatory status.
* **Supersedence Alerts**: Alerts procurement officers when their tender cites a superseded standard and suggests the valid legal successor.
* **Ambiguity Routing**: Automatically identifies under-specified tenders (missing pipe diameters, pressure ratings, or fluid media) and routes them to human engineers, preventing procurement disputes.
