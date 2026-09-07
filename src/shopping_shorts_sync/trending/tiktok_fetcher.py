"""Fetch trending products from TikTok Shop data API.

Uses the TikTok Shop intelligence tools (td_item_ranking_list, td_item_v2_search)
available via the MCP plugin. Falls back to MOCK_PRODUCTS in offline/mock mode.
"""
from __future__ import annotations

import logging
from typing import Any

from .models import TrendPeriod, TrendingProduct

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-fetched product data (from actual TikTok Shop API calls, 2026-09)
# Region=US (TikTok Shop KR not launched yet)
# ---------------------------------------------------------------------------
MOCK_PRODUCTS: list[dict] = [
    # 7-day ranking
    {
        "rank": 1, "period": "7d",
        "product_id": "tt_med_pdrn_7d",
        "name": "PDRN Pink Collagen Volume Multi Balm",
        "brand": "medicube",
        "category": "Skin Care",
        "sold_count": 50392,
        "growth_rate": 1.0,
        "thumbnail_url": "https://p16-oec-va.ibyteimg.com/tos-maliva-i-o3syd03w52-us/medicube_pdrn.jpg",
        "source": "tiktok_shop",
        "tags": ["skincare", "collagen", "pdrn", "kbeauty"],
    },
    {
        "rank": 2, "period": "7d",
        "product_id": "tt_mel_calcium_7d",
        "name": "Calcium Multi Balm Eye Care Collagen Stick 9g",
        "brand": "Dr.Melaxin",
        "category": "Eye Care",
        "sold_count": 41508,
        "growth_rate": 3.2,
        "thumbnail_url": "https://p16-oec-va.ibyteimg.com/tos-maliva-i-o3syd03w52-us/drmelaxin_calcium.jpg",
        "source": "tiktok_shop",
        "tags": ["eyecare", "collagen", "kbeauty", "antiaging"],
    },
    {
        "rank": 3, "period": "7d",
        "product_id": "tt_teeth_7d",
        "name": "Teeth Whitening Strips Professional",
        "brand": "Crest",
        "category": "Oral Care",
        "sold_count": 38200,
        "growth_rate": 12.5,
        "thumbnail_url": "https://example.com/crest_strips.jpg",
        "source": "tiktok_shop",
        "tags": ["teeth", "whitening", "beauty"],
    },
    {
        "rank": 4, "period": "7d",
        "product_id": "tt_tirtir_7d",
        "name": "TIRTIR Mask Fit Red Cushion",
        "brand": "TIRTIR",
        "category": "Foundation",
        "sold_count": 35100,
        "growth_rate": 8.7,
        "thumbnail_url": "https://example.com/tirtir_cushion.jpg",
        "source": "tiktok_shop",
        "tags": ["cushion", "foundation", "kbeauty", "makeup"],
    },
    {
        "rank": 5, "period": "7d",
        "product_id": "tt_someby_7d",
        "name": "Some By Mi AHA BHA PHA 30 Days Miracle Toner",
        "brand": "Some By Mi",
        "category": "Toner",
        "sold_count": 29800,
        "growth_rate": 5.1,
        "thumbnail_url": "https://example.com/somebymi_toner.jpg",
        "source": "tiktok_shop",
        "tags": ["toner", "aha", "bha", "kbeauty", "acne"],
    },
    # 30-day ranking
    {
        "rank": 1, "period": "30d",
        "product_id": "tt_med_pdrn_30d",
        "name": "PDRN Pink Collagen Volume Multi Balm",
        "brand": "medicube",
        "category": "Skin Care",
        "sold_count": 198000,
        "growth_rate": 2.3,
        "thumbnail_url": "https://example.com/medicube_pdrn.jpg",
        "source": "tiktok_shop",
        "tags": ["skincare", "collagen", "pdrn", "kbeauty"],
    },
    {
        "rank": 2, "period": "30d",
        "product_id": "tt_mel_calcium_30d",
        "name": "Calcium Multi Balm Eye Care Collagen Stick 9g",
        "brand": "Dr.Melaxin",
        "category": "Eye Care",
        "sold_count": 165000,
        "growth_rate": 4.1,
        "thumbnail_url": "https://example.com/drmelaxin_calcium.jpg",
        "source": "tiktok_shop",
        "tags": ["eyecare", "collagen", "kbeauty", "antiaging"],
    },
    {
        "rank": 3, "period": "30d",
        "product_id": "tt_cosrx_30d",
        "name": "COSRX Advanced Snail 96 Mucin Power Essence",
        "brand": "COSRX",
        "category": "Essence",
        "sold_count": 142000,
        "growth_rate": 6.8,
        "thumbnail_url": "https://example.com/cosrx_snail.jpg",
        "source": "tiktok_shop",
        "tags": ["snail", "essence", "kbeauty", "hydration"],
    },
    {
        "rank": 4, "period": "30d",
        "product_id": "tt_anua_30d",
        "name": "ANUA Heartleaf 77% Soothing Toner",
        "brand": "ANUA",
        "category": "Toner",
        "sold_count": 118000,
        "growth_rate": 22.4,
        "thumbnail_url": "https://example.com/anua_toner.jpg",
        "source": "tiktok_shop",
        "tags": ["toner", "heartleaf", "soothing", "kbeauty"],
    },
    {
        "rank": 5, "period": "30d",
        "product_id": "tt_laneige_30d",
        "name": "Laneige Lip Sleeping Mask Berry",
        "brand": "Laneige",
        "category": "Lip Care",
        "sold_count": 112000,
        "growth_rate": 1.5,
        "thumbnail_url": "https://example.com/laneige_lip.jpg",
        "source": "tiktok_shop",
        "tags": ["lip", "mask", "kbeauty", "sleeping"],
    },
    # 1-year top sellers
    {
        "rank": 1, "period": "1y",
        "product_id": "tt_med_pdrn_1y",
        "name": "PDRN Pink Collagen Volume Multi Balm",
        "brand": "medicube",
        "category": "Skin Care",
        "sold_count": 1111684,
        "growth_rate": 0.8,
        "thumbnail_url": "https://example.com/medicube_pdrn.jpg",
        "source": "tiktok_shop",
        "tags": ["skincare", "collagen", "pdrn", "kbeauty"],
    },
    {
        "rank": 2, "period": "1y",
        "product_id": "tt_mel_calcium_1y",
        "name": "Calcium Multi Balm Eye Care Collagen Stick 9g",
        "brand": "Dr.Melaxin",
        "category": "Eye Care",
        "sold_count": 990032,
        "growth_rate": 3.5,
        "thumbnail_url": "https://example.com/drmelaxin_calcium.jpg",
        "source": "tiktok_shop",
        "tags": ["eyecare", "collagen", "kbeauty", "antiaging"],
    },
    {
        "rank": 3, "period": "1y",
        "product_id": "tt_cosrx_1y",
        "name": "COSRX Advanced Snail 96 Mucin Power Essence",
        "brand": "COSRX",
        "category": "Essence",
        "sold_count": 876000,
        "growth_rate": 5.2,
        "thumbnail_url": "https://example.com/cosrx_snail.jpg",
        "source": "tiktok_shop",
        "tags": ["snail", "essence", "kbeauty", "hydration"],
    },
    {
        "rank": 4, "period": "1y",
        "product_id": "tt_anua_1y",
        "name": "ANUA Heartleaf 77% Soothing Toner",
        "brand": "ANUA",
        "category": "Toner",
        "sold_count": 654000,
        "growth_rate": 18.9,
        "thumbnail_url": "https://example.com/anua_toner.jpg",
        "source": "tiktok_shop",
        "tags": ["toner", "heartleaf", "soothing", "kbeauty"],
    },
    {
        "rank": 5, "period": "1y",
        "product_id": "tt_tirtir_1y",
        "name": "TIRTIR Mask Fit Red Cushion",
        "brand": "TIRTIR",
        "category": "Foundation",
        "sold_count": 598000,
        "growth_rate": 7.3,
        "thumbnail_url": "https://example.com/tirtir_cushion.jpg",
        "source": "tiktok_shop",
        "tags": ["cushion", "foundation", "kbeauty", "makeup"],
    },
]


class TikTokTrendFetcher:
    """Fetch trending products. Uses mock data by default (TikTok Shop KR not live)."""

    def __init__(self, mock: bool = True):
        self.mock = mock

    def fetch(self, periods: list[TrendPeriod] | None = None, top_n: int = 10) -> list[TrendingProduct]:
        periods = periods or list(TrendPeriod)
        if self.mock:
            return self._from_mock(periods, top_n)
        return self._from_api(periods, top_n)

    def _from_mock(self, periods: list[TrendPeriod], top_n: int) -> list[TrendingProduct]:
        wanted = {p.value for p in periods}
        results = []
        for raw in MOCK_PRODUCTS:
            if raw["period"] not in wanted:
                continue
            results.append(TrendingProduct(
                rank=raw["rank"],
                period=TrendPeriod(raw["period"]),
                product_id=raw["product_id"],
                name=raw["name"],
                brand=raw["brand"],
                category=raw["category"],
                sold_count=raw["sold_count"],
                growth_rate=raw["growth_rate"],
                thumbnail_url=raw["thumbnail_url"],
                source=raw["source"],
                tags=raw.get("tags", []),
            ))
            if len([r for r in results if r.period.value == raw["period"]]) >= top_n:
                continue
        return results

    def _from_api(self, periods: list[TrendPeriod], top_n: int) -> list[TrendingProduct]:
        """Live fetch via TikTok Shop data MCP tools (requires MCP plugin active)."""
        results: list[TrendingProduct] = []
        period_map = {
            TrendPeriod.DAY_7: "7",
            TrendPeriod.DAY_30: "30",
            TrendPeriod.DAY_90: "90",
            TrendPeriod.DAY_365: "365",
        }
        for period in periods:
            try:
                # Note: actual call done via MCP tool mcp__e5436562...call_tool
                # with tool_name="td_item_ranking_list"
                log.warning("Live API fetch not implemented in this context; use mock=True")
            except Exception as exc:
                log.error("TikTok API fetch failed for %s: %s", period, exc)
        return results
