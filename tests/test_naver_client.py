import pytest

from shopping_shorts_sync.search.naver import API_URL, NaverApiError, NaverShopClient


def test_search_parses_results(requests_mock):
    requests_mock.get(
        API_URL,
        json={
            "items": [
                {
                    "title": "<b>무선</b> 청소기 XYZ",
                    "link": "https://shopping.naver.com/x",
                    "image": "https://example.com/x.jpg",
                    "lprice": "50000",
                }
            ]
        },
    )

    client = NaverShopClient(client_id="id", client_secret="secret")
    results = client.search("무선 청소기")

    assert len(results) == 1
    assert results[0].name == "무선 청소기 XYZ"  # <b> tags stripped
    assert results[0].source == "naver"
    assert results[0].price == "50000"


def test_search_respects_limit(requests_mock):
    requests_mock.get(
        API_URL,
        json={"items": [{"title": f"item {i}", "link": "x", "image": "y"} for i in range(10)]},
    )
    client = NaverShopClient(client_id="id", client_secret="secret")
    assert len(client.search("x", limit=3)) == 3


def test_missing_credentials_raises():
    with pytest.raises(NaverApiError):
        NaverShopClient(client_id="", client_secret="")
