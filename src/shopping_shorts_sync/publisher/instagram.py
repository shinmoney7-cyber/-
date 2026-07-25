from __future__ import annotations

import time

import requests

from .models import PublishResult

_GRAPH_BASE = "https://graph.facebook.com/v19.0"
_POLL_INTERVAL_S = 5
_POLL_MAX_ATTEMPTS = 24  # 2 minutes total


class InstagramPublisher:
    """Publishes a video to Instagram as a Reel via the Instagram Graph API.

    Required env vars:
        INSTAGRAM_ACCESS_TOKEN: Long-lived page/system-user access token with
            instagram_basic, instagram_content_publish, and pages_read_engagement
            permissions.
        INSTAGRAM_BUSINESS_ACCOUNT_ID: Numeric IG user ID tied to the Business/
            Creator account.

    Note:
        Instagram Reels require a **publicly accessible** video URL — local files
        cannot be uploaded directly. Pass the Higgsfield CDN URL returned from the
        video generation step as ``video_path``. The ``video_path`` parameter name
        is kept consistent with VideoPublisherProtocol but must be a public HTTPS URL.
    """

    def __init__(self, access_token: str, business_account_id: str) -> None:
        self._token = access_token
        self._account_id = business_account_id

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def publish(self, video_path: str, caption: str, product_name: str) -> PublishResult:
        try:
            return self._publish(video_path, caption)
        except requests.RequestException as exc:
            return PublishResult(platform="instagram", success=False, error=str(exc))
        except _InstagramAPIError as exc:
            return PublishResult(platform="instagram", success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _params(self, extra: dict | None = None) -> dict[str, str]:
        base = {"access_token": self._token}
        if extra:
            base.update(extra)
        return base

    def _publish(self, video_url: str, caption: str) -> PublishResult:
        creation_id = self._create_container(video_url, caption)
        self._poll_until_ready(creation_id)
        media_id = self._publish_container(creation_id)

        post_url = f"https://www.instagram.com/p/{media_id}/"
        return PublishResult(
            platform="instagram",
            success=True,
            post_id=media_id,
            post_url=post_url,
        )

    def _create_container(self, video_url: str, caption: str) -> str:
        url = f"{_GRAPH_BASE}/{self._account_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": True,
        }
        resp = requests.post(url, params=self._params(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._raise_for_graph_error(data)
        return data["id"]

    def _poll_until_ready(self, creation_id: str) -> None:
        url = f"{_GRAPH_BASE}/{creation_id}"
        for _ in range(_POLL_MAX_ATTEMPTS):
            resp = requests.get(
                url,
                params=self._params({"fields": "status_code,status"}),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self._raise_for_graph_error(data)

            status_code = data.get("status_code", "")
            if status_code == "FINISHED":
                return
            if status_code == "ERROR":
                raise _InstagramAPIError(f"Media container failed: {data.get('status')}")

            time.sleep(_POLL_INTERVAL_S)

        raise _InstagramAPIError("Timed out waiting for Instagram media container to finish processing")

    def _publish_container(self, creation_id: str) -> str:
        url = f"{_GRAPH_BASE}/{self._account_id}/media_publish"
        resp = requests.post(
            url,
            params=self._params({"creation_id": creation_id}),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._raise_for_graph_error(data)
        return data["id"]

    @staticmethod
    def _raise_for_graph_error(data: dict) -> None:
        if "error" in data:
            err = data["error"]
            raise _InstagramAPIError(f"{err.get('code')} {err.get('type')}: {err.get('message')}")


class _InstagramAPIError(Exception):
    pass
