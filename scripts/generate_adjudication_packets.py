#!/usr/bin/env python3
"""
scripts/generate_adjudication_packets.py

Generates reviewer-ready case packets for domain expert adjudication.
Compiles 40 cases (20 active benchmark cases from ground_truth.csv and 
20 staged candidate cases from candidates_staging.csv).

For each case, fetches:
- Verbatim requirement text and category
- Physical source PDF link and page reference
- Current system prediction and reasoning
- Relevant BIS catalogue metadata (title, status, scope) from standards.db
- Standardized blank two-party adjudication reply form conforming to ADJUDICATION_RUBRIC.md

Outputs to: reports/adjudication_packets/packets/
Emits manifest: reports/adjudication_packets/packet_manifest.json
"""

import os
import re
import csv
import json
import sqlite3
import datetime
from typing import Dict, List, Any, Optional

DB_PATH = "data/standards.db"
GT_PATH = "dataset/ground_truth/ground_truth.csv"
STAGING_PATH = "dataset/ground_truth/candidates_staging.csv"
OUTPUT_DIR = "reports/adjudication_packets/packets"
MANIFEST_PATH = "reports/adjudication_packets/packet_manifest.json"


def get_standard_details(standard_number: str) -> Optional[Dict[str, Any]]:
    """Fetches title, status, and scope for a standard from standards.db."""
    if not os.path.isfile(DB_PATH) or not standard_number:
        return None
    
    # Normalize token for search
    m = re.search(r'\b(?:IS|IS/ISO|IS/IEC|SP)\s*(?:/|\s*)?\d+(?:\s*(?:Part|Sec)\s*\d+)*', standard_number, re.IGNORECASE)
    norm = m.group(0).strip() if m else standard_number.strip()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT standard_number, full_title, status, scope, technical_committee FROM standards WHERE standard_number LIKE ? LIMIT 1",
            (f"%{norm}%",)
        )
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "standard_number": row[0],
                "full_title": row[1],
                "status": row[2],
                "scope": row[3] or "Scope excerpt not available in offline catalogue snapshot.",
                "technical_committee": row[4] or "Unspecified"
            }
    except Exception:
        pass
    return None


def generate_packet_content(row: Dict[str, Any], cohort: str) -> str:
    req_id = row.get("requirement_id", "REQ-UNKNOWN")
    tender_id = row.get("tender_id", "T-UNKNOWN")
    sector = row.get("procurement_sector", "PROVISIONAL:UNKNOWN")
    doc = row.get("source_document", "Unknown Document")
    page = row.get("source_page", "1")
    req_text = row.get("requirement_text", "")
    category = row.get("category", "material")
    expected_dec = row.get("expected_decision", "RECOMMEND")
    applicable_std = row.get("applicable_standard", "") or "None Specified / Under-Specified"
    std_title = row.get("standard_title", "")
    reasoning = row.get("reasoning", "")
    evidence_ref = row.get("evidence_reference", "")
    evidence_snip = row.get("evidence_snippet", "")
    
    # Standard lookup
    details = get_standard_details(applicable_std) if applicable_std and applicable_std != "None Specified / Under-Specified" else None

    lines = [
        "---",
        f"packet_id: \"CASE_{req_id.replace('-', '_')}\"",
        f"requirement_id: \"{req_id}\"",
        f"tender_id: \"{tender_id}\"",
        f"source_document: \"{doc}\"",
        f"source_page: {page}",
        f"procurement_sector: \"{sector}\"",
        f"cohort: \"{cohort}\"",
        f"current_expected_decision: \"{expected_dec}\"",
        f"generated_at_utc: \"{datetime.datetime.now(datetime.timezone.utc).isoformat()}\"",
        "---",
        "",
        f"# Tender Saathi — Expert Adjudication Packet: {req_id}",
        "",
        "## 1. Case Metadata & Source Provenance",
        "",
        f"- **Requirement ID**: `{req_id}`",
        f"- **Tender Notice ID**: `{tender_id}`",
        f"- **Procurement Sector**: `{sector}`",
        f"- **Physical Source Document**: `{doc}`",
        f"- **Source Page / Section**: Page `{page}`",
        f"- **Procurement Category**: `{category}`",
        f"- **Benchmark Cohort**: `{cohort}`",
        "",
        "---",
        "",
        "## 2. Tender Specification Text (Verbatim)",
        "",
        "> " + req_text.replace("\n", " "),
        "",
        "---",
        "",
        "## 3. Current Machine / Baseline Classification",
        "",
        f"- **Proposed Decision**: `{expected_dec}`",
        f"- **Candidate Standard(s)**: `{applicable_std}`",
        f"- **Candidate Title**: {std_title or (details['full_title'] if details else 'N/A')}",
        f"- **Recorded Evidence Reference**: `{evidence_ref or 'Pending Expert Citation'}`",
        f"- **Recorded Technical Reasoning**: {reasoning or 'Pending Expert Adjudication'}",
        "",
        "---",
        "",
        "## 4. BIS Standards Catalogue Context",
        ""
    ]

    if details:
        lines.extend([
            f"- **Standard Number**: `{details['standard_number']}`",
            f"- **Official Title**: {details['full_title']}",
            f"- **Lifecycle Status**: `{details['status']}`",
            f"- **Technical Committee**: `{details['technical_committee']}`",
            f"- **Official Scope Excerpt**:",
            f"  > {details['scope']}",
            ""
        ])
    else:
        lines.extend([
            "*No single specific catalogue standard bound. Case requires expert determination from the BIS catalogue.*",
            ""
        ])

    lines.extend([
        "---",
        "",
        "## 5. Domain Expert Adjudication Form",
        "",
        "> [!IMPORTANT]",
        "> Refer to `docs/data/ADJUDICATION_RUBRIC.md` for complete decision criteria.",
        "> Approved roles: `CPWD_EXECUTIVE_ENGINEER`, `CPWD_ASSISTANT_ENGINEER`, `BIS_STANDARDS_OFFICER`, `MES_MILITARY_ENGINEER`, `PUBLIC_PROCUREMENT_SPECIALIST`.",
        "",
        "### Reviewer A Evaluation",
        "",
        "```yaml",
        "reviewer_id: \"\"",
        "reviewer_full_name: \"\"",
        "reviewer_role: \"\" # e.g. CPWD_EXECUTIVE_ENGINEER",
        "organization: \"\"",
        "decision: \"\" # RECOMMEND | ABSTAIN_UNDER_SPECIFIED | ABSTAIN_AMBIGUOUS | ABSTAIN_CONFLICTING | REJECT_INELIGIBLE",
        "verified_standards: \"\" # e.g. IS 15905 : 2011",
        "clause_reference: \"\" # e.g. IS 15905:2011 Clause 1 Scope",
        "technical_rationale: \"\" # Minimum 20 characters explaining the engineering basis",
        "reviewed_at_utc: \"\" # YYYY-MM-DDTHH:MM:SSZ",
        "signature_or_token: \"\"",
        "```",
        "",
        "### Reviewer B Evaluation (Consensus Check)",
        "",
        "```yaml",
        "reviewer_id: \"\"",
        "reviewer_full_name: \"\"",
        "reviewer_role: \"\" # e.g. BIS_STANDARDS_OFFICER",
        "organization: \"\"",
        "decision: \"\" # RECOMMEND | ABSTAIN_UNDER_SPECIFIED | ABSTAIN_AMBIGUOUS | ABSTAIN_CONFLICTING | REJECT_INELIGIBLE",
        "verified_standards: \"\" # e.g. IS 15905 : 2011",
        "clause_reference: \"\" # e.g. IS 15905:2011 Clause 1 Scope",
        "technical_rationale: \"\" # Minimum 20 characters explaining the engineering basis",
        "reviewed_at_utc: \"\" # YYYY-MM-DDTHH:MM:SSZ",
        "signature_or_token: \"\"",
        "```",
        "",
        "### Consensus & Adjudication Status",
        "",
        "- [ ] **Consensus Reached**: Reviewer A and Reviewer B agreed on Decision and Standard(s).",
        "- [ ] **Disagreement / Escalation**: Requires Senior Adjudicator arbitration.",
        ""
    ])

    return "\n".join(lines)


def main():
    print("Generating Tender Saathi Domain Expert Adjudication Packets (Phase 13)...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    manifest_cases = []
    
    # 1. Process 20 Baseline Cases
    if os.path.isfile(GT_PATH):
        with open(GT_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                packet_str = generate_packet_content(row, cohort="UNVERIFIED_BASELINE")
                fname = f"CASE_{row['requirement_id'].replace('-', '_')}.md"
                fpath = os.path.join(OUTPUT_DIR, fname)
                with open(fpath, "w", encoding="utf-8") as pf:
                    pf.write(packet_str)
                manifest_cases.append({
                    "packet_file": fname,
                    "requirement_id": row["requirement_id"],
                    "tender_id": row.get("tender_id", ""),
                    "procurement_sector": row.get("procurement_sector", ""),
                    "cohort": "UNVERIFIED_BASELINE",
                    "current_expected_decision": row.get("expected_decision", "")
                })

    # 2. Process 20 Staged Candidate Cases
    if os.path.isfile(STAGING_PATH):
        with open(STAGING_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                packet_str = generate_packet_content(row, cohort="MACHINE_PREDICTED")
                fname = f"CASE_{row['requirement_id'].replace('-', '_')}.md"
                fpath = os.path.join(OUTPUT_DIR, fname)
                with open(fpath, "w", encoding="utf-8") as pf:
                    pf.write(packet_str)
                manifest_cases.append({
                    "packet_file": fname,
                    "requirement_id": row["requirement_id"],
                    "tender_id": row.get("tender_id", ""),
                    "procurement_sector": row.get("procurement_sector", ""),
                    "cohort": "MACHINE_PREDICTED",
                    "current_expected_decision": row.get("expected_decision", "")
                })

    manifest = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_packets": len(manifest_cases),
        "unverified_baseline_count": sum(1 for c in manifest_cases if c["cohort"] == "UNVERIFIED_BASELINE"),
        "machine_predicted_count": sum(1 for c in manifest_cases if c["cohort"] == "MACHINE_PREDICTED"),
        "packets_directory": OUTPUT_DIR,
        "cases": manifest_cases
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    print(f"\n[✓] Generated {len(manifest_cases)} adjudication packets in {OUTPUT_DIR}")
    print(f"[✓] Emitted packet manifest to {MANIFEST_PATH}\n")


if __name__ == "__main__":
    main()
