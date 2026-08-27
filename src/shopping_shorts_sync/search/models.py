from __future__ import annotations

from dataclasses import dataclass

SOURCES = ("naver", "daiso", "oliveyoung", "google")


@dataclass(frozen=True)
class SearchResult:
    source: str
    name: str
    image_url: str
    product_url: str
    price: str | None = None
