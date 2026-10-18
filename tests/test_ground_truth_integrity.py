"""
tests/test_ground_truth_integrity.py

Automated integrity tests for the extended 24-column ground truth benchmark schema,
canonical vocabularies, source document defensibility, and anti-falsification constraints.
Part of Phase 12 (Plan 12-01).
"""

import csv
import json
import os
import unittest
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GT_PATH = os.path.join(REPO_ROOT, "dataset", "ground_truth", "ground_truth.csv")
EXTRACTION_RESULTS_DIR = os.path.join(REPO_ROOT, "dataset", "extraction_results")

CORE_18_COLUMNS = [
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
]

NEW_6_COLUMNS = [
    "source_document",
    "procurement_sector",
    "expected_decision",
    "adjudication_status",
    "reviewer_role",
    "reviewed_at",
]

ALL_24_COLUMNS = CORE_18_COLUMNS + NEW_6_COLUMNS

CANONICAL_DECISIONS = {
    "RECOMMEND",
    "ABSTAIN_UNDER_SPECIFIED",
    "ABSTAIN_AMBIGUOUS",
    "ABSTAIN_CONFLICTING",
    "REJECT_INELIGIBLE",
}

CANONICAL_ADJUDICATION_STATUSES = {
    "UNVERIFIED_BASELINE",
    "MACHINE_PREDICTED",
    "EXPERT_VERIFIED",
}


def normalize_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


class TestGroundTruthIntegrity(unittest.TestCase):
    """Tests guaranteeing schema integrity, backward compatibility, and audit defensibility."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.isfile(GT_PATH), f"ground_truth.csv not found at {GT_PATH}")
        with open(GT_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            cls.header = next(reader)
            cls.raw_rows = list(reader)

        with open(GT_PATH, "r", encoding="utf-8") as f:
            dict_reader = csv.DictReader(f)
            cls.dict_rows = list(dict_reader)

    def test_01_schema_column_count_and_order(self):
        """1. Verify ground_truth.csv has exactly 24 columns in strict canonical order."""
        self.assertEqual(
            len(self.header), 24,
            f"Expected exactly 24 columns, got {len(self.header)}"
        )
        self.assertEqual(
            self.header[:18], CORE_18_COLUMNS,
            "The first 18 columns must strictly preserve the original column names and order."
        )
        self.assertEqual(
            self.header[18:], NEW_6_COLUMNS,
            "The appended 6 columns must strictly match NEW_6_COLUMNS."
        )
        self.assertEqual(self.header, ALL_24_COLUMNS)

    def test_02_row_count_and_primary_keys(self):
        """2. Verify exactly 20 locked baseline rows with unique primary keys."""
        self.assertEqual(
            len(self.raw_rows), 20,
            f"Expected exactly 20 baseline rows, got {len(self.raw_rows)}"
        )
        for i, row in enumerate(self.raw_rows):
            self.assertEqual(
                len(row), 24,
                f"Row {i} has {len(row)} values, expected 24"
            )

        req_ids = [r["requirement_id"] for r in self.dict_rows]
        self.assertEqual(len(req_ids), len(set(req_ids)), "Duplicate requirement_id detected!")
        for rid in req_ids:
            self.assertTrue(bool(rid), "Empty requirement_id found!")

    def test_03_canonical_expected_decision_vocabulary(self):
        """3. Verify all expected_decision values conform to canonical vocabulary."""
        for row in self.dict_rows:
            rid = row["requirement_id"]
            decision = row.get("expected_decision", "")
            self.assertIn(
                decision, CANONICAL_DECISIONS,
                f"Invalid expected_decision '{decision}' in row {rid}"
            )

        # Specifically verify T002-R002 is ABSTAIN_UNDER_SPECIFIED
        r002 = next((r for r in self.dict_rows if r["requirement_id"] == "T002-R002"), None)
        self.assertIsNotNone(r002)
        self.assertEqual(r002["expected_decision"], "ABSTAIN_UNDER_SPECIFIED")

    def test_04_adjudication_status_vocabulary(self):
        """4. Verify all adjudication_status values conform to canonical vocabulary."""
        for row in self.dict_rows:
            rid = row["requirement_id"]
            status = row.get("adjudication_status", "")
            self.assertIn(
                status, CANONICAL_ADJUDICATION_STATUSES,
                f"Invalid adjudication_status '{status}' in row {rid}"
            )

    def test_05_anti_falsification_no_unbacked_human_verified(self):
        """
        5. CRITICAL: Prevent falsification of expert sign-offs.
        All baseline rows must remain human_verified: FALSE, UNVERIFIED_BASELINE,
        with empty reviewer_role and reviewed_at until formal expert adjudication.
        """
        for row in self.dict_rows:
            rid = row["requirement_id"]
            hv = row.get("human_verified", "").upper()
            status = row.get("adjudication_status", "")
            role = row.get("reviewer_role", "").strip()
            date = row.get("reviewed_at", "").strip()

            self.assertEqual(
                hv, "FALSE",
                f"Falsification error: Row {rid} claims human_verified: TRUE without panel review!"
            )
            self.assertEqual(
                status, "UNVERIFIED_BASELINE",
                f"Baseline row {rid} must have adjudication_status 'UNVERIFIED_BASELINE'"
            )
            self.assertEqual(
                role, "",
                f"Baseline row {rid} has non-empty reviewer_role '{role}' without genuine review!"
            )
            self.assertEqual(
                date, "",
                f"Baseline row {rid} has non-empty reviewed_at '{date}' without genuine review!"
            )

    def test_06_provisional_sector_tagging(self):
        """6. Inferred sectors must be marked PROVISIONAL: to distinguish from certified taxonomy."""
        for row in self.dict_rows:
            rid = row["requirement_id"]
            sector = row.get("procurement_sector", "")
            self.assertTrue(
                sector.startswith("PROVISIONAL:"),
                f"Sector in row {rid} must be prefixed with 'PROVISIONAL:', got '{sector}'"
            )

    def test_07_source_document_defensibility(self):
        """7. Verify each linked source document exists on disk and contains the requirement text."""
        for row in self.dict_rows:
            rid = row["requirement_id"]
            tid = row["tender_id"]
            doc_rel = row.get("source_document", "")
            req_text = normalize_whitespace(row.get("requirement_text", "")).lower()

            self.assertFalse(
                doc_rel.startswith("UNRESOLVED:"),
                f"Row {rid} has unresolved source document: {doc_rel}"
            )

            doc_abs = os.path.join(REPO_ROOT, doc_rel)
            self.assertTrue(
                os.path.isfile(doc_abs),
                f"Linked document for {rid} does not exist: {doc_abs}"
            )
            self.assertGreater(
                os.path.getsize(doc_abs), 0,
                f"Linked document for {rid} is empty: {doc_abs}"
            )

            # Verify text match in extraction pages
            ext_path = os.path.join(EXTRACTION_RESULTS_DIR, f"{tid}.json")
            self.assertTrue(
                os.path.isfile(ext_path),
                f"Extraction result missing for {tid}"
            )

            with open(ext_path, "r", encoding="utf-8") as ef:
                edata = json.load(ef)
                all_text = " ".join(
                    normalize_whitespace(p.get("text", "")).lower()
                    for p in edata.get("pages", [])
                )
                self.assertIn(
                    req_text, all_text,
                    f"Requirement text for {rid} not found verbatim in extracted pages of {doc_rel}"
                )

    def test_08_compatibility_with_pandas_and_dictreader(self):
        """8. Verify seamless backwards compatibility with pandas and dict readers."""
        df = pd.read_csv(GT_PATH)
        self.assertEqual(len(df), 20)
        self.assertEqual(len(df.columns), 24)

        # Legacy consumers querying core fields must encounter no missing columns
        for col in CORE_18_COLUMNS:
            self.assertIn(col, df.columns)

        # Check that legacy non-null fields have no NaN
        self.assertEqual(df["requirement_id"].isna().sum(), 0)
        self.assertEqual(df["requirement_text"].isna().sum(), 0)


if __name__ == "__main__":
    unittest.main()
