"""오프라인 아울렛 매입 판단.

Fill a CSV while walking the outlet (매장, 브랜드, 품번, 가격, 사이즈, 수량);
each row is checked against Naver Shopping: the online sellers whose title
contains the same 품번, their lowest/median price, and the margin if we
list just below the lowest online price. Verdict = 매입 / 보류 / 비추천.
"""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

from .category import classify
from .discover import MARKET_MALLS, _norm_mall, _title_has_code
from .models import normalize_style_code
from .pricing import list_price, net_margin
from .settings import VendingSettings

COLUMNS = {"date": "날짜", "store": "매장", "brand": "브랜드", "style_code": "품번", "name": "상품명",
           "price": "가격", "sizes": "사이즈", "qty": "수량"}


@dataclass(frozen=True)
class OutletFind:
    date: str
    store: str
    brand: str
    style_code: str
    name: str
    price: int
    sizes: str
    qty: int


@dataclass(frozen=True)
class OutletVerdict:
    find: OutletFind
    sellers: int
    online_low: int | None
    online_low_mall: str
    online_median: int | None
    sell_price: int | None
    margin: int | None
    margin_rate: float | None
    verdict: str
    reason: str


def _int(v) -> int:
    digits = "".join(ch for ch in str(v or "") if ch.isdigit())
    return int(digits) if digits else 0


def load_finds(path: str | Path) -> list[OutletFind]:
    with open(path, encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel-saved CSVs
        rows = list(csv.DictReader(f))
    finds = []
    for r in rows:
        get = lambda k: (r.get(COLUMNS[k]) or r.get(k) or "").strip()
        if not get("style_code") or not get("price"):
            continue
        finds.append(OutletFind(get("date"), get("store"), get("brand"), get("style_code"), get("name"),
                                _int(get("price")), get("sizes"), _int(get("qty")) or 1))
    return finds


def judge(finds: list[OutletFind], searcher, s: VendingSettings, min_sellers: int = 2, echo=print) -> list[OutletVerdict]:
    out = []
    for f in finds:
        key = normalize_style_code(f.style_code)
        try:
            raw = searcher.search(f"{f.brand} {f.style_code}")
        except Exception as exc:
            out.append(OutletVerdict(f, 0, None, "", None, None, None, None, "보류", f"검색 실패: {exc}"))
            continue
        prices = []
        for r in raw:
            mall = r.get("mallName", "")
            price = _int(r.get("lprice"))
            if (price <= 0 or not mall or mall == "네이버" or _norm_mall(mall) in MARKET_MALLS
                    or not _title_has_code(r.get("title", ""), key)):
                continue
            prices.append((price, mall))
        if not prices:
            out.append(OutletVerdict(f, 0, None, "", None, None, None, None, "보류",
                                     "온라인 판매처 없음 (시세 확인 불가 - 경쟁 없을 수도 있음)"))
            continue
        prices.sort()
        low, low_mall = prices[0]
        median = int(statistics.median(p for p, _ in prices))
        sell = list_price(low, s.undercut)
        margin = net_margin(sell, f.price, s.market_fee_rate, s.shipping_cost)
        rate = round(margin / sell, 4) if sell else 0.0
        if margin >= s.min_margin and len(prices) >= min_sellers:
            verdict, reason = "매입", f"최저가({low_mall}) 아래로 팔아도 마진 {margin:,}원"
        elif margin >= s.min_margin:
            verdict, reason = "보류", f"마진은 나지만 판매처 {len(prices)}곳뿐 - 시세 신뢰도 낮음"
        else:
            verdict, reason = "비추천", f"마진 {margin:,}원 < 기준 {s.min_margin:,}원"
        out.append(OutletVerdict(f, len(prices), low, low_mall, median, sell, margin, rate, verdict, reason))
        echo(f"  [{verdict}] {f.store} | {f.brand} {f.style_code} {f.price:,} -> 온라인 최저 {low:,}({low_mall}) "
             f"| 마진 {margin:,} ({rate:.0%})")
    return out


def write_outlet_xlsx(verdicts: list[OutletVerdict], path: str | Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    fills = {"매입": PatternFill("solid", fgColor="C6EFCE"), "보류": PatternFill("solid", fgColor="FFEB9C"),
             "비추천": PatternFill("solid", fgColor="FFC7CE")}
    wb = Workbook()
    ws = wb.active
    ws.title = "아울렛 매입 판단"
    ws.append(["판단", "카테고리", "매장", "브랜드", "품번", "상품명", "아울렛가", "사이즈", "수량", "온라인 판매처 수",
               "온라인 최저가", "최저 판매처", "온라인 중간가", "판매가", "개당 마진", "마진율", "총 마진", "사유", "날짜"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for v in verdicts:
        f = v.find
        ws.append([v.verdict, classify(f.name, f.brand), f.store, f.brand, f.style_code, f.name, f.price, f.sizes, f.qty, v.sellers,
                   v.online_low, v.online_low_mall, v.online_median, v.sell_price, v.margin, v.margin_rate,
                   (v.margin or 0) * f.qty if v.margin and v.margin > 0 else None, v.reason, f.date])
        r = ws.max_row
        ws.cell(row=r, column=1).fill = fills.get(v.verdict, PatternFill())
        for col in (7, 11, 13, 14, 15, 17):
            ws.cell(row=r, column=col).number_format = "#,##0"
        ws.cell(row=r, column=16).number_format = "0.0%"
    ws.freeze_panes = "B2"
    for col, w in zip("ABCDEFGHIJKLMNOPQRS", (8, 8, 18, 10, 16, 28, 11, 9, 6, 9, 12, 12, 12, 11, 11, 8, 11, 40, 11)):
        ws.column_dimensions[col].width = w
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
