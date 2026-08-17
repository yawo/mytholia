"""Narrative generation: subgraph → podcast-style script.

Corpus-agnostic (AGENTS.md §6). Respects ``narrative_style`` from the corpus
manifest — no tone, length, or deity name is hardcoded.

An OpenAI-compatible chat-completions backend is available when
``OPENAI_API_KEY``, ``OPENAI_BASE_URL``, and ``OPENAI_MODEL`` are configured.
The deterministic template generator remains the offline fallback so tests and
local development never require paid API calls.

i18n: script headings/labels are localized via the ``locale`` argument, which
defaults to French (fr). Mirrors the frontend dictionaries.
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import httpx

from api.i18n import DEFAULT_LOCALE, Locale
from api.retrieval.hybrid_search import neighbor_edges

if TYPE_CHECKING:
    from api.models import CorpusManifest, GraphData, GraphNode

log = logging.getLogger(__name__)

_NARRATIVE_STRINGS: dict[Locale, dict[str, str]] = {
    "fr": {
        "tone_label": "Ton",
        "relations_heading": "Relations et événements",
        "sources_heading": "Sources",
        "fallback_intro": "Voici l'histoire de {label}, un {type}.",
        "summary_intro": "Voici {label} : {summary}",
        "source_marker": "[source : {text}{loc}]",
    },
    "en": {
        "tone_label": "Tone",
        "relations_heading": "Relations and events",
        "sources_heading": "Sources",
        "fallback_intro": "This is the story of {label}, a {type}.",
        "summary_intro": "This is {label}: {summary}",
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


class OpenAICompatibleNarrativeGenerator(NarrativeGenerator):
    """Narrative generation via an OpenAI-compatible chat completions API."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(
        self,
        manifest: CorpusManifest,
        node: GraphNode,
        subgraph: GraphData,
        locale: Locale = DEFAULT_LOCALE,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write concise mythology podcast scripts grounded only in "
                        "the supplied knowledge graph JSON. Do not add any claim unless "
                        "it is supported by source_refs. Preserve source markers."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "locale": locale,
                            "corpus_id": manifest.id,
                            "corpus_name": manifest.name,
                            "style": manifest.narrative_style.model_dump(),
                            "entity": node.model_dump(),
                            "subgraph": subgraph.model_dump(),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.4,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI-compatible narrative response was missing content") from exc
        return clean_audio_narration(str(content))


class TemplateNarrativeGenerator(NarrativeGenerator):
    """Deterministic, offline narrative generator."""

    def generate(
        self,
        manifest: CorpusManifest,
        node: GraphNode,
        subgraph: GraphData,
        locale: Locale = DEFAULT_LOCALE,
    ) -> str:
        lines: list[str] = []
        summary = node.summary.strip()
        intro = (
            _s(locale, "summary_intro").format(label=node.label, summary=summary)
            if summary
            else _s(locale, "fallback_intro").format(label=node.label, type=node.type.lower())
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

        if node.source_refs:
            lines.append(f"{_s(locale, 'sources_heading')} :")
            for ref in node.source_refs:
                loc = f" ({ref.location})" if ref.location else ""
                lines.append(f"  • {ref.text}{loc}")

        return clean_audio_narration("\n".join(lines))


_STAGE_DIRECTION_RE = re.compile(r"^\s*(?:\*\*)?\s*[\[(].*?[\])]\s*(?:\*\*)?\s*:??\s*$")
_MARKDOWN_EMPHASIS_RE = re.compile(r"\*\*(.*?)\*\*")


def clean_audio_narration(script: str) -> str:
    """Remove non-spoken stage directions and markdown from podcast narration."""
    cleaned: list[str] = []
    for raw_line in script.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if _STAGE_DIRECTION_RE.match(line) and not line.lower().startswith(
            ("[source", "[source :")
        ):
            continue
        line = _MARKDOWN_EMPHASIS_RE.sub(r"\1", line)
        cleaned.append(line)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned).strip()


def generator_for(manifest: CorpusManifest) -> NarrativeGenerator:
    """Pick a narrative generator for a manifest (corpus-agnostic)."""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL")
    if api_key and base_url and model:
        return OpenAICompatibleNarrativeGenerator(api_key=api_key, base_url=base_url, model=model)
    return TemplateNarrativeGenerator()
