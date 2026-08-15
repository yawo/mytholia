"""Corpus loader: drive scrape → extract → build_graph from a manifest.

This is the corpus-agnostic driver (AGENTS.md §5). It reads a manifest and
runs the pipeline stages without any corpus-specific code paths. Adding a
corpus means writing a manifest (+ optional prompt override), not touching
this file (AGENTS.md §2, §13).

Usage::

    python pipeline/corpus_loader.py --corpus greek-odyssey

Produces ``data/processed/{corpus_id}/graph.json``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make ``api`` importable when run as a script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from api.models import CorpusManifest  # noqa: E402
from pipeline import build_graph, extract, scrape  # noqa: E402

log = logging.getLogger(__name__)

#: Directory containing one folder per corpus, each with a manifest.yaml.
CORPORA_DIR = _REPO_ROOT / "corpora"


def load_manifest(corpus_id: str, corpora_dir: Path | None = None) -> CorpusManifest:
    """Load a corpus manifest by id.

    Looks for ``corpora/{corpus_id}/manifest.yaml``. No corpus name is
    hardcoded here — the id comes from the caller (CLI arg or API).
    """
    corpora_dir = corpora_dir or CORPORA_DIR
    path = corpora_dir / corpus_id / "manifest.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no manifest for corpus {corpus_id!r} at {path}")
    return CorpusManifest.from_file(path)


def list_corpus_ids(corpora_dir: Path | None = None) -> list[str]:
    """Return the sorted list of corpus ids found under ``corpora/``."""
    corpora_dir = corpora_dir or CORPORA_DIR
    ids: list[str] = []
    if not corpora_dir.exists():
        return ids
    for child in sorted(corpora_dir.iterdir()):
        if child.is_dir() and (child / "manifest.yaml").exists():
            ids.append(child.name)
    return ids


def run_pipeline(corpus_id: str, corpora_dir: Path | None = None) -> Path:
    """Run the full pipeline for a corpus and return the graph.json path.

    Stages: scrape → extract → build_graph → save.
    """
    manifest = load_manifest(corpus_id, corpora_dir)
    log.info("loaded manifest for %s (%s)", manifest.id, manifest.name)

    docs = scrape.scrape(manifest)
    log.info("scrape: %d documents", len(docs))

    nodes, edges = extract.extract(manifest, docs)
    log.info("extract: %d nodes, %d edges", len(nodes), len(edges))

    graph = build_graph.build_graph(manifest, nodes, edges)
    out_path = build_graph.save_graph(graph)
    log.info("done: %s", out_path)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a corpus knowledge graph from its manifest (AGENTS.md §7)."
    )
    parser.add_argument("--corpus", default=None, help="Corpus id (kebab-case)")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available corpus ids and exit.",
    )
    parser.add_argument(
        "--corpora-dir",
        default=None,
        help="Override the corpora/ directory (default: <repo>/corpora).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    corpora_dir = Path(args.corpora_dir) if args.corpora_dir else None

    if args.list:
        for cid in list_corpus_ids(corpora_dir):
            print(cid)
        return 0

    try:
        out = run_pipeline(args.corpus, corpora_dir)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 2
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
