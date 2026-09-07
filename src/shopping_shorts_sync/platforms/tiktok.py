"""TikTok Content Posting API v2 client.

Docs: https://developers.tiktok.com/doc/content-posting-api-get-started
Scope needed: video.publish, video.upload
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


@dataclass
class TikTokPublishResult:
    success: bool
    publish_id: Optional[str]
    share_url: Optional[str]
    error: Optional[str]


class TikTokClient:
    """Publishes vertical video to TikTok via Content Posting API."""

    def __init__(self, access_token: str, client_key: str = "", client_secret: str = ""):
        self.access_token = access_token
        self.client_key = client_key
        self.client_secret = client_secret
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        })

    # ------------------------------------------------------------------
    # Creator info
    # ------------------------------------------------------------------

    def get_creator_info(self) -> dict:
        resp = self._session.post(
            f"{TIKTOK_API_BASE}/post/publish/creator_info/query/",
            json={},
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Direct-post video (file < 4 GB, < 60 min)
    # ------------------------------------------------------------------

    def init_video_upload(
        self,
        video_path: str,
        title: str,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        duet_disabled: bool = False,
        stitch_disabled: bool = False,
        comment_disabled: bool = False,
    ) -> dict:
        """Step 1: initialise an upload and get upload_url."""
        size = Path(video_path).stat().st_size
        payload = {
            "post_info": {
                "title": title[:2200],
                "privacy_level": privacy_level,
                "disable_duet": duet_disabled,
                "disable_stitch": stitch_disabled,
                "disable_comment": comment_disabled,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        }
        resp = self._session.post(
            f"{TIKTOK_API_BASE}/post/publish/video/init/",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def upload_video_chunk(self, upload_url: str, video_path: str) -> None:
        """Step 2: PUT the binary to the signed upload URL."""
        path = Path(video_path)
        size = path.stat().st_size
        with path.open("rb") as fh:
            headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{size - 1}/{size}",
                "Content-Length": str(size),
            }
            resp = requests.put(upload_url, data=fh, headers=headers)
            resp.raise_for_status()
        log.info("video chunk uploaded to TikTok")

    def check_publish_status(self, publish_id: str) -> dict:
        resp = self._session.post(
            f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
            json={"publish_id": publish_id},
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # High-level publish
    # ------------------------------------------------------------------

    def publish_video(
        self,
        video_path: str,
        title: str,
        tags: list[str] | None = None,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        poll_seconds: int = 30,
        max_polls: int = 20,
    ) -> TikTokPublishResult:
        hashtags = " ".join(f"#{t.lstrip('#')}" for t in (tags or []))
        full_title = f"{title} {hashtags}".strip()

        try:
            init_data = self.init_video_upload(video_path, full_title, privacy_level)
            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"]["publish_id"]

            self.upload_video_chunk(upload_url, video_path)

            for _ in range(max_polls):
                status_data = self.check_publish_status(publish_id)
                status = status_data.get("data", {}).get("status", "")
                log.info("TikTok publish status: %s", status)
                if status == "PUBLISH_COMPLETE":
                    share_url = status_data["data"].get("publicaly_available_post_id", [None])[0]
                    return TikTokPublishResult(True, publish_id, share_url, None)
                if status in ("FAILED", "CANCELLED"):
                    err = status_data["data"].get("fail_reason", "unknown")
                    return TikTokPublishResult(False, publish_id, None, err)
                time.sleep(poll_seconds)

            return TikTokPublishResult(False, publish_id, None, "timed out waiting for publish")

        except Exception as exc:
            log.exception("TikTok publish failed")
            return TikTokPublishResult(False, None, None, str(exc))

    # ------------------------------------------------------------------
    # Trending music helper
    # ------------------------------------------------------------------

    def get_trending_music(self, region: str = "KR", limit: int = 20) -> list[dict]:
        """Returns trending music for the given region (uses unofficial endpoint)."""
        try:
            resp = requests.get(
                "https://www.tiktok.com/api/recommend/music/",
                params={"region": region, "count": limit},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("music", [])
        except Exception as exc:
            log.warning("could not fetch TikTok trending music: %s", exc)
            return []


class MockTikTokClient(TikTokClient):
    def __init__(self):
        self.access_token = "mock"
        self.client_key = "mock"
        self.client_secret = "mock"

    def publish_video(self, video_path, title, tags=None, **kwargs):
        log.info("[MOCK] TikTok publish: %s | %s | tags=%s", video_path, title, tags)
        return TikTokPublishResult(True, "mock-publish-id", "https://tiktok.com/@mock/video/0", None)

    def get_creator_info(self):
        return {"data": {"creator_nickname": "mock_user"}}
