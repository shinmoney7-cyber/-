from __future__ import annotations

from ..config import Config
from .categories import CATEGORIES
from .history_store import TrendHistoryStore
from .models import CategoryKeywordRank, KeywordTrend
from .naver_ad import NaverAdApiError, NaverAdKeywordClient
from .naver_datalab import NaverDatalabApiError, NaverDatalabCategoryRankClient
from .rank_history_store import RankHistoryStore

__all__ = [
    "CATEGORIES",
    "CategoryKeywordRank",
    "KeywordTrend",
    "NaverAdApiError",
    "NaverAdKeywordClient",
    "NaverDatalabApiError",
    "NaverDatalabCategoryRankClient",
    "RankHistoryStore",
    "TrendHistoryStore",
    "build_trend_client",
    "build_category_rank_client",
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


def build_category_rank_client(config: Config, dry_run: bool = True):
    if dry_run:
        from .mock import MockCategoryRankClient

        return MockCategoryRankClient()

    return NaverDatalabCategoryRankClient(
        client_id=config.naver_client_id,
        client_secret=config.naver_client_secret,
    )
