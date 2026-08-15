"""FastAPI backend for GraphOdyssée (AGENTS.md §6, §8).

Run::

    cd api && uvicorn main:app --reload --port 8000

The app depends only on the corpus-agnostic ``GraphStore`` interface and the
manifest-driven pipeline — no corpus name is hardcoded here.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import graph, podcast

app = FastAPI(
    title="GraphOdyssée API",
    description="Interactive mythology knowledge-graph explorer (GraphRAG).",
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


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": "GraphOdyssée API", "docs": "/docs"}
