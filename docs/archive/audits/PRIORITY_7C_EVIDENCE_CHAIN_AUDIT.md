# PRIORITY 7C — EVIDENCE CHAIN, AUDIT TRAIL & DECISION TRACEABILITY AUDIT REPORT

**Project:** TenderSaathi (SIH26108)  
**Milestone:** Priority 7C  
**Audit Date:** 2026-09-12  
**Baseline Parent Commit:** `8f12c35`  
**Working Tree Status:** Verified Clean Prior to Implementation  

---

## 1. Objective

The engineering objective of Priority 7C is to verify and formalize the complete, end-to-end evidence chain:

$$\text{Tender Text} \longrightarrow \text{Extracted Requirement} \longrightarrow \text{Understood Technical Facets} \longrightarrow \text{Candidate Standard} \longrightarrow \text{Evidence Standard} \longrightarrow \text{Evidence Text} \longrightarrow \text{Source \& Provenance} \longrightarrow \text{Lifecycle} \longrightarrow \text{Why This / Why Not} \longrightarrow \text{Dependencies} \longrightarrow \text{Regulatory Intelligence} \longrightarrow \text{Human Review} \longrightarrow \text{Tender Readiness}$$

Can a procurement officer trace every critical finding from the tender text all the way to its underlying standard, evidence source, provenance, and final audit readiness verdict without encountering fabricated citations, inflated claims, or missing links?

---

## 2. Priority 7B Audit Metadata Correction

- **Inconsistency Inspected:** `docs/PRIORITY_7B_API_UI_CONTRACT_AUDIT.json` recorded commit `7e81c36` (the head commit before committing Priority 7B changes), whereas the Markdown report recorded `ac22e87` (the committed commit).
- **Resolution:**
  - Audit metadata in `docs/PRIORITY_7B_API_UI_CONTRACT_AUDIT.json` was updated to `ac22e87`.
  - Zero findings, test results, or contract verifications were modified.
  - Changes were cleanly committed to git as `8f12c35`.
  - Working tree was verified 100% clean prior to beginning Priority 7C implementation.

---

## 3. Evidence Model Data-Flow Inventory

| Field | Producer | Transformation | API Field | UI Location | User Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Requirement Text** | `src/extract.py` (`extract_from_pdf` / `extract_from_text`) | Strips boilerplate, isolates technical clauses & BoQ lines | `req.text` | `RequirementCard` header & `EvidenceDrawer` Section 1 | Verbatim technical clause from tender |
| **Candidate Standard** | `src/recommend.py` (`StandardsRecommender`) | Version-aware hybrid BM25 + Semantic retrieval with Cross-Encoder | `req.candidate_standard` | `RequirementCard` title & `EvidenceDrawer` Section 2 | Recommended governing Indian Standard |
| **Evidence Standard** | `src/critic.py` (`CriticPipeline`) | Canonical identity enforced: strictly equals candidate or `null` | `req.evidence_standard` | `EvidenceDrawer` Section 4 & safety invariants | Standard providing evidentiary scope |
| **Evidence Text** | `src/critic.py` (`CriticResult`) | Extracts authoritative clause 1 scope or explicit citation | `req.evidence` | `EvidenceDrawer` Section 4 blockquote | Verbatim proof of standard scope |
| **Evidence Strength** | `src/critic.py` | `STRONG` (citation), `MODERATE` (scope), `NONE` (abstention) | `req.evidence_strength` | `EvidenceDrawer` Section 5 `EvBadge` | Groundedness level of technical evidence |
| **Provenance** | `src/standards.py` & `catalogue.db` | Grounded in database metadata without artificial inflation | `req.provenance` | `EvidenceDrawer` Section 5 badge & description | Origin tier of standards record |
| **Source & URL** | `src/critic.py` (`evidence_source`, `source_url`) | Propagated through API into requirement payload | `req.source`, `req.source_url` | `EvidenceDrawer` Section 5 citation box | Specific gazette, order, or portal citation |
| **Why It Matches** | `src/recommend.py` (`why_it_matches`) | Synthesized from matching attributes & scope clauses | `req.why_it_matches` | `RequirementCard` & `EvidenceDrawer` Section 3 | Concise justification for procurement officer |
| **Why Not Alternatives** | `src/recommend.py` (`why_not`) | Identifies weaker relevance, conflicting types, or lack of evidence | `req.why_not` | `EvidenceDrawer` Section 3 ("Why Alternatives Were Not Selected") | Rejection/ranking rationale for alternatives |
| **Lifecycle & Successor** | `src/graph.py` (`StandardsGraph`) | Active, Superseded, or Withdrawn; resolves active successor | `req.lifecycle_status`, `req.successor_standard` | `UpdateCard` & `EvidenceDrawer` Section 6 | Current standard validity & replacement |
| **Dependencies** | `src/dependencies.py` (`DependencyGraph`) | Normative references, test methods, installation codes | `req.dependencies`, `req.standards_coverage` | `EvidenceDrawer` Section 9 | Allied standards to co-apply in contract |
| **Regulatory Information** | `src/regulatory/` (`RegulatoryEngine`) | QCO, CRS, Hallmarking, Scheme-I BIS certification cross-checks | `req.regulatory` | `EvidenceDrawer` Section 10 | Legal mandates and statutory compliance |
| **Human Review** | `src/critic.py` & `src/ambiguity.py` | Boolean flag triggered by uncertainty, gaps, or ambiguity | `req.human_review_required` | `RequirementCard` amber banner & `EvidenceDrawer` Section 11 | Explicit call for engineering officer verification |
| **Tender Readiness** | `src/audit.py` (`TenderAuditEngine`) | Executive audit verdict: `READY_FOR_REVIEW`, `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE` | `result.readiness`, `result.readiness_reasons` | Results page Publication Readiness Banner | Final readiness assessment for tender publication |

---

## 4. Evidence-Chain Contract

### Non-Null Recommendations
For every non-null recommendation:
1. **Requirement:** Verbatim text is preserved in `req.text`.
2. **Selected Standard:** Displayed prominently as `req.candidate_standard` with official title.
3. **Supporting Evidence:** `req.evidence_standard` identically equals `req.candidate_standard`. Scope text or citation is rendered in Section 4.
4. **Origin & Provenance:** `req.provenance`, `req.source`, and `req.source_url` identify exactly where the record and clause originate.
5. **Lifecycle:** Status (`Active`, `Superseded`, `Withdrawn`) is displayed; if superseded, the old citation is kept and the successor is identified with a human-review warning.
6. **Grounding:** "Why this standard?" is grounded in requirement attributes and official scope without inventing unmentioned parameters.
7. **Human Review:** Preserved whenever technical details are missing or evidence requires co-application.

### Null / Abstained Recommendations
For every abstention:
1. **Reason:** Classified into `AMBIGUOUS`, `INCOMPLETE`, or `NO_RELIABLE_MATCH`.
2. **Zero Fabrication:** `candidate_standard = null`, `evidence_standard = null`, and no artificial evidence quote is displayed.
3. **Competing Interpretations:** For `AMBIGUOUS`, competing candidates with titles and relevance scores are listed.
4. **Missing Information:** For `INCOMPLETE`, missing technical parameters and clarification questions are listed.
5. **Truthful Wording:** Displays *"No reliable Indian Standard match was identified from the available catalogue/evidence."* Never claims *"No standard exists"*.

---

## 5. Provenance Safety Audit

The catalogue distribution in `data/catalogue/catalogue.db` (502 records) is strictly maintained:
- `OFFICIAL_PRIMARY`: 173 records
- `OFFICIAL_SECONDARY`: 271 records
- `CURATED`: 52 records
- `VERIFIED`: 6 records

The frontend Evidence Drawer (`EvidenceDrawer.tsx`) does not conflate `CURATED` or `INFERRED` with `OFFICIAL_PRIMARY`. It uses distinct, honest labels:
- **`OFFICIAL_PRIMARY`:** Verified Official Primary Source (Gazette notification, Ministry QCO order, or statutory BIS core registry).
- **`OFFICIAL_SECONDARY`:** Official Secondary Source (Ministry or departmental procurement catalogue / public sector schedule).
- **`VERIFIED`:** Verified Official Source (Cross-verified active record in Bureau of Indian Standards catalogue).
- **`CURATED`:** Curated Technical Source (Expert-compiled engineering standard repository verified against domain specifications).
- **`INFERRED`:** Inferred / Derived (Heuristic specification mapping requiring human technical review).

---

## 6. Source Traceability

The API server (`api/server.py`) now explicitly extracts `evidence_source` and `source_url` from the grounded critic evidence and passes them to the UI as `req.source` and `req.source_url`.
The Evidence Drawer displays the specific origin (e.g. *"BIS Standards Catalogue"*, *"Tender Document Explicit Citation"*, *"IS 15778:2007 Clause 1 Scope; Order S.O. 982(E)"*) directly beneath the provenance badge.

---

## 7. Lifecycle Audit

- **Active Standards:** Marked with clean green `badge--active` badge.
- **Superseded Standards:** Never silently replaced. The tender's cited standard is retained as `req.superseded_citation`, marked with amber `badge--superseded`, and accompanied by a prominent **Lifecycle Advisory**:
  > *"Your tender references X, which appears superseded. Recommended current active successor: Y. Technical officer verification is required before tender finalization."*

---

## 8. Why This / Why Not Audit

- **Why This:** Synthesizes verified technical facets (e.g. *"IS 15778 covers chlorinated polyvinyl chloride (CPVC) pipes for potable water supplies under pressure"*). Does not invent unstated pressure classes, manufacturer brands, or unverified regulatory mandates.
- **Why Not:** Distinguishes lower relevance ranking from hard incompatibility (e.g. *"Alternative standard IS 1239 (Part 2) has lower composite relevance (0.440 vs 0.920)"*).

---

## 9. Abstention Traceability

- Tested against ambiguous terms (e.g. *"valves in cooling water line"*), incomplete scopes (e.g. *"pumps maintenance"*), and unsupported non-standard commodities (e.g. *"office stationery"*).
- In all cases, `candidate_standard` is `null`, `evidence_standard` is `null`, and the UI states: *"No reliable Indian Standard match found in the available catalogue."*

---

## 10. Dependency Traceability

- Preserves explicit relationship roles:
  - `INSTALLATION_STANDARD`
  - `CODE_OF_PRACTICE`
  - `TEST_METHOD`
  - `NORMATIVE_REFERENCE`
  - `ALLIED_STANDARD`
- Never misrepresents dependencies as the primary product standard.
- Displays co-application advice: *"Review for co-application."*

---

## 11. Regulatory Traceability

- Quality Control Orders (QCO), Compulsory Registration (CRS), Hallmarking, and Scheme-I certification preserve their exact statutory categories.
- `UNKNOWN` is never converted to `NOT_APPLICABLE`.
- `REVIEW_REQUIRED` is never converted to `APPLICABLE`.
- Evidentiary basis accordion displays the gazette order number, legal basis, and effective dates where available.

---

## 12. Evidence Drawer UX Findings

- Information hierarchy matches the natural technical audit workflow:
  1. What the Tender Says (Original text & category)
  2. Recommended Indian Standard (Candidate, title, composite score)
  3. Why It Matches & Why Not Alternatives
  4. Authoritative Evidence Quote
  5. Source & Provenance (With honest badge, description, and source citation)
  6. Lifecycle Status & Successor Advisory
  7. Missing Technical Parameters
  8. Related Standards & Co-application Guidance
  9. Standards Ecosystem & Dependencies (Gaps, testing, installation)
  10. Regulatory & Certification Intelligence (QCO, CRS, BIS Schemes)
  11. Human Review Decision & Technical Facets
- Professional procurement styling: Clean layout, high contrast, zero unnecessary animations.

---

## 13. Ten Real-Tender Trace Results

Audited across 10 distinct government tender PDFs from CPPP:

| Tender ID | Req ID | Requirement Summary | Candidate Standard | Evidence Standard | Strength | Provenance | Source | Lifecycle | State | Review? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T020** | T020-R001 | Repair/maint CPVC pipe in lieu of GI | `IS 15778 : 2007` | `IS 15778 : 2007` | `MODERATE` | `CURATED` | BIS Standards Catalogue | Active | `CLEAR` | No |
| **T001** | T001-R001 | Renovation of toilets, tiles, pipeline | `IS 15622 : 2017` | `IS 15622 : 2017` | `MODERATE` | `CURATED` | BIS Standards Catalogue | Active | `CLEAR` | No |
| **T002** | T002-R001 | ARC mechanical maintenance pumps | *None* (Abstain) | *None* | `NONE` | `UNKNOWN` | UNKNOWN | Unknown | `INCOMPLETE` | **Yes** |
| **T005** | T005-R001 | Cable connection of DG Set | *None* (Abstain) | *None* | `NONE` | `UNKNOWN` | UNKNOWN | Unknown | `AMBIGUOUS` | **Yes** |
| **T007** | T007-R001 | Low-oil food outlet equipment | `IS 302 : 1994` | `IS 302 : 1994` | `MODERATE` | `CURATED` | BIS Standards Catalogue | Active | `REVIEW_REQUIRED` | **Yes** |
| **T010** | T010-R001 | Electromechanical & sewerage STP | *None* (Abstain) | *None* | `NONE` | `UNKNOWN` | UNKNOWN | Unknown | `AMBIGUOUS` | **Yes** |
| **T011** | T011-R001 | Underground cable for STP | *None* (Abstain) | *None* | `NONE` | `UNKNOWN` | UNKNOWN | Unknown | `AMBIGUOUS` | **Yes** |
| **T013** | T013-R001 | SITC of VFD water pump panel | `IS/IEC 61439-2 : 2011` | `IS/IEC 61439-2 : 2011` | `MODERATE` | `CURATED` | BIS Standards Catalogue | Active | `REVIEW_REQUIRED` | **Yes** |
| **T016** | T016-R001 | Surveillance shelter construction | `SP 62 : 1997` | `SP 62 : 1997` | `MODERATE` | `CURATED` | BIS Standards Catalogue | Active | `CLEAR` | No |
| **T018** | T018-R001 | Surveillance shelter construction | `SP 62 : 1997` | `SP 62 : 1997` | `MODERATE` | `CURATED` | BIS Standards Catalogue | Active | `CLEAR` | No |

**Trace Verification Result:**
- In all 6 recommended cases, $\text{candidate\_standard} == \text{evidence\_standard}$ (100.0%).
- In all 4 abstention cases, $\text{candidate\_standard} == \text{evidence\_standard} == \text{null}$, with zero fabricated evidence quotes or artificial dependencies.

---

## 14. Automated Test Results

- **Dedicated Evidence Chain Tests:** `tests/test_p7c_evidence_chain.py`
  - 15 tests, 15 passed, 0 failed.
- **Dedicated Contract Tests:** `tests/test_p7b_api_ui_contract.py`
  - 20 tests, 20 passed, 0 failed.
- **Full Repository Test Suite:** `pytest tests/ -v`
  - **290 passed**, 0 failed, 32 harmless deprecation warnings (Python 3.12+ `datetime.utcnow()`).

---

## 15. Frontend Build Result

- Executed `npm run build` in `frontend/`.
- TypeScript validation: 0 errors.
- Vite compilation: Built in 946 ms.

---

## 16. End-to-End Regression Result

- Executed `python3 scripts/validate_e2e.py` across all 20 real government tender PDFs:
  - 20 / 20 tenders audited successfully.
  - 25 requirements analyzed.
  - Candidate == Evidence invariant: **25 / 25 (100.0%)**.
  - Publication readiness distribution remains rock-solid:
    - `READY_FOR_REVIEW`: 7
    - `REVIEW_REQUIRED`: 7
    - `INSUFFICIENT_EVIDENCE`: 6
  - Benchmark hash: `db62e0367ea2983dab49a9ac8a98958efb0c17882df86f131ecfa6b04903690b` (Untouched).
  - Database row counts: `standards.db` = 90 rows (90 distinct IDs); `catalogue.db` = 502 records.

---

## 17. Defects Discovered & Remediations

- **Defect 1 (Source Metadata Gap):** Grounded evidence produced by `src/critic.py` contained `evidence_source` and `source_url`, but `_normalize_result` in `api/server.py` did not expose them directly on the requirement payload.
  - *Fix:* Added `source` and `source_url` fields to `req_dict` in `api/server.py` and typed them in `frontend/src/types.ts`.
- **Defect 2 (Provenance Visibility):** `EvidenceDrawer.tsx` rendered raw provenance enum strings (e.g. `CURATED`) without explaining what they meant to a procurement officer.
  - *Fix:* Added `getProvenanceDetails()` to map each provenance level to an honest, clear technical description and badge class, preventing any misleading implication that curated records are primary statutory gazettes.
- **Defect 3 (Lifecycle Advisory Prominence):** Superseded standards identified the successor in a small tag but lacked an explicit textual warning requiring officer verification.
  - *Fix:* Added a clear **Lifecycle Advisory** in Section 6 explaining that the tender references a superseded standard, identifying the modern successor, and advising officer review.

---

## 18. Files Modified / Created

- **Modified:**
  - [`api/server.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/api/server.py)
  - [`frontend/src/types.ts`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/frontend/src/types.ts)
  - [`frontend/src/components/EvidenceDrawer.tsx`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/frontend/src/components/EvidenceDrawer.tsx)
  - [`docs/PRIORITY_7B_API_UI_CONTRACT_AUDIT.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/docs/PRIORITY_7B_API_UI_CONTRACT_AUDIT.json) (Metadata fix)
- **Created:**
  - [`tests/test_p7c_evidence_chain.py`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/tests/test_p7c_evidence_chain.py)
  - [`docs/PRIORITY_7C_EVIDENCE_CHAIN_AUDIT.md`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/docs/PRIORITY_7C_EVIDENCE_CHAIN_AUDIT.md)
  - [`docs/PRIORITY_7C_EVIDENCE_CHAIN_AUDIT.json`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/docs/PRIORITY_7C_EVIDENCE_CHAIN_AUDIT.json)

---

## 19. Known Limitations

- Standards catalogue contains 502 high-priority procurement standards. Requirements outside this scope result in safe, explicit `NO_RELIABLE_MATCH` or `AMBIGUOUS` abstentions rather than guesses.
- Python 3.12+ standard library deprecation warning on `datetime.utcnow()` remains in server logging without affecting runtime correctness.

---

## 20. Reproducibility Commands

```bash
# 1. Verify Priority 7C Evidence Chain tests
pytest tests/test_p7c_evidence_chain.py -v

# 2. Verify Priority 7B Contract tests
pytest tests/test_p7b_api_ui_contract.py -v

# 3. Verify all repository tests
pytest tests/ -v

# 4. Verify Frontend build
cd frontend && npm run build && cd ..

# 5. Verify 20-Tender E2E regression
python3 scripts/validate_e2e.py

# 6. Verify frozen benchmark hash
sha256sum dataset/ground_truth/multilingual_benchmark.json
```

---

## 21. Final Verdict

# **PRIORITY 7C PASS — PROCEED TO P7D**
