from __future__ import annotations

import hashlib

from .models import TTSResult


class MockTypecastClient:
    """Drop-in stand-in for TypecastClient. No network, no API key.

    Produces a deterministic fake audio URL so repeated runs against the
    same text+actor are stable (useful for state/idempotency testing).
    """

    def synthesize(self, text: str, actor_id: str, speed: float = 1.2) -> TTSResult:
        digest = hashlib.sha256(f"{actor_id}:{speed}:{text}".encode("utf-8")).hexdigest()[:10]
        return TTSResult(audio_url=f"https://example.com/mock-tts/{digest}.mp3", actor_id=actor_id)
