"""Ties the download + stitch steps together: 3 source URLs in, 1 stitched
preview video out. This is the "영상중 3개를 선택하면 생성 클릭하면 바로
자연스러운 영상 1개를 짜집기를 완성해준다" step from the owner's spec."""
from __future__ import annotations

from pathlib import Path

from ..config import Config
from . import build_downloader, build_stitcher

EXPECTED_URL_COUNT = 3


class VideoPipelineError(RuntimeError):
    pass


def generate_stitched_video(urls: list[str], product_id: str, config: Config) -> Path:
    if len(urls) != EXPECTED_URL_COUNT:
        raise VideoPipelineError(f"expected exactly {EXPECTED_URL_COUNT} urls, got {len(urls)}")

    downloader = build_downloader(config)
    stitcher = build_stitcher(config)

    product_dir = Path(config.video_output_dir) / product_id
    clip_paths = []
    for i, url in enumerate(urls):
        clip_path = product_dir / f"source_{i}.mp4"
        downloader.download(url, clip_path)
        clip_paths.append(clip_path)

    output_path = product_dir / "stitched.mp4"
    stitcher.stitch(clip_paths, output_path, clip_seconds=config.video_clip_seconds)
    return output_path
