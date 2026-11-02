from __future__ import annotations

from dataclasses import dataclass

from .db import SeenDB
from .models import Item


@dataclass(frozen=True)
class Event:
    kind: str                # "new" | "price_drop"
    item: Item
    prev_price: int | None = None
    our_cost: int | None = None  # after coupons

    @property
    def drop_rate(self) -> float:
        if not self.prev_price:
            return 0.0
        return 1 - self.item.price / self.prev_price


def is_blocked(item: Item, blacklist: set[str], excluded_brands: list[str]) -> bool:
    if item.product_no in blacklist or item.key in blacklist:
        return True
    return item.brand.lower().replace(" ", "") in {b.replace(" ", "") for b in excluded_brands}


def detect(items: list[Item], db: SeenDB, drop_threshold: float, baseline: bool) -> list[Event]:
    """Compare a fresh fetch against the DB, then record it.

    baseline=True (first run for a source) records everything silently so we
    don't alert on thousands of existing products."""
    events = []
    for item in items:
        prev = db.get(item)
        if prev is None:
            if not baseline and not item.sold_out:
                events.append(Event("new", item))
        elif item.price and prev["price"] and item.price < prev["price"]:
            if 1 - item.price / prev["price"] >= drop_threshold and not item.sold_out:
                events.append(Event("price_drop", item, prev_price=prev["price"]))
        db.upsert(item)
    return events
