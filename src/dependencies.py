"""
Module: src/dependencies.py
Purpose: Standards Dependency & Allied/Normative Reference Intelligence Engine.

Enforces Milestone 10 principles:
- Evolve from: Requirement -> Applicable standard
  into: Requirement -> Applicable standard -> Standards ecosystem -> Dependency analysis.
- Distinguishes RELATIONSHIP from APPLICABILITY:
  A relationship in the graph does NOT make the target standard automatically applicable.
- Grounded in authoritative evidence:
  Explicitly typed relationships (NORMATIVE_REFERENCE, TEST_METHOD, INSTALLATION_STANDARD,
  CODE_OF_PRACTICE, SAFETY_STANDARD, ALLIED_STANDARD, etc.) with strict provenance (VERIFIED, CURATED).
- Never hallucinate relationships:
  Same title, domain, material, or year != relationship.
  Semantic similarity != normative reference.
  LLMs are NOT the source of truth for standards relationships.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set
import re

from src.graph import StandardsGraph, StandardRelationship, RelatedStandardResult
from src.applicability import ApplicabilityGate, ApplicabilityResult
from src.extract import Requirement



# ---------------------------------------------------------------------------
# Dependency Data Models
# ---------------------------------------------------------------------------

@dataclass
class DependencyItem:
    """Represents a specific standard dependency linked to a primary standard."""
    standard_number: str                  # e.g. "IS 12235 : 2004"
    title: str                            # Title of the dependency standard
    relationship_type: str                # TEST_METHOD, INSTALLATION_STANDARD, NORMATIVE_REFERENCE, etc.
    dependency_status: str                # NORMATIVE_DEPENDENCY, TEST_DEPENDENCY, INSTALLATION_DEPENDENCY, etc.
    direction: str                        # "OUTGOING" or "INCOMING"
    lifecycle_status: str                 # "Active", "Superseded", "Withdrawn", "Unknown"
    provenance: str                       # "VERIFIED", "CURATED", "INFERRED"
    evidence_strength: str                # "STRONG", "MODERATE", "WEAK"
    evidence_text: str                    # Authoritative text establishing relationship
    source: str                           # "BSB_EDGE_MANUALLY_VERIFIED", "RELATIONSHIPS_JSON", etc.
    confidence: float                     # 0.0 to 1.0
    why_related: str                      # Plain-English explanation of why this standard is related
    functional_category: str              # "testing", "installation", "normative", "safety", "allied", "other"
    is_applicable_to_requirement: bool    # Whether requirement context warrants this dependency
    applicability_decision: str           # "APPLICABLE", "REVIEW_REQUIRED", "NOT_APPLICABLE"
    dependency_state: str = "UNKNOWN"
    evidence: str = ""
    evidence_source: str = "BSB_EDGE_MANUALLY_VERIFIED"
    applicability_assessment: str = "REVIEW_REQUIRED"
    explanation: str = ""

    def __post_init__(self):
        if not self.dependency_state or self.dependency_state == "UNKNOWN":
            self.dependency_state = self.dependency_status or "UNKNOWN"
        if not self.dependency_status:
            self.dependency_status = self.dependency_state
        if not self.evidence:
            self.evidence = self.evidence_text
        if not self.evidence_text:
            self.evidence_text = self.evidence
        if not self.evidence_source:
            self.evidence_source = self.source
        if not self.source:
            self.source = self.evidence_source
        if not self.applicability_assessment:
            self.applicability_assessment = self.applicability_decision
        if not self.applicability_decision:
            self.applicability_decision = self.applicability_assessment
        if not self.explanation:
            self.explanation = self.why_related
        if not self.why_related:
            self.why_related = self.explanation

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StandardsDependencyReport:
    """Complete dependency report for a primary standard and requirement."""
    primary_standard: Optional[str]
    primary_title: str
    total_dependencies: int
    normative_references: List[DependencyItem] = field(default_factory=list)
    test_methods: List[DependencyItem] = field(default_factory=list)
    installation_standards: List[DependencyItem] = field(default_factory=list)
    codes_of_practice: List[DependencyItem] = field(default_factory=list)
    safety_standards: List[DependencyItem] = field(default_factory=list)
    terminology_standards: List[DependencyItem] = field(default_factory=list)
    allied_standards: List[DependencyItem] = field(default_factory=list)
    certification_related: List[DependencyItem] = field(default_factory=list)
    qco_related: List[DependencyItem] = field(default_factory=list)
    related_for_review: List[DependencyItem] = field(default_factory=list)
    all_dependencies: List[DependencyItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_standard": self.primary_standard,
            "primary_title": self.primary_title,
            "total_dependencies": self.total_dependencies,
            "normative_references": [d.to_dict() for d in self.normative_references],
            "test_methods": [d.to_dict() for d in self.test_methods],
            "installation_standards": [d.to_dict() for d in self.installation_standards],
            "codes_of_practice": [d.to_dict() for d in self.codes_of_practice],
            "safety_standards": [d.to_dict() for d in self.safety_standards],
            "terminology_standards": [d.to_dict() for d in self.terminology_standards],
            "allied_standards": [d.to_dict() for d in self.allied_standards],
            "certification_related": [d.to_dict() for d in self.certification_related],
            "qco_related": [d.to_dict() for d in self.qco_related],
            "related_for_review": [d.to_dict() for d in self.related_for_review],
            "all_dependencies": [d.to_dict() for d in self.all_dependencies]
        }


# ---------------------------------------------------------------------------
# Standards Dependency Engine
# ---------------------------------------------------------------------------

class StandardsDependencyEngine:
    """
    Evaluates evidence-backed dependencies for a primary standard,
    categorizes them into functional roles, and tests requirement context
    applicability without conflating relatedness with mandatory applicability.
    """

    def __init__(
        self,
        graph: Optional[StandardsGraph] = None,
        applicability_gate: Optional[ApplicabilityGate] = None
    ):
        self.graph = graph or StandardsGraph()
        self.applicability_gate = applicability_gate or ApplicabilityGate()

    def analyze_dependencies(
        self,
        requirement: Any,
        primary_standard: Optional[str],
        primary_title: str = "",
        depth: int = 1
    ) -> StandardsDependencyReport:
        """
        Analyzes dependencies for a primary standard within the context of the requirement.
        """
        if not primary_standard:
            return StandardsDependencyReport(
                primary_standard=None,
                primary_title="",
                total_dependencies=0
            )

        # Retrieve direct relationships from graph (depth = 1)
        direct_rels = self.graph.get_direct_relationships(primary_standard, depth=depth)

        report = StandardsDependencyReport(
            primary_standard=primary_standard,
            primary_title=primary_title,
            total_dependencies=0
        )

        seen_stds: Set[str] = set()
        clean_primary_digits = re.search(r'\b\d{3,5}\b', primary_standard)
        p_digits = clean_primary_digits.group(0) if clean_primary_digits else None

        req_text = getattr(requirement, "text", "") if hasattr(requirement, "text") else str(requirement or "")

        for rel in direct_rels:
            target_str = rel.target_standard if rel.direction == "OUTGOING" else rel.source_standard
            clean_name = target_str.strip()
            target_digits_m = re.search(r'\b\d{3,5}\b', clean_name)
            t_digits = target_digits_m.group(0) if target_digits_m else None

            # Skip self-references
            if p_digits and t_digits and p_digits == t_digits:
                continue
            if clean_name in seen_stds:
                continue
            seen_stds.add(clean_name)

            # Resolve standard details
            std_info = self.graph._resolve_standard_info(clean_name)
            title = std_info.get("full_title") or std_info.get("title") or clean_name
            raw_status = std_info.get("status") or "Unknown"
            if raw_status in ("Unknown", "UNKNOWN"):
                status = "UNKNOWN / NOT_AVAILABLE_IN_CATALOGUE"
            else:
                status = raw_status

            # Determine functional category & dependency state
            func_cat, dep_state = self._classify_dependency_role(rel.relationship_type)

            # Evaluate context applicability
            is_app, app_dec = self._evaluate_context_applicability(
                requirement=requirement,
                dep_standard_number=clean_name,
                dep_title=title,
                dep_type=rel.relationship_type
            )
            if status == "UNKNOWN / NOT_AVAILABLE_IN_CATALOGUE":
                app_dec = "REVIEW_REQUIRED"

            # Plain-English explanation
            why_related = self._build_why_related_explanation(
                primary_standard=primary_standard,
                dep_standard=clean_name,
                dep_title=title,
                rel_type=rel.relationship_type,
                evidence=rel.evidence,
                provenance=rel.provenance
            )

            ev_strength = "STRONG" if rel.provenance == "VERIFIED" else "MODERATE"
            if rel.provenance == "INFERRED":
                ev_strength = "WEAK"

            dep_item = DependencyItem(
                standard_number=clean_name,
                title=title,
                relationship_type=rel.relationship_type,
                dependency_status=dep_state,
                direction=rel.direction,
                lifecycle_status=status,
                provenance=rel.provenance,
                evidence_strength=ev_strength,
                evidence_text=rel.evidence,
                source=getattr(rel, "source", "BIS_PORTAL"),
                confidence=rel.confidence,
                why_related=why_related,
                functional_category=func_cat,
                is_applicable_to_requirement=is_app,
                applicability_decision=app_dec
            )

            # Populate categorized buckets
            report.all_dependencies.append(dep_item)

            if rel.relationship_type in ["NORMATIVE_REFERENCE", "REFERENCES"]:
                report.normative_references.append(dep_item)
            elif rel.relationship_type == "TEST_METHOD":
                report.test_methods.append(dep_item)
            elif rel.relationship_type == "INSTALLATION_STANDARD":
                report.installation_standards.append(dep_item)
            elif rel.relationship_type in ["CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"]:
                report.codes_of_practice.append(dep_item)
            elif rel.relationship_type == "SAFETY_STANDARD":
                report.safety_standards.append(dep_item)
            elif rel.relationship_type == "TERMINOLOGY_STANDARD":
                report.terminology_standards.append(dep_item)
            elif rel.relationship_type == "ALLIED_STANDARD":
                report.allied_standards.append(dep_item)
            elif rel.relationship_type == "CERTIFICATION_RELATED":
                report.certification_related.append(dep_item)
            elif rel.relationship_type == "QCO_RELATED":
                report.qco_related.append(dep_item)
            else:
                report.related_for_review.append(dep_item)

        report.total_dependencies = len(report.all_dependencies)
        return report

    def _classify_dependency_role(self, rel_type: str) -> tuple:
        """Maps relationship_type to functional category and dependency status."""
        rtype = (rel_type or "").upper()
        if rtype in ["TEST_METHOD"]:
            return ("testing", "TEST_DEPENDENCY")
        elif rtype in ["INSTALLATION_STANDARD"]:
            return ("installation", "INSTALLATION_DEPENDENCY")
        elif rtype in ["CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"]:
            return ("installation", "CODE_OF_PRACTICE")
        elif rtype in ["NORMATIVE_REFERENCE", "REFERENCES"]:
            return ("normative", "NORMATIVE_DEPENDENCY")
        elif rtype in ["SAFETY_STANDARD"]:
            return ("safety", "SAFETY_DEPENDENCY")
        elif rtype in ["ALLIED_STANDARD"]:
            return ("allied", "ALLIED_DEPENDENCY")
        elif rtype in ["CERTIFICATION_RELATED"]:
            return ("certification", "CERTIFICATION_DEPENDENCY")
        elif rtype in ["QCO_RELATED"]:
            return ("certification", "QCO_DEPENDENCY")
        elif rtype in ["SUPERSEDES", "SUPERSEDED_BY"]:
            return ("lifecycle", "RELATED_FOR_REVIEW")
        else:
            return ("other", "RELATED_FOR_REVIEW")

    def _evaluate_context_applicability(
        self,
        requirement: Any,
        dep_standard_number: str,
        dep_title: str,
        dep_type: str
    ) -> tuple:
        """
        Evaluates whether requirement text specifically requires or references
        the activity governed by the dependency (e.g. testing, laying).
        """
        text = (getattr(requirement, "text", "") or str(requirement or "")).lower()

        # Testing dependency check
        if dep_type == "TEST_METHOD":
            if any(w in text for w in ["test", "testing", "sampling", "inspection", "quality", "hydrostatic"]):
                return (True, "APPLICABLE")
            return (False, "REVIEW_REQUIRED")

        # Installation / laying dependency check
        if dep_type in ["INSTALLATION_STANDARD", "CODE_OF_PRACTICE", "CODE_OF_PRACTICE_FOR"]:
            if any(w in text for w in ["laying", "fixing", "installation", "jointing", "erection", "construction", "civil works"]):
                return (True, "APPLICABLE")
            return (False, "REVIEW_REQUIRED")

        # Safety dependency check
        if dep_type == "SAFETY_STANDARD":
            if any(w in text for w in ["safety", "hazard", "protection", "flameproof", "fire", "shock"]):
                return (True, "APPLICABLE")
            return (False, "REVIEW_REQUIRED")

        # Normative reference
        if dep_type in ["NORMATIVE_REFERENCE", "REFERENCES"]:
            return (True, "APPLICABLE")

        return (False, "REVIEW_REQUIRED")

    def _build_why_related_explanation(
        self,
        primary_standard: str,
        dep_standard: str,
        dep_title: str,
        rel_type: str,
        evidence: str,
        provenance: str
    ) -> str:
        """Constructs plain-English, evidence-backed relationship explanation."""
        type_labels = {
            "TEST_METHOD": "official test method standard for quality and verification",
            "INSTALLATION_STANDARD": "installation, laying, and execution standard",
            "CODE_OF_PRACTICE": "code of practice for installation and civil execution",
            "CODE_OF_PRACTICE_FOR": "code of practice for civil execution",
            "NORMATIVE_REFERENCE": "normative reference cited within the primary specification",
            "REFERENCES": "normative reference cited within the primary specification",
            "SAFETY_STANDARD": "mandatory safety or protection standard",
            "ALLIED_STANDARD": "allied product or equipment specification standard",
            "SUPERSEDES": "authoritative successor standard",
            "CERTIFICATION_RELATED": "certification and conformity assessment standard",
            "QCO_RELATED": "Quality Control Order mandatory reference"
        }
        label = type_labels.get(rel_type, "related standard")
        return f"{dep_standard} ({dep_title}) is identified as an evidence-backed {label} associated with {primary_standard}. Evidence: {evidence} [Provenance: {provenance}]."
