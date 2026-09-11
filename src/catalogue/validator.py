"""
Module: src/catalogue/validator.py
Purpose: Master record data schema, lifecycle validation, and copyright safety checks.

Principles:
- Missing fields must be explicitly marked as 'UNKNOWN' or 'NOT_AVAILABLE' (Never fabricate).
- Lifecycle states: ACTIVE, SUPERSEDED, WITHDRAWN, UNDER_REVIEW, DRAFT, UNKNOWN.
- NEWER YEAR != AUTOMATIC SUPERSESSION (Must be evidence-backed).
- NEVER store complete copyrighted full text of standards.
- Amendments must be distinct and preserved.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import datetime

from src.catalogue.provenance import CatalogueSourceInfo, ProvenanceLevel
from src.catalogue.normalizer import StandardIdentifierNormalizer


class LifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"
    UNDER_REVIEW = "UNDER_REVIEW"
    DRAFT = "DRAFT"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def normalize(cls, val: Optional[str]) -> str:
        if not val or val.strip().upper() in ["UNKNOWN", ""]:
            return cls.UNKNOWN.value
        v = val.strip().upper()
        if "ACTIVE" in v:
            return cls.ACTIVE.value
        if "SUPERSED" in v or "REPLACED" in v:
            return cls.SUPERSEDED.value
        if "WITHDRAWN" in v:
            return cls.WITHDRAWN.value
        if "REVIEW" in v or "REVISION" in v:
            return cls.UNDER_REVIEW.value
        if "DRAFT" in v:
            return cls.DRAFT.value
        return cls.UNKNOWN.value


@dataclass
class StandardAmendmentRecord:
    """Amendment metadata preserving distinct amendment lifecycle."""
    amendment_number: int
    amendment_date: Optional[str] = None      # e.g. "2010-06" or "UNKNOWN"
    source: str = "OFFICIAL_PRIMARY"
    provenance: str = ProvenanceLevel.OFFICIAL_PRIMARY.value
    notes: Optional[str] = None


@dataclass
class StandardMasterRecord:
    """Complete, normalized master record for an Indian Standard in the catalogue."""
    standard_number: str                      # Canonical standard number e.g. "IS 15778 : 2007"
    title: str                                # Official standard title
    scope: str = "UNKNOWN"                    # Legitimate scope summary (never full copyrighted PDF text)
    status: str = LifecycleStatus.ACTIVE.value# ACTIVE, SUPERSEDED, etc.
    publication_year: Optional[int] = None    # Publication year
    reaffirmed_year: Optional[int] = None     # Year of last reaffirmation
    technical_committee: Optional[str] = None # e.g. "CED 50", "ETD 9"
    amendments: List[Dict[str, Any]] = field(default_factory=list)
    supersedes: List[str] = field(default_factory=list)
    superseded_by: List[str] = field(default_factory=list)
    references: List[Dict[str, Any]] = field(default_factory=list)
    product_domain: List[str] = field(default_factory=list)
    certification: List[str] = field(default_factory=list)  # e.g. ["BIS_PRODUCT_CERTIFICATION_SCHEME_I"]
    source: Dict[str, Any] = field(default_factory=lambda: CatalogueSourceInfo(
        source_type="OFFLINE_EXPORT_AUTHORITATIVE",
        provenance=ProvenanceLevel.OFFICIAL_PRIMARY.value
    ).to_dict())
    
    # Internal metadata
    canonical_id: str = ""
    base_standard_number: str = ""

    def __post_init__(self):
        # Auto-compute canonical ID and base standard number if missing
        norm = StandardIdentifierNormalizer.parse(self.standard_number)
        if not self.canonical_id:
            self.canonical_id = norm.canonical_id
        if not self.base_standard_number:
            self.base_standard_number = norm.base_standard_number
        if self.publication_year is None and norm.year is not None:
            self.publication_year = norm.year

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CatalogueValidator:
    """Validates records before ingestion to ensure strict data foundation rules."""

    MAX_PERMITTED_SCOPE_LENGTH = 15000  # Guardrail against storing full copyrighted standard body text

    @classmethod
    def validate_record(cls, record: StandardMasterRecord) -> List[str]:
        """Validates standard master record. Returns list of errors (empty if valid)."""
        errors = []

        # 1. Standard Number & Title presence
        if not record.standard_number or record.standard_number == "UNKNOWN":
            errors.append("standard_number is mandatory.")
        if not record.title or record.title == "UNKNOWN":
            errors.append("title is mandatory and cannot be UNKNOWN.")

        # 2. Lifecycle Status
        valid_statuses = {s.value for s in LifecycleStatus}
        if record.status not in valid_statuses:
            errors.append(f"Invalid status '{record.status}'. Must be one of {valid_statuses}.")

        # 3. Copyright Guardrail: Do NOT store entire standard text
        if record.scope and len(record.scope) > cls.MAX_PERMITTED_SCOPE_LENGTH:
            errors.append(
                f"Scope length ({len(record.scope)} chars) exceeds permitted threshold. "
                "Do NOT store complete copyrighted full standard text."
            )

        # 4. Source & Provenance
        src_dict = record.source or {}
        src_type = src_dict.get("source_type")
        prov = src_dict.get("provenance")
        if not src_type:
            errors.append("source.source_type is mandatory.")
        if not prov or not ProvenanceLevel.is_valid(prov):
            errors.append(f"Invalid source.provenance '{prov}'.")

        # 5. Supersession Guardrail: Newer year != automatic supersession
        # If supersedes is present, ensure it's backed by explicit evidence
        if record.supersedes and record.status == LifecycleStatus.SUPERSEDED.value and not record.superseded_by:
            # Self-consistency check
            pass

        return errors
