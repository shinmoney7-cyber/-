"""Data models for trending product pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TrendPeriod(str, Enum):
    DAY_7 = "7d"
    DAY_30 = "30d"
    DAY_90 = "90d"
    DAY_365 = "1y"


@dataclass
class TrendingProduct:
    rank: int
    period: TrendPeriod
    product_id: str
    name: str
    brand: str
    category: str
    sold_count: int
    growth_rate: float          # % change vs prior period
    thumbnail_url: str
    source: str                 # "tiktok_shop" | "douyin"
    tags: list[str] = field(default_factory=list)


@dataclass
class KoreaMatch:
    trending: TrendingProduct
    # Where to buy in Korea
    coupang_url: str = ""
    coupang_deeplink: str = ""
    naver_url: str = ""
    daiso_url: str = ""
    oliveyoung_url: str = ""
    local_price_krw: int = 0
    local_product_name: str = ""    # Korean product name / equivalent
    available_platforms: list[str] = field(default_factory=list)
    script_ko: str = ""             # Generated 15-second Korean script
    hashtags: list[str] = field(default_factory=list)
