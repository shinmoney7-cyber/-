"""Tests for PublishStore and the publishing pipeline state machine."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from shopping_shorts_sync.publish_store import (
    DestinationRecord,
    PipelineStatus,
    PublishRecord,
    PublishStore,
)


@pytest.fixture
def tmp_store(tmp_path):
    return PublishStore(tmp_path / "publish_state.json")


# ── CRUD ──────────────────────────────────────────────────────────────────

def test_create_and_get(tmp_store):
    rec = tmp_store.create("p1", "테스트 상품", "IT")
    assert rec.product_id == "p1"
    assert rec.pipeline_status == PipelineStatus.DISCOVERED.value
    assert tmp_store.get("p1") is rec


def test_upsert_and_persist(tmp_path):
    path = tmp_path / "state.json"
    store = PublishStore(path)
    rec = store.create("p2", "상품2", "뷰티")
    rec.set_status(PipelineStatus.SCRIPTED)
    rec.inpock_url = "https://link.inpock.co.kr/test"
    store.save()

    store2 = PublishStore(path)
    rec2 = store2.get("p2")
    assert rec2 is not None
    assert rec2.pipeline_status == PipelineStatus.SCRIPTED.value
    assert rec2.inpock_url == "https://link.inpock.co.kr/test"


def test_reset(tmp_store):
    tmp_store.create("p3", "상품3", "생활")
    removed = tmp_store.reset("p3")
    assert removed is True
    assert tmp_store.get("p3") is None
    assert tmp_store.reset("p3") is False


# ── Status transitions ─────────────────────────────────────────────────────

def test_status_progression(tmp_store):
    rec = tmp_store.create("p4", "상품4", "육아")
    for status in [
        PipelineStatus.FACT_CHECKED,
        PipelineStatus.SCRIPTED,
        PipelineStatus.ASSETS_READY,
        PipelineStatus.RENDERED,
        PipelineStatus.LINK_READY,
        PipelineStatus.APPROVED,
        PipelineStatus.UPLOADED,
        PipelineStatus.PUBLISHED,
        PipelineStatus.VERIFIED,
    ]:
        rec.set_status(status)
        assert rec.pipeline_status == status.value


# ── Destination recording ──────────────────────────────────────────────────

class _FakeResult:
    def __init__(self, ok, post_id=None, post_url=None, error=None):
        self.ok = ok
        self.post_id = post_id
        self.post_url = post_url
        self.error = error


def test_record_destination_ok(tmp_store):
    rec = tmp_store.create("p5", "상품5", "IT")
    result = _FakeResult(ok=True, post_id="media_123", post_url="https://ig.com/p/abc/")
    rec.record_destination("mom_moneytip", "instagram", result)
    assert "mom_moneytip_instagram" in rec.destinations
    dest = rec.destinations["mom_moneytip_instagram"]
    assert dest["status"] == "published"
    assert dest["post_id"] == "media_123"


def test_record_destination_fail(tmp_store):
    rec = tmp_store.create("p6", "상품6", "뷰티")
    result = _FakeResult(ok=False, error="API error")
    rec.record_destination("showpingkkultem", "threads", result)
    dest = rec.destinations["showpingkkultem_threads"]
    assert dest["status"] == "failed"
    assert dest["error"] == "API error"


def test_verify_destination(tmp_store):
    rec = tmp_store.create("p7", "상품7", "생활")
    result = _FakeResult(ok=True, post_id="p7_mid", post_url="https://ig.com/p/old/")
    rec.record_destination("haru_moneytip", "instagram", result)
    rec.verify_destination("haru_moneytip", "instagram", "https://ig.com/p/new/")
    dest = rec.destinations["haru_moneytip_instagram"]
    assert dest["status"] == "verified"
    assert dest["post_url"] == "https://ig.com/p/new/"


# ── all_published / all_verified ──────────────────────────────────────────

def test_all_published_when_all_ok(tmp_store):
    rec = tmp_store.create("p8", "상품8", "IT")
    for acct in ("mom_moneytip", "showpingkkultem", "haru_moneytip"):
        for plat in ("instagram", "threads"):
            rec.record_destination(acct, plat, _FakeResult(ok=True, post_id=f"{acct}_{plat}"))
    assert rec.all_published() is True


def test_not_all_published_when_one_fails(tmp_store):
    rec = tmp_store.create("p9", "상품9", "뷰티")
    rec.record_destination("mom_moneytip", "instagram", _FakeResult(ok=True, post_id="x"))
    rec.record_destination("mom_moneytip", "threads", _FakeResult(ok=False, error="err"))
    assert rec.all_published() is False


def test_all_verified(tmp_store):
    rec = tmp_store.create("p10", "상품10", "과일")
    for acct in ("mom_moneytip",):
        for plat in ("instagram",):
            rec.record_destination(acct, plat, _FakeResult(ok=True, post_id="x"))
            rec.verify_destination(acct, plat, None)
    assert rec.all_verified() is True


# ── summary_rows ──────────────────────────────────────────────────────────

def test_summary_rows_no_destinations(tmp_store):
    rec = tmp_store.create("p11", "상품11", "IT")
    rows = rec.summary_rows()
    assert len(rows) == 1
    assert rows[0]["destination"] == "(none)"


def test_summary_rows_with_destinations(tmp_store):
    rec = tmp_store.create("p12", "상품12", "IT")
    rec.record_destination("mom_moneytip", "instagram", _FakeResult(ok=True, post_id="m"))
    rows = rec.summary_rows()
    assert len(rows) == 1
    assert rows[0]["destination"] == "mom_moneytip_instagram"


# ── add_error ─────────────────────────────────────────────────────────────

def test_add_error(tmp_store):
    rec = tmp_store.create("p13", "상품13", "생활")
    rec.add_error("something went wrong")
    assert len(rec.errors) == 1
    assert "something went wrong" in rec.errors[0]
