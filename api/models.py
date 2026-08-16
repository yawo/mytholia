"""Shared pydantic models for graph nodes/edges, API request/response, and corpus manifests.

These models are corpus-agnostic by design (see AGENTS.md §4). No corpus name,
entity type, deity name, or relation label is hardcoded here.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Graph schema (AGENTS.md §4)
# ---------------------------------------------------------------------------

#: Fixed node types — corpus-agnostic. PascalCase per AGENTS.md §10.
NODE_TYPES: tuple[str, ...] = (
    "Character",
    "Place",
    "Object",
    "Event",
    "Concept",
)


class NodeType(str, Enum):
    """Corpus-agnostic node types.

    The set is deliberately abstract so a single schema covers a Greek hero,
    an Egyptian god, a loa, or a Catholic saint without modification.
    """

    CHARACTER = "Character"
    PLACE = "Place"
    OBJECT = "Object"
    EVENT = "Event"
    CONCEPT = "Concept"


#: Relation types are an *open* vocabulary, but a controlled list per-corpus
#: keeps frontend legends consistent (AGENTS.md §4). SCREAMING_SNAKE_CASE.
DEFAULT_RELATION_TYPES: tuple[str, ...] = (
    "CHILD_OF",
    "SPOUSE_OF",
    "FOUGHT",
    "MET",
    "TOOK_PLACE_AT",
    "WORSHIPPED_AS",
    "GUARDS",
    "TRANSFORMED_INTO",
    "RULER_OF",
    "ASSOCIATED_WITH",
)


class SourceRef(BaseModel):
    """A traceable reference to a source passage.

    ``corpus_id`` and ``source_refs`` are mandatory (AGENTS.md §4): every
    extracted fact must be traceable back to a passage.
    """

    model_config = ConfigDict(extra="allow")

    text: str = Field(..., description="Source text title, e.g. 'Odyssey'.")
    location: str | None = Field(
        default=None,
        description=(
            "Free-form locator within the source: book/line range, chapter, URL fragment, etc."
        ),
    )


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Stable, corpus-scoped unique id, e.g. 'char_odysseus'.")
    type: str = Field(..., description=f"One of {NODE_TYPES}.")
    corpus_id: str = Field(..., description="kebab-case corpus identifier this node belongs to.")
    label: str = Field(..., description="Human-readable label, e.g. 'Odysseus'.")
    summary: str = Field(default="", description="Short prose summary grounded in source_refs.")
    source_refs: list[SourceRef] = Field(
        default_factory=list,
        description="Mandatory traceability to source passages (AGENTS.md §4, §10).",
    )

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in NODE_TYPES:
            raise ValueError(f"Unknown node type {v!r}; expected one of {NODE_TYPES}")
        return v


class GraphEdge(BaseModel):
    """A directed relation between two graph nodes."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Stable unique edge id, e.g. 'edge_odysseus_spouse_penelope'.")
    source: str = Field(..., description="Id of the from-node.")
    target: str = Field(..., description="Id of the to-node.")
    relation: str = Field(
        ...,
        description=(
            "Relation label, SCREAMING_SNAKE_CASE, from the corpus controlled list (AGENTS.md §4)."
        ),
    )
    corpus_id: str = Field(..., description="kebab-case corpus identifier this edge belongs to.")
    label: str = Field(default="", description="Human-readable relation label for display.")
    source_refs: list[SourceRef] = Field(default_factory=list)
    summary: str = Field(default="", description="Optional prose about this relation.")


class GraphData(BaseModel):
    """The full graph payload for a corpus: nodes + edges."""

    model_config = ConfigDict(extra="allow")

    corpus_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Corpus manifest (AGENTS.md §5)
# ---------------------------------------------------------------------------


class ScrapeSource(BaseModel):
    """A scrape source entry in a corpus manifest."""

    model_config = ConfigDict(extra="allow")

    type: str = "web_scrape"
    tool: str = Field(default="crawl4ai", description="Scraping tool: crawl4ai or scrapling.")
    seed_urls: list[str] = Field(default_factory=list)


class SearchAugmentedSource(BaseModel):
    """A search-augmented source entry in a corpus manifest."""

    model_config = ConfigDict(extra="allow")

    type: str = "search_augmented"
    tool: str = Field(default="tavily", description="Search tool: tavily or perplexity_sonar.")
    queries: list[str] = Field(default_factory=list)


class ExtractionConfig(BaseModel):
    """Extraction configuration block of a manifest."""

    model_config = ConfigDict(extra="allow")

    prompt_override: str | None = Field(
        default=None,
        description="Filename of an optional prompt override relative to the corpus dir.",
    )
    node_type_hints: list[str] = Field(
        default_factory=lambda: list(NODE_TYPES),
        description="Node types the extractor may emit.",
    )


class NarrativeStyle(BaseModel):
    """Narrative style block of a manifest (AGENTS.md §5)."""

    model_config = ConfigDict(extra="allow")

    tone: str = "reverent, mythic narrator, not academic"
    length_seconds: int = 180


class VoiceConfig(BaseModel):
    """Voice/TTS configuration block of a manifest."""

    model_config = ConfigDict(extra="allow")

    provider: str = "elevenlabs"
    voice_id: str = "${GRAPHODYSSEE_DEFAULT_VOICE_ID}"


class CorpusManifest(BaseModel):
    """A corpus manifest (AGENTS.md §5).

    Adding a corpus means writing one of these (plus an optional prompt
    override). The pipeline reads it and drives scrape → extract → build_graph
    without corpus-specific code paths.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="kebab-case corpus identifier.")
    name: str
    language: str = "en"
    sources: list[dict[str, Any]] = Field(default_factory=list)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    narrative_style: NarrativeStyle = Field(default_factory=NarrativeStyle)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    license_note: str | None = None
    #: Controlled relation vocabulary for this corpus (AGENTS.md §4).
    relation_types: list[str] = Field(default_factory=lambda: list(DEFAULT_RELATION_TYPES))

    @field_validator("id")
    @classmethod
    def _kebab(cls, v: str) -> str:
        if v != v.lower() or " " in v or "_" in v:
            raise ValueError(f"corpus id must be kebab-case (lowercase, hyphenated), got {v!r}")
        return v

    @classmethod
    def from_file(cls, path: str | Path) -> CorpusManifest:
        """Load a manifest from a YAML file."""
        path = Path(path)
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.model_validate(data)

    def sources_parsed(self) -> list[ScrapeSource | SearchAugmentedSource]:
        """Return typed source objects (web_scrape or search_augmented)."""
        out: list[ScrapeSource | SearchAugmentedSource] = []
        for s in self.sources:
            st = (s.get("type") if isinstance(s, dict) else getattr(s, "type", "") or "").lower()
            if st == "search_augmented":
                out.append(SearchAugmentedSource.model_validate(s))
            else:
                out.append(ScrapeSource.model_validate(s))
        return out


# ---------------------------------------------------------------------------
# API request/response envelopes (AGENTS.md §8 sprint 2/4)
# ---------------------------------------------------------------------------


class CorpusSummary(BaseModel):
    """Lightweight corpus descriptor for the /corpora listing."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    language: str = "en"
    node_count: int = 0
    edge_count: int = 0
    license_note: str | None = None


class CorpusDetail(BaseModel):
    """Full corpus metadata for the /corpora/{corpus_id} endpoint.

    Includes the controlled relation vocabulary and narrative style so the
    frontend can render legends and UI without hardcoding anything
    (AGENTS.md §2, §4).
    """

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    language: str = "en"
    node_count: int = 0
    edge_count: int = 0
    relation_types: list[str] = Field(default_factory=list)
    narrative_tone: str = ""
    narrative_length_seconds: int = 180
    voice_provider: str = "elevenlabs"
    license_note: str | None = None


class GraphStats(BaseModel):
    """Statistics for a corpus graph (node-type distribution, totals)."""

    model_config = ConfigDict(extra="allow")

    corpus_id: str
    total_nodes: int
    total_edges: int
    node_type_counts: dict[str, int] = Field(default_factory=dict)
    relation_type_counts: dict[str, int] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A search hit: the node plus a relevance score."""

    model_config = ConfigDict(extra="allow")

    node: GraphNode
    score: float


class HealthStatus(BaseModel):
    """Health check response with diagnostic info."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    corpus_count: int = 0
    store_backend: str = "networkx"


class PodcastRequest(BaseModel):
    """Request body for /podcast."""

    corpus_id: str
    entity_id: str
    length_seconds: int | None = None
    force: bool = Field(
        default=False,
        description="Regenerate the script and audio even when a cached podcast exists.",
    )


class PodcastResponse(BaseModel):
    """Response for /podcast."""

    corpus_id: str
    entity_id: str
    script: str
    audio_url: str | None = None
    length_seconds: int = 180
    cached: bool = False
