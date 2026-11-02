from __future__ import annotations

import datetime
from dataclasses import dataclass

import requests

GRAPH_API = "https://graph.facebook.com/v22.0"

# Instagram requires scheduled_publish_time to be 10 min – 75 days from now.
SCHEDULE_MIN_SECONDS = 10 * 60
SCHEDULE_MAX_SECONDS = 75 * 24 * 3600


@dataclass(frozen=True)
class PostResult:
    product_id: str
    media_id: str | None
    permalink: str | None = None
    scheduled_publish_time: int | None = None  # Unix timestamp, set when scheduled
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.media_id is not None and self.error is None

    @property
    def is_scheduled(self) -> bool:
        return self.scheduled_publish_time is not None


class InstagramApiError(RuntimeError):
    pass


def next_scheduled_timestamp(hour: int = 9, minute: int = 0) -> int:
    """Returns the Unix timestamp of the next HH:MM KST occurrence.
    If that time is fewer than 10 minutes away today, returns tomorrow's."""
    kst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(kst)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if (candidate - now).total_seconds() < SCHEDULE_MIN_SECONDS:
        candidate += datetime.timedelta(days=1)
    return int(candidate.timestamp())


def parse_schedule_time(value: str) -> int:
    """Parses 'YYYY-MM-DD HH:MM' (KST, UTC+9) and returns a Unix timestamp.
    Raises ValueError when the resulting time is outside the allowed window."""
    kst = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=kst)
    ts = int(dt.timestamp())
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    delta = ts - now
    if delta < SCHEDULE_MIN_SECONDS:
        raise ValueError(f"scheduled time must be at least 10 minutes from now (got {delta}s)")
    if delta > SCHEDULE_MAX_SECONDS:
        raise ValueError(f"scheduled time must be within 75 days from now (got {delta}s)")
    return ts


class InstagramClient:
    """Posts or schedules a single image on an Instagram Business/Creator account
    via the Meta Graph API.

    Requires instagram_basic + instagram_content_publish permissions on the
    access token. See docs/CALIBRATION.md for token setup steps.
    """

    def __init__(self, user_id: str, access_token: str, timeout: float = 30.0):
        if not user_id or not access_token:
            raise InstagramApiError(
                "Instagram user_id and access_token are required in live mode"
            )
        self.user_id = user_id
        self.access_token = access_token
        self.timeout = timeout

    def post_image(
        self,
        product_id: str,
        image_url: str,
        caption: str,
        scheduled_publish_time: int | None = None,
    ) -> PostResult:
        creation_id = self._create_container(image_url, caption, scheduled_publish_time)
        media_id = self._publish(creation_id)
        permalink = self._get_permalink(media_id)
        return PostResult(
            product_id=product_id,
            media_id=media_id,
            permalink=permalink,
            scheduled_publish_time=scheduled_publish_time,
        )

    def _create_container(
        self, image_url: str, caption: str, scheduled_publish_time: int | None
    ) -> str:
        params: dict = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        if scheduled_publish_time is not None:
            params["published"] = "false"
            params["scheduled_publish_time"] = str(scheduled_publish_time)

        resp = requests.post(
            f"{GRAPH_API}/{self.user_id}/media",
            params=params,
            timeout=self.timeout,
        )
        body = resp.json()
        if not resp.ok or "id" not in body:
            raise InstagramApiError(
                f"media container creation failed: {body.get('error', {}).get('message', body)}"
            )
        return body["id"]

    def _publish(self, creation_id: str) -> str:
        resp = requests.post(
            f"{GRAPH_API}/{self.user_id}/media_publish",
            params={
                "creation_id": creation_id,
                "access_token": self.access_token,
            },
            timeout=self.timeout,
        )
        body = resp.json()
        if not resp.ok or "id" not in body:
            raise InstagramApiError(
                f"media publish failed: {body.get('error', {}).get('message', body)}"
            )
        return body["id"]

    def _get_permalink(self, media_id: str) -> str | None:
        try:
            resp = requests.get(
                f"{GRAPH_API}/{media_id}",
                params={"fields": "permalink", "access_token": self.access_token},
                timeout=self.timeout,
            )
            return resp.json().get("permalink")
        except Exception:
            return None
