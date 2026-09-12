# TenderSaathi Evidence-Backed Indian Standards Review Report

**Standards review aid for procurement specifications**

> [!NOTE]
> This report is a standards-review aid and does not constitute legal compliance certification.

---

## 1. Tender Information

- **Tender ID:** `PKG-EXPLICIT-CITATIONS`
- **Tender Title:** Special Verification Package: Explicit IS Citations, Supersedence & Lifecycle
- **Organisation / Department:** TenderSaathi Verification Suite
- **Source File:** `synthetic_explicit_citations_verification.pdf`
- **Requirements Analysed:** 4

## 2. Publication Readiness

**Status:** 🟡 REVIEW_REQUIRED

### Key Observations:
- 1 requirement(s) cite or match superseded standard(s).
- 1 requirement(s) flagged with CRITICAL risk.
- 1 requirement(s) flagged with HIGH risk.
- 2 requirement(s) require technical engineer review.
- 4 requirement(s) have potentially missing specification parameters.

## 3. Executive Summary

| Metric | Count / Distribution | Notes |
|---|---|---|
| **Requirements Analysed** | 4 | Total clauses extracted |
| **Direct Recommendations** | 2 | Active standards grounded in evidence |
| **Review Required** | 2 | Flagged for engineering attention |
| **Insufficient Evidence** | 0 | No reliable standard matched |
| **Active Standards** | 3 | Verified current in BIS catalogue |
| **Superseded Standards** | 1 | Outdated standards identified |
| **Withdrawn Standards** | 0 | Cancelled standards |
| **Unknown Lifecycle** | 0 | Unindexed in local catalogue |
| **Related Standards to Review** | 10 | Discovered via relationship graph (depth=1) |

### Governance Distributions

- **Evidence Strength:** STRONG: `4` | MODERATE: `0` | WEAK: `0` | NONE: `0`
- **Specification Review Completeness:** KNOWN: `0` | POTENTIALLY_MISSING: `4` | UNKNOWN: `0` | NOT_APPLICABLE: `0`
- **Risk Distribution:** CRITICAL: `1` | HIGH: `1` | MEDIUM: `0` | LOW: `2`

### Standards Ecosystem & Dependency Coverage

- **Normative References:** `26`
- **Testing Method Dependencies:** `1`
- **Installation / Laying Standards:** `5`
- **Allied Standards:** `1`
- **Potential Standard Gaps:** `2`
- **Verified Standard Gaps:** `0`

## 4. Prioritized Human Review Queue

| # | Priority | Requirement ID | Candidate Standard | Issue / Primary Reason |
|---|---|---|---|---|
| 1 | **CRITICAL** | `CITE-001` | `IS/ISO 10434 : 2020` | Tender explicitly cited a superseded standard requiring replacement verification. |
| 2 | **HIGH** | `CITE-003` | `IS 14846 : 2000` | Potentially missing engineering parameters: Nominal Size / Diameter (DN), Pressure Rating (PN / Class), Body Metallurgy / Material |

## 5. Requirement-by-Requirement Review

### 5.1 Requirement `CITE-001` [PRODUCT_EQUIPMENT]

**Original Requirement Text:**
> "Procurement of steel gate valves conforming to IS 10611"

- **Decomposed Technical Components:** `general: gate valves`
- **Recommended Standard:** **IS/ISO 10434 : 2020** — *Bolted Bonnet Steel Gate Valves for the Petroleum, Petrochemical and Allied Industries*
- **Candidate Standard:** `IS/ISO 10434 : 2020` | **Evidence Standard:** `IS/ISO 10434 : 2020` (Candidate == Evidence Grounding Established)
- **Why It Matches:** This Indian Standard which is identical with ISO 10434 : 2020 'Bolted bonnet steel gate valves for the petroleum, petrochemical and allied industries' covers bolted bonnet steel gate valves with flanged and butt-welded ends.
- **Lifecycle Status:** **ACTIVE** (Active successor replacing cited superseded `IS 10611`) | **Composite Relevance Score:** `1.000`
- **Ambiguity & Verification State:** `REVIEW_REQUIRED` — *Reason:* Tender cited superseded standard 'IS 10611'. Recommended current active replacement.; Potentially missing engineering parameters: Nominal Size / Diameter (DN), Pressure Rating (PN / Class), Body Metallurgy / Material; Valve body metallurgy/material is not specified in tender. Human review recommended to confirm metallurgy (copper alloy vs cast iron vs steel).
- **Evidence Strength:** `STRONG` | **Provenance:** `VERIFIED`
- **Verbatim Evidence (BSB Edge Portal):** "This Indian Standard which is identical with ISO 10434 : 2020 'Bolted bonnet steel gate valves for the petroleum, petrochemical and allied industries' covers bolted bonnet steel gate valves with flanged and butt-welded ends."
- **Why This Standard?:**
  - Recommended authoritative active successor standard recorded in BIS database.
- **Why Not Alternatives?:**
  - Original cited standard is superseded/obsolete.
- **Specification Review Completeness:** `POTENTIALLY_MISSING` (Potentially missing: Nominal Size / Diameter (DN), Pressure Rating (PN / Class), Body Metallurgy / Material, Fluid Medium / Service)
- **Related Standards Identified for Review (Graph Depth = 1):**
  - [→ SUPERSEDES] `IS 10611 : 1983` — *Bolted Bonnet Steel Gate Valves for the Petroleum, Petrochemical and Allied Industries* (Superseded) — *Note:* Authoritative successor standard supersedes IS 10611 : 1983. Review legacy specifications.
- **Standards Dependencies Mapped (1):**
  - [SUPERSEDES] `IS 10611 : 1983` — *Bolted Bonnet Steel Gate Valves for the Petroleum, Petrochemical and Allied Industries* (IS 10611 : 1983 (Bolted Bonnet Steel Gate Valves for the Petroleum, Petrochemical and Allied Industries) is identified as an evidence-backed authoritative successor standard associated with IS/ISO 10434 : 2020. Evidence: National Foreword explicitly states: 'This standard supersedes IS 10611 : 1983 Steel gate valves (flanged and butt-welded ends) for petroleum, petrochemicals and allied industries.' [Provenance: VERIFIED].)
- **Regulatory & Statutory Intelligence:** Product Certification: `NOT_IDENTIFIED` | QCO: `NOT_IDENTIFIED` | CRS: `NOT_IDENTIFIED` | Hallmarking: `NOT_APPLICABLE`
- **Standards Review Decision:** `REVIEW_REQUIRED` | **Risk Level:** `CRITICAL` | **Confidence:** `High`
- ⚠ **Human Technical Review Required:** Tender cited superseded standard 'IS 10611'. Recommended current active replacement.

---

### 5.2 Requirement `CITE-002` [GENERAL_SPECIFICATION]

**Original Requirement Text:**
> "Food establishment hygiene management in accordance with IS 15000"

- **Recommended Standard:** **IS 15000 : 2024** — *Hazard Analysis and Critical Control Point (HACCP) - Requirements for Any Organization in the Food Chain*
- **Candidate Standard:** `IS 15000 : 2024` | **Evidence Standard:** `IS 15000 : 2024` (Candidate == Evidence Grounding Established)
- **Why It Matches:** Tender explicitly requires compliance with IS 15000.
- **Lifecycle Status:** **ACTIVE** | **Composite Relevance Score:** `1.000`
- **Ambiguity & Verification State:** `CLEAR` — *Reason:* Primary applicable standard IS 15000 is clearly identifiable and sufficiently supported.
- **Evidence Strength:** `STRONG` | **Provenance:** `VERIFIED`
- **Verbatim Evidence (Tender Document):** "Tender explicitly requires compliance with IS 15000."
- **Why This Standard?:**
  - Official title aligns with specification: 'Hazard Analysis and Critical Control Point (HACCP) - Requirements for Any Organization in the Food Chain'.
  - Authoritative scope explicitly covers application: "Tender explicitly requires compliance with IS 15000."
  - Standard is currently active in the BIS repository with verified currency.
  - Provenance established via Tender Document (VERIFIED).
  - Cites normative reference IS 2491 : 2024 (Food Hygiene - General Principles - Code of Practice).
- **Why Not Alternatives?:**
  - Alternative standard IS 2491 has lower composite relevance (0.842 vs 1.000).
- **Specification Review Completeness:** `POTENTIALLY_MISSING` (Potentially missing: Food Establishment Type)
- **Related Standards Identified for Review (Graph Depth = 1):**
  - [→ REFERENCES] `IS 2491 : 2024` — *Food Hygiene - General Principles - Code of Practice* (Active) — *Note:* Normative reference cited within primary standard. Review for co-application.
- **Standards Dependencies Mapped (3):**
  - [REFERENCES] `IS 2491 : 2024` — *Food Hygiene - General Principles - Code of Practice* (IS 2491 : 2024 (Food Hygiene - General Principles - Code of Practice) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 15000 : 2024. Evidence: Clause 2 Reference in IS 15000:2024 explicitly cites IS 2491 : 2024 Food hygiene - General principles - Code of practice (fourth revision). [Provenance: VERIFIED].)
  - [CODE OF PRACTICE] `IS 2491 : 2013` — *Food Hygiene - General Principles - Code of Practice; FSSAI General Sanitary and Hygienic Requirements [IS 2491]* ()
  - [CODE OF PRACTICE] `FSSAI Schedule 4` — *Food Hygiene - General Principles - Code of Practice; FSSAI General Sanitary and Hygienic Requirements [FSSAI Schedule 4]* ()
- **Regulatory & Statutory Intelligence:** Product Certification: `NOT_IDENTIFIED` | QCO: `NOT_IDENTIFIED` | CRS: `NOT_IDENTIFIED` | Hallmarking: `NOT_APPLICABLE`
- **Standards Review Decision:** `RECOMMEND` | **Risk Level:** `LOW` | **Confidence:** `High`

---

### 5.3 Requirement `CITE-003` [PRODUCT_EQUIPMENT]

**Original Requirement Text:**
> "Sluice valves for water works conforming to IS 780"

- **Decomposed Technical Components:** `general: Sluice valves`
- **Recommended Standard:** **IS 14846 : 2000** — *Sluice Valve for Water Works Purposes (50 to 1200 mm Size) - Specification*
- **Candidate Standard:** `IS 14846 : 2000` | **Evidence Standard:** `IS 14846 : 2000` (Candidate == Evidence Grounding Established)
- **Why It Matches:** This standard covers requirements for non-rising stem typesluice valves from 50 to 1200 mm sizes used for water supply u...
- **Lifecycle Status:** **ACTIVE** | **Composite Relevance Score:** `0.884`
- **Ambiguity & Verification State:** `REVIEW_REQUIRED` — *Reason:* Potentially missing engineering parameters: Nominal Size / Diameter (DN), Pressure Rating (PN / Class), Body Metallurgy / Material; Valve body metallurgy/material is not specified in tender. Human review recommended to confirm metallurgy (copper alloy vs cast iron vs steel).
- **Evidence Strength:** `STRONG` | **Provenance:** `VERIFIED`
- **Verbatim Evidence (BSB Edge Portal):** "This standard covers requirements for non-rising stem typesluice valves from 50 to 1200 mm sizes used for water supply up to 45 deg C and having double flanged ends forconnections."
- **Why This Standard?:**
  - Official title aligns with specification: 'Sluice Valve for Water Works Purposes (50 to 1200 mm Size) - Specification'.
  - Authoritative scope explicitly covers application: "This standard covers requirements for non-rising stem typesluice valves from 50 to 1200 mm sizes used for water supply u..."
  - Standard is currently active in the BIS repository with verified currency.
  - Provenance established via BSB Edge Portal (VERIFIED).
  - Cites normative reference IS 778 : 1984 (Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes).
  - Cites normative reference IS 28 : 1982 (Title not in local index).
- **Why Not Alternatives?:**
  - Alternative standard IS 778 has lower composite relevance (0.388 vs 0.884).
- **Specification Review Completeness:** `POTENTIALLY_MISSING` (Potentially missing: Nominal Size / Diameter (DN), Pressure Rating (PN / Class), Body Metallurgy / Material, Fluid Medium / Service)
- **Related Standards Identified for Review (Graph Depth = 1):**
  - [→ REFERENCES] `IS 778 : 1984` — *Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes* (Active) — *Note:* Normative reference cited within primary standard. Review for co-application.
  - [→ REFERENCES] `IS 28 : 1982` — *Title not in local index* (Unknown) — *Note:* Normative reference cited within primary standard. Review for co-application.
  - [→ REFERENCES] `IS 210 : 1993` — *Title not in local index* (Unknown) — *Note:* Normative reference cited within primary standard. Review for co-application.
  - [→ REFERENCES] `IS 318 : 1981` — *Title not in local index* (Unknown) — *Note:* Normative reference cited within primary standard. Review for co-application.
  - [→ REFERENCES] `IS 320 : 1980` — *Title not in local index* (Unknown) — *Note:* Normative reference cited within primary standard. Review for co-application.
- **Standards Dependencies Mapped (26):**
  - [REFERENCES] `IS 778 : 1984` — *Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes* (IS 778 : 1984 (Specification for Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Listed under Clause 2 References in IS 14846:2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 28 : 1982` — *Title not in local index* (IS 28 : 1982 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 210 : 1993` — *Title not in local index* (IS 210 : 1993 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 318 : 1981` — *Title not in local index* (IS 318 : 1981 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 320 : 1980` — *Title not in local index* (IS 320 : 1980 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 341 : 1973` — *Title not in local index* (IS 341 : 1973 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 638 : 1979` — *Title not in local index* (IS 638 : 1979 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 1030 : 1989` — *Title not in local index* (IS 1030 : 1989 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 1363 (Part 1) : 1992` — *Title not in local index* (IS 1363 (Part 1) : 1992 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 1538 : 1993` — *Title not in local index* (IS 1538 : 1993 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 1570 (Part 3) : 1979` — *Title not in local index* (IS 1570 (Part 3) : 1979 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 1865 : 1991` — *Title not in local index* (IS 1865 : 1991 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 2062 : 1992` — *Title not in local index* (IS 2062 : 1992 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 2535 : 1978` — *Title not in local index* (IS 2535 : 1978 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 2712 : 1979` — *Steel Pipe Flanges; Compressed Asbestos/Non-Asbestos Fiber Jointing Sheets - Specification [IS 2712]* (IS 2712 : 1979 (Steel Pipe Flanges; Compressed Asbestos/Non-Asbestos Fiber Jointing Sheets - Specification [IS 2712]) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 2932 : 1993` — *Title not in local index* (IS 2932 : 1993 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 3444 : 1987` — *Title not in local index* (IS 3444 : 1987 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 3658 : 1981` — *Title not in local index* (IS 3658 : 1981 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 4218 (Part 5) : 1979` — *Title not in local index* (IS 4218 (Part 5) : 1979 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 4687 : 1995` — *Title not in local index* (IS 4687 : 1995 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 4854 (Part 1) : 1969` — *Title not in local index* (IS 4854 (Part 1) : 1969 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 4905 : 1968` — *Title not in local index* (IS 4905 : 1968 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 5414 : 1995` — *Title not in local index* (IS 5414 : 1995 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 5660 : 1970` — *Title not in local index* (IS 5660 : 1970 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [REFERENCES] `IS 6603 : 2000` — *Title not in local index* (IS 6603 : 2000 (Title not in local index) is identified as an evidence-backed normative reference cited within the primary specification associated with IS 14846 : 2000. Evidence: Cited under Clause 2 References in IS 14846 : 2000. [Provenance: VERIFIED].)
  - [CODE OF PRACTICE] `SP 57 (QAWSM) : 1993` — *Handbook on Pipes and Fittings for Drinking Water Supply* ()
- **Regulatory & Statutory Intelligence:** Product Certification: `APPLICABLE` | QCO: `CURRENT` | CRS: `NOT_IDENTIFIED` | Hallmarking: `NOT_APPLICABLE`
- **Standards Review Decision:** `REVIEW_REQUIRED` | **Risk Level:** `HIGH` | **Confidence:** `High`
- ⚠ **Human Technical Review Required:** Potentially missing engineering parameters: Nominal Size / Diameter (DN), Pressure Rating (PN / Class), Body Metallurgy / Material; Valve body metallurgy/material is not specified in tender. Human review recommended to confirm metallurgy (copper alloy vs cast iron vs steel).

---

### 5.4 Requirement `CITE-004` [MATERIAL]

**Original Requirement Text:**
> "CPVC pipes conforming to IS 15778 for domestic plumbing"

- **Decomposed Technical Components:** `general: CPVC pipes`
- **Recommended Standard:** **IS 15778 : 2007** — *Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Supplies - Specification*
- **Candidate Standard:** `IS 15778 : 2007` | **Evidence Standard:** `IS 15778 : 2007` (Candidate == Evidence Grounding Established)
- **Why It Matches:** Tender explicitly requires compliance with IS 15778.
- **Lifecycle Status:** **ACTIVE** | **Composite Relevance Score:** `1.000`
- **Ambiguity & Verification State:** `CLEAR` — *Reason:* Primary applicable standard IS 15778 is clearly identifiable and sufficiently supported.
- **Evidence Strength:** `STRONG` | **Provenance:** `CURATED`
- **Verbatim Evidence (Tender Document):** "Tender explicitly requires compliance with IS 15778."
- **Why This Standard?:**
  - Official title aligns with specification: 'Chlorinated Polyvinyl Chloride (CPVC) Pipes for Potable Hot and Cold Water Supplies - Specification'.
  - Authoritative scope explicitly covers application: "Tender explicitly requires compliance with IS 15778."
  - Standard is currently active in the BIS repository with verified currency.
  - Provenance established via Tender Document (VERIFIED).
- **Why Not Alternatives?:**
  - Alternative standard IS 14333 has lower composite relevance (0.298 vs 1.000).
- **Specification Review Completeness:** `POTENTIALLY_MISSING` (Potentially missing: Diameter / Nominal Bore (DN/OD), Pressure Class / Schedule / SDR)
- **Related Standards Identified for Review (Graph Depth = 1):**
  - [→ TEST_METHOD] `IS 12235 : 2004` — *Title not in local index* (Unknown) — *Note:* Official test method standard for parameter verification and quality assurance. Review for testing protocol compliance.
  - [→ INSTALLATION_STANDARD] `IS 7634 (Part 3) : 2003` — *Title not in local index* (Unknown) — *Note:* Installation, laying, and jointing standard associated with IS 7634 (Part 3) : 2003. Review for installation execution.
  - [→ ALLIED_STANDARD] `IS 4985 : 2000` — *Title not in local index* (Unknown) — *Note:* Allied product or component standard. Review for equipment interface compatibility.
- **Standards Dependencies Mapped (4):**
  - [TEST METHOD] `IS 12235 : 2004` — *Title not in local index* (IS 12235 : 2004 (Title not in local index) is identified as an evidence-backed official test method standard for quality and verification associated with IS 15778 : 2007. Evidence: Clause 2 References and Clause 8 Requirements cite IS 12235 (various parts) for methods of testing plastic piping, including hydrostatic pressure, dimensions, and opacity. [Provenance: CURATED].)
  - [INSTALLATION STANDARD] `IS 7634 (Part 3) : 2003` — *Title not in local index* (IS 7634 (Part 3) : 2003 (Title not in local index) is identified as an evidence-backed installation, laying, and execution standard associated with IS 15778 : 2007. Evidence: Foreword note and Annex B recommend laying and jointing of CPVC/PVC water pipes to be executed per IS 7634 (Part 3). [Provenance: CURATED].)
  - [ALLIED STANDARD] `IS 4985 : 2000` — *Title not in local index* (IS 4985 : 2000 (Title not in local index) is identified as an evidence-backed allied product or equipment specification standard associated with IS 15778 : 2007. Evidence: Allied thermoplastic pipe standard for potable water supplies (uPVC vs CPVC). [Provenance: CURATED].)
  - [INSTALLATION STANDARD] `IS 783 : 1985` — *Code of Practice for Laying of Concrete Pipes* ()
- **Regulatory & Statutory Intelligence:** Product Certification: `APPLICABLE` | QCO: `CURRENT` | CRS: `NOT_IDENTIFIED` | Hallmarking: `NOT_APPLICABLE`
- **Standards Review Decision:** `RECOMMEND` | **Risk Level:** `LOW` | **Confidence:** `High`

---

## 6. Evidence & Provenance Governance Summary

> [!IMPORTANT]
> AI/retrieval results are not treated as authoritative evidence by themselves. Factual standards claims are constrained by the available evidence and provenance.

| Provenance Tier | Criteria | Count in Tender | Evidence Strength Produced |
|---|---|---|---|
| **VERIFIED** | Authoritative BSB Edge / BIS portal record manually verified | 3 | `STRONG` |
| **CURATED** | Loaded from official BIS Standards Catalogues / Excel indices | 1 | `MODERATE` |
| **INFERRED** | Contextual heuristic or tender co-citation (strictly unverified) | 0 | `WEAK` |

## 7. Officer Notice & Disclaimer

TenderSaathi is a standards-review aid for procurement specifications. Final applicability, specification, procurement, regulatory and legal decisions remain with the responsible human authority.
