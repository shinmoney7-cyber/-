"""Machine 2: 품번 매칭 소싱표."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import Item
from .pricing import apply_coupons, list_price, net_margin
from .settings import VendingSettings


@dataclass(frozen=True)
class Opportunity:
    brand: str
    name: str
    style_code: str
    source: str         # where we buy (소싱처)
    source_url: str
    store: str          # cheapest competing naver 직구 store
    store_price: int
    sizes: str
    supply_price: int   # sourcing price before coupons
    our_cost: int       # after coupons (공급가)
    sell_price: int     # recommended listing price
    margin: int
    margin_rate: float


def build_opportunities(sourcing: list[Item], stores: list[Item], s: VendingSettings) -> list[Opportunity]:
    # cheapest in-stock sourcing offer per 품번
    best_src: dict[str, Item] = {}
    for it in sourcing:
        k = it.style_key
        if not k or it.sold_out or it.price <= 0:
            continue
        if k not in best_src or it.price < best_src[k].price:
            best_src[k] = it
    # cheapest competitor per 품번
    best_store: dict[str, Item] = {}
    for it in stores:
        k = it.style_key
        if not k or it.price <= 0:
            continue
        if k not in best_store or it.price < best_store[k].price:
            best_store[k] = it

    out = []
    for k, src in best_src.items():
        comp = best_store.get(k)
        if comp is None:
            continue
        cost = apply_coupons(src.price, s.coupons)
        sell = list_price(comp.price, s.undercut)
        margin = net_margin(sell, cost, s.market_fee_rate, s.shipping_cost)
        if margin < s.min_margin:
            continue
        out.append(Opportunity(
            brand=src.brand, name=src.name, style_code=src.style_code, source=src.source,
            source_url=src.url, store=comp.store or comp.source, store_price=comp.price,
            sizes=src.sizes, supply_price=src.price, our_cost=cost, sell_price=sell,
            margin=margin, margin_rate=round(margin / sell, 4) if sell else 0.0,
        ))
    out.sort(key=lambda o: o.margin, reverse=True)
    return out


HEADERS = ["순", "브랜드", "크롤 상품명", "품번", "소싱처", "경쟁 스토어", "경쟁가", "가능/사이즈",
           "소싱가", "공급가(쿠폰적용)", "판매가", "마진", "마진율", "소싱 URL"]


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
        ws.append([i, o.brand, o.name, o.style_code, o.source, o.store, o.store_price, o.sizes,
                   o.supply_price, o.our_cost, o.sell_price, o.margin, o.margin_rate, o.source_url])
        ws.cell(row=i + 1, column=13).number_format = "0.0%"
        for col in (7, 9, 10, 11, 12):
            ws.cell(row=i + 1, column=col).number_format = "#,##0"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col, width in zip("ABCDEFGHIJKLMN", (5, 14, 40, 18, 10, 14, 11, 10, 11, 13, 11, 10, 8, 40)):
        ws.column_dimensions[col].width = width
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
