"""Graph store interface: NetworkX (V1) or FalkorDB/Memgraph (V2).

Same interface for both (AGENTS.md §6, §8 sprint 2). The API loads whichever
store is configured via one interface — no corpus-specific code.

Sprint 0 ships the ``NetworkXGraphStore`` (zero infra, AGENTS.md §6) backed by
the ``graph.json`` files produced by the pipeline. A ``CypherGraphStore`` stub
shows how FalkorDB/Memgraph would slot in behind the same ``GraphStore`` ABC.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from api.i18n import Locale
from api.models import CorpusDetail, CorpusManifest, CorpusSummary, GraphData, GraphNode, GraphStats

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

#: Root for processed graph output (mirrors pipeline.build_graph).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PROCESSED_DIR = Path(os.environ.get("DATA_PROCESSED_DIR", REPO_ROOT / "data" / "processed"))
#: Root for corpora manifests.
CORPORA_DIR = Path(os.environ.get("CORPORA_DIR", REPO_ROOT / "corpora"))


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
    def get_graph(self, corpus_id: str, locale: Locale = "en") -> GraphData:
        """Return the full graph for a corpus."""
        raise NotImplementedError

    @abstractmethod
    def get_node(self, corpus_id: str, node_id: str, locale: Locale = "en") -> GraphNode | None:
        """Return a single node by id, or None."""
        raise NotImplementedError

    @abstractmethod
    def get_subgraph(
        self, corpus_id: str, node_id: str, radius: int = 1, locale: Locale = "en"
    ) -> GraphData:
        """Return the local subgraph around a node within ``radius`` hops."""
        raise NotImplementedError

    def get_corpus_detail(self, corpus_id: str) -> CorpusDetail | None:
        """Return full metadata for a single corpus (optional override)."""
        return None

    def get_stats(self, corpus_id: str) -> GraphStats:
        """Return node-type and relation-type distribution (optional override)."""
        raise NotImplementedError

    def get_neighbors(self, corpus_id: str, node_id: str, locale: Locale = "en") -> GraphData:
        """Return direct neighbors of a node (optional override)."""
        raise NotImplementedError


def _load_manifest_summary(corpus_id: str, corpora_dir: Path | None = None) -> CorpusSummary | None:
    """Load a lightweight summary from a corpus manifest (corpus-agnostic)."""
    from api.models import CorpusManifest

    root = corpora_dir or CORPORA_DIR
    path = root / corpus_id / "manifest.yaml"
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

    @staticmethod
    def _localized_graph(data: GraphData, locale: Locale) -> GraphData:
        """Overlay locale-specific display text while preserving graph facts."""
        if locale == "en":
            return data

        payload = data.model_dump()
        for item in [*payload["nodes"], *payload["edges"]]:
            localized = item.get("i18n", {}).get(locale, {})
            for field in ("label", "summary"):
                if localized.get(field):
                    item[field] = localized[field]
        return GraphData.model_validate(payload)

    def list_corpora(self) -> list[CorpusSummary]:
        summaries: list[CorpusSummary] = []
        if not self.corpora_dir.exists():
            return summaries
        for child in sorted(self.corpora_dir.iterdir()):
            if not child.is_dir() or not (child / "manifest.yaml").exists():
                continue
            summary = _load_manifest_summary(child.name, self.corpora_dir)
            if summary is None:
                continue
            data = self._load_graph_data(child.name)
            summary.node_count = len(data.nodes)
            summary.edge_count = len(data.edges)
            summaries.append(summary)
        return summaries

    def get_graph(self, corpus_id: str, locale: Locale = "en") -> GraphData:
        return self._localized_graph(self._load_graph_data(corpus_id), locale)

    def get_corpus_detail(self, corpus_id: str) -> CorpusDetail | None:
        """Return full metadata for a single corpus (AGENTS.md §4, §5)."""
        path = self.corpora_dir / corpus_id / "manifest.yaml"
        if not path.exists():
            return None
        manifest = CorpusManifest.from_file(path)
        data = self._load_graph_data(corpus_id)
        return CorpusDetail(
            id=manifest.id,
            name=manifest.name,
            language=manifest.language,
            node_count=len(data.nodes),
            edge_count=len(data.edges),
            relation_types=manifest.relation_types,
            narrative_tone=manifest.narrative_style.tone,
            narrative_length_seconds=manifest.narrative_style.length_seconds,
            voice_provider=manifest.voice.provider,
            license_note=manifest.license_note,
        )

    def get_stats(self, corpus_id: str) -> GraphStats:
        """Return node-type and relation-type distribution for a corpus."""
        data = self._load_graph_data(corpus_id)
        node_type_counts: dict[str, int] = {}
        for n in data.nodes:
            node_type_counts[n.type] = node_type_counts.get(n.type, 0) + 1
        relation_type_counts: dict[str, int] = {}
        for e in data.edges:
            relation_type_counts[e.relation] = relation_type_counts.get(e.relation, 0) + 1
        return GraphStats(
            corpus_id=corpus_id,
            total_nodes=len(data.nodes),
            total_edges=len(data.edges),
            node_type_counts=node_type_counts,
            relation_type_counts=relation_type_counts,
        )

    def get_neighbors(self, corpus_id: str, node_id: str, locale: Locale = "en") -> GraphData:
        """Return only the direct neighbors of a node (radius=1, no ego_graph)."""
        data = self.get_graph(corpus_id, locale=locale)
        neighbor_ids: set[str] = set()
        for e in data.edges:
            if e.source == node_id:
                neighbor_ids.add(e.target)
            if e.target == node_id:
                neighbor_ids.add(e.source)
        if not neighbor_ids:
            return GraphData(corpus_id=corpus_id)
        all_ids = {node_id} | neighbor_ids
        sub_nodes = [n for n in data.nodes if n.id in all_ids]
        sub_edges = [e for e in data.edges if e.source in all_ids and e.target in all_ids]
        return GraphData(corpus_id=corpus_id, nodes=sub_nodes, edges=sub_edges)

    def get_node(self, corpus_id: str, node_id: str, locale: Locale = "en") -> GraphNode | None:
        data = self.get_graph(corpus_id, locale=locale)
        for node in data.nodes:
            if node.id == node_id:
                return node
        return None

    def get_subgraph(
        self, corpus_id: str, node_id: str, radius: int = 1, locale: Locale = "en"
    ) -> GraphData:
        """Return nodes/edges within ``radius`` hops of ``node_id``.

        Uses NetworkX ego_graph when available; falls back to direct neighbors.
        """
        nx = self._import_nx()
        data = self.get_graph(corpus_id, locale=locale)

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

    def __init__(
        self,
        uri: str | None = None,
        *,
        provider: str | None = None,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri
        self.provider = provider or os.environ.get("GRAPH_DB_PROVIDER", "falkordb")
        self.database = database or os.environ.get("GRAPH_DB_NAME", "graphodyssee")
        self.username = username or os.environ.get("GRAPH_DB_USER")
        self.password = password or os.environ.get("GRAPH_DB_PASSWORD")

    def list_corpora(self) -> list[CorpusSummary]:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_graph(self, corpus_id: str, locale: Locale = "en") -> GraphData:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_node(self, corpus_id: str, node_id: str, locale: Locale = "en") -> GraphNode | None:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_subgraph(
        self, corpus_id: str, node_id: str, radius: int = 1, locale: Locale = "en"
    ) -> GraphData:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_stats(self, corpus_id: str) -> GraphStats:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")

    def get_neighbors(self, corpus_id: str, node_id: str, locale: Locale = "en") -> GraphData:
        raise NotImplementedError("CypherGraphStore is wired up in sprint 2 (V2)")


_store: GraphStore | None = None


def get_store() -> GraphStore:
    """Return the configured graph store (AGENTS.md §6).

    Selects CypherGraphStore when ``GRAPH_DB_URI`` is set, else the V1
    NetworkXGraphStore. Routers depend only on this function.
    """
    global _store, _store_backend
    if _store is not None:
        return _store

    backend = os.environ.get("GRAPH_STORE_BACKEND", "").strip().lower()
    uri = os.environ.get("GRAPH_DB_URI")
    use_cypher = backend in {"cypher", "falkordb", "memgraph"} or bool(uri)
    if use_cypher:
        log.info("using CypherGraphStore (V2)")
        _store = CypherGraphStore(
            uri=uri,
            provider=os.environ.get("GRAPH_DB_PROVIDER") or backend or None,
        )
        _store_backend = "cypher"
    else:
        _store = NetworkXGraphStore()
        _store_backend = "networkx"
    return _store


_store_backend: str = "networkx"


def get_store_backend() -> str:
    """Return the name of the active store backend (for /health)."""
    return _store_backend


def set_store(store: GraphStore) -> None:
    """Override the store (used by tests to inject an in-memory store)."""
    global _store, _store_backend
    _store = store
    _store_backend = type(store).__name__
