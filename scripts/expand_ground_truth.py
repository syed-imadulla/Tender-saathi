#!/usr/bin/env python3
"""
scripts/expand_ground_truth.py

Candidate benchmark expansion script for Tender Saathi.
Extracts unbenchmarked procurement requirements from real government tenders,
generates machine-predicted standard proposals, and stages them in candidates_staging.csv.

Guarantees:
- Output is written exclusively to staging (default: dataset/ground_truth/candidates_staging.csv).
- Active benchmark dataset (dataset/ground_truth/ground_truth.csv) is strictly read-only.
- All staged rows are explicitly tagged with adjudication_status: MACHINE_PREDICTED.
- All staged rows have human_verified: FALSE, empty reviewer_role, and empty reviewed_at.
- Runs 100% offline.
"""

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Set

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.extract import extract_from_text
from src.recommend import StandardsRecommender

# Canonical 24 columns
ALL_24_COLUMNS = [
    "tender_id",
    "requirement_id",
    "requirement_text",
    "category",
    "source_page",
    "explicit_standard",
    "applicable_standard",
    "standard_title",
    "standard_status",
    "verification_outcome",
    "verification_method",
    "evidence_source",
    "evidence_reference",
    "evidence_snippet",
    "reasoning",
    "confidence",
    "human_verified",
    "reviewer_notes",
    "source_document",
    "procurement_sector",
    "expected_decision",
    "adjudication_status",
    "reviewer_role",
    "reviewed_at",
]


def load_existing_benchmark_ids(gt_path: str) -> Set[str]:
    """Load requirement IDs from the active benchmark to prevent duplicates."""
    if not os.path.isfile(gt_path):
        return set()
    with open(gt_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {r["requirement_id"].strip() for r in reader if r.get("requirement_id")}


def load_tender_metadata(meta_path: str) -> Dict[str, Dict[str, str]]:
    """Load tender metadata for document and sector provenance mapping."""
    if not os.path.isfile(meta_path):
        return {}
    meta_by_id = {}
    with open(meta_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            meta_by_id[r["tender_id"].strip()] = r
    return meta_by_id


def resolve_provisional_sector(meta: Dict[str, str], fallback_cat: str) -> str:
    """Map product category to an explicit provisional sector tag."""
    cat = meta.get("product_category_if_detected", fallback_cat or "Unknown").lower()
    if "civil" in cat:
        return "PROVISIONAL:CIVIL_WORKS"
    elif "elect" in cat:
        return "PROVISIONAL:ELECTRICAL"
    elif "mech" in cat:
        return "PROVISIONAL:MECHANICAL"
    elif "cater" in cat or "hotel" in cat or "food" in cat:
        return "PROVISIONAL:CATERING"
    else:
        clean_cat = "".join(c if c.isalnum() else "_" for c in cat).upper()
        return f"PROVISIONAL:{clean_cat}"


def stage_expansion_candidates(
    output_path: str,
    gt_path: str = "dataset/ground_truth/ground_truth.csv",
    reqs_path: str = "dataset/tender_requirements.jsonl",
    meta_path: str = "dataset/tender_metadata.csv",
    limit: int = 20,
    recommender: StandardsRecommender = None
) -> List[Dict[str, Any]]:
    """
    Extracts candidate requirements, runs model proposal, and writes to staging.
    Never modifies gt_path.
    """
    existing_ids = load_existing_benchmark_ids(gt_path)
    meta_by_id = load_tender_metadata(meta_path)
    rec = recommender or StandardsRecommender(retrieval_mode="hybrid")

    candidates: List[Dict[str, Any]] = []

    if not os.path.isfile(reqs_path):
        raise FileNotFoundError(f"Tender requirements file not found at: {reqs_path}")

    with open(reqs_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            rid = item.get("requirement_id", "").strip()
            tid = item.get("tender_id", "").strip()
            text = item.get("candidate_requirement", "").strip()

            if not rid or rid in existing_ids:
                continue

            # Limit staged count
            if len(candidates) >= limit:
                break

            m = meta_by_id.get(tid, {})
            orig_doc = m.get("original_filename", "")
            doc_rel = os.path.join("tenders", "raw", orig_doc) if orig_doc else "UNRESOLVED:missing_tender_file"
            sector = resolve_provisional_sector(m, item.get("category", "material"))

            # Run offline recommendation proposal
            req_obj = extract_from_text(text, requirement_id=rid)
            rec_res = rec.recommend_for_requirement(req_obj)

            top1_std = rec_res.candidate_standard or ""
            top1_title = rec_res.title or ""
            top1_status = rec_res.status or "Active"
            confidence = rec_res.confidence or "Medium"
            reason = rec_res.reason or "Candidate standard proposed by machine retrieval ensemble."
            evidence = str(rec_res.evidence or "")

            if top1_std and not rec_res.human_review_required:
                exp_decision = "RECOMMEND"
                verification_outcome = "STANDARD_MISSING"
            else:
                exp_decision = "ABSTAIN_UNDER_SPECIFIED"
                verification_outcome = "NEEDS_EXPERT_VERIFICATION"

            row = {
                "tender_id": tid,
                "requirement_id": rid,
                "requirement_text": text,
                "category": item.get("category", "material"),
                "source_page": str(item.get("page", 1)),
                "explicit_standard": item.get("mentioned_standard") or "",
                "applicable_standard": top1_std,
                "standard_title": top1_title,
                "standard_status": top1_status,
                "verification_outcome": verification_outcome,
                "verification_method": "MACHINE_PREDICTED",
                "evidence_source": "BIS Catalogue & Hybrid Retrieval Index",
                "evidence_reference": f"Proposed for {top1_std} pending human review",
                "evidence_snippet": evidence[:250],
                "reasoning": reason,
                "confidence": confidence,
                "human_verified": "FALSE",  # Mandatory: NEVER True from machine extraction
                "reviewer_notes": "Staged candidate generated by expansion pipeline. Requires domain expert verification.",
                "source_document": doc_rel,
                "procurement_sector": sector,
                "expected_decision": exp_decision,
                "adjudication_status": "MACHINE_PREDICTED",  # Mandatory segregation
                "reviewer_role": "",  # Mandatory: empty until expert review
                "reviewed_at": "",    # Mandatory: empty until expert review
            }
            candidates.append(row)

    # Write to staging CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(ALL_24_COLUMNS)
        for c in candidates:
            writer.writerow([c.get(col, "") for col in ALL_24_COLUMNS])

    return candidates


def main():
    parser = argparse.ArgumentParser(
        description="Stage candidate benchmark requirements from unlabelled tender specifications"
    )
    parser.add_argument(
        "--output",
        default="dataset/ground_truth/candidates_staging.csv",
        help="Path for candidate staging CSV output (default: dataset/ground_truth/candidates_staging.csv)"
    )
    parser.add_argument(
        "--ground-truth",
        default="dataset/ground_truth/ground_truth.csv",
        help="Path to active ground truth CSV (read-only, to prevent duplicates)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum candidate cases to extract and stage"
    )

    args = parser.parse_args()

    # Safety check: Prevent user from accidentally specifying ground_truth.csv as output
    if os.path.abspath(args.output) == os.path.abspath(args.ground_truth):
        print("ERROR: Output path cannot be the active ground_truth.csv benchmark file!")
        print("Candidates must be written to a staging file (e.g. dataset/ground_truth/candidates_staging.csv).")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("      TENDER SAATHI — BENCHMARK GROUND-TRUTH EXPANSION PIPELINE      ")
    print("=" * 80)
    print(f"Active Benchmark (Protected): {args.ground_truth}")
    print(f"Staging Destination        : {args.output}")
    print(f"Extraction Limit           : {args.limit} candidates")
    print("Executing offline candidate extraction & heuristic recommendation...\n")

    candidates = stage_expansion_candidates(
        output_path=args.output,
        gt_path=args.ground_truth,
        limit=args.limit
    )

    print("\n" + "=" * 80)
    print("                         EXPANSION STAGING COMPLETE                     ")
    print("=" * 80)
    print(f"Staged Candidates Count     : {len(candidates)}")
    print(f"Adjudication Status Assigned: MACHINE_PREDICTED (100%)")
    print(f"Human Verified Flag         : FALSE (100%)")
    print(f"Reviewer Credentials Flag   : UNASSIGNED (100%)")
    print(f"Output File                 : {args.output}")
    print("=" * 80)
    print("\nNext step: Domain expert panel must review and adjudicate staged rows")
    print("per instructions in docs/data/GROUND_TRUTH_GOVERNANCE.md before promotion.\n")


if __name__ == "__main__":
    main()
