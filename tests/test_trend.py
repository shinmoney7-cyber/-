import json
from datetime import date

import pytest

from shopping_shorts_sync.trend import (
    NaverAdApiError,
    NaverAdKeywordClient,
    NaverDatalabApiError,
    NaverDatalabCategoryRankClient,
    RankHistoryStore,
    TrendHistoryStore,
    build_category_rank_client,
    build_trend_client,
)
from shopping_shorts_sync.trend.history_store import _prev_month, current_month
from shopping_shorts_sync.trend.mock import MockCategoryRankClient, MockKeywordTrendClient
from shopping_shorts_sync.trend.models import CategoryKeywordRank
from shopping_shorts_sync.trend.naver_ad import API_HOST, URI, _parse_count
from shopping_shorts_sync.trend.naver_datalab import API_URL as DATALAB_API_URL
from shopping_shorts_sync.trend.signing import build_headers, build_signature


# ---------------------------------------------------------------------
# mock client
# ---------------------------------------------------------------------


def test_mock_client_is_deterministic():
    client = MockKeywordTrendClient()
    first = client.search(["무타공 수납장"])
    second = client.search(["무타공 수납장"])
    assert first == second


def test_mock_client_returns_one_trend_per_keyword():
    client = MockKeywordTrendClient()
    results = client.search(["a", "b", "c"])
    assert [t.keyword for t in results] == ["a", "b", "c"]
    for t in results:
        assert t.monthly_total_count == t.monthly_pc_count + t.monthly_mobile_count
        assert t.growth_pct is None


# ---------------------------------------------------------------------
# signing
# ---------------------------------------------------------------------


def test_build_signature_is_deterministic_for_fixed_timestamp():
    sig1 = build_signature("secret", "1700000000000", "GET", "/keywordstool")
    sig2 = build_signature("secret", "1700000000000", "GET", "/keywordstool")
    assert sig1 == sig2


def test_build_signature_requires_secret_key():
    with pytest.raises(ValueError):
        build_signature("", "1700000000000", "GET", "/keywordstool")


def test_build_headers_contains_expected_keys():
    headers = build_headers("api-key", "secret", "customer-1", "GET", "/keywordstool")
    assert set(headers) == {"X-Timestamp", "X-API-KEY", "X-Customer", "X-Signature"}
    assert headers["X-API-KEY"] == "api-key"
    assert headers["X-Customer"] == "customer-1"


# ---------------------------------------------------------------------
# naver_ad live client (requests_mock)
# ---------------------------------------------------------------------


def test_naver_ad_client_requires_credentials():
    with pytest.raises(NaverAdApiError):
        NaverAdKeywordClient(api_key="", secret_key="", customer_id="")


def test_naver_ad_client_parses_keyword_list(requests_mock):
    requests_mock.get(
        f"{API_HOST}{URI}",
        json={
            "keywordList": [
                {
                    "relKeyword": "무타공 수납장",
                    "monthlyPcQcCnt": 1200,
                    "monthlyMobileQcCnt": 8900,
                    "compIdx": "중간",
                }
            ]
        },
    )
    client = NaverAdKeywordClient(api_key="k", secret_key="s", customer_id="c")
    results = client.search(["무타공 수납장"])

    assert len(results) == 1
    assert results[0].keyword == "무타공 수납장"
    assert results[0].monthly_pc_count == 1200
    assert results[0].monthly_mobile_count == 8900
    assert results[0].comp_idx == "중간"

    sent_headers = requests_mock.last_request.headers
    assert sent_headers["X-API-KEY"] == "k"
    assert sent_headers["X-Customer"] == "c"

    # Naver rejects hintKeywords containing spaces with a 400 (confirmed
    # against the live API) -- space-separated phrases must be sent compound.
    assert requests_mock.last_request.qs["hintkeywords"] == ["무타공수납장"]


def test_parse_count_handles_low_volume_string():
    assert _parse_count("< 10") == 10
    assert _parse_count(500) == 500
    assert _parse_count(None) == 0


# ---------------------------------------------------------------------
# history store (전월 대비 증가율)
# ---------------------------------------------------------------------


def test_prev_month_wraps_year_boundary():
    assert _prev_month("2026-01") == "2025-12"
    assert _prev_month("2026-09") == "2026-08"


def test_history_store_first_query_has_no_growth(tmp_path):
    store = TrendHistoryStore(tmp_path / "history.json")
    trends = MockKeywordTrendClient().search(["키워드1"])
    enriched = store.apply(trends, month="2026-09")
    assert enriched[0].growth_pct is None


def test_history_store_computes_growth_on_second_month(tmp_path):
    path = tmp_path / "history.json"
    store = TrendHistoryStore(path)
    store.record("키워드1", "2026-08", 1000)
    store.save()

    reloaded = TrendHistoryStore(path)
    from shopping_shorts_sync.trend.models import KeywordTrend

    trend = KeywordTrend(keyword="키워드1", monthly_pc_count=600, monthly_mobile_count=600, comp_idx="낮음")
    enriched = reloaded.apply([trend], month="2026-09")

    assert enriched[0].growth_pct == pytest.approx(20.0)


def test_history_store_persists_across_instances(tmp_path):
    path = tmp_path / "history.json"
    store = TrendHistoryStore(path)
    store.record("키워드1", "2026-08", 500)
    store.save()

    assert json.loads(path.read_text())["키워드1"]["2026-08"] == 500


def test_current_month_format():
    assert len(current_month().split("-")) == 2


# ---------------------------------------------------------------------
# factory
# ---------------------------------------------------------------------


def test_build_trend_client_dry_run_returns_mock():
    import dataclasses

    from shopping_shorts_sync.config import load_config

    config = load_config(env_file="/nonexistent/.env")
    client = build_trend_client(config, dry_run=True)
    assert isinstance(client, MockKeywordTrendClient)


def test_build_trend_client_live_requires_credentials():
    import dataclasses

    from shopping_shorts_sync.config import load_config

    config = load_config(env_file="/nonexistent/.env")
    config = dataclasses.replace(config, naver_ad_api_key="", naver_ad_secret_key="", naver_ad_customer_id="")
    with pytest.raises(NaverAdApiError):
        build_trend_client(config, dry_run=False)


# ---------------------------------------------------------------------
# category rank: mock client
# ---------------------------------------------------------------------


def test_mock_category_rank_client_is_deterministic_per_day():
    client = MockCategoryRankClient()
    d = date(2026, 9, 3)
    first = client.category_rank("50000005", target_date=d)
    second = client.category_rank("50000005", target_date=d)
    assert first == second


def test_mock_category_rank_client_ranks_are_sequential():
    client = MockCategoryRankClient()
    results = client.category_rank("50000005", target_date=date(2026, 9, 3), count=5)
    assert [r.rank for r in results] == [1, 2, 3, 4, 5]
    assert len(results) == 5


# ---------------------------------------------------------------------
# category rank: naver_datalab live client (requests_mock)
# ---------------------------------------------------------------------


def test_naver_datalab_client_requires_credentials():
    with pytest.raises(NaverDatalabApiError):
        NaverDatalabCategoryRankClient(client_id="", client_secret="")


def test_naver_datalab_client_parses_ranks(requests_mock):
    requests_mock.post(
        DATALAB_API_URL,
        json={
            "categoryCode": "50000005",
            "categoryName": "식품",
            "ranks": [
                {"rank": 1, "keyword": "샤인머스캣"},
                {"rank": 2, "keyword": "홍삼스틱"},
            ],
        },
    )
    client = NaverDatalabCategoryRankClient(client_id="id", client_secret="secret")
    results = client.category_rank("50000005", target_date=date(2026, 9, 2))

    assert [r.keyword for r in results] == ["샤인머스캣", "홍삼스틱"]
    assert [r.rank for r in results] == [1, 2]

    sent_headers = requests_mock.last_request.headers
    assert sent_headers["X-Naver-Client-Id"] == "id"
    assert sent_headers["X-Naver-Client-Secret"] == "secret"

    sent_body = requests_mock.last_request.json()
    assert sent_body["category"] == "50000005"
    assert sent_body["startDate"] == sent_body["endDate"] == "2026-09-02"


def test_naver_datalab_client_raises_on_error_response(requests_mock):
    requests_mock.post(DATALAB_API_URL, status_code=400, text='{"errorMessage":"bad category"}')
    client = NaverDatalabCategoryRankClient(client_id="id", client_secret="secret")
    with pytest.raises(NaverDatalabApiError):
        client.category_rank("bad-category")


# ---------------------------------------------------------------------
# rank history store (전일 대비 순위 변동)
# ---------------------------------------------------------------------


def test_rank_history_store_first_query_has_no_prev_rank(tmp_path):
    store = RankHistoryStore(tmp_path / "ranks.json")
    ranks = [CategoryKeywordRank(rank=1, keyword="샤인머스캣")]
    enriched = store.apply("50000005", "2026-09-03", ranks)
    assert enriched[0].prev_rank is None
    assert enriched[0].rank_delta is None


def test_rank_history_store_computes_delta_on_next_day(tmp_path):
    path = tmp_path / "ranks.json"
    store = RankHistoryStore(path)
    store.record("50000005", "2026-09-02", [CategoryKeywordRank(rank=10, keyword="샤인머스캣")])
    store.save()

    reloaded = RankHistoryStore(path)
    today_ranks = [CategoryKeywordRank(rank=3, keyword="샤인머스캣")]
    enriched = reloaded.apply("50000005", "2026-09-03", today_ranks)

    assert enriched[0].prev_rank == 10
    assert enriched[0].rank_delta == 7  # 10위 -> 3위 = 7계단 상승


def test_rank_history_store_persists_across_instances(tmp_path):
    path = tmp_path / "ranks.json"
    store = RankHistoryStore(path)
    store.record("50000005", "2026-09-02", [CategoryKeywordRank(rank=1, keyword="키워드1")])
    store.save()

    assert json.loads(path.read_text())["50000005"]["2026-09-02"] == {"키워드1": 1}


# ---------------------------------------------------------------------
# category rank factory
# ---------------------------------------------------------------------


def test_build_category_rank_client_dry_run_returns_mock():
    from shopping_shorts_sync.config import load_config

    config = load_config(env_file="/nonexistent/.env")
    client = build_category_rank_client(config, dry_run=True)
    assert isinstance(client, MockCategoryRankClient)


def test_build_category_rank_client_live_requires_credentials():
    import dataclasses

    from shopping_shorts_sync.config import load_config

    config = load_config(env_file="/nonexistent/.env")
    config = dataclasses.replace(config, naver_client_id="", naver_client_secret="")
    with pytest.raises(NaverDatalabApiError):
        build_category_rank_client(config, dry_run=False)
