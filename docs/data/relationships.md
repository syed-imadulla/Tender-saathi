# Standards Relationships Dataset Reference

This document details the verified standards relationship dataset maintained in **Tender Saathi** at [`data/standards/relationships.json`](../../data/standards/relationships.json).

---

## 1. Dataset Overview

The dataset defines **72 verified relationships** connecting core Indian Standards across five key public procurement demonstration domains.

- **Storage Location**: `data/standards/relationships.json`
- **Total Relationships**: 72
- **Provenance Distribution**: 100% `VERIFIED` or `CURATED` (0 `INFERRED` records)
- **Active Demonstration Domains**: 5

```text
Relationships by Demonstration Domain:
  ├── Civil & Water Distribution (CPVC, concrete pipes, ductile iron, HDPE)
  ├── Electrical Systems (LT/HT XLPE power cables, wiring, earthing codes)
  ├── Mechanical & Fluid Control (Gate valves, butterfly valves, check valves)
  ├── Pumping Machinery (Submersible pumpsets, centrifugal pumps, motors)
  └── Food & Canteen Hygiene (Commercial canteen hygiene, food-grade plastics, HACCP)
```

---

## 2. Record Schema

Each relationship entry in `data/standards/relationships.json` conforms to the following schema:

```json
{
  "source_standard": "IS 15778",
  "target_standard": "IS 12235",
  "relationship_type": "TEST_METHOD",
  "description": "Methods of test for unplasticized and chlorinated polyvinyl chloride pipes.",
  "provenance": "VERIFIED",
  "source_clause": "Clause 8.1 (Physical and Mechanical Tests)",
  "confidence": 1.0,
  "domain": "civil_plumbing"
}
```

### Field Definitions:
- `source_standard`: The standard defining or referencing the relationship.
- `target_standard`: The companion, testing, normative, or superseded standard.
- `relationship_type`: One of the 8 canonical types (`NORMATIVE_REFERENCE`, `TEST_METHOD`, `INSTALLATION_CODE`, `SAFETY_STANDARD`, `TERMINOLOGY_STANDARD`, `ALLIED_STANDARD`, `SUPERSEDES`, `AMENDS`).
- `provenance`: Must be `VERIFIED` (backed by verbatim clause text in the published standard) or `CURATED` (verified by sectional committee technical officers).
- `source_clause`: Specific clause or section in `source_standard` where the target standard is cited.
- `confidence`: Confidence score ($1.0$ for verified relationships).
- `domain`: Engineering domain tag for domain-aware filtering.

---

## 3. Directionality & Supersedence Mapping

For supersedence edges:
- `source_standard` is the **active modern standard** (e.g. `IS/ISO 10434 : 2020`).
- `relationship_type` is `SUPERSEDES`.
- `target_standard` is the **withdrawn/replaced standard** (e.g. `IS 10611 : 1983`).

When a query cites the older standard `IS 10611`, the engine reverses this edge via `SUPERSEDED_BY` logic in [`src/dependencies.py`](../../src/dependencies.py) to resolve the active successor `IS/ISO 10434`.
