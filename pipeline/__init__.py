"""Package marker for the pipeline.

The pipeline is corpus-agnostic (AGENTS.md §2, §5). It reads a
``CorpusManifest`` and drives scrape → extract → build_graph generically via
``corpus_loader.py``. No corpus name, entity name, or relation label is
hardcoded anywhere in this package.
"""
