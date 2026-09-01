from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from shopping_shorts_sync.facebook.client import (
    FacebookApiError,
    FacebookPageClient,
    FBPostResult,
    MockFacebookPageClient,
)


class TestFBPostResult:
    def test_ok_when_post_id_set(self):
        r = FBPostResult(product_id="p1", post_id="123")
        assert r.ok is True

    def test_not_ok_when_post_id_none(self):
        r = FBPostResult(product_id="p1", post_id=None, error="boom")
        assert r.ok is False

    def test_not_ok_when_error_set(self):
        r = FBPostResult(product_id="p1", post_id="123", error="bad")
        assert r.ok is False

    def test_is_scheduled_when_scheduled_publish_time_set(self):
        r = FBPostResult(product_id="p1", post_id="123", scheduled_publish_time=9999999)
        assert r.is_scheduled is True

    def test_not_scheduled_by_default(self):
        r = FBPostResult(product_id="p1", post_id="123")
        assert r.is_scheduled is False


class TestFacebookPageClientInit:
    def test_raises_without_page_id(self):
        with pytest.raises(FacebookApiError):
            FacebookPageClient("", "token")

    def test_raises_without_token(self):
        with pytest.raises(FacebookApiError):
            FacebookPageClient("page123", "")

    def test_stores_credentials(self):
        client = FacebookPageClient("page123", "mytoken")
        assert client.page_id == "page123"
        assert client.page_access_token == "mytoken"


class TestFacebookPageClientPostPhoto:
    def _make_client(self):
        return FacebookPageClient("page123", "token")

    def test_success_immediate(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "post-abc"}

        with patch("shopping_shorts_sync.facebook.client.requests.post", return_value=mock_resp):
            client = self._make_client()
            result = client.post_photo("p1", "https://img.example.com/x.jpg", "caption text")

        assert result.ok
        assert result.post_id == "post-abc"
        assert result.product_id == "p1"
        assert result.scheduled_publish_time is None

    def test_success_scheduled(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "post-sched"}

        with patch("shopping_shorts_sync.facebook.client.requests.post", return_value=mock_resp) as mock_post:
            client = self._make_client()
            result = client.post_photo("p1", "https://img.example.com/x.jpg", "caption", scheduled_publish_time=9999999)

        assert result.ok
        assert result.scheduled_publish_time == 9999999
        assert result.is_scheduled

        call_kwargs = mock_post.call_args
        sent_params = call_kwargs[1]["params"]
        assert sent_params["published"] == "false"
        assert sent_params["scheduled_publish_time"] == "9999999"

    def test_api_error_response(self):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.json.return_value = {"error": {"message": "invalid token"}}

        with patch("shopping_shorts_sync.facebook.client.requests.post", return_value=mock_resp):
            client = self._make_client()
            result = client.post_photo("p1", "https://img.example.com/x.jpg", "caption")

        assert not result.ok
        assert result.post_id is None
        assert "invalid token" in result.error

    def test_missing_id_in_response(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {}

        with patch("shopping_shorts_sync.facebook.client.requests.post", return_value=mock_resp):
            client = self._make_client()
            result = client.post_photo("p1", "https://img.example.com/x.jpg", "caption")

        assert not result.ok
        assert result.post_id is None

    def test_posts_to_correct_endpoint(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "post-xyz"}

        with patch("shopping_shorts_sync.facebook.client.requests.post", return_value=mock_resp) as mock_post:
            client = FacebookPageClient("mypageid", "token")
            client.post_photo("p1", "https://img.example.com/x.jpg", "caption")

        url = mock_post.call_args[0][0]
        assert "mypageid/photos" in url


class TestMockFacebookPageClient:
    def test_returns_deterministic_post_id(self):
        client = MockFacebookPageClient()
        r1 = client.post_photo("prod-a", "https://img.example.com/x.jpg", "caption")
        r2 = client.post_photo("prod-a", "https://img.example.com/x.jpg", "caption")
        assert r1.post_id == r2.post_id

    def test_different_product_ids_differ(self):
        client = MockFacebookPageClient()
        r1 = client.post_photo("prod-a", "https://img.example.com/x.jpg", "cap")
        r2 = client.post_photo("prod-b", "https://img.example.com/x.jpg", "cap")
        assert r1.post_id != r2.post_id

    def test_ok_result(self):
        client = MockFacebookPageClient()
        r = client.post_photo("p1", "https://img.example.com/x.jpg", "cap")
        assert r.ok
        assert r.post_id is not None
        assert r.post_id.startswith("mock-fb-")

    def test_scheduled(self):
        client = MockFacebookPageClient()
        r = client.post_photo("p1", "https://img.example.com/x.jpg", "cap", scheduled_publish_time=999)
        assert r.is_scheduled
        assert r.scheduled_publish_time == 999
