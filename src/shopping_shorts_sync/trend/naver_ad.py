"""Naver 검색광고(SearchAd) API -- 키워드 도구(keywordstool).

Official endpoint for monthly PC/mobile search volume + competition level
per keyword (the same underlying data source tools like 아이템스카우트/
판다랭크 build their UI on top of). This session's network policy blocks
api.naver.com, so this client has not been exercised against the live
endpoint -- verify the response field names once a real key is issued,
see docs/CALIBRATION.md.
"""
from __future__ import annotations

import requests

from .models import KeywordTrend
from .signing import build_headers

API_HOST = "https://api.naver.com"
URI = "/keywordstool"


class NaverAdApiError(RuntimeError):
    pass


class NaverAdKeywordClient:
    def __init__(self, api_key: str, secret_key: str, customer_id: str, timeout: float = 10.0):
        if not api_key or not secret_key or not customer_id:
            raise NaverAdApiError(
                "NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY and NAVER_AD_CUSTOMER_ID are required in live mode"
            )
        self.api_key = api_key
        self.secret_key = secret_key
        self.customer_id = customer_id
        self.timeout = timeout

    def search(self, keywords: list[str]) -> list[KeywordTrend]:
        """`keywords`: up to 5 seed keywords per Naver's documented limit."""
        headers = build_headers(self.api_key, self.secret_key, self.customer_id, "GET", URI)
        response = requests.get(
            f"{API_HOST}{URI}",
            params={"hintKeywords": ",".join(keywords), "showDetail": "1"},
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()

        results = []
        for item in body.get("keywordList", []):
            results.append(
                KeywordTrend(
                    keyword=item.get("relKeyword", ""),
                    monthly_pc_count=_parse_count(item.get("monthlyPcQcCnt")),
                    monthly_mobile_count=_parse_count(item.get("monthlyMobileQcCnt")),
                    comp_idx=item.get("compIdx"),
                )
            )
        return results


def _parse_count(value) -> int:
    """Naver returns "< 10" for very low volume instead of a number."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("<").strip().isdigit():
        return int(value.strip().lstrip("<").strip())
    return 0
