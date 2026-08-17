"""Podcast router: /podcast (AGENTS.md §8 sprint 4).

Subgraph → narrative (respecting ``narrative_style`` from the manifest) → TTS
provider from the manifest → returns audio URL/blob. Corpus is always a param
— no corpus-specific logic here (AGENTS.md §2). Error messages and the script
are localized via the Accept-Language header (api.i18n).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse

from api.generation.narrative import generator_for
from api.generation.podcast_cache import load_cached_podcast, save_cached_podcast
from api.generation.tts import (
    SUPPORTED_TTS_ENGINES,
    audio_path,
    available_engines,
    default_engine_for,
    engine_available,
    normalize_engine,
    provider_for,
)
from api.i18n import parse_accept_language, t
from api.models import PodcastRequest, PodcastResponse, TTSEnginesResponse, TTSEngineStatus
from api.retrieval.graph_store import get_store
from pipeline.corpus_loader import load_manifest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/podcast", response_model=PodcastResponse, tags=["podcast"])
def generate_podcast(
    req: PodcastRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> PodcastResponse:
    """Generate a podcast-style narration for an entity in a corpus.

    Pipeline: retrieve subgraph → narrative script → TTS → response.
    The script is grounded in the subgraph's ``source_refs``; claims that
    can't be grounded are omitted (AGENTS.md §10).
    """
    locale = parse_accept_language(accept_language)
    try:
        manifest = load_manifest(req.corpus_id)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=t("corpus_not_found", locale=locale, corpus_id=req.corpus_id),
        ) from e

    store = get_store()
    node = store.get_node(req.corpus_id, req.entity_id)
    if node is None:
        raise HTTPException(
            status_code=404,
            detail=t(
                "node_not_found",
                locale=locale,
                node_id=req.entity_id,
                corpus_id=req.corpus_id,
            ),
        )

    selected_engine = normalize_engine(req.engine)
    if req.engine is not None and selected_engine is None:
        raise HTTPException(status_code=400, detail="Unsupported TTS engine")
    selected_engine = selected_engine or default_engine_for(manifest)
    configured_engines = available_engines(manifest)

    length = req.length_seconds or manifest.narrative_style.length_seconds
    if not req.force:
        cached = load_cached_podcast(req.corpus_id, req.entity_id, locale, length, selected_engine)
        if cached is not None:
            return cached.model_copy(update={"cached": True})

    subgraph = store.get_subgraph(req.corpus_id, req.entity_id, radius=1)
    generator = generator_for(manifest)
    script = generator.generate(manifest, node, subgraph, locale=locale)

    tts = provider_for(manifest, selected_engine)
    try:
        audio_url = tts.synthesize(
            manifest,
            script,
            f"{locale}-{length}-{selected_engine}-{abs(hash(script)) & 0xFFFFFFFF:08x}",
        )
    except NotImplementedError:
        log.info("[%s] TTS provider not yet implemented; returning script only", manifest.id)
        audio_url = None

    response = PodcastResponse(
        corpus_id=req.corpus_id,
        entity_id=req.entity_id,
        script=script,
        audio_url=audio_url,
        length_seconds=length,
        engine=selected_engine,
        available_engines=configured_engines,
        cached=False,
    )
    save_cached_podcast(response, locale)
    return response


@router.get("/podcast/engines", response_model=TTSEnginesResponse, tags=["podcast"])
def list_podcast_engines(corpus_id: str) -> TTSEnginesResponse:
    """List TTS engines available for a corpus based on required environment keys."""
    try:
        manifest = load_manifest(corpus_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Corpus not found: {corpus_id}") from e

    default_engine = default_engine_for(manifest)
    return TTSEnginesResponse(
        corpus_id=corpus_id,
        engines=[
            TTSEngineStatus(
                engine=engine,
                configured=engine_available(engine, manifest),
                default=engine == default_engine,
            )
            for engine in SUPPORTED_TTS_ENGINES
        ],
    )


@router.get("/podcast/audio/{corpus_id}/{filename}", response_model=None, tags=["podcast"])
def get_podcast_audio(corpus_id: str, filename: str) -> FileResponse:
    """Serve generated podcast audio files from the podcast cache directory."""
    path = audio_path(corpus_id, filename)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/mpeg")
