from __future__ import annotations

import hashlib

from .client import PostResult


class MockInstagramClient:
    """Dry-run Instagram client that returns deterministic fake media IDs."""

    def post_image(
        self,
        product_id: str,
        image_url: str,
        caption: str,
        scheduled_publish_time: int | None = None,
    ) -> PostResult:
        digest = hashlib.sha256(product_id.encode()).hexdigest()[:12]
        media_id = f"mock-ig-{digest}"
        return PostResult(
            product_id=product_id,
            media_id=media_id,
            permalink=f"https://www.instagram.com/p/{digest}/",
            scheduled_publish_time=scheduled_publish_time,
        )
