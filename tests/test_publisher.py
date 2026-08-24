import dataclasses

import pytest

from shopping_shorts_sync.config import load_config
from shopping_shorts_sync.publisher import (
    InstagramPublisher,
    TikTokPublisher,
    YouTubePublisher,
    build_publisher,
    public_video_url,
)

_TIKTOK_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"


def _config(**overrides):
    config = load_config(env_file="/nonexistent/.env")
    return dataclasses.replace(config, **overrides)


# ---------------------------------------------------------------------
# dry_run: no network for any of the three
# ---------------------------------------------------------------------


def test_tiktok_dry_run_returns_success_without_network():
    publisher = TikTokPublisher(access_token="", dry_run=True)
    result = publisher.publish("does/not/exist.mp4", "caption", "product")
    assert result.success is True
    assert result.platform == "tiktok"


def test_youtube_dry_run_returns_success_without_network():
    publisher = YouTubePublisher(client_secrets_file="", dry_run=True)
    result = publisher.publish("does/not/exist.mp4", "caption", "product")
    assert result.success is True
    assert result.platform == "youtube"
    assert result.post_url.startswith("https://www.youtube.com/watch?v=")


def test_instagram_dry_run_returns_success_without_network():
    publisher = InstagramPublisher(access_token="", ig_user_id="", dry_run=True)
    result = publisher.publish("https://example.com/video.mp4", "caption", "product")
    assert result.success is True
    assert result.platform == "instagram"


# ---------------------------------------------------------------------
# TikTok live flow (requests_mock)
# ---------------------------------------------------------------------


def test_tiktok_publish_uploads_chunks(requests_mock, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x" * 100)

    upload_url = "https://open.tiktokapis.com/upload/abc"
    requests_mock.post(
        _TIKTOK_INIT_URL,
        json={"data": {"publish_id": "pub123", "upload_url": upload_url}, "error": {"code": "ok"}},
    )
    requests_mock.put(upload_url, status_code=201)

    publisher = TikTokPublisher(access_token="tok")
    result = publisher.publish(str(video), "caption text", "product")

    assert result.success is True
    assert result.post_id == "pub123"
    assert requests_mock.last_request.method == "PUT"


def test_tiktok_publish_returns_error_on_api_error(requests_mock, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x" * 10)

    requests_mock.post(
        _TIKTOK_INIT_URL,
        json={"error": {"code": "invalid_param", "message": "bad title"}},
    )

    publisher = TikTokPublisher(access_token="tok")
    result = publisher.publish(str(video), "caption text", "product")

    assert result.success is False
    assert "invalid_param" in result.error


def test_tiktok_publish_returns_error_on_network_failure(requests_mock, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x" * 10)

    requests_mock.post(_TIKTOK_INIT_URL, status_code=500)

    publisher = TikTokPublisher(access_token="tok")
    result = publisher.publish(str(video), "caption text", "product")

    assert result.success is False
    assert result.error


# ---------------------------------------------------------------------
# Instagram live flow (requests_mock)
# ---------------------------------------------------------------------


def test_instagram_publish_creates_polls_and_publishes(requests_mock, monkeypatch):
    monkeypatch.setattr("shopping_shorts_sync.publisher.instagram.time.sleep", lambda _s: None)

    account_id = "ig123"
    creation_id = "creation456"
    media_id = "media789"

    requests_mock.post(
        f"https://graph.facebook.com/v19.0/{account_id}/media",
        json={"id": creation_id},
    )
    requests_mock.get(
        f"https://graph.facebook.com/v19.0/{creation_id}",
        [
            {"json": {"status_code": "IN_PROGRESS", "status": "processing"}},
            {"json": {"status_code": "FINISHED", "status": "ok"}},
        ],
    )
    requests_mock.post(
        f"https://graph.facebook.com/v19.0/{account_id}/media_publish",
        json={"id": media_id},
    )

    publisher = InstagramPublisher(access_token="tok", ig_user_id=account_id)
    result = publisher.publish("https://example.com/video.mp4", "caption", "product")

    assert result.success is True
    assert result.post_id == media_id
    assert result.post_url == f"https://www.instagram.com/p/{media_id}/"


def test_instagram_publish_returns_error_on_container_failure(requests_mock):
    account_id = "ig123"
    creation_id = "creation456"

    requests_mock.post(
        f"https://graph.facebook.com/v19.0/{account_id}/media",
        json={"id": creation_id},
    )
    requests_mock.get(
        f"https://graph.facebook.com/v19.0/{creation_id}",
        json={"status_code": "ERROR", "status": "publishing_error"},
    )

    publisher = InstagramPublisher(access_token="tok", ig_user_id=account_id)
    result = publisher.publish("https://example.com/video.mp4", "caption", "product")

    assert result.success is False
    assert "publishing_error" in result.error


def test_instagram_publish_returns_error_on_graph_api_error(requests_mock):
    account_id = "ig123"
    requests_mock.post(
        f"https://graph.facebook.com/v19.0/{account_id}/media",
        json={"error": {"code": 100, "type": "OAuthException", "message": "bad token"}},
    )

    publisher = InstagramPublisher(access_token="badtok", ig_user_id=account_id)
    result = publisher.publish("https://example.com/video.mp4", "caption", "product")

    assert result.success is False
    assert "bad token" in result.error


# ---------------------------------------------------------------------
# YouTube live flow (monkeypatched service, no real OAuth)
# ---------------------------------------------------------------------


class _FakeRequest:
    def next_chunk(self):
        return None, {"id": "yt123"}


class _FakeVideosResource:
    def insert(self, part, body, media_body):
        return _FakeRequest()


class _FakeService:
    def videos(self):
        return _FakeVideosResource()


def test_youtube_publish_uses_resumable_upload(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x" * 10)

    publisher = YouTubePublisher(client_secrets_file="secrets.json")
    monkeypatch.setattr(publisher, "_build_service", lambda: _FakeService())

    result = publisher.publish(str(video), "caption", "product name")

    assert result.success is True
    assert result.post_id == "yt123"
    assert result.post_url == "https://www.youtube.com/watch?v=yt123"


def test_youtube_publish_returns_error_when_service_build_fails(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x" * 10)

    publisher = YouTubePublisher(client_secrets_file="secrets.json")

    def _raise():
        raise RuntimeError("oauth flow failed")

    monkeypatch.setattr(publisher, "_build_service", _raise)

    result = publisher.publish(str(video), "caption", "product name")

    assert result.success is False
    assert "oauth flow failed" in result.error


# ---------------------------------------------------------------------
# build_publisher / public_video_url
# ---------------------------------------------------------------------


def test_build_publisher_returns_matching_class():
    config = _config(tiktok_access_token="t", instagram_access_token="a", instagram_ig_user_id="u")
    assert isinstance(build_publisher("tiktok", config), TikTokPublisher)
    assert isinstance(build_publisher("youtube", config), YouTubePublisher)
    assert isinstance(build_publisher("instagram", config), InstagramPublisher)


def test_build_publisher_unknown_platform_raises():
    config = _config()
    with pytest.raises(ValueError):
        build_publisher("threads", config)


def test_public_video_url_none_when_not_configured():
    config = _config(public_base_url="")
    assert public_video_url(config, "p1", "/data/videos/p1/stitched.mp4") is None


def test_public_video_url_builds_from_base_and_filename():
    config = _config(public_base_url="https://example.onrender.com/")
    url = public_video_url(config, "p1", "/data/videos/p1/stitched.mp4")
    assert url == "https://example.onrender.com/videos/p1/stitched.mp4"
