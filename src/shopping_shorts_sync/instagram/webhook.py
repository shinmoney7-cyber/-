"""FastAPI webhook server for Instagram comment-triggered auto-DM.

Flow:
  1. Instagram POST webhook → comment event arrives.
  2. Server checks comment text against registered keywords (from products.json).
  3. If matched, sends a DM with the product's Coupang deeplink via Graph API.

Setup (see docs/CALIBRATION.md for full steps):
  - Register webhook at developers.facebook.com → Webhooks → Instagram
    Callback URL : https://<your-host>/instagram/webhook
    Verify Token : value of INSTAGRAM_WEBHOOK_VERIFY_TOKEN in .env
  - Subscribe to the `comments` field on your Instagram user object.
  - Ensure your app has instagram_manage_messages permission (requires Meta app review).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response

from ..config import Config
from ..input_loader import load_products
from ..state_store import StateStore
from .dm_client import InstagramDMClient, MockInstagramDMClient

logger = logging.getLogger(__name__)


def build_keyword_map(
    products_path: str, state: StateStore
) -> dict[str, tuple[str, str]]:
    """Returns {keyword_lower: (target_page, deeplink)} for all enabled products
    that have both instagram_keyword and a deeplink in state."""
    products = load_products(products_path)
    mapping: dict[str, tuple[str, str]] = {}
    for p in products:
        if not p.enabled or not p.instagram_keyword:
            continue
        product_state = state.get(p.id)
        if product_state and product_state.deeplink:
            key = p.instagram_keyword.strip().lower()
            mapping[key] = (p.target_page, product_state.deeplink)
    return mapping


def _build_dm_text(deeplink: str, disclaimer: str) -> str:
    lines = [
        "안녕하세요 😊 요청하신 링크입니다!",
        "",
        deeplink,
    ]
    if disclaimer:
        lines += ["", disclaimer]
    return "\n".join(lines)


def create_app(config: Config, products_path: str) -> FastAPI:
    app = FastAPI(title="Instagram DM Webhook")
    state = StateStore(config.state_file_path)

    def _dm_client(target_page: str):
        if config.instagram_api_mode == "live":
            user_id, token = config.instagram_credentials(target_page)
            return InstagramDMClient(user_id, token)
        return MockInstagramDMClient()

    @app.get("/instagram/webhook")
    def verify_webhook(
        hub_mode: str = Query(None, alias="hub.mode"),
        hub_challenge: str = Query(None, alias="hub.challenge"),
        hub_verify_token: str = Query(None, alias="hub.verify_token"),
    ):
        if hub_mode == "subscribe" and hub_verify_token == config.instagram_webhook_verify_token:
            return Response(content=hub_challenge, media_type="text/plain")
        raise HTTPException(status_code=403, detail="Verification failed")

    @app.post("/instagram/webhook")
    async def handle_webhook(request: Request):
        body: dict[str, Any] = await request.json()
        keyword_map = build_keyword_map(products_path, state)

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "comments":
                    continue
                value = change.get("value", {})
                comment_text: str = value.get("text", "").strip().lower()
                sender_igsid: str = value.get("from", {}).get("id", "")

                if not comment_text or not sender_igsid:
                    continue

                # Check if any registered keyword appears in the comment text.
                matched = next(
                    ((tp, dl) for kw, (tp, dl) in keyword_map.items() if kw in comment_text),
                    None,
                )
                if matched is None:
                    continue

                target_page, deeplink = matched
                text = _build_dm_text(deeplink, config.instagram_disclaimer)
                result = _dm_client(target_page).send_text(sender_igsid, text)
                if result.ok:
                    logger.info(
                        "DM sent to %s for keyword match in %r (deeplink=%s)",
                        sender_igsid,
                        comment_text,
                        deeplink,
                    )
                else:
                    logger.error("DM send failed for %s: %s", sender_igsid, result.error)

        return {"ok": True}

    return app
