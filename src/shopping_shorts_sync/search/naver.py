"""Naver Shopping search — official Open API.

Endpoint and auth are per Naver's documented "검색 API - 쇼핑" spec
(openapi.naver.com/v1/search/shop.json, X-Naver-Client-Id/Secret headers).
This session's network policy blocks openapi.naver.com, so this client has
not been exercised against the live endpoint — verify the response shape
once network access + real client id/secret are available.
"""
from __future__ import annotations

import re

import requests

from .models import SearchResult

API_URL = "https://openapi.naver.com/v1/search/shop.json"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text)


class NaverApiError(RuntimeError):
    pass


class NaverShopClient:
    def __init__(self, client_id: str, client_secret: str, timeout: float = 10.0):
        if not client_id or not client_secret:
            raise NaverApiError("NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are required in live mode")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    def search(self, keyword: str, limit: int = 5) -> list[SearchResult]:
        response = requests.get(
            API_URL,
            params={"query": keyword, "display": limit, "start": 1, "sort": "sim"},
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()

        results = []
        for item in body.get("items", [])[:limit]:
            results.append(
                SearchResult(
                    source="naver",
                    name=_strip_tags(item.get("title", "")),
                    image_url=item.get("image", ""),
                    product_url=item.get("link", ""),
                    price=item.get("lprice") or None,
                )
            )
        return results
