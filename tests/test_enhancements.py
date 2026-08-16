"""Tests for new API endpoints: /search, /corpora/{id}, /graph/stats,
/character/{id}/neighbors, enhanced /health.

Validated against all corpora (AGENTS.md §9).
"""

from __future__ import annotations

import pytest

from tests.conftest import CORPUS_FIXTURES


def test_health_returns_corpus_count_and_backend(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["corpus_count"] >= 2
    assert body["store_backend"] in ("networkx", "NetworkXGraphStore")


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_get_corpus_detail(client, corpus_id: str, fixture_name: str):
    """The /corpora/{id} endpoint returns full metadata including relation types."""
    r = client.get(f"/api/corpora/{corpus_id}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["id"] == corpus_id
    assert detail["name"]
    assert len(detail["relation_types"]) > 0
    assert detail["narrative_tone"]
    assert detail["narrative_length_seconds"] > 0
    assert detail["voice_provider"]
    assert detail["node_count"] >= 5


def test_get_corpus_detail_404(client):
    r = client.get("/api/corpora/no-such-corpus")
    assert r.status_code == 404


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_graph_stats(client, corpus_id: str, fixture_name: str):
    """The /graph/stats endpoint returns node-type and relation-type counts."""
    r = client.get("/api/graph/stats", params={"corpus_id": corpus_id})
    assert r.status_code == 200
    stats = r.json()
    assert stats["corpus_id"] == corpus_id
    assert stats["total_nodes"] >= 5
    assert stats["total_edges"] >= 3
    # node_type_counts should contain at least one known type
    assert any(
        k in ("Character", "Place", "Object", "Event", "Concept") for k in stats["node_type_counts"]
    )
    # The counts should sum to total_nodes
    assert sum(stats["node_type_counts"].values()) == stats["total_nodes"]
    assert sum(stats["relation_type_counts"].values()) == stats["total_edges"]


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_search_returns_matching_nodes(client, corpus_id: str, fixture_name: str):
    """The /search endpoint returns nodes matching the query."""
    # Search for a common letter that will appear in node labels.
    r = client.get("/api/search", params={"corpus_id": corpus_id, "q": "a", "limit": "5"})
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert len(results) > 0
    for result in results:
        assert "node" in result
        assert "score" in result
        assert result["node"]["corpus_id"] == corpus_id


def test_search_empty_query_rejected(client):
    """A search with an empty query returns 422 (Query min_length=1)."""
    r = client.get("/api/search", params={"corpus_id": "greek-odyssey", "q": "", "limit": "5"})
    assert r.status_code == 422


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_get_neighbors(client, corpus_id: str, fixture_name: str):
    """The /character/{id}/neighbors endpoint returns direct neighbors."""
    # Get the full graph, find a connected node.
    r = client.get("/api/graph", params={"corpus_id": corpus_id})
    edges = r.json()["edges"]
    connected = {e["source"] for e in edges} | {e["target"] for e in edges}
    node_id = next(n["id"] for n in r.json()["nodes"] if n["id"] in connected)

    r2 = client.get(f"/api/character/{node_id}/neighbors", params={"corpus_id": corpus_id})
    assert r2.status_code == 200
    sub = r2.json()
    # The node itself must be in the result
    assert any(n["id"] == node_id for n in sub["nodes"])
    # And at least one neighbor
    assert len(sub["nodes"]) >= 2
    # All edges must involve the node or its neighbors
    for e in sub["edges"]:
        assert e["source"] in {n["id"] for n in sub["nodes"]}
        assert e["target"] in {n["id"] for n in sub["nodes"]}


def test_get_neighbors_404(client):
    r = client.get("/api/character/nope/neighbors", params={"corpus_id": "greek-odyssey"})
    assert r.status_code == 404
