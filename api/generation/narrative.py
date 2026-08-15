"""Narrative generation: subgraph → podcast-style script (Claude).

Corpus-agnostic (AGENTS.md §6). Respects ``narrative_style`` from the corpus
manifest — no tone, length, or deity name is hardcoded.

Sprint 0 stub: a deterministic templating generator runs offline so the
``/podcast`` endpoint is exercisable without API calls. Real Claude
generation is wired behind the same ``NarrativeGenerator`` interface in
later sprints (AGENTS.md §13 cost control).

i18n: script headings/labels are localized via the ``locale`` argument, which
defaults to French (fr). Mirrors the frontend dictionaries.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from api.i18n import DEFAULT_LOCALE, Locale
from api.retrieval.hybrid_search import neighbor_edges

if TYPE_CHECKING:
    from api.models import CorpusManifest, GraphData, GraphNode

log = logging.getLogger(__name__)

# Localized template strings per locale. Mirrors frontend/src/i18n/locales/.
_NARRATIVE_STRINGS: dict[Locale, dict[str, str]] = {
    "fr": {
        "tone_label": "Ton",
        "relations_heading": "Relations et événements",
        "sources_heading": "Sources",
        "fallback_intro": "Voici l'histoire de {label}, un {type}.",
        "source_marker": "[source : {text}{loc}]",
    },
    "en": {
        "tone_label": "Tone",
        "relations_heading": "Relations and events",
        "sources_heading": "Sources",
        "fallback_intro": "This is the story of {label}, a {type}.",
        "source_marker": "[source: {text}{loc}]",
    },
}


def _s(locale: Locale, key: str) -> str:
    return _NARRATIVE_STRINGS.get(locale, _NARRATIVE_STRINGS[DEFAULT_LOCALE]).get(
        key, _NARRATIVE_STRINGS[DEFAULT_LOCALE][key]
    )


class NarrativeGenerator(ABC):
    """Interface for narrative generation (AGENTS.md §5, §6)."""

    @abstractmethod
    def generate(
        self,
        manifest: CorpusManifest,
        node: GraphNode,
        subgraph: GraphData,
        locale: Locale = DEFAULT_LOCALE,
    ) -> str:
        raise NotImplementedError


class ClaudeNarrativeGenerator(NarrativeGenerator):
    """Real narrative generation via Claude (AGENTS.md §6).

    Sprint 0 stub: raises when ``ANTHROPIC_API_KEY`` is absent so callers fall
    back to the deterministic generator. The real call respects
    ``manifest.narrative_style`` and grounds the script in the subgraph's
    ``source_refs`` (no invented mythology, AGENTS.md §10). The prompt would
    be localized via the ``locale`` argument.
    """

    def generate(
        self,
        manifest: CorpusManifest,
        node: GraphNode,
        subgraph: GraphData,
        locale: Locale = DEFAULT_LOCALE,
    ) -> str:
        import os

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set; Claude narrative unavailable in Sprint 0"
            )
        raise NotImplementedError("Live Claude narrative is wired up in a later sprint")


class TemplateNarrativeGenerator(NarrativeGenerator):
    """Deterministic, offline narrative generator.

    Produces a short script grounded strictly in the subgraph's nodes, edges,
    and their ``source_refs``. It never invents facts: if a relation or summary
    is absent, it is omitted rather than filled in (AGENTS.md §10).
    """

    def generate(
        self,
        manifest: CorpusManifest,
        node: GraphNode,
        subgraph: GraphData,
        locale: Locale = DEFAULT_LOCALE,
    ) -> str:
        tone = manifest.narrative_style.tone
        lines: list[str] = []
        lines.append(f"[{node.label}]")  # title marker for the narrator
        lines.append(f"({_s(locale, 'tone_label')}: {tone}.)")
        lines.append("")

        intro = node.summary.strip() or _s(locale, "fallback_intro").format(
            label=node.label, type=node.type.lower()
        )
        lines.append(intro)
        lines.append("")

        edges = neighbor_edges(subgraph, node.id)
        if edges:
            lines.append(f"{_s(locale, 'relations_heading')} :")
            for edge in edges:
                direction = "→"
                other_id = edge.target if edge.source == node.id else edge.source
                other = next((n for n in subgraph.nodes if n.id == other_id), None)
                other_label = other.label if other else other_id
                rel = edge.label or edge.relation.replace("_", " ").lower()
                lines.append(f"  • {rel} {direction} {other_label}.")
                if edge.summary:
                    lines.append(f"    {edge.summary}")
                for ref in edge.source_refs:
                    loc = f" ({ref.location})" if ref.location else ""
                    lines.append(
                        "    " + _s(locale, "source_marker").format(text=ref.text, loc=loc)
                    )
            lines.append("")

        # Source provenance for the node itself (AGENTS.md §4, §10).
        if node.source_refs:
            lines.append(f"{_s(locale, 'sources_heading')} :")
            for ref in node.source_refs:
                loc = f" ({ref.location})" if ref.location else ""
                lines.append(f"  • {ref.text}{loc}")

        return "\n".join(lines)


def generator_for(manifest: CorpusManifest) -> NarrativeGenerator:
    """Pick a narrative generator for a manifest (corpus-agnostic)."""
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeNarrativeGenerator()
    return TemplateNarrativeGenerator()
