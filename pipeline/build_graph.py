"""Build-graph stage: assemble nodes/edges into a persisted ``graph.json``.

Corpus-agnostic (AGENTS.md §2). Takes extracted nodes/edges for a corpus and
writes ``data/processed/{corpus_id}/graph.json``. The output schema is the
shared ``GraphData`` model, so the API can load it directly with no
corpus-specific code (AGENTS.md §8 sprint 2).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from api.models import GraphData

if TYPE_CHECKING:
    from api.models import CorpusManifest, GraphEdge, GraphNode

log = logging.getLogger(__name__)

#: Root for processed graph output (AGENTS.md §3).
DATA_PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def build_graph(
    manifest: CorpusManifest,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
) -> GraphData:
    """Assemble and validate a graph for a corpus.

    Performs corpus-agnostic integrity checks:
      - every edge references nodes that exist in this corpus;
      - node/edge ``corpus_id`` matches the manifest id;
      - no duplicate node or edge ids.
    """
    node_ids = {n.id for n in nodes}
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()

    for node in nodes:
        if node.corpus_id != manifest.id:
            raise ValueError(
                f"node {node.id!r} has corpus_id {node.corpus_id!r} but manifest is {manifest.id!r}"
            )
        if node.id in seen_nodes:
            raise ValueError(f"duplicate node id {node.id!r}")
        seen_nodes.add(node.id)

    for edge in edges:
        if edge.corpus_id != manifest.id:
            raise ValueError(
                f"edge {edge.id!r} has corpus_id {edge.corpus_id!r} but manifest is {manifest.id!r}"
            )
        if edge.id in seen_edges:
            raise ValueError(f"duplicate edge id {edge.id!r}")
        seen_edges.add(edge.id)
        if edge.source not in node_ids:
            raise ValueError(f"edge {edge.id!r} references unknown source node {edge.source!r}")
        if edge.target not in node_ids:
            raise ValueError(f"edge {edge.id!r} references unknown target node {edge.target!r}")

    graph = GraphData(corpus_id=manifest.id, nodes=nodes, edges=edges)
    log.info(
        "[%s] built graph: %d nodes, %d edges", manifest.id, len(graph.nodes), len(graph.edges)
    )
    return graph


def save_graph(graph: GraphData, out_dir: Path | None = None) -> Path:
    """Persist a graph to ``data/processed/{corpus_id}/graph.json``."""
    out_dir = out_dir or (DATA_PROCESSED_DIR / graph.corpus_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "graph.json"
    path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    log.info("[%s] wrote %s", graph.corpus_id, path)
    return path


def load_graph(corpus_id: str, processed_dir: Path | None = None) -> GraphData:
    """Load a previously built ``graph.json`` for a corpus."""
    processed_dir = processed_dir or DATA_PROCESSED_DIR
    path = processed_dir / corpus_id / "graph.json"
    if not path.exists():
        raise FileNotFoundError(f"no processed graph for corpus {corpus_id!r} at {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return GraphData.model_validate(raw)
