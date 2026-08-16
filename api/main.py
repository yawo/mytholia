"""FastAPI backend for GraphOdyssée (AGENTS.md §6, §8).

Run::

    cd api && uvicorn main:app --reload --port 8000

The app depends only on the corpus-agnostic ``GraphStore`` interface and the
manifest-driven pipeline — no corpus name is hardcoded here.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.models import HealthStatus
from api.retrieval.graph_store import get_store, get_store_backend
from api.routers import graph, podcast

app = FastAPI(
    title="GraphOdyssée API",
    description="Explorateur interactif de graphe de connaissances mythologiques (GraphRAG).",
    version="0.1.0",
)

# Permissive CORS for the local frontend dev server (AGENTS.md §7).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph.router, prefix="/api")
app.include_router(podcast.router, prefix="/api")

STATIC_DIR = Path(__file__).resolve().parent.parent / "app" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health", response_model=HealthStatus, tags=["meta"])
def health() -> HealthStatus:
    """Health check with diagnostic info: corpus count and store backend."""
    try:
        corpora = get_store().list_corpora()
        count = len(corpora)
    except Exception:
        count = 0
    return HealthStatus(status="ok", corpus_count=count, store_backend=get_store_backend())


@app.get("/", include_in_schema=False, response_model=None)
def root():
    """Serve the bundled frontend from the same Python app."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"name": "GraphOdyssée API", "docs": "/docs"}


@app.get("/{path:path}", include_in_schema=False, response_model=None)
def spa_fallback(path: str):
    """Allow client-side routes while keeping /api handled by routers above."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"name": "GraphOdyssée API", "docs": "/docs", "path": path}
