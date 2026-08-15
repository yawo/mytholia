"""Text-to-speech: script → audio via ElevenLabs or Qwen TTS.

Corpus-agnostic (AGENTS.md §6). The provider is selected from the corpus
manifest's ``voice`` block — never hardcoded.

Sprint 0 stub: returns a placeholder audio URL when no provider key is
configured, so ``/podcast`` is exercisable offline. Real TTS is wired behind
the same ``TTSProvider`` interface in later sprints (AGENTS.md §13 cost
control; voice-cloning consent handled out of repo, AGENTS.md §12).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.models import CorpusManifest

log = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Interface for TTS providers (AGENTS.md §6, §12)."""

    @abstractmethod
    def synthesize(self, manifest: CorpusManifest, script: str) -> str | None:
        """Return an audio URL/blob reference, or None if unavailable."""
        raise NotImplementedError


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs TTS (primary). Voice id comes from the manifest
    (``GRAPHODYSSEE_DEFAULT_VOICE_ID``), pointing to an already-authorized
    voice — never generated ad hoc (AGENTS.md §12)."""

    def synthesize(self, manifest: CorpusManifest, script: str) -> str | None:
        import os

        if not os.environ.get("ELEVENLABS_API_KEY"):
            log.info("ELEVENLABS_API_KEY not set; TTS skipped")
            return None
        # Real ElevenLabs call wired up in later sprint behind the same interface.
        raise NotImplementedError("Live ElevenLabs TTS is wired up in a later sprint")


class QwenTTSProvider(TTSProvider):
    """Qwen TTS (local/cheaper fallback). Wired up in a later sprint."""

    def synthesize(self, manifest: CorpusManifest, script: str) -> str | None:
        import os

        if not os.environ.get("QWEN_TTS_API_KEY"):
            log.info("QWEN_TTS_API_KEY not set; TTS skipped")
            return None
        raise NotImplementedError("Live Qwen TTS is wired up in a later sprint")


class StubTTSProvider(TTSProvider):
    """Offline stub: returns a placeholder audio URL so /podcast is exercisable."""

    def synthesize(self, manifest: CorpusManifest, script: str) -> str | None:
        return f"stub://tts/{manifest.id}/{hash(script) & 0xFFFFFFFF:08x}.wav"


def provider_for(manifest: CorpusManifest) -> TTSProvider:
    """Pick a TTS provider from the manifest's ``voice`` block (corpus-agnostic)."""
    import os

    provider = manifest.voice.provider.lower()
    if provider == "elevenlabs" and os.environ.get("ELEVENLABS_API_KEY"):
        return ElevenLabsProvider()
    if provider == "qwen" and os.environ.get("QWEN_TTS_API_KEY"):
        return QwenTTSProvider()
    # Fallback: stub so the endpoint works without paid calls (Sprint 0).
    return StubTTSProvider()
