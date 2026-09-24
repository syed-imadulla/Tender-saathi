# BIS Catalogue Data Architecture

This document describes the structure, provenance, and management of the national Bureau of Indian Standards (BIS) catalogue in **Tender Saathi**.

---

## 1. Catalogue Overview & Storage

Tender Saathi maintains two distinct standards database layers to balance comprehensive national catalogue coverage with deep clause-level evidence grounding:

| Database File | Record Count | Scope & Role |
| :--- | :---: | :--- |
| [`data/catalogue/bis_catalogue.db`](../../data/catalogue/bis_catalogue.db) | **35,208** | Normalized national BIS standards catalogue metadata across all engineering divisions |
| [`data/standards/standards.db`](../../data/standards/standards.db) | **90** | Working standards database populated with verbatim clause text, scope excerpts, and deep evidence chains |

---

## 2. National Catalogue Schema (`bis_catalogue.db`)

The SQLite database at `data/catalogue/bis_catalogue.db` contains 35,208 validated records structured as follows:

```sql
CREATE TABLE standards (
    id TEXT PRIMARY KEY,                       -- e.g. "IS-15778-2007"
    standard_number TEXT NOT NULL,             -- e.g. "IS 15778"
    year INTEGER,                              -- Publication year, e.g. 2007
    title TEXT NOT NULL,                       -- Official BIS standard title
    status TEXT DEFAULT 'Active',              -- 'Active', 'Superseded', 'Withdrawn'
    reaffirmed_year INTEGER,                   -- e.g. 2022
    amendments_count INTEGER DEFAULT 0,        -- Number of official amendments
    technical_committee TEXT,                  -- Sectional committee, e.g. "CED 50"
    ics_code TEXT,                             -- International Classification for Standards
    scope_text TEXT,                           -- Authoritative scope clause extract
    keywords TEXT,                             -- Extracted technical keywords
    ingested_at TEXT,                          -- ISO8601 timestamp
    source_provenance TEXT DEFAULT 'BIS_PORTAL'-- Provenance tracking tier
);
```

### Supporting Tables in `bis_catalogue.db`:
- `quarantine_records` (391 records): Standards flagged during ingestion for manual deduplication or incomplete gazette numbering.
- `catalogue_snapshots`: Tracks historical manifest snapshots.
- `catalogue_change_history` (42 records): Audit log tracking status transitions and metadata updates.

---

## 3. Catalogue Boundaries & Provenance

1. **Strict BIS-Only Scope**:
   `bis_catalogue.db` strictly contains standards published by the Bureau of Indian Standards (including dual-numbered harmonized standards like `IS/ISO` and `IS/IEC`).
2. **External Authority Isolation**:
   External ministerial or regulatory standards (such as FSSAI regulations, CEA electrical codes, or CPWD manuals) are **strictly barred** from entering `bis_catalogue.db`. They reside exclusively in the decoupled advisory layer (`src/regulatory/external_authority.py`).
3. **Immutability of Frozen Assets**:
   The database is version-controlled and protected from unverified runtime mutations.
