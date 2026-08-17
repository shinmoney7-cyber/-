from __future__ import annotations

import hashlib

from .models import SearchResult


class MockSearchClient:
    """Drop-in stand-in for any of the real search clients (Naver/Daiso/OliveYoung).

    No network, no browser. Produces deterministic fake results so repeated
    searches for the same keyword are stable.
    """

    def __init__(self, source: str):
        self.source = source

    def search(self, keyword: str, limit: int = 5) -> list[SearchResult]:
        results = []
        for i in range(limit):
            digest = hashlib.sha256(f"{self.source}:{keyword}:{i}".encode("utf-8")).hexdigest()[:8]
            results.append(
                SearchResult(
                    source=self.source,
                    name=f"{keyword} {self.source} 상품 {i + 1}",
                    image_url=f"https://example.com/{self.source}/{digest}.jpg",
                    product_url=f"https://example.com/{self.source}/product/{digest}",
                    price=str(10000 + i * 1000),
                )
            )
        return results
