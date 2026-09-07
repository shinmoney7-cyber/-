"""Coupang product price monitor (RPA-based).

쿠팡 공개 API에는 가격 조회 기능이 없으므로 Playwright로 상품 페이지를 긁어
가격 변동을 감지하고 알림을 보낸다.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class PriceSnapshot:
    product_id: str
    product_name: str
    coupang_url: str
    price: Optional[int]
    rocket: bool
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PriceAlert:
    product_id: str
    product_name: str
    old_price: int
    new_price: int
    drop_pct: float
    coupang_url: str


def _parse_price(text: str) -> Optional[int]:
    """Extract integer price from strings like '12,900원' or '₩12,900'."""
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


class PriceMonitor:
    """Scrapes prices from Coupang product pages and detects drops."""

    PRICE_SELECTOR = "span.total-price > strong"
    ROCKET_SELECTOR = "span.badge-rocket"

    def __init__(
        self,
        chromium_path: str,
        price_history_path: str = "data/price_history.json",
        drop_threshold_pct: float = 10.0,
        headless: bool = True,
    ):
        self.chromium_path = chromium_path
        self.history_path = Path(price_history_path)
        self.drop_threshold_pct = drop_threshold_pct
        self.headless = headless
        self._history: dict[str, list[dict]] = self._load_history()

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def _load_history(self) -> dict:
        if self.history_path.exists():
            return json.loads(self.history_path.read_text("utf-8"))
        return {}

    def _save_history(self) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(
            json.dumps(self._history, ensure_ascii=False, indent=2), "utf-8"
        )

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    def _scrape_price(self, url: str) -> tuple[Optional[int], bool]:
        """Returns (price_won, is_rocket). Requires playwright."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=self.chromium_path,
                headless=self.headless,
            )
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            price_el = page.query_selector(self.PRICE_SELECTOR)
            price_text = price_el.inner_text() if price_el else ""
            price = _parse_price(price_text)

            rocket_el = page.query_selector(self.ROCKET_SELECTOR)
            is_rocket = rocket_el is not None

            browser.close()
        return price, is_rocket

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def check_product(
        self,
        product_id: str,
        product_name: str,
        coupang_url: str,
        dry_run: bool = False,
    ) -> tuple[PriceSnapshot, Optional[PriceAlert]]:
        if dry_run:
            price, rocket = 19900, True
        else:
            price, rocket = self._scrape_price(coupang_url)

        snapshot = PriceSnapshot(
            product_id=product_id,
            product_name=product_name,
            coupang_url=coupang_url,
            price=price,
            rocket=rocket,
        )

        alert: Optional[PriceAlert] = None
        history = self._history.setdefault(product_id, [])

        if history and price is not None:
            last_price = history[-1].get("price")
            if last_price and price < last_price:
                drop_pct = (last_price - price) / last_price * 100
                if drop_pct >= self.drop_threshold_pct:
                    alert = PriceAlert(
                        product_id=product_id,
                        product_name=product_name,
                        old_price=last_price,
                        new_price=price,
                        drop_pct=round(drop_pct, 1),
                        coupang_url=coupang_url,
                    )
                    log.info(
                        "PRICE DROP %s: %d -> %d (%.1f%%)",
                        product_name, last_price, price, drop_pct,
                    )

        history.append({
            "price": price,
            "rocket": rocket,
            "checked_at": snapshot.checked_at,
        })
        self._save_history()
        return snapshot, alert

    def check_all(
        self,
        products: list[dict],
        dry_run: bool = False,
    ) -> list[tuple[PriceSnapshot, Optional[PriceAlert]]]:
        results = []
        for p in products:
            if not p.get("enabled", True):
                continue
            snapshot, alert = self.check_product(
                p["id"], p["name"], p["coupang_url"], dry_run=dry_run
            )
            results.append((snapshot, alert))
        return results

    def get_history(self, product_id: str) -> list[dict]:
        return self._history.get(product_id, [])
