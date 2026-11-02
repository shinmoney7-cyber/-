from __future__ import annotations

from dataclasses import dataclass

import requests

GRAPH_API = "https://graph.facebook.com/v22.0"


@dataclass(frozen=True)
class DMResult:
    recipient_igsid: str
    message_id: str | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.message_id is not None and self.error is None


class InstagramDMClient:
    """Sends Instagram DMs via the Meta Graph API (Messenger API for Instagram).

    Requires instagram_manage_messages permission on the access token.
    See docs/CALIBRATION.md for permission setup steps.

    The recipient's IGSID (Instagram-scoped user ID) comes from the
    incoming webhook comment event.
    """

    def __init__(self, ig_user_id: str, access_token: str, timeout: float = 10.0):
        self.ig_user_id = ig_user_id
        self.access_token = access_token
        self.timeout = timeout

    def send_text(self, recipient_igsid: str, text: str) -> DMResult:
        resp = requests.post(
            f"{GRAPH_API}/{self.ig_user_id}/messages",
            json={
                "recipient": {"id": recipient_igsid},
                "message": {"text": text},
            },
            params={"access_token": self.access_token},
            timeout=self.timeout,
        )
        body = resp.json()
        if not resp.ok or "message_id" not in body:
            error = body.get("error", {}).get("message", str(body))
            return DMResult(recipient_igsid=recipient_igsid, message_id=None, error=error)
        return DMResult(recipient_igsid=recipient_igsid, message_id=body["message_id"])


class MockInstagramDMClient:
    """Mock DM client for tests and dry-run."""

    def send_text(self, recipient_igsid: str, text: str) -> DMResult:
        return DMResult(
            recipient_igsid=recipient_igsid,
            message_id=f"mock-dm-{recipient_igsid[:8]}",
        )
