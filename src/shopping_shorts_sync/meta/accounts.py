from __future__ import annotations

import logging
from dataclasses import dataclass

from .client import MetaApiError
from .instagram import InstagramClient
from .threads import ThreadsClient

logger = logging.getLogger(__name__)

ACCOUNTS = ("mom_moneytip", "showpingkkultem", "haru_moneytip")
PLATFORMS = ("instagram", "threads")


@dataclass(frozen=True)
class AccountConfig:
    name: str
    ig_user_id: str
    threads_user_id: str
    access_token: str

    def destination_keys(self) -> list[str]:
        return [f"{self.name}_instagram", f"{self.name}_threads"]


@dataclass
class PublishResult:
    account: str
    platform: str
    ok: bool
    post_id: str | None = None
    post_url: str | None = None
    error: str | None = None


class MultiAccountPublisher:
    """Publishes one video to all 3 accounts × 2 platforms."""

    def __init__(self, accounts: list[AccountConfig], api_version: str = "v21.0"):
        self._accounts = accounts
        self._api_version = api_version

    def _ig_client(self, token: str) -> InstagramClient:
        return InstagramClient(token, api_version=self._api_version)

    def _threads_client(self, token: str) -> ThreadsClient:
        return ThreadsClient(token, api_version=self._api_version)

    def publish(
        self,
        video_url: str,
        captions: dict[str, str],
        *,
        max_retries: int = 3,
        retry_base: float = 2.0,
    ) -> list[PublishResult]:
        """Publishes video_url to all configured accounts/platforms.

        captions: mapping from account name (or 'default') to caption text.
        Returns one PublishResult per destination.
        """
        import time

        results: list[PublishResult] = []

        for account in self._accounts:
            caption = captions.get(account.name) or captions.get("default", "")

            for platform in PLATFORMS:
                result = self._publish_one_with_retry(
                    account, platform, video_url, caption, max_retries, retry_base
                )
                results.append(result)

        return results

    def _publish_one_with_retry(
        self,
        account: AccountConfig,
        platform: str,
        video_url: str,
        caption: str,
        max_retries: int,
        retry_base: float,
    ) -> PublishResult:
        import time

        last_error: str | None = None
        for attempt in range(max_retries):
            try:
                record = self._publish_one(account, platform, video_url, caption)
                return record
            except MetaApiError as exc:
                last_error = str(exc)
                # Auth / permission errors → no retry
                if exc.code in (190, 200, 10, 803):
                    logger.error(
                        "[%s/%s] auth/permission error (code=%s), stopping: %s",
                        account.name, platform, exc.code, exc,
                    )
                    break
                wait = retry_base ** attempt
                logger.warning(
                    "[%s/%s] attempt %d failed, retrying in %.0fs: %s",
                    account.name, platform, attempt + 1, wait, exc,
                )
                if attempt < max_retries - 1:
                    time.sleep(wait)

        return PublishResult(account=account.name, platform=platform, ok=False, error=last_error)

    def _publish_one(
        self, account: AccountConfig, platform: str, video_url: str, caption: str
    ) -> PublishResult:
        if platform == "instagram":
            client = self._ig_client(account.access_token)
            media = client.publish_reel(account.ig_user_id, video_url, caption)
            return PublishResult(
                account=account.name,
                platform="instagram",
                ok=True,
                post_id=media.get("id"),
                post_url=media.get("permalink"),
            )
        elif platform == "threads":
            client = self._threads_client(account.access_token)
            post = client.publish_video(account.threads_user_id, video_url, caption)
            return PublishResult(
                account=account.name,
                platform="threads",
                ok=True,
                post_id=post.get("id"),
                post_url=post.get("permalink"),
            )
        else:
            raise ValueError(f"unknown platform: {platform!r}")

    def verify_accounts(self) -> list[dict]:
        """Calls the API to confirm each account's credentials are valid."""
        statuses = []
        for account in self._accounts:
            ig_client = self._ig_client(account.access_token)
            threads_client = self._threads_client(account.access_token)

            for platform, user_id, check_fn in [
                ("instagram", account.ig_user_id, lambda: ig_client.graph_get("me", fields="id,name")),
                ("threads", account.threads_user_id, lambda: threads_client.threads_get("me", fields="id,name")),
            ]:
                try:
                    data = check_fn()
                    statuses.append({
                        "account": account.name,
                        "platform": platform,
                        "ok": True,
                        "user_id": data.get("id"),
                        "name": data.get("name"),
                    })
                except MetaApiError as exc:
                    statuses.append({
                        "account": account.name,
                        "platform": platform,
                        "ok": False,
                        "error": str(exc),
                    })
        return statuses
