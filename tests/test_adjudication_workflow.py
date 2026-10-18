"""
tests/test_adjudication_workflow.py

Comprehensive deterministic tests for Phase 13:
1. Adjudication rubric completeness.
2. Reviewer packet generation and manifest verification (40 packets).
3. Reviewer qualification and evidence validation.
4. Two-party consensus logic and conflict escalation.
5. Ingestion gating and active corpus protection.
"""

import os
import json
import hashlib
import unittest
from scripts.ingest_adjudication import (
    validate_reviewer_block,
    check_consensus,
    parse_packet_yaml_blocks,
    APPROVED_ROLES,
    CANONICAL_DECISIONS
)

RUBRIC_PATH = "docs/data/ADJUDICATION_RUBRIC.md"
MANIFEST_PATH = "reports/adjudication_packets/packet_manifest.json"
PACKETS_DIR = "reports/adjudication_packets/packets"
GT_PATH = "dataset/ground_truth/ground_truth.csv"
EXPECTED_GT_SHA = "8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc"


class TestAdjudicationWorkflow(unittest.TestCase):
    """Deterministic tests for expert adjudication workflow and governance."""

    def test_01_adjudication_rubric_file_integrity(self):
        """1. Verify ADJUDICATION_RUBRIC.md covers all 5 canonical decisions and evidence requirements."""
        self.assertTrue(os.path.isfile(RUBRIC_PATH), f"Rubric file missing at {RUBRIC_PATH}")
        with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        for dec in CANONICAL_DECISIONS:
            self.assertIn(dec, content, f"Rubric must document canonical decision: {dec}")

        self.assertIn("Clause-Level Evidence", content)
        self.assertIn("Two-Party Consensus", content)
        self.assertIn("CPWD", content)
        self.assertIn("BIS", content)

    def test_02_packet_manifest_and_count(self):
        """2. Verify that 40 reviewer packets are indexed in packet_manifest.json."""
        self.assertTrue(os.path.isfile(MANIFEST_PATH), f"Manifest missing at {MANIFEST_PATH}")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertGreaterEqual(manifest["total_packets"], 40)
        self.assertEqual(manifest["unverified_baseline_count"], 20)
        self.assertGreaterEqual(manifest["machine_predicted_count"], 20)
        self.assertEqual(len(manifest["cases"]), manifest["total_packets"])

        # Check physical packet files exist
        for case in manifest["cases"]:
            pfile = os.path.join(PACKETS_DIR, case["packet_file"])
            self.assertTrue(os.path.isfile(pfile), f"Physical packet file missing: {pfile}")

    def test_03_packet_format_and_unverified_guard(self):
        """3. Verify packets contain required sections and leave reviewer blocks blank."""
        sample_packet = os.path.join(PACKETS_DIR, "CASE_T001_R002.md")
        self.assertTrue(os.path.isfile(sample_packet))
        with open(sample_packet, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Tender Specification Text (Verbatim)", content)
        self.assertIn("BIS Standards Catalogue Context", content)
        self.assertIn("Domain Expert Adjudication Form", content)
        self.assertIn("Reviewer A Evaluation", content)
        self.assertIn("Reviewer B Evaluation", content)

        rev_a, rev_b, fm = parse_packet_yaml_blocks(content)
        self.assertIsNotNone(fm)
        self.assertEqual(fm.get("requirement_id"), "T001-R002")
        # Reviewer blocks must be empty in generated packets waiting for human experts
        self.assertEqual(str(rev_a.get("reviewer_role", "")), "")
        self.assertEqual(str(rev_b.get("reviewer_role", "")), "")

    def test_04_consensus_validator_agreement(self):
        """4. Verify two-party consensus succeeds when both reviewers submit valid matching verdicts."""
        rev_a = {
            "reviewer_id": "REV-01",
            "reviewer_full_name": "Er. R. Sharma",
            "reviewer_role": "CPWD_EXECUTIVE_ENGINEER",
            "organization": "CPWD Northern Zone",
            "decision": "RECOMMEND",
            "verified_standards": "IS 15905 : 2011",
            "clause_reference": "IS 15905:2011 Clause 1 Scope",
            "technical_rationale": "Requirement calls for hubless cast iron drainage pipe. Conforms to IS 15905 specifications.",
            "reviewed_at_utc": "2026-10-18T10:00:00Z",
            "signature_or_token: ": "CPWD-EE-DEL-9842"
        }
        rev_b = {
            "reviewer_id": "REV-02",
            "reviewer_full_name": "Dr. V. Patel",
            "reviewer_role": "BIS_STANDARDS_OFFICER",
            "organization": "Bureau of Indian Standards",
            "decision": "RECOMMEND",
            "verified_standards": "IS 15905 : 2011",
            "clause_reference": "IS 15905:2011 Clause 1 Scope",
            "technical_rationale": "Verified against CED 53 catalogue. Definitive standard for spigotless hubless soil pipes.",
            "reviewed_at_utc": "2026-10-18T11:30:00Z",
            "signature_or_token: ": "BIS-SO-HQ-4412"
        }

        val_a, errs_a = validate_reviewer_block(rev_a, "Reviewer A")
        val_b, errs_b = validate_reviewer_block(rev_b, "Reviewer B")
        self.assertTrue(val_a, f"Reviewer A errors: {errs_a}")
        self.assertTrue(val_b, f"Reviewer B errors: {errs_b}")

        consensus_ok, status, dissents = check_consensus(rev_a, rev_b)
        self.assertTrue(consensus_ok)
        self.assertEqual(status, "REACHED")
        self.assertEqual(len(dissents), 0)

    def test_05_consensus_validator_conflict_escalation(self):
        """5. Verify conflict escalation when Reviewer A and Reviewer B disagree."""
        rev_a = {
            "reviewer_id": "REV-01",
            "reviewer_role": "CPWD_EXECUTIVE_ENGINEER",
            "decision": "RECOMMEND",
            "verified_standards": "IS 778 : 1984",
            "clause_reference": "IS 778 Clause 1",
            "technical_rationale": "Presumes low pressure brass isolation valve for generic replacement.",
            "reviewed_at_utc": "2026-10-18T10:00:00Z"
        }
        rev_b = {
            "reviewer_id": "REV-02",
            "reviewer_role": "BIS_STANDARDS_OFFICER",
            "decision": "ABSTAIN_UNDER_SPECIFIED",
            "verified_standards": "",
            "clause_reference": "",
            "technical_rationale": "Generic valve replacement without line pressure, temperature, or media is under-specified.",
            "reviewed_at_utc": "2026-10-18T11:00:00Z"
        }

        consensus_ok, status, dissents = check_consensus(rev_a, rev_b)
        self.assertFalse(consensus_ok)
        self.assertEqual(status, "CONFLICT_ESCALATION")
        self.assertIn("Decision mismatch", dissents[0])

    def test_06_unapproved_role_rejection(self):
        """6. Verify reviewer block validation rejects unapproved roles."""
        bad_rev = {
            "reviewer_id": "REV-FAKE",
            "reviewer_role": "SOFTWARE_DEVELOPER",  # Unapproved
            "decision": "RECOMMEND",
            "verified_standards": "IS 15905",
            "clause_reference": "Clause 1",
            "technical_rationale": "Looks correct to me based on website search.",
            "reviewed_at_utc": "2026-10-18T10:00:00Z"
        }
        ok, errs = validate_reviewer_block(bad_rev, "Reviewer A")
        self.assertFalse(ok)
        self.assertTrue(any("Invalid or unapproved role" in e for e in errs))

    def test_07_insufficient_rationale_rejection(self):
        """7. Verify reviewer block validation rejects rationale < 20 chars."""
        short_rev = {
            "reviewer_id": "REV-01",
            "reviewer_role": "CPWD_EXECUTIVE_ENGINEER",
            "decision": "RECOMMEND",
            "verified_standards": "IS 15905",
            "clause_reference": "Clause 1",
            "technical_rationale": "Approved.",  # Only 9 chars!
            "reviewed_at_utc": "2026-10-18T10:00:00Z"
        }
        ok, errs = validate_reviewer_block(short_rev, "Reviewer A")
        self.assertFalse(ok)
        self.assertTrue(any("at least 20 characters" in e for e in errs))

    def test_08_active_ground_truth_untouched_boundary(self):
        """8. Verify active ground_truth.csv remains byte-for-byte intact with 0 unbacked approvals."""
        self.assertTrue(os.path.isfile(GT_PATH))
        with open(GT_PATH, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(
            actual_sha,
            EXPECTED_GT_SHA,
            "CRITICAL: Active ground_truth.csv was modified without formal expert adjudication approval!"
        )


if __name__ == "__main__":
    unittest.main()
