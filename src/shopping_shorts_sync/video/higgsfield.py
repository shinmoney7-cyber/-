from __future__ import annotations

import mimetypes
import time
from pathlib import Path

import requests

from .base import VideoApiError, VideoJob

DEFAULT_BASE_URL = "https://api.higgsfield.ai"
DEFAULT_MODEL = "higgsfield-ai/dop/standard"

_PENDING = ("queued", "in_progress")
_FAILED = ("failed", "nsfw", "canceled")


def extract_video_url(body: dict) -> str | None:
    """Completed responses carry the clip under ``video.url``; tolerate the
    list form (``videos[0].url``) some models return as well."""
    video = body.get("video")
    if isinstance(video, dict) and video.get("url"):
        return video["url"]
    videos = body.get("videos")
    if isinstance(videos, list) and videos and isinstance(videos[0], dict):
        return videos[0].get("url")
    return None


class HiggsfieldVideoClient:
    """Image-to-video client for the Higgsfield platform queue API.

    Mirrors the official ``higgsfield-client`` SDK: ``POST /{model}`` returns a
    ``request_id``, then ``GET /requests/{id}/status`` is polled until it is
    ``completed`` / ``failed`` / ``nsfw`` / ``canceled``. Auth header is
    ``Authorization: Key {api_key}:{api_secret}``. The submit body fields for a
    given model are unverified -- see docs/CALIBRATION.md.
    """

    provider = "higgsfield"

    def __init__(
        self,
        credential: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        poll_interval: float = 5.0,
        max_wait: float = 900.0,
    ):
        if not credential:
            raise VideoApiError(
                "HIGGSFIELD_API_KEY and HIGGSFIELD_API_SECRET (or HF_KEY) are required in live mode"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model.strip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_wait = max_wait
        self._session = requests.Session()
        self._session.headers.update(
            {"Authorization": f"Key {credential}", "Content-Type": "application/json"}
        )

    def _request(self, method: str, url: str, **kwargs) -> dict:
        response = self._session.request(method, url, timeout=self.timeout, **kwargs)
        if response.status_code >= 400:
            raise VideoApiError(f"Higgsfield API {response.status_code}: {response.text[:300]}")
        return response.json()

    def prepare_image(self, image: str) -> str:
        """Image inputs must be public URLs; local files are uploaded first."""
        if image.startswith(("http://", "https://")):
            return image
        path = Path(image)
        if not path.is_file():
            raise VideoApiError(f"thumbnail is neither a URL nor an existing file: {image!r}")
        content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        body = self._request(
            "POST", f"{self.base_url}/files/generate-upload-url", json={"content_type": content_type}
        )
        headers = body.get("upload_headers") or {"Content-Type": content_type}
        put = requests.put(body["upload_url"], data=path.read_bytes(), headers=headers, timeout=self.timeout)
        if put.status_code >= 400:
            raise VideoApiError(f"Higgsfield image upload failed {put.status_code}: {put.text[:300]}")
        return body["public_url"]

    def submit(self, image_ref: str, prompt: str, duration: int) -> str:
        body = self._request(
            "POST",
            f"{self.base_url}/{self.model}",
            json={"image_url": image_ref, "prompt": prompt, "duration": duration},
        )
        request_id = body.get("request_id")
        if not request_id:
            raise VideoApiError(f"Higgsfield submit response has no request_id: {body}")
        return request_id

    def status(self, request_id: str) -> VideoJob:
        body = self._request("GET", f"{self.base_url}/requests/{request_id}/status")
        raw = body.get("status", "unknown")
        if raw in _PENDING:
            return VideoJob(request_id=request_id, status="pending")
        if raw == "completed":
            return VideoJob(request_id=request_id, status="completed", video_url=extract_video_url(body))
        error = body.get("error") or raw if raw in _FAILED else f"unknown status {raw!r}"
        return VideoJob(request_id=request_id, status="failed", error=error)

    def wait(self, request_id: str) -> VideoJob:
        return poll_until_done(self, request_id, self.poll_interval, self.max_wait)


def poll_until_done(client, request_id: str, poll_interval: float, max_wait: float) -> VideoJob:
    deadline = time.monotonic() + max_wait
    while True:
        job = client.status(request_id)
        if job.status != "pending":
            return job
        if time.monotonic() >= deadline:
            return VideoJob(request_id=request_id, status="failed", error="timed out waiting for video")
        time.sleep(poll_interval)
