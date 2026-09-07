"""Instagram Graph API client for Reels / image post publishing.

Docs: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
Requires: instagram_content_publish, instagram_basic permissions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

log = logging.getLogger(__name__)

IG_API_BASE = "https://graph.instagram.com/v18.0"


@dataclass
class InstagramPublishResult:
    success: bool
    media_id: Optional[str]
    permalink: Optional[str]
    error: Optional[str]


class InstagramClient:
    """Publishes Reels and feed images to Instagram via Graph API."""

    def __init__(self, access_token: str, business_account_id: str):
        self.access_token = access_token
        self.account_id = business_account_id

    def _get(self, path: str, **params) -> dict:
        resp = requests.get(
            f"{IG_API_BASE}/{path}",
            params={"access_token": self.access_token, **params},
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: dict) -> dict:
        resp = requests.post(
            f"{IG_API_BASE}/{path}",
            params={"access_token": self.access_token},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Reels
    # ------------------------------------------------------------------

    def create_reels_container(
        self,
        video_url: str,
        caption: str,
        cover_url: str | None = None,
        share_to_feed: bool = True,
        location_id: str | None = None,
    ) -> str:
        """Step 1: create a media container. Returns container_id."""
        payload: dict = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption[:2200],
            "share_to_feed": share_to_feed,
        }
        if cover_url:
            payload["cover_url"] = cover_url
        if location_id:
            payload["location_id"] = location_id

        data = self._post(f"{self.account_id}/media", payload)
        return data["id"]

    def wait_for_container_ready(self, container_id: str, timeout: int = 300, interval: int = 10) -> bool:
        """Step 2: poll until the container is FINISHED processing."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = self._get(container_id, fields="status_code")
            status = data.get("status_code", "")
            log.info("Instagram container status: %s", status)
            if status == "FINISHED":
                return True
            if status == "ERROR":
                log.error("container processing error")
                return False
            time.sleep(interval)
        return False

    def publish_container(self, container_id: str) -> str:
        """Step 3: publish the container. Returns media_id."""
        data = self._post(f"{self.account_id}/media_publish", {"creation_id": container_id})
        return data["id"]

    def get_permalink(self, media_id: str) -> str:
        data = self._get(media_id, fields="permalink")
        return data.get("permalink", "")

    # ------------------------------------------------------------------
    # High-level publish
    # ------------------------------------------------------------------

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        tags: list[str] | None = None,
        cover_url: str | None = None,
    ) -> InstagramPublishResult:
        hashtags = " ".join(f"#{t.lstrip('#')}" for t in (tags or []))
        full_caption = f"{caption}\n\n{hashtags}".strip()

        try:
            container_id = self.create_reels_container(video_url, full_caption, cover_url)
            ready = self.wait_for_container_ready(container_id)
            if not ready:
                return InstagramPublishResult(False, None, None, "container not ready in time")

            media_id = self.publish_container(container_id)
            permalink = self.get_permalink(media_id)
            return InstagramPublishResult(True, media_id, permalink, None)

        except Exception as exc:
            log.exception("Instagram publish failed")
            return InstagramPublishResult(False, None, None, str(exc))

    # ------------------------------------------------------------------
    # Image post
    # ------------------------------------------------------------------

    def publish_image(
        self,
        image_url: str,
        caption: str,
        tags: list[str] | None = None,
    ) -> InstagramPublishResult:
        hashtags = " ".join(f"#{t.lstrip('#')}" for t in (tags or []))
        full_caption = f"{caption}\n\n{hashtags}".strip()

        try:
            data = self._post(f"{self.account_id}/media", {
                "image_url": image_url,
                "caption": full_caption[:2200],
            })
            container_id = data["id"]
            media_id = self.publish_container(container_id)
            permalink = self.get_permalink(media_id)
            return InstagramPublishResult(True, media_id, permalink, None)
        except Exception as exc:
            log.exception("Instagram image publish failed")
            return InstagramPublishResult(False, None, None, str(exc))

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_media_insights(self, media_id: str) -> dict:
        metrics = "plays,likes,comments,shares,saved,reach"
        data = self._get(f"{media_id}/insights", metric=metrics)
        return {item["name"]: item["values"][0]["value"] for item in data.get("data", [])}


class MockInstagramClient(InstagramClient):
    def __init__(self):
        self.access_token = "mock"
        self.account_id = "mock"

    def publish_reel(self, video_url, caption, **kwargs):
        log.info("[MOCK] Instagram Reel: %s | %s", video_url, caption[:60])
        return InstagramPublishResult(True, "mock-media-id", "https://www.instagram.com/reel/mock/", None)

    def publish_image(self, image_url, caption, **kwargs):
        log.info("[MOCK] Instagram Image: %s | %s", image_url, caption[:60])
        return InstagramPublishResult(True, "mock-image-id", "https://www.instagram.com/p/mock/", None)
