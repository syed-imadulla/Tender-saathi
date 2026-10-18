"""
tests/test_offline_isolation.py

Regression test suite verifying deterministic offline test guarantees (Phase 2A):
1. Confirms external network socket connections are strictly blocked by conftest.py.
2. Confirms Hugging Face Hub offline mode is active.
3. Confirms AI requirement understanding runs deterministically through mock fixtures.
4. Confirms that missing credentials trigger deterministic fallback without hanging or leaking.
"""

import os
import socket
import json
import unittest
from unittest.mock import patch
from api.server import app
from src.ai_understanding import AIRequirementParser


class TestOfflineIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_01_external_network_socket_blocked(self):
        """1. External network connections to non-loopback addresses must be blocked."""
        s = socket.socket()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                s.connect(("8.8.8.8", 80))
            self.assertIn("blocked", str(ctx.exception).lower())
        finally:
            s.close()

    def test_02_huggingface_offline_environment_enforced(self):
        """2. HF_HUB_OFFLINE and TRANSFORMERS_OFFLINE must be set to 1."""
        self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), "1")
        self.assertEqual(os.environ.get("TRANSFORMERS_OFFLINE"), "1")

    def test_03_deterministic_llm_fixture_without_credentials(self):
        """3. AI understanding runs through deterministic fixtures without real API credentials."""
        parser = AIRequirementParser(enabled=True, api_key="dummy_offline_key")
        mock_facets = {
            "equipment": ["Submersible Pump"],
            "control": ["Starter panel"],
            "electrical": ["415V 3-phase"],
            "voltage": ["415V"],
            "application": ["Agricultural water supply"],
            "work_type": ["supply", "commissioning"]
        }
        with patch.object(parser, "_call_llm_api", return_value=json.dumps(mock_facets)):
            res = parser.parse("Supply of 415V 3-phase submersible pump with starter panel")
            self.assertFalse(res.is_fallback)
            self.assertEqual(res.equipment, ["Submersible Pump"])
            self.assertEqual(res.voltage, ["415V"])

    def test_04_missing_credentials_graceful_fallback(self):
        """4. Missing credentials trigger deterministic offline fallback cleanly."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "", "TENDERSAATHI_LLM_ENABLED": "false"}):
            parser = AIRequirementParser()
            res = parser.parse("Procurement of CPVC pipes")
            self.assertTrue(res.is_fallback)
            self.assertEqual(res.ai_provider, "deterministic")
