"""API tests — validated against BOTH corpora (AGENTS.md §9).

Any PR touching api/retrieval/ must pass against Greek AND Egyptian fixtures.
The client fixture builds both corpora first (conftest.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import CORPUS_FIXTURES


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_corpora_includes_both(client):
    r = client.get("/api/corpora")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert {"greek-odyssey", "egyptian-mythology"} <= ids


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_get_graph_returns_nodes_and_edges(client, corpus_id: str, fixture_name: str):
    r = client.get("/api/graph", params={"corpus_id": corpus_id})
    assert r.status_code == 200
    data = r.json()
    assert data["corpus_id"] == corpus_id
    assert len(data["nodes"]) >= 5
    assert len(data["edges"]) >= 3


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_get_character_returns_node(client, corpus_id: str, fixture_name: str):
    # Pick the first node id from the graph, then fetch it directly — no
    # hardcoded entity name (AGENTS.md §2).
    r = client.get("/api/graph", params={"corpus_id": corpus_id})
    nodes = r.json()["nodes"]
    node_id = nodes[0]["id"]
    r2 = client.get(f"/api/character/{node_id}", params={"corpus_id": corpus_id})
    assert r2.status_code == 200
    assert r2.json()["id"] == node_id
    assert r2.json()["corpus_id"] == corpus_id


def test_get_character_404_for_missing(client):
    r = client.get("/api/character/does_not_exist", params={"corpus_id": "greek-odyssey"})
    assert r.status_code == 404


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_get_subgraph_returns_local_neighborhood(client, corpus_id: str, fixture_name: str):
    r = client.get("/api/graph", params={"corpus_id": corpus_id})
    nodes = r.json()["nodes"]
    # Find a node that has at least one edge (corpus-agnostic).
    edges = r.json()["edges"]
    connected = {e["source"] for e in edges} | {e["target"] for e in edges}
    node_id = next(n["id"] for n in nodes if n["id"] in connected)

    r2 = client.get(
        "/api/subgraph", params={"corpus_id": corpus_id, "node_id": node_id, "radius": 1}
    )
    assert r2.status_code == 200
    sub = r2.json()
    assert any(n["id"] == node_id for n in sub["nodes"])
    assert len(sub["nodes"]) <= len(nodes)


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_podcast_endpoint_returns_script(client, corpus_id: str, fixture_name: str):
    """The /podcast endpoint returns a grounded script for an entity.

    Uses the first node — no hardcoded entity name (AGENTS.md §2). The script
    must be non-empty and must not invent facts outside the subgraph.
    """
    r = client.get("/api/graph", params={"corpus_id": corpus_id})
    node_id = r.json()["nodes"][0]["id"]
    label = r.json()["nodes"][0]["label"]

    r2 = client.post("/api/podcast", json={"corpus_id": corpus_id, "entity_id": node_id})
    assert r2.status_code == 200
    body = r2.json()
    assert body["corpus_id"] == corpus_id
    assert body["entity_id"] == node_id
    assert label in body["script"]
    assert len(body["script"]) > 0


def test_podcast_endpoint_reuses_cache(client):
    r = client.get("/api/graph", params={"corpus_id": "greek-odyssey"})
    node_id = r.json()["nodes"][0]["id"]

    first = client.post("/api/podcast", json={"corpus_id": "greek-odyssey", "entity_id": node_id})
    assert first.status_code == 200
    assert first.json()["cached"] is False

    second = client.post("/api/podcast", json={"corpus_id": "greek-odyssey", "entity_id": node_id})
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert second.json()["script"] == first.json()["script"]
    assert second.json()["audio_url"] == first.json()["audio_url"]

    forced = client.post(
        "/api/podcast",
        json={"corpus_id": "greek-odyssey", "entity_id": node_id, "force": True},
    )
    assert forced.status_code == 200
    assert forced.json()["cached"] is False


def test_podcast_engines_reports_configuration(client, monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_TTS_API_KEY", raising=False)

    r = client.get("/api/podcast/engines", params={"corpus_id": "greek-odyssey"})
    assert r.status_code == 200
    body = r.json()
    engines = {engine["engine"]: engine for engine in body["engines"]}
    assert engines["deepgram"]["configured"] is True
    assert engines["deepgram"]["default"] is True
    assert engines["elevenlabs"]["configured"] is False
    assert engines["qwentts"]["configured"] is False


def test_deepgram_model_for_locale_defaults_to_agathe_for_french(monkeypatch):
    from api.generation.tts import deepgram_model_for_locale

    monkeypatch.delenv("DEEPGRAM_TTS_MODEL", raising=False)
    monkeypatch.delenv("DEEPGRAM_TTS_MODEL_FR", raising=False)

    assert deepgram_model_for_locale("fr") == "aura-2-agathe-fr"
    assert deepgram_model_for_locale("fr-FR") == "aura-2-agathe-fr"
    assert deepgram_model_for_locale("en") == "aura-asteria-en"


def test_deepgram_model_for_locale_allows_french_override(monkeypatch):
    from api.generation.tts import deepgram_model_for_locale

    monkeypatch.setenv("DEEPGRAM_TTS_MODEL_FR", "custom-french-model")

    assert deepgram_model_for_locale("fr") == "custom-french-model"


def test_podcast_rejects_unknown_engine(client):
    r = client.get("/api/graph", params={"corpus_id": "greek-odyssey"})
    node_id = r.json()["nodes"][0]["id"]

    r2 = client.post(
        "/api/podcast",
        json={"corpus_id": "greek-odyssey", "entity_id": node_id, "engine": "not-real"},
    )
    assert r2.status_code == 400


def test_podcast_404_unknown_corpus(client):
    r = client.post("/api/podcast", json={"corpus_id": "no-such-corpus", "entity_id": "x"})
    assert r.status_code == 404


def test_podcast_404_unknown_entity(client):
    r = client.post(
        "/api/podcast", json={"corpus_id": "greek-odyssey", "entity_id": "no-such-entity"}
    )
    assert r.status_code == 404


def test_podcast_cache_defaults_to_tmp_on_serverless(monkeypatch):
    """Serverless bundles are read-only, so the default cache must use tmp."""
    import importlib
    import tempfile

    import api.generation.podcast_cache as cache_mod
    import api.generation.tts as tts_mod

    monkeypatch.delenv("PODCAST_CACHE_DIR", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    cache_mod = importlib.reload(cache_mod)
    tts_mod = importlib.reload(tts_mod)

    expected = Path(tempfile.gettempdir()) / "graphodyssee" / "podcasts"
    assert cache_mod.PODCAST_CACHE_DIR == expected
    assert tts_mod._AUDIO_DIR == expected / "audio"

    monkeypatch.delenv("VERCEL", raising=False)
    importlib.reload(cache_mod)
    importlib.reload(tts_mod)


def test_networkx_store_uses_injected_corpora_dir(tmp_path: Path) -> None:
    """NetworkXGraphStore lists manifests from its configured corpora_dir."""
    from api.retrieval.graph_store import NetworkXGraphStore

    corpus_id = "test-corpus"
    corpus_dir = tmp_path / "corpora" / corpus_id
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "manifest.yaml").write_text(
        "id: test-corpus\nname: Test Corpus\nlanguage: en\n", encoding="utf-8"
    )

    store = NetworkXGraphStore(
        processed_dir=tmp_path / "processed", corpora_dir=tmp_path / "corpora"
    )
    summaries = store.list_corpora()

    assert [summary.id for summary in summaries] == [corpus_id]
    assert summaries[0].name == "Test Corpus"


def test_write_audio_falls_back_to_tmp_when_cache_dir_read_only(tmp_path, monkeypatch):
    import errno

    import api.generation.tts as tts_mod

    read_only_audio = tmp_path / "bundle" / "data" / "podcasts" / "audio"
    fallback_root = tmp_path / "tmp-podcasts"
    monkeypatch.setattr(tts_mod, "_AUDIO_DIR", read_only_audio)
    monkeypatch.setattr(tts_mod, "_fallback_podcast_cache_dir", lambda: fallback_root)

    original_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        if self == read_only_audio:
            raise OSError(errno.EROFS, "Read-only file system", str(self))
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    audio_url = tts_mod.write_audio("catholic-saints", "episode", "mp3", b"audio")

    assert audio_url == "/api/podcast/audio/catholic-saints/episode.mp3"
    assert (fallback_root / "audio" / "catholic-saints" / "episode.mp3").read_bytes() == b"audio"
    assert (
        tts_mod.audio_path("catholic-saints", "episode.mp3")
        == fallback_root / "audio" / "catholic-saints" / "episode.mp3"
    )


def test_save_cached_podcast_falls_back_to_tmp_when_cache_dir_read_only(tmp_path, monkeypatch):
    import errno

    import api.generation.podcast_cache as cache_mod
    from api.models import PodcastResponse

    read_only_cache = tmp_path / "bundle" / "data" / "podcasts"
    fallback_root = tmp_path / "tmp-podcasts"
    monkeypatch.setattr(cache_mod, "PODCAST_CACHE_DIR", read_only_cache)
    monkeypatch.setattr(cache_mod, "fallback_podcast_cache_dir", lambda: fallback_root)

    original_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        if self == read_only_cache:
            raise OSError(errno.EROFS, "Read-only file system", str(self))
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    response = PodcastResponse(
        corpus_id="catholic-saints",
        entity_id="saint_example",
        script="Grounded script",
        audio_url="/api/podcast/audio/catholic-saints/episode.mp3",
        length_seconds=180,
        engine="deepgram",
        available_engines=[],
        cached=False,
    )

    path = cache_mod.save_cached_podcast(response, "en")

    assert path.is_relative_to(fallback_root)
    assert (
        cache_mod.load_cached_podcast("catholic-saints", "saint_example", "en", 180, "deepgram")
        == response
    )
