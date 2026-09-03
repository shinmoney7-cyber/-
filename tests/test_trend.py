import json

import pytest

from shopping_shorts_sync.trend import NaverAdApiError, NaverAdKeywordClient, TrendHistoryStore, build_trend_client
from shopping_shorts_sync.trend.history_store import _prev_month, current_month
from shopping_shorts_sync.trend.mock import MockKeywordTrendClient
from shopping_shorts_sync.trend.naver_ad import API_HOST, URI, _parse_count
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
