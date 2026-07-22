"""YouTube Data API v3 search — official API, used as the video-content
source for "2차 창작"(derivative-content) material instead of TikTok/Douyin/
Xiaohongshu (which have no accessible public search API — see README).

This session's network policy blocks googleapis.com, so this client has not
been exercised against the live endpoint. Verify the response shape once
network access + a real API key are available (same caveat as
search/naver.py) — see docs/CALIBRATION.md.
"""
from __future__ import annotations

import requests

from .models import SearchResult

API_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeApiError(RuntimeError):
    pass


class YouTubeSearchClient:
    def __init__(self, api_key: str, timeout: float = 10.0):
        if not api_key:
            raise YouTubeApiError("YOUTUBE_API_KEY is required in live mode")
        self.api_key = api_key
        self.timeout = timeout

    def search(self, keyword: str, limit: int = 5) -> list[SearchResult]:
        response = requests.get(
            API_URL,
            params={
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "maxResults": limit,
                "key": self.api_key,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()

        results = []
        for item in body.get("items", [])[:limit]:
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("default", {}).get("url")
                or ""
            )
            results.append(
                SearchResult(
                    source="youtube",
                    name=snippet.get("title", ""),
                    image_url=thumbnail_url,
                    product_url=f"https://www.youtube.com/watch?v={video_id}",
                    price=None,
                )
            )
        return results
