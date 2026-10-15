from __future__ import annotations

import hashlib

from .base import VideoJob


class MockVideoClient:
    """Drop-in stand-in for the real video clients. No network, no credits.

    Request ids and video URLs are derived from the inputs, so re-running the
    same product/script produces the same fake output.
    """

    def __init__(self, provider: str = "mock"):
        self.provider = provider

    def prepare_image(self, image: str) -> str:
        return image

    def submit(self, image_ref: str, prompt: str, duration: int) -> str:
        digest = hashlib.sha256(f"{self.provider}|{image_ref}|{prompt}|{duration}".encode("utf-8")).hexdigest()[:12]
        return f"mock-{self.provider}-{digest}"

    def status(self, request_id: str) -> VideoJob:
        return VideoJob(
            request_id=request_id,
            status="completed",
            video_url=f"https://cdn.example.com/mock-videos/{request_id}.mp4",
        )

    def wait(self, request_id: str) -> VideoJob:
        return self.status(request_id)
