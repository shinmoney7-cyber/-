"""Finds the best-guess Coupang product URL for a product name.

There is no official Coupang Partners API for name/keyword search — the
Partners deeplink API only converts an *already known* coupang.com URL
into an affiliate link, and developers.coupangcorp.com's Product APIs are
the Wing seller API (registered sellerProductId lookups), not a public
catalog search. So this uses RPA against coupang.com's own site search,
same caveats as search/daiso.py and search/oliveyoung.py: selectors are
unverified placeholders (network to coupang.com was blocked in this
build environment) — see docs/CALIBRATION.md.

Per the owner's explicit choice: this returns the top-1 result and the
caller applies it automatically, accepting that a name-similarity match
can occasionally be wrong.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from urllib.parse import quote

from .selectors import CoupangSearchSelectors

logger = logging.getLogger(__name__)

DEBUG_DIR = Path("debug")


class CoupangMatchError(RuntimeError):
    pass


class CoupangMatchRPAClient:
    def __init__(self, page, screenshot_on_failure: bool = True, search_url_template: str | None = None):
        self.page = page
        self.screenshot_on_failure = screenshot_on_failure
        self.search_url_template = search_url_template or CoupangSearchSelectors.SEARCH_URL_TEMPLATE

    def find_top_match(self, product_name: str) -> str | None:
        """Returns the top search result's coupang.com URL, or None if no
        results were found."""
        url = self.search_url_template.format(keyword=quote(product_name))
        try:
            self.page.goto(url)
            items = self.page.query_selector_all(CoupangSearchSelectors.RESULT_ITEM)
        except Exception as exc:
            self._on_failure("search")
            raise CoupangMatchError(f"coupang search failed: {exc}") from exc

        if not items:
            return None

        link_el = items[0].query_selector(CoupangSearchSelectors.ITEM_LINK)
        if link_el is None:
            return None
        href = link_el.get_attribute("href")
        if not href:
            return None
        if href.startswith("/"):
            href = f"https://www.coupang.com{href}"
        return href

    def _on_failure(self, label: str) -> None:
        if not self.screenshot_on_failure:
            return
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(DEBUG_DIR / f"coupang_match_{label}.png"))
        except Exception:
            logger.exception("failed to capture debug screenshot for coupang_match/%s", label)


class MockCoupangMatchClient:
    """Deterministic stand-in — no browser, no network."""

    def find_top_match(self, product_name: str) -> str | None:
        digest = hashlib.sha256(product_name.encode("utf-8")).hexdigest()[:10]
        return f"https://www.coupang.com/vp/products/mock-{digest}"
