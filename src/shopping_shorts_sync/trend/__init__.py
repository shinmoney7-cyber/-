from __future__ import annotations

from ..config import Config
from .history_store import TrendHistoryStore
from .models import KeywordTrend
from .naver_ad import NaverAdApiError, NaverAdKeywordClient

__all__ = [
    "KeywordTrend",
    "NaverAdApiError",
    "NaverAdKeywordClient",
    "TrendHistoryStore",
    "build_trend_client",
]


def build_trend_client(config: Config, dry_run: bool = True):
    """Mirrors `sync.build_coupang_client`'s mock/live factory pattern."""
    if dry_run:
        from .mock import MockKeywordTrendClient

        return MockKeywordTrendClient()

    return NaverAdKeywordClient(
        api_key=config.naver_ad_api_key,
        secret_key=config.naver_ad_secret_key,
        customer_id=config.naver_ad_customer_id,
    )
