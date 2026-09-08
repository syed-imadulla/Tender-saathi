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

from src.recommend import StandardsRecommender, RequirementRecommendationResult
from src.extract import extract_from_pdf, extract_from_text


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

    # 2. DETECTED CATEGORY
    print(f"\n{BOLD}[2] DETECTED CATEGORY{RESET}     : {YELLOW}{res.category.upper()}{RESET}")

    # 3. TOP CANDIDATE STANDARDS
    print(f"\n{BOLD}[3] TOP CANDIDATE STANDARDS{RESET}:")
    for idx, r in enumerate(res.recommendations[:3], start=1):
        stat_color = GREEN if "active" in r.status.lower() else RED
        star = " ★ (PRIMARY RECOMMENDATION)" if idx == 1 else ""
        print(f"    {idx}. {BOLD}{r.standard_number}{RESET}{star} — {r.title}")
        print(f"       Status: {stat_color}{r.status}{RESET} [{r.version_role}] | Relevance: {r.relevance_score} | Confidence: {r.confidence}")
        if r.superseded_warning:
            print(f"       {RED}⚠ SUPERSEDENCE ALERT: {r.superseded_warning}{RESET}")

    # 4. WHY THIS STANDARD?
    print(f"\n{BOLD}[4] WHY THIS STANDARD?{RESET}    : {res.reason}")

    # 5. SCOPE / EVIDENCE
    print(f"\n{BOLD}[5] SCOPE / EVIDENCE{RESET}      :")
    print(f"    • Provenance Source   : {BLUE}{res.provenance}{RESET}")
    print(f"    • Verbatim Evidence   : {res.evidence}")

    # 6. CURRENT STATUS
    stat_color = GREEN if "active" in res.status.lower() else RED
    print(f"\n{BOLD}[6] CURRENT STATUS{RESET}        : {stat_color}{res.status.upper()}{RESET} [{res.version_role}]")

    # 7. CONFIDENCE
    conf_color = GREEN if res.confidence == "High" else (YELLOW if res.confidence == "Medium" else RED)
    print(f"\n{BOLD}[7] CONFIDENCE{RESET}            : {conf_color}{res.confidence.upper()}{RESET}")

    # 8. ALTERNATIVE STANDARDS
    alt_str = ", ".join(res.alternatives) if res.alternatives else "None identified in top-k retrieval"
    print(f"\n{BOLD}[8] ALTERNATIVE STANDARDS{RESET} : {alt_str}")

    # 9. HUMAN VERIFICATION REQUIRED?
    print(f"\n{BOLD}[9] HUMAN VERIFICATION REQUIRED?{RESET}:")
    if res.human_review_required:
        print(f"    >>> {RED}{BOLD}YES (FLAGGED FOR HUMAN REVIEW){RESET}")
        print(f"    • Reason for Review   : {YELLOW}{res.reason}{RESET}")
    else:
        print(f"    >>> {GREEN}{BOLD}NO (AUTOMATED RECOMMENDATION GROUNDED IN EVIDENCE){RESET}")

    print(CYAN + d_hr + RESET + "\n")


def main():
    parser = argparse.ArgumentParser(description="SIH26108 Presentation-Ready Recommendation Demo CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", type=str, help="Single procurement requirement specification string")
    group.add_argument("--tender", type=str, help="Tender ID to demo (e.g. T002, T007, T010, T020) or PDF path")

    args = parser.parse_args()
    recommender = StandardsRecommender()

    if args.query:
        print(f"\nProcessing single requirement query: \"{args.query}\"...")
        res = recommender.recommend_for_text(args.query, req_id="DEMO-REQ-001")
        format_card(res, input_source=f"CLI Text Query: '{args.query}'")

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


if __name__ == "__main__":
    main()
