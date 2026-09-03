import pytest

from shopping_shorts_sync.search.instagram import (
    GRAPH_API_BASE,
    HASHTAG_SEARCH_URL,
    InstagramApiError,
    InstagramSearchClient,
)


def test_search_parses_video_results(requests_mock):
    requests_mock.get(HASHTAG_SEARCH_URL, json={"data": [{"id": "hash123"}]})
    requests_mock.get(
        f"{GRAPH_API_BASE}/hash123/top_media",
        json={
            "data": [
                {
                    "id": "1",
                    "caption": "무선청소기 리뷰\n더보기",
                    "media_type": "VIDEO",
                    "thumbnail_url": "https://example.com/thumb.jpg",
                    "permalink": "https://www.instagram.com/p/abc/",
                }
            ]
        },
    )

    client = InstagramSearchClient(access_token="token", ig_user_id="ig123")
    results = client.search("무선 청소기")

    assert len(results) == 1
    assert results[0].source == "instagram"
    assert results[0].name == "무선청소기 리뷰"
    assert results[0].image_url == "https://example.com/thumb.jpg"
    assert results[0].product_url == "https://www.instagram.com/p/abc/"


def test_search_filters_out_non_video_media(requests_mock):
    requests_mock.get(HASHTAG_SEARCH_URL, json={"data": [{"id": "hash123"}]})
    requests_mock.get(
        f"{GRAPH_API_BASE}/hash123/top_media",
        json={
            "data": [
                {"id": "1", "media_type": "IMAGE", "permalink": "https://instagram.com/p/img/"},
                {"id": "2", "media_type": "VIDEO", "permalink": "https://instagram.com/p/vid/", "caption": "영상"},
            ]
        },
    )

    client = InstagramSearchClient(access_token="token", ig_user_id="ig123")
    results = client.search("청소기")

    assert len(results) == 1
    assert results[0].product_url == "https://instagram.com/p/vid/"


def test_search_respects_limit(requests_mock):
    requests_mock.get(HASHTAG_SEARCH_URL, json={"data": [{"id": "hash123"}]})
    requests_mock.get(
        f"{GRAPH_API_BASE}/hash123/top_media",
        json={
            "data": [
                {"id": str(i), "media_type": "VIDEO", "permalink": f"https://instagram.com/p/{i}/"}
                for i in range(10)
            ]
        },
    )
    client = InstagramSearchClient(access_token="token", ig_user_id="ig123")
    assert len(client.search("x", limit=3)) == 3


def test_no_hashtag_match_returns_empty(requests_mock):
    requests_mock.get(HASHTAG_SEARCH_URL, json={"data": []})
    client = InstagramSearchClient(access_token="token", ig_user_id="ig123")
    assert client.search("존재하지않는해시태그") == []


def test_missing_credentials_raises():
    with pytest.raises(InstagramApiError):
        InstagramSearchClient(access_token="", ig_user_id="")
