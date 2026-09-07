"""Naver Blog API client.

Docs: https://developers.naver.com/docs/blog/api/
OAuth2 scope: blog
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

log = logging.getLogger(__name__)

NAVER_OAUTH_BASE = "https://nid.naver.com/oauth2.0"
NAVER_BLOG_API = "https://openapi.naver.com/blog/writePost.json"


@dataclass
class NaverBlogResult:
    success: bool
    post_url: Optional[str]
    error: Optional[str]


class NaverBlogClient:
    """Posts to Naver Blog via OAuth2 API."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        blog_id: str = "",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.blog_id = blog_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

    def write_post(
        self,
        title: str,
        content_html: str,
        tags: list[str] | None = None,
        category_no: int = 0,
        publish: bool = True,
    ) -> NaverBlogResult:
        """Write a new post to the authenticated user's Naver Blog."""
        tag_str = ",".join((tags or [])[:10])
        payload = {
            "title": title[:100],
            "contents": content_html,
            "tags": tag_str,
            "categoryNo": category_no,
            "publish": "1" if publish else "0",
        }
        try:
            resp = requests.post(
                NAVER_BLOG_API,
                headers=self._headers(),
                data=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # API returns the URL of the created post
            post_url = data.get("message", {}).get("result", {}).get("postUrl", "")
            return NaverBlogResult(True, post_url, None)
        except Exception as exc:
            log.exception("Naver Blog post failed")
            return NaverBlogResult(False, None, str(exc))

    # ------------------------------------------------------------------
    # Helper: build HTML for a product shopping post
    # ------------------------------------------------------------------

    @staticmethod
    def build_product_post_html(
        product_name: str,
        coupang_deeplink: str,
        thumbnail_url: str,
        script_text: str,
        category: str,
    ) -> str:
        return f"""
<div style="max-width:600px;margin:0 auto;font-family:sans-serif;">
  <h2>{product_name}</h2>
  <p><strong>카테고리:</strong> {category}</p>
  <a href="{coupang_deeplink}" target="_blank" rel="noopener">
    <img src="{thumbnail_url}" alt="{product_name}" style="max-width:100%;border-radius:8px;">
  </a>
  <div style="margin-top:16px;white-space:pre-wrap;line-height:1.7;">
{script_text}
  </div>
  <p style="margin-top:24px;">
    <a href="{coupang_deeplink}" target="_blank" rel="noopener"
       style="background:#e81f25;color:#fff;padding:12px 24px;border-radius:4px;text-decoration:none;font-weight:bold;">
      쿠팡에서 구매하기 →
    </a>
  </p>
  <p style="font-size:12px;color:#888;margin-top:32px;">
    이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
  </p>
</div>
""".strip()


class MockNaverBlogClient(NaverBlogClient):
    def __init__(self):
        self.client_id = "mock"
        self.client_secret = "mock"
        self.access_token = "mock"
        self.blog_id = "mock"

    def write_post(self, title, content_html, **kwargs):
        log.info("[MOCK] Naver Blog post: %s", title)
        return NaverBlogResult(True, f"https://blog.naver.com/mock/000001", None)
