from __future__ import annotations

import datetime
import time

import pytest

from shopping_shorts_sync.instagram.client import (
    SCHEDULE_MIN_SECONDS,
    PostResult,
    next_scheduled_timestamp,
    parse_schedule_time,
)
from shopping_shorts_sync.instagram.mock_client import MockInstagramClient


class TestPostResult:
    def test_ok_when_media_id_set(self):
        r = PostResult(product_id="p1", media_id="123")
        assert r.ok is True

    def test_not_ok_when_error(self):
        r = PostResult(product_id="p1", media_id=None, error="fail")
        assert r.ok is False

    def test_is_scheduled(self):
        r = PostResult(product_id="p1", media_id="123", scheduled_publish_time=9999999999)
        assert r.is_scheduled is True

    def test_not_scheduled_when_none(self):
        r = PostResult(product_id="p1", media_id="123")
        assert r.is_scheduled is False


class TestParseScheduleTime:
    def test_valid_future_time(self):
        kst = datetime.timezone(datetime.timedelta(hours=9))
        future = datetime.datetime.now(kst) + datetime.timedelta(hours=1)
        value = future.strftime("%Y-%m-%d %H:%M")
        ts = parse_schedule_time(value)
        assert isinstance(ts, int)
        assert ts > int(time.time())

    def test_too_soon_raises(self):
        kst = datetime.timezone(datetime.timedelta(hours=9))
        soon = datetime.datetime.now(kst) + datetime.timedelta(minutes=5)
        with pytest.raises(ValueError, match="10 minutes"):
            parse_schedule_time(soon.strftime("%Y-%m-%d %H:%M"))

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            parse_schedule_time("not-a-date")


class TestNextScheduledTimestamp:
    def test_returns_future_timestamp(self):
        ts = next_scheduled_timestamp(hour=9, minute=0)
        now = int(time.time())
        assert ts > now + SCHEDULE_MIN_SECONDS - 60  # within 1 min tolerance

    def test_different_hours_give_different_results(self):
        ts9 = next_scheduled_timestamp(hour=9)
        ts10 = next_scheduled_timestamp(hour=10)
        assert ts10 > ts9 or abs(ts10 - ts9) == 3600


class TestMockInstagramClient:
    def test_post_image_returns_ok(self):
        client = MockInstagramClient()
        result = client.post_image("product-1", "https://example.com/img.jpg", "caption")
        assert result.ok
        assert result.media_id.startswith("mock-ig-")
        assert "instagram.com" in result.permalink

    def test_deterministic_media_id(self):
        client = MockInstagramClient()
        r1 = client.post_image("product-1", "https://example.com/img.jpg", "caption")
        r2 = client.post_image("product-1", "https://example.com/img.jpg", "caption")
        assert r1.media_id == r2.media_id

    def test_scheduled_publish_time_propagated(self):
        client = MockInstagramClient()
        ts = int(time.time()) + 3600
        result = client.post_image("p", "https://img.com/x.jpg", "cap", scheduled_publish_time=ts)
        assert result.scheduled_publish_time == ts
        assert result.is_scheduled
