"""사입 재고장 (아울렛 매입 재고).

data/vending/inventory.csv is an append-only ledger:
  날짜,구분,품번,사이즈,브랜드,상품명,수량,단가,거래처,메모
사이즈 is optional, but stock is kept per (품번, 사이즈) — essential for 신발
(250 and 270 of the same 품번 sell independently).
구분: 입고(buy, 단가=매입가) / 판매(sale, 단가=판매가) / 반품(customer return, 단가=환불한 판매가)
      / 폐기(write-off) / 조정(+/- 수량, stock count correction)

Cost is tracked FIFO by lot so 보유일수 = age of the oldest unsold lot.
"""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .category import classify
from .discover import MARKET_MALLS, _norm_mall, _title_has_code
from .models import normalize_style_code
from .pricing import list_price
from .settings import VendingSettings

HEADER = ["날짜", "구분", "품번", "사이즈", "브랜드", "상품명", "수량", "단가", "거래처", "메모"]
KINDS = ("입고", "판매", "반품", "폐기", "조정")


class InventoryError(ValueError):
    pass


@dataclass
class Tx:
    date: date
    kind: str
    style_code: str
    brand: str
    name: str
    qty: int
    price: int
    partner: str = ""
    memo: str = ""
    size: str = ""


@dataclass
class Lot:
    date: date
    qty: int
    cost: int


@dataclass
class StockLine:
    style_code: str
    size: str = ""
    brand: str = ""
    name: str = ""
    lots: list[Lot] = field(default_factory=list)
    bought_qty: int = 0
    sold_qty: int = 0
    revenue: int = 0
    cogs: int = 0              # cost of goods sold (FIFO)
    fees: int = 0              # market fee + shipping on sales
    written_off: int = 0       # cost of 폐기
    last_sale: date | None = None
    # filled by the report
    market_low: int | None = None
    market_mall: str = ""
    flag: str = ""
    advice: str = ""

    @property
    def qty(self) -> int:
        return sum(l.qty for l in self.lots)

    @property
    def stock_cost(self) -> int:
        return sum(l.qty * l.cost for l in self.lots)

    @property
    def avg_cost(self) -> int:
        return self.stock_cost // self.qty if self.qty else 0

    @property
    def realized(self) -> int:
        return self.revenue - self.cogs - self.fees - self.written_off

    @property
    def category(self) -> str:
        return classify(self.name, self.brand)

    def holding_days(self, today: date) -> int:
        return (today - self.lots[0].date).days if self.lots else 0


def _int(v) -> int:
    s = str(v or "").strip()
    neg = s.startswith("-")
    d = "".join(ch for ch in s if ch.isdigit())
    n = int(d) if d else 0
    return -n if neg else n


def _date(v: str) -> date:
    v = (v or "").strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    raise InventoryError(f"날짜 형식 오류: {v!r} (예: 2026-11-02)")


def load_ledger(path: str | Path) -> list[Tx]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    txs = []
    for i, r in enumerate(rows, 2):
        kind = (r.get("구분") or "").strip()
        if not kind:
            continue
        if kind not in KINDS:
            raise InventoryError(f"{path}:{i} 구분은 {'/'.join(KINDS)} 중 하나: {kind!r}")
        txs.append(Tx(_date(r.get("날짜")), kind, (r.get("품번") or "").strip(), (r.get("브랜드") or "").strip(),
                      (r.get("상품명") or "").strip(), _int(r.get("수량")), _int(r.get("단가")),
                      (r.get("거래처") or "").strip(), (r.get("메모") or "").strip(),
                      _norm_size(r.get("사이즈"))))
    return txs


def _norm_size(v) -> str:
    """'270mm' / ' 270 ' -> '270'; 'm' -> 'M'."""
    s = str(v or "").strip().upper().replace("MM", "").strip()
    return s


def _row(t: Tx) -> dict:
    return {"날짜": t.date.isoformat(), "구분": t.kind, "품번": t.style_code, "사이즈": t.size, "브랜드": t.brand,
            "상품명": t.name, "수량": t.qty, "단가": t.price, "거래처": t.partner, "메모": t.memo}


def append_ledger(path: str | Path, txs: list[Tx]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    header_ok = False
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            header_ok = reader.fieldnames == HEADER
            existing = list(reader)
    if path.exists() and header_ok:
        with open(path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADER)
            for t in txs:
                w.writerow(_row(t))
        return
    # new file, or an older ledger without the 사이즈 column: rewrite with the current header
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, extrasaction="ignore")
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in HEADER})
        for t in txs:
            w.writerow(_row(t))


def _take_fifo(line: StockLine, qty: int) -> int:
    """Remove qty units FIFO, return their cost. Raises if not enough stock."""
    if qty > line.qty:
        label = line.style_code + (f" ({line.size})" if line.size else "")
        raise InventoryError(f"{label}: 재고 {line.qty}개인데 {qty}개 출고 시도 - 장부 확인")
    cost = 0
    while qty:
        lot = line.lots[0]
        n = min(qty, lot.qty)
        cost += n * lot.cost
        lot.qty -= n
        qty -= n
        if not lot.qty:
            line.lots.pop(0)
    return cost


def build_stock(txs: list[Tx], s: VendingSettings) -> dict[str, StockLine]:
    lines: dict[str, StockLine] = {}
    for t in sorted(txs, key=lambda t: t.date):
        key = normalize_style_code(t.style_code) + (f"#{t.size}" if t.size else "")
        line = lines.setdefault(key, StockLine(t.style_code, t.size))
        line.brand = line.brand or t.brand
        line.name = line.name or t.name
        if t.kind == "입고":
            line.lots.append(Lot(t.date, t.qty, t.price))
            line.bought_qty += t.qty
        elif t.kind == "판매":
            line.cogs += _take_fifo(line, t.qty)
            line.sold_qty += t.qty
            line.revenue += t.qty * t.price
            line.fees += int(t.qty * (t.price * s.market_fee_rate + s.shipping_cost))
            line.last_sale = t.date
        elif t.kind == "반품":
            back_cost = line.cogs // line.sold_qty if line.sold_qty else t.price
            line.lots.append(Lot(t.date, t.qty, back_cost))
            line.sold_qty -= t.qty
            line.revenue -= t.qty * t.price
            line.cogs -= t.qty * back_cost
            line.fees += t.qty * s.shipping_cost  # return shipping
        elif t.kind == "폐기":
            line.written_off += _take_fifo(line, t.qty)
        elif t.kind == "조정":
            if t.qty >= 0:
                line.lots.append(Lot(t.date, t.qty, t.price or line.avg_cost))
            else:
                line.written_off += _take_fifo(line, -t.qty)
    return lines


def assess(lines: dict[str, StockLine], s: VendingSettings, today: date, searcher=None,
           stale_days: int = 30) -> list[StockLine]:
    active = [l for l in lines.values() if l.qty > 0]
    searched: dict[str, list] = {}
    for l in active:
        if searcher is not None:
            key = normalize_style_code(l.style_code)
            if key not in searched:  # one search per 품번, shared by all its sizes
                try:
                    searched[key] = searcher.search(f"{l.brand} {l.style_code}")
                except Exception:
                    searched[key] = []
            raw = searched[key]
            prices = sorted((int(r.get("lprice") or 0), r.get("mallName", "")) for r in raw
                            if int(r.get("lprice") or 0) > 0 and r.get("mallName") not in ("", "네이버")
                            and _norm_mall(r.get("mallName", "")) not in MARKET_MALLS
                            and _title_has_code(r.get("title", ""), key))
            if prices:
                l.market_low, l.market_mall = prices[0]
        days = l.holding_days(today)
        if l.market_low:
            sell = list_price(l.market_low, s.undercut)
            unit = int(sell * (1 - s.market_fee_rate) - s.shipping_cost - l.avg_cost)
            if unit < 0:
                l.flag, l.advice = "손실 위험", f"시세 {l.market_low:,} 기준 개당 {unit:,}원 - 시세 회복 대기 또는 손절 판단"
            elif days >= stale_days:
                l.flag, l.advice = "처분 추천", f"{days}일 보유 - {sell:,}원(최저가-{s.undercut})로 내려 회전"
            elif unit < s.min_margin:
                l.flag, l.advice = "마진 축소", f"개당 {unit:,}원 - 최저가 추적 필요"
            else:
                l.flag, l.advice = "정상", f"{sell:,}원 판매 시 개당 {unit:,}원"
        else:
            l.flag = "처분 추천" if days >= stale_days else "시세 미확인"
            l.advice = f"{days}일 보유" + (" - 시세 확인 후 가격 조정" if days >= stale_days else "")
    order = {"손실 위험": 0, "처분 추천": 1, "마진 축소": 2, "시세 미확인": 3, "정상": 4}
    return sorted(active, key=lambda l: (order.get(l.flag, 9), -l.holding_days(today)))


def write_stock_xlsx(active: list[StockLine], lines: dict[str, StockLine], today: date, path: str | Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    fills = {"손실 위험": "FFC7CE", "처분 추천": "FFEB9C", "마진 축소": "FFF2CC", "정상": "C6EFCE"}
    wb = Workbook()
    ws = wb.active
    ws.title = "재고 현황"
    ws.append(["상태", "카테고리", "품번", "사이즈", "브랜드", "상품명", "재고", "평균 매입가", "재고 금액", "보유일수",
               "온라인 최저가", "최저 판매처", "조언"])
    for l in active:
        ws.append([l.flag, l.category, l.style_code, l.size, l.brand, l.name, l.qty, l.avg_cost, l.stock_cost, l.holding_days(today),
                   l.market_low, l.market_mall, l.advice])
        r = ws.max_row
        if l.flag in fills:
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=fills[l.flag])
        for col in (8, 9, 11):
            ws.cell(row=r, column=col).number_format = "#,##0"

    ws2 = wb.create_sheet("품번별 손익")
    ws2.append(["카테고리", "품번", "사이즈", "브랜드", "상품명", "입고", "판매", "재고", "매출", "매출원가", "수수료·배송", "폐기손실", "실현손익"])
    for l in sorted(lines.values(), key=lambda l: -l.realized):
        ws2.append([l.category, l.style_code, l.size, l.brand, l.name, l.bought_qty, l.sold_qty, l.qty, l.revenue, l.cogs, l.fees,
                    l.written_off, l.realized])
        for col in range(9, 14):
            ws2.cell(row=ws2.max_row, column=col).number_format = "#,##0"
    tot = ["합계", "", "", "", "", sum(l.bought_qty for l in lines.values()), sum(l.sold_qty for l in lines.values()),
           sum(l.qty for l in lines.values())] + [sum(getattr(l, a) for l in lines.values())
                                                   for a in ("revenue", "cogs", "fees", "written_off", "realized")]
    ws2.append(tot)
    for c in ws2[ws2.max_row]:
        c.font = Font(bold=True)
        if isinstance(c.value, int):
            c.number_format = "#,##0"
    for sheet in (ws, ws2):
        for c in sheet[1]:
            c.font = Font(bold=True)
        sheet.freeze_panes = "B2"
    for col, w in zip("ABCDEFGHIJKLM", (11, 8, 16, 7, 10, 28, 6, 12, 12, 8, 12, 12, 50)):
        ws.column_dimensions[col].width = w
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def txs_from_outlet_xlsx(path: str | Path, on: date) -> list[Tx]:
    """'매입' rows of an `vending outlet` result -> 입고 transactions."""
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    head = {name: i for i, name in enumerate(rows[0])}
    out = []
    for r in rows[1:]:
        if r[head["판단"]] != "매입":
            continue
        out.append(Tx(on, "입고", str(r[head["품번"]]), str(r[head["브랜드"]] or ""), str(r[head["상품명"]] or ""),
                      int(r[head["수량"]] or 1), int(r[head["아울렛가"]] or 0), str(r[head["매장"]] or ""),
                      "아울렛 매입판단 가져오기", _norm_size(r[head["사이즈"]]) if "," not in str(r[head["사이즈"]] or "") else ""))
    return out
