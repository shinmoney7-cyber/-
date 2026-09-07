"""YouTube Data API v3 client for video uploads.

Docs: https://developers.google.com/youtube/v3/guides/uploading_a_video
OAuth scopes: https://www.googleapis.com/auth/youtube.upload
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

YT_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_API_BASE = "https://www.googleapis.com/youtube/v3"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass
class YouTubeUploadResult:
    success: bool
    video_id: Optional[str]
    url: Optional[str]
    error: Optional[str]


class YouTubeClient:
    """Uploads shorts/videos to YouTube via resumable upload."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        channel_id: str = "",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.channel_id = channel_id
        self._access_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _refresh_access_token(self) -> str:
        resp = requests.post(OAUTH_TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        return self._access_token

    def _headers(self) -> dict:
        if not self._access_token:
            self._refresh_access_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def _init_resumable_upload(self, metadata: dict, file_size: int) -> str:
        """Returns the resumable session URI."""
        headers = self._headers()
        headers.update({
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/mp4",
        })
        resp = requests.post(
            f"{YT_UPLOAD_URL}?uploadType=resumable&part=snippet,status",
            headers=headers,
            json=metadata,
        )
        resp.raise_for_status()
        return resp.headers["Location"]

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        category_id: str = "22",
        privacy_status: str = "public",
        is_short: bool = True,
        thumbnail_path: str | None = None,
    ) -> YouTubeUploadResult:
        path = Path(video_path)
        file_size = path.stat().st_size

        tag_list = tags or []
        if is_short and "#Shorts" not in tag_list:
            tag_list = ["#Shorts"] + tag_list

        short_suffix = "\n\n#Shorts" if is_short else ""
        metadata = {
            "snippet": {
                "title": title[:100],
                "description": f"{description}{short_suffix}",
                "tags": tag_list[:500],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
            upload_uri = self._init_resumable_upload(metadata, file_size)
            with path.open("rb") as fh:
                resp = requests.put(
                    upload_uri,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(file_size),
                    },
                    data=fh,
                )
            resp.raise_for_status()
            video_id = resp.json()["id"]
            url = f"https://www.youtube.com/shorts/{video_id}" if is_short else f"https://youtu.be/{video_id}"

            if thumbnail_path:
                self._set_thumbnail(video_id, thumbnail_path)

            return YouTubeUploadResult(True, video_id, url, None)

        except Exception as exc:
            log.exception("YouTube upload failed")
            return YouTubeUploadResult(False, None, None, str(exc))

    def _set_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        headers = self._headers()
        with open(thumbnail_path, "rb") as fh:
            resp = requests.post(
                f"{YT_API_BASE}/thumbnails/set",
                headers=headers,
                params={"videoId": video_id},
                files={"thumbnail": fh},
            )
        if not resp.ok:
            log.warning("thumbnail upload failed: %s", resp.text)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_video_analytics(self, video_id: str) -> dict:
        """Fetch view/like/comment counts for a video."""
        resp = requests.get(
            f"{YT_API_BASE}/videos",
            headers=self._headers(),
            params={
                "part": "statistics",
                "id": video_id,
            },
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0]["statistics"] if items else {}


class MockYouTubeClient(YouTubeClient):
    def __init__(self):
        self.client_id = "mock"
        self.client_secret = "mock"
        self.refresh_token = "mock"
        self.channel_id = "mock"
        self._access_token = "mock"

    def upload_video(self, video_path, title, **kwargs):
        log.info("[MOCK] YouTube upload: %s | %s", video_path, title)
        return YouTubeUploadResult(True, "mock-video-id", "https://youtube.com/shorts/mock-video-id", None)
