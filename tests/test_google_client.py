import pytest

from shopping_shorts_sync.search.google import API_URL, GoogleShopApiError, GoogleShopClient


def test_search_parses_results(requests_mock):
    requests_mock.get(
        API_URL,
        json={
            "items": [
                {
                    "title": "무선 청소기 Google XYZ",
                    "link": "https://shopping.google.com/x",
                    "image": {"thumbnailLink": "https://example.com/x.jpg"},
                    "pagemap": {"offer": [{"price": "79000"}]},
                }
            ]
        },
    )

    client = GoogleShopClient(api_key="key", cx="cx123")
    results = client.search("무선 청소기")

    assert len(results) == 1
    assert results[0].name == "무선 청소기 Google XYZ"
    assert results[0].source == "google"
    assert results[0].price == "79000"
    assert results[0].image_url == "https://example.com/x.jpg"


def test_search_respects_limit(requests_mock):
    requests_mock.get(
        API_URL,
        json={"items": [{"title": f"item {i}", "link": "x", "image": {}} for i in range(10)]},
    )
    client = GoogleShopClient(api_key="key", cx="cx123")
    assert len(client.search("x", limit=3)) == 3


def test_api_error_in_body_raises(requests_mock):
    requests_mock.get(
        API_URL,
        json={"error": {"message": "API key invalid"}},
    )
    client = GoogleShopClient(api_key="key", cx="cx123")
    with pytest.raises(GoogleShopApiError, match="API key invalid"):
        client.search("test")


def test_missing_credentials_raises():
    with pytest.raises(GoogleShopApiError):
        GoogleShopClient(api_key="", cx="")


def test_fallback_image_from_pagemap(requests_mock):
    requests_mock.get(
        API_URL,
        json={
            "items": [
                {
                    "title": "상품",
                    "link": "https://example.com",
                    "image": {},
                    "pagemap": {"cse_image": [{"src": "https://example.com/fallback.jpg"}]},
                }
            ]
        },
    )
    client = GoogleShopClient(api_key="key", cx="cx123")
    results = client.search("상품")
    assert results[0].image_url == "https://example.com/fallback.jpg"
