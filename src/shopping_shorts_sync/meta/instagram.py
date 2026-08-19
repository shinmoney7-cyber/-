from __future__ import annotations

import logging

from .client import MetaApiClient, MetaApiError

logger = logging.getLogger(__name__)

# Instagram Graph API statuses for media containers
_READY_STATUSES = {"FINISHED"}
_ERROR_STATUSES = {"ERROR", "EXPIRED"}


class InstagramClient(MetaApiClient):
    """Instagram Graph API — Reels upload and publish."""

    def create_reels_container(
        self,
        ig_user_id: str,
        video_url: str,
        caption: str,
        *,
        share_to_feed: bool = True,
    ) -> str:
        """Creates an IG media container for a Reel.

        Returns the container ID (creation_id).
        """
        data = self.graph_post(
            f"{ig_user_id}/media",
            media_type="REELS",
            video_url=video_url,
            caption=caption,
            share_to_feed="true" if share_to_feed else "false",
        )
        container_id = data.get("id")
        if not container_id:
            raise MetaApiError(f"no container id in response: {data}")
        logger.info("ig container created: %s", container_id)
        return container_id

    def get_container_status(self, container_id: str) -> str:
        """Returns the processing status string (FINISHED, IN_PROGRESS, ERROR, …)."""
        data = self.graph_get(container_id, fields="status_code")
        return data.get("status_code", "UNKNOWN")

    def wait_for_container(self, container_id: str) -> None:
        """Blocks until the container is FINISHED or raises MetaApiError."""
        self.poll_until_ready(
            poll_fn=lambda: self.get_container_status(container_id),
            ready_statuses=_READY_STATUSES,
            error_statuses=_ERROR_STATUSES,
            label=f"ig-container:{container_id}",
        )

    def publish_container(self, ig_user_id: str, container_id: str) -> str:
        """Publishes a FINISHED container. Returns the published media ID."""
        data = self.graph_post(f"{ig_user_id}/media_publish", creation_id=container_id)
        media_id = data.get("id")
        if not media_id:
            raise MetaApiError(f"no media id in publish response: {data}")
        logger.info("ig media published: %s", media_id)
        return media_id

    def verify_media(self, media_id: str) -> dict:
        """Fetches the published media record to confirm it exists.

        Returns a dict with at least ``id``, ``timestamp``, and ``permalink``.
        """
        return self.graph_get(media_id, fields="id,timestamp,permalink")

    def publish_reel(
        self,
        ig_user_id: str,
        video_url: str,
        caption: str,
        *,
        share_to_feed: bool = True,
    ) -> dict:
        """Full end-to-end: create container → wait → publish → verify.

        Returns the verified media record.
        """
        container_id = self.create_reels_container(
            ig_user_id, video_url, caption, share_to_feed=share_to_feed
        )
        self.wait_for_container(container_id)
        media_id = self.publish_container(ig_user_id, container_id)
        return self.verify_media(media_id)

    def refresh_long_lived_token(self, app_secret: str) -> dict:
        """Refreshes a long-lived user access token. Returns {access_token, token_type, expires_in}."""
        return self.graph_get(
            "oauth/access_token",
            grant_type="fb_exchange_token",
            client_id=app_secret,
            fb_exchange_token=self.access_token,
        )
