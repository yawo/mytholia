"""Extract stage: turn raw text into graph nodes/edges via an OpenAI-compatible AI.

Corpus-agnostic (AGENTS.md §2, §5). A single default extraction prompt is used
unless a corpus supplies an ``extraction_prompt.md`` override in its manifest.
No deity name, entity type, or relation label is hardcoded here.

An OpenAI-compatible extractor is wired behind an ``Extractor`` interface but
defaults to a deterministic rule-based extractor so the pipeline runs
end-to-end offline on fixtures. The deterministic extractor parses a simple,
human-readable text format (see ``_parse_marker_format``) so fixtures can
express a known-good subgraph without API calls (AGENTS.md §13).
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from api.models import (
    DEFAULT_RELATION_TYPES,
    GraphEdge,
    GraphNode,
    NodeType,
    SourceRef,
)

if TYPE_CHECKING:
    from api.models import CorpusManifest

log = logging.getLogger(__name__)

#: Default extraction prompt (overridable per corpus via the manifest).
DEFAULT_PROMPT = """You are extracting a knowledge graph from mythology source text.

Use the abstract node types: Character, Place, Object, Event, Concept.
Use relation labels from the corpus controlled list (SCREAMING_SNAKE_CASE).

Every node and edge MUST carry a source_refs entry pointing to a passage in the
provided text. If a claim cannot be grounded in the provided text, OMIT it —
do not invent mythology.

Return JSON: {"nodes": [GraphNode...], "edges": [GraphEdge...]}.
"""

#: Marker format for fixture extraction. Each block looks like:
#:   ## NODE char_odysseus Character "Odysseus" "Odyssey" "book 9"
#:     summary: King of Ithaca, son of Laertes.
#:   ## EDGE edge_1 char_odysseus SPOUSE_OF char_penelope "Odyssey" "book 1"
_NODE_RE = re.compile(
    r'^\s*##\s*NODE\s+(?P<id>\S+)\s+(?P<type>\S+)\s+"(?P<label>[^"]+)"(?:\s+"(?P<src_text>[^"]+)")?'
    r'(?:\s+"(?P<src_loc>[^"]+)")?\s*$'
)
_EDGE_RE = re.compile(
    r"^\s*##\s*EDGE\s+(?P<id>\S+)\s+(?P<source>\S+)\s+(?P<relation>[A-Z_]+)\s+(?P<target>\S+)"
    r'(?:\s+"(?P<src_text>[^"]+)")?(?:\s+"(?P<src_loc>[^"]+)")?\s*$'
)
_SUMMARY_RE = re.compile(r"^\s*summary:\s*(?P<summary>.+?)\s*$")


class Extractor(ABC):
    """Interface for extraction implementations (AGENTS.md §5).

    The pipeline drives any implementation via ``extract``; corpora select via
    the manifest's ``extraction.prompt_override`` (and, in later sprints,
    possibly a different implementation). This does not fork the pipeline.
    """

    @abstractmethod
    def extract(
        self, manifest: CorpusManifest, docs: list[dict]
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        raise NotImplementedError


class OpenAICompatibleExtractor(Extractor):
    """Extraction via an OpenAI-compatible chat completions API.

    When ``OPENAI_API_KEY``, ``OPENAI_BASE_URL``, and ``OPENAI_MODEL`` are absent,
    callers fall back to the deterministic fixture extractor.
    """

    def __init__(self, prompt_override: str | None = None, corpus_dir: Path | None = None) -> None:
        self.prompt_override = prompt_override
        self.corpus_dir = corpus_dir

    def _prompt(self) -> str:
        if self.prompt_override and self.corpus_dir:
            p = self.corpus_dir / self.prompt_override
            if p.exists():
                return p.read_text(encoding="utf-8")
        return DEFAULT_PROMPT

    def extract(
        self, manifest: CorpusManifest, docs: list[dict]
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        import os

        import httpx

        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        model = os.environ.get("OPENAI_MODEL")
        if not (api_key and base_url and model):
            raise RuntimeError("OpenAI-compatible extraction is not configured")

        prompt = self._prompt()
        content = json.dumps(
            {
                "manifest": manifest.model_dump(),
                "documents": docs,
                "instructions": prompt,
            },
            ensure_ascii=False,
        )
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract only grounded graph facts. Return strict JSON with "
                        "nodes and edges arrays matching the provided schema."
                    ),
                },
                {"role": "user", "content": content},
            ],
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
        data = response.json()
        try:
            generated = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI-compatible extraction response was missing content") from exc
        return parse_json_payload(str(generated))


class FixtureExtractor(Extractor):
    """Deterministic extractor for cached/fixture text.

    Parses the simple marker format (see module docstring) so a known-good
    subgraph can be expressed in a fixture text file and the pipeline can run
    end-to-end offline. This is the Sprint 0 default so the pipeline is
    runnable without API calls (AGENTS.md §13).
    """

    def extract(
        self, manifest: CorpusManifest, docs: list[dict]
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_node_ids: set[str] = set()
        seen_edge_ids: set[str] = set()

        for doc in docs:
            text = doc.get("text", "")
            filename = doc.get("filename")
            n, e = self._parse_marker_format(text, manifest.id, filename)
            for node in n:
                if node.id in seen_node_ids:
                    continue
                seen_node_ids.add(node.id)
                nodes.append(node)
            for edge in e:
                if edge.id in seen_edge_ids:
                    continue
                seen_edge_ids.add(edge.id)
                edges.append(edge)
        log.info("[%s] extracted %d nodes, %d edges", manifest.id, len(nodes), len(edges))
        return nodes, edges

    def _parse_marker_format(
        self, text: str, corpus_id: str, filename: str | None
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            m = _NODE_RE.match(line)
            if m:
                node = self._build_node(m, corpus_id, filename)
                # consume summary lines that follow
                i += 1
                while i < len(lines):
                    sm = _SUMMARY_RE.match(lines[i])
                    if sm:
                        node.summary = sm.group("summary").strip()
                        i += 1
                        continue
                    if lines[i].strip() == "" or lines[i].lstrip().startswith("## "):
                        break
                    # continuation of summary
                    node.summary = (node.summary + " " + lines[i].strip()).strip()
                    i += 1
                nodes.append(node)
                continue
            em = _EDGE_RE.match(line)
            if em:
                edges.append(self._build_edge(em, corpus_id, filename))
            i += 1
        return nodes, edges

    def _build_node(self, m: re.Match, corpus_id: str, filename: str | None) -> GraphNode:
        refs: list[SourceRef] = []
        if m.group("src_text"):
            loc = m.group("src_loc") or (f"file:{filename}" if filename else None)
            refs.append(SourceRef(text=m.group("src_text"), location=loc))
        return GraphNode(
            id=m.group("id"),
            type=m.group("type"),
            corpus_id=corpus_id,
            label=m.group("label"),
            summary="",
            source_refs=refs,
        )

    def _build_edge(self, m: re.Match, corpus_id: str, filename: str | None) -> GraphEdge:
        refs: list[SourceRef] = []
        if m.group("src_text"):
            loc = m.group("src_loc") or (f"file:{filename}" if filename else None)
            refs.append(SourceRef(text=m.group("src_text"), location=loc))
        relation = m.group("relation")
        label = relation.replace("_", " ").title()
        return GraphEdge(
            id=m.group("id"),
            source=m.group("source"),
            target=m.group("target"),
            relation=relation,
            corpus_id=corpus_id,
            label=label,
            source_refs=refs,
        )


def extractor_for(manifest: CorpusManifest) -> Extractor:
    """Pick an extractor for a manifest.

    Uses ``OpenAICompatibleExtractor`` when configured, else the
    deterministic ``FixtureExtractor`` so the pipeline runs offline (Sprint 0).
    """
    import os

    corpus_dir = Path(__file__).resolve().parent.parent / "corpora" / manifest.id
    if (
        os.environ.get("OPENAI_API_KEY")
        and os.environ.get("OPENAI_BASE_URL")
        and os.environ.get("OPENAI_MODEL")
    ):
        return OpenAICompatibleExtractor(
            prompt_override=manifest.extraction.prompt_override,
            corpus_dir=corpus_dir,
        )
    return FixtureExtractor()


def extract(manifest: CorpusManifest, docs: list[dict]) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Run the extract stage.

    Returns ``(nodes, edges)``. Validates node types against the fixed schema
    and (warns on) relations outside the corpus controlled list.
    """
    ext = extractor_for(manifest)
    nodes, edges = ext.extract(manifest, docs)

    # Validate node types (GraphNode already enforces via pydantic).
    for node in nodes:
        if node.type not in {t.value for t in NodeType}:
            raise ValueError(f"[{manifest.id}] node {node.id} has invalid type {node.type!r}")

    # Warn on relations outside the corpus controlled list (open vocabulary,
    # but controlled per corpus per AGENTS.md §4).
    allowed = set(manifest.relation_types or DEFAULT_RELATION_TYPES)
    for edge in edges:
        if edge.relation not in allowed:
            log.warning(
                "[%s] edge %s uses relation %r not in corpus controlled list %s",
                manifest.id,
                edge.id,
                edge.relation,
                sorted(allowed),
            )
    return nodes, edges


def nodes_edges_to_json(nodes: list[GraphNode], edges: list[GraphEdge], corpus_id: str) -> str:
    """Serialize nodes/edges to a ``graph.json`` string."""
    from api.models import GraphData

    data = GraphData(corpus_id=corpus_id, nodes=nodes, edges=edges)
    return data.model_dump_json(indent=2)


def parse_json_payload(payload: str) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Parse a JSON payload of ``{"nodes":..., "edges":...}``."""
    raw = json.loads(payload)
    nodes = [GraphNode.model_validate(n) for n in raw.get("nodes", [])]
    edges = [GraphEdge.model_validate(e) for e in raw.get("edges", [])]
    return nodes, edges
