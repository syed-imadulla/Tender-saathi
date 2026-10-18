# Tender Saathi — Phase 13 Expert Adjudication Handoff Dossier

**Document Status**: Official Handoff Dossier (Ready for Domain Expert Panel)  
**Date**: 2026-10-18  
**Governing SOP**: [`docs/data/GROUND_TRUTH_GOVERNANCE.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/data/GROUND_TRUTH_GOVERNANCE.md)  
**Adjudication Rubric**: [`docs/data/ADJUDICATION_RUBRIC.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/data/ADJUDICATION_RUBRIC.md)  
**Packet Manifest**: [`reports/adjudication_packets/packet_manifest.json`](file:///home/syed-imadulla/Desktop/Tender_Saathi/reports/adjudication_packets/packet_manifest.json)  

---

## 1. Executive Summary & Verification Boundary

In accordance with GSD Phase 13 specifications, **the automated adjudication workflow, packet compiler, two-party consensus validator, and anti-falsification governance gates have been fully implemented and verified**.

As mandated by Tender Saathi's core architectural constraints:
> **Human Review Boundary**: Execution has deliberately stopped at the human-expert boundary. **Zero rows have been marked `human_verified: TRUE`**. No synthetic reviewer identities, credentials, timestamps, or approvals have been manufactured.

Claims of expert-validated accuracy remain reported as `N/A (Awaiting Phase 13 Expert Sign-off)` until physical panels of certified CPWD, BIS, or MES engineers complete their adjudications.

---

## 2. Inventory of Delivered Review Packets

Exactly **40 case review packets** have been generated and staged in [`reports/adjudication_packets/packets/`](file:///home/syed-imadulla/Desktop/Tender_Saathi/reports/adjudication_packets/packets/):

| Packet Cohort | Count | Source Dataset | Current Adjudication Status | Human Verified Status |
| :--- | :--- | :--- | :--- | :--- |
| **Active Benchmark Baseline** | 20 cases | `dataset/ground_truth/ground_truth.csv` | `UNVERIFIED_BASELINE` | `FALSE` |
| **Staged Candidates** | 20 cases | `dataset/ground_truth/candidates_staging.csv` | `MACHINE_PREDICTED` | `FALSE` |
| **Total Review Packets** | **40 cases** | — | — | **0 Verified (Safe Boundary)** |

Every packet contains:
1. **Physical Source Document Link**: Bound to real tender PDFs in `tenders/raw/` with exact page numbers.
2. **Verbatim Requirement Text**: Raw specification extracted from the tender.
3. **Current AI Model Prediction**: Proposed standard, confidence, decision, and rationale.
4. **BIS Catalogue Context**: Standard title, status, technical committee, and official scope excerpt from `data/standards.db`.
5. **Standardized Reply Form**: Independent Reviewer A and Reviewer B evaluation blocks.

---

## 3. Step-by-Step Instructions for the Expert Review Panel

### Step 1: Distribute Packets to Certified Adjudicators
Qualified reviewers must belong to approved engineering roles:
- `CPWD_EXECUTIVE_ENGINEER` / `CPWD_ASSISTANT_ENGINEER`
- `BIS_STANDARDS_OFFICER` / `BIS_SCIENTIST`
- `MES_MILITARY_ENGINEER`
- `RAILWAY_SENIOR_SECTION_ENGINEER`
- `PUBLIC_PROCUREMENT_SPECIALIST`

### Step 2: Adjudication Against Canonical Rubric
Reviewers must inspect each packet and classify the requirement according to [`docs/data/ADJUDICATION_RUBRIC.md`](file:///home/syed-imadulla/Desktop/Tender_Saathi/docs/data/ADJUDICATION_RUBRIC.md):
- `RECOMMEND` (specify active standard and mandatory clause number)
- `ABSTAIN_UNDER_SPECIFIED` (document missing engineering parameters)
- `ABSTAIN_AMBIGUOUS` (document competing mutually exclusive interpretations)
- `ABSTAIN_CONFLICTING` (document internal technical contradictions)
- `REJECT_INELIGIBLE` (document why out-of-scope for BIS standards)

### Step 3: Complete Reviewer Blocks
Each packet must receive independent sign-offs in its YAML blocks:
```yaml
reviewer_id: "REV-CPWD-01"
reviewer_full_name: "Er. [Name]"
reviewer_role: "CPWD_EXECUTIVE_ENGINEER"
organization: "Central Public Works Department"
decision: "RECOMMEND"
verified_standards: "IS 15905 : 2011"
clause_reference: "IS 15905:2011 Clause 1 Scope"
technical_rationale: "Hubless cast iron soil and waste piping is governed by IS 15905 with mechanical couplings."
reviewed_at_utc: "2026-10-20T10:30:00Z"
signature_or_token: "CPWD-EE-VERIFIED-TOKEN"
```

### Step 4: Save to Completed Packets Directory
Save filled packets into `reports/adjudication_packets/completed/CASE_<ID>.md`.

### Step 5: Execute Automated Consensus & Ingestion Gate
Run the consensus and ingestion CLI:
```bash
# 1. Dry-run inspection (detects consensus and conflicts)
python3 scripts/ingest_adjudication.py --dry-run

# 2. Stage consensus-verified cases
python3 scripts/ingest_adjudication.py --promote --output-staging dataset/ground_truth/verified_staging.csv
```

---

## 4. Integrity Check & Baseline Preservation

- Active ground truth file: [`dataset/ground_truth/ground_truth.csv`](file:///home/syed-imadulla/Desktop/Tender_Saathi/dataset/ground_truth/ground_truth.csv)
- Active SHA-256: `8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc` (Verified 100% intact)
- Staged candidate file: [`dataset/ground_truth/candidates_staging.csv`](file:///home/syed-imadulla/Desktop/Tender_Saathi/dataset/ground_truth/candidates_staging.csv)
- Offline Test Suite Status: 543 / 543 tests passing offline.
