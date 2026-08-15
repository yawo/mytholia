"""Graph router: /corpora, /graph, /character/{id} (AGENTS.md §8 sprint 2).

Corpus is always a query/route param — nothing about "Greek" or "Odyssey" is
hardcoded in these handlers (AGENTS.md §2, §8 sprint 3).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

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
) -> GraphNode:
    """Return a single node by id within a corpus."""
    node = get_store().get_node(corpus_id, node_id)
    if node is None:
        raise HTTPException(
            status_code=404, detail=f"node {node_id!r} not found in corpus {corpus_id!r}"
        )
    return node


@router.get("/subgraph", response_model=GraphData, tags=["graph"])
def get_subgraph(
    corpus_id: str = Query(...),
    node_id: str = Query(...),
    radius: int = Query(1, ge=1, le=3),
) -> GraphData:
    """Return the local subgraph around a node within ``radius`` hops."""
    store = get_store()
    node = store.get_node(corpus_id, node_id)
    if node is None:
        raise HTTPException(
            status_code=404, detail=f"node {node_id!r} not found in corpus {corpus_id!r}"
        )
    return store.get_subgraph(corpus_id, node_id, radius=radius)
