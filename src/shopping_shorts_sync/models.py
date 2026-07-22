from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

TARGET_PAGES = ("harujin", "shinjh")


class ProductValidationError(ValueError):
    pass


def normalize_coupang_url(url: str) -> str:
    """Strips query params so tracking-param changes don't churn the derived id."""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def derive_product_id(coupang_url: str) -> str:
    digest = hashlib.sha256(normalize_coupang_url(coupang_url).encode("utf-8")).hexdigest()
    return digest[:16]


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    coupang_url: str
    thumbnail: str
    category: str
    target_page: str
    enabled: bool = True

    @staticmethod
    def from_dict(raw: dict) -> "Product":
        missing = [f for f in ("name", "coupang_url", "target_page") if not raw.get(f)]
        if missing:
            raise ProductValidationError(f"product row missing required field(s): {missing}")

        target_page = raw["target_page"]
        if target_page not in TARGET_PAGES:
            raise ProductValidationError(
                f"target_page must be one of {TARGET_PAGES}, got {target_page!r}"
            )

        product_id = raw.get("id") or derive_product_id(raw["coupang_url"])
        enabled_raw = raw.get("enabled", True)
        if isinstance(enabled_raw, str):
            enabled = enabled_raw.strip().lower() in ("1", "true", "yes", "y")
        else:
            enabled = bool(enabled_raw)

        return Product(
            id=product_id,
            name=raw["name"],
            coupang_url=raw["coupang_url"],
            thumbnail=raw.get("thumbnail", ""),
            category=raw.get("category", ""),
            target_page=target_page,
            enabled=enabled,
        )

    def content_hash(self, deeplink: str) -> str:
        payload = "|".join([self.name, self.thumbnail, self.category, deeplink])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
