"""Multi-platform publish orchestrator.

One call to PublishOrchestrator.publish_product() publishes a product short
to every enabled platform and returns a summary.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class PlatformResult:
    platform: str
    success: bool
    url: Optional[str]
    error: Optional[str]


@dataclass
class PublishSummary:
    product_id: str
    product_name: str
    results: list[PlatformResult] = field(default_factory=list)

    @property
    def succeeded(self) -> list[str]:
        return [r.platform for r in self.results if r.success]

    @property
    def failed(self) -> list[str]:
        return [r.platform for r in self.results if not r.success]

    def __str__(self) -> str:
        lines = [f"Product: {self.product_name}"]
        for r in self.results:
            status = "OK" if r.success else f"FAIL ({r.error})"
            url_part = f" | {r.url}" if r.url else ""
            lines.append(f"  [{r.platform}] {status}{url_part}")
        return "\n".join(lines)


class PublishOrchestrator:
    """Coordinates publishing to TikTok, YouTube Shorts, Instagram Reels, Naver Blog, Email."""

    def __init__(
        self,
        tiktok=None,
        youtube=None,
        instagram=None,
        naver_blog=None,
        email_sender=None,
        email_recipients: list[str] | None = None,
    ):
        self.tiktok = tiktok
        self.youtube = youtube
        self.instagram = instagram
        self.naver_blog = naver_blog
        self.email_sender = email_sender
        self.email_recipients = email_recipients or []

    # ------------------------------------------------------------------
    # Per-platform helpers
    # ------------------------------------------------------------------

    def _publish_tiktok(self, video_path: str, title: str, tags: list[str]) -> PlatformResult:
        if not self.tiktok:
            return PlatformResult("tiktok", False, None, "client not configured")
        result = self.tiktok.publish_video(video_path, title, tags=tags)
        return PlatformResult("tiktok", result.success, result.share_url, result.error)

    def _publish_youtube(
        self, video_path: str, title: str, description: str, tags: list[str]
    ) -> PlatformResult:
        if not self.youtube:
            return PlatformResult("youtube", False, None, "client not configured")
        result = self.youtube.upload_video(
            video_path, title, description=description, tags=tags, is_short=True
        )
        return PlatformResult("youtube", result.success, result.url, result.error)

    def _publish_instagram(
        self, video_url: str, caption: str, tags: list[str]
    ) -> PlatformResult:
        if not self.instagram:
            return PlatformResult("instagram", False, None, "client not configured")
        result = self.instagram.publish_reel(video_url, caption, tags=tags)
        return PlatformResult("instagram", result.success, result.permalink, result.error)

    def _publish_naver_blog(
        self,
        product_name: str,
        deeplink: str,
        thumbnail_url: str,
        script_text: str,
        category: str,
        tags: list[str],
    ) -> PlatformResult:
        if not self.naver_blog:
            return PlatformResult("naver_blog", False, None, "client not configured")
        from ..platforms.naver_blog import NaverBlogClient
        html = NaverBlogClient.build_product_post_html(
            product_name, deeplink, thumbnail_url, script_text, category
        )
        result = self.naver_blog.write_post(
            title=f"[추천] {product_name}",
            content_html=html,
            tags=tags,
        )
        return PlatformResult("naver_blog", result.success, result.post_url, result.error)

    def _publish_email(
        self, products_data: list[dict], subject: str
    ) -> PlatformResult:
        if not self.email_sender or not self.email_recipients:
            return PlatformResult("email", False, None, "sender or recipients not configured")
        from ..platforms.email_sender import EmailSender
        html = EmailSender.build_product_newsletter_html(products_data)
        result = self.email_sender.send(self.email_recipients, subject, html)
        return PlatformResult(
            "email",
            result.success,
            None,
            result.error,
        )

    # ------------------------------------------------------------------
    # Main publish
    # ------------------------------------------------------------------

    def publish_product(
        self,
        product_id: str,
        product_name: str,
        category: str,
        coupang_deeplink: str,
        thumbnail_url: str,
        script_text: str,
        video_path: str,
        video_cdn_url: str = "",
        tags: list[str] | None = None,
        platforms: list[str] | None = None,
    ) -> PublishSummary:
        """Publish to all (or selected) platforms."""
        enabled = set(platforms or ["tiktok", "youtube", "instagram", "naver_blog", "email"])
        tag_list = tags or []
        summary = PublishSummary(product_id=product_id, product_name=product_name)

        if "tiktok" in enabled:
            log.info("Publishing to TikTok: %s", product_name)
            summary.results.append(
                self._publish_tiktok(video_path, product_name, tag_list)
            )

        if "youtube" in enabled:
            log.info("Publishing to YouTube Shorts: %s", product_name)
            summary.results.append(
                self._publish_youtube(video_path, product_name, script_text, tag_list)
            )

        if "instagram" in enabled and video_cdn_url:
            log.info("Publishing to Instagram Reels: %s", product_name)
            summary.results.append(
                self._publish_instagram(video_cdn_url, product_name, tag_list)
            )

        if "naver_blog" in enabled:
            log.info("Publishing to Naver Blog: %s", product_name)
            summary.results.append(
                self._publish_naver_blog(
                    product_name, coupang_deeplink, thumbnail_url, script_text, category, tag_list
                )
            )

        if "email" in enabled:
            log.info("Sending email newsletter for: %s", product_name)
            product_data = [{
                "name": product_name,
                "category": category,
                "thumbnail": thumbnail_url,
                "deeplink": coupang_deeplink,
            }]
            summary.results.append(
                self._publish_email(product_data, f"[추천] {product_name}")
            )

        return summary
