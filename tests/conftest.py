"""
tests/conftest.py

Pytest configuration and deterministic isolation fixtures for Tender Saathi test suite.
Guarantees 100% offline execution by:
1. Setting Hugging Face cache offline flags (HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1).
2. Blocking accidental outbound socket connections to external endpoints.
3. Providing reusable deterministic fixtures for LLM parsing and understanding.
4. Resetting shared in-memory caches between test sessions.
"""

import os
import json
import socket
from typing import Dict, Any, Optional
from unittest.mock import patch
import pytest

# Ensure offline operation for Hugging Face transformer models
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Prevent accidental leak of live API keys to unmocked provider calls
os.environ["TENDERSAATHI_TEST_MODE"] = "1"


# ---------------------------------------------------------------------------
# Network Isolation Guard
# ---------------------------------------------------------------------------

_ORIG_SOCKET_CONNECT = socket.socket.connect


def _guarded_socket_connect(self, address):
    host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
    # Allow local IPC / loopback connections
    if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
        return _ORIG_SOCKET_CONNECT(self, address)
    raise RuntimeError(
        f"External network connection to {address} was blocked. "
        "Automated tests must run deterministically offline without external API dependencies."
    )


@pytest.fixture(autouse=True, scope="session")
def enforce_network_isolation():
    """Session-level guard preventing accidental external socket connections."""
    socket.socket.connect = _guarded_socket_connect
    yield
    socket.socket.connect = _ORIG_SOCKET_CONNECT


# ---------------------------------------------------------------------------
# State Reset Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_test_state():
    """Resets shared in-memory caches and state between tests."""
    from src.ai_understanding import AIRequirementParser
    AIRequirementParser.clear_cache()
    yield
    AIRequirementParser.clear_cache()


# ---------------------------------------------------------------------------
# Reusable Deterministic LLM Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_groq_understanding():
    """
    Factory fixture providing a deterministic Groq LLM parsing mock for AIRequirementParser.
    Allows tests to supply custom facets or use standard realistic defaults.
    """
    def _create_mock(custom_facets: Optional[Dict[str, Any]] = None):
        default_facets = {
            "equipment": ["CPVC pipes"],
            "control": [],
            "electrical": [],
            "voltage": [],
            "application": ["potable water supply"],
            "work_type": ["supply", "installation"]
        }
        facets = custom_facets if custom_facets is not None else default_facets
        raw_json = json.dumps(facets)
        return patch("src.ai_understanding.AIRequirementParser._call_llm_api", return_value=raw_json)

    return _create_mock
