"""Graph router: /corpora, /corpora/{id}, /graph, /graph/stats, /search,
/character/{id}, /character/{id}/neighbors, /subgraph (AGENTS.md §8 sprint 2).

Corpus is always a query/route param — nothing about "Greek" or "Odyssey" is
hardcoded in these handlers (AGENTS.md §2, §8 sprint 3). Error messages are
localized via the Accept-Language header (api.i18n).
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from api.i18n import parse_accept_language, t
from api.models import (
    CorpusDetail,
    CorpusSummary,
    GraphData,
    GraphNode,
    GraphStats,
    SearchResult,
)
from api.retrieval.graph_store import get_store
from api.retrieval.hybrid_search import HybridSearch

router = APIRouter()


@router.get("/corpora", response_model=list[CorpusSummary], tags=["graph"])
def list_corpora() -> list[CorpusSummary]:
    """List all available corpora with their node/edge counts."""
    return get_store().list_corpora()


@router.get("/corpora/{corpus_id}", response_model=CorpusDetail, tags=["graph"])
def get_corpus(
    corpus_id: str,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> CorpusDetail:
    """Return full metadata for a single corpus: relation types, narrative style, license."""
    detail = get_store().get_corpus_detail(corpus_id)
    if detail is None:
        locale = parse_accept_language(accept_language)
        raise HTTPException(
            status_code=404,
            detail=t("corpus_not_found", locale=locale, corpus_id=corpus_id),
        )
    return detail


@router.get("/graph", response_model=GraphData, tags=["graph"])
def get_graph(
    corpus_id: str = Query(..., description="kebab-case corpus id"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> GraphData:
    """Return the full graph for a corpus."""
    locale = parse_accept_language(accept_language)
    return get_store().get_graph(corpus_id, locale=locale)


@router.get("/graph/stats", response_model=GraphStats, tags=["graph"])
def get_graph_stats(
    corpus_id: str = Query(..., description="kebab-case corpus id"),
) -> GraphStats:
    """Return node-type and relation-type distribution for a corpus."""
    return get_store().get_stats(corpus_id)


@router.get("/search", response_model=list[SearchResult], tags=["graph"])
def search_nodes(
    corpus_id: str = Query(...),
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> list[SearchResult]:
    """Search nodes within a corpus by keyword (hybrid: graph + keyword fusion)."""
    store = get_store()
    searcher = HybridSearch(store)
    nodes = searcher.search(corpus_id, q, limit=limit)
    locale = parse_accept_language(accept_language)
    if locale != "en":
        localized = {node.id: node for node in store.get_graph(corpus_id, locale=locale).nodes}
        nodes = [localized.get(node.id, node) for node in nodes]
    return [SearchResult(node=n, score=1.0) for n in nodes]


@router.get("/character/{node_id}", response_model=GraphNode, tags=["graph"])
def get_character(
    node_id: str,
    corpus_id: str = Query(..., description="kebab-case corpus id"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> GraphNode:
    """Return a single node by id within a corpus."""
    locale = parse_accept_language(accept_language)
    node = get_store().get_node(corpus_id, node_id, locale=locale)
    if node is None:
        raise HTTPException(
            status_code=404,
            detail=t("node_not_found", locale=locale, node_id=node_id, corpus_id=corpus_id),
        )
    return node


@router.get("/character/{node_id}/neighbors", response_model=GraphData, tags=["graph"])
def get_neighbors(
    node_id: str,
    corpus_id: str = Query(..., description="kebab-case corpus id"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> GraphData:
    """Return the direct neighbors of a node (faster than /subgraph for radius=1)."""
    store = get_store()
    locale = parse_accept_language(accept_language)
    node = store.get_node(corpus_id, node_id, locale=locale)
    if node is None:
        raise HTTPException(
            status_code=404,
            detail=t("node_not_found", locale=locale, node_id=node_id, corpus_id=corpus_id),
        )
    return store.get_neighbors(corpus_id, node_id, locale=locale)


@router.get("/subgraph", response_model=GraphData, tags=["graph"])
def get_subgraph(
    corpus_id: str = Query(...),
    node_id: str = Query(...),
    radius: int = Query(1, ge=1, le=3),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> GraphData:
    """Return the local subgraph around a node within ``radius`` hops."""
    store = get_store()
    locale = parse_accept_language(accept_language)
    node = store.get_node(corpus_id, node_id, locale=locale)
    if node is None:
        raise HTTPException(
            status_code=404,
            detail=t("node_not_found", locale=locale, node_id=node_id, corpus_id=corpus_id),
        )
    return store.get_subgraph(corpus_id, node_id, radius=radius, locale=locale)
