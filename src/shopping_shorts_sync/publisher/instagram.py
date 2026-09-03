"""Instagram Graph API Reels publisher.

Requires an Instagram Business/Creator account (same account used for
search/instagram.py) with the additional `instagram_content_publish`
permission on top of the search scopes. Not exercised against the live API
in this environment -- see docs/CALIBRATION.md before --live use.

Important constraint: Instagram Reels require a **publicly accessible**
video URL -- a local file path (like the one video/stitcher.py produces)
cannot be uploaded directly. The caller must first host the stitched video
somewhere public (e.g. the webapp's own /videos/<id>/<file> route once
deployed, or external storage) and pass that public HTTPS URL as
video_path.
"""
from __future__ import annotations

import time

import requests

from .models import PublishResult

_GRAPH_BASE = "https://graph.facebook.com/v19.0"
_POLL_INTERVAL_S = 5
_POLL_MAX_ATTEMPTS = 24  # 2 minutes total


class InstagramPublisher:
    """Publishes a video to Instagram as a Reel via the Instagram Graph API.

    Required credentials (reused from search/instagram.py's config fields):
        access_token: Long-lived page/system-user access token with
            instagram_basic, instagram_content_publish, and
            pages_read_engagement permissions.
        ig_user_id: Numeric IG user ID tied to the Business/Creator account
            (config.instagram_ig_user_id).
    """

    def __init__(self, access_token: str, ig_user_id: str, dry_run: bool = False) -> None:
        self._token = access_token
        self._account_id = ig_user_id
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def publish(self, video_path: str, caption: str, product_name: str) -> PublishResult:
        if self.dry_run:
            return PublishResult(
                platform="instagram",
                success=True,
                post_id="DRY_RUN_ID",
                post_url="https://www.instagram.com/p/DRY_RUN_ID/",
            )

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
