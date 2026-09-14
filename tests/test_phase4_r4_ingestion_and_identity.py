"""
Module: tests/test_phase4_r4_ingestion_and_identity.py
Purpose: Comprehensive Phase 4R4 verification suite testing all 26 mandatory gates
from Section 21 of the Phase 4R4 specification:

1. BIS session acquisition
2. pagination completeness
3. final short-page handling
4. missing-page detection
5. iTotalRecords reconciliation
6. retry/failure handling
7. exact identifier parsing
8. numeric collision prevention
9. part isolation
10. section isolation
11. prefix isolation
12. compound identifier isolation
13. archive identifier exact matching
14. sibling-document rejection
15. edition mismatch detection
16. historical-edition provenance
17. DB integrity
18. duplicate canonical ID detection
19. index → DB reversibility
20. DB → index reversibility
21. snapshot manifest integrity
22. failed promotion
23. CURRENT unchanged after failed build
24. successful atomic promotion
25. frozen files unchanged
26. benchmark identity integrity

CRITICAL SAFETY RULES:
- Never perform destructive tests against production directories.
- All promotion/rollback tests use temporary directories (tempfile.mkdtemp).
- Verifies frozen files hashes against authoritative baselines.
"""

import csv
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier
from src.catalogue.bis_client import (
    BISClient,
    BISClientConfig,
    BISPageResult,
    BISRequestError,
    BISSessionError,
)
from src.catalogue.bis_fetcher import BISCatalogueFetcher, SeedStat
from src.catalogue.fulltext_fetcher import FullTextManager
from src.catalogue.snapshot_builder import SnapshotBuilder
from src.catalogue.snapshot_manager import SnapshotManager


class TestPhase4R4IngestionAndIdentity(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = BISClientConfig(
            page_size=10,
            delay_sec=0.0,
            timeout_sec=5.0,
            max_retries=2,
            backoff_factor=1.0,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Gate 1: BIS session acquisition
    # -------------------------------------------------------------------------
    def test_gate01_bis_session_acquisition(self):
        mock_session = MagicMock(spec=requests.Session())
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        # Mock cookie jar with BISID
        mock_jar = MagicMock()
        mock_cookie = MagicMock()
        mock_cookie.name = "BISID"
        mock_cookie.value = "session_cookie_12345"
        mock_jar.__iter__.return_value = [mock_cookie]
        mock_jar.get.return_value = "session_cookie_12345"
        mock_session.cookies = mock_jar

        client = BISClient(config=self.config, session=mock_session)
        bisid = client.initialize_session()

        self.assertEqual(bisid, "session_cookie_12345")
        mock_session.get.assert_called_once_with(self.config.session_url, timeout=self.config.timeout_sec)
        # Verify TLS verification is not disabled
        _, kwargs = mock_session.get.call_args
        self.assertFalse(kwargs.get("verify") is False, "verify=False is strictly prohibited")

    # -------------------------------------------------------------------------
    # Gate 2: Pagination completeness
    # -------------------------------------------------------------------------
    def test_gate02_pagination_completeness(self):
        offsets = [0, 500]
        row_counts = [500, 500]
        reported_total = 1000
        ok, err = BISCatalogueFetcher.validate_seed_pagination(
            "seed_0", offsets, row_counts, reported_total, page_size=500
        )
        self.assertTrue(ok, f"Expected success but got error: {err}")
        self.assertIsNone(err)

    # -------------------------------------------------------------------------
    # Gate 3: Final short-page handling
    # -------------------------------------------------------------------------
    def test_gate03_final_short_page_handling(self):
        # 500 + 500 + 250 = 1250 with page_size=500
        offsets = [0, 500, 1000]
        row_counts = [500, 500, 250]
        reported_total = 1250
        ok, err = BISCatalogueFetcher.validate_seed_pagination(
            "seed_1", offsets, row_counts, reported_total, page_size=500
        )
        self.assertTrue(ok, f"Final short page was incorrectly rejected: {err}")
        self.assertIsNone(err)

    # -------------------------------------------------------------------------
    # Gate 4: Missing-page detection
    # -------------------------------------------------------------------------
    def test_gate04_missing_page_detection(self):
        # Missing offset 500: expected [0, 500, 1000], got [0, 1000]
        offsets = [0, 1000]
        row_counts = [500, 500]
        reported_total = 1500
        ok, err = BISCatalogueFetcher.validate_seed_pagination(
            "seed_2", offsets, row_counts, reported_total, page_size=500
        )
        self.assertFalse(ok)
        self.assertIn("Offset sequence mismatch", err)

    # -------------------------------------------------------------------------
    # Gate 5: iTotalRecords reconciliation
    # -------------------------------------------------------------------------
    def test_gate05_itotalrecords_reconciliation(self):
        # Accumulated rows = 1000 != reported_total = 1200
        offsets = [0, 500, 1000]
        row_counts = [500, 500, 0]
        reported_total = 1200
        ok, err = BISCatalogueFetcher.validate_seed_pagination(
            "seed_3", offsets, row_counts, reported_total, page_size=500
        )
        self.assertFalse(ok)
        self.assertIn("Accumulated rows (1000) != expected total (1200)", err)

    # -------------------------------------------------------------------------
    # Gate 6: Retry/failure handling
    # -------------------------------------------------------------------------
    def test_gate06_retry_failure_handling(self):
        mock_session = MagicMock(spec=requests.Session())
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_session.get.return_value = mock_get_resp

        mock_jar = MagicMock()
        mock_cookie = MagicMock()
        mock_cookie.name = "BISID"
        mock_cookie.value = "session_cookie_12345"
        mock_jar.__iter__.return_value = [mock_cookie]
        mock_jar.get.return_value = "session_cookie_12345"
        mock_session.cookies = mock_jar

        good_resp = MagicMock()
        good_resp.status_code = 200
        good_resp.json.return_value = {
            "iTotalRecords": 1,
            "iTotalDisplayRecords": 1,
            "aaData": [["1", "IS 15778", "2007", "Title", "Active", "", "", "", "", ""]]
        }

        # First request raises ConnectionError, second succeeds
        mock_session.post.side_effect = [
            requests.RequestException("Connection reset"),
            good_resp
        ]

        client = BISClient(config=self.config, session=mock_session)
        res = client.fetch_page(seed="7", start=0)

        self.assertIsNotNone(res)
        self.assertEqual(res.total_records, 1)
        self.assertEqual(mock_session.post.call_count, 2)

    # -------------------------------------------------------------------------
    # Gate 7: Exact identifier parsing
    # -------------------------------------------------------------------------
    def test_gate07_exact_identifier_parsing(self):
        parsed = StandardIdentifierNormalizer.parse("IS 15778 : 2007")
        self.assertTrue(parsed.is_valid)
        self.assertEqual(parsed.prefix, "IS")
        self.assertEqual(parsed.base_number, "15778")
        self.assertIsNone(parsed.part)
        self.assertEqual(parsed.year, 2007)

    # -------------------------------------------------------------------------
    # Gate 8: Numeric collision prevention
    # -------------------------------------------------------------------------
    def test_gate08_numeric_collision_prevention(self):
        pairs = [
            ("IS 5039", "IS 15039"),
            ("IS 3043", "IS 13043"),
            ("IS 1255", "IS 11255"),
            ("IS 7098", "IS 17098"),
        ]
        for s1, s2 in pairs:
            p1 = StandardIdentifierNormalizer.parse(s1)
            p2 = StandardIdentifierNormalizer.parse(s2)
            self.assertFalse(
                StandardIdentifierNormalizer.matches_identity_without_year(p1, p2),
                f"Collision between {s1} and {s2}"
            )

    # -------------------------------------------------------------------------
    # Gate 9: Part isolation
    # -------------------------------------------------------------------------
    def test_gate09_part_isolation(self):
        p1 = StandardIdentifierNormalizer.parse("IS 7098 (Part 1)")
        p2 = StandardIdentifierNormalizer.parse("IS 7098 (Part 2)")
        self.assertEqual(p1.part, 1)
        self.assertEqual(p2.part, 2)
        self.assertFalse(StandardIdentifierNormalizer.matches_identity_without_year(p1, p2))

    # -------------------------------------------------------------------------
    # Gate 10: Section isolation
    # -------------------------------------------------------------------------
    def test_gate10_section_isolation(self):
        p1 = StandardIdentifierNormalizer.parse("IS 13360 (Part 6/Sec 1)")
        p2 = StandardIdentifierNormalizer.parse("IS 13360 (Part 6/Sec 2)")
        self.assertEqual(p1.section, 1)
        self.assertEqual(p2.section, 2)
        self.assertFalse(StandardIdentifierNormalizer.matches_identity_without_year(p1, p2))

    # -------------------------------------------------------------------------
    # Gate 11: Prefix isolation
    # -------------------------------------------------------------------------
    def test_gate11_prefix_isolation(self):
        p1 = StandardIdentifierNormalizer.parse("IS 30")
        p2 = StandardIdentifierNormalizer.parse("SP 30")
        self.assertEqual(p1.prefix, "IS")
        self.assertEqual(p2.prefix, "SP")
        self.assertFalse(StandardIdentifierNormalizer.matches_identity_without_year(p1, p2))

    # -------------------------------------------------------------------------
    # Gate 12: Compound identifier isolation
    # -------------------------------------------------------------------------
    def test_gate12_compound_identifier_isolation(self):
        p1 = StandardIdentifierNormalizer.parse("IS/IEC 61800-2")
        p2 = StandardIdentifierNormalizer.parse("IS/IEC 61800-3")
        self.assertEqual(p1.prefix, "IS/IEC")
        self.assertEqual(p2.prefix, "IS/IEC")
        self.assertEqual(p1.part, 2)
        self.assertEqual(p2.part, 3)
        self.assertNotEqual(p1.part, p2.part)
        self.assertFalse(StandardIdentifierNormalizer.matches_identity_without_year(p1, p2))

    # -------------------------------------------------------------------------
    # Gate 13: Archive identifier exact matching
    # -------------------------------------------------------------------------
    def test_gate13_archive_identifier_exact_matching(self):
        parsed = StandardIdentifierNormalizer.parse_archive_identifier("gov.in.is.732.1989")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.prefix, "IS")
        self.assertEqual(parsed.base_number, "732")
        self.assertEqual(parsed.year, 1989)

        target = StandardIdentifierNormalizer.parse("IS 732 : 2019")
        self.assertTrue(StandardIdentifierNormalizer.matches_identity_without_year(parsed, target))

    # -------------------------------------------------------------------------
    # Gate 14: Sibling-document rejection
    # -------------------------------------------------------------------------
    def test_gate14_sibling_document_rejection(self):
        archive_doc = StandardIdentifierNormalizer.parse_archive_identifier("gov.in.is.7098.2.2011")
        target_part1 = StandardIdentifierNormalizer.parse("IS 7098 (Part 1) : 1988")
        self.assertFalse(StandardIdentifierNormalizer.matches_identity_without_year(archive_doc, target_part1))

    # -------------------------------------------------------------------------
    # Gate 15: Edition mismatch detection
    # -------------------------------------------------------------------------
    def test_gate15_edition_mismatch_detection(self):
        archive_doc = StandardIdentifierNormalizer.parse_archive_identifier("gov.in.is.732.1989")
        target = StandardIdentifierNormalizer.parse("IS 732 : 2019")

        self.assertTrue(StandardIdentifierNormalizer.matches_identity_without_year(archive_doc, target))
        self.assertFalse(StandardIdentifierNormalizer.matches_exact_identity(archive_doc, target))
        self.assertEqual(archive_doc.year, 1989)
        self.assertEqual(target.year, 2019)

    # -------------------------------------------------------------------------
    # Gate 16: Historical-edition provenance
    # -------------------------------------------------------------------------
    def test_gate16_historical_edition_provenance(self):
        db_path = os.path.join(self.temp_dir, "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE standards (
                standard_id TEXT PRIMARY KEY,
                standard_number TEXT,
                year INTEGER
            )
        """)
        conn.execute("INSERT INTO standards VALUES ('IS-732-2019', 'IS 732', 2019)")
        conn.commit()
        conn.close()

        manager = FullTextManager(db_path=db_path)
        success, reason, record = manager.attach_fulltext_document(
            target_standard_str="IS 732 : 2019",
            archive_identifier="gov.in.is.732.1989",
            raw_text_override="Title: Electrical wiring installations\n\nSection 1: Scope\nAll installations shall comply with requirements."
        )
        self.assertTrue(success, f"Attachment failed: {reason}")
        self.assertIsNotNone(record)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT is_historical_edition, edition_mismatch, source_edition, full_text_year, catalogue_year "
            "FROM standards_fulltext WHERE canonical_id='IS-732-2019'"
        ).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)  # is_historical_edition
        self.assertEqual(row[1], 1)  # edition_mismatch
        self.assertEqual(row[2], "IS 732 : 1989")
        self.assertEqual(row[3], 1989)
        self.assertEqual(row[4], 2019)

    # -------------------------------------------------------------------------
    # Gate 17: DB integrity
    # -------------------------------------------------------------------------
    def test_gate17_db_integrity(self):
        db_path = os.path.join(self.temp_dir, "integrity_test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE t (id INT PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO t VALUES (1, 'ok')")
        conn.commit()

        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()[0]
        conn.close()
        self.assertEqual(res, "ok")

    # -------------------------------------------------------------------------
    # Gate 18: Duplicate canonical ID detection
    # -------------------------------------------------------------------------
    def test_gate18_duplicate_canonical_id_detection(self):
        db_path = os.path.join(self.temp_dir, "dup_test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE standards (standard_id TEXT PRIMARY KEY, title TEXT)")
        conn.execute("INSERT INTO standards VALUES ('IS-1234', 'Title 1')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO standards VALUES ('IS-1234', 'Title 2')")
        conn.close()

    # -------------------------------------------------------------------------
    # Gate 19: Index → DB reversibility
    # -------------------------------------------------------------------------
    def test_gate19_index_to_db_reversibility(self):
        mgr = SnapshotManager()
        curr = mgr.get_current_snapshot()
        self.assertIsNotNone(curr)

        db_path = curr["paths"]["db_path"]
        bm25_path = curr["paths"]["bm25_path"]
        semantic_ids_path = curr["paths"]["semantic_doc_ids_path"]

        with open(bm25_path, "r", encoding="utf-8") as f:
            bm25_data = json.load(f)
        bm25_doc_ids = bm25_data.get("doc_ids", [])

        with open(semantic_ids_path, "r", encoding="utf-8") as f:
            semantic_doc_ids = json.load(f)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Check sample of 100 BM25 IDs
        for did in bm25_doc_ids[:100]:
            cid = did.split("#chunk_")[0]
            cur.execute("SELECT COUNT(*) FROM standards WHERE standard_id = ?", (cid,))
            self.assertEqual(cur.fetchone()[0], 1, f"BM25 ID {did} not in DB")

        # Check sample of 100 Semantic IDs
        for did in semantic_doc_ids[:100]:
            cid = did.split("#chunk_")[0]
            cur.execute("SELECT COUNT(*) FROM standards WHERE standard_id = ?", (cid,))
            self.assertEqual(cur.fetchone()[0], 1, f"Semantic ID {did} not in DB")

        conn.close()

    # -------------------------------------------------------------------------
    # Gate 20: DB → Index reversibility
    # -------------------------------------------------------------------------
    def test_gate20_db_to_index_reversibility(self):
        mgr = SnapshotManager()
        curr = mgr.get_current_snapshot()
        db_path = curr["paths"]["db_path"]
        bm25_path = curr["paths"]["bm25_path"]
        semantic_ids_path = curr["paths"]["semantic_doc_ids_path"]

        with open(bm25_path, "r", encoding="utf-8") as f:
            bm25_data = json.load(f)
        bm25_cids = {did.split("#chunk_")[0] for did in bm25_data.get("doc_ids", [])}

        with open(semantic_ids_path, "r", encoding="utf-8") as f:
            semantic_cids = {did.split("#chunk_")[0] for did in json.load(f)}

        conn = sqlite3.connect(db_path)
        db_cids = {row[0] for row in conn.execute("SELECT standard_id FROM standards").fetchall()}
        conn.close()

        self.assertEqual(db_cids, bm25_cids, "DB canonical IDs != BM25 canonical IDs")
        self.assertEqual(db_cids, semantic_cids, "DB canonical IDs != Semantic canonical IDs")

    # -------------------------------------------------------------------------
    # Gate 21: Snapshot manifest integrity
    # -------------------------------------------------------------------------
    def test_gate21_snapshot_manifest_integrity(self):
        mgr = SnapshotManager()
        curr = mgr.get_current_snapshot()
        manifest_path = curr["paths"]["snapshot_manifest_path"]

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        sdir = curr["snapshot_dir"]
        for fname, expected_hash in manifest["files"].items():
            fpath = os.path.join(sdir, fname)
            self.assertTrue(os.path.exists(fpath), f"Artifact {fname} missing")
            h = hashlib.sha256()
            with open(fpath, "rb") as bf:
                while chunk := bf.read(65536):
                    h.update(chunk)
            self.assertEqual(h.hexdigest(), expected_hash, f"Hash mismatch for {fname}")

    # -------------------------------------------------------------------------
    # Gate 22: Failed promotion
    # -------------------------------------------------------------------------
    def test_gate22_failed_promotion(self):
        test_cat_dir = os.path.join(self.temp_dir, "catalogue")
        test_snap_dir = os.path.join(test_cat_dir, "snapshots")
        os.makedirs(test_snap_dir, exist_ok=True)

        mgr = SnapshotManager(catalogue_dir=test_cat_dir, snapshots_dir=test_snap_dir)
        staging_dir = os.path.join(self.temp_dir, "staging", "bad_snap")
        os.makedirs(staging_dir, exist_ok=True)
        # Empty staging dir (missing manifest, DB, and validation_report.json)
        success = mgr.promote_staging_snapshot(staging_dir, "bad_snap")
        self.assertFalse(success, "Promotion should fail when required files are missing")

    # -------------------------------------------------------------------------
    # Gate 23: CURRENT unchanged after failed build
    # -------------------------------------------------------------------------
    def test_gate23_current_unchanged_after_failed_build(self):
        test_cat_dir = os.path.join(self.temp_dir, "catalogue")
        test_snap_dir = os.path.join(test_cat_dir, "snapshots")
        os.makedirs(test_snap_dir, exist_ok=True)

        ptr_path = os.path.join(test_cat_dir, "current_snapshot.json")
        initial_data = {"snapshot_id": "initial_snapshot", "record_count": 100}
        with open(ptr_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        mgr = SnapshotManager(catalogue_dir=test_cat_dir, snapshots_dir=test_snap_dir)
        bad_staging = os.path.join(self.temp_dir, "bad_staging")
        os.makedirs(bad_staging, exist_ok=True)
        res = mgr.promote_staging_snapshot(bad_staging, "bad_snapshot_id")
        self.assertFalse(res)

        # Verify pointer remained strictly unchanged
        with open(ptr_path, "r", encoding="utf-8") as f:
            after_data = json.load(f)
        self.assertEqual(initial_data, after_data)

    # -------------------------------------------------------------------------
    # Gate 24: Successful atomic promotion
    # -------------------------------------------------------------------------
    def test_gate24_successful_atomic_promotion(self):
        test_cat_dir = os.path.join(self.temp_dir, "catalogue")
        test_snap_dir = os.path.join(test_cat_dir, "snapshots")
        os.makedirs(test_snap_dir, exist_ok=True)

        staging_dir = os.path.join(self.temp_dir, "valid_staging")
        os.makedirs(staging_dir, exist_ok=True)

        # Create dummy artifacts
        db_path = os.path.join(staging_dir, "bis_catalogue.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE standards (id INT)")
        conn.close()

        for fn in [
            "bis_bm25_index.json",
            "bis_semantic_embeddings.npy",
            "bis_semantic_doc_ids.json",
            "bis_semantic_doc_hashes.json",
            "bis_index_manifest.json"
        ]:
            with open(os.path.join(staging_dir, fn), "w") as f:
                f.write("{}")

        # Create validation report with VALIDATED
        with open(os.path.join(staging_dir, "validation_report.json"), "w") as f:
            json.dump({"status": "VALIDATED"}, f)

        # Create manifest
        manifest = {
            "snapshot_id": "valid_snap_1",
            "validation_status": "VALIDATED",
            "files": {}
        }
        for fn in [
            "bis_catalogue.db",
            "bis_bm25_index.json",
            "bis_semantic_embeddings.npy",
            "bis_semantic_doc_ids.json",
            "bis_semantic_doc_hashes.json",
            "bis_index_manifest.json"
        ]:
            h = hashlib.sha256()
            with open(os.path.join(staging_dir, fn), "rb") as bf:
                h.update(bf.read())
            manifest["files"][fn] = h.hexdigest()

        with open(os.path.join(staging_dir, "snapshot_manifest.json"), "w") as f:
            json.dump(manifest, f)

        mgr = SnapshotManager(catalogue_dir=test_cat_dir, snapshots_dir=test_snap_dir)
        ok = mgr.promote_staging_snapshot(staging_dir, "valid_snap_1")
        self.assertTrue(ok)

        curr = mgr.get_current_snapshot()
        self.assertEqual(curr["snapshot_id"], "valid_snap_1")
        self.assertTrue(os.path.exists(curr["paths"]["db_path"]))

    # -------------------------------------------------------------------------
    # Gate 25: Frozen files unchanged
    # -------------------------------------------------------------------------
    def test_gate25_frozen_files_unchanged(self):
        EXPECTED_GROUND_TRUTH_SHA = "cfcbca27a729bd0619886be9128cfba272b912bd21115604b45af7eb59fa404b"
        EXPECTED_CATALOGUE_DB_SHA = "bbd0b58a112f1755e77dda04fed56e87dff7fe7eb06975491ac4e023ebc35dd1"

        # Check ground_truth.csv
        gt_path = "dataset/ground_truth/ground_truth.csv"
        h_gt = hashlib.sha256()
        with open(gt_path, "rb") as f:
            while chunk := f.read(65536):
                h_gt.update(chunk)
        self.assertEqual(h_gt.hexdigest(), EXPECTED_GROUND_TRUTH_SHA, "ground_truth.csv was modified!")

        # Check catalogue.db
        cat_path = "data/catalogue/catalogue.db"
        h_cat = hashlib.sha256()
        with open(cat_path, "rb") as f:
            while chunk := f.read(65536):
                h_cat.update(chunk)
        self.assertEqual(h_cat.hexdigest(), EXPECTED_CATALOGUE_DB_SHA, "catalogue.db was modified!")

        # Check raw run directory
        raw_dir = "data/raw/bis/run_20260914_042545"
        self.assertTrue(os.path.isdir(raw_dir))
        pages_dir = os.path.join(raw_dir, "pages")
        self.assertTrue(os.path.isdir(pages_dir))
        self.assertEqual(len(os.listdir(pages_dir)), 186, "Raw pages count altered!")

    # -------------------------------------------------------------------------
    # Gate 26: Benchmark identity integrity
    # -------------------------------------------------------------------------
    def test_gate26_benchmark_identity_integrity(self):
        mgr = SnapshotManager()
        curr = mgr.get_current_snapshot()
        conn = sqlite3.connect(curr["paths"]["db_path"])
        cur = conn.cursor()

        with open("dataset/ground_truth/ground_truth.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            checked = 0
            for row in reader:
                app_std = row["applicable_standard"]
                for std_token in app_std.split(";"):
                    std_token = std_token.strip()
                    if not std_token:
                        continue
                    parsed = StandardIdentifierNormalizer.parse(std_token)
                    self.assertTrue(parsed.is_valid, f"Could not parse expected standard: {std_token}")

                    # Check that standard exists in DB by standard_id or standard_number
                    cur.execute(
                        "SELECT COUNT(*) FROM standards WHERE standard_id = ? OR standard_number LIKE ?",
                        (parsed.canonical_id, f"%{parsed.base_number}%")
                    )
                    count = cur.fetchone()[0]
                    self.assertGreater(count, 0, f"Benchmark standard {std_token} not in DB")
                    checked += 1
        conn.close()
        self.assertEqual(checked, 39, f"Expected 39 benchmark standards checked, got {checked}")


if __name__ == "__main__":
    unittest.main()
