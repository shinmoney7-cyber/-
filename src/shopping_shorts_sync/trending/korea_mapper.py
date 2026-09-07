"""Map global TikTok trending products to Korean platform purchase links.

Coupang affiliate deeplinks, Naver Shopping, Daiso, Olive Young.
Uses a curated static map for known K-beauty brands + search URL fallback.
"""
from __future__ import annotations

import logging
import urllib.parse

from .models import KoreaMatch, TrendingProduct

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known product map: brand+keywords → Korean purchase data
# ---------------------------------------------------------------------------
_KNOWN: list[dict] = [
    {
        "keywords": ["medicube", "pdrn", "collagen", "balm"],
        "local_name": "메디큐브 PDRN 핑크 콜라겐 멀티밤",
        "platforms": ["coupang", "oliveyoung", "naver"],
        "coupang_path": "/vp/products/7332040419",
        "oliveyoung_keyword": "메디큐브 PDRN 멀티밤",
        "approx_krw": 32000,
    },
    {
        "keywords": ["dr.melaxin", "drmelaxin", "calcium", "eye", "balm"],
        "local_name": "닥터멜라신 칼슘 아이케어 콜라겐 스틱",
        "platforms": ["coupang", "oliveyoung", "naver"],
        "coupang_path": "/vp/products/7198234512",
        "oliveyoung_keyword": "닥터멜라신 아이밤",
        "approx_krw": 28000,
    },
    {
        "keywords": ["cosrx", "snail", "mucin", "essence"],
        "local_name": "COSRX 어드밴스드 스네일 96 뮤신 에센스",
        "platforms": ["coupang", "oliveyoung", "naver"],
        "coupang_path": "/vp/products/4974921817",
        "oliveyoung_keyword": "COSRX 스네일 에센스",
        "approx_krw": 22000,
    },
    {
        "keywords": ["anua", "heartleaf", "toner", "soothing"],
        "local_name": "아누아 어성초 77 진정 토너",
        "platforms": ["coupang", "oliveyoung", "naver"],
        "coupang_path": "/vp/products/7055819234",
        "oliveyoung_keyword": "아누아 어성초 토너",
        "approx_krw": 19800,
    },
    {
        "keywords": ["laneige", "lip", "sleeping", "mask"],
        "local_name": "라네즈 립 슬리핑 마스크 베리",
        "platforms": ["coupang", "oliveyoung", "naver"],
        "coupang_path": "/vp/products/3948201756",
        "oliveyoung_keyword": "라네즈 립 슬리핑마스크",
        "approx_krw": 14000,
    },
    {
        "keywords": ["tirtir", "mask fit", "cushion", "red"],
        "local_name": "티르티르 마스크핏 레드 쿠션",
        "platforms": ["coupang", "oliveyoung", "naver"],
        "coupang_path": "/vp/products/6812034521",
        "oliveyoung_keyword": "티르티르 레드쿠션",
        "approx_krw": 26000,
    },
    {
        "keywords": ["some by mi", "somebymi", "aha", "bha", "toner", "miracle"],
        "local_name": "섬바이미 AHA BHA PHA 30 데이즈 미라클 토너",
        "platforms": ["coupang", "oliveyoung", "naver"],
        "coupang_path": "/vp/products/5123874521",
        "oliveyoung_keyword": "섬바이미 AHA BHA 토너",
        "approx_krw": 17500,
    },
    {
        "keywords": ["crest", "teeth", "whitening", "strips"],
        "local_name": "치아미백 스트립 (화이트닝)",
        "platforms": ["coupang", "naver"],
        "coupang_path": "/vp/products/6234891023",
        "oliveyoung_keyword": "치아미백 스트립",
        "approx_krw": 35000,
    },
]

COUPANG_BASE = "https://www.coupang.com"
NAVER_SHOPPING_BASE = "https://search.shopping.naver.com/search/all"
OLIVEYOUNG_BASE = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do"
DAISO_BASE = "https://www.daisomall.co.kr/search"


class KoreaMapper:
    """Map TrendingProduct to KoreaMatch with purchase links."""

    def map(self, product: TrendingProduct) -> KoreaMatch:
        match = KoreaMatch(trending=product)
        entry = self._find_entry(product)
        if entry:
            match.local_product_name = entry["local_name"]
            match.local_price_krw = entry["approx_krw"]
            match.available_platforms = entry["platforms"]
            if "coupang" in entry["platforms"]:
                match.coupang_url = COUPANG_BASE + entry["coupang_path"]
                match.coupang_deeplink = self._coupang_deeplink(entry["coupang_path"])
            if "oliveyoung" in entry["platforms"] and entry.get("oliveyoung_keyword"):
                match.oliveyoung_url = self._oliveyoung_url(entry["oliveyoung_keyword"])
            if "naver" in entry["platforms"]:
                match.naver_url = self._naver_url(entry.get("local_name", product.name))
        else:
            # Fallback: search URLs
            match.local_product_name = product.name
            match.available_platforms = ["coupang", "naver"]
            match.coupang_url = self._naver_url(product.name)
            match.naver_url = self._naver_url(product.name)
            match.coupang_deeplink = ""
        return match

    def map_all(self, products: list[TrendingProduct]) -> list[KoreaMatch]:
        return [self.map(p) for p in products]

    def _find_entry(self, product: TrendingProduct) -> dict | None:
        text = (product.name + " " + product.brand).lower()
        best_entry = None
        best_hits = 0
        for entry in _KNOWN:
            hits = sum(1 for kw in entry["keywords"] if kw in text)
            if hits > best_hits:
                best_hits = hits
                best_entry = entry
        return best_entry if best_hits >= 2 else None

    def _coupang_deeplink(self, path: str) -> str:
        return f"https://link.coupang.com/a/bDummyAff?link={urllib.parse.quote(COUPANG_BASE + path)}"

    def _naver_url(self, query: str) -> str:
        return f"{NAVER_SHOPPING_BASE}?query={urllib.parse.quote(query)}"

    def _oliveyoung_url(self, keyword: str) -> str:
        return f"{OLIVEYOUNG_BASE}?query={urllib.parse.quote(keyword)}"

    def _daiso_url(self, keyword: str) -> str:
        return f"{DAISO_BASE}?searchWord={urllib.parse.quote(keyword)}"
