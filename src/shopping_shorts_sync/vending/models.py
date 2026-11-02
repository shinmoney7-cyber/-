from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_STYLE_RE = re.compile(r"[^0-9A-Z]")


def normalize_style_code(code: str | None) -> str:
    """'2W987906V 04' / '2w987906v-04' -> '2W987906V04' so codes match across sites."""
    if not code:
        return ""
    return _STYLE_RE.sub("", code.upper())


@dataclass(frozen=True)
class Item:
    source: str          # e.g. musinsa, cm29, okmall, naver_store
    product_no: str      # site-specific id
    brand: str
    name: str
    price: int           # current sale price (KRW), before our coupons
    url: str = ""
    image: str = ""
    style_code: str = "" # 품번
    sizes: str = ""      # e.g. "1/3" available/total or "S,M,L"
    store: str = ""      # seller/store name (naver 직구 stores)
    sold_out: bool = False

    @property
    def key(self) -> str:
        return f"{self.source}:{self.product_no}"

    @property
    def style_key(self) -> str:
        return normalize_style_code(self.style_code)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Item":
        return Item(**{k: d[k] for k in Item.__dataclass_fields__ if k in d})
