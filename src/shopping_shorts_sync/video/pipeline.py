from __future__ import annotations

import logging
from pathlib import Path

import requests

from ..config import Config
from ..models import Product
from ..script_store import ScriptCandidate
from .base import VideoApiError, VideoClient
from .higgsfield import HiggsfieldVideoClient
from .mock_client import MockVideoClient
from .prompt import build_scenes
from .topview import TopviewVideoClient

logger = logging.getLogger(__name__)


def build_video_client(config: Config, provider: str, live: bool) -> VideoClient:
    if not live:
        return MockVideoClient(provider)
    if provider == "higgsfield":
        return HiggsfieldVideoClient(
            config.higgsfield_credential,
            base_url=config.higgsfield_base_url,
            model=config.higgsfield_video_model,
        )
    if provider == "topview":
        return TopviewVideoClient(
            config.topview_uid,
            config.topview_api_key,
            base_url=config.topview_base_url,
            model=config.topview_video_model,
        )
    raise VideoApiError(f"provider {provider!r} has no API client")


def generate_product_video(
    product: Product,
    candidate: ScriptCandidate,
    client: VideoClient,
    duration: int,
    download_dir: str | Path | None = None,
) -> tuple[list[dict], str | None]:
    """Generates one clip per AIDA stage of the selected script, all from the
    product thumbnail. All scenes are submitted first and then awaited, so the
    provider renders them in parallel. Returns (clips, first_error)."""
    if not product.thumbnail:
        raise VideoApiError(f"product {product.id!r} has no thumbnail to animate")

    scenes = build_scenes(product, candidate)
    image_ref = client.prepare_image(product.thumbnail)

    submitted = []
    for scene in scenes:
        request_id = client.submit(image_ref, scene.prompt, duration)
        logger.info("submitted %s scene %s -> %s", product.id, scene.stage, request_id)
        submitted.append((scene, request_id))

    clips: list[dict] = []
    first_error = None
    for index, (scene, request_id) in enumerate(submitted, start=1):
        job = client.wait(request_id)
        clip = {
            "stage": scene.stage,
            "caption": scene.caption,
            "request_id": request_id,
            "status": job.status,
            "video_url": job.video_url,
            "error": job.error,
            "local_path": None,
        }
        if job.ok and download_dir is not None:
            clip["local_path"] = str(_download(job.video_url, Path(download_dir) / product.id / f"{index:02d}-{scene.stage}.mp4"))
        if not job.ok and first_error is None:
            first_error = f"{scene.stage}: {job.error or job.status}"
        clips.append(clip)
    return clips, first_error


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with dest.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    return dest
