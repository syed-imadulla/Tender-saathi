# Ground Truth Verification Progress Report (SIH26108)

**Project**: *AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications*  
**Date**: 2026-09-04  
**Feasibility Phase**: Step 2 — Human Ground Truth Dataset Curation  

---

## 1. Progress Status Overview

| Metric | Count | Percentage |
|---|---|---|
| **Total Candidate Requirements Extracted** | **72** | 100.0% |
| **Selected for First Manual Ground-Truth Batch** | **20** | **27.8%** |
| **Remaining for Subsequent Validation Waves** | **52** | 72.2% |
| **Current Verified Count (`human_verified = TRUE`)** | **0** | 0.0% (Pending human expert review) |

---

## 2. Domain Distribution of Selected Batch (20 Requirements)

The initial 20 requirements were selected across 12 distinct tenders covering diverse procurement engineering domains:

| Category / Domain | Selected Count | Example Requirements |
|---|---|---|
| **Plumbing & Piping Materials** | 4 | Hubless cast iron pipes, CPVC pipe in lieu of GI pipe, Sewerage pipelines |
| **Building Finishes & Masonry** | 2 | Ceramic/vitrified wall tiles, Cement plaster repairing |
| **Sanitary & Water Supply Fittings** | 2 | Upgradation of sanitary fittings, General plumbing fittings |
| **Electrical Power Cabling** | 3 | Underground power cable for STP, Power cables to AMF room, DG set cables |
| **Electrical Switchgear & Distribution** | 2 | Distribution boards & sports stadium lighting, Feeder pillar switchgear |
| **Heavy Industrial Mechanical & Equipment** | 3 | Process Water Pump motors (3.3 kV), Industrial valve replacement, Flange joints |
| **Automation & Motor Drives** | 1 | SITC of Variable Frequency Drive (VFD) water pump panel |
| **Thermal & Acoustic Insulation** | 1 | Pipe insulation work |
| **Architectural Fabrication** | 1 | UPVC partition walls for microbiology laboratory |
| **Commercial Services & Food Hygiene** | 1 | Low-Oil Food Outlet catering establishment (BOT) |

---

## 3. Step-by-Step Instructions for Manual Verification

For each row in [`dataset/ground_truth/ground_truth.csv`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/dataset/ground_truth/ground_truth.csv):

1. **Read Requirement & Trace to PDF**:
   - Note the `tender_id` (e.g. `T001`) and `source_page` (e.g. `1`).
   - If context is needed, review the corresponding tender summary JSON in `dataset/extraction_results/T001.json` or the PDF in `tenders/raw/`.

2. **Cross-Reference Against Indian Standards**:
   - Check our audited 54 BIS standards repository in `data/standards/standards.xlsx`.
   - For additional standards, search the official BIS Manakonline / BSB Edge portal (`standardsbis.bsbedge.com`).
   - Identify the primary applicable standard (e.g., for *GI pipe*, the standard is `IS 1239 (Part 1)`).

3. **Verify Standard Currency**:
   - Confirm whether the standard is currently **Active** or has been **Withdrawn/Superseded**.
   - If superseded, enter the superseding standard number and note the transition year in `reviewer_notes`.

4. **Populate Verified Fields**:
   - `applicable_standard`: Official IS code (e.g. `IS 15778 : 2007`).
   - `standard_title`: Official title from BIS catalogue.
   - `standard_status`: `Active` or `Withdrawn`.
   - `reasoning`: A concise sentence explaining why this standard governs this requirement.
   - `confidence`: `High` (if standard is unambiguous or mandatory under a Quality Control Order), `Medium`, or `Low`.
   - `human_verified`: Set to `TRUE`.
   - `reviewer_notes`: Any relevant QCO orders (e.g., *Pipes QCO 2023*), dual numbering with ISO/IEC, or scope exclusions.

---

## 4. Evidence Quality Checklist

Before marking `human_verified = TRUE`, verify the following 5 quality criteria:

- [ ] **Traceability**: The requirement text is directly grounded in the source PDF and not synthesized or embellished.
- [ ] **Authenticity**: The proposed standard actually exists in the Bureau of Indian Standards catalogue (no hallucinations or simulated standard numbers).
- [ ] **Scope Alignment**: The scope of the Indian Standard covers the specific product, material grade, or test method demanded by the tender.
- [ ] **Currency Verification**: Checked whether the standard is current or superseded by a recent revision (e.g., IS 432:1982 transitioning to IS 432:2026).
- [ ] **Objective Reasoning**: The `reasoning` articulates the technical connection between the tender requirement and the standard's scope.
