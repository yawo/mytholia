"""Scrape stage: fetch raw source text for a corpus.

Corpus-agnostic. The strategy (web_scrape vs search_augmented vs a custom
``SourceStrategy``) is selected from the manifest — never hardcoded (AGENTS.md
§5, §13).

In Sprint 0 this is a runnable stub: it resolves the source strategy from the
manifest, and where real scraping tools (crawl4ai, scrapling) or search APIs
(tavily, perplexity) are unavailable, it falls back to cached fixture text so
the pipeline can run end-to-end on a tiny fixture without network calls
(AGENTS.md §13 cost control).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.models import CorpusManifest

log = logging.getLogger(__name__)

#: Root for cached raw text (AGENTS.md §3, §12). gitignored except .gitkeep.
DATA_RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


class SourceStrategy(ABC):
    """Interface for corpus source strategies (AGENTS.md §5).

    A corpus selects a strategy implementation via its manifest's ``sources``
    block. New sourcing logic (e.g. oral-tradition sourcing for Vodou) lives
    behind a new implementation of this interface, selected by the manifest —
    it does not fork the pipeline file.
    """

    @abstractmethod
    def fetch(self, manifest: CorpusManifest) -> list[dict]:
        """Return a list of ``{"text": str, "url": str | None}`` documents.

        Each document must carry enough provenance to populate ``source_refs``
        downstream. Strategies that cannot ground a claim should return no
        document rather than invent one (AGENTS.md §10).
        """
        raise NotImplementedError


class WebScrapeStrategy(SourceStrategy):
    """Web scraping via crawl4ai or scrapling.

    In Sprint 0 the real scrapers are optional dependencies. If unavailable,
    this strategy logs and returns an empty list so the pipeline can fall back
    to fixture text. Real scraping is wired up in later sprints behind the same
    interface.
    """

    def __init__(self, tool: str = "crawl4ai", seed_urls: list[str] | None = None) -> None:
        self.tool = tool
        self.seed_urls = list(seed_urls or [])

    def fetch(self, manifest: CorpusManifest) -> list[dict]:
        if not self.seed_urls:
            log.info("[%s] web_scrape strategy has no seed_urls", manifest.id)
            return []
        # Sprint 0: do not perform real network scraping in the hot path or
        # during tests (AGENTS.md §13 cost control). Real scraping is wired up
        # in later sprints behind the same interface.
        try:
            if self.tool == "crawl4ai":
                _maybe_crawl4ai()  # raises ImportError if not installed
            elif self.tool == "scrapling":
                _maybe_scrapling()
            else:
                log.warning("[%s] unknown scrape tool %r; skipping", manifest.id, self.tool)
                return []
        except ImportError:
            log.info(
                "[%s] scrape tool %r not installed; skipping live scrape "
                "(use cached fixtures in tests)",
                manifest.id,
                self.tool,
            )
            return []
        # When a real scraper is present, it would fetch here. Left to later
        # sprints; the interface and manifest-driven selection are stable.
        log.info("[%s] live scraping not yet implemented in Sprint 0", manifest.id)
        return []


class SearchAugmentedStrategy(SourceStrategy):
    """Search-augmented sourcing via Tavily or Perplexity Sonar.

    Sprint 0 stub: returns empty docs unless the API key is present and a real
    client is available. Keeps the pipeline runnable without paid calls
    (AGENTS.md §13).
    """

    def __init__(self, tool: str = "tavily", queries: list[str] | None = None) -> None:
        self.tool = tool
        self.queries = list(queries or [])

    def fetch(self, manifest: CorpusManifest) -> list[dict]:
        if not self.queries:
            return []
        log.info(
            (
            "[%s] search_augmented strategy (%s) has %d queries; "
            "live search deferred to later sprint"
        ),
            manifest.id,
            self.tool,
            len(self.queries),
        )
        return []


class FixtureSourceStrategy(SourceStrategy):
    """Reads cached raw text from ``data/raw/{corpus_id}/``.

    Used so the pipeline can run end-to-end on a tiny fixture without network
    calls (AGENTS.md §13). This is a first-class strategy, not a test hack:
    ``data/raw/`` is the documented cache location (AGENTS.md §3, §12).
    """

    def __init__(self, corpus_id: str, raw_dir: Path | None = None) -> None:
        self.corpus_id = corpus_id
        self.raw_dir = raw_dir or (DATA_RAW_DIR / corpus_id)

    def fetch(self, manifest: CorpusManifest) -> list[dict]:
        docs: list[dict] = []
        if not self.raw_dir.exists():
            log.info("[%s] no cached raw text at %s", manifest.id, self.raw_dir)
            return docs
        for p in sorted(self.raw_dir.glob("*.txt")):
            text = p.read_text(encoding="utf-8")
            docs.append({"text": text, "url": None, "filename": p.name})
        log.info(
            "[%s] loaded %d cached raw documents from %s", manifest.id, len(docs), self.raw_dir
        )
        return docs


def strategy_for(manifest: CorpusManifest) -> SourceStrategy:
    """Pick a source strategy for a manifest.

    Selects the first declared source by type. Keeps the manifest-driven,
    corpus-agnostic flow (AGENTS.md §5).
    """
    sources = manifest.sources_parsed()
    if not sources:
        return FixtureSourceStrategy(manifest.id)
    for s in sources:
        stype = getattr(s, "type", "")
        if stype == "web_scrape":
            return WebScrapeStrategy(tool=s.tool, seed_urls=s.seed_urls)  # type: ignore[attr-defined]
        if stype == "search_augmented":
            return SearchAugmentedStrategy(tool=s.tool, queries=s.queries)  # type: ignore[attr-defined]
    return FixtureSourceStrategy(manifest.id)


def scrape(manifest: CorpusManifest) -> list[dict]:
    """Run the scrape stage for a corpus and return raw documents.

    Documents are dicts of ``{"text": str, "url": str | None, ...}``.
    """
    strat = strategy_for(manifest)
    docs = strat.fetch(manifest)
    if not docs:
        # Fall back to cached fixture text so the pipeline is runnable on a
        # tiny fixture even when no real source is configured (Sprint 0).
        docs = FixtureSourceStrategy(manifest.id).fetch(manifest)
    return docs


# --- optional-dependency probes --------------------------------------------


def _maybe_crawl4ai() -> None:
    import crawl4ai  # noqa: F401


def _maybe_scrapling() -> None:
    import scrapling  # noqa: F401
