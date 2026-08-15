"""Shared pytest fixtures.

Per AGENTS.md §9, both the Greek and Egyptian fixtures are required and used by
every test touching the pipeline or API. These fixtures wire the fixture text
into ``data/raw/{corpus_id}/`` so the corpus-agnostic pipeline can run
end-to-end offline (AGENTS.md §13).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

# Ensure no live API calls happen during tests (AGENTS.md §13).
for _k in (
    "ANTHROPIC_API_KEY",
    "ELEVENLABS_API_KEY",
    "QWEN_TTS_API_KEY",
    "TAVILY_API_KEY",
    "PERPLEXITY_API_KEY",
):
    os.environ.pop(_k, None)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"

#: (corpus_id, fixture_dir_name) pairs — both corpora required (AGENTS.md §9).
CORPUS_FIXTURES = [("greek-odyssey", "greek"), ("egyptian-mythology", "egyptian")]


@pytest.fixture()
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def isolated_data(tmp_path: Path, monkeypatch) -> Path:
    """Copy fixture raw text into a temp data/raw + data/processed tree.

    This isolates tests from the real data/ directory and lets the
    corpus-agnostic pipeline read fixtures as if they were cached scrapes.
    """
    data_root = tmp_path / "data"
    raw_root = data_root / "raw"
    processed_root = data_root / "processed"
    for corpus_id, fixture_name in CORPUS_FIXTURES:
        src = FIXTURES / fixture_name / "raw.txt"
        dst_dir = raw_root / corpus_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst_dir / "raw.txt")
    processed_root.mkdir(parents=True, exist_ok=True)

    # Point the pipeline + store at the temp tree.
    import api.retrieval.graph_store as store_mod
    import pipeline.build_graph as build_mod
    import pipeline.scrape as scrape_mod

    monkeypatch.setattr(scrape_mod, "DATA_RAW_DIR", raw_root)
    monkeypatch.setattr(build_mod, "DATA_PROCESSED_DIR", processed_root)
    monkeypatch.setattr(store_mod, "DATA_PROCESSED_DIR", processed_root)
    return data_root


@pytest.fixture()
def greek_graph(isolated_data) -> object:
    """Build and return the greek-odyssey GraphData."""
    from pipeline.corpus_loader import run_pipeline

    run_pipeline("greek-odyssey")
    from api.retrieval.graph_store import NetworkXGraphStore

    return NetworkXGraphStore


@pytest.fixture()
def client(isolated_data):
    """FastAPI TestClient pointed at the isolated data tree."""
    from fastapi.testclient import TestClient

    from api.main import app
    from api.retrieval.graph_store import NetworkXGraphStore, set_store
    from pipeline.corpus_loader import run_pipeline

    # Build both corpora graphs first (AGENTS.md §9: both required).
    for corpus_id, _ in CORPUS_FIXTURES:
        run_pipeline(corpus_id)

    set_store(NetworkXGraphStore())
    with TestClient(app) as c:
        yield c
    set_store(NetworkXGraphStore())  # reset
