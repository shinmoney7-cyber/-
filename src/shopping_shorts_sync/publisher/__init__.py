from __future__ import annotations

from pathlib import Path

from ..config import Config
from .instagram import InstagramPublisher
from .models import PublishResult, VideoPublisherProtocol
from .tiktok import TikTokPublisher
from .youtube import YouTubePublisher

__all__ = [
    "PublishResult",
    "VideoPublisherProtocol",
    "TikTokPublisher",
    "YouTubePublisher",
    "InstagramPublisher",
    "build_publisher",
    "public_video_url",
]

PUBLISH_PLATFORMS = ("tiktok", "youtube", "instagram")


def build_publisher(platform: str, config: Config, dry_run: bool = True) -> VideoPublisherProtocol:
    if platform == "tiktok":
        return TikTokPublisher(config.tiktok_access_token, dry_run=dry_run)
    if platform == "youtube":
        return YouTubePublisher(
            config.youtube_client_secrets_file,
            token_file=config.youtube_token_file,
            dry_run=dry_run,
        )
    if platform == "instagram":
        return InstagramPublisher(
            config.instagram_access_token,
            config.instagram_ig_user_id,
            dry_run=dry_run,
        )
    raise ValueError(f"unknown publish platform {platform!r} -- expected one of {PUBLISH_PLATFORMS}")


def public_video_url(config: Config, product_id: str, video_path: str) -> str | None:
    """Instagram --live needs a public HTTPS URL, not a local path -- build
    one from PUBLIC_BASE_URL + the webapp's own /videos/<id>/<file> route.
    Returns None if PUBLIC_BASE_URL isn't configured."""
    if not config.public_base_url:
        return None
    filename = Path(video_path).name
    return f"{config.public_base_url.rstrip('/')}/videos/{product_id}/{filename}"
