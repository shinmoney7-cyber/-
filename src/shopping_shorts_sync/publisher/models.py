from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class PublishResult:
    platform: str
    success: bool
    post_url: str | None = None
    post_id: str | None = None
    error: str | None = None


class VideoPublisherProtocol(Protocol):
    def publish(self, video_path: str, caption: str, product_name: str) -> PublishResult: ...
