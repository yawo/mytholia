"""Graph router: /corpora, /graph, /character/{id} (AGENTS.md §8 sprint 2).

Corpus is always a query/route param — nothing about "Greek" or "Odyssey" is
hardcoded in these handlers (AGENTS.md §2, §8 sprint 3). Error messages are
localized via the Accept-Language header (api.i18n).
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from api.i18n import parse_accept_language, t
from api.models import CorpusSummary, GraphData, GraphNode
from api.retrieval.graph_store import get_store

router = APIRouter()


@router.get("/corpora", response_model=list[CorpusSummary], tags=["graph"])
def list_corpora() -> list[CorpusSummary]:
    """List all available corpora with their node/edge counts."""
    return get_store().list_corpora()


@router.get("/graph", response_model=GraphData, tags=["graph"])
def get_graph(corpus_id: str = Query(..., description="kebab-case corpus id")) -> GraphData:
    """Return the full graph for a corpus."""
    return get_store().get_graph(corpus_id)


@router.get("/character/{node_id}", response_model=GraphNode, tags=["graph"])
def get_character(
    node_id: str,
    corpus_id: str = Query(..., description="kebab-case corpus id"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> GraphNode:
    """Return a single node by id within a corpus."""
    node = get_store().get_node(corpus_id, node_id)
    if node is None:
        locale = parse_accept_language(accept_language)
        raise HTTPException(
            status_code=404,
            detail=t("node_not_found", locale=locale, node_id=node_id, corpus_id=corpus_id),
        )
    return node


@router.get("/subgraph", response_model=GraphData, tags=["graph"])
def get_subgraph(
    corpus_id: str = Query(...),
    node_id: str = Query(...),
    radius: int = Query(1, ge=1, le=3),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> GraphData:
    """Return the local subgraph around a node within ``radius`` hops."""
    store = get_store()
    node = store.get_node(corpus_id, node_id)
    if node is None:
        locale = parse_accept_language(accept_language)
        raise HTTPException(
            status_code=404,
            detail=t("node_not_found", locale=locale, node_id=node_id, corpus_id=corpus_id),
        )
    return store.get_subgraph(corpus_id, node_id, radius=radius)
