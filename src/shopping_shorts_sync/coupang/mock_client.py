from __future__ import annotations

import hashlib

from .client import DeeplinkResult


class MockCoupangClient:
    """Drop-in stand-in for CoupangPartnersClient. No network, no credentials.

    Produces deterministic fake shortened URLs so repeated runs against the
    same product URL are stable (useful for state/idempotency testing).
    """

    def get_deeplinks(self, urls: list[str]) -> list[DeeplinkResult]:
        results = []
        for url in urls:
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
            results.append(
                DeeplinkResult(
                    original_url=url,
                    shorten_url=f"https://link.coupang.com/a/mock-{digest}",
                )
            )
        return results
