"""
Module: tests/test_bis_acquisition.py
Purpose: Unit tests for Phase 1 BIS Catalogue Acquisition layer.

Covers:
- Base64 query parameter encoding ('seachby', 'txt_search')
- Session initialization and cookie acquisition
- Request construction (URL, headers, POST body: draw, start, length)
- Response parsing (iTotalRecords, aaData)
- Multi-page pagination and termination logic
- Deduplication across seeds and within seeds
- Malformed row detection and rejection without inventing identities
- Retry logic on transient HTTP failures
- Unrecoverable error handling and seed failure isolation
- Run audit summary generation (JSON and TXT)
- Guarantee of zero side-effects on production catalogue
"""

import base64
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from src.catalogue.bis_client import (
    BISClient,
    BISClientConfig,
    BISPageResult,
    BISRequestError,
    BISSessionError,
)
from src.catalogue.bis_fetcher import (
    BISCatalogueFetcher,
    RawRecordValidator,
    SeedStat,
)


class TestBISAcquisition(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = BISClientConfig(
            page_size=10,
            delay_sec=0.0,  # zero delay in unit tests
            timeout_sec=5.0,
            max_retries=2,
            backoff_factor=1.0,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Base64 Encoding Tests
    # -------------------------------------------------------------------------
    def test_base64_param_encoding(self):
        """Verifies correct Base64 encoding required by the BIS backend."""
        self.assertEqual(BISClient.encode_param("isnumber"), "aXNudW1iZXI=")
        self.assertEqual(BISClient.encode_param("0"), "MA==")
        self.assertEqual(BISClient.encode_param("1"), "MQ==")
        self.assertEqual(BISClient.encode_param("7"), "Nw==")
        self.assertEqual(BISClient.encode_param(""), "")
        self.assertEqual(BISClient.encode_param(None), "")

        # Test decoding equivalence
        val = "778"
        encoded = BISClient.encode_param(val)
        decoded = base64.b64decode(encoded.encode("ascii")).decode("utf-8")
        self.assertEqual(decoded, val)

    # -------------------------------------------------------------------------
    # 2. Session Initialization Tests
    # -------------------------------------------------------------------------
    def test_session_cookie_initialization_success(self):
        """Verifies session landing page request acquires BISID cookie."""
        mock_session = MagicMock(spec=requests.Session())
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        # Mock cookie jar
        mock_jar = MagicMock()
        mock_cookie = MagicMock()
        mock_cookie.name = "BISID"
        mock_cookie.value = "abc123bisid"
        mock_jar.__iter__.return_value = [mock_cookie]
        mock_jar.get.return_value = "abc123bisid"
        mock_session.cookies = mock_jar

        client = BISClient(config=self.config, session=mock_session)
        bisid = client.initialize_session()

        self.assertEqual(bisid, "abc123bisid")
        mock_session.get.assert_called_once_with(self.config.session_url, timeout=self.config.timeout_sec)

    def test_session_cookie_initialization_failure(self):
        """Verifies failure on session landing page raises BISSessionError."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.get.side_effect = requests.RequestException("Connection refused")

        client = BISClient(config=self.config, session=mock_session)
        with self.assertRaises(BISSessionError):
            client.initialize_session()

    # -------------------------------------------------------------------------
    # 3. Request Construction & Headers Tests
    # -------------------------------------------------------------------------
    def test_search_request_construction(self):
        """Verifies correct endpoint URL, query params, POST body, and headers."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "dummy_cookie"

        # Mock session landing page and POST response
        mock_landing = MagicMock()
        mock_landing.status_code = 200
        mock_session.get.return_value = mock_landing

        mock_post = MagicMock()
        mock_post.status_code = 200
        mock_post.json.return_value = {
            "draw": "1",
            "iTotalRecords": 10,
            "iTotalDisplayRecords": 10,
            "aaData": [
                {"id": 1, "is_no": "IS 10778:1983", "is_title": "Test Title"}
            ]
        }
        mock_session.post.return_value = mock_post

        client = BISClient(config=self.config, session=mock_session)
        result = client.fetch_page(seed="7", start=0, length=10, draw=1)

        # Verify POST URL contains 'seachby' and 'txt_search' with base64 values
        expected_seachby = BISClient.encode_param("isnumber")
        expected_txt = BISClient.encode_param("7")
        expected_url = f"{self.config.search_url}?seachby={expected_seachby}&txt_search={expected_txt}"

        mock_session.post.assert_called_once_with(
            expected_url,
            data={"draw": "1", "start": "0", "length": "10"},
            timeout=self.config.timeout_sec
        )
        self.assertEqual(result.total_records, 10)
        self.assertEqual(len(result.rows), 1)

    # -------------------------------------------------------------------------
    # 4. Response Parsing Tests
    # -------------------------------------------------------------------------
    def test_response_parsing(self):
        """Verifies extraction of DataTables response fields."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "dummy"
        mock_session.get.return_value = MagicMock(status_code=200)

        raw_payload = {
            "draw": "2",
            "iTotalRecords": 150,
            "iTotalDisplayRecords": 150,
            "aaData": [
                {
                    "id": 1,
                    "is_no": "IS 1554 (Part 1):1988<br>IEC 60502<br> (Active)",
                    "is_title": "PVC Insulated Cables",
                    "amendments": "2",
                    "technical_committee": "ETD 9",
                    "aspect": None,
                    "referirmatin_year": "Identical",
                    "withdrawn_status": "A"
                }
            ]
        }
        mock_post = MagicMock(status_code=200)
        mock_post.json.return_value = raw_payload
        mock_session.post.return_value = mock_post

        client = BISClient(config=self.config, session=mock_session)
        res = client.fetch_page(seed="0", start=0, length=10, draw=2)

        self.assertEqual(res.draw, 2)
        self.assertEqual(res.total_records, 150)
        self.assertEqual(res.total_display_records, 150)
        self.assertEqual(len(res.rows), 1)
        self.assertIn("is_no", res.rows[0])
        self.assertIn("referirmatin_year", res.rows[0])

    # -------------------------------------------------------------------------
    # 5. Pagination & Loop Termination Tests
    # -------------------------------------------------------------------------
    def test_pagination_and_termination(self):
        """Verifies fetcher loops through all pages until iTotalRecords is reached."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "cookie"
        mock_session.get.return_value = MagicMock(status_code=200)

        # Simulate 2 pages for total 5 records (page 1: 3 rows, page 2: 2 rows)
        def mock_post_impl(url, data, timeout):
            start = int(data["start"])
            m = MagicMock(status_code=200)
            if start == 0:
                m.json.return_value = {
                    "draw": data["draw"],
                    "iTotalRecords": 5,
                    "aaData": [
                        {"is_no": "IS 101:1980", "is_title": "P1"},
                        {"is_no": "IS 102:1980", "is_title": "P2"},
                        {"is_no": "IS 103:1980", "is_title": "P3"},
                    ]
                }
            else:
                m.json.return_value = {
                    "draw": data["draw"],
                    "iTotalRecords": 5,
                    "aaData": [
                        {"is_no": "IS 104:1980", "is_title": "P4"},
                        {"is_no": "IS 105:1980", "is_title": "P5"},
                    ]
                }
            return m

        mock_session.post.side_effect = mock_post_impl

        client = BISClient(config=BISClientConfig(page_size=3, delay_sec=0.0), session=mock_session)
        fetcher = BISCatalogueFetcher(client=client, output_base_dir=self.temp_dir, page_size=3, delay_sec=0.0)

        summary = fetcher.run_acquisition(seeds=["1"])

        self.assertEqual(summary.status, "SUCCESS")
        self.assertEqual(summary.total_raw_rows, 5)
        self.assertEqual(summary.total_unique_rows, 5)
        self.assertEqual(summary.seed_stats["1"]["pages_fetched"], 2)
        self.assertEqual(mock_session.post.call_count, 2)

    # -------------------------------------------------------------------------
    # 6. Deduplication Tests
    # -------------------------------------------------------------------------
    def test_deduplication_across_seeds(self):
        """Verifies duplicates across different seeds are detected and counted accurately."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "cookie"
        mock_session.get.return_value = MagicMock(status_code=200)

        # Seed '0' returns IS 101, IS 201
        # Seed '1' returns IS 101 (duplicate!), IS 311
        def mock_post_impl(url, data, timeout):
            m = MagicMock(status_code=200)
            if "MA==" in url:  # seed '0'
                m.json.return_value = {
                    "draw": data["draw"],
                    "iTotalRecords": 2,
                    "aaData": [
                        {"is_no": "IS 101:1980", "is_title": "Title 101"},
                        {"is_no": "IS 201:1980", "is_title": "Title 201"},
                    ]
                }
            else:  # seed '1'
                m.json.return_value = {
                    "draw": data["draw"],
                    "iTotalRecords": 2,
                    "aaData": [
                        {"is_no": "IS 101:1980", "is_title": "Title 101"},  # duplicate
                        {"is_no": "IS 311:1980", "is_title": "Title 311"},
                    ]
                }
            return m

        mock_session.post.side_effect = mock_post_impl

        client = BISClient(config=BISClientConfig(page_size=10, delay_sec=0.0), session=mock_session)
        fetcher = BISCatalogueFetcher(client=client, output_base_dir=self.temp_dir, page_size=10, delay_sec=0.0)

        summary = fetcher.run_acquisition(seeds=["0", "1"])

        self.assertEqual(summary.total_raw_rows, 4)
        self.assertEqual(summary.total_unique_rows, 3)
        self.assertEqual(summary.total_duplicates, 1)
        self.assertEqual(summary.seed_stats["0"]["unique_rows"], 2)
        self.assertEqual(summary.seed_stats["1"]["unique_rows"], 1)
        self.assertEqual(summary.seed_stats["1"]["duplicate_rows"], 1)

    # -------------------------------------------------------------------------
    # 7. Basic Validation & Rejection Tests
    # -------------------------------------------------------------------------
    def test_raw_record_validation_and_rejection(self):
        """Verifies corrupt rows or rows with missing identities are rejected and logged."""
        # 1. Valid rows
        valid1 = {"is_no": "IS 1554 (Part 1):1988<br>IEC 60502<br> (Active)", "is_title": "Valid"}
        ok1, id1, reason1 = RawRecordValidator.validate_raw_row(valid1)
        self.assertTrue(ok1)
        self.assertEqual(id1, "IS 1554 (PART 1):1988")
        self.assertIsNone(reason1)

        valid2 = {"is_no": "IS/IEC 61439 (Part 1):2011", "is_title": "Switchgear"}
        ok2, id2, reason2 = RawRecordValidator.validate_raw_row(valid2)
        self.assertTrue(ok2)
        self.assertEqual(id2, "IS/IEC 61439 (PART 1):2011")

        valid3 = {"is_no": "IS/ISO/IEC 24751 (Part 1):2008<br> (Active)", "is_title": "E-learning"}
        ok3, id3, reason3 = RawRecordValidator.validate_raw_row(valid3)
        self.assertTrue(ok3)
        self.assertEqual(id3, "IS/ISO/IEC 24751 (PART 1):2008")

        # 2. Corrupt source rows (missing number, e.g. "IS  (Part 1/Sec 1):1975")
        corrupt1 = {"is_no": "IS  (Part 1/Sec 1):1975", "is_title": "Missing number"}
        ok_c1, id_c1, r_c1 = RawRecordValidator.validate_raw_row(corrupt1)
        self.assertFalse(ok_c1)
        self.assertIn("Corrupt", r_c1)

        corrupt2 = {"is_no": "IS/IEC -1-310:2005", "is_title": "Malformed"}
        ok_c2, id_c2, r_c2 = RawRecordValidator.validate_raw_row(corrupt2)
        self.assertFalse(ok_c2)

        # 3. Missing or empty is_no
        empty_row = {"is_title": "No standard number"}
        ok_e, _, r_e = RawRecordValidator.validate_raw_row(empty_row)
        self.assertFalse(ok_e)
        self.assertIn("Missing", r_e)

        # 4. Non-dictionary row
        non_dict = "Just a string"
        ok_nd, _, r_nd = RawRecordValidator.validate_raw_row(non_dict)
        self.assertFalse(ok_nd)

    # -------------------------------------------------------------------------
    # 8. Retry & Failure Handling Tests
    # -------------------------------------------------------------------------
    def test_retry_on_transient_http_error(self):
        """Verifies retry with recovery on transient HTTP 500 / 503."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "cookie"
        mock_session.get.return_value = MagicMock(status_code=200)

        # First call fails with 500, second call succeeds with 200
        fail_resp = MagicMock(status_code=500, text="Internal Server Error")
        success_resp = MagicMock(status_code=200)
        success_resp.json.return_value = {
            "draw": "1",
            "iTotalRecords": 1,
            "aaData": [{"is_no": "IS 456:2000", "is_title": "Concrete"}]
        }
        mock_session.post.side_effect = [fail_resp, success_resp]

        client = BISClient(config=BISClientConfig(page_size=10, delay_sec=0.0, max_retries=2), session=mock_session)
        res = client.fetch_page(seed="4", start=0, length=10)

        self.assertEqual(res.total_records, 1)
        self.assertEqual(len(res.rows), 1)
        self.assertEqual(mock_session.post.call_count, 2)

    def test_seed_failure_isolation(self):
        """Verifies that if one seed permanently fails, other seeds continue and run status is PARTIAL."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "cookie"
        mock_session.get.return_value = MagicMock(status_code=200)

        def mock_post_impl(url, data, timeout):
            if "MA==" in url:  # seed '0' fails permanently
                raise requests.RequestException("Gateway Timeout")
            # seed '1' succeeds
            m = MagicMock(status_code=200)
            m.json.return_value = {
                "draw": data["draw"],
                "iTotalRecords": 1,
                "aaData": [{"is_no": "IS 101:1980", "is_title": "P1"}]
            }
            return m

        mock_session.post.side_effect = mock_post_impl

        client = BISClient(config=BISClientConfig(page_size=10, delay_sec=0.0, max_retries=1), session=mock_session)
        fetcher = BISCatalogueFetcher(client=client, output_base_dir=self.temp_dir, page_size=10, delay_sec=0.0)

        summary = fetcher.run_acquisition(seeds=["0", "1"])

        self.assertEqual(summary.status, "PARTIAL")
        self.assertIn("0", summary.failed_seeds)
        self.assertNotIn("1", summary.failed_seeds)
        self.assertEqual(summary.total_unique_rows, 1)

    # -------------------------------------------------------------------------
    # 9. Summary & File Artifact Tests
    # -------------------------------------------------------------------------
    def test_summary_and_file_artifacts_created(self):
        """Verifies raw pages, raw_records.jsonl, run_summary.json, and run_summary.txt are written."""
        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "cookie"
        mock_session.get.return_value = MagicMock(status_code=200)

        m = MagicMock(status_code=200)
        m.json.return_value = {
            "draw": "1",
            "iTotalRecords": 1,
            "aaData": [{"is_no": "IS 778:1984", "is_title": "Valves"}]
        }
        mock_session.post.return_value = m

        client = BISClient(config=BISClientConfig(page_size=10, delay_sec=0.0), session=mock_session)
        fetcher = BISCatalogueFetcher(client=client, output_base_dir=self.temp_dir, page_size=10, delay_sec=0.0)

        summary = fetcher.run_acquisition(seeds=["7"])

        run_dir = summary.output_dir
        self.assertTrue(os.path.isdir(run_dir))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "run_summary.json")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "run_summary.txt")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "run_metadata.json")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "raw_records.jsonl")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "pages", "seed_7_page_0000.json")))

        # Check content of run_summary.json
        with open(os.path.join(run_dir, "run_summary.json"), "r") as f:
            data = json.load(f)
            self.assertEqual(data["total_unique_rows"], 1)
            self.assertEqual(data["status"], "SUCCESS")

    # -------------------------------------------------------------------------
    # 10. Production DB Isolation Test
    # -------------------------------------------------------------------------
    def test_production_db_remains_untouched(self):
        """Guarantees Phase 1 acquisition never writes to or alters production database files."""
        prod_db_path = "data/catalogue/catalogue.db"
        self.assertTrue(os.path.exists(prod_db_path))
        mtime_before = os.path.getmtime(prod_db_path)
        size_before = os.path.getsize(prod_db_path)

        mock_session = MagicMock(spec=requests.Session())
        mock_session.cookies.get.return_value = "cookie"
        mock_session.get.return_value = MagicMock(status_code=200)

        m = MagicMock(status_code=200)
        m.json.return_value = {
            "draw": "1",
            "iTotalRecords": 1,
            "aaData": [{"is_no": "IS 999:2020", "is_title": "Isolated Test"}]
        }
        mock_session.post.return_value = m

        client = BISClient(config=BISClientConfig(page_size=10, delay_sec=0.0), session=mock_session)
        fetcher = BISCatalogueFetcher(client=client, output_base_dir=self.temp_dir, page_size=10, delay_sec=0.0)
        fetcher.run_acquisition(seeds=["9"])

        # Check DB unchanged
        mtime_after = os.path.getmtime(prod_db_path)
        size_after = os.path.getsize(prod_db_path)
        self.assertEqual(mtime_before, mtime_after)
        self.assertEqual(size_before, size_after)


if __name__ == "__main__":
    unittest.main()
