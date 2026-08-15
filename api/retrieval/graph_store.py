"""Graph store interface: NetworkX (V1) or FalkorDB/Memgraph (V2).

Same interface for both (AGENTS.md §6, §8 sprint 2). The API loads whichever
store is configured via one interface — no corpus-specific code.

Sprint 0 ships the ``NetworkXGraphStore`` (zero infra, AGENTS.md §6) backed by
the ``graph.json`` files produced by the pipeline. A ``CypherGraphStore`` stub
shows how FalkorDB/Memgraph would slot in behind the same ``GraphStore`` ABC.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from api.models import CorpusSummary, GraphData, GraphNode

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

#: Root for processed graph output (mirrors pipeline.build_graph).
DATA_PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
#: Root for corpora manifests.
CORPORA_DIR = Path(__file__).resolve().parent.parent.parent / "corpora"


class GraphStore(ABC):
    """Corpus-agnostic graph store interface (AGENTS.md §6).

    V1 (NetworkX + graph.json) and V2 (FalkorDB/Memgraph) both implement this.
    The API depends only on this interface, so the store can be swapped via
    config without touching routers.
    """

    @abstractmethod
    def list_corpora(self) -> list[CorpusSummary]:
        """Return a summary of all available corpora."""
        raise NotImplementedError

    @abstractmethod
    def get_graph(self, corpus_id: str) -> GraphData:
        """Return the full graph for a corpus."""
        raise NotImplementedError

    @abstractmethod
    def get_node(self, corpus_id: str, node_id: str) -> GraphNode | None:
        """Return a single node by id, or None."""
        raise NotImplementedError

    @abstractmethod
    def get_subgraph(self, corpus_id: str, node_id: str, radius: int = 1) -> GraphData:
        """Return the local subgraph around a node within ``radius`` hops."""
        raise NotImplementedError


def _load_manifest_summary(corpus_id: str) -> CorpusSummary | None:
    """Load a lightweight summary from a corpus manifest (corpus-agnostic)."""
    from api.models import CorpusManifest

    path = CORPORA_DIR / corpus_id / "manifest.yaml"
    if not path.exists():
        return None
    manifest = CorpusManifest.from_file(path)
    return CorpusSummary(
        id=manifest.id,
        name=manifest.name,
        language=manifest.language,
        license_note=manifest.license_note,
    )


class NetworkXGraphStore(GraphStore):
    """V1 store: loads ``graph.json`` into an in-memory NetworkX graph.

    Zero infra (AGENTS.md §6). If ``graph.json`` is absent for a corpus, the
    graph is empty but the corpus is still listed (manifest exists).
    """

    def __init__(self, processed_dir: Path | None = None, corpora_dir: Path | None = None) -> None:
        self.processed_dir = processed_dir or DATA_PROCESSED_DIR
        self.corpora_dir = corpora_dir or CORPORA_DIR
        self._nx: object | None = None  # lazily imported

    def _import_nx(self):
        if self._nx is None:
            try:
                import networkx as nx

                self._nx = nx
            except ImportError as e:
                raise ImportError(
                    "networkx is required for NetworkXGraphStore (V1). Install it or configure a "
                    "different GraphStore."
                ) from e
        return self._nx

    def _graph_path(self, corpus_id: str) -> Path:
        return self.processed_dir / corpus_id / "graph.json"

    def _load_graph_data(self, corpus_id: str) -> GraphData:
        import json

        path = self._graph_path(corpus_id)
        if not path.exists():
            return GraphData(corpus_id=corpus_id)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return GraphData.model_validate(raw)

    def list_corpora(self) -> list[CorpusSummary]:
        summaries: list[CorpusSummary] = []
        if not self.corpora_dir.exists():
            return summaries
        for child in sorted(self.corpora_dir.iterdir()):
            if not child.is_dir() or not (child / "manifest.yaml").exists():
                continue
            summary = _load_manifest_summary(child.name)
            if summary is None:
                continue
            data = self._load_graph_data(child.name)
            summary.node_count = len(data.nodes)
            summary.edge_count = len(data.edges)
            summaries.append(summary)
        return summaries

    def get_graph(self, corpus_id: str) -> GraphData:
        return self._load_graph_data(corpus_id)

    def get_node(self, corpus_id: str, node_id: str) -> GraphNode | None:
        data = self._load_graph_data(corpus_id)
        for node in data.nodes:
            if node.id == node_id:
                return node
        return None

    def get_subgraph(self, corpus_id: str, node_id: str, radius: int = 1) -> GraphData:
        """Return nodes/edges within ``radius`` hops of ``node_id``.

        Uses NetworkX ego_graph when available; falls back to direct neighbors.
        """
        nx = self._import_nx()
        data = self._load_graph_data(corpus_id)

        g = nx.MultiDiGraph()
        id_to_node = {n.id: n for n in data.nodes}
        for n in data.nodes:
            g.add_node(n.id)
        for e in data.edges:
            if e.source in id_to_node and e.target in id_to_node:
                g.add_edge(e.source, e.target, key=e.id, edge=e)

        if node_id not in g:
            return GraphData(corpus_id=corpus_id)

        try:
            sub = nx.ego_graph(g.to_undirected(as_view=True), node_id, radius=radius)
            sub_ids = set(sub.nodes())
        except Exception:
            # Fallback: direct neighbors only.
            sub_ids = {node_id} | set(g.successors(node_id)) | set(g.predecessors(node_id))

        sub_nodes = [n for n in data.nodes if n.id in sub_ids]
        sub_edges = [e for e in data.edges if e.source in sub_ids and e.target in sub_ids]
        return GraphData(corpus_id=corpus_id, nodes=sub_nodes, edges=sub_edges)


class CypherGraphStore(GraphStore):
    """V2 store stub: FalkorDB (default) or Memgraph, both openCypher.

    Wired up in a later sprint behind the same interface (AGENTS.md §6). The
    retrieval code is written once against Cypher-style queries and targets
    either backend — no Neo4j dependency needed.
    """

    def __init__(self, uri: str | None = None) -> None:
        self.uri = uri

    def list_corpora(self) -> list[CorpusSummary]:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_graph(self, corpus_id: str) -> GraphData:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_node(self, corpus_id: str, node_id: str) -> GraphNode | None:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_subgraph(self, corpus_id: str, node_id: str, radius: int = 1) -> GraphData:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")


_store: GraphStore | None = None


def get_store() -> GraphStore:
    """Return the configured graph store (AGENTS.md §6).

    Selects CypherGraphStore when ``GRAPH_DB_URI`` is set, else the V1
    NetworkXGraphStore. Routers depend only on this function.
    """
    global _store
    if _store is not None:
        return _store
    import os

    uri = os.environ.get("GRAPH_DB_URI")
    if uri:
        log.info("using CypherGraphStore (V2) with GRAPH_DB_URI")
        _store = CypherGraphStore(uri=uri)
    else:
        _store = NetworkXGraphStore()
    return _store


def set_store(store: GraphStore) -> None:
    """Override the store (used by tests to inject an in-memory store)."""
    global _store
    _store = store
