from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Coupon:
    rate: float  # 0.05 = 5%
    cap: int     # max discount in KRW


@dataclass(frozen=True)
class SourceSpec:
    """Generic JSON-over-HTTP listing source. Every site-specific detail lives in
    config (url template + field mapping) so a site can be (re)calibrated
    without code changes. See docs/VENDING.md."""

    name: str
    url: str                      # may contain {brand_id} and {page}
    list_path: str                # dotted path to the item list, e.g. "data.list"
    fields: dict                  # Item field -> dotted path in each raw item
    warmup_url: str = ""
    headers: dict = field(default_factory=dict)
    max_pages: int = 1
    role: str = "sourcing"        # "sourcing" (we buy here) or "market" (sell-price reference, e.g. 무신사/29cm)
    detect: bool = False          # run 신상품/가격하락 detection + alerts on this source
    brand_ids: dict = field(default_factory=dict)  # brand name -> site brand id/query; missing = skipped
    type: str = "json_http"       # "json_http" (config-mapped JSON) or "naver_shop" (Naver Shopping Open API)
    stores: list = field(default_factory=list)     # naver_shop only: mallName allow-list (네이버직구 스토어)


@dataclass(frozen=True)
class VendingSettings:
    brands: list[str]
    excluded_brands: list[str]
    coupons: list[Coupon]
    conservative_coupons: list[Coupon]
    price_drop_threshold: float   # 0.1 = alert when price falls >= 10%
    market_fee_rate: float        # smartstore fees, e.g. 0.055
    shipping_cost: int
    min_margin: int               # KRW net margin required for the sourcing sheet
    undercut: int                 # list this much below the market (판매 기준) price
    cache_ttl_minutes: int
    request_delay_sec: float
    sources: list[SourceSpec]

    @property
    def sourcing_sources(self) -> list[SourceSpec]:
        return [s for s in self.sources if s.role == "sourcing"]

    @property
    def market_sources(self) -> list[SourceSpec]:
        return [s for s in self.sources if s.role == "market"]


def _coupons(raw) -> list[Coupon]:
    return [Coupon(rate=float(c["rate"]), cap=int(c["cap"])) for c in raw or []]


def load_settings(path: str | Path) -> VendingSettings:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return VendingSettings(
        brands=list(raw.get("brands", [])),
        excluded_brands=[b.lower() for b in raw.get("excluded_brands", [])],
        coupons=_coupons(raw.get("coupons")),
        conservative_coupons=_coupons(raw.get("conservative_coupons")),
        price_drop_threshold=float(raw.get("price_drop_threshold", 0.1)),
        market_fee_rate=float(raw.get("market_fee_rate", 0.055)),
        shipping_cost=int(raw.get("shipping_cost", 0)),
        min_margin=int(raw.get("min_margin", 10000)),
        undercut=int(raw.get("undercut", 100)),
        cache_ttl_minutes=int(raw.get("cache_ttl_minutes", 120)),
        request_delay_sec=float(raw.get("request_delay_sec", 1.0)),
        sources=[SourceSpec(**{k: v for k, v in s.items() if k in SourceSpec.__dataclass_fields__})
                 for s in raw.get("sources", [])],
    )


def load_blacklist(path: str | Path | None) -> set[str]:
    """One product number (or source:product_no) per line; '#' comments allowed."""
    if not path or not Path(path).exists():
        return set()
    out = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out
