#!/usr/bin/env python3
"""
Presentation-ready Demo CLI for SIH26108: AI-Powered Recommendation Engine for Indian Standards.

Usage:
  python3 scripts/demo.py --query "CPVC pipe replacement for water supply"
  python3 scripts/demo.py --tender T020
  python3 scripts/demo.py --tender T002
  python3 scripts/demo.py --tender T007
  python3 scripts/demo.py --tender T010
"""

import sys
import os
import argparse
from typing import Optional, Dict

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.recommend import StandardsRecommender, RequirementRecommendationResult
from src.extract import extract_from_pdf, extract_from_text
from src.audit import TenderAuditResult
from src.report import ReportGenerator


TENDER_MAP = {
    "T001": "data/tenders/eProcurement System Government of India2.pdf",
    "T002": "data/tenders/eProcurement System Government of India3.pdf",
    "T003": "data/tenders/eProcurement System Government of India4.pdf",
    "T004": "data/tenders/eProcurement System Government of India5.pdf",
    "T005": "data/tenders/eProcurement System Government of India6.pdf",
    "T006": "data/tenders/eProcurement System Government of India7.pdf",
    "T007": "data/tenders/eProcurement System Government of India8.pdf",
    "T008": "data/tenders/eProcurement System Government of India9.pdf",
    "T009": "data/tenders/eProcurement System Government of India10.pdf",
    "T010": "data/tenders/eProcurement System Government of India11.pdf",
    "T011": "data/tenders/eProcurement System Government of India12.pdf",
    "T012": "data/tenders/eProcurement System Government of India13.pdf",
    "T013": "data/tenders/eProcurement System Government of India14.pdf",
    "T014": "data/tenders/eProcurement System Government of India15.pdf",
    "T015": "data/tenders/eProcurement System Government of India16.pdf",
    "T016": "data/tenders/eProcurement System Government of India17.pdf",
    "T017": "data/tenders/eProcurement System Government of India18.pdf",
    "T018": "data/tenders/eProcurement System Government of India19.pdf",
    "T019": "data/tenders/eProcurement System Government of India20.pdf",
    "T020": "data/tenders/eProcurement System Government of India.pdf"
}


# ANSI Colors for Presentation Display
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"


def format_card(res: RequirementRecommendationResult, input_source: str):
    """Prints a structured visual card for judges matching the required demo flow."""
    box_w = 78
    hr = "─" * box_w
    d_hr = "═" * box_w

    print("\n" + CYAN + d_hr + RESET)
    print(f"{BOLD}{CYAN}▶ SIH26108 STANDARDS RECOMMENDATION ENGINE — EVALUATION CARD{RESET}")
    print(CYAN + d_hr + RESET)

    # 1. REQUIREMENT
    print(f"{BOLD}[1] REQUIREMENT{RESET}           : \"{res.requirement_text}\"")
    print(f"    • Requirement ID      : {BOLD}{res.requirement_id}{RESET} ({input_source})")
    if res.explicit_standards_found:
        print(f"    • Cited Standards     : {MAGENTA}{', '.join(res.explicit_standards_found)}{RESET}")
    if hasattr(res, "decomposed_components") and res.decomposed_components:
        print(f"    • Decomposed Components:")
        for c in res.decomposed_components:
            c_txt = c.get("text", "")
            c_type = c.get("component_type", "").upper()
            c_dom = c.get("domain", "")
            print(f"      - [{c_type}] {BOLD}{c_txt}{RESET} ({c_dom})")

    # 1b. AI REQUIREMENT UNDERSTANDING (Milestone 8)
    ai_und = getattr(res, "ai_understanding", None) or {}
    ai_prov = getattr(res, "ai_provider", "deterministic")
    ai_model = getattr(res, "ai_model", None)
    is_fallback = getattr(res, "is_ai_fallback", True)
    fallback_tag = f" {YELLOW}(Fallback: Deterministic Decomposer){RESET}" if is_fallback else f" {GREEN}(AI Extracted Facets){RESET}"
    print(f"\n{BOLD}[1b] AI REQUIREMENT UNDERSTANDING{RESET}: {CYAN}{ai_prov}{RESET} | Model: {CYAN}{ai_model or 'rule-based'}{RESET}{fallback_tag}")
    if ai_und:
        for facet in ["equipment", "control", "electrical", "voltage", "application", "work_type"]:
            vals = ai_und.get(facet, [])
            if vals:
                print(f"      • {facet.capitalize():<12}: {', '.join(vals)}")

    # 2. DETECTED CATEGORY
    print(f"\n{BOLD}[2] DETECTED CATEGORY{RESET}     : {YELLOW}{res.category.upper()}{RESET}")

    # 3. TOP CANDIDATE STANDARDS
    print(f"\n{BOLD}[3] TOP CANDIDATE STANDARDS{RESET}:")
    for idx, r in enumerate(res.recommendations[:3], start=1):
        stat_color = GREEN if "active" in r.status.lower() else RED
        star = " ★ (PRIMARY RECOMMENDATION)" if idx == 1 else ""
        print(f"    {idx}. {BOLD}{r.standard_number}{RESET}{star} — {r.title}")
        print(f"       Status: {stat_color}{r.status}{RESET} [{r.version_role}] | Relevance: {r.relevance_score} | Confidence: {r.confidence}")
        rerank_str = f"{r.reranker_score:.3f}" if r.reranker_score is not None else "N/A"
        print(f"       Scores: BM25={r.bm25_score:.2f} | Semantic={r.semantic_score:.2f} | Det={r.deterministic_score:.2f} | Rerank={rerank_str} | Final={r.final_score:.3f}")
        if r.superseded_warning:
            print(f"       {RED}⚠ SUPERSEDENCE ALERT: {r.superseded_warning}{RESET}")


    # 4. WHY THIS STANDARD?
    print(f"\n{BOLD}[4] WHY THIS STANDARD?{RESET}    :")
    why_this_list = getattr(res, "why_this", None)
    if why_this_list:
        for reason in why_this_list:
            print(f"    • {reason}")
    else:
        print(f"    • {res.reason}")

    # 4b. WHY NOT ALTERNATIVES? (Milestone 3 measurable candidate differences)
    why_not_list = getattr(res, "why_not", None)
    if why_not_list:
        print(f"\n{BOLD}[4b] WHY NOT ALTERNATIVES?{RESET} :")
        if isinstance(why_not_list, list):
            for reason in why_not_list:
                print(f"    • {reason}")
        elif isinstance(why_not_list, dict):
            for std_num, reasons in why_not_list.items():
                print(f"    • {BOLD}{std_num}{RESET}: {'; '.join(reasons)}")

    # 5. SCOPE / EVIDENCE & TRUST GATE
    print(f"\n{BOLD}[5] EVIDENCE & TRUST GATE{RESET} :")
    print(f"    • Provenance Source   : {BLUE}{res.provenance}{RESET}")
    print(f"    • Verbatim Evidence   : {res.evidence}")
    c_res = getattr(res, "critic_result", None) or {}
    if c_res:
        ev_dict = c_res.get("evidence") or {}
        ev_strength = ev_dict.get("evidence_strength", "UNKNOWN") if isinstance(ev_dict, dict) else getattr(ev_dict, "evidence_strength", "UNKNOWN")
        ret_score = c_res.get("relevance_score", 0.0)
        ev_color = GREEN if ev_strength in ["STRONG", "MODERATE"] else YELLOW
        print(f"    • Evidence Strength   : {ev_color}{ev_strength}{RESET} | Retrieval Score: {ret_score:.3f}")

    # 5b. SPECIFICATION REVIEW COMPLETENESS
    c_rep = getattr(res, "specification_completeness", None) or getattr(res, "completeness_report", None) or {}
    if c_rep:
        c_label = c_rep.get("completeness_label", "UNKNOWN")
        c_dom = c_rep.get("domain", "generic")
        is_adeq = c_rep.get("is_adequately_specified", False)
        known_params = c_rep.get("known_parameters", {})
        missing_params = c_rep.get("potentially_missing_parameters", [])

        c_stat_color = GREEN if is_adeq else (YELLOW if c_dom != "generic" else BLUE)
        print(f"\n{BOLD}[5b] SPEC REVIEW COMPLETENESS{RESET}: {c_stat_color}{c_label}{RESET} (Domain: {c_dom})")
        if known_params:
            print(f"    • Known Parameters    : {', '.join(f'{k}={v}' for k, v in known_params.items())}")
        if missing_params:
            print(f"    • Potentially Missing : {YELLOW}{', '.join(missing_params)}{RESET}")

    # 6. CURRENT STATUS
    stat_color = GREEN if "active" in res.status.lower() else RED
    print(f"\n{BOLD}[6] CURRENT STATUS{RESET}        : {stat_color}{res.status.upper()}{RESET} [{res.version_role}]")

    # 7. CONFIDENCE & CRITIC DECISION
    conf_color = GREEN if res.confidence == "High" else (YELLOW if res.confidence == "Medium" else RED)
    decision_val = c_res.get("decision") if c_res else ("RECOMMEND" if not res.human_review_required else "REVIEW_REQUIRED")
    risk_val = getattr(res, "risk_level", None) or ("LOW" if not res.human_review_required else "HIGH")
    risk_color = GREEN if risk_val == "LOW" else (YELLOW if risk_val == "MEDIUM" else RED)
    
    print(f"\n{BOLD}[7] DECISION & RISK{RESET}      :")
    print(f"    • Critic Decision     : {BOLD}{decision_val}{RESET}")
    print(f"    • Risk Level          : {risk_color}{BOLD}{risk_val}{RESET}")
    print(f"    • Final Confidence    : {conf_color}{res.confidence.upper()}{RESET}")
    risk_reasons = getattr(res, "risk_reasons", [])
    if risk_reasons:
        print(f"    • Risk Factors        : {'; '.join(risk_reasons)}")

    # 8. ALTERNATIVE STANDARDS
    alt_str = ", ".join(res.alternatives) if res.alternatives else "None identified in top-k retrieval"
    print(f"\n{BOLD}[8] ALTERNATIVE STANDARDS{RESET} : {alt_str}")

    # 8b. RELATED STANDARDS TO REVIEW (GRAPH DEPTH 1)
    rel_stds = getattr(res, "related_standards", [])
    if rel_stds:
        print(f"\n{BOLD}[8b] RELATED STANDARDS TO REVIEW (GRAPH DEPTH 1){RESET}:")
        for r in rel_stds[:3]:
            dir_str = "→" if r.get("direction") == "OUTGOING" else "←"
            rel_type = r.get("relationship_type", "RELATED")
            tgt_std = r.get("standard_number", "")
            title = r.get("title", "")
            stat = r.get("lifecycle_status", "Active")
            ev_str = r.get("evidence_strength", "MODERATE")
            note = r.get("review_note", "Related standard to review")
            print(f"    • [{dir_str} {rel_type}] {BOLD}{tgt_std}{RESET} — {title}")
            print(f"      Status: {stat} | Evidence: {ev_str} | Note: {note}")

    # 9. HUMAN VERIFICATION REQUIRED?
    print(f"\n{BOLD}[9] HUMAN VERIFICATION REQUIRED?{RESET}:")
    if res.human_review_required:
        print(f"    >>> {RED}{BOLD}YES (FLAGGED FOR HUMAN REVIEW){RESET}")
        print(f"    • Reason for Review   : {YELLOW}{res.reason}{RESET}")
    else:
        print(f"    >>> {GREEN}{BOLD}NO (AUTOMATED RECOMMENDATION GROUNDED IN EVIDENCE){RESET}")

    print(CYAN + d_hr + RESET + "\n")


def format_audit(audit: TenderAuditResult):
    """Formats tender-level audit and publication readiness for presentation."""
    box_w = 60
    eq_hr = "=" * box_w

    print("\n" + eq_hr)
    print(f"{BOLD}TENDER AUDIT — {audit.tender_id}{RESET}")
    print(eq_hr)
    print(f"Requirements analysed: {audit.requirements_analyzed}")

    print(f"\n{BOLD}Standards Review{RESET}")
    print(f"  Recommendations:        {audit.recommendations_count}")
    print(f"  Review Required:        {audit.review_required_count}")
    print(f"  Insufficient Evidence:  {audit.insufficient_evidence_count}")

    print(f"\n{BOLD}Lifecycle{RESET}")
    print(f"  Active:                 {audit.lifecycle_distribution.get('Active', 0)}")
    print(f"  Superseded:             {audit.lifecycle_distribution.get('Superseded', 0)}")
    print(f"  Withdrawn:              {audit.lifecycle_distribution.get('Withdrawn', 0)}")
    print(f"  Unknown:                {audit.lifecycle_distribution.get('Unknown', 0)}")

    print(f"\n{BOLD}Evidence{RESET}")
    print(f"  STRONG:                 {audit.evidence_distribution.get('STRONG', 0)}")
    print(f"  MODERATE:               {audit.evidence_distribution.get('MODERATE', 0)}")
    print(f"  WEAK:                   {audit.evidence_distribution.get('WEAK', 0)}")
    print(f"  NONE:                   {audit.evidence_distribution.get('NONE', 0)}")

    print(f"\n{BOLD}Specification Review{RESET}")
    for k in ["KNOWN", "POTENTIALLY_MISSING", "UNKNOWN", "NOT_APPLICABLE"]:
        val = audit.completeness_distribution.get(k, 0)
        if val > 0 or k in ["KNOWN", "POTENTIALLY_MISSING"]:
            print(f"  {k:<22}: {val}")

    print(f"\nRelated Standards to Review: {audit.related_standards_count}")

    # Publication Readiness Status
    stat = audit.publication_readiness
    if stat == "READY_FOR_REVIEW":
        stat_color = GREEN
        icon = "✓"
    elif stat == "REVIEW_REQUIRED":
        stat_color = YELLOW
        icon = "⚠"
    else:
        stat_color = RED
        icon = "✗"

    print(f"\n{BOLD}Publication Readiness:{RESET}")
    print(f"{stat_color}{BOLD}{icon} {stat}{RESET}")

    if audit.readiness_reasons:
        print(f"\n{BOLD}Reasons:{RESET}")
        for reason in audit.readiness_reasons:
            print(f"• {reason}")

    if audit.review_queue:
        print(f"\n{BOLD}Human Review Queue:{RESET}")
        for idx, item in enumerate(audit.review_queue[:5], 1):
            color = RED if item.risk_level == "CRITICAL" else (YELLOW if item.risk_level == "HIGH" else BLUE)
            clean_text = item.requirement_text[:48] + "..." if len(item.requirement_text) > 48 else item.requirement_text
            print(f"{idx}. {color}{BOLD}{item.risk_level:<8}{RESET} — Req: '{clean_text}'")
            print(f"   Candidate: {item.candidate_standard} | Issue: {item.primary_reason}")

    print(eq_hr + "\n")


def main():
    parser = argparse.ArgumentParser(description="SIH26108 Presentation-Ready Recommendation Demo CLI")
    parser.add_argument("--query", type=str, help="Single procurement requirement specification string")
    parser.add_argument("--tender", type=str, help="Tender ID to demo (e.g. T002, T007, T010, T020) or PDF path")
    parser.add_argument("--audit", nargs="?", const="SAMPLE", default=None, type=str, help="Run tender-level audit demonstration (e.g. --audit or --audit T001)")
    parser.add_argument("--report", action="store_true", help="Generate Evidence-Backed Standards Review Report (Markdown + JSON)")
    parser.add_argument("--llm", action="store_true", default=None, help="Enable AI requirement understanding via Groq LLM")
    parser.add_argument("--no-llm", action="store_false", dest="llm", help="Disable LLM (use deterministic decomposition only)")
    parser.add_argument("--rerank", action="store_true", default=False, help="Enable Cross-Encoder neural reranker (cross-encoder/ms-marco-MiniLM-L-6-v2)")
    parser.add_argument("--no-rerank", action="store_false", dest="rerank", help="Disable neural reranker")
    parser.add_argument("target", nargs="?", default=None, help="Optional tender ID or query parameter")

    args = parser.parse_args()

    # Allow python scripts/demo.py --audit --report <tender> syntax
    if args.audit and args.target:
        args.audit = args.target
    elif args.tender is None and args.query is None and args.audit is None and args.target:
        # If target provided without flag, infer tender or audit
        args.audit = args.target

    if not (args.query or args.tender or args.audit):
        parser.print_help()
        sys.exit(1)

    retrieval_mode = "hybrid+rerank" if args.rerank else "hybrid"
    recommender = StandardsRecommender(
        retrieval_mode=retrieval_mode,
        ai_enabled=args.llm
    )


    if args.query:
        print(f"\nProcessing single requirement query: \"{args.query}\"...")
        res = recommender.recommend_for_text(args.query, req_id="DEMO-REQ-001")
        format_card(res, input_source=f"CLI Text Query: '{args.query}'")

        if args.report:
            audit_res = recommender.audit_tender([res], tender_id="QUERY_AUDIT")
            rep_gen = ReportGenerator()
            md_path, json_path = rep_gen.generate_and_save(
                audit_res,
                [res],
                output_dir="reports/generated",
                tender_metadata={"tender_title": f"Ad-Hoc Query: {args.query[:50]}"}
            )
            print(f"{BOLD}{GREEN}============================================================{RESET}")
            print(f"{BOLD}{GREEN}REPORT GENERATED SUCCESSFULLY{RESET}")
            print(f"{BOLD}{GREEN}============================================================{RESET}")
            print(f"Publication Readiness : {audit_res.publication_readiness}")
            print(f"Requirements Analysed : {audit_res.requirements_analyzed}")
            print(f"Review Queue Items    : {len(audit_res.review_queue)}")
            print(f"Markdown Report       : {BOLD}{md_path}{RESET}")
            print(f"JSON Report           : {BOLD}{json_path}{RESET}")
            print(f"{BOLD}{GREEN}============================================================{RESET}\n")

    elif args.tender:
        t_key = args.tender.upper().strip()
        pdf_path = TENDER_MAP.get(t_key, args.tender)

        if not os.path.exists(pdf_path):
            print(f"{RED}Error: Tender PDF file not found at: {pdf_path}{RESET}")
            print(f"Available pre-mapped tender IDs: {', '.join(sorted(TENDER_MAP.keys()))}")
            sys.exit(1)

        print(f"\nProcessing Tender PDF: {pdf_path} (ID: {t_key})...")
        report = recommender.recommend_for_pdf(pdf_path, tender_id=t_key)

        print(f"Found {report.total_requirements} requirement(s) in tender {t_key}.\n")
        for res in report.results:
            format_card(res, input_source=f"Tender PDF: {os.path.basename(pdf_path)} ({t_key})")

        # Automatically display aggregated tender audit summary
        audit_res = recommender.audit_tender(report.results, tender_id=t_key)
        format_audit(audit_res)

        if args.report:
            rep_gen = ReportGenerator()
            md_path, json_path = rep_gen.generate_and_save(
                audit_res,
                report.results,
                output_dir="reports/generated",
                tender_metadata={"tender_title": f"Tender Package {t_key}", "source_file": os.path.basename(pdf_path)}
            )
            print(f"{BOLD}{GREEN}============================================================{RESET}")
            print(f"{BOLD}{GREEN}REPORT GENERATED SUCCESSFULLY{RESET}")
            print(f"{BOLD}{GREEN}============================================================{RESET}")
            print(f"Publication Readiness : {audit_res.publication_readiness}")
            print(f"Requirements Analysed : {audit_res.requirements_analyzed}")
            print(f"Review Queue Items    : {len(audit_res.review_queue)}")
            print(f"Markdown Report       : {BOLD}{md_path}{RESET}")
            print(f"JSON Report           : {BOLD}{json_path}{RESET}")
            print(f"{BOLD}{GREEN}============================================================{RESET}\n")

    elif args.audit:
        audit_target = args.audit.upper().strip()
        print(f"\nRunning Tender Audit & Publication Readiness Engine for: {audit_target}...")

        source_file = None
        if audit_target in TENDER_MAP:
            pdf_path = TENDER_MAP[audit_target]
            source_file = os.path.basename(pdf_path)
            report = recommender.recommend_for_pdf(pdf_path, tender_id=audit_target)
            results = report.results
        else:
            # Representative multi-requirement procurement package
            sample_queries = [
                ("REQ-001", "Supply of CPVC pipes for potable water distribution"),
                ("REQ-002", "Replacement of damaged valves in pumping station"),
                ("REQ-003", "Procurement of valves conforming to IS 10611"),
                ("REQ-004", "Sewerage Pipeline works from Collection Chamber to STP"),
                ("REQ-005", "Low-Oil Food Outlet on BOT concession agreement"),
                ("REQ-006", "SITC of VFD water pump panel for booster station")
            ]
            results = [
                recommender.recommend_for_text(text, req_id=req_id)
                for req_id, text in sample_queries
            ]

        audit_res = recommender.audit_tender(results, tender_id=audit_target)
        format_audit(audit_res)

        if args.report:
            rep_gen = ReportGenerator()
            md_path, json_path = rep_gen.generate_and_save(
                audit_res,
                results,
                output_dir="reports/generated",
                tender_metadata={"tender_title": f"Procurement Audit: {audit_target}", "source_file": source_file}
            )
            print(f"{BOLD}{GREEN}============================================================{RESET}")
            print(f"{BOLD}{GREEN}REPORT GENERATED SUCCESSFULLY{RESET}")
            print(f"{BOLD}{GREEN}============================================================{RESET}")
            print(f"Publication Readiness : {audit_res.publication_readiness}")
            print(f"Requirements Analysed : {audit_res.requirements_analyzed}")
            print(f"Review Queue Items    : {len(audit_res.review_queue)}")
            print(f"Markdown Report       : {BOLD}{md_path}{RESET}")
            print(f"JSON Report           : {BOLD}{json_path}{RESET}")
            print(f"{BOLD}{GREEN}============================================================{RESET}\n")


if __name__ == "__main__":
    main()
