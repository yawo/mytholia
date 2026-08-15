"""i18n tests — localized API error messages and narrative script.

Validates that the API returns French (default) and English error details
based on the Accept-Language header, and that the narrative generator
produces localized headings. Corpus-agnostic (AGENTS.md §2).
"""

from __future__ import annotations

import pytest

from tests.conftest import CORPUS_FIXTURES


def test_parse_accept_language_defaults_to_fr():
    from api.i18n import parse_accept_language

    assert parse_accept_language(None) == "fr"
    assert parse_accept_language("") == "fr"
    assert parse_accept_language("de-DE,de;q=0.9") == "fr"
    assert parse_accept_language("fr-FR,fr;q=0.9,en;q=0.8") == "fr"
    assert parse_accept_language("en-US,en;q=0.9") == "en"


def test_graph_error_localized_fr(client):
    r = client.get(
        "/api/character/nope",
        params={"corpus_id": "greek-odyssey"},
        headers={"Accept-Language": "fr-FR"},
    )
    assert r.status_code == 404
    detail = r.json()["detail"]
    # French message uses guillemets « »
    assert "«" in detail and "»" in detail
    assert "introuvable" in detail


def test_graph_error_localized_en(client):
    r = client.get(
        "/api/character/nope",
        params={"corpus_id": "greek-odyssey"},
        headers={"Accept-Language": "en-US"},
    )
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "not found" in detail
    assert "«" not in detail


def test_graph_error_defaults_to_fr_without_header(client):
    r = client.get("/api/character/nope", params={"corpus_id": "greek-odyssey"})
    assert r.status_code == 404
    assert "introuvable" in r.json()["detail"]


def test_subgraph_error_localized(client):
    r = client.get(
        "/api/subgraph",
        params={"corpus_id": "greek-odyssey", "node_id": "nope"},
        headers={"Accept-Language": "en"},
    )
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


def test_podcast_corpus_error_localized_fr(client):
    r = client.post(
        "/api/podcast",
        json={"corpus_id": "no-such-corpus", "entity_id": "x"},
        headers={"Accept-Language": "fr"},
    )
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "«" in detail
    assert "introuvable" in detail


def test_podcast_corpus_error_localized_en(client):
    r = client.post(
        "/api/podcast",
        json={"corpus_id": "no-such-corpus", "entity_id": "x"},
        headers={"Accept-Language": "en"},
    )
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_podcast_script_localized_fr(client, corpus_id: str, fixture_name: str):
    """The podcast script uses French headings when Accept-Language is fr."""
    r = client.get("/api/graph", params={"corpus_id": corpus_id})
    node_id = r.json()["nodes"][0]["id"]
    r2 = client.post(
        "/api/podcast",
        json={"corpus_id": corpus_id, "entity_id": node_id},
        headers={"Accept-Language": "fr-FR"},
    )
    assert r2.status_code == 200
    script = r2.json()["script"]
    assert "Relations et événements" in script
    assert "Sources" in script
    assert "Ton" in script


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_podcast_script_localized_en(client, corpus_id: str, fixture_name: str):
    """The podcast script uses English headings when Accept-Language is en."""
    r = client.get("/api/graph", params={"corpus_id": corpus_id})
    node_id = r.json()["nodes"][0]["id"]
    r2 = client.post(
        "/api/podcast",
        json={"corpus_id": corpus_id, "entity_id": node_id},
        headers={"Accept-Language": "en"},
    )
    assert r2.status_code == 200
    script = r2.json()["script"]
    assert "Relations and events" in script
    assert "Sources" in script
    assert "Tone" in script
    # French heading must NOT appear in the English script
    assert "Relations et événements" not in script
