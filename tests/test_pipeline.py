"""Pipeline tests — validated against BOTH corpora (AGENTS.md §9).

Any PR touching pipeline/ must pass against Greek AND Egyptian fixtures.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tests.conftest import CORPUS_FIXTURES


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_manifest_loads(corpus_id: str, fixture_name: str, repo_root: Path) -> None:
    """Each corpus manifest loads and is well-formed (AGENTS.md §5)."""
    from pipeline.corpus_loader import load_manifest

    manifest = load_manifest(corpus_id)
    assert manifest.id == corpus_id
    assert manifest.name
    assert manifest.id == manifest.id.lower()
    assert "_" not in manifest.id  # kebab-case (AGENTS.md §10)


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_pipeline_produces_graph_json(
    corpus_id: str, fixture_name: str, isolated_data: Path
) -> None:
    """run_pipeline writes a valid graph.json with >=5 nodes (AGENTS.md §8 sprint 1)."""
    from pipeline.corpus_loader import run_pipeline

    out = run_pipeline(corpus_id)
    assert out.exists()
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["corpus_id"] == corpus_id
    assert len(raw["nodes"]) >= 5, f"{corpus_id}: expected >=5 nodes, got {len(raw['nodes'])}"
    assert len(raw["edges"]) >= 3


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_nodes_carry_source_refs(corpus_id: str, fixture_name: str, isolated_data: Path) -> None:
    """Every node carries a source_ref — mandatory traceability (AGENTS.md §4, §10)."""
    from pipeline.corpus_loader import run_pipeline

    out = run_pipeline(corpus_id)
    raw = json.loads(out.read_text(encoding="utf-8"))
    for node in raw["nodes"]:
        assert node["source_refs"], f"node {node['id']} has no source_refs"
    for edge in raw["edges"]:
        assert edge["source_refs"], f"edge {edge['id']} has no source_refs"


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_node_types_are_valid_schema(
    corpus_id: str, fixture_name: str, isolated_data: Path
) -> None:
    """Nodes use only the fixed, corpus-agnostic node types (AGENTS.md §4)."""
    from api.models import NODE_TYPES
    from pipeline.corpus_loader import run_pipeline

    out = run_pipeline(corpus_id)
    raw = json.loads(out.read_text(encoding="utf-8"))
    for node in raw["nodes"]:
        assert node["type"] in NODE_TYPES, f"node {node['id']} has invalid type {node['type']!r}"


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_edges_reference_existing_nodes(
    corpus_id: str, fixture_name: str, isolated_data: Path
) -> None:
    """Integrity: every edge references nodes that exist (build_graph enforces)."""
    from pipeline.corpus_loader import run_pipeline

    out = run_pipeline(corpus_id)
    raw = json.loads(out.read_text(encoding="utf-8"))
    ids = {n["id"] for n in raw["nodes"]}
    for edge in raw["edges"]:
        assert edge["source"] in ids, f"edge {edge['id']} source missing"
        assert edge["target"] in ids, f"edge {edge['id']} target missing"


@pytest.mark.parametrize("corpus_id,fixture_name", CORPUS_FIXTURES)
def test_no_corpus_specific_hardcoding(corpus_id: str, fixture_name: str) -> None:
    """Corpus-agnosticism: pipeline code must not hardcode corpus-specific logic.

    Scans pipeline/*.py for corpus-id strings used in executable code. A corpus
    id appearing in a string constant in code -- e.g. a branch like
    ``if corpus_id == "greek-odyssey"`` -- would break the corpus-agnosticism
    rule (AGENTS.md §2). Docstrings and argparse help text are allowed.
    """
    pipeline_dir = Path(__file__).resolve().parent.parent / "pipeline"
    offenders: list[str] = []
    for py in pipeline_dir.glob("*.py"):
        source = py.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py))
        # Collect lineno of all docstrings (Expr(Constant(str)) at the head of
        # a module/function/class body).
        docstring_lines: set[int] = set()
        for parent in ast.walk(tree):
            body = getattr(parent, "body", None)
            if not isinstance(body, list) or not body:
                continue
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstring_lines.add(first.value.lineno)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and corpus_id in node.value
            ):
                if node.lineno in docstring_lines:
                    continue
                offenders.append(f"{py.name}:{node.lineno}")
    assert not offenders, f"corpus id {corpus_id!r} hardcoded in pipeline code: {offenders}"


def test_list_corpus_ids_includes_both(repo_root: Path) -> None:
    """Both seeded corpora are discoverable (AGENTS.md §9)."""
    from pipeline.corpus_loader import list_corpus_ids

    ids = set(list_corpus_ids())
    assert {"greek-odyssey", "egyptian-mythology"} <= ids


def test_build_graph_rejects_dangling_edge(tmp_path: Path) -> None:
    """build_graph raises on an edge referencing a missing node (integrity)."""
    from api.models import CorpusManifest, GraphEdge, GraphNode

    manifest = CorpusManifest(id="test-corpus", name="Test")
    n = GraphNode(id="n1", type="Character", corpus_id="test-corpus", label="A")
    # edge references n2 which does not exist
    e = GraphEdge(
        id="e1", source="n1", target="n2", relation="MET", corpus_id="test-corpus", label="met"
    )
    from pipeline.build_graph import build_graph

    with pytest.raises(ValueError, match="unknown target node"):
        build_graph(manifest, [n], [e])


def test_build_graph_rejects_cross_corpus_node() -> None:
    """A node whose corpus_id doesn't match the manifest is rejected."""
    from api.models import CorpusManifest, GraphNode
    from pipeline.build_graph import build_graph

    manifest = CorpusManifest(id="test-corpus", name="Test")
    n = GraphNode(id="n1", type="Character", corpus_id="other-corpus", label="A")
    with pytest.raises(ValueError, match="corpus_id"):
        build_graph(manifest, [n], [])
