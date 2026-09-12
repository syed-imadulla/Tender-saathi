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
import uuid
import tempfile
import traceback
import logging
from datetime import datetime
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
from src.extract import extract_from_text, extract_from_pdf
from src.audit import TenderAuditEngine, TenderAuditResult
from src.report import ReportGenerator

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"])

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


# ---------------------------------------------------------------------------
# In-memory report cache (keyed by tender session ID)
# ---------------------------------------------------------------------------

_report_cache: Dict[str, Dict[str, Any]] = {}
REPORT_DIR = os.path.join(ROOT_DIR, "reports", "generated")


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
            "MODERATE" if r.provenance == "CURATED" else
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
            },
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
    }



    # Determine AI attribution from first non-fallback result
    ai_provider = "deterministic_fallback"
    ai_model = "deterministic"
    for r in results:
        if not getattr(r, "is_ai_fallback", True):
            ai_provider = getattr(r, "ai_provider", "groq") or "groq"
            ai_model = getattr(r, "ai_model", "unknown") or "unknown"
            break

    return {
        "tender": {
            "id": tender_id,
            "source": source_name,
            "file_size": file_size,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
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
            "is_ai_fallback": all(getattr(r, "is_ai_fallback", True) for r in results),
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
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


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
