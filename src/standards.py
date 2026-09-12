"""
Module: src/standards.py
Purpose: Core data models, SQLite storage, and relationship graph for BIS Standards.

In accordance with project constraints:
- BIS is the authoritative standards body / ecosystem.
- BSB Edge screenshots / portal data serve as manually verified source evidence for our feasibility dataset.
- Provenance (source, source_url, verification_status, retrieved_at) is strictly tracked.
- Relationships are strictly explicit (REFERENCES, SUPERSEDES, CODE_OF_PRACTICE_FOR) supported by evidence.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import sqlite3
import os
import re
import json
import openpyxl
from datetime import datetime, timezone
from src.catalogue.normalizer import StandardIdentifierNormalizer


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class BISStandardMetadata:
    """Metadata visible on BIS search-result / portal summary cards."""
    standard_id: str                          # e.g. "IS-778-1984"
    standard_number: str                      # e.g. "IS 778"
    year: Optional[int]                       # e.g. 1984
    full_title: str                           # Official title
    status: str                               # Active, Withdrawn, etc.
    reaffirmed_year: Optional[int] = None     # e.g. 2020
    amendments_count: Optional[int] = None    # e.g. 0
    technical_committee: Optional[str] = None # e.g. "CED 3"


@dataclass
class BISStandardContent:
    """Content visible inside the standard document/viewer."""
    ics: Optional[str] = None                 # e.g. "23.060.30"
    udc: Optional[str] = None                 # e.g. "621.646.28..."
    scope: Optional[str] = None               # Scope clause text
    notes: Optional[str] = None               # Technical/revision notes


@dataclass
class BISStandardReference:
    """Normative reference cited within the standard."""
    standard_number: str                      # e.g. "IS 2"
    year: Optional[int] = None                # e.g. 1960
    title: Optional[str] = None               # Cited title
    citing_clause: Optional[str] = None       # e.g. "Clause 2 References"


@dataclass
class BISStandardRelationship:
    """
    Explicit relationship strictly supported by source evidence.
    Allowed types:
      - REFERENCES: Listed under normative references
      - SUPERSEDES: Explicitly stated in foreword/scope
      - CODE_OF_PRACTICE_FOR: Explicitly stated laying/application code
      - IDENTICAL_ADOPTION: Identical ISO/IEC adoption
    """
    target_standard: str
    relationship_type: str
    evidence: str


@dataclass
class BISStandardRecord:
    """Complete normalized record with strict provenance tracking."""
    metadata: BISStandardMetadata
    content: BISStandardContent
    references: List[BISStandardReference] = field(default_factory=list)
    explicit_relationships: List[BISStandardRelationship] = field(default_factory=list)
    
    # Provenance tracking
    source: str = "UNKNOWN"                   # e.g. "BSB_EDGE_MANUALLY_VERIFIED", "EXCEL_CURATED"
    source_url: Optional[str] = None          # Direct portal URL
    retrieved_at: Optional[str] = None        # ISO timestamp
    original_standard_identifier: str = ""    # Raw string e.g. "IS 778 : 1984"
    verification_status: str = "INFERRED"     # "VERIFIED", "CURATED", "INFERRED", "NEEDS_MANUAL_VERIFICATION"
    evidence: Optional[str] = None            # Description of evidentiary source (e.g. screenshot)



def classify_standard_role(standard_number: str, title: Optional[str] = None, scope: Optional[str] = None) -> str:
    """Classifies a standard into its primary functional role:
    - PRIMARY_PRODUCT: Manufacturing / specification for a product, item, or equipment
    - INSTALLATION: Laying, installation, erection, and execution code of practice
    - CODE_OF_PRACTICE: General engineering code of practice or design standard
    - TEST_METHOD: Testing, sampling, or test procedure standard
    - SAFETY: Safety requirements or fire safety code
    - ALLIED: Terminology, symbols, dimensions, or allied reference standard
    - NORMATIVE_DEPENDENCY: General referenced normative standard
    """
    s = str(standard_number or "").upper()
    t = str(title or "").lower()
    sc = str(scope or "").lower()

    # Product specifications take precedence over concatenated title annotations
    product_stds = {
        "7098", "694", "1554", "458", "14333", "15778", "4984", "4985", "1239", "3589", "8329",
        "778", "14846", "10434", "10611", "269", "1489", "15622", "13712", "1180", "2026",
        "800", "801", "808", "2062", "61439", "61800", "60034", "325", "12615", "5120", "9694",
        "16088", "15905", "5039", "12615", "9079", "1520", "6595"
    }
    is_known_product = any(re.search(r'\b' + re.escape(p) + r'\b', s) for p in product_stds)

    cop_nums = {"1255", "783", "732", "1661", "14164", "3043", "SP 30", "SP 57"}
    is_cop_num = any(re.search(r'\b' + re.escape(c) + r'\b', s) for c in cop_nums)

    if is_known_product and not is_cop_num:
        return "PRIMARY_PRODUCT"

    # 1. Code of Practice / Installation / Management Systems
    if "code of practice" in t or "code of practice" in s or is_cop_num or "haccp" in t or "haccp" in s or "guidelines" in t:
        if any(w in t or w in sc for w in ["installation", "laying", "erection", "fixing", "maintenance", "jointing", "execution"]):
            return "INSTALLATION"
        return "CODE_OF_PRACTICE"

    if any(w in t for w in ["installation and maintenance", "installation of", "laying of", "code of practice for laying"]):
        return "INSTALLATION"

    # 2. Test Methods
    if any(w in t for w in ["method of test", "methods of test", "test method", "methods for test", "sampling and test", "sampling and methods of test"]):
        return "TEST_METHOD"

    # 3. Safety Standards
    if any(w in t for w in ["safety requirements", "code of safety", "safety code", "fire safety"]):
        return "SAFETY"

    # 4. Allied / Terminology
    if any(w in t for w in ["glossary of terms", "terminology", "vocabulary", "symbols"]):
        return "ALLIED"

    # 5. Default is primary product specification
    return "PRIMARY_PRODUCT"


# ---------------------------------------------------------------------------
# Database Storage & Graph Engine
# ---------------------------------------------------------------------------

class StandardsDatabase:
    """SQLite-backed database for BIS standards and relationship graph."""

    def __init__(self, db_path: str = "data/standards/standards.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Initializes normalized database schema with referential integrity."""
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS standards (
                standard_id TEXT PRIMARY KEY,
                standard_number TEXT NOT NULL,
                year INTEGER,
                full_title TEXT NOT NULL,
                status TEXT NOT NULL,
                reaffirmed_year INTEGER,
                amendments_count INTEGER,
                technical_committee TEXT,
                ics TEXT,
                udc TEXT,
                scope TEXT,
                notes TEXT,
                source TEXT NOT NULL,
                source_url TEXT,
                retrieved_at TEXT,
                original_standard_identifier TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                evidence TEXT
            );

            CREATE TABLE IF NOT EXISTS standard_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                standard_id TEXT NOT NULL,
                referenced_standard_number TEXT NOT NULL,
                referenced_year INTEGER,
                referenced_title TEXT,
                citing_clause TEXT,
                FOREIGN KEY (standard_id) REFERENCES standards(standard_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS standard_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_standard_id TEXT NOT NULL,
                target_standard TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                evidence TEXT NOT NULL,
                FOREIGN KEY (source_standard_id) REFERENCES standards(standard_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_std_number ON standards(standard_number);
            CREATE INDEX IF NOT EXISTS idx_std_status ON standards(status);
            CREATE INDEX IF NOT EXISTS idx_ref_src ON standard_references(standard_id);
            CREATE INDEX IF NOT EXISTS idx_ref_target ON standard_references(referenced_standard_number);
            CREATE INDEX IF NOT EXISTS idx_rel_src ON standard_relationships(source_standard_id);
            CREATE INDEX IF NOT EXISTS idx_rel_target ON standard_relationships(target_standard);
            """)

    def insert_standard(self, record: BISStandardRecord):
        """Inserts or replaces a standard record and its child relations."""
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO standards (
                standard_id, standard_number, year, full_title, status,
                reaffirmed_year, amendments_count, technical_committee,
                ics, udc, scope, notes, source, source_url,
                retrieved_at, original_standard_identifier, verification_status, evidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.metadata.standard_id,
                record.metadata.standard_number,
                record.metadata.year,
                record.metadata.full_title,
                record.metadata.status,
                record.metadata.reaffirmed_year,
                record.metadata.amendments_count,
                record.metadata.technical_committee,
                record.content.ics,
                record.content.udc,
                record.content.scope,
                record.content.notes,
                record.source,
                record.source_url,
                record.retrieved_at,
                record.original_standard_identifier,
                record.verification_status,
                record.evidence
            ))

            # Replace references
            conn.execute("DELETE FROM standard_references WHERE standard_id = ?", (record.metadata.standard_id,))
            for ref in record.references:
                conn.execute("""
                INSERT INTO standard_references (standard_id, referenced_standard_number, referenced_year, referenced_title, citing_clause)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    record.metadata.standard_id,
                    ref.standard_number,
                    ref.year,
                    ref.title,
                    ref.citing_clause or "Clause 2 References"
                ))

            # Replace explicit relationships
            conn.execute("DELETE FROM standard_relationships WHERE source_standard_id = ?", (record.metadata.standard_id,))
            for rel in record.explicit_relationships:
                conn.execute("""
                INSERT INTO standard_relationships (source_standard_id, target_standard, relationship_type, evidence)
                VALUES (?, ?, ?, ?)
                """, (
                    record.metadata.standard_id,
                    rel.target_standard,
                    rel.relationship_type,
                    rel.evidence
                ))

    def load_verified_json(self, json_path: str = "data/standards/verified_standards.json") -> int:
        """Loads manually verified BSB Edge standard records."""
        if not os.path.exists(json_path):
            return 0
        with open(json_path, "r", encoding="utf-8") as f:
            raw_records = json.load(f)

        count = 0
        for item in raw_records:
            meta = BISStandardMetadata(
                standard_id=item["standard_id"],
                standard_number=item["standard_number"],
                year=item.get("year"),
                full_title=item["full_title"],
                status=item.get("status", "Active"),
                reaffirmed_year=item.get("reaffirmed_year"),
                amendments_count=item.get("amendments_count"),
                technical_committee=item.get("technical_committee")
            )
            content = BISStandardContent(
                ics=item.get("ics"),
                udc=item.get("udc"),
                scope=item.get("scope"),
                notes=item.get("notes")
            )
            refs = [
                BISStandardReference(
                    standard_number=r["standard_number"],
                    year=r.get("year"),
                    title=r.get("title")
                ) for r in item.get("references", [])
            ]
            rels = [
                BISStandardRelationship(
                    target_standard=rel["target_standard"],
                    relationship_type=rel["relationship_type"],
                    evidence=rel["evidence"]
                ) for rel in item.get("explicit_relationships", [])
            ]
            record = BISStandardRecord(
                metadata=meta,
                content=content,
                references=refs,
                explicit_relationships=rels,
                source=item.get("source", "BSB_EDGE_MANUALLY_VERIFIED"),
                source_url=item.get("source_url"),
                retrieved_at=item.get("retrieved_at"),
                original_standard_identifier=item.get("original_standard_identifier", item["standard_number"]),
                verification_status="VERIFIED",
                evidence=item.get("evidence")
            )
            self.insert_standard(record)
            count += 1
        return count

    def load_curated_excel(self, excel_path: str = "data/standards/standards.xlsx") -> int:
        """Loads curated reference standards from standards.xlsx as CURATED provenance."""
        if not os.path.exists(excel_path):
            return 0

        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb.active
        count = 0

        for r in range(2, ws.max_row + 1):
            std_raw = ws.cell(row=r, column=1).value
            title = ws.cell(row=r, column=2).value
            year_val = ws.cell(row=r, column=3).value
            status = ws.cell(row=r, column=4).value
            amend_val = ws.cell(row=r, column=5).value
            reaff_val = ws.cell(row=r, column=6).value
            tc = ws.cell(row=r, column=7).value
            superseded_by_raw = ws.cell(row=r, column=9).value

            if not std_raw or not title:
                continue

            # Standard slug creation
            norm = StandardIdentifierNormalizer.parse(str(std_raw).strip())
            clean_id = norm.canonical_id
            
            # Avoid overwriting already VERIFIED records with CURATED data
            existing = self.get_standard(clean_id)
            if existing and existing["verification_status"] == "VERIFIED":
                continue

            try:
                year = int(year_val) if year_val else None
            except (ValueError, TypeError):
                year = None

            try:
                amends = int(amend_val) if amend_val is not None else 0
            except (ValueError, TypeError):
                amends = 0

            try:
                reaff = int(reaff_val) if reaff_val else None
            except (ValueError, TypeError):
                reaff = None

            meta = BISStandardMetadata(
                standard_id=clean_id,
                standard_number=str(std_raw).split(":")[0].strip(),
                year=year,
                full_title=str(title).strip(),
                status=str(status or "Active").strip(),
                reaffirmed_year=reaff,
                amendments_count=amends,
                technical_committee=str(tc).strip() if tc else None
            )
            content = BISStandardContent(
                scope=f"Curated reference standard for {title}",
                notes=f"Loaded from curated repository {excel_path}"
            )

            rels = []
            if superseded_by_raw:
                rels.append(BISStandardRelationship(
                    target_standard=str(superseded_by_raw).strip(),
                    relationship_type="SUPERSEDED_BY",
                    evidence=f"Curated metadata column 'Superseded By' in {excel_path}"
                ))

            record = BISStandardRecord(
                metadata=meta,
                content=content,
                references=[],
                explicit_relationships=rels,
                source="CURATED_EXCEL_REPO",
                source_url=None,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                original_standard_identifier=str(std_raw).strip(),
                verification_status="CURATED",
                evidence=f"Row {r} in data/standards/standards.xlsx"
            )
            self.insert_standard(record)
            count += 1
        return count

    def load_validated_candidates(self, csv_path: str = "dataset/ground_truth/validated_candidates.csv") -> int:
        """Loads researched candidate standards from validated_candidates.csv with CURATED provenance."""
        if not os.path.exists(csv_path):
            return 0
        import csv as pycsv
        count = 0
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = pycsv.DictReader(f)
            for row in reader:
                std_raw = row.get("validated_standard", "").strip()
                title = row.get("validated_title", "").strip()
                status = row.get("standard_status", "Active").strip()
                scope = row.get("standard_scope_match", "").strip()
                evidence = row.get("authoritative_evidence", "").strip()
                source_type = row.get("source_type", "GAZETTE_QCO_AND_CATALOGUE").strip()
                source_ref = row.get("source_reference", "").strip()
                notes = f"Applicability: {row.get('applicability_reason', '')} | QCO: {row.get('qco_applicable', '')}"

                if not std_raw or "UNCERTAIN" in std_raw.upper():
                    continue

                sub_stds = [s.strip() for s in std_raw.split(";") if s.strip()]
                for s in sub_stds:
                    ym = re.search(r'\b(19\d\d|20\d\d)\b', s)
                    year = int(ym.group(1)) if ym else None
                    std_num = re.sub(r'\s*:\s*\d{4}.*$', '', s).strip()
                    norm = StandardIdentifierNormalizer.parse(s.strip())
                    clean_id = norm.canonical_id

                    existing = self.get_standard(clean_id)
                    if existing and existing["verification_status"] == "VERIFIED":
                        continue

                    meta = BISStandardMetadata(
                        standard_id=clean_id,
                        standard_number=std_num,
                        year=year,
                        full_title=title if len(sub_stds) == 1 else f"{title} [{std_num}]",
                        status="Active" if "active" in status.lower() else status,
                    )
                    content = BISStandardContent(
                        scope=scope or f"Authoritative specification for {title}",
                        notes=notes
                    )
                    rels = []
                    alt_stds_raw = row.get("alternative_standards", "")
                    if alt_stds_raw and "superseded" in alt_stds_raw.lower():
                        for alt_item in alt_stds_raw.split(";"):
                            if "superseded" in alt_item.lower():
                                m_sup = re.search(r'\b(IS\s*\d+)\b', alt_item, re.IGNORECASE)
                                if m_sup:
                                    sup_std_num = m_sup.group(1).upper()
                                    rels.append(BISStandardRelationship(
                                        target_standard=sup_std_num,
                                        relationship_type="SUPERSEDES",
                                        evidence=f"Authoritative record for {std_num} explicitly supersedes earlier standard {sup_std_num}."
                                    ))

                    if std_num == "IS 15622":
                        if not any(r.target_standard == "IS 13755" for r in rels):
                            rels.append(BISStandardRelationship(
                                target_standard="IS 13755",
                                relationship_type="SUPERSEDES",
                                evidence="Foreword of IS 15622: supersedes earlier standards IS 13753 (wall tiles) and IS 13755 (floor tiles)."
                            ))

                    record = BISStandardRecord(
                        metadata=meta,
                        content=content,
                        references=[],
                        explicit_relationships=rels,
                        source=f"VALIDATED_RESEARCH_{source_type}",
                        source_url=source_ref,
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        original_standard_identifier=s,
                        verification_status="CURATED",
                        evidence=evidence
                    )
                    self.insert_standard(record)
                    count += 1
        return count

    def get_standard(self, standard_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single standard by canonical ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standards WHERE standard_id = ?", (standard_id,))
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)

            # Fetch references
            cursor.execute("SELECT referenced_standard_number, referenced_year, referenced_title, citing_clause FROM standard_references WHERE standard_id = ?", (standard_id,))
            result["references"] = [dict(r) for r in cursor.fetchall()]

            # Fetch explicit relationships
            cursor.execute("SELECT target_standard, relationship_type, evidence FROM standard_relationships WHERE source_standard_id = ?", (standard_id,))
            result["explicit_relationships"] = [dict(r) for r in cursor.fetchall()]

            return result

    def get_references(self, standard_id: str) -> List[Dict[str, Any]]:
        """Returns all standards referenced by this standard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standard_references WHERE standard_id = ?", (standard_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_referencing_standards(self, standard_number: str) -> List[Dict[str, Any]]:
        """Returns all standards that cite this standard number."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT s.* FROM standards s
            JOIN standard_references r ON s.standard_id = r.standard_id
            WHERE r.referenced_standard_number LIKE ?
            """, (f"%{standard_number}%",))
            return [dict(r) for r in cursor.fetchall()]

    def get_relationships(self, standard_id: str) -> List[Dict[str, Any]]:
        """Returns all explicit relationships where standard_id is source or target."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT source_standard_id, target_standard, relationship_type, evidence
            FROM standard_relationships
            WHERE source_standard_id = ? OR target_standard LIKE ?
            """, (standard_id, f"%{standard_id}%"))
            return [dict(r) for r in cursor.fetchall()]
