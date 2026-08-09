from __future__ import annotations

import logging

from .client import MetaApiClient, MetaApiError

logger = logging.getLogger(__name__)

_READY_STATUSES = {"FINISHED"}
_ERROR_STATUSES = {"ERROR", "EXPIRED"}


class ThreadsClient(MetaApiClient):
    """Threads API — video and text post publish."""

    def create_video_container(
        self, threads_user_id: str, video_url: str, text: str
    ) -> str:
        """Creates a Threads media container for a video post.

        Returns the container ID (creation_id).
        """
        data = self.threads_post(
            f"{threads_user_id}/threads",
            media_type="VIDEO",
            video_url=video_url,
            text=text,
        )
        container_id = data.get("id")
        if not container_id:
            raise MetaApiError(f"no container id in threads response: {data}")
        logger.info("threads container created: %s", container_id)
        return container_id

    def create_text_container(self, threads_user_id: str, text: str) -> str:
        """Creates a text-only Threads post container."""
        data = self.threads_post(
            f"{threads_user_id}/threads",
            media_type="TEXT",
            text=text,
        )
        container_id = data.get("id")
        if not container_id:
            raise MetaApiError(f"no container id in threads text response: {data}")
        return container_id

    def get_container_status(self, container_id: str) -> str:
        data = self.threads_get(container_id, fields="status")
        return data.get("status", "UNKNOWN")

    def wait_for_container(self, container_id: str) -> None:
        self.poll_until_ready(
            poll_fn=lambda: self.get_container_status(container_id),
            ready_statuses=_READY_STATUSES,
            error_statuses=_ERROR_STATUSES,
            label=f"threads-container:{container_id}",
        )

    def publish_container(self, threads_user_id: str, container_id: str) -> str:
        """Publishes a FINISHED container. Returns the published post ID."""
        data = self.threads_post(
            f"{threads_user_id}/threads_publish",
            creation_id=container_id,
        )
        post_id = data.get("id")
        if not post_id:
            raise MetaApiError(f"no post id in threads publish response: {data}")
        logger.info("threads post published: %s", post_id)
        return post_id

    def verify_post(self, post_id: str) -> dict:
        """Fetches the published post record to confirm it exists."""
        return self.threads_get(post_id, fields="id,timestamp,permalink")

    def publish_video(
        self, threads_user_id: str, video_url: str, text: str
    ) -> dict:
        """Full end-to-end: create container → wait → publish → verify."""
        container_id = self.create_video_container(threads_user_id, video_url, text)
        self.wait_for_container(container_id)
        post_id = self.publish_container(threads_user_id, container_id)
        return self.verify_post(post_id)

    def refresh_long_lived_token(self) -> dict:
        """Refreshes a Threads long-lived token. Returns {access_token, token_type, expires_in}."""
        return self.threads_get(
            "refresh_access_token",
            grant_type="th_refresh_token",
            access_token=self.access_token,
        )
