import pytest

from shopping_shorts_sync.search.youtube import API_URL, YouTubeApiError, YouTubeSearchClient


def test_search_parses_results(requests_mock):
    requests_mock.get(
        API_URL,
        json={
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {
                        "title": "무선 청소기 XYZ 리뷰",
                        "channelTitle": "리뷰채널",
                        "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
                    },
                }
            ]
        },
    )

    client = YouTubeSearchClient(api_key="key")
    results = client.search("무선 청소기")

    assert len(results) == 1
    assert results[0].source == "youtube"
    assert results[0].name == "무선 청소기 XYZ 리뷰"
    assert results[0].product_url == "https://www.youtube.com/watch?v=abc123"
    assert results[0].image_url == "https://example.com/thumb.jpg"
    assert results[0].price is None


def test_search_respects_limit(requests_mock):
    requests_mock.get(
        API_URL,
        json={
            "items": [
                {"id": {"videoId": f"v{i}"}, "snippet": {"title": f"item {i}", "thumbnails": {}}}
                for i in range(10)
            ]
        },
    )
    client = YouTubeSearchClient(api_key="key")
    assert len(client.search("x", limit=3)) == 3


def test_items_without_video_id_are_skipped(requests_mock):
    requests_mock.get(
        API_URL,
        json={"items": [{"id": {}, "snippet": {"title": "no id"}}]},
    )
    client = YouTubeSearchClient(api_key="key")
    assert client.search("x") == []


def test_missing_api_key_raises():
    with pytest.raises(YouTubeApiError):
        YouTubeSearchClient(api_key="")
