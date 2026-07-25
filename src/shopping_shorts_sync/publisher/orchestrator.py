from __future__ import annotations

from .models import PublishResult, VideoPublisherProtocol


def publish_to_all(
    publishers: dict[str, VideoPublisherProtocol],
    video_path: str,
    caption: str,
    product_name: str,
) -> dict[str, PublishResult]:
    return {
        platform: publisher.publish(video_path, caption, product_name)
        for platform, publisher in publishers.items()
    }


def build_publishers(config, dry_run: bool, platforms: list[str]) -> dict[str, VideoPublisherProtocol]:
    from .mock import MockPublisher
    if dry_run:
        return {p: MockPublisher(platform=p) for p in platforms}

    publishers = {}
    if "tiktok" in platforms:
        from .tiktok import TikTokPublisher
        publishers["tiktok"] = TikTokPublisher(access_token=config.tiktok_access_token)
    if "instagram" in platforms:
        from .instagram import InstagramPublisher
        publishers["instagram"] = InstagramPublisher(
            access_token=config.instagram_access_token,
            business_account_id=config.instagram_business_account_id,
        )
    if "youtube" in platforms:
        from .youtube import YouTubePublisher
        publishers["youtube"] = YouTubePublisher(
            client_secrets_file=config.youtube_client_secrets_file,
            token_file=config.youtube_token_file,
        )
    return publishers
