"""TikTok Content Posting API v2 (FILE_UPLOAD source) publisher.

Requires an app that has passed TikTok's app review for the Content Posting
API scope -- before that review, videos can only be posted to the
developer's own test account. Not exercised against the live API in this
environment (no network access to open.tiktokapis.com) -- see
docs/CALIBRATION.md before --live use.
"""
from __future__ import annotations

import math
from pathlib import Path

import requests

from .models import PublishResult

_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MiB


class TikTokPublisher:
    """Publishes a local video file to TikTok via the Content Posting API v2 (FILE_UPLOAD source)."""

    def __init__(self, access_token: str, dry_run: bool = False) -> None:
        self._token = access_token
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def publish(self, video_path: str, caption: str, product_name: str) -> PublishResult:
        if self.dry_run:
            return PublishResult(
                platform="tiktok",
                success=True,
                post_id="DRY_RUN_ID",
            )

        try:
            return self._publish(video_path, caption)
        except requests.RequestException as exc:
            return PublishResult(platform="tiktok", success=False, error=str(exc))
        except _TikTokAPIError as exc:
            return PublishResult(platform="tiktok", success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def _publish(self, video_path: str, caption: str) -> PublishResult:
        path = Path(video_path)
        video_size = path.stat().st_size
        total_chunk_count = max(1, math.ceil(video_size / _CHUNK_SIZE))

        init_payload = {
            "post_info": {
                "title": caption[:2200],  # TikTok title cap
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 0,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": _CHUNK_SIZE,
                "total_chunk_count": total_chunk_count,
            },
        }

        init_resp = requests.post(_INIT_URL, json=init_payload, headers=self._headers(), timeout=30)
        init_resp.raise_for_status()
        init_data = init_resp.json()

        error_info = init_data.get("error", {})
        if error_info.get("code", "ok") != "ok":
            raise _TikTokAPIError(f"{error_info.get('code')}: {error_info.get('message')}")

        data = init_data.get("data", {})
        publish_id: str = data["publish_id"]
        upload_url: str = data["upload_url"]

        self._upload_chunks(path, upload_url, video_size, total_chunk_count)

        # FILE_UPLOAD source does not require a separate confirm call.
        return PublishResult(
            platform="tiktok",
            success=True,
            post_id=publish_id,
        )

    def _upload_chunks(
        self,
        path: Path,
        upload_url: str,
        video_size: int,
        total_chunk_count: int,
    ) -> None:
        with path.open("rb") as fh:
            for chunk_index in range(total_chunk_count):
                chunk = fh.read(_CHUNK_SIZE)
                start = chunk_index * _CHUNK_SIZE
                end = start + len(chunk) - 1

                headers = {
                    "Content-Range": f"bytes {start}-{end}/{video_size}",
                    "Content-Type": "video/mp4",
                }
                resp = requests.put(upload_url, data=chunk, headers=headers, timeout=120)
                resp.raise_for_status()


class _TikTokAPIError(Exception):
    pass
