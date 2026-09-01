from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shopping_shorts_sync.config import load_config
from shopping_shorts_sync.instagram.webhook import build_keyword_map, create_app
from shopping_shorts_sync.state_store import StateStore


PRODUCTS = [
    {
        "id": "harujin-etude-01",
        "name": "에뛰드 픽싱 틴트",
        "coupang_url": "https://www.coupang.com/vp/products/1111",
        "thumbnail": "",
        "category": "뷰티",
        "target_page": "harujin",
        "enabled": True,
        "instagram_keyword": "에뛰드",
    },
    {
        "id": "harujin-watermelon-01",
        "name": "수박 5kg",
        "coupang_url": "https://www.coupang.com/vp/products/2222",
        "thumbnail": "",
        "category": "과일",
        "target_page": "harujin",
        "enabled": True,
        "instagram_keyword": "수박",
    },
    {
        "id": "harujin-no-keyword",
        "name": "키워드 없는 상품",
        "coupang_url": "https://www.coupang.com/vp/products/3333",
        "thumbnail": "",
        "category": "기타",
        "target_page": "harujin",
        "enabled": True,
        "instagram_keyword": "",
    },
]


@pytest.fixture()
def products_file(tmp_path):
    p = tmp_path / "products.json"
    p.write_text(json.dumps(PRODUCTS), encoding="utf-8")
    return str(p)


@pytest.fixture()
def state_with_deeplinks(tmp_path):
    state_path = tmp_path / "state.json"
    state = StateStore(str(state_path))
    # Manually inject deeplinks
    from shopping_shorts_sync.state_store import ProductState
    state._products["harujin-etude-01"] = ProductState(
        coupang_url="https://www.coupang.com/vp/products/1111",
        deeplink="https://link.coupang.com/a/etude123",
        status="deeplink_ready",
    )
    state._products["harujin-watermelon-01"] = ProductState(
        coupang_url="https://www.coupang.com/vp/products/2222",
        deeplink="https://link.coupang.com/a/watermelon456",
        status="deeplink_ready",
    )
    state.save()
    return state, str(state_path)


@pytest.fixture()
def app_client(products_file, state_with_deeplinks, monkeypatch):
    _, state_path = state_with_deeplinks
    monkeypatch.setenv("STATE_FILE_PATH", state_path)
    monkeypatch.setenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "test-token")
    config = load_config()
    app = create_app(config, products_file)
    return TestClient(app)


class TestBuildKeywordMap:
    def test_maps_keywords_to_deeplinks(self, products_file, state_with_deeplinks):
        state, state_path = state_with_deeplinks
        mapping = build_keyword_map(products_file, state)
        assert "에뛰드" in mapping
        assert "수박" in mapping
        assert mapping["에뛰드"][1] == "https://link.coupang.com/a/etude123"

    def test_excludes_products_without_keyword(self, products_file, state_with_deeplinks):
        state, _ = state_with_deeplinks
        mapping = build_keyword_map(products_file, state)
        assert len(mapping) == 2  # only the two with keywords


class TestWebhookVerification:
    def test_valid_token_returns_challenge(self, app_client):
        resp = app_client.get(
            "/instagram/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "abc123",
                "hub.verify_token": "test-token",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "abc123"

    def test_wrong_token_returns_403(self, app_client):
        resp = app_client.get(
            "/instagram/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "abc123",
                "hub.verify_token": "wrong-token",
            },
        )
        assert resp.status_code == 403


class TestWebhookCommentHandling:
    def _comment_event(self, text: str, sender_id: str = "user-ig-123") -> dict:
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "text": text,
                                "from": {"id": sender_id},
                            },
                        }
                    ]
                }
            ]
        }

    def test_keyword_match_returns_ok(self, app_client):
        resp = app_client.post(
            "/instagram/webhook", json=self._comment_event("에뛰드 구매하고 싶어요")
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_no_keyword_match_still_returns_ok(self, app_client):
        resp = app_client.post(
            "/instagram/webhook", json=self._comment_event("그냥 구경해요")
        )
        assert resp.status_code == 200

    def test_non_comment_field_ignored(self, app_client):
        body = {
            "entry": [{"changes": [{"field": "mentions", "value": {}}]}]
        }
        resp = app_client.post("/instagram/webhook", json=body)
        assert resp.status_code == 200
