"""Tests for Meta API clients using requests-mock."""
from __future__ import annotations

import pytest
import requests_mock as rm_module

from shopping_shorts_sync.meta.client import MetaApiClient, MetaApiError
from shopping_shorts_sync.meta.instagram import InstagramClient
from shopping_shorts_sync.meta.threads import ThreadsClient
from shopping_shorts_sync.meta.accounts import AccountConfig, MultiAccountPublisher
from shopping_shorts_sync.meta.mock_client import MockMultiAccountPublisher

_TOKEN = "fake_token"
_IG_USER = "111"
_THREADS_USER = "222"
_GRAPH = "https://graph.facebook.com/v21.0"
_THREADS = "https://graph.threads.net/v21.0"


@pytest.fixture
def ig_client():
    return InstagramClient(_TOKEN)


@pytest.fixture
def threads_client():
    return ThreadsClient(_TOKEN)


# ── MetaApiClient ──────────────────────────────────────────────────────────

def test_graph_get_success(requests_mock):
    requests_mock.get(f"{_GRAPH}/me", json={"id": "123", "name": "Test"})
    client = MetaApiClient(_TOKEN)
    data = client.graph_get("me", fields="id,name")
    assert data["id"] == "123"


def test_graph_post_raises_on_error(requests_mock):
    requests_mock.post(f"{_GRAPH}/me/media", json={"error": {"message": "Oops", "code": 100}})
    client = MetaApiClient(_TOKEN)
    with pytest.raises(MetaApiError) as exc_info:
        client.graph_post("me/media", media_type="REELS")
    assert exc_info.value.code == 100


def test_threads_get_success(requests_mock):
    requests_mock.get(f"{_THREADS}/me", json={"id": "456"})
    client = MetaApiClient(_TOKEN)
    data = client.threads_get("me", fields="id")
    assert data["id"] == "456"


def test_poll_until_ready_succeeds(requests_mock):
    client = MetaApiClient(_TOKEN)
    call_count = [0]

    def status_fn():
        call_count[0] += 1
        return "IN_PROGRESS" if call_count[0] < 3 else "FINISHED"

    final = client.poll_until_ready(
        status_fn,
        ready_statuses={"FINISHED"},
        error_statuses={"ERROR"},
        max_attempts=5,
        interval=0,
    )
    assert final == "FINISHED"
    assert call_count[0] == 3


def test_poll_until_ready_times_out():
    client = MetaApiClient(_TOKEN)
    with pytest.raises(MetaApiError, match="not ready after"):
        client.poll_until_ready(
            lambda: "IN_PROGRESS",
            ready_statuses={"FINISHED"},
            error_statuses={"ERROR"},
            max_attempts=3,
            interval=0,
        )


# ── InstagramClient ────────────────────────────────────────────────────────

def test_create_reels_container(requests_mock, ig_client):
    requests_mock.post(f"{_GRAPH}/{_IG_USER}/media", json={"id": "container_abc"})
    cid = ig_client.create_reels_container(_IG_USER, "https://example.com/video.mp4", "caption")
    assert cid == "container_abc"


def test_get_container_status(requests_mock, ig_client):
    requests_mock.get(f"{_GRAPH}/container_abc", json={"status_code": "FINISHED"})
    status = ig_client.get_container_status("container_abc")
    assert status == "FINISHED"


def test_publish_container(requests_mock, ig_client):
    requests_mock.post(f"{_GRAPH}/{_IG_USER}/media_publish", json={"id": "media_xyz"})
    media_id = ig_client.publish_container(_IG_USER, "container_abc")
    assert media_id == "media_xyz"


def test_verify_media(requests_mock, ig_client):
    requests_mock.get(
        f"{_GRAPH}/media_xyz",
        json={"id": "media_xyz", "timestamp": "2025-01-01T00:00:00Z", "permalink": "https://ig.com/p/abc/"},
    )
    data = ig_client.verify_media("media_xyz")
    assert data["permalink"] == "https://ig.com/p/abc/"


def test_publish_reel_full_flow(requests_mock, ig_client):
    requests_mock.post(f"{_GRAPH}/{_IG_USER}/media", json={"id": "cid"})
    requests_mock.get(f"{_GRAPH}/cid", json={"status_code": "FINISHED"})
    requests_mock.post(f"{_GRAPH}/{_IG_USER}/media_publish", json={"id": "mid"})
    requests_mock.get(
        f"{_GRAPH}/mid",
        json={"id": "mid", "timestamp": "2025-01-01T00:00:00Z", "permalink": "https://ig.com/p/mid/"},
    )
    result = ig_client.publish_reel(_IG_USER, "https://example.com/v.mp4", "caption text")
    assert result["id"] == "mid"
    assert "permalink" in result


# ── ThreadsClient ──────────────────────────────────────────────────────────

def test_create_video_container(requests_mock, threads_client):
    requests_mock.post(f"{_THREADS}/{_THREADS_USER}/threads", json={"id": "tc_abc"})
    cid = threads_client.create_video_container(_THREADS_USER, "https://example.com/v.mp4", "text")
    assert cid == "tc_abc"


def test_threads_publish_full_flow(requests_mock, threads_client):
    requests_mock.post(f"{_THREADS}/{_THREADS_USER}/threads", json={"id": "tc"})
    requests_mock.get(f"{_THREADS}/tc", json={"status": "FINISHED"})
    requests_mock.post(f"{_THREADS}/{_THREADS_USER}/threads_publish", json={"id": "tp"})
    requests_mock.get(
        f"{_THREADS}/tp",
        json={"id": "tp", "timestamp": "2025-01-01T00:00:00Z", "permalink": "https://threads.net/p/tp/"},
    )
    result = threads_client.publish_video(_THREADS_USER, "https://example.com/v.mp4", "text")
    assert result["id"] == "tp"


# ── MockMultiAccountPublisher ──────────────────────────────────────────────

def _make_accounts() -> list[AccountConfig]:
    return [
        AccountConfig("mom_moneytip", "ig1", "th1", "tok1"),
        AccountConfig("showpingkkultem", "ig2", "th2", "tok2"),
        AccountConfig("haru_moneytip", "ig3", "th3", "tok3"),
    ]


def test_mock_publisher_returns_six_results():
    publisher = MockMultiAccountPublisher(_make_accounts())
    results = publisher.publish(
        "https://mock-cdn.example.com/v.mp4",
        {"default": "test caption"},
    )
    assert len(results) == 6
    assert all(r.ok for r in results)
    platforms = {r.platform for r in results}
    assert platforms == {"instagram", "threads"}
    accounts = {r.account for r in results}
    assert accounts == {"mom_moneytip", "showpingkkultem", "haru_moneytip"}


def test_mock_publisher_verify_accounts():
    publisher = MockMultiAccountPublisher(_make_accounts())
    statuses = publisher.verify_accounts()
    assert len(statuses) == 6
    assert all(s["ok"] for s in statuses)
