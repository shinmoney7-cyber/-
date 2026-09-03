from __future__ import annotations

from ..config import Config
from .downloader import YtDlpDownloader
from .mock_downloader import MockDownloader
from .mock_stitcher import MockStitcher
from .stitcher import FfmpegStitcher


def build_downloader(config: Config):
    if config.video_mode == "live":
        return YtDlpDownloader(config.ytdlp_path)
    return MockDownloader()


def build_stitcher(config: Config):
    if config.video_mode == "live":
        return FfmpegStitcher(config.ffmpeg_path)
    return MockStitcher()
