from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from .models import SearchResult

logger = logging.getLogger(__name__)

DEBUG_DIR = Path("debug")


class SearchRPAError(RuntimeError):
    pass


class GenericSearchRPAClient:
    """Shared Playwright flow for sites with no product-search API.

    Each concrete site module (daiso.py, oliveyoung.py) just supplies a
    `source` name, its `search_url_template`, and its result-card
    selectors from search/selectors.py — the navigate/extract flow itself
    is identical, so selector calibration (docs/CALIBRATION.md) is the
    only thing that should need to change per site.
    """

    def __init__(
        self,
        page,
        source: str,
        search_url_template: str,
        result_item_selector: str,
        item_name_selector: str,
        item_image_selector: str,
        item_link_selector: str,
        item_price_selector: str | None = None,
        screenshot_on_failure: bool = True,
    ):
        self.page = page
        self.source = source
        self.search_url_template = search_url_template
        self.result_item_selector = result_item_selector
        self.item_name_selector = item_name_selector
        self.item_image_selector = item_image_selector
        self.item_link_selector = item_link_selector
        self.item_price_selector = item_price_selector
        self.screenshot_on_failure = screenshot_on_failure

    def search(self, keyword: str, limit: int = 5) -> list[SearchResult]:
        url = self.search_url_template.format(keyword=quote(keyword))
        try:
            self.page.goto(url)
            cards = self.page.query_selector_all(self.result_item_selector)
        except Exception as exc:
            self._on_failure("search")
            raise SearchRPAError(f"{self.source} search failed: {exc}") from exc

        results = []
        for card in cards[:limit]:
            results.append(self._extract_result(card))
        return results

    def _extract_result(self, card) -> SearchResult:
        name_el = card.query_selector(self.item_name_selector)
        image_el = card.query_selector(self.item_image_selector)
        link_el = card.query_selector(self.item_link_selector)
        price_el = card.query_selector(self.item_price_selector) if self.item_price_selector else None

        return SearchResult(
            source=self.source,
            name=name_el.inner_text().strip() if name_el else "",
            image_url=(image_el.get_attribute("src") or "") if image_el else "",
            product_url=(link_el.get_attribute("href") or "") if link_el else "",
            price=price_el.inner_text().strip() if price_el else None,
        )

    def _on_failure(self, label: str) -> None:
        if not self.screenshot_on_failure:
            return
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(DEBUG_DIR / f"{self.source}_{label}.png"))
        except Exception:
            logger.exception("failed to capture debug screenshot for %s/%s", self.source, label)
