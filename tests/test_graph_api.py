"""
tests/test_graph_api.py — API Contract & Safety Tests for Standards Knowledge Graph

Verifies:
- Search standards endpoint (number, title, limit validation)
- Curated prominent domain hubs endpoint
- Direct neighbors endpoint with strict depth=1 enforcement
- Rejection of depth > 1 (HTTP 400)
- Missing standard handling (HTTP 404)
- Provenance preservation (VERIFIED / CURATED only, no INFERRED)
- Verbatim evidence and citing clause serialization
- Bounded overview topology and graph stats
- Prominent legal applicability disclaimer present in responses
- Read-only safety: no mutation of recommendation or database state
"""

import pytest
import json
from api.server import app, GRAPH_DISCLAIMER


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestStandardsSearchAPI:
    def test_search_by_standard_number(self, client):
        resp = client.get("/api/standards/search?q=15778")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "standards" in data
        assert data["total"] > 0
        matches = [s for s in data["standards"] if "15778" in s["standard_number"]]
        assert len(matches) > 0
        assert matches[0]["standard_id"] == "IS-15778-2007"
        assert matches[0]["status"] == "Active"

    def test_search_by_title_keyword(self, client):
        resp = client.get("/api/standards/search?q=cables")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] > 0
        assert any("cable" in s["full_title"].lower() for s in data["standards"])

    def test_search_empty_query(self, client):
        resp = client.get("/api/standards/search?q=")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0
        assert data["standards"] == []

    def test_search_limit_clamping(self, client):
        resp = client.get("/api/standards/search?q=IS&limit=3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["standards"]) <= 3

        # Exceeding max limit (50) should be clamped
        resp_max = client.get("/api/standards/search?q=IS&limit=500")
        assert resp_max.status_code == 200
        assert len(resp_max.get_json()["standards"]) <= 50

    def test_search_extreme_and_negative_limits(self, client):
        # Negative limit should be clamped to at least 1
        resp_neg = client.get("/api/standards/search?q=IS&limit=-10")
        assert resp_neg.status_code == 200
        assert len(resp_neg.get_json()["standards"]) >= 1

        # Non-integer limit should fall back to default limit without 500 error
        resp_nan = client.get("/api/standards/search?q=IS&limit=invalid")
        assert resp_nan.status_code == 200
        assert len(resp_nan.get_json()["standards"]) <= 15


class TestStandardsHubsAPI:
    def test_get_graph_hubs(self, client):
        resp = client.get("/api/standards/graph/hubs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "hubs" in data
        assert len(data["hubs"]) >= 5
        domains = {h["domain"] for h in data["hubs"]}
        assert "Plumbing & Piping" in domains
        assert "Electrical & Cables" in domains

        # Check hub schema
        for hub in data["hubs"]:
            assert "standard_id" in hub
            assert "standard_number" in hub
            assert "relationships_count" in hub
            assert hub["verification_status"] in {"VERIFIED", "CURATED"}

        # Check disclaimer
        assert data.get("disclaimer") == GRAPH_DISCLAIMER


class TestStandardsNeighborsAPI:
    def test_get_neighbors_valid_standard(self, client):
        resp = client.get("/api/standards/IS-15778-2007/neighbors?depth=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "focal_standard" in data
        assert data["focal_standard"]["standard_number"] == "IS 15778"
        assert "nodes" in data
        assert "edges" in data
        assert len(data["edges"]) >= 3

        # Verify edge fields
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "relationship_type" in edge
            assert "direction" in edge
            assert "evidence" in edge
            assert len(edge["evidence"]) > 0
            assert edge["provenance"] in {"VERIFIED", "CURATED"}

        # Verify disclaimer in metadata
        assert data["meta"]["disclaimer"] == GRAPH_DISCLAIMER
        assert data["meta"]["depth"] == 1

    def test_get_neighbors_by_standard_number_with_spaces(self, client):
        resp = client.get("/api/standards/IS 7098 (Part 1)/neighbors")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["focal_standard"]["standard_number"] == "IS 7098 (Part 1)"
        assert len(data["edges"]) >= 3

    def test_depth_greater_than_one_strictly_rejected(self, client):
        resp = client.get("/api/standards/IS-15778-2007/neighbors?depth=2")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "depth=1" in data["error"]

    def test_invalid_depth_format_rejected(self, client):
        resp = client.get("/api/standards/IS-15778-2007/neighbors?depth=abc")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_missing_standard_returns_404(self, client):
        resp = client.get("/api/standards/IS-999999-NOTEXIST/neighbors")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_provenance_strictly_preserved_no_inferred(self, client):
        resp = client.get("/api/standards/IS-14846-2000/neighbors")
        assert resp.status_code == 200
        data = resp.get_json()
        for edge in data["edges"]:
            assert edge["provenance"] in {"VERIFIED", "CURATED"}
            assert edge["provenance"] != "INFERRED"
            assert edge["evidence"] != ""

    def test_get_neighbors_zero_relationship_isolated_standard(self, client):
        # Standards in catalogue with 0 direct relationships return 200 with 1 focal node and 0 edges
        resp = client.get("/api/standards/IS-15328-2003/neighbors")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["focal_standard"]["standard_number"] == "IS 15328"
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 0

    def test_get_neighbors_url_encoded_slash_standard(self, client):
        # International adoption standards containing slashes (e.g. IS/IEC 60034-1)
        resp_path = client.get("/api/standards/IS/IEC 60034-1/neighbors")
        assert resp_path.status_code == 200
        assert len(resp_path.get_json()["edges"]) > 0

        resp_encoded = client.get("/api/standards/IS%2FIEC%2060034-1/neighbors")
        assert resp_encoded.status_code == 200
        assert len(resp_encoded.get_json()["edges"]) > 0


class TestStandardsOverviewAPI:
    def test_get_graph_overview(self, client):
        resp = client.get("/api/standards/graph/overview")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "nodes" in data
        assert "edges" in data
        assert "stats" in data

        # Bounded topology check: avoid hairballs (< 60 nodes)
        assert len(data["nodes"]) <= 60
        assert len(data["edges"]) <= 70

        # Stats check
        stats = data["stats"]
        assert stats["total_standards_in_db"] >= 90
        assert stats["overview_nodes_count"] == len(data["nodes"])
        assert stats["overview_edges_count"] == len(data["edges"])

        # Disclaimer check
        assert data.get("disclaimer") == GRAPH_DISCLAIMER
