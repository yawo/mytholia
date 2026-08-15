"""Backend i18n: localized strings for API error details and narrative labels.

The API localizes user-facing error messages based on the ``Accept-Language``
HTTP header. French (fr) is the default per the project; English (en) is the
fallback. Adding a locale = add a new dict here — no router changes.

This mirrors the frontend dictionaries (frontend/src/i18n/locales/) so the
whole app speaks the same language. Corpus-agnostic: no corpus names here.
"""

from __future__ import annotations

from typing import Literal

Locale = Literal["fr", "en"]
DEFAULT_LOCALE: Locale = "fr"


_MESSAGES = {
    "fr": {
        "node_not_found": "nœud « {node_id} » introuvable dans le corpus « {corpus_id} »",
        "corpus_not_found": "corpus « {corpus_id} » introuvable",
        "tone_label": "Ton",
        "relations_heading": "Relations et événements",
        "sources_heading": "Sources",
    },
    "en": {
        "node_not_found": "node {node_id!r} not found in corpus {corpus_id!r}",
        "corpus_not_found": "corpus {corpus_id!r} not found",
        "tone_label": "Tone",
        "relations_heading": "Relations and events",
        "sources_heading": "Sources",
    },
}


def parse_accept_language(header: str | None) -> Locale:
    """Parse an Accept-Language header into a supported locale.

    Returns fr (default) when the header is absent or doesn't mention en.
    """
    if not header:
        return DEFAULT_LOCALE
    # Accept-Language looks like "fr-FR,fr;q=0.9,en;q=0.8".
    for part in header.split(","):
        tag = part.strip().split(";")[0].strip().lower()
        if tag.startswith("en"):
            return "en"
        if tag.startswith("fr"):
            return "fr"
    return DEFAULT_LOCALE


def t(key: str, *, locale: Locale = DEFAULT_LOCALE, **params: object) -> str:
    """Translate a message key for the given locale with placeholder params."""
    template = _MESSAGES[locale].get(key, _MESSAGES[DEFAULT_LOCALE].get(key, key))
    try:
        return template.format(**params)
    except (KeyError, IndexError):
        return template
