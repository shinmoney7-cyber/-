from __future__ import annotations

from .models import PublishResult


class MockPublisher:
    """Drop-in publisher for local testing; never makes network calls."""

    def __init__(self, platform: str = "mock", should_fail: bool = False) -> None:
        self._platform = platform
        self._should_fail = should_fail

    def publish(self, video_path: str, caption: str, product_name: str) -> PublishResult:
        if self._should_fail:
            return PublishResult(
                platform=self._platform,
                success=False,
                error="MockPublisher simulated failure",
            )
        return PublishResult(
            platform=self._platform,
            success=True,
            post_id=f"mock_{self._platform}_id",
            post_url=f"https://{self._platform}.example.com/post/mock_{self._platform}_id",
        )
