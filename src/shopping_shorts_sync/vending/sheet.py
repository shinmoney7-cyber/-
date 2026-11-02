"""Machine 2: 품번 매칭 소싱표.

Sourcing side = where we buy (네이버직구 스토어, 오케이몰), coupons applied.
Market side   = where the same 품번 sells (무신사, 29cm) -> sell-price reference.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from pathlib import Path

from .models import Item
from .pricing import apply_coupons, list_price, net_margin
from .settings import VendingSettings

SOURCE_LABELS = {"naver_direct": "네이버직구", "okmall": "오케이몰", "musinsa": "무신사", "cm29": "29cm"}
MIN_PREFIX = 6


@dataclass(frozen=True)
class Opportunity:
    brand: str
    name: str
    style_code: str
    source: str         # 소싱처 (네이버직구 / 오케이몰)
    store: str          # 스토어 (FABSTYLE, 럭스보이 ...)
    sizes: str
    source_price: int   # 소싱가 (쿠폰 전)
    our_cost: int       # 공급가 (쿠폰 적용)
    market: str         # 판매 기준 (무신사 / 29cm)
    market_price: int
    sell_price: int
    margin: int
    margin_rate: float
    source_url: str


def _cheapest(items: list[Item], skip_sold_out: bool) -> dict[str, Item]:
    best: dict[str, Item] = {}
    for it in items:
        k = it.style_key
        if not k or it.price <= 0 or (skip_sold_out and it.sold_out):
            continue
        if k not in best or it.price < best[k].price:
            best[k] = it
    return best


def _find_market(key: str, market: dict[str, Item], keys: list[str]) -> Item | None:
    """Exact 품번 match, else prefix match (one site appends color/size codes)."""
    if key in market:
        return market[key]
    # market keys that extend ours: '591970VCQR1' -> '591970VCQR11000'
    i = bisect.bisect_left(keys, key)
    if i < len(keys) and keys[i].startswith(key) and len(key) >= MIN_PREFIX:
        return market[keys[i]]
    # our key extends a market key
    for n in range(len(key) - 1, MIN_PREFIX - 1, -1):
        if key[:n] in market:
            return market[key[:n]]
    return None


def build_opportunities(sourcing: list[Item], market_items: list[Item], s: VendingSettings) -> list[Opportunity]:
    src_best = _cheapest(sourcing, skip_sold_out=True)
    market = _cheapest(market_items, skip_sold_out=False)
    keys = sorted(market)

    out = []
    for k, src in src_best.items():
        mk = _find_market(k, market, keys)
        if mk is None:
            continue
        cost = apply_coupons(src.price, s.coupons)
        sell = list_price(mk.price, s.undercut)
        margin = net_margin(sell, cost, s.market_fee_rate, s.shipping_cost)
        if margin < s.min_margin:
            continue
        out.append(Opportunity(
            brand=src.brand, name=src.name, style_code=src.style_code,
            source=SOURCE_LABELS.get(src.source, src.source), store=src.store or SOURCE_LABELS.get(src.source, src.source),
            sizes=src.sizes, source_price=src.price, our_cost=cost,
            market=SOURCE_LABELS.get(mk.source, mk.source), market_price=mk.price, sell_price=sell,
            margin=margin, margin_rate=round(margin / sell, 4) if sell else 0.0, source_url=src.url,
        ))
    out.sort(key=lambda o: o.margin, reverse=True)
    return out


HEADERS = ["순", "브랜드", "크롤 상품명", "품번", "소싱처", "스토어", "가능/사이즈", "소싱가",
           "공급가(쿠폰적용)", "판매 기준", "기준가", "판매가", "마진", "마진율", "소싱 URL"]


def write_xlsx(opps: list[Opportunity], path: str | Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "소싱표"
    ws.append(HEADERS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for i, o in enumerate(opps, 1):
        ws.append([i, o.brand, o.name, o.style_code, o.source, o.store, o.sizes, o.source_price,
                   o.our_cost, o.market, o.market_price, o.sell_price, o.margin, o.margin_rate, o.source_url])
        r = i + 1
        for col in (8, 9, 11, 12, 13):
            ws.cell(row=r, column=col).number_format = "#,##0"
        ws.cell(row=r, column=14).number_format = "0.0%"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col, width in zip("ABCDEFGHIJKLMNO", (5, 14, 40, 18, 11, 14, 10, 11, 13, 10, 11, 11, 10, 8, 40)):
        ws.column_dimensions[col].width = width
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
