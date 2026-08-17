"""Filesystem cache for generated podcast scripts and audio references.

The cache is keyed by corpus, entity, locale, requested length, and TTS engine so
repeated requests can reuse both generated text and the synthesized audio reference.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import tempfile
from pathlib import Path
from tempfile import NamedTemporaryFile

from api.i18n import Locale
from api.models import PodcastResponse


def default_podcast_cache_dir() -> Path:
    """Return the default writable podcast cache directory.

    Serverless deployments such as Vercel and AWS Lambda expose the application
    bundle as read-only, so generated podcast cache files must live under the
    platform temporary directory unless an explicit ``PODCAST_CACHE_DIR`` is set.
    """
    configured = os.environ.get("PODCAST_CACHE_DIR")
    if configured:
        return Path(configured)
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return Path(tempfile.gettempdir()) / "graphodyssee" / "podcasts"
    return Path("data/podcasts")


PODCAST_CACHE_DIR = default_podcast_cache_dir()


def fallback_podcast_cache_dir() -> Path:
    """Return the platform temp podcast cache directory."""
    return Path(tempfile.gettempdir()) / "graphodyssee" / "podcasts"


def writable_podcast_cache_dir() -> Path:
    """Return a podcast cache root that can be created in this runtime."""
    try:
        PODCAST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return PODCAST_CACHE_DIR
    except OSError as exc:
        if exc.errno not in {errno.EROFS, errno.EACCES}:
            raise
        fallback = fallback_podcast_cache_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _safe_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value)


def cache_path(
    corpus_id: str, entity_id: str, locale: Locale, length_seconds: int, engine: str = "deepgram"
) -> Path:
    """Return the JSON cache path for a podcast request."""
    entity_hash = hashlib.sha256(entity_id.encode("utf-8")).hexdigest()[:16]
    filename = f"{_safe_part(locale)}-{length_seconds}-{_safe_part(engine)}-{entity_hash}.json"
    primary = PODCAST_CACHE_DIR / _safe_part(corpus_id) / filename
    if primary.exists():
        return primary
    return fallback_podcast_cache_dir() / _safe_part(corpus_id) / filename


def load_cached_podcast(
    corpus_id: str, entity_id: str, locale: Locale, length_seconds: int, engine: str = "deepgram"
) -> PodcastResponse | None:
    """Load a cached podcast response, if present and still valid for the request."""
    path = cache_path(corpus_id, entity_id, locale, length_seconds, engine)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    response = PodcastResponse.model_validate(data)
    if response.corpus_id != corpus_id or response.entity_id != entity_id:
        return None
    return response


def save_cached_podcast(response: PodcastResponse, locale: Locale) -> Path:
    """Persist a podcast response atomically and return its cache path."""
    path = cache_path(
        response.corpus_id, response.entity_id, locale, response.length_seconds, response.engine
    )
    cache_root = writable_podcast_cache_dir()
    if not path.exists():
        path = cache_root / _safe_part(response.corpus_id) / path.name
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = response.model_dump(mode="json")
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        tmp_name = fh.name
    Path(tmp_name).replace(path)
    return path
