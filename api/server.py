"""
api/server.py — TenderSaathi Flask REST API Adapter

Thin adapter over the existing M1–M8 backend engine.
Does NOT duplicate any recommendation logic.

Security:
- GROQ_API_KEY is loaded server-side via .env; never sent to browser.
- No stack traces, filesystem paths, or .env values in responses.
- CORS restricted to localhost in development.
"""

from __future__ import annotations

import os
import sys
import re
import json
import csv
import io
import uuid
import tempfile
import traceback
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Ensure project root on path before any src imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
except ImportError:
    pass

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

from src.recommend import StandardsRecommender, RequirementRecommendationResult, TenderRecommendationReport
from src.critic import are_standards_equivalent
from src.extract import Requirement, extract_from_text, extract_from_pdf, extract_packages_and_requirements
from src.audit import TenderAuditEngine, TenderAuditResult, ReviewStatus
from src.report import ReportGenerator
from src.graph import StandardsGraph, StandardRelationship
from src.standards import StandardsDatabase, CANONICAL_RELATIONSHIP_TYPES


# Ingestion layer (image upload / OCR)
try:
    from api.ingestion import ImageProcessor, ImageValidationError, get_default_ocr_engine
    _IMAGE_PROCESSOR = ImageProcessor()
    _INGESTION_AVAILABLE = True
except Exception as _ing_err:
    _IMAGE_PROCESSOR = None  # type: ignore[assignment]
    _INGESTION_AVAILABLE = False
    logging.getLogger("tendersaathi.api").warning(
        "Ingestion layer unavailable: %s", _ing_err
    )

# ---------------------------------------------------------------------------
# Flask app & CORS Configuration
# ---------------------------------------------------------------------------

_cors_origins_env = os.environ.get("CORS_ORIGINS", "")
if _cors_origins_env.strip() == "*":
    _cors_origins: Any = "*"
elif _cors_origins_env.strip():
    _cors_origins = [o.strip().rstrip("/") for o in _cors_origins_env.split(",") if o.strip()]
    for _dev_origin in ("http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"):
        if _dev_origin not in _cors_origins:
            _cors_origins.append(_dev_origin)
else:
    _cors_origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

app = Flask(__name__)
CORS(app, origins=_cors_origins)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tendersaathi.api")

# ---------------------------------------------------------------------------
# Shared engine instances (loaded once at startup)
# ---------------------------------------------------------------------------

_recommender: Optional[StandardsRecommender] = None
_audit_engine: Optional[TenderAuditEngine] = None
_report_gen: Optional[ReportGenerator] = None


def get_recommender() -> StandardsRecommender:
    global _recommender
    if _recommender is None:
        _recommender = StandardsRecommender()
    return _recommender


def get_audit_engine() -> TenderAuditEngine:
    global _audit_engine
    if _audit_engine is None:
        _audit_engine = TenderAuditEngine()
    return _audit_engine


def get_report_gen() -> ReportGenerator:
    global _report_gen
    if _report_gen is None:
        _report_gen = ReportGenerator()
    return _report_gen


_standards_db: Optional[StandardsDatabase] = None
_standards_graph: Optional[StandardsGraph] = None


def get_standards_db() -> StandardsDatabase:
    global _standards_db
    if _standards_db is None:
        _standards_db = StandardsDatabase()
    return _standards_db


def get_standards_graph() -> StandardsGraph:
    global _standards_graph
    if _standards_graph is None:
        _standards_graph = StandardsGraph(db=get_standards_db())
    return _standards_graph


# ---------------------------------------------------------------------------
# In-memory report cache (keyed by tender session ID)
# ---------------------------------------------------------------------------

_report_cache: Dict[str, Dict[str, Any]] = {}
REPORT_DIR = os.environ.get("REPORT_DIR", os.path.join(ROOT_DIR, "reports", "generated"))


# ---------------------------------------------------------------------------
# Sample requirement texts
# ---------------------------------------------------------------------------

SAMPLE_TEXTS = {
    "cpvc": (
        "Supply and installation of CPVC pipes and fittings for domestic hot and cold water "
        "distribution system, conforming to IS 15778."
    ),
    "valve": (
        "Repair and replacement of valves in the mechanical distribution system."
    ),
    "superseded": (
        "Procurement of bolted bonnet steel gate valves conforming to IS 10611 : 1983."
    ),
}


# ---------------------------------------------------------------------------
# Response normalizer
# ---------------------------------------------------------------------------

def _safe_float(val, default=0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _normalize_result(
    results: List[RequirementRecommendationResult],
    audit: TenderAuditResult,
    tender_id: str,
    source_name: str = "text",
    file_size: int = 0,
) -> Dict[str, Any]:
    """
    Maps backend objects into the normalized API response contract.
    No values are invented — all data comes from existing backend outputs.
    """
    # Classify requirements into the 3 UI sections
    needs_attention: List[Dict] = []
    looks_good: List[Dict] = []
    standards_to_update: List[Dict] = []

    all_reqs: List[Dict] = []

    for r in results:
        crit = getattr(r, "critic_result", None) or {}
        ev = crit.get("evidence") or {}
        ev_strength = ev.get("evidence_strength") or (
            "STRONG" if r.provenance == "VERIFIED" else
            "MODERATE" if r.provenance in ("CURATED", "NATIONAL_CATALOGUE_CITATION", "NATIONAL_CATALOGUE_DISCOVERY", "NATIONAL_CATALOGUE_UNINDEXED") else
            "WEAK" if r.provenance == "INFERRED" else "NONE"
        )
        spec_comp = getattr(r, "specification_completeness", None) or {}
        missing = spec_comp.get("potentially_missing_parameters") or []
        known = spec_comp.get("known_parameters") or {}
        ai_und = getattr(r, "ai_understanding", None) or {}

        # Score breakdown
        scores = {
            "bm25": _safe_float(getattr(r, "bm25_score", 0)),
            "semantic": _safe_float(getattr(r, "semantic_score", 0)),
            "deterministic": _safe_float(getattr(r, "deterministic_score", 0)),
            "reranker": _safe_float(getattr(r, "reranker_score", None)),
            "final": _safe_float(getattr(r, "final_score", r.relevance_score)),
        }

        # Determine superseded citation and successor standard
        is_superseded_status = (r.status or "").lower() == "superseded"
        has_superseded_warn = any(bool(getattr(rec, "superseded_warning", "")) for rec in (r.recommendations or []))
        has_superseded_reason = bool(r.reason and "cited superseded standard" in r.reason.lower())

        is_superseded = is_superseded_status or has_superseded_warn or has_superseded_reason

        successor_std = None
        superseded_cite = None

        if is_superseded:
            # If the candidate itself is superseded
            if is_superseded_status:
                superseded_cite = r.candidate_standard
                for rel in (r.related_standards or []):
                    if rel.get("relationship_type") in ("SUPERSEDED_BY",):
                        successor_std = rel.get("standard_number")
                        break
            else:
                # The candidate is the active replacement (e.g. IS/ISO 10434)
                # and the tender cited the superseded standard (e.g. IS 10611)
                successor_std = r.candidate_standard
                if r.explicit_standards_found:
                    superseded_cite = r.explicit_standards_found[0]
                else:
                    for rel in (r.related_standards or []):
                        if (rel.get("lifecycle_status") or "").lower() == "superseded":
                            superseded_cite = rel.get("standard_number")
                            break

            # Fallback search for successor in superseded_warning
            if not successor_std:
                for rec in (r.recommendations or []):
                    warn = getattr(rec, "superseded_warning", "") or ""
                    match = re.search(r"SUPERSEDED by\s+([A-Za-z0-9/:\s\-]+?)(?:\.|$)", warn, re.IGNORECASE)
                    if match:
                        successor_std = match.group(1).strip()
                        break

        # Primary "reason" / why-flagged text
        why_flagged = r.reason or ""
        if is_superseded and superseded_cite and successor_std:
            why_flagged = f"Cited standard '{superseded_cite}' is superseded. Recommended current active successor: {successor_std}."
        elif r.human_review_required and missing:
            why_flagged = f"Missing: {', '.join(missing)}."
        elif not why_flagged and missing:
            why_flagged = f"Potentially missing parameters: {', '.join(missing[:3])}."

        # Determine candidate and evidence consistency
        cand_std = r.candidate_standard
        ev_std = getattr(r, "evidence_standard", None) or (cand_std if cand_std else None)
        why_it_matches = getattr(r, "why_it_matches", None)

        if cand_std:
            if ev_std and not are_standards_equivalent(cand_std, ev_std):
                why_it_matches = "Match identified from the requirement context; supporting evidence needs review."
                r.human_review_required = True
                ev_std = None
            elif not why_it_matches:
                why_it_matches = "Match identified from the requirement context; supporting evidence needs review."
        else:
            ev_std = None
            why_it_matches = "No reliable Indian Standard match found in the available catalogue."

        req_dict: Dict[str, Any] = {
            "id": r.requirement_id,
            "text": r.requirement_text,
            "category": r.category,
            # Standard
            "candidate_standard": r.candidate_standard,
            "title": r.title or "",
            "lifecycle_status": r.status or "Unknown",
            "successor_standard": successor_std,
            "superseded_citation": superseded_cite,
            # Evidence
            "evidence": r.evidence or "",
            "evidence_strength": ev_strength,
            "provenance": r.provenance or "UNKNOWN",
            "source": ev.get("evidence_source") or (r.provenance or "BIS Official Catalogue"),
            "source_url": ev.get("source_url"),
            "evidence_standard": ev_std,
            "why_it_matches": why_it_matches,
            # Quality
            "confidence": r.confidence or "Low",
            "relevance_score": _safe_float(r.relevance_score),
            # Review flags
            "human_review_required": r.human_review_required,
            "why_flagged": why_flagged,
            "why_this": r.why_this or [],
            "why_not": r.why_not or [],
            "risk_level": r.risk_level or "LOW",
            "risk_reasons": r.risk_reasons or [],
            # Decision
            "decision": (crit.get("decision") or "REVIEW_REQUIRED"),
            # Completeness
            "completeness_label": spec_comp.get("completeness_label", "NOT_APPLICABLE"),
            "missing_parameters": missing,
            "known_parameters": known,
            # Related standards
            "related_standards": r.related_standards or [],
            # AI understanding
            "ai_understanding": {
                "facets": ai_und,
                "provider": getattr(r, "ai_provider", None) or "unknown",
                "model": getattr(r, "ai_model", None) or "unknown",
                "is_fallback": getattr(r, "is_ai_fallback", True),
                "understanding_method": (
                    ai_und.get("understanding_method")
                    or ("groq_llm" if not getattr(r, "is_ai_fallback", True) else "deterministic_fallback")
                ),
            },
            "understanding_method": (
                ai_und.get("understanding_method")
                or ("groq_llm" if not getattr(r, "is_ai_fallback", True) else "deterministic_fallback")
            ),
            # Score breakdown
            "scores": scores,
            # Milestone 9: Applicability Gate results
            "applicability": getattr(r, "applicability", None),
            # Milestone 10: Standards Dependency & Coverage results
            "dependencies": getattr(r, "dependencies", []) or [],
            "standards_coverage": getattr(r, "standards_coverage", None),
            "potential_gaps": getattr(r, "potential_gaps", []) or [],
            "verified_missing": getattr(r, "verified_missing", []) or [],
            "potentially_missing": getattr(r, "potentially_missing", []) or [],
            "related_for_review": getattr(r, "related_for_review", []) or [],
            # Milestone 11: Regulatory Intelligence results
            "regulatory": getattr(r, "regulatory", None) or {},
            # Milestone 12: Controlled Ambiguity & Human Review contract
            "ambiguity_state": getattr(r, "ambiguity_state", "CLEAR") or "CLEAR",
            "ambiguity_reason": getattr(r, "ambiguity_reason", "") or "",
            "retrieval_status": getattr(r, "retrieval_status", "CANDIDATES_FOUND") or "CANDIDATES_FOUND",
            "applicability_status": getattr(r, "applicability_status", "APPLICABLE") or "APPLICABLE",
            "evidence_status": getattr(r, "evidence_status", "VALID") or "VALID",
            "missing_information": getattr(r, "missing_information", []) or [],
            "competing_interpretations": getattr(r, "competing_interpretations", []) or [],
            "suggested_clarification_question": getattr(r, "suggested_clarification_question", None),
            "unresolved_components": getattr(r, "unresolved_components", []) or [],
            # Milestone 13: Multilingual Provenance
            "multilingual": getattr(r, "multilingual", None) or {
                "is_multilingual": False,
                "detected_language": "en",
                "original_text": r.requirement_text,
                "canonical_text": r.requirement_text,
                "language_confidence": 1.0,
                "normalization_confidence": 1.0,
                "entity_preservation_status": "N/A",
                "is_translated": False,
                "human_review_required": False,
                "normalization_method": "fast_path",
            },
            # Phase 9: Standards Relationships & Regulatory Intelligence
            "component_recommendations": getattr(r, "component_recommendations", []) or [],
            "external_regulations": getattr(r, "external_regulations", []) or [],
            "lifecycle_warnings": getattr(r, "lifecycle_warnings", []) or [],
            "amendment_metadata": getattr(r, "amendment_metadata", None),
            # Phase 16: Evidence Traceability & Recommendation Verification
            "trace_record": getattr(r, "trace_record", None),
            "component_trace_records": getattr(r, "component_trace_records", []) or [],
            # Phase 19: Normative Clause Evidence
            "clause_evidence": getattr(r, "clause_evidence", None),
            # Phase 27: Multi-Package & Traceability Tier fields
            "package_id": getattr(r, "package_id", "PKG-01"),
            "package_name": getattr(r, "package_name", "Main Scope"),
            "domain": getattr(r, "domain", None),
            "verification_tier": getattr(r, "verification_tier", "SAFE_ABSTENTION"),
            "evidence_tier": getattr(r, "verification_tier", "SAFE_ABSTENTION"),
            "passage_id": getattr(r, "passage_id", None),
            "clause_number": getattr(r, "clause_number", None),
            "edition_year": getattr(r, "edition_year", None),
            "explicit_standards_found": getattr(r, "explicit_standards_found", []) or [],
            "traversed_cross_references": getattr(r, "traversed_cross_references", []) or [],
        }

        all_reqs.append(req_dict)


        # Classify into sections
        decision = req_dict["decision"]
        if is_superseded:
            standards_to_update.append(req_dict)
        elif decision in ("REVIEW_REQUIRED", "RECOMMEND_WITH_REVIEW", "REJECT", "INSUFFICIENT_EVIDENCE", "NO_RELIABLE_MATCH") or r.human_review_required or req_dict["candidate_standard"] is None:
            needs_attention.append(req_dict)
        else:
            looks_good.append(req_dict)

    # Build summary using real audit numbers
    summary = {
        "requirements_analyzed": audit.requirements_analyzed,
        "needs_attention": len(needs_attention),
        "looks_good": len(looks_good),
        "standards_to_update": len(standards_to_update),
        "review_required_count": audit.review_required_count,
        "insufficient_evidence_count": audit.insufficient_evidence_count,
        "active_count": audit.active_count,
        "superseded_count": audit.superseded_count,
        "withdrawn_count": audit.withdrawn_count,
        "related_standards_count": audit.related_standards_count,
        "evidence_distribution": audit.evidence_distribution,
        "risk_distribution": audit.risk_distribution,
        "dependency_count": getattr(audit, "dependency_count", 0),
        "normative_reference_count": getattr(audit, "normative_reference_count", 0),
        "allied_standard_count": getattr(audit, "allied_standard_count", 0),
        "test_standard_count": getattr(audit, "test_standard_count", 0),
        "installation_standard_count": getattr(audit, "installation_standard_count", 0),
        "verified_missing_count": getattr(audit, "verified_missing_count", 0),
        "potentially_missing_count": getattr(audit, "potentially_missing_count", 0),
        "related_for_review_count": getattr(audit, "related_for_review_count", 0),
        "standards_coverage": getattr(audit, "standards_coverage", {}),
        "gap_summary": getattr(audit, "gap_summary", {}),
        "certification_checks": getattr(audit, "certification_checks", 0),
        "qco_checks": getattr(audit, "qco_checks", 0),
        "crs_checks": getattr(audit, "crs_checks", 0),
        "hallmarking_checks": getattr(audit, "hallmarking_checks", 0),
        "regulatory_review_items": getattr(audit, "regulatory_review_items", 0),
        "unknown_regulatory_items": getattr(audit, "unknown_regulatory_items", 0),
        "upcoming_qco_items": getattr(audit, "upcoming_qco_items", 0),
        "mandatory_qco_count": getattr(audit, "mandatory_qco_count", 0),
        "mandatory_certification_count": getattr(audit, "mandatory_certification_count", 0),
        "crs_applicable_count": getattr(audit, "crs_applicable_count", 0),
        "hallmarking_applicable_count": getattr(audit, "hallmarking_applicable_count", 0),
        "ambiguity_summary": {
            "clear": sum(1 for req in all_reqs if req.get("ambiguity_state") == "CLEAR"),
            "ambiguous": sum(1 for req in all_reqs if req.get("ambiguity_state") == "AMBIGUOUS"),
            "incomplete": sum(1 for req in all_reqs if req.get("ambiguity_state") == "INCOMPLETE"),
            "conflicting": sum(1 for req in all_reqs if req.get("ambiguity_state") == "CONFLICTING"),
            "no_reliable_match": sum(1 for req in all_reqs if req.get("ambiguity_state") == "NO_RELIABLE_MATCH"),
            "review_required": sum(1 for req in all_reqs if req.get("ambiguity_state") == "REVIEW_REQUIRED"),
        },
        "multilingual_summary": {
            "total_multilingual": sum(1 for req in all_reqs if req.get("multilingual", {}).get("is_multilingual", False)),
            "languages_detected": sorted(list({req.get("multilingual", {}).get("detected_language") for req in all_reqs if req.get("multilingual", {}).get("detected_language")})),
        },
        # Phase 4 Tender Audit & Standards Gap Intelligence additions:
        "supported_standards_count": getattr(audit, "supported_standards_count", 0),
        "safe_abstention_count": getattr(audit, "safe_abstention_count", 0),
        "clarification_required_count": getattr(audit, "clarification_required_count", 0),
        "lifecycle_concern_count": getattr(audit, "lifecycle_concern_count", 0),
        "potential_gap_count": getattr(audit, "potential_gap_count", 0),
        "multi_standard_count": getattr(audit, "multi_standard_count", 0),
        "human_review_count": getattr(audit, "human_review_count", 0),
        "coverage_distribution": getattr(audit, "coverage_distribution", {}),
        "coverage_matrix": getattr(audit, "coverage_matrix", []),
        "audit_findings": getattr(audit, "audit_findings", []),
        "gap_findings": getattr(audit, "gap_findings", []),
        "lifecycle_findings": getattr(audit, "lifecycle_findings", []),
        "ambiguity_findings": getattr(audit, "ambiguity_findings", []),
        "multi_standard_items": getattr(audit, "multi_standard_items", []),
        "structured_audit_report": getattr(audit, "structured_audit_report", None),
        "cross_requirement_conflicts": getattr(audit, "cross_requirement_conflicts", []),
        "has_cross_requirement_contradictions": getattr(audit, "has_cross_requirement_contradictions", False),
        "has_unresolved_precedence": getattr(audit, "has_unresolved_precedence", False),
        "has_edition_divergence": getattr(audit, "has_edition_divergence", False),
        # Phase 27: Multi-Package & Traceability Tier additions
        "clause_verified_count": getattr(audit, "clause_verified_count", 0),
        "catalogue_discovered_count": getattr(audit, "catalogue_discovered_count", 0),
        "package_summaries": getattr(audit, "package_summaries", []),
        "domain_distribution": getattr(audit, "domain_distribution", {}),
        "complementary_standards": getattr(audit, "complementary_standards", []),
        "uncovered_tender_dependencies": getattr(audit, "uncovered_tender_dependencies", []),
    }



    # Determine AI attribution from first non-fallback result
    ai_provider = "deterministic_fallback"
    ai_model = "deterministic"
    for r in results:
        if not getattr(r, "is_ai_fallback", True):
            ai_provider = getattr(r, "ai_provider", "groq") or "groq"
            ai_model = getattr(r, "ai_model", "unknown") or "unknown"
            break

    is_ai_fallback_all = all(getattr(r, "is_ai_fallback", True) for r in results) if results else True
    overall_understanding_method = "groq_llm" if not is_ai_fallback_all else "deterministic_fallback"

    return {
        "tender": {
            "id": tender_id,
            "source": source_name,
            "file_size": file_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "understanding_method": overall_understanding_method,
        "summary": summary,
        "readiness": audit.publication_readiness,
        "readiness_reasons": audit.readiness_reasons,
        "sections": {
            "needs_attention": needs_attention,
            "looks_good": looks_good,
            "standards_to_update": standards_to_update,
        },
        "requirements": all_reqs,
        "metadata": {
            "ai_provider": ai_provider,
            "ai_model": ai_model,
            "retrieval_mode": "hybrid+rerank",
            "is_ai_fallback": is_ai_fallback_all,
            "understanding_method": overall_understanding_method,
        },
    }


def _run_analysis(
    texts: Optional[List[str]] = None,
    pdf_path: Optional[str] = None,
    tender_id: Optional[str] = None,
    source_name: str = "text",
    file_size: int = 0,
) -> Dict[str, Any]:
    """
    Shared analysis runner. Accepts either a list of texts or a pdf path.
    Returns normalized API response dict.
    """
    recommender = get_recommender()
    audit_eng = get_audit_engine()
    report_gen = get_report_gen()
    tid = tender_id or f"TS-{uuid.uuid4().hex[:8].upper()}"

    if pdf_path:
        report: TenderRecommendationReport = recommender.recommend_for_pdf(pdf_path, tender_id=tid)
        results = report.results
    elif texts:
        results = []
        if len(texts) == 1:
            reqs = extract_packages_and_requirements(texts[0], tender_id=tid)
            results = [recommender.recommend_for_requirement(rq) for rq in reqs]
        else:
            for i, t in enumerate(texts, start=1):
                r = recommender.recommend_for_text(t, req_id=f"REQ-{i:03d}")
                results.append(r)
    else:
        raise ValueError("Either texts or pdf_path must be provided.")

    audit: TenderAuditResult = audit_eng.audit_tender(results, tender_id=tid)
    normalized = _normalize_result(results, audit, tid, source_name=source_name, file_size=file_size)

    # Cache report for download
    tender_meta = {
        "tender_id": tid,
        "source_file": source_name,
    }
    md_path, json_path = report_gen.generate_and_save(
        audit_result=audit,
        requirement_results=results,
        output_dir=REPORT_DIR,
        tender_metadata=tender_meta,
    )
    _report_cache[tid] = {
        "md_path": md_path,
        "json_path": json_path,
        "normalized": normalized,
        "audit": audit,
        "results": results,
        "tender_meta": tender_meta,
        "human_decisions": {},
    }

    return normalized


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "TenderSaathi API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/analyze/tender", methods=["POST"])
def analyze_tender():
    body = request.get_json(silent=True) or {}
    tender_id = body.get("tender_id") or f"TS-{uuid.uuid4().hex[:8].upper()}"
    packages = body.get("packages") or []

    recommender = get_recommender()
    audit_eng = get_audit_engine()
    report_gen = get_report_gen()

    requirements: List[Requirement] = []
    if packages:
        for p_idx, pkg in enumerate(packages, 1):
            pid = pkg.get("package_id") or f"PKG-{p_idx:02d}"
            pname = pkg.get("package_name") or pkg.get("name") or f"Package {p_idx}"
            raw_reqs = pkg.get("requirements", [])
            for r_idx, r_item in enumerate(raw_reqs, 1):
                r_text = r_item if isinstance(r_item, str) else r_item.get("text", "")
                r_id = (r_item.get("id") if isinstance(r_item, dict) else None) or f"{pid}-REQ-{r_idx:02d}"
                r_dom = (r_item.get("domain") if isinstance(r_item, dict) else None)
                if r_text.strip():
                    req = extract_from_text(r_text.strip(), requirement_id=r_id)
                    req.package_id = pid
                    req.package_name = pname
                    if r_dom:
                        req.domain = r_dom
                    requirements.append(req)

    if not requirements and body.get("text"):
        requirements = extract_packages_and_requirements(body.get("text"), tender_id=tender_id)

    if not requirements:
        return jsonify({"error": "No packages or requirements provided."}), 400

    results = [recommender.recommend_for_requirement(rq) for rq in requirements]
    audit = audit_eng.audit_tender(results, tender_id=tender_id)
    normalized = _normalize_result(results, audit, tender_id, source_name="multi-package tender", file_size=0)

    tender_meta = {
        "tender_id": tender_id,
        "source_file": "multi-package tender payload",
    }
    md_path, json_path = report_gen.generate_and_save(
        audit_result=audit,
        requirement_results=results,
        output_dir=REPORT_DIR,
        tender_metadata=tender_meta,
    )
    _report_cache[tender_id] = {
        "md_path": md_path,
        "json_path": json_path,
        "normalized": normalized,
        "audit": audit,
        "results": results,
        "tender_meta": tender_meta,
        "human_decisions": {},
    }
    return jsonify(normalized)


@app.route("/api/analyze/text", methods=["POST"])
def analyze_text():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Missing 'text' field."}), 400
    if len(text) > 10_000:
        return jsonify({"error": "Text too long (max 10,000 characters)."}), 400

    req_id = body.get("req_id") or "REQ-001"
    tender_id = body.get("tender_id") or f"TS-{uuid.uuid4().hex[:8].upper()}"

    try:
        result = _run_analysis(texts=[text], tender_id=tender_id, source_name="text input")
        return jsonify(result)
    except Exception as e:
        logger.error("analyze_text error: %s", traceback.format_exc())
        return jsonify({"error": "Analysis failed. Please try again.", "detail": str(e)}), 500


@app.route("/api/analyze/pdf", methods=["POST"])
def analyze_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename."}), 400

    fname = f.filename.lower()
    if not (fname.endswith(".pdf") or fname.endswith(".docx")):
        return jsonify({"error": "Unsupported file type. Upload PDF or DOCX."}), 400

    # Read into memory and check size
    data = f.read()
    max_bytes = 25 * 1024 * 1024  # 25 MB
    if len(data) > max_bytes:
        return jsonify({"error": "File too large. Maximum size is 25 MB."}), 400

    if fname.endswith(".docx"):
        return jsonify({"error": "DOCX analysis coming soon. Please upload a PDF."}), 400

    tender_id = f"TS-{uuid.uuid4().hex[:8].upper()}"
    source_name = f.filename

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        result = _run_analysis(
            pdf_path=tmp_path,
            tender_id=tender_id,
            source_name=source_name,
            file_size=len(data),
        )
        # Overwrite the source name with original filename (not tmp path)
        result["tender"]["source"] = source_name
        return jsonify(result)
    except Exception as e:
        logger.error("analyze_pdf error: %s", traceback.format_exc())
        return jsonify({"error": "PDF analysis failed. Please try again.", "detail": str(e)}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route("/api/analyze/sample/<demo>", methods=["GET"])
def analyze_sample(demo: str):
    demo = demo.lower().strip()
    if demo not in SAMPLE_TEXTS:
        return jsonify({
            "error": f"Unknown sample '{demo}'. Available: {list(SAMPLE_TEXTS.keys())}"
        }), 400

    text = SAMPLE_TEXTS[demo]
    tender_id = f"SAMPLE-{demo.upper()}"

    # Return cached result if already computed
    if tender_id in _report_cache:
        return jsonify(_report_cache[tender_id]["normalized"])

    try:
        result = _run_analysis(
            texts=[text],
            tender_id=tender_id,
            source_name=f"Sample: {demo}",
        )
        return jsonify(result)
    except Exception as e:
        logger.error("analyze_sample[%s] error: %s", demo, traceback.format_exc())
        return jsonify({"error": "Sample analysis failed.", "detail": str(e)}), 500


@app.route("/api/report/<tender_id>/json", methods=["GET"])
def report_json(tender_id: str):
    cache = _report_cache.get(tender_id)
    if not cache:
        return jsonify({"error": "Report not found. Run analysis first."}), 404
    json_path = cache.get("json_path")
    if not json_path or not os.path.exists(json_path):
        return jsonify({"error": "Report file unavailable."}), 404
    return send_file(json_path, mimetype="application/json", as_attachment=True,
                     download_name=f"tendersaathi_report_{tender_id}.json")


@app.route("/api/report/<tender_id>/markdown", methods=["GET"])
def report_markdown(tender_id: str):
    cache = _report_cache.get(tender_id)
    if not cache:
        return jsonify({"error": "Report not found. Run analysis first."}), 404
    md_path = cache.get("md_path")
    if not md_path or not os.path.exists(md_path):
        return jsonify({"error": "Report file unavailable."}), 404
    return send_file(md_path, mimetype="text/markdown", as_attachment=True,
                     download_name=f"tendersaathi_report_{tender_id}.md")


# Convenience: report download without specifying tender_id (uses most recent)
@app.route("/api/report/json", methods=["GET"])
def report_json_latest():
    if not _report_cache:
        return jsonify({"error": "No analysis results yet."}), 404
    tid = list(_report_cache.keys())[-1]
    return report_json(tid)


@app.route("/api/report/markdown", methods=["GET"])
def report_markdown_latest():
    if not _report_cache:
        return jsonify({"error": "No analysis results yet."}), 404
    tid = list(_report_cache.keys())[-1]
    return report_markdown(tid)


@app.route("/api/report/<tender_id>/csv", methods=["GET"])
def report_csv(tender_id: str):
    cache = _report_cache.get(tender_id)
    if not cache:
        return jsonify({"error": "Report not found. Run analysis first."}), 404
    normalized = cache.get("normalized") or {}
    requirements = normalized.get("requirements") or []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Requirement ID", "Package ID", "Category", "Requirement Statement",
        "Candidate Standard", "Title", "Lifecycle Status", "Verification Tier",
        "Confidence", "Decision", "Human Review Required", "Evidence Source",
        "Clause Evidence", "Traversed References"
    ])
    for req in requirements:
        traversed = ", ".join(t.get("target_standard", "") for t in req.get("traversed_cross_references", []))
        writer.writerow([
            req.get("id", ""),
            req.get("package_id", "PKG-01"),
            req.get("category", ""),
            req.get("text", ""),
            req.get("candidate_standard") or "None (Safe Abstention)",
            req.get("title", ""),
            req.get("lifecycle_status", "Unknown"),
            req.get("verification_tier", "SAFE_ABSTENTION"),
            req.get("confidence", "Low"),
            req.get("decision", "REVIEW_REQUIRED"),
            req.get("human_review_required", False),
            req.get("source", ""),
            req.get("clause_number") or "",
            traversed
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tendersaathi_report_{tender_id}.csv"}
    )


@app.route("/api/report/csv", methods=["GET"])
def report_csv_latest():
    if not _report_cache:
        return jsonify({"error": "No analysis results yet."}), 404
    tid = list(_report_cache.keys())[-1]
    return report_csv(tid)


# ---------------------------------------------------------------------------
# Phase 5: Human Review & Decision Endpoints
# ---------------------------------------------------------------------------

def _compute_review_progress(
    total_review_items: int,
    all_decisions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Computes human review workflow progress matching ReviewProgressSummary contract."""
    accepted_count = sum(1 for d in all_decisions if d.get("decision") == "ACCEPT")
    edited_count = sum(1 for d in all_decisions if d.get("decision") == "EDIT")
    dismissed_count = sum(1 for d in all_decisions if d.get("decision") == "DISMISS")
    reviewed_count = accepted_count + edited_count + dismissed_count
    pending_count = max(0, total_review_items - reviewed_count)

    if total_review_items == 0 or (total_review_items > 0 and pending_count == 0):
        review_status = ReviewStatus.REVIEW_COMPLETE.value
    elif reviewed_count > 0:
        review_status = ReviewStatus.IN_PROGRESS.value
    else:
        review_status = ReviewStatus.REVIEW_REQUIRED.value

    return {
        "total_review_items": total_review_items,
        "reviewed_count": reviewed_count,
        "pending_count": pending_count,
        "accepted_count": accepted_count,
        "edited_count": edited_count,
        "dismissed_count": dismissed_count,
        "review_status": review_status,
    }


@app.route("/api/tender/<tender_id>/review", methods=["POST"])
def submit_tender_review(tender_id: str):
    """
    Records human review decisions and notes for a tender session.
    Regenerates the Markdown and JSON reports in cache so immediate downloads
    include the complete Human Review & Decision Trail.
    """
    cache = _report_cache.get(tender_id)
    if not cache:
        return jsonify({"error": f"Tender session '{tender_id}' not found. Run analysis first."}), 404

    body = request.get_json(silent=True) or {}
    raw_decisions = body.get("decisions")
    if raw_decisions is None:
        if "requirement_id" in body and "decision" in body:
            raw_decisions = [body]
        else:
            return jsonify({"error": "Missing 'decisions' field."}), 400

    if not isinstance(raw_decisions, list):
        return jsonify({"error": "'decisions' must be a list."}), 400

    results_by_id = {r.requirement_id: r for r in cache.get("results", [])}
    human_decisions_dict = cache.setdefault("human_decisions", {})

    now_ts = datetime.now(timezone.utc).isoformat()

    valid_states = {"PENDING", "ACCEPT", "EDIT", "DISMISS"}

    for d in raw_decisions:
        if not isinstance(d, dict):
            continue
        req_id = d.get("requirement_id")
        if not req_id:
            continue
        dec = str(d.get("decision", "PENDING")).upper().strip()
        if dec not in valid_states:
            dec = "PENDING"

        orig_res = results_by_id.get(req_id)
        sys_std = orig_res.candidate_standard if orig_res else None
        sys_finding = orig_res.reason if orig_res else (orig_res.title if orig_res else None)

        record = {
            "requirement_id": req_id,
            "decision": dec,
            "reviewer_standard": str(d.get("reviewer_standard", "")).strip() if dec == "EDIT" else None,
            "reviewer_note": str(d.get("reviewer_note", "")).strip(),
            "reviewed_at": d.get("reviewed_at") or now_ts,
            "system_standard": sys_std,
            "system_finding": sys_finding,
        }
        human_decisions_dict[req_id] = record

    all_decisions = list(human_decisions_dict.values())

    # Calculate review progress
    audit_obj = cache.get("audit")
    reqs_in_tender = len(cache.get("results", []))
    review_queue = getattr(audit_obj, "review_queue", []) if audit_obj else []
    total_review_items = len(review_queue) if review_queue else reqs_in_tender

    progress = _compute_review_progress(total_review_items, all_decisions)

    # Regenerate reports with human review decision trail
    report_gen = get_report_gen()
    if audit_obj and "results" in cache:
        md_path, json_path = report_gen.generate_and_save(
            audit_result=audit_obj,
            requirement_results=cache["results"],
            output_dir=REPORT_DIR,
            tender_metadata=cache.get("tender_meta"),
            human_decisions=all_decisions,
        )
        cache["md_path"] = md_path
        cache["json_path"] = json_path

    return jsonify({
        "status": "ok",
        "tender_id": tender_id,
        "decisions": all_decisions,
        "progress": progress,
    })


@app.route("/api/tender/<tender_id>/review", methods=["GET"])
def get_tender_review(tender_id: str):
    """Retrieves current human review decisions and progress for a tender session."""
    cache = _report_cache.get(tender_id)
    if not cache:
        return jsonify({"error": f"Tender session '{tender_id}' not found."}), 404

    human_decisions_dict = cache.get("human_decisions", {})
    all_decisions = list(human_decisions_dict.values())

    audit_obj = cache.get("audit")
    reqs_in_tender = len(cache.get("results", []))
    review_queue = getattr(audit_obj, "review_queue", []) if audit_obj else []
    total_review_items = len(review_queue) if review_queue else reqs_in_tender

    progress = _compute_review_progress(total_review_items, all_decisions)

    return jsonify({
        "status": "ok",
        "tender_id": tender_id,
        "decisions": all_decisions,
        "progress": progress,
    })



# ---------------------------------------------------------------------------
# Image analysis endpoint
# ---------------------------------------------------------------------------

# Accepted MIME types for image upload
_ACCEPTED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB per image
_MAX_IMAGES = 5


@app.route("/api/analyze/image", methods=["POST"])
def analyze_image():
    """
    POST /api/analyze/image

    Accepts: multipart/form-data
      files[]  — one or more image files (PNG, JPG, WEBP)

    Returns the same normalized analysis response as /api/analyze/text.
    The combined OCR text is passed through the same evidence pipeline.
    OCR output is clearly flagged in the response; it is NOT authoritative.
    """
    if not _INGESTION_AVAILABLE or _IMAGE_PROCESSOR is None:
        return jsonify({
            "error": "Image analysis is not available on this server. "
                     "The ingestion module could not be loaded."
        }), 503

    # Collect uploaded files from 'files[]' or single 'file'
    uploaded = request.files.getlist("files[]") or request.files.getlist("file")
    if not uploaded:
        return jsonify({"error": "No image files uploaded. Use field name 'files[]'."}), 400

    if len(uploaded) > _MAX_IMAGES:
        return jsonify({
            "error": f"Too many files: {len(uploaded)}. Maximum is {_MAX_IMAGES} images per request."
        }), 400

    # Read and validate each file
    images: List[tuple] = []
    total_bytes = 0
    for f in uploaded:
        if not f.filename:
            return jsonify({"error": "One or more files has an empty filename."}), 400

        # MIME / extension check
        content_type = (f.content_type or "").split(";")[0].strip().lower()
        fname_lower = f.filename.lower()
        ext_ok = any(fname_lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp"))
        mime_ok = content_type in _ACCEPTED_IMAGE_MIMES
        if not ext_ok and not mime_ok:
            return jsonify({
                "error": f"Unsupported file type: '{f.filename}'. "
                         f"Accepted formats: PNG, JPG, WEBP."
            }), 400

        data = f.read()
        if len(data) > _MAX_IMAGE_BYTES:
            mb = _MAX_IMAGE_BYTES // (1024 * 1024)
            return jsonify({
                "error": f"File too large: '{f.filename}'. Maximum image size is {mb} MB."
            }), 400

        total_bytes += len(data)
        images.append((data, f.filename))

    source_name = ", ".join(fname for _, fname in images)
    tender_id = f"TS-{uuid.uuid4().hex[:8].upper()}"

    try:
        from api.ingestion import ImageValidationError as IVE
        try:
            document = _IMAGE_PROCESSOR.process_images(images, source_name=source_name)
        except IVE as ve:
            return jsonify({"error": str(ve)}), 400

        ocr_summary = document.ocr_summary
        combined = document.combined_text

        # If no text extracted, still run analysis — pipeline will safely abstain
        if not combined.strip():
            logger.warning(
                "Image upload produced no extractable text (tender_id=%s). "
                "OCR may be unavailable or the image may be blank.",
                tender_id,
            )
            combined = "[No text could be extracted from the uploaded image(s). Human review required.]"

        result = _run_analysis(
            texts=[combined],
            tender_id=tender_id,
            source_name=source_name,
            file_size=total_bytes,
        )

        # Attach OCR metadata so the UI can inform the user
        result["tender"]["source_type"] = document.metadata.source_type
        result["tender"]["ocr_metadata"] = ocr_summary
        result["tender"]["ocr_quality_warning"] = document.metadata.any_ocr_low_quality

        return jsonify(result)

    except Exception as e:
        logger.error("analyze_image error: %s", traceback.format_exc())
        return jsonify({"error": "Image analysis failed. Please try again.", "detail": str(e)}), 500


# ---------------------------------------------------------------------------
# Standards Knowledge Graph Endpoints (Read-Only)
# ---------------------------------------------------------------------------

GRAPH_DISCLAIMER = (
    "Graph relationships represent technical references and lifecycle links in the BIS catalogue; "
    "they do not independently establish legal applicability or procurement compliance for any specific tender."
)


@app.route("/api/standards/search", methods=["GET"])
def search_standards():
    """
    GET /api/standards/search?q=<query>&limit=<limit>

    Search standards by standard number, ID, or title.
    Read-only, bounded, safe.
    """
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"query": "", "total": 0, "standards": []})

    try:
        limit = min(max(1, int(request.args.get("limit", 15))), 50)
    except (ValueError, TypeError):
        limit = 15

    db = get_standards_db()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        query_pattern = f"%{q}%"
        prefix_pattern = f"{q}%"
        cursor.execute(
            """
            SELECT standard_id, standard_number, year, full_title, status,
                   technical_committee, verification_status
            FROM standards
            WHERE standard_number LIKE ? OR standard_id LIKE ? OR full_title LIKE ?
            ORDER BY 
                CASE 
                    WHEN standard_number LIKE ? THEN 1
                    WHEN standard_id LIKE ? THEN 2
                    WHEN standard_number LIKE ? THEN 3
                    ELSE 4
                END,
                standard_number ASC
            LIMIT ?
            """,
            (query_pattern, query_pattern, query_pattern, prefix_pattern, prefix_pattern, query_pattern, limit)
        )
        rows = [dict(r) for r in cursor.fetchall()]

    return jsonify({
        "query": q,
        "total": len(rows),
        "standards": rows
    })


@app.route("/api/standards/graph/hubs", methods=["GET"])
def get_graph_hubs():
    """
    GET /api/standards/graph/hubs

    Returns curated, prominent standards hubs across engineering domains
    with relationship counts and quick metadata for exploratory entry points.
    """
    hub_definitions = [
        {"standard_id": "IS-15778-2007", "standard_number": "IS 15778", "domain": "Plumbing & Piping", "icon": "droplet"},
        {"standard_id": "IS-7098-(Part-1)-1988", "standard_number": "IS 7098 (Part 1)", "domain": "Electrical & Cables", "icon": "zap"},
        {"standard_id": "IS-1180-Part-1-2014", "standard_number": "IS 1180 (Part 1)", "domain": "Power & Transformers", "icon": "cpu"},
        {"standard_id": "IS-14846-2000", "standard_number": "IS 14846", "domain": "Water Works & Valves", "icon": "filter"},
        {"standard_id": "IS-8034-2018", "standard_number": "IS 8034", "domain": "Pumps & Pumping Systems", "icon": "activity"},
        {"standard_id": "IS-458-2021", "standard_number": "IS 458", "domain": "Civil & Concrete Pipes", "icon": "layers"},
        {"standard_id": "IS-778-1984", "standard_number": "IS 778", "domain": "Alloy Valves & Fittings", "icon": "tool"},
        {"standard_id": "IS-12615-2018", "standard_number": "IS 12615", "domain": "Motors & Energy Efficiency", "icon": "disc"},
    ]

    db = get_standards_db()
    graph = get_standards_graph()
    hubs = []

    for hub in hub_definitions:
        std_row = db.get_standard(hub["standard_id"])
        if not std_row:
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM standards WHERE standard_number = ? LIMIT 1", (hub["standard_number"],))
                r = c.fetchone()
                if r:
                    std_row = dict(r)

        if std_row:
            rels = graph.get_direct_relationships(hub["standard_number"], depth=1)
            hubs.append({
                "standard_id": std_row["standard_id"],
                "standard_number": std_row["standard_number"],
                "year": std_row.get("year"),
                "full_title": std_row.get("full_title", ""),
                "status": std_row.get("status", "Active"),
                "verification_status": std_row.get("verification_status", "CURATED"),
                "domain": hub["domain"],
                "icon": hub["icon"],
                "relationships_count": len(rels)
            })

    return jsonify({
        "hubs": hubs,
        "disclaimer": GRAPH_DISCLAIMER
    })


@app.route("/api/standards/<path:standard_id>/neighbors", methods=["GET"])
def get_standard_neighbors(standard_id: str):
    """
    GET /api/standards/<standard_id>/neighbors?depth=1

    Returns focal standard metadata, direct depth=1 connected nodes, and explicit edges.
    Strictly enforces depth=1.
    """
    depth_param = request.args.get("depth", "1")
    try:
        depth = int(depth_param)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid depth parameter. Must be an integer."}), 400

    if depth != 1:
        return jsonify({
            "error": "Only depth=1 is supported to prevent unbounded or speculative graph traversal."
        }), 400

    clean_id = (standard_id or "").strip()
    if not clean_id:
        return jsonify({"error": "standard_id parameter is required."}), 400

    db = get_standards_db()
    graph = get_standards_graph()

    # Look up focal standard
    focal = db.get_standard(clean_id)
    if not focal:
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM standards WHERE standard_number = ? OR standard_id = ? OR standard_number LIKE ?", (clean_id, clean_id, f"%{clean_id}%"))
            r = c.fetchone()
            if r:
                focal = dict(r)

    focal_lookup_key = focal["standard_number"] if focal else clean_id
    rels = graph.get_direct_relationships(focal_lookup_key, depth=1)
    if not focal and not rels:
        return jsonify({"error": f"Standard '{clean_id}' not found in standards catalogue or relationship index."}), 404

    focal_number = focal["standard_number"] if focal else clean_id

    nodes_dict: Dict[str, Dict[str, Any]] = {}
    edges_list: List[Dict[str, Any]] = []

    def get_or_create_node(std_num_or_id: str, is_focal: bool = False) -> Dict[str, Any]:
        norm_key = re.sub(r'\s+', ' ', std_num_or_id.strip()).upper()
        base_match = re.sub(r'\s*:\s*\d{4}.*$', '', norm_key).strip()

        if norm_key in nodes_dict:
            if is_focal:
                nodes_dict[norm_key]["is_focal"] = True
            return nodes_dict[norm_key]
        if base_match in nodes_dict:
            if is_focal:
                nodes_dict[base_match]["is_focal"] = True
            return nodes_dict[base_match]

        row = db.get_standard(base_match) or db.get_standard(norm_key) or db.get_standard(std_num_or_id.strip())
        if not row:
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT standard_id, standard_number, year, full_title, status, verification_status, technical_committee, scope "
                    "FROM standards WHERE standard_number LIKE ? OR standard_id LIKE ? LIMIT 1",
                    (base_match, base_match)
                )
                r = c.fetchone()
                if r:
                    row = dict(r)

        if row:
            node_data = {
                "id": row["standard_id"],
                "standard_number": row["standard_number"],
                "year": row.get("year"),
                "title": row.get("full_title", ""),
                "status": row.get("status", "Active"),
                "verification_status": row.get("verification_status", "CURATED"),
                "technical_committee": row.get("technical_committee"),
                "scope": row.get("scope"),
                "is_focal": is_focal
            }
        else:
            ym = re.search(r'\b(19\d\d|20\d\d)\b', norm_key)
            extracted_year = int(ym.group(1)) if ym else None
            clean_display_num = re.sub(r'\s*:\s*\d{4}.*$', '', norm_key).strip()

            ref_title = None
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT referenced_title, referenced_year FROM standard_references "
                    "WHERE referenced_standard_number LIKE ? LIMIT 1",
                    (f"%{clean_display_num}%",)
                )
                r = c.fetchone()
                if r:
                    ref_title = r["referenced_title"]
                    if not extracted_year and r["referenced_year"]:
                        extracted_year = r["referenced_year"]

            node_data = {
                "id": norm_key.replace(" ", "-").replace(":", "-").replace("(", "").replace(")", ""),
                "standard_number": clean_display_num,
                "year": extracted_year,
                "title": ref_title or f"BIS Standard {clean_display_num}",
                "status": "Active",
                "verification_status": "CURATED",
                "technical_committee": None,
                "scope": None,
                "is_focal": is_focal
            }

        nodes_dict[norm_key] = node_data
        return node_data

    # Ensure focal node is present
    focal_node = get_or_create_node(focal_number, is_focal=True)

    for idx, rel in enumerate(rels):
        src_node = get_or_create_node(rel.source_standard, is_focal=(rel.source_standard == focal_number))
        tgt_node = get_or_create_node(rel.target_standard, is_focal=(rel.target_standard == focal_number))

        edge_data = {
            "id": f"edge-{idx}-{src_node['id']}-{tgt_node['id']}",
            "source": src_node["id"],
            "target": tgt_node["id"],
            "source_standard": rel.source_standard,
            "target_standard": rel.target_standard,
            "relationship_type": str(rel.relationship_type),
            "direction": rel.direction,
            "evidence": rel.evidence,
            "evidence_clause": rel.evidence_clause or "Referenced Document Clause",
            "provenance": rel.provenance,
            "confidence": rel.confidence,
            "source_url": rel.source_url
        }
        edges_list.append(edge_data)

    return jsonify({
        "focal_standard": focal_node,
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
        "meta": {
            "total_nodes": len(nodes_dict),
            "total_edges": len(edges_list),
            "depth": 1,
            "disclaimer": GRAPH_DISCLAIMER
        }
    })


@app.route("/api/standards/<path:standard_id>/traversal", methods=["GET"])
@app.route("/api/graph/traverse", methods=["GET"])
def get_standard_traversal(standard_id: Optional[str] = None):
    """
    GET /api/standards/<standard_id>/traversal?depth=1
    GET /api/graph/traverse?standard=<standard_id>&depth=1&context=<text>

    Returns evidence-grounded cross-reference traversal journey starting from grounded clauses.
    Strictly bounded to depth 1 or 2. Preserves originating clauses, citation text, reference kinds,
    and lifecycle currency.
    """
    std = standard_id or request.args.get("standard", "")
    clean_id = (std or "").strip()
    if not clean_id:
        return jsonify({"error": "standard or standard_id parameter is required."}), 400

    depth_param = request.args.get("depth", "1")
    try:
        depth = int(depth_param)
    except (ValueError, TypeError):
        depth = 1

    depth = max(1, min(depth, 2))  # Strictly bounded to 1 or 2

    context = request.args.get("context", "")
    clause_id = request.args.get("clause")

    graph = get_standards_graph()
    traversed = graph.traverse_cross_references(
        start_standard=clean_id,
        grounded_clause=clause_id,
        max_depth=depth,
        tender_context=context or None
    )

    return jsonify({
        "start_standard": clean_id,
        "max_depth": depth,
        "traversed_references": [t.to_dict() for t in traversed],
        "count": len(traversed),
        "disclaimer": (
            "Evidence-grounded cross-references traverse normative citations and testing codes cited in "
            "authoritative operative clauses. Graph traversal alone does not establish tender applicability."
        )
    }), 200


@app.route("/api/standards/graph/overview", methods=["GET"])
def get_graph_overview():
    """
    GET /api/standards/graph/overview

    Returns a bounded overview topology and relationship distribution stats.
    Keeps node count bounded (30-40 nodes) to prevent unreadable hairballs.
    """
    db = get_standards_db()
    graph = get_standards_graph()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM standards")
        total_standards = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM standard_relationships")
        total_db_relationships = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM standard_references")
        total_db_references = cursor.fetchone()[0]

    core_hubs = [
        "IS 14846", "IS 15778", "IS 7098 (Part 1)", "IS 1180 (Part 1)",
        "IS 458", "IS 8034", "IS 2491", "IS 12615"
    ]

    all_nodes: Dict[str, Dict[str, Any]] = {}
    all_edges: List[Dict[str, Any]] = []
    seen_edge_keys = set()
    edge_idx = 0

    for hub in core_hubs:
        rels = graph.get_direct_relationships(hub, depth=1)
        for rel in rels[:4]:
            edge_key = (rel.source_standard, rel.target_standard, str(rel.relationship_type))
            if edge_key in seen_edge_keys:
                continue
            seen_edge_keys.add(edge_key)

            for std_str in (rel.source_standard, rel.target_standard):
                clean_num = re.sub(r'\s*:\s*\d{4}.*$', '', std_str).strip()
                node_id = clean_num.replace(" ", "-").replace("(", "").replace(")", "")
                if node_id not in all_nodes:
                    db_std = db.get_standard(clean_num)
                    all_nodes[node_id] = {
                        "id": node_id,
                        "standard_number": clean_num,
                        "year": db_std.get("year") if db_std else None,
                        "title": db_std.get("full_title", f"BIS Standard {clean_num}") if db_std else f"BIS Standard {clean_num}",
                        "status": db_std.get("status", "Active") if db_std else "Active",
                        "verification_status": db_std.get("verification_status", "CURATED") if db_std else "CURATED",
                        "is_focal": clean_num in core_hubs
                    }

            src_num = re.sub(r'\s*:\s*\d{4}.*$', '', rel.source_standard).strip()
            tgt_num = re.sub(r'\s*:\s*\d{4}.*$', '', rel.target_standard).strip()
            src_id = src_num.replace(" ", "-").replace("(", "").replace(")", "")
            tgt_id = tgt_num.replace(" ", "-").replace("(", "").replace(")", "")

            all_edges.append({
                "id": f"overview-edge-{edge_idx}",
                "source": src_id,
                "target": tgt_id,
                "source_standard": rel.source_standard,
                "target_standard": rel.target_standard,
                "relationship_type": str(rel.relationship_type),
                "direction": rel.direction,
                "evidence": rel.evidence,
                "evidence_clause": rel.evidence_clause or "Referenced Document Clause",
                "provenance": rel.provenance,
                "confidence": rel.confidence,
                "source_url": rel.source_url
            })
            edge_idx += 1

    return jsonify({
        "nodes": list(all_nodes.values()),
        "edges": all_edges,
        "stats": {
            "total_standards_in_db": total_standards,
            "total_explicit_relationships": total_db_relationships,
            "total_normative_references": total_db_references,
            "overview_nodes_count": len(all_nodes),
            "overview_edges_count": len(all_edges)
        },
        "disclaimer": GRAPH_DISCLAIMER
    })


# ---------------------------------------------------------------------------
# Capabilities endpoint
# ---------------------------------------------------------------------------

@app.route("/api/capabilities", methods=["GET"])
def capabilities():
    """
    GET /api/capabilities

    Returns supported file types, size limits, and feature availability.
    Safe to call without authentication.
    """
    ocr_available = False
    if _INGESTION_AVAILABLE and _IMAGE_PROCESSOR is not None:
        try:
            ocr_available = _IMAGE_PROCESSOR._ocr.is_available()
        except Exception:
            ocr_available = False

    return jsonify({
        "supported_inputs": {
            "text": {"available": True, "max_chars": 10_000},
            "pdf": {"available": True, "max_bytes": 25 * 1024 * 1024, "formats": ["pdf"]},
            "image": {
                "available": _INGESTION_AVAILABLE,
                "ocr_available": ocr_available,
                "max_bytes_per_image": _MAX_IMAGE_BYTES,
                "max_images": _MAX_IMAGES,
                "max_dimension_px": 8000,
                "formats": ["png", "jpg", "jpeg", "webp"],
                "ocr_note": (
                    "OCR-assisted extraction. "
                    "OCR output is input text only — not authoritative evidence. "
                    "Human review is required for OCR-derived analysis."
                    if _INGESTION_AVAILABLE else
                    "Image analysis module not available on this server."
                ),
            },
        },
        "analysis": {
            "mode": "evidence-grounded",
            "abstains_when_uncertain": True,
            "human_review_required_for_ocr": True,
        },
        "version": "1.1.0",
    })


# ---------------------------------------------------------------------------
# Error handlers — never expose internals
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error."}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(REPORT_DIR, exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("TenderSaathi API starting on http://localhost:%d", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
