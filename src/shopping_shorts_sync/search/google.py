"""Google Shopping search — Google Custom Search JSON API.

Uses the Programmable Search Engine (CSE) with shopping search enabled.
API docs: https://developers.google.com/custom-search/v1/overview
Requires a Google API key (GOOGLE_API_KEY) and a CSE ID (GOOGLE_CX)
configured to return shopping results. This module has NOT been exercised
against the live endpoint in this sandbox (network blocked) — verify
the response shape once credentials and network access are available.
"""
from __future__ import annotations

import requests

from .models import SearchResult

API_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleShopApiError(RuntimeError):
    pass


class GoogleShopClient:
    def __init__(self, api_key: str, cx: str, timeout: float = 10.0):
        if not api_key or not cx:
            raise GoogleShopApiError(
                "GOOGLE_API_KEY and GOOGLE_CX are required in live mode"
            )
        self.api_key = api_key
        self.cx = cx
        self.timeout = timeout

    def search(self, keyword: str, limit: int = 5) -> list[SearchResult]:
        # Google CSE returns max 10 per request; clamp limit accordingly.
        num = min(limit, 10)
        response = requests.get(
            API_URL,
            params={
                "key": self.api_key,
                "cx": self.cx,
                "q": keyword,
                "num": num,
                "searchType": "image",  # TODO CALIBRATE: remove if CSE is set to shopping-only
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()

        if "error" in body:
            raise GoogleShopApiError(body["error"].get("message", "unknown Google API error"))

        results = []
        for item in body.get("items", [])[:num]:
            image_url = (
                item.get("image", {}).get("thumbnailLink", "")
                or item.get("pagemap", {}).get("cse_image", [{}])[0].get("src", "")
            )
            price = None
            for offer in item.get("pagemap", {}).get("offer", []):
                price = offer.get("price")
                if price:
                    break

            results.append(
                SearchResult(
                    source="google",
                    name=item.get("title", ""),
                    image_url=image_url,
                    product_url=item.get("link", ""),
                    price=price,
                )
            )
        return results
