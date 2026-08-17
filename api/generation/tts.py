"""Text-to-speech: podcast script → audio.

The router lets the user choose a TTS engine per request while keeping the
implementation corpus-agnostic. Engines are considered selectable only when
all required environment values for that engine are present.
"""

from __future__ import annotations

import errno
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Literal

import httpx

if TYPE_CHECKING:
    from api.models import CorpusManifest

log = logging.getLogger(__name__)

TTSEngine = Literal["deepgram", "elevenlabs", "qwentts"]
SUPPORTED_TTS_ENGINES: tuple[TTSEngine, ...] = ("deepgram", "elevenlabs", "qwentts")
DEFAULT_TTS_ENGINE: TTSEngine = "deepgram"


def _default_podcast_cache_dir() -> Path:
    configured = os.environ.get("PODCAST_CACHE_DIR")
    if configured:
        return Path(configured)
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return _fallback_podcast_cache_dir()
    return Path("data/podcasts")


def _fallback_podcast_cache_dir() -> Path:
    return Path(tempfile.gettempdir()) / "graphodyssee" / "podcasts"


_AUDIO_DIR = _default_podcast_cache_dir() / "audio"


def _fallback_audio_dir() -> Path:
    return _fallback_podcast_cache_dir() / "audio"


def _writable_audio_dir() -> Path:
    try:
        _AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        return _AUDIO_DIR
    except OSError as exc:
        if exc.errno not in {errno.EROFS, errno.EACCES}:
            raise
        fallback = _fallback_audio_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value and value.strip() else None


def _manifest_voice_id(manifest: CorpusManifest) -> str | None:
    voice_id = manifest.voice.voice_id
    if voice_id.startswith("${") and voice_id.endswith("}"):
        return _env(voice_id[2:-1])
    return voice_id or _env("GRAPHODYSSEE_DEFAULT_VOICE_ID")


def deepgram_model_for_locale(locale: str) -> str:
    """Choose the Deepgram Aura voice model for the podcast locale.

    French podcasts use Agathe's French Aura 2 voice by default, while English
    and other locales keep the existing English default. Both can be overridden
    without code changes via environment variables.
    """
    normalized = locale.strip().lower()
    if normalized.startswith("fr"):
        return _env("DEEPGRAM_TTS_MODEL_FR") or "aura-2-agathe-fr"
    return _env("DEEPGRAM_TTS_MODEL") or "aura-asteria-en"


def _safe_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value)


def audio_path(corpus_id: str, filename: str) -> Path:
    """Resolve a generated audio filename for a corpus."""
    primary = _AUDIO_DIR / _safe_part(corpus_id) / filename
    if primary.exists():
        return primary
    return _fallback_audio_dir() / _safe_part(corpus_id) / filename


def write_audio(corpus_id: str, stem: str, extension: str, content: bytes) -> str:
    """Persist synthesized audio and return a same-origin URL for the API."""
    directory = _writable_audio_dir() / _safe_part(corpus_id)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_part(stem)}.{extension.lstrip('.')}"
    final_path = directory / filename
    with NamedTemporaryFile("wb", dir=directory, delete=False) as fh:
        fh.write(content)
        tmp_name = fh.name
    Path(tmp_name).replace(final_path)
    return f"/api/podcast/audio/{_safe_part(corpus_id)}/{filename}"


class TTSProvider(ABC):
    """Interface for TTS providers (AGENTS.md §6, §12)."""

    engine: TTSEngine

    @abstractmethod
    def synthesize(
        self, manifest: CorpusManifest, script: str, output_stem: str, locale: str
    ) -> str | None:
        """Return an audio URL/blob reference, or None if unavailable."""
        raise NotImplementedError


class DeepgramProvider(TTSProvider):
    """Deepgram Aura text-to-speech provider."""

    engine: TTSEngine = "deepgram"

    def synthesize(
        self, manifest: CorpusManifest, script: str, output_stem: str, locale: str
    ) -> str | None:
        from deepgram import DeepgramClient

        api_key = _env("DEEPGRAM_API_KEY")
        if not api_key:
            log.info("DEEPGRAM_API_KEY not set; Deepgram TTS skipped")
            return None

        model = deepgram_model_for_locale(locale)
        deepgram = DeepgramClient(api_key=api_key)
        chunks = deepgram.speak.v1.audio.generate(text=script, model=model)
        content = b"".join(bytes(chunk) for chunk in chunks)
        return write_audio(manifest.id, output_stem, "mp3", content)


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs TTS. Voice id comes from manifest/env and must be authorized."""

    engine: TTSEngine = "elevenlabs"

    def synthesize(
        self, manifest: CorpusManifest, script: str, output_stem: str, locale: str
    ) -> str | None:
        api_key = _env("ELEVENLABS_API_KEY")
        voice_id = _manifest_voice_id(manifest)
        if not api_key or not voice_id:
            log.info("ElevenLabs env incomplete; TTS skipped")
            return None

        model_id = _env("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                url,
                headers={"xi-api-key": api_key, "Accept": "audio/mpeg"},
                json={"text": script, "model_id": model_id},
            )
            response.raise_for_status()
        return write_audio(manifest.id, output_stem, "mp3", response.content)


class QwenTTSProvider(TTSProvider):
    """Qwen TTS via an OpenAI-compatible audio speech endpoint."""

    engine: TTSEngine = "qwentts"

    def synthesize(
        self, manifest: CorpusManifest, script: str, output_stem: str, locale: str
    ) -> str | None:
        api_key = _env("QWEN_TTS_API_KEY")
        base_url = (
            _env("QWEN_TTS_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ).rstrip("/")
        if not api_key:
            log.info("QWEN_TTS_API_KEY not set; Qwen TTS skipped")
            return None

        model = _env("QWEN_TTS_MODEL") or "qwen-tts"
        voice = _env("QWEN_TTS_VOICE") or _manifest_voice_id(manifest) or "Cherry"
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{base_url}/audio/speech",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "voice": voice, "input": script},
            )
            response.raise_for_status()
        return write_audio(manifest.id, output_stem, "mp3", response.content)


class StubTTSProvider(TTSProvider):
    """Offline stub used only when no live engine is fully configured."""

    engine: TTSEngine = "deepgram"

    def synthesize(
        self, manifest: CorpusManifest, script: str, output_stem: str, locale: str
    ) -> str | None:
        return f"stub://tts/{manifest.id}/{output_stem}.wav"


_PROVIDER_BY_ENGINE: dict[TTSEngine, type[TTSProvider]] = {
    "deepgram": DeepgramProvider,
    "elevenlabs": ElevenLabsProvider,
    "qwentts": QwenTTSProvider,
}


def engine_available(engine: TTSEngine, manifest: CorpusManifest) -> bool:
    """Return whether all required env values are present for an engine."""
    if engine == "deepgram":
        return _env("DEEPGRAM_API_KEY") is not None
    if engine == "elevenlabs":
        return _env("ELEVENLABS_API_KEY") is not None and _manifest_voice_id(manifest) is not None
    if engine == "qwentts":
        return _env("QWEN_TTS_API_KEY") is not None
    return False


def available_engines(manifest: CorpusManifest) -> list[TTSEngine]:
    """List engines that are fully configured; Deepgram sorts first as default."""
    return [engine for engine in SUPPORTED_TTS_ENGINES if engine_available(engine, manifest)]


def normalize_engine(engine: str | None) -> TTSEngine | None:
    """Normalize user input and reject unsupported engines."""
    if engine is None:
        return None
    normalized = engine.strip().lower().replace("_", "")
    if normalized == "qwen":
        normalized = "qwentts"
    if normalized in SUPPORTED_TTS_ENGINES:
        return normalized  # type: ignore[return-value]
    return None


def default_engine_for(manifest: CorpusManifest) -> TTSEngine:
    """Pick Deepgram when configured, then manifest/default configured engines."""
    if engine_available(DEFAULT_TTS_ENGINE, manifest):
        return DEFAULT_TTS_ENGINE
    manifest_engine = normalize_engine(manifest.voice.provider)
    if manifest_engine and engine_available(manifest_engine, manifest):
        return manifest_engine
    configured = available_engines(manifest)
    return configured[0] if configured else DEFAULT_TTS_ENGINE


def provider_for(manifest: CorpusManifest, engine: str | None = None) -> TTSProvider:
    """Pick a TTS provider from a user choice, manifest, and configured env."""
    selected = normalize_engine(engine) or default_engine_for(manifest)
    if engine_available(selected, manifest):
        return _PROVIDER_BY_ENGINE[selected]()
    stub = StubTTSProvider()
    stub.engine = selected
    return stub
