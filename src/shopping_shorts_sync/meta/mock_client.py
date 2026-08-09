from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .accounts import AccountConfig, MultiAccountPublisher, PublishResult


def _fake_id() -> str:
    return str(uuid.uuid4().int)[:15]


class MockInstagramClient:
    """Simulates Instagram API responses for tests and dry-runs."""

    def create_reels_container(self, ig_user_id, video_url, caption, **_) -> str:
        return f"mock_ig_container_{_fake_id()}"

    def get_container_status(self, container_id: str) -> str:
        return "FINISHED"

    def wait_for_container(self, container_id: str) -> None:
        pass

    def publish_container(self, ig_user_id: str, container_id: str) -> str:
        return f"mock_ig_media_{_fake_id()}"

    def verify_media(self, media_id: str) -> dict:
        return {
            "id": media_id,
            "timestamp": "2025-01-01T00:00:00+0000",
            "permalink": f"https://www.instagram.com/p/mock_{media_id}/",
        }

    def publish_reel(self, ig_user_id, video_url, caption, **_) -> dict:
        container_id = self.create_reels_container(ig_user_id, video_url, caption)
        self.wait_for_container(container_id)
        media_id = self.publish_container(ig_user_id, container_id)
        return self.verify_media(media_id)


class MockThreadsClient:
    """Simulates Threads API responses for tests and dry-runs."""

    def create_video_container(self, threads_user_id, video_url, text) -> str:
        return f"mock_threads_container_{_fake_id()}"

    def get_container_status(self, container_id: str) -> str:
        return "FINISHED"

    def wait_for_container(self, container_id: str) -> None:
        pass

    def publish_container(self, threads_user_id: str, container_id: str) -> str:
        return f"mock_threads_post_{_fake_id()}"

    def verify_post(self, post_id: str) -> dict:
        return {
            "id": post_id,
            "timestamp": "2025-01-01T00:00:00+0000",
            "permalink": f"https://www.threads.net/@mock/post/{post_id}",
        }

    def publish_video(self, threads_user_id, video_url, text) -> dict:
        container_id = self.create_video_container(threads_user_id, video_url, text)
        self.wait_for_container(container_id)
        post_id = self.publish_container(threads_user_id, container_id)
        return self.verify_post(post_id)


class MockMultiAccountPublisher(MultiAccountPublisher):
    """Drop-in replacement for MultiAccountPublisher that never calls the real API."""

    def _publish_one(self, account, platform, video_url, caption) -> PublishResult:
        if platform == "instagram":
            client = MockInstagramClient()
            media = client.publish_reel(account.ig_user_id, video_url, caption)
            return PublishResult(
                account=account.name,
                platform="instagram",
                ok=True,
                post_id=media.get("id"),
                post_url=media.get("permalink"),
            )
        else:
            client = MockThreadsClient()
            post = client.publish_video(account.threads_user_id, video_url, caption)
            return PublishResult(
                account=account.name,
                platform="threads",
                ok=True,
                post_id=post.get("id"),
                post_url=post.get("permalink"),
            )

    def verify_accounts(self) -> list[dict]:
        return [
            {"account": a.name, "platform": p, "ok": True, "user_id": f"mock_{a.name}_{p}"}
            for a in self._accounts
            for p in ("instagram", "threads")
        ]
