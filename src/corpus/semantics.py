"""
src/corpus/semantics.py — Verification States & Semantic Definitions

Defines the 7 distinct evidence verification states for full-text standards
ingestion and retrieval in Tender Saathi. Enforces strict semantic boundaries
so that parser runs, hash matches, and retrieval do not imply expert approval
or statutory authentication.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Any, Optional, Set


class VerificationState(str, Enum):
    """
    Seven distinct evidence verification states.
    States are ordered and strictly scoped to prevent false claims.
    """
    # 1. Document source recorded in manifest with provenance metadata
    DOCUMENT_SOURCE_RECORDED = "DOCUMENT_SOURCE_RECORDED"

    # 2. Raw text extracted from PDF file via deterministic parser
    PDF_TEXT_EXTRACTED = "PDF_TEXT_EXTRACTED"

    # 3. Extraction quality verified (character density, encoding, OCR checks passed)
    EXTRACTION_QUALITY_CHECKED = "EXTRACTION_QUALITY_CHECKED"

    # 4. Extracted passage text hash matches stored document representation
    PASSAGE_MATCHES_STORED_DOCUMENT = "PASSAGE_MATCHES_STORED_DOCUMENT"

    # 5. Clause identifier structurally verified against document layout/heading schema
    CLAUSE_IDENTIFIER_VERIFIED = "CLAUSE_IDENTIFIER_VERIFIED"

    # 6. Engineering applicability reviewed by automated validation / domain rules
    ENGINEERING_APPLICABILITY_REVIEWED = "ENGINEERING_APPLICABILITY_REVIEWED"

    # 7. Qualified human expert adjudicated and signed off with immutable record
    HUMAN_EXPERT_ADJUDICATED = "HUMAN_EXPERT_ADJUDICATED"


STATE_DESCRIPTIONS: Dict[VerificationState, Dict[str, str]] = {
    VerificationState.DOCUMENT_SOURCE_RECORDED: {
        "meaning": "Document acquisition provenance, source citation or URL, and raw file SHA-256 are recorded in the manifest.",
        "does_not_mean": "Does NOT mean the document has been parsed, validated, or verified as authentic by statutory authorities."
    },
    VerificationState.PDF_TEXT_EXTRACTED: {
        "meaning": "Raw text stream extracted from PDF without crash or structural file failure.",
        "does_not_mean": "Does NOT mean extraction quality was checked, characters are free from OCR errors, or clauses are recognized."
    },
    VerificationState.EXTRACTION_QUALITY_CHECKED: {
        "meaning": "Text density, empty page ratio, replacement character rates, and scanned page checks have been evaluated and passed.",
        "does_not_mean": "Does NOT mean clause boundaries are correct, the standard is currently legally enforced, or text is expert-adjudicated."
    },
    VerificationState.PASSAGE_MATCHES_STORED_DOCUMENT: {
        "meaning": "The passage content SHA-256 matches the stored database passage representation derived from the original file.",
        "does_not_mean": "Does NOT imply official BIS statutory authentication or that the standard applies to any specific tender."
    },
    VerificationState.CLAUSE_IDENTIFIER_VERIFIED: {
        "meaning": "The clause number/heading was structurally identified in the text rather than hallucinated or guessed.",
        "does_not_mean": "Does NOT mean the clause applies to a specific tender requirement or that human engineers have reviewed it."
    },
    VerificationState.ENGINEERING_APPLICABILITY_REVIEWED: {
        "meaning": "Automated domain logic or specification criteria reviewed the requirement-to-clause applicability.",
        "does_not_mean": "Does NOT mean a human expert has approved or signed off on the recommendation."
    },
    VerificationState.HUMAN_EXPERT_ADJUDICATED: {
        "meaning": "A qualified professional engineer or standards officer has reviewed and signed off with an immutable adjudication record.",
        "does_not_mean": "Must NEVER be set automatically or inferred by machine parsing."
    }
}


# Valid progressive transitions
VALID_TRANSITIONS: Dict[VerificationState, Set[VerificationState]] = {
    VerificationState.DOCUMENT_SOURCE_RECORDED: {
        VerificationState.PDF_TEXT_EXTRACTED
    },
    VerificationState.PDF_TEXT_EXTRACTED: {
        VerificationState.EXTRACTION_QUALITY_CHECKED
    },
    VerificationState.EXTRACTION_QUALITY_CHECKED: {
        VerificationState.PASSAGE_MATCHES_STORED_DOCUMENT
    },
    VerificationState.PASSAGE_MATCHES_STORED_DOCUMENT: {
        VerificationState.CLAUSE_IDENTIFIER_VERIFIED
    },
    VerificationState.CLAUSE_IDENTIFIER_VERIFIED: {
        VerificationState.ENGINEERING_APPLICABILITY_REVIEWED
    },
    VerificationState.ENGINEERING_APPLICABILITY_REVIEWED: {
        VerificationState.HUMAN_EXPERT_ADJUDICATED
    },
    VerificationState.HUMAN_EXPERT_ADJUDICATED: set()
}


def can_transition(current: VerificationState, target: VerificationState) -> bool:
    """Checks whether transitioning from current to target state is permissible."""
    return target in VALID_TRANSITIONS.get(current, set())


def get_state_semantics(state: VerificationState) -> Dict[str, str]:
    """Returns detailed semantic description of what the state guarantees and excludes."""
    return STATE_DESCRIPTIONS.get(state, {"meaning": "Unknown", "does_not_mean": "Unknown"})


class ClauseEvidenceOutcome(str, Enum):
    """
    Distinct outcomes for clause-level evidence lookup in the normative standards corpus.
    Maintains clean boundaries between corpus availability failures and substantive clause absences.
    """
    # 1. Authentic clause passage found in an eligible, extracted corpus document matching standard & edition
    CLAUSE_EVIDENCE_FOUND = "CLAUSE_EVIDENCE_FOUND"

    # 2. Eligible corpus document exists, but the requested clause identifier was not found in it
    CLAUSE_EVIDENCE_NOT_FOUND = "CLAUSE_EVIDENCE_NOT_FOUND"

    # 3. Corpus database or storage subsystem is uninitialized, inaccessible, or absent
    CORPUS_NOT_AVAILABLE = "CORPUS_NOT_AVAILABLE"

    # 4. No corpus document exists for standard/edition, or document is in ineligible state (OCR_REQUIRED, CORRUPT, etc.)
    CORPUS_DOCUMENT_NOT_ELIGIBLE = "CORPUS_DOCUMENT_NOT_ELIGIBLE"

    # 5. Unexpected operational error during query or retrieval execution
    CORPUS_LOOKUP_ERROR = "CORPUS_LOOKUP_ERROR"


OUTCOME_DESCRIPTIONS: Dict[ClauseEvidenceOutcome, str] = {
    ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND: "Authentic clause passage located in an eligible local corpus document.",
    ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND: "Eligible document was inspected, but requested clause identifier does not exist in it.",
    ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE: "Local full-text corpus storage is not initialized or accessible.",
    ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE: "No eligible full-text corpus document registered for this standard and edition.",
    ClauseEvidenceOutcome.CORPUS_LOOKUP_ERROR: "An operational or database error occurred during clause lookup.",
}


class RequirementEvidenceSupportState(str, Enum):
    """
    Evaluates whether normative clause passage(s) actually support the procurement requirement.
    Distinguishes structural passage existence from substantive requirement coverage.
    """
    # 1. Authentic passage(s) support all technical conditions/components of the requirement
    FULLY_SUPPORTED = "FULLY_SUPPORTED"

    # 2. Passage(s) support one or more conditions, but compound requirement has missing components
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"

    # 3. Passage located by clause ID or search, but does not support the requirement's technical subject
    UNSUPPORTED = "UNSUPPORTED"

    # 4. Passage text specifies ratings, boundaries, or conditions that directly contradict the requirement
    CONFLICTING = "CONFLICTING"

    # 5. No eligible normative clause evidence in corpus; coverage relies on catalogue scope or unverified
    UNVERIFIED_COVERAGE = "UNVERIFIED_COVERAGE"


SUPPORT_STATE_DESCRIPTIONS: Dict[RequirementEvidenceSupportState, str] = {
    RequirementEvidenceSupportState.FULLY_SUPPORTED: "Authentic normative passage supports all material parameters and components of the requirement.",
    RequirementEvidenceSupportState.PARTIALLY_SUPPORTED: "Passage supports part of the requirement, but other compound components lack clause evidence.",
    RequirementEvidenceSupportState.UNSUPPORTED: "Retrieved clause passage does not substantively support the requirement's technical subject.",
    RequirementEvidenceSupportState.CONFLICTING: "Retrieved normative passage contradicts or excludes specified requirement parameters or ratings.",
    RequirementEvidenceSupportState.UNVERIFIED_COVERAGE: "Normative clause evidence is unavailable in local corpus; requirement coverage is unverified at clause level.",
}


class CrossRequirementConflictState(str, Enum):
    """
    Seven distinct outcomes when evaluating systemic interactions between multiple requirements across a tender.
    Prevents artificial precedence rules while enforcing verifiable contradiction and co-applicability detection.
    """
    # 1. No incompatible parameters, operating conditions, or lifecycle clashes detected across requirements
    NO_CROSS_REQUIREMENT_CONFLICT = "NO_CROSS_REQUIREMENT_CONFLICT"

    # 2. Verifiable technical contradiction between two requirements on the same equipment tag or shared parameter
    CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION = "CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION"

    # 3. Possible parameter clash, but requirement text lacks distinguishing details (e.g. uncertain circuit sharing)
    POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED = "POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED"

    # 4. Complementary standards serving distinct roles for the same equipment (e.g. Product specification + Installation code)
    CO_APPLICABLE_COMPLEMENTARY_STANDARDS = "CO_APPLICABLE_COMPLEMENTARY_STANDARDS"

    # 5. Overlapping candidate standards where published source evidence does not establish normative precedence
    UNRESOLVED_NORMATIVE_PRECEDENCE = "UNRESOLVED_NORMATIVE_PRECEDENCE"

    # 6. Requirements in the same tender cite active and superseded editions of the same standard family
    LIFECYCLE_EDITION_DIVERGENCE = "LIFECYCLE_EDITION_DIVERGENCE"

    # 7. Explicit tender specification stipulates higher stringency permitted by standard buyer options
    TENDER_SPECIFICATION_OVERRIDE = "TENDER_SPECIFICATION_OVERRIDE"


CROSS_CONFLICT_STATE_DESCRIPTIONS: Dict[CrossRequirementConflictState, str] = {
    CrossRequirementConflictState.NO_CROSS_REQUIREMENT_CONFLICT: "Requirements concern distinct equipment, disjoint zones, or compatible engineering parameters.",
    CrossRequirementConflictState.CONFIRMED_CROSS_REQUIREMENT_CONTRADICTION: "Two requirements specify mutually exclusive physical ratings or operating envelopes for the same equipment.",
    CrossRequirementConflictState.POTENTIAL_CROSS_CONFLICT_MORE_EVIDENCE_NEEDED: "Potential technical tension identified, but evidence is insufficient to confirm whether items share the same circuit or apparatus.",
    CrossRequirementConflictState.CO_APPLICABLE_COMPLEMENTARY_STANDARDS: "Standards govern complementary facets (e.g. product specification, installation code, or routine test method); no contradiction exists.",
    CrossRequirementConflictState.UNRESOLVED_NORMATIVE_PRECEDENCE: "Multiple standards appear applicable to the same scope with overlapping mandates, and priority is not established by statutory orders or standard clauses.",
    CrossRequirementConflictState.LIFECYCLE_EDITION_DIVERGENCE: "Different requirements in the same tender cite divergent editions (e.g., active vs withdrawn) of the same standard family.",
    CrossRequirementConflictState.TENDER_SPECIFICATION_OVERRIDE: "Tender specification prescribes a more stringent option permitted by the governing standard without breaching statutory safety minimums.",
}

