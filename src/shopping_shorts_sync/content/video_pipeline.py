"""Vertical video generation pipeline.

Generates 9:16 short-form videos for TikTok / YouTube Shorts / Instagram Reels
using the Higgs API (higgsfield.ai). Requires HIGGS_API_KEY.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

HIGGS_API_BASE = "https://api.higgsfield.ai/v1"


@dataclass
class VideoJob:
    job_id: str
    status: str
    video_url: Optional[str]
    error: Optional[str]


class VideoPipeline:
    """Generate vertical (9:16) product shorts via Higgs API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # Image generation (thumbnail)
    # ------------------------------------------------------------------

    def generate_thumbnail(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        model: str = "flux-dev",
    ) -> dict:
        resp = self._session.post(f"{HIGGS_API_BASE}/images/generate", json={
            "prompt": prompt,
            "width": width,
            "height": height,
            "model": model,
        })
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Video generation
    # ------------------------------------------------------------------

    def generate_product_video(
        self,
        product_name: str,
        script_text: str,
        product_image_url: str,
        style: str = "korean_shopping_short",
        duration_seconds: int = 30,
    ) -> VideoJob:
        """Submit a product video generation job."""
        prompt = (
            f"Korean shopping short video for product: {product_name}. "
            f"Script: {script_text[:300]}. "
            f"Style: energetic, vertical 9:16, Korean text overlays, bright colors."
        )

        payload = {
            "prompt": prompt,
            "image_url": product_image_url,
            "duration": duration_seconds,
            "aspect_ratio": "9:16",
            "style": style,
        }

        try:
            resp = self._session.post(f"{HIGGS_API_BASE}/videos/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return VideoJob(
                job_id=data.get("job_id", ""),
                status="pending",
                video_url=None,
                error=None,
            )
        except Exception as exc:
            log.exception("video generation request failed")
            return VideoJob("", "failed", None, str(exc))

    def poll_job(self, job_id: str) -> VideoJob:
        try:
            resp = self._session.get(f"{HIGGS_API_BASE}/videos/jobs/{job_id}")
            resp.raise_for_status()
            data = resp.json()
            return VideoJob(
                job_id=job_id,
                status=data.get("status", "unknown"),
                video_url=data.get("video_url"),
                error=data.get("error"),
            )
        except Exception as exc:
            return VideoJob(job_id, "error", None, str(exc))

    def wait_for_video(
        self,
        job_id: str,
        timeout: int = 600,
        interval: int = 15,
    ) -> VideoJob:
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.poll_job(job_id)
            log.info("video job %s: %s", job_id, job.status)
            if job.status in ("completed", "done", "success"):
                return job
            if job.status in ("failed", "error"):
                return job
            time.sleep(interval)
        return VideoJob(job_id, "timeout", None, "timed out waiting for video")

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_video(self, video_url: str, output_path: str) -> str:
        resp = requests.get(video_url, stream=True, timeout=120)
        resp.raise_for_status()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        log.info("video downloaded to %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def generate_and_download(
        self,
        product_name: str,
        script_text: str,
        product_image_url: str,
        output_path: str,
        **kwargs,
    ) -> Optional[str]:
        job = self.generate_product_video(
            product_name, script_text, product_image_url, **kwargs
        )
        if job.status == "failed":
            log.error("video generation failed: %s", job.error)
            return None

        job = self.wait_for_video(job.job_id)
        if not job.video_url:
            log.error("no video URL in completed job: %s", job.error)
            return None

        return self.download_video(job.video_url, output_path)


class MockVideoPipeline(VideoPipeline):
    def __init__(self):
        self.api_key = "mock"

    def generate_and_download(self, product_name, script_text, product_image_url, output_path, **kwargs):
        log.info("[MOCK] Video pipeline: %s -> %s", product_name, output_path)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"MOCK_VIDEO")
        return output_path
