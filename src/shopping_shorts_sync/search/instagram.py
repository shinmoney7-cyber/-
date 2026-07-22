"""Instagram Graph API hashtag search.

Unlike TikTok/Douyin/Xiaohongshu (no accessible public search API at all),
Instagram does have an official path -- but it's meaningfully harder to get
working than YouTube's:

- Requires an Instagram **Business or Creator** account linked to a
  Facebook Page (a personal account cannot use this API).
- Requires a Meta app with the `instagram_basic` permission, and Meta App
  Review before it works for anyone other than the app's own test users.
- Search is by **hashtag only** (not free-text keyword) -- this client
  strips whitespace from the keyword and searches it as a single hashtag.
- Rate limited to 30 unique hashtags queried per 7 rolling days per
  IG user, and `top_media` only returns recent popular posts for that tag.

Two-step call: `ig_hashtag_search` resolves a hashtag string to an ID,
then `{hashtag_id}/top_media` returns media for it. This session's network
policy blocks graph.facebook.com, so this client has not been exercised
against the live API -- verify field names/behavior once real
credentials + network access are available (see docs/CALIBRATION.md).
"""
from __future__ import annotations

import requests

from .models import SearchResult

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
HASHTAG_SEARCH_URL = f"{GRAPH_API_BASE}/ig_hashtag_search"


class InstagramApiError(RuntimeError):
    pass


class InstagramSearchClient:
    def __init__(self, access_token: str, ig_user_id: str, timeout: float = 10.0):
        if not access_token or not ig_user_id:
            raise InstagramApiError("INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_IG_USER_ID are required in live mode")
        self.access_token = access_token
        self.ig_user_id = ig_user_id
        self.timeout = timeout

    def _find_hashtag_id(self, hashtag: str) -> str | None:
        response = requests.get(
            HASHTAG_SEARCH_URL,
            params={"user_id": self.ig_user_id, "q": hashtag, "access_token": self.access_token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        return data[0]["id"] if data else None

    def search(self, keyword: str, limit: int = 5) -> list[SearchResult]:
        hashtag = keyword.replace(" ", "")
        hashtag_id = self._find_hashtag_id(hashtag)
        if hashtag_id is None:
            return []

        response = requests.get(
            f"{GRAPH_API_BASE}/{hashtag_id}/top_media",
            params={
                "user_id": self.ig_user_id,
                "fields": "id,caption,media_type,media_url,permalink,thumbnail_url",
                "access_token": self.access_token,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        items = response.json().get("data", [])

        results = []
        for item in items:
            if item.get("media_type") != "VIDEO":
                continue  # 짜깁기 소재로는 영상만 필요 -- 이미지/캐러셀 게시물은 제외
            results.append(
                SearchResult(
                    source="instagram",
                    name=(item.get("caption") or "").splitlines()[0][:100] if item.get("caption") else f"#{hashtag}",
                    image_url=item.get("thumbnail_url") or item.get("media_url", ""),
                    product_url=item.get("permalink", ""),
                    price=None,
                )
            )
            if len(results) >= limit:
                break
        return results
