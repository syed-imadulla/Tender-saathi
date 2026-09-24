# Statutory Boundaries & External Regulatory Intelligence

This document details the architectural boundaries governing external statutory and ministerial regulations in **Tender Saathi** ([`src/regulatory/external_authority.py`](../../src/regulatory/external_authority.py)).

---

## 1. Architectural Separation

In public procurement, technical specifications must align not only with national Bureau of Indian Standards (`IS`) codes, but also with statutory regulations gazetted by line ministries and public works authorities.

However, mixing ministerial specifications directly into the national standards catalogue creates catastrophic data pollution:
- External regulations often cite standards without being standards themselves.
- They change on departmental notification schedules rather than BIS review cycles.
- Conflating them with BIS codes compromises provenance and verification integrity.

To solve this, Tender Saathi enforces a **strict architectural boundary**:

```text
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│       Core Standards Database        │     │  Decoupled Regulatory Advisory Layer │
│   (standards.db & bis_catalogue.db)  │     │ (src/regulatory/external_authority.py)│
├──────────────────────────────────────┤     ├──────────────────────────────────────┤
│ • BIS standards only (IS, IS/ISO)    │     │ • FSSAI Packaging Regulations, 2018  │
│ • Official titles, years, committees │     │ • CEA Electrical Safety Regs, 2023   │
│ • Verbatim published scope clauses   │     │ • CPWD Works Specifications, 2019/23 │
│ • Verified relationships only        │     │ • Domain heuristic triggers          │
│ • Candidate standard source          │     │ • Advisory signals only (NOT stds)   │
└──────────────────────────────────────┘     └──────────────────────────────────────┘
                  ▲                                             ▲
                  │                                             │
                  └────────────── Strict Separation ────────────┘
                        (Zero Foreign Data Infiltration)
```

---

## 2. Implemented Statutory Authorities

In Phase 9, Tender Saathi implemented verified advisory heuristics for three primary public procurement domains:

### 1. FSSAI — Food Safety and Standards Authority of India
- **Statutory Instrument**: *Food Safety and Standards (Packaging) Regulations, 2018* (Regulation 4(4) and Schedule I).
- **Linked Standards**: `IS 10146`, `IS 10151`, `IS 15000`, `IS 2491`.
- **Advisory Role**: In commercial canteen, kitchen, or food-contact procurement, alerts technical officers that plastics in direct contact with food or potable water must comply with prescribed Indian Standards, and handling facilities require HACCP hygiene compliance.

### 2. CEA — Central Electricity Authority
- **Statutory Instrument**: *CEA (Measures relating to Safety and Electric Supply) Regulations, 2023* (Regulations 29, 35, 43, 67).
- **Linked Standards**: `IS 3043`, `IS 732`, `IS 1255`, `IS 7098`, `IS 2026`, `IS 1180`.
- **Advisory Role**: Mandates strict adherence to Indian Standards for electrical earthing (`IS 3043`), building wiring execution (`IS 732`), underground cable installation (`IS 1255`), and distribution transformers (`IS 1180`) in public supplies.

### 3. CPWD — Central Public Works Department
- **Statutory Instrument**: *CPWD Specifications 2019 / 2023 (Civil & Electrical Works)* (Sections 19, 20, 31).
- **Linked Standards**: `IS 458`, `IS 783`, `IS 1239`, `IS 4985`, `IS 15778`, `IS 15905`, `IS 732`.
- **Advisory Role**: Recommends mandatory execution codes for laying, jointing, and pressure testing water supply and drainage conduits in central government works.

---

## 3. Strict Boundary Rules

1. **External Authorities Cannot Become Candidate Standards**:
   The engine will never output `candidate_standard = "FSSAI Regulation 4"`. Candidates must originate strictly from the BIS catalogue.
2. **Zero Database Contamination**:
   External regulations are stored in Python registry data structures and are never written to `standards.db` or `bis_catalogue.db`.
3. **Mandatory Advisory Disclaimer**:
   Every regulatory signal carries the statutory notice:
   > *"Regulatory signals are advisory engineering heuristics based on published statutory frameworks and gazette notifications. They do not constitute statutory legal certifications or official compliance certificates."*
