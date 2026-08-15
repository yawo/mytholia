"""Hybrid search: vector + graph fusion with a local reranker.

Corpus-agnostic (AGENTS.md §6). V1 provides graph-only retrieval (ego subgraph
plus keyword match over node labels/summaries). Vector (Qdrant) and local
cross-encoder reranking slots in behind the same ``HybridSearch`` interface in
later sprints — without touching routers.

No corpus name or entity type is hardcoded here.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from api.models import GraphData, GraphEdge, GraphNode

if TYPE_CHECKING:
    from api.retrieval.graph_store import GraphStore

log = logging.getLogger(__name__)


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", text.lower()) if t}


class HybridSearch:
    """Corpus-agnostic hybrid retrieval interface (AGENTS.md §6).

    V1: graph ego-subgraph retrieval fused with keyword matching. V2 adds
    Qdrant vectors and a local cross-encoder reranker behind the same method.
    """

    def __init__(self, store: GraphStore) -> None:
        self.store = store

    def search(
        self,
        corpus_id: str,
        query: str,
        limit: int = 10,
    ) -> list[GraphNode]:
        """Return nodes matching ``query`` by keyword over label/summary.

        Graph-context fusion: also boosts nodes connected to keyword-matched
        neighbors. Reranking is local-only in V1 (no paid rerank API in the hot
        path, AGENTS.md §6).
        """
        graph = self.store.get_graph(corpus_id)
        if not graph.nodes:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        scored: list[tuple[float, GraphNode]] = []
        by_id = {n.id: n for n in graph.nodes}
        adj: dict[str, set[str]] = {n.id: set() for n in graph.nodes}
        for e in graph.edges:
            if e.source in adj and e.target in adj:
                adj[e.source].add(e.target)
                adj[e.target].add(e.source)

        for node in graph.nodes:
            tokens = _tokenize(f"{node.label} {node.type} {node.summary}")
            overlap = q_tokens & tokens
            if not overlap:
                continue
            score = float(len(overlap))
            # graph-context fusion: neighbors that also match boost the node
            for nid in adj.get(node.id, ()):
                nb = by_id.get(nid)
                if nb is None:
                    continue
                nb_tokens = _tokenize(f"{nb.label} {nb.summary}")
                score += 0.25 * len(q_tokens & nb_tokens)
            scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:limit]]

    def retrieve_context(
        self,
        corpus_id: str,
        node_id: str,
        radius: int = 1,
    ) -> GraphData:
        """Return the local subgraph around a node — the GraphRAG context.

        This is what the narrative generator grounds its script in
        (AGENTS.md §1, §10).
        """
        return self.store.get_subgraph(corpus_id, node_id, radius=radius)


def neighbor_edges(graph: GraphData, node_id: str) -> list[GraphEdge]:
    """Return edges incident to ``node_id`` within ``graph``."""
    return [e for e in graph.edges if e.source == node_id or e.target == node_id]
