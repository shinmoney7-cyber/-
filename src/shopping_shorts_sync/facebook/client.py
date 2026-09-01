from __future__ import annotations

import datetime
from dataclasses import dataclass

import requests

GRAPH_API = "https://graph.facebook.com/v22.0"

KST = datetime.timezone(datetime.timedelta(hours=9))


@dataclass(frozen=True)
class FBPostResult:
    product_id: str
    post_id: str | None
    scheduled_publish_time: int | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.post_id is not None and self.error is None

    @property
    def is_scheduled(self) -> bool:
        return self.scheduled_publish_time is not None


class FacebookApiError(RuntimeError):
    pass


class FacebookPageClient:
    """Posts or schedules a photo post to a Facebook Page via the Graph API.

    Requires a Page Access Token with pages_manage_posts and
    pages_read_engagement permissions.
    See docs/CALIBRATION.md for token setup steps.
    """

    def __init__(self, page_id: str, page_access_token: str, timeout: float = 30.0):
        if not page_id or not page_access_token:
            raise FacebookApiError(
                "Facebook page_id and page_access_token are required in live mode"
            )
        self.page_id = page_id
        self.page_access_token = page_access_token
        self.timeout = timeout

    def post_photo(
        self,
        product_id: str,
        image_url: str,
        caption: str,
        scheduled_publish_time: int | None = None,
    ) -> FBPostResult:
        params: dict = {
            "url": image_url,
            "message": caption,
            "access_token": self.page_access_token,
        }
        if scheduled_publish_time is not None:
            params["published"] = "false"
            params["scheduled_publish_time"] = str(scheduled_publish_time)

        resp = requests.post(
            f"{GRAPH_API}/{self.page_id}/photos",
            params=params,
            timeout=self.timeout,
        )
        body = resp.json()
        if not resp.ok or "id" not in body:
            error = body.get("error", {}).get("message", str(body))
            return FBPostResult(product_id=product_id, post_id=None, error=error)

        return FBPostResult(
            product_id=product_id,
            post_id=body["id"],
            scheduled_publish_time=scheduled_publish_time,
        )


class MockFacebookPageClient:
    """Dry-run Facebook client that returns deterministic fake post IDs."""

    def post_photo(
        self,
        product_id: str,
        image_url: str,
        caption: str,
        scheduled_publish_time: int | None = None,
    ) -> FBPostResult:
        import hashlib
        digest = hashlib.sha256(product_id.encode()).hexdigest()[:12]
        return FBPostResult(
            product_id=product_id,
            post_id=f"mock-fb-{digest}",
            scheduled_publish_time=scheduled_publish_time,
        )
