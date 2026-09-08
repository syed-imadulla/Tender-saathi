"""
Module: src/evidence.py
Purpose: Evidence grounding and claim verification for BIS standards answers.

Implements an evidence-grounding constraint:
- Every factual claim about an Indian Standard must map to retrieved source evidence.
- If evidence cannot be verified from the retrieved standard content or metadata, returns:
  'Insufficient evidence from the retrieved BIS standard.'
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from src.standards import StandardsDatabase
from src.search import SearchResult


@dataclass
class EvidenceClaim:
    claim: str
    source_standard: str
    source_section: str                     # e.g. "Scope", "Foreword", "References", "Metadata"
    source_text: str                        # The exact verbatim or normalized snippet
    evidence_type: str                      # "VERIFIED_PORTAL_VIEWER", "VERIFIED_PORTAL_SUMMARY", "CURATED_CATALOGUE"
    confidence: float                       # 0.0 to 1.0
    is_grounded: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceVerifier:
    """Verifies factual claims against the retrieved standard data."""

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db or StandardsDatabase()

    def verify_claim(
        self,
        claim: str,
        standard_id: str,
        expected_section: str = "Scope"
    ) -> EvidenceClaim:
        """
        Validates if a claim regarding a standard can be grounded in retrieved evidence.
        If no evidence exists in the standard's record, returns an ungrounded claim.
        """
        std = self.db.get_standard(standard_id)
        if not std:
            return EvidenceClaim(
                claim=claim,
                source_standard=standard_id,
                source_section=expected_section,
                source_text="Insufficient evidence from the retrieved BIS standard.",
                evidence_type="NONE",
                confidence=0.0,
                is_grounded=False
            )

        # Inspect section text
        source_text = None
        evidence_type = "VERIFIED_PORTAL_VIEWER" if std["verification_status"] == "VERIFIED" else "CURATED_CATALOGUE"

        if expected_section.lower() in ["scope", "application"]:
            source_text = std.get("scope")
        elif expected_section.lower() in ["references", "cited_standards"]:
            refs = [r["referenced_standard_number"] for r in std.get("references", [])]
            source_text = "; ".join(refs) if refs else None
        elif expected_section.lower() in ["foreword", "supersedes", "relationships"]:
            rels = [f"{r['relationship_type']} {r['target_standard']}: {r['evidence']}" for r in std.get("explicit_relationships", [])]
            source_text = "; ".join(rels) if rels else None
        elif expected_section.lower() in ["metadata", "status", "reaffirmation"]:
            source_text = f"Status: {std['status']}, Reaffirmed: {std.get('reaffirmed_year')}, Committee: {std.get('technical_committee')}"

        if not source_text or "insufficient" in source_text.lower():
            return EvidenceClaim(
                claim=claim,
                source_standard=std["original_standard_identifier"],
                source_section=expected_section,
                source_text="Insufficient evidence from the retrieved BIS standard.",
                evidence_type="INSUFFICIENT_INFORMATION",
                confidence=0.0,
                is_grounded=False
            )

        # Check keyword or semantic overlap with claim
        claim_words = [w.lower() for w in claim.split() if len(w) > 3]
        matching_words = [w for w in claim_words if w in source_text.lower()]
        
        confidence = min(1.0, (len(matching_words) / len(claim_words))) if claim_words else 0.5

        return EvidenceClaim(
            claim=claim,
            source_standard=std["original_standard_identifier"],
            source_section=expected_section,
            source_text=source_text[:300],
            evidence_type=evidence_type,
            confidence=round(confidence, 2),
            is_grounded=confidence >= 0.25
        )

    def format_grounded_answer(
        self,
        search_result: SearchResult,
        question: str
    ) -> Dict[str, Any]:
        """Formats a standard answer anchored to retrieved evidence."""
        # Grounding checks
        scope_claim = self.verify_claim(question, search_result.standard_id, expected_section="Scope")

        return {
            "standard_number": search_result.standard_number,
            "year": search_result.year,
            "title": search_result.full_title,
            "status": search_result.status,
            "version_role": search_result.version_role,
            "relevance_reason": search_result.relevance_reason,
            "evidence": scope_claim.to_dict() if scope_claim.is_grounded else {
                "source_text": "Insufficient evidence from the retrieved BIS standard.",
                "is_grounded": False
            },
            "referenced_standards": search_result.referenced_standards,
            "explicit_relationships": search_result.explicit_relationships,
            "provenance": search_result.source_provenance
        }
