from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class VideoApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoJob:
    request_id: str
    status: str  # normalized: "pending" | "completed" | "failed"
    video_url: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "completed" and bool(self.video_url)


class VideoClient(Protocol):
    """Image-to-video provider. ``prepare_image`` turns a product thumbnail
    (URL or local path) into whatever the provider's submit call accepts."""

    provider: str

    def prepare_image(self, image: str) -> str: ...

    def submit(self, image_ref: str, prompt: str, duration: int) -> str: ...

    def status(self, request_id: str) -> VideoJob: ...

    def wait(self, request_id: str) -> VideoJob: ...
