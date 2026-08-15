"""Podcast router: /podcast (AGENTS.md §8 sprint 4).

Subgraph → narrative (respecting ``narrative_style`` from the manifest) → TTS
provider from the manifest → returns audio URL/blob. Corpus is always a param
— no corpus-specific logic here (AGENTS.md §2).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.generation.narrative import generator_for
from api.generation.tts import provider_for
from api.models import PodcastRequest, PodcastResponse
from api.retrieval.graph_store import get_store
from pipeline.corpus_loader import load_manifest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/podcast", response_model=PodcastResponse, tags=["podcast"])
def generate_podcast(req: PodcastRequest) -> PodcastResponse:
    """Generate a podcast-style narration for an entity in a corpus.

    Pipeline: retrieve subgraph → narrative script → TTS → response.
    The script is grounded in the subgraph's ``source_refs``; claims that
    can't be grounded are omitted (AGENTS.md §10).
    """
    try:
        manifest = load_manifest(req.corpus_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    store = get_store()
    node = store.get_node(req.corpus_id, req.entity_id)
    if node is None:
        raise HTTPException(
            status_code=404,
            detail=f"node {req.entity_id!r} not found in corpus {req.corpus_id!r}",
        )

    subgraph = store.get_subgraph(req.corpus_id, req.entity_id, radius=1)
    generator = generator_for(manifest)
    script = generator.generate(manifest, node, subgraph)

    tts = provider_for(manifest)
    try:
        audio_url = tts.synthesize(manifest, script)
    except NotImplementedError:
        log.info("[%s] TTS provider not yet implemented; returning script only", manifest.id)
        audio_url = None

    length = req.length_seconds or manifest.narrative_style.length_seconds
    return PodcastResponse(
        corpus_id=req.corpus_id,
        entity_id=req.entity_id,
        script=script,
        audio_url=audio_url,
        length_seconds=length,
    )
