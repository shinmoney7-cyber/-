from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from .signing import build_authorization_header

DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
API_HOST = "https://api-gateway.coupang.com"


@dataclass(frozen=True)
class DeeplinkResult:
    original_url: str
    shorten_url: str | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.shorten_url is not None and self.error is None


class CoupangApiError(RuntimeError):
    pass


class CoupangPartnersClient:
    """Real client for the Coupang Partners deeplink-generation API.

    Batches requests in groups of ``batch_size`` (default cap unconfirmed —
    see docs/CALIBRATION.md) and surfaces per-URL failures individually so one
    bad product doesn't fail an entire batch.
    """

    def __init__(self, access_key: str, secret_key: str, batch_size: int = 50, timeout: float = 10.0):
        if not access_key or not secret_key:
            raise CoupangApiError("COUPANG_ACCESS_KEY and COUPANG_SECRET_KEY are required in live mode")
        self.access_key = access_key
        self.secret_key = secret_key
        self.batch_size = batch_size
        self.timeout = timeout

    def get_deeplinks(self, urls: list[str]) -> list[DeeplinkResult]:
        results: list[DeeplinkResult] = []
        for start in range(0, len(urls), self.batch_size):
            batch = urls[start : start + self.batch_size]
            results.extend(self._request_batch(batch))
        return results

    def _request_batch(self, urls: list[str]) -> list[DeeplinkResult]:
        path = urlparse(DEEPLINK_PATH).path
        auth_header = build_authorization_header(
            method="POST",
            path_with_query=path,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )
        response = requests.post(
            f"{API_HOST}{DEEPLINK_PATH}",
            json={"coupangUrls": urls},
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()

        if body.get("rCode") not in ("0", 0):
            raise CoupangApiError(f"Coupang API error rCode={body.get('rCode')}: {body.get('rMessage')}")

        results = []
        for item in body.get("data", []):
            shorten_url = item.get("shortenUrl")
            error = item.get("errorMessage") if not shorten_url else None
            results.append(
                DeeplinkResult(
                    original_url=item.get("originalUrl", ""),
                    shorten_url=shorten_url,
                    error=error,
                )
            )
        return results
