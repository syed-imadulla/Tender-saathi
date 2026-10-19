# Smart India Hackathon — 5-Minute Live Demonstration Script

**Project:** Tender Saathi (AI-Powered Indian Standards Tender Auditing & Compliance Engine)  
**Track:** Smart Governance & Procurement Transparency  
**Duration:** 5 Minutes (Strictly timed for Hackathon Jury)  
**Host Target:** `http://localhost:3000` (Docker Compose) or `http://localhost:5173` (Local Dev)

---

## 0. Executive Elevator Pitch (0:00 – 0:45)

> *"Good morning, esteemed judges. Over ₹20 Lakh Crore of public and defense procurement in India is executed through tenders annually. Yet, tender specifications frequently cite outdated British-era standards, obsolete revisions, or contradictory material specs—leading to project disputes, safety failures, and legal arbitration.*
>
> *Generic Large Language Models hallucinate standard numbers and invent clauses that don't exist in the gazette. Tender Saathi solves this with an **evidence-backed, deterministic auditing engine** that maps procurement requirements to the **National BIS Catalogue of 23,510 active standards** with zero clause fabrication."*

---

## 1. Stage 1: Clause-Grounded Engineering Recommendation (0:45 – 2:00)

### Goal
Demonstrate how Tender Saathi extracts engineering requirements, matches active standards, and grounds recommendations in authentic statutory gazette passages and mandatory Quality Control Orders (QCOs).

### Actions on Screen
1. On the Landing Page (`/`), click **"Try Sample Specification"** or paste:
   ```text
   Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for domestic hot and cold water distribution conforming to IS 15778.
   ```
2. Click **"Audit Tender Specification"** (Analysis executes in < 1.5 seconds).
3. On the Results Page (`/results`), highlight the following UI elements:
   - **Publication Readiness Banner**: 🟢 `READY_FOR_REVIEW` with clear key observations.
   - **Recommended Standard Card**: **IS 15778 : 2007** (Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Supplies).
   - **Verification Tier Badge**: `CLAUSE_VERIFIED` / `BSB_CURATED`.
   - **Statutory Mandate Badges**:
     - **QCO Mandate**: Current DPIIT QCO (`S.O. 1205(E)`) mandating ISI Mark under Section 16 of the BIS Act, 2016.
     - **BIS Scheme-I Certification**: Mandatory product certification before supply.
   - Click **"Inspect Clause Evidence"**: Show verbatim statutory gazette passages (Clause 1 Scope, Clause 8 Hydrostatic Pressure Requirements).

### Talking Point for Judges
> *"Notice that Tender Saathi does not just return a number. It links the exact legal gazette order, the mandatory certification scheme, and verbatim clause passages so procurement officers have legally defensible audit grounding."*

---

## 2. Stage 2: Multi-Requirement Partitioning & Commercial Abstention (2:00 – 3:15)

### Goal
Demonstrate how Tender Saathi decomposes compound multi-package tenders into isolated requirements and refuses to fabricate standards for non-technical commercial terms.

### Actions on Screen
1. Click **"New Check"** in the top navigation bar.
2. In the text area, paste this mixed tender specification:
   ```text
   Section 1: Electrical Wiring
   Supply and laying of PVC insulated unsheathed copper conductor cables for electrical installations conforming to IS 694.

   Section 2: Commercial Conditions
   Earnest Money Deposit (EMD) of INR 1,50,000 shall be submitted online. A mobilization advance of 10% shall be released against a bank guarantee. Penalty of 0.5% per week of delay up to 10%.
   ```
3. Click **"Audit Tender Specification"**.
4. On the Results Page:
   - Point out **Section 1**: Correctly extracted as an electrical engineering requirement, mapped to **IS 694 : 2010**, with verified cable insulation specifications.
   - Point out **Section 2**: Correctly categorized as commercial/financial terms.
   - **Highlight the Safe Abstention**: The candidate standard is `None (Safe Abstention)`. Tender Saathi generated **zero hallucinated standards** for EMD, advance payment, or delay penalties.

### Talking Point for Judges
> *"A critical safety flaw of standard LLMs is hallucinating engineering standards for administrative terms—like claiming an Indian Standard exists for a 'mobilization advance'. Tender Saathi detects non-standardizable commercial clauses and cleanly separates technical scope from contractual terms."*

---

## 3. Stage 3: Catalogue Discovery, Normative Traversal & Human Review (3:15 – 4:30)

### Goal
Demonstrate honest catalogue-only presentation for unindexed standards, interactive normative traversal, and human-in-the-loop decision recording.

### Actions on Screen
1. Click **"Standards Graph"** in the navigation header (`/standards-graph`).
2. Search for **IS 456** (Plain and Reinforced Concrete).
3. View the **Interactive Normative Traversal Journey**:
   - Depth toggle (1 vs 2 hops).
   - Show how IS 456 cites **IS 1786** (High strength deformed steel bars) and **IS 269** (Ordinary Portland cement).
   - Point out the non-elevation safety invariant disclaimer: *"Traversal edges explore normative relationships but never elevate ungrounded standards to primary recommendations."*
4. Next, analyze a tender citing a catalogue-only standard:
   ```text
   Procurement of self-contained open-circuit compressed air breathing apparatus conforming to IS 10245.
   ```
5. On the Results Page:
   - Point out the **Verification Tier**: `CATALOGUE_DISCOVERED`.
   - Show the transparency note: *"Pending technical clause indexing in local semantic corpus; manual engineering review required."*
   - Scroll to the **Prioritized Human Review Queue**:
     - Click **"Accept"** or **"Edit"**.
     - Enter an officer comment: *"Verified against fire rescue operations protocol."*
     - Click **"Save Review Decision"**.
   - Show that the audit trail updates immediately with the officer's timestamped record.
6. Click **"Download Report"** -> Select **"Structured CSV Table (.CSV)"** and **"Full Audit Report (.MD)"** to show instant export.

### Talking Point for Judges
> *"We practice radical evidence transparency. If a standard exists in the 23,510 active BIS catalogue records but our corpus does not yet hold its authentic full-text gazette, we tell the officer honestly: 'Catalogue-Discovered—human review required'. We never invent missing text."*

---

## 4. Closing & Impact Summary (4:30 – 5:00)

> *"In summary, Tender Saathi provides:*
> *1. **National Scale**: 23,510 active BIS catalogue records indexed via FTS5 BM25.*
> *2. **Legal Provenance**: Grounded in authentic statutory gazette passages and mandatory QCOs.*
> *3. **Defensive Governance**: Zero hallucination, physical conflict detection, and human review audit trails.*
> *4. **Instant Deployment**: Packaged in turnkey Docker containers ready for government intranets.*
>
> *Thank you, judges. We welcome your questions."*

---

## 5. Demonstration Contingency & Fallback Protocol

| Failure Scenario | Immediate Workaround for Presenter |
|---|---|
| **Network disconnection / offline venue** | The entire system runs 100% offline. `localhost:3000` / `localhost:5173` uses local SQLite databases and local sentence embeddings without internet access. |
| **PDF upload latency** | Use the **"Try Sample Specification"** button or pre-extracted text snippets provided in this script. |
| **Browser cache glitch** | Open an Incognito window to `http://localhost:3000` or use the pre-generated sample reports in `reports/generated/`. |
| **Groq / LLM API unavailable** | The system automatically falls back to the deterministic heuristic engine (`is_ai_fallback: true`) with 0 degradation in recommendation accuracy. |
