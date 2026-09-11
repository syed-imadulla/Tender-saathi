"""
scripts/validate_real_world_domains.py
Purpose: Real-world validation of TenderSaathi Priority 3 + 4 pipeline across 7 distinct domains:
1. CPVC pipes (IS 15778, CPVC QCO)
2. Waterworks valves (IS 778, Valves QCO)
3. Electrical cables (IS 694, Cables QCO)
4. Electric motors (IS 12615, Motors QCO)
5. Cement (IS 8112 / IS 269, Cement QCO)
6. Electronics / IT equipment (IS 13252, MeitY CRS)
7. Precious metals (IS 1417, Gold Hallmarking Order)
"""

import json
import os
from src.standards import StandardsDatabase
from src.recommend import StandardsRecommender


DOMAINS_TEST_CASES = [
    {
        "domain": "Civil / Plumbing (CPVC)",
        "query": "Providing and fixing Chlorinated Polyvinyl Chloride (CPVC) pipes for hot and cold water distribution including CPVC fittings",
        "expected_standard": "IS 15778",
        "expected_qco": "CURRENT",
        "expected_cert": "APPLICABLE",
        "expected_crs": "NOT_IDENTIFIED",
        "expected_hallmarking": "NOT_APPLICABLE"
    },
    {
        "domain": "Mechanical / Waterworks Valves",
        "query": "Copper alloy gate globe and check valves for waterworks purposes 50 mm diameter",
        "expected_standard": "IS 778",
        "expected_qco": "CURRENT",
        "expected_cert": "APPLICABLE",
        "expected_crs": "NOT_IDENTIFIED",
        "expected_hallmarking": "NOT_APPLICABLE"
    },
    {
        "domain": "Electrical / Wires & Cables",
        "query": "PVC insulated unsheathed copper cables 1100V grade for internal conduit wiring",
        "expected_standard": "IS 694",
        "expected_qco": "CURRENT",
        "expected_cert": "APPLICABLE",
        "expected_crs": "NOT_IDENTIFIED",
        "expected_hallmarking": "NOT_APPLICABLE"
    },
    {
        "domain": "Electrical / Electric Motors",
        "query": "Three phase squirrel cage induction motors energy efficient IE3 premium class 11 kW",
        "expected_standard": "IS 12615",
        "expected_qco": "CURRENT",
        "expected_cert": "APPLICABLE",
        "expected_crs": "NOT_IDENTIFIED",
        "expected_hallmarking": "NOT_APPLICABLE"
    },
    {
        "domain": "Civil / Cement Materials",
        "query": "Ordinary Portland Cement 43 grade in 50 kg bags for structural concrete",
        "expected_standard": "IS 8112",
        "expected_qco": "CURRENT",
        "expected_cert": "APPLICABLE",
        "expected_crs": "NOT_IDENTIFIED",
        "expected_hallmarking": "NOT_APPLICABLE"
    },
    {
        "domain": "Electronics / IT Equipment (CRS)",
        "query": "Supply of laptop computers and notebooks for engineering design office",
        "expected_standard": "IS 13252",
        "expected_qco": "NOT_IDENTIFIED",
        "expected_cert": "NOT_IDENTIFIED",
        "expected_crs": "APPLICABLE",
        "expected_hallmarking": "NOT_APPLICABLE"
    },
    {
        "domain": "Precious Metals / Hallmarking",
        "query": "Procurement of 22 carat gold commemorative medals and jewellery artefacts with mandatory BIS hallmarking",
        "expected_standard": "IS 1417",
        "expected_qco": "NOT_IDENTIFIED",
        "expected_cert": "NOT_IDENTIFIED",
        "expected_crs": "NOT_IDENTIFIED",
        "expected_hallmarking": "APPLICABLE"
    }
]


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Use expanded catalogue for 7-domain validation
    catalogue_db = StandardsDatabase(db_path=os.path.join(root_dir, "data", "catalogue", "catalogue.db"))
    recommender = StandardsRecommender(db=catalogue_db)

    print("==================================================================")
    print("       TENDERSAATHI REAL-WORLD 7-DOMAIN VALIDATION REPORT         ")
    print("==================================================================\n")

    all_passed = True

    for i, tc in enumerate(DOMAINS_TEST_CASES, start=1):
        domain = tc["domain"]
        query = tc["query"]
        res = recommender.recommend_for_text(query, req_id=f"VAL-{i:02d}")

        cand = res.candidate_standard or "NONE"
        reg = res.regulatory or {}
        qco_st = (reg.get("qco") or {}).get("status", "NONE")
        cert_st = (reg.get("certification") or {}).get("status", "NONE")
        crs_st = (reg.get("crs") or {}).get("status", "NONE")
        hm_st = (reg.get("hallmarking") or {}).get("status", "NONE")

        qco_ok = (qco_st == tc["expected_qco"])
        cert_ok = (cert_st == tc["expected_cert"])
        crs_ok = (crs_st == tc["expected_crs"])
        hm_ok = (hm_st == tc["expected_hallmarking"])
        std_ok = tc["expected_standard"] in cand

        passed = qco_ok and cert_ok and crs_ok and hm_ok and std_ok
        if not passed:
            all_passed = False

        status_mark = "✓ PASS" if passed else "✗ FAIL"

        print(f"Domain {i}: {domain} [{status_mark}]")
        print(f"  Requirement : {query[:75]}...")
        print(f"  Standard    : {cand} (expected: {tc['expected_standard']}) -> {'OK' if std_ok else 'MISMATCH'}")
        print(f"  QCO Status  : {qco_st:14} (expected: {tc['expected_qco']:14}) -> {'OK' if qco_ok else 'MISMATCH'}")
        print(f"  Cert Status : {cert_st:14} (expected: {tc['expected_cert']:14}) -> {'OK' if cert_ok else 'MISMATCH'}")
        print(f"  CRS Status  : {crs_st:14} (expected: {tc['expected_crs']:14}) -> {'OK' if crs_ok else 'MISMATCH'}")
        print(f"  Hallmarking : {hm_st:14} (expected: {tc['expected_hallmarking']:14}) -> {'OK' if hm_ok else 'MISMATCH'}")
        print(f"  Human Review: {res.human_review_required}")
        print(f"  Why Matches : {res.why_it_matches}")
        print("-" * 66)

    print(f"\nFinal Validation Status: {'ALL 7 DOMAINS PASSED PERFECTLY' if all_passed else 'SOME DOMAINS FAILED'}")


if __name__ == "__main__":
    main()
