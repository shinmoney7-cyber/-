from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from .base import VideoApiError, VideoJob
from .higgsfield import poll_until_done

DEFAULT_BASE_URL = "https://api.topview.ai"
DEFAULT_MODEL = "Topview Pro"

SUBMIT_PATH = "/v2/common_task/image2video/task/submit"
QUERY_PATH = "/v2/common_task/image2video/task/query"

_IMAGE_FORMATS = ("png", "jpg", "jpeg", "bmp", "webp")


class TopviewVideoClient:
    """Image-to-video client for the TopView open API (Image-to-Video V2).

    Endpoints, headers and response envelope follow TopView's official
    ``topview-ai-mcp`` package: every response is ``{"code": "200",
    "result": {...}}``; auth is ``Topview-Uid`` + ``Authorization: Bearer``.
    Images must be uploaded first (credential -> S3 PUT -> check) to get a
    ``fileId`` -- URL thumbnails are downloaded and re-uploaded.
    """

    provider = "topview"

    def __init__(
        self,
        uid: str,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        aspect_ratio: str = "9:16",
        timeout: float = 30.0,
        poll_interval: float = 5.0,
        max_wait: float = 900.0,
    ):
        if not uid or not api_key:
            raise VideoApiError("TOPVIEW_UID and TOPVIEW_API_KEY are required in live mode")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.aspect_ratio = aspect_ratio
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_wait = max_wait
        self._session = requests.Session()
        self._session.headers.update({"Topview-Uid": uid, "Authorization": f"Bearer {api_key}"})

    def _call(self, method: str, path: str, **kwargs):
        response = self._session.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        if response.status_code >= 400:
            raise VideoApiError(f"TopView API {response.status_code}: {response.text[:300]}")
        body = response.json()
        code = str(body.get("code", ""))
        if code != "200":
            raise VideoApiError(f"TopView API code={code}: {body.get('message')}")
        return body.get("result", body)

    def _upload(self, path: Path) -> str:
        fmt = path.suffix.lstrip(".").lower()
        if fmt not in _IMAGE_FORMATS:
            raise VideoApiError(f"TopView does not accept image format {fmt!r} ({path.name})")
        cred = self._call("GET", "/v1/upload/credential", params={"format": fmt, "needAccelerateUrl": ""})
        put = requests.put(cred["uploadUrl"], data=path.read_bytes(), timeout=self.timeout)
        if put.status_code >= 400:
            raise VideoApiError(f"TopView S3 upload failed {put.status_code}: {put.text[:300]}")
        check = self._call("GET", "/v1/upload/check", params={"fileId": cred["fileId"]})
        if check is not True and str(check).lower() != "true":
            raise VideoApiError(f"TopView upload check failed for fileId {cred['fileId']}")
        return cred["fileId"]

    def prepare_image(self, image: str) -> str:
        if not image.startswith(("http://", "https://")):
            path = Path(image)
            if not path.is_file():
                raise VideoApiError(f"thumbnail is neither a URL nor an existing file: {image!r}")
            return self._upload(path)

        suffix = Path(urlparse(image).path).suffix or ".jpg"
        response = requests.get(image, timeout=self.timeout)
        if response.status_code >= 400:
            raise VideoApiError(f"could not download thumbnail {image}: {response.status_code}")
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(response.content)
            return self._upload(Path(tmp))
        finally:
            os.remove(tmp)

    def submit(self, image_ref: str, prompt: str, duration: int) -> str:
        result = self._call(
            "POST",
            SUBMIT_PATH,
            json={
                "model": self.model,
                "firstFrameFileId": image_ref,
                "prompt": prompt,
                "aspectRatio": self.aspect_ratio,
                "duration": duration,
                "generatingCount": 1,
            },
        )
        task_id = result.get("taskId")
        if not task_id:
            raise VideoApiError(f"TopView submit response has no taskId: {result}")
        return task_id

    def status(self, request_id: str) -> VideoJob:
        result = self._call("GET", QUERY_PATH, params={"taskId": request_id})
        raw = str(result.get("status", "")).lower()
        if raw == "success":
            videos = result.get("videos") or []
            url = next((v.get("filePath") for v in videos if str(v.get("status", "")).lower() == "success"), None)
            if url:
                return VideoJob(request_id=request_id, status="completed", video_url=url)
            return VideoJob(request_id=request_id, status="failed", error="task succeeded but returned no video")
        if raw in ("failed", "fail"):
            return VideoJob(request_id=request_id, status="failed", error=result.get("errorMsg") or "task failed")
        return VideoJob(request_id=request_id, status="pending")

    def wait(self, request_id: str) -> VideoJob:
        return poll_until_done(self, request_id, self.poll_interval, self.max_wait)
