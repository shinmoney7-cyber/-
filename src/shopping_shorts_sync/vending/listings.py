"""위탁(무재고) 판매 상품 감시.

data/vending/listings.csv lists what is live on our store and where we'd
buy it on order. Each cycle we look the source item up in that cycle's
fetch and flag:
  unlist — 소싱처 품절, or the source price rose so margin < min_margin
  check  — item vanished from the source's listing (sold out/deleted, or
           just beyond the pages we fetch) — verify by hand
Sources not fetched this cycle are never flagged (unknown != sold out).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .detect import Event
from .models import Item, normalize_style_code
from .pricing import apply_coupons, net_margin
from .settings import VendingSettings

COLUMNS = {"style_code": "품번", "source": "소싱처", "product_no": "소싱 상품번호", "sell_price": "내 판매가",
           "brand": "브랜드", "name": "상품명", "store": "스토어"}


@dataclass(frozen=True)
class Listing:
    style_code: str
    source: str
    product_no: str
    sell_price: int
    brand: str
    name: str
    store: str = ""


def _int(v) -> int:
    d = "".join(ch for ch in str(v or "") if ch.isdigit())
    return int(d) if d else 0


def load_listings(path: str | Path | None) -> list[Listing]:
    if not path or not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        get = lambda k: (r.get(COLUMNS[k]) or r.get(k) or "").strip()
        if not get("source") or not (get("style_code") or get("product_no")):
            continue
        out.append(Listing(get("style_code"), get("source"), get("product_no"), _int(get("sell_price")),
                           get("brand"), get("name"), get("store")))
    return out


def _lookup(listing: Listing, items: list[Item]) -> Item | None:
    if listing.product_no:
        for it in items:
            if it.product_no == listing.product_no:
                return it
        return None
    key = normalize_style_code(listing.style_code)
    cands = [it for it in items if it.style_key == key and (not listing.store or it.store == listing.store)]
    in_stock = [it for it in cands if not it.sold_out]
    pool = in_stock or cands
    return min(pool, key=lambda it: it.price) if pool else None


def check_listings(listings: list[Listing], fetched: dict[str, list[Item]], s: VendingSettings) -> list[Event]:
    events = []
    for l in listings:
        if l.source not in fetched:
            continue
        placeholder = Item(source=l.source, product_no=l.product_no or l.style_code, brand=l.brand,
                           name=l.name or l.style_code, price=0, style_code=l.style_code, store=l.store)
        it = _lookup(l, fetched[l.source])
        if it is None:
            events.append(Event("check", placeholder,
                                reason=f"{l.source}에서 상품이 안 보임 (품절/삭제 또는 수집 범위 밖) - 직접 확인"))
            continue
        if it.sold_out:
            events.append(Event("unlist", it, reason=f"소싱처 품절 ({l.source}{'/' + it.store if it.store else ''})"))
            continue
        cost = apply_coupons(it.price, s.coupons)
        if l.sell_price:
            margin = net_margin(l.sell_price, cost, s.market_fee_rate, s.shipping_cost)
            if margin < s.min_margin:
                events.append(Event("unlist", it, our_cost=cost,
                                    reason=f"마진 {margin:,}원 < 기준 {s.min_margin:,}원 "
                                           f"(소싱가 {it.price:,}, 내 판매가 {l.sell_price:,}) - 가격 올리거나 내리기"))
    return events
