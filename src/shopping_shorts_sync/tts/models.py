from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TTSResult:
    audio_url: str
    actor_id: str
