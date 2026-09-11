"""
Module: src/gap_detection.py
Purpose: Missing-Standard & Standards Coverage Detection Engine for TenderSaathi.

Enforces Milestone 10 principles:
- Detect what the tender already contains (reuse explicit citation extraction).
- Cross-reference tender-cited standards against evidence-backed dependency graph.
- Distinguish 3 defensible levels:
  🔴 VERIFIED_MISSING: Strong evidence establishes tender should reference it and does not.
  🟠 POTENTIALLY_MISSING: Evidence-backed dependency expected for complete execution.
  🟡 RELATED_FOR_REVIEW: Useful standard available for engineering review.
- Strictly separate missing specification parameters (SPECIFICATION_GAP)
  from missing standards (STANDARD_GAP).
- Advisory review language: Never declare non-compliance without statutory authority.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set
import re

from src.dependencies import DependencyItem, StandardsDependencyReport


# ---------------------------------------------------------------------------
# Coverage & Gap Data Models
# ---------------------------------------------------------------------------

@dataclass
class GapItem:
    """Represents an identified gap in tender specifications or standards coverage."""
    gap_type: str                         # "STANDARD_GAP", "SPECIFICATION_GAP", "LIFECYCLE_RISK", "EVIDENCE_GAP"
    standard_number: Optional[str]        # Associated standard (if applicable)
    title: Optional[str]                  # Standard title or parameter name
    gap_severity: str                     # "VERIFIED_MISSING", "POTENTIALLY_MISSING", "RELATED_FOR_REVIEW", "CRITICAL", "HIGH", "MEDIUM"
    relationship_type: Optional[str]      # TEST_METHOD, INSTALLATION_STANDARD, etc.
    description: str                      # Concise summary of what is missing
    why_flagged: str                      # Plain-English advisory explanation
    remediation_suggestion: str           # Actionable guidance for procurement officer
    provenance: str = "CURATED"           # VERIFIED, CURATED, INFERRED
    confidence: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CoverageSummary:
    """Quantitative summary of standards coverage for a requirement."""
    primary_standard_covered: bool
    total_dependencies: int
    covered_in_tender: int
    potentially_missing: int
    verified_missing: int
    related_for_review: int
    coverage_percentage: float            # Ratio of covered / total relevant standards

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequirementCoverageMap:
    """Complete structured Standards Coverage Map for a single requirement."""
    requirement_id: str
    requirement_text: str
    primary_standard: Optional[Dict[str, Any]]
    coverage_summary: CoverageSummary
    dependencies_coverage: List[Dict[str, Any]] = field(default_factory=list)
    specification_gaps: List[GapItem] = field(default_factory=list)
    standard_gaps: List[GapItem] = field(default_factory=list)
    all_gaps: List[GapItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "requirement_text": self.requirement_text,
            "primary_standard": self.primary_standard,
            "coverage_summary": self.coverage_summary.to_dict(),
            "dependencies_coverage": self.dependencies_coverage,
            "specification_gaps": [g.to_dict() for g in self.specification_gaps],
            "standard_gaps": [g.to_dict() for g in self.standard_gaps],
            "all_gaps": [g.to_dict() for g in self.all_gaps]
        }


# ---------------------------------------------------------------------------
# Standards Gap Detector Engine
# ---------------------------------------------------------------------------

class StandardsGapDetector:
    """
    Detects missing standards and parameter gaps by comparing tender-cited
    standards against the evidence-backed dependency graph and completeness metrics.
    """

    def __init__(self):
        pass

    def _extract_digits(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        m = re.search(r'\b\d{3,5}\b', text)
        return m.group(0) if m else None

    def _is_standard_cited(self, std_number: str, cited_standards: List[str]) -> bool:
        """Checks if a standard is already cited in the tender."""
        if not std_number or not cited_standards:
            return False
        digits = self._extract_digits(std_number)
        norm_std = re.sub(r'[\s\-:]+', '', std_number.upper())

        for cited in cited_standards:
            c_digits = self._extract_digits(cited)
            if digits and c_digits and digits == c_digits:
                return True
            norm_cited = re.sub(r'[\s\-:]+', '', cited.upper())
            if norm_std in norm_cited or norm_cited in norm_std:
                return True
        return False

    def detect_gaps(
        self,
        requirement: Any,
        primary_standard: Optional[str],
        primary_title: str,
        dependency_report: StandardsDependencyReport,
        completeness_report: Optional[Dict[str, Any]] = None,
        tender_cited_standards: Optional[List[str]] = None
    ) -> RequirementCoverageMap:
        """
        Executes standards coverage analysis and identifies missing standards & parameters.
        """
        req_id = getattr(requirement, "requirement_id", "REQ-001") if hasattr(requirement, "requirement_id") else "REQ-001"
        req_text = getattr(requirement, "text", "") if hasattr(requirement, "text") else str(requirement or "")
        cited_list = tender_cited_standards or []

        # Also extract explicitly cited standards from the requirement itself if not passed
        req_explicit = getattr(requirement, "explicit_standards", []) if hasattr(requirement, "explicit_standards") else []
        combined_cited = list(set(cited_list + req_explicit))

        # Check primary standard status
        is_primary_cited = self._is_standard_cited(primary_standard, combined_cited) if primary_standard else False
        primary_info = None
        if primary_standard:
            primary_info = {
                "standard": primary_standard,
                "title": primary_title,
                "status": "CITED_IN_TENDER" if is_primary_cited else "RECOMMENDED_BY_TENDERSAATHI"
            }

        dep_coverage_list: List[Dict[str, Any]] = []
        standard_gaps: List[GapItem] = []

        covered_count = 1 if (primary_standard and is_primary_cited) else 0
        pot_missing_count = 0
        ver_missing_count = 0
        review_count = 0

        text_lower = req_text.lower()

        # Evaluate each dependency
        for dep in dependency_report.all_dependencies:
            is_cited = self._is_standard_cited(dep.standard_number, combined_cited)

            if is_cited:
                covered_count += 1
                dep_coverage_list.append({
                    "standard": dep.standard_number,
                    "title": dep.title,
                    "relationship_type": dep.relationship_type,
                    "dependency_status": dep.dependency_status,
                    "coverage_status": "COVERED_IN_TENDER",
                    "evidence": dep.evidence_text,
                    "provenance": dep.provenance
                })
            else:
                # Dependency is NOT cited in tender. Determine gap severity.
                # Check for VERIFIED_MISSING condition:
                # e.g. Precast concrete pipe requirement specifies "laying/jointing/fixing" and installation standard IS 783 is omitted
                # e.g. CPVC pipe requirement specifies "pressure testing" or "jointing per code" and testing/installation standard is omitted
                is_verified = False
                if dep.relationship_type in ["INSTALLATION_STANDARD", "CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"]:
                    if any(w in text_lower for w in ["laying", "fixing", "jointing", "erection", "construction"]) and dep.provenance == "VERIFIED":
                        is_verified = True
                elif dep.relationship_type == "TEST_METHOD":
                    if any(w in text_lower for w in ["pressure test", "hydrostatic test", "acceptance test", "sampling"]) and dep.provenance == "VERIFIED":
                        is_verified = True

                if is_verified:
                    gap_sev = "VERIFIED_MISSING"
                    ver_missing_count += 1
                    why_text = (
                        f"Tender specification explicitly calls for installation/testing operations governed by {dep.standard_number}, "
                        f"which is an authoritative {dep.relationship_type} of {primary_standard}. No reference found in tender."
                    )
                    remedy = f"Add explicit citation to {dep.standard_number} ({dep.title}) in the tender technical specifications."
                elif dep.relationship_type in ["TEST_METHOD", "INSTALLATION_STANDARD", "CODE_OF_PRACTICE", "SAFETY_STANDARD"]:
                    gap_sev = "POTENTIALLY_MISSING"
                    pot_missing_count += 1
                    why_text = (
                        f"The recommended standard {primary_standard} has an evidence-backed relationship to {dep.standard_number} "
                        f"for {dep.relationship_type}. Tender analysis found no explicit reference to {dep.standard_number}. "
                        f"Important: This is an advisory review suggestion to ensure procurement quality, not a determination of non-compliance."
                    )
                    remedy = f"Review whether testing or installation protocols from {dep.standard_number} should be specified."
                else:
                    gap_sev = "RELATED_FOR_REVIEW"
                    review_count += 1
                    why_text = (
                        f"Related standard {dep.standard_number} ({dep.title}) identified as {dep.relationship_type} of {primary_standard}. "
                        f"Review for potential co-application or interface compatibility."
                    )
                    remedy = f"Verify whether {dep.standard_number} is needed for equipment interfaces."

                gap_item = GapItem(
                    gap_type="STANDARD_GAP",
                    standard_number=dep.standard_number,
                    title=dep.title,
                    gap_severity=gap_sev,
                    relationship_type=dep.relationship_type,
                    description=f"Uncited {dep.relationship_type.replace('_', ' ').title()}: {dep.standard_number}",
                    why_flagged=why_text,
                    remediation_suggestion=remedy,
                    provenance=dep.provenance,
                    confidence=dep.confidence
                )
                standard_gaps.append(gap_item)

                dep_coverage_list.append({
                    "standard": dep.standard_number,
                    "title": dep.title,
                    "relationship_type": dep.relationship_type,
                    "dependency_status": dep.dependency_status,
                    "coverage_status": gap_sev,
                    "evidence": dep.evidence_text,
                    "provenance": dep.provenance,
                    "why_flagged": why_text
                })

        # Process Specification Parameter Gaps (STRICTLY SEPARATED from standard gaps)
        spec_gaps: List[GapItem] = []
        if completeness_report:
            missing_params = completeness_report.get("missing_parameters", [])
            for param in missing_params:
                spec_gaps.append(GapItem(
                    gap_type="SPECIFICATION_GAP",
                    standard_number=None,
                    title=param,
                    gap_severity="MEDIUM",
                    relationship_type=None,
                    description=f"Specification Parameter Gap: {param}",
                    why_flagged=f"Tender requirement does not specify '{param}', which is required by {primary_standard or 'the applicable standard'} to order or verify the product.",
                    remediation_suggestion=f"Specify '{param}' explicitly in the tender schedule / bill of quantities.",
                    provenance="VERIFIED",
                    confidence=0.9
                ))

        total_req_stds = (1 if primary_standard else 0) + len(dependency_report.all_dependencies)
        cov_pct = round((covered_count / total_req_stds * 100.0), 1) if total_req_stds > 0 else 0.0

        cov_summary = CoverageSummary(
            primary_standard_covered=(primary_standard is not None),
            total_dependencies=len(dependency_report.all_dependencies),
            covered_in_tender=covered_count,
            potentially_missing=pot_missing_count,
            verified_missing=ver_missing_count,
            related_for_review=review_count,
            coverage_percentage=cov_pct
        )

        return RequirementCoverageMap(
            requirement_id=req_id,
            requirement_text=req_text,
            primary_standard=primary_info,
            coverage_summary=cov_summary,
            dependencies_coverage=dep_coverage_list,
            specification_gaps=spec_gaps,
            standard_gaps=standard_gaps,
            all_gaps=spec_gaps + standard_gaps
        )
