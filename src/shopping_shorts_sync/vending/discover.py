"""소싱처 발굴: find Naver Shopping sellers that keep undercutting the market.

For every 품번 we can sell on the market side (무신사/29cm), search Naver
Shopping for "브랜드 품번", keep listings whose title really contains that
품번, and rank sellers (mallName) by how many 품번 they sell below market
and by how much. Top sellers not yet in the naver_shop `stores` list are
new 소싱처 candidates.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .models import Item, normalize_style_code
from .pricing import apply_coupons, list_price, net_margin
from .settings import VendingSettings

# market platforms themselves also show up as Naver sellers; never suggest them
MARKET_MALLS = {"무신사", "musinsa", "29cm", "w컨셉", "wconcept", "kream", "크림"}


def _norm_mall(name: str) -> str:
    return "".join((name or "").lower().split())


@dataclass
class Listing:
    mall: str
    price: int
    title: str
    url: str


@dataclass
class CodeResult:
    brand: str
    name: str
    style_code: str
    market: str
    market_price: int
    listings: list[Listing] = field(default_factory=list)  # cheapest first, title contains 품번


@dataclass
class MallStat:
    mall: str
    known: bool                # already in our stores list
    codes_found: int = 0       # 품번 this mall sells
    codes_cheaper: int = 0     # ... below market price
    codes_profitable: int = 0  # ... with coupons applied, margin >= min_margin
    cheapest_count: int = 0    # times it was the cheapest seller for a 품번
    discount_sum: float = 0.0
    total_margin: int = 0
    examples: list[str] = field(default_factory=list)

    @property
    def avg_discount(self) -> float:
        return self.discount_sum / self.codes_cheaper if self.codes_cheaper else 0.0


class NaverSearcher:
    API_URL = "https://openapi.naver.com/v1/search/shop.json"

    def __init__(self, client_id: str, client_secret: str, delay_sec: float = 0.15, session=None):
        if not client_id or not client_secret:
            raise ValueError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET are required (developers.naver.com)")
        self.headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        self.delay_sec = delay_sec
        self.session = session or requests.Session()

    def search(self, query: str) -> list[dict]:
        resp = self.session.get(self.API_URL, headers=self.headers, timeout=15,
                                params={"query": query, "display": 100, "sort": "asc"})
        resp.raise_for_status()
        time.sleep(self.delay_sec)  # Naver API: 25,000 calls/day per app
        return resp.json().get("items", [])


class FixtureSearcher:
    """Offline: fixtures/vending/naver_search.json -> {normalized 품번: [raw items]}."""

    def __init__(self, path: str | Path):
        self.data = json.loads(Path(path).read_text(encoding="utf-8"))

    def search(self, query: str) -> list[dict]:
        key = normalize_style_code(query.split(" ", 1)[-1])
        return self.data.get(key, [])


def _title_has_code(title: str, code_key: str) -> bool:
    return code_key in normalize_style_code(re.sub(r"<[^>]+>", "", title))


def search_codes(market_items: list[Item], searcher, limit: int | None = None, echo=print) -> list[CodeResult]:
    # one query per 품번, cheapest market price as the reference
    best: dict[str, Item] = {}
    for it in market_items:
        k = it.style_key
        if len(k) >= 6 and it.price > 0 and (k not in best or it.price < best[k].price):
            best[k] = it
    codes = list(best.items())[:limit] if limit else list(best.items())
    echo(f"[소싱처 발굴] 판매 기준 품번 {len(codes)}개 검색")

    results = []
    for i, (k, it) in enumerate(codes, 1):
        try:
            raw = searcher.search(f"{it.brand} {it.style_code}")
        except Exception as exc:
            echo(f"  [{i}/{len(codes)}] {it.style_code}: 검색 실패 ({exc})")
            continue
        listings = []
        for r in raw:
            mall = r.get("mallName", "")
            price = int(r.get("lprice") or 0)
            if not mall or price <= 0 or _norm_mall(mall) in MARKET_MALLS or mall == "네이버":
                continue  # '네이버' = price-comparison bundle, not a single seller
            if not _title_has_code(r.get("title", ""), k):
                continue
            listings.append(Listing(mall, price, re.sub(r"<[^>]+>", "", r.get("title", "")), r.get("link", "")))
        listings.sort(key=lambda l: l.price)
        results.append(CodeResult(it.brand, it.name, it.style_code, it.source, it.price, listings))
    return results


def rank_malls(results: list[CodeResult], settings: VendingSettings, known_stores: list[str]) -> list[MallStat]:
    known = {_norm_mall(s) for s in known_stores}
    stats: dict[str, MallStat] = {}
    for cr in results:
        seen_here = set()
        for idx, l in enumerate(cr.listings):
            if l.mall in seen_here:
                continue  # count each mall once per 품번 (its cheapest listing)
            seen_here.add(l.mall)
            st = stats.setdefault(l.mall, MallStat(l.mall, _norm_mall(l.mall) in known))
            st.codes_found += 1
            if idx == 0:
                st.cheapest_count += 1
            if l.price < cr.market_price:
                st.codes_cheaper += 1
                st.discount_sum += 1 - l.price / cr.market_price
                cost = apply_coupons(l.price, settings.coupons)
                m = net_margin(list_price(cr.market_price, settings.undercut), cost,
                               settings.market_fee_rate, settings.shipping_cost)
                if m >= settings.min_margin:
                    st.codes_profitable += 1
                    st.total_margin += m
                    if len(st.examples) < 3:
                        st.examples.append(f"{cr.brand} {cr.style_code} {l.price:,}<{cr.market_price:,}")
    return sorted(stats.values(),
                  key=lambda s: (s.codes_profitable, s.codes_cheaper, s.avg_discount), reverse=True)


def write_discovery_xlsx(ranking: list[MallStat], results: list[CodeResult], path: str | Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "소싱처 순위"
    ws.append(["순위", "판매처", "상태", "수익 품번", "시세보다 싼 품번", "최저가 1위 횟수", "취급 품번",
               "평균 할인율", "예상 마진 합계", "예시"])
    new_fill = PatternFill("solid", fgColor="FFF2CC")
    for i, s in enumerate(ranking, 1):
        ws.append([i, s.mall, "기존" if s.known else "★신규 후보", s.codes_profitable, s.codes_cheaper,
                   s.cheapest_count, s.codes_found, s.avg_discount, s.total_margin, " / ".join(s.examples)])
        ws.cell(row=i + 1, column=8).number_format = "0.0%"
        ws.cell(row=i + 1, column=9).number_format = "#,##0"
        if not s.known and s.codes_profitable:
            for c in ws[i + 1]:
                c.fill = new_fill

    ws2 = wb.create_sheet("품번별 최저가")
    ws2.append(["브랜드", "품번", "상품명", "판매 기준", "기준가", "최저 판매처", "최저가", "할인율", "2위", "3위", "링크"])
    for cr in results:
        if not cr.listings:
            continue
        top = cr.listings[0]
        others = [f"{l.mall} {l.price:,}" for l in cr.listings[1:3]]
        ws2.append([cr.brand, cr.style_code, cr.name, cr.market, cr.market_price, top.mall, top.price,
                    1 - top.price / cr.market_price, *(others + ["", ""])[:2], top.url])
        r = ws2.max_row
        for col in (5, 7):
            ws2.cell(row=r, column=col).number_format = "#,##0"
        ws2.cell(row=r, column=8).number_format = "0.0%"
    for sheet in (ws, ws2):
        for c in sheet[1]:
            c.font = Font(bold=True)
        sheet.freeze_panes = "A2"
    for col, w in zip("ABCDEFGHIJ", (6, 18, 11, 10, 14, 13, 10, 11, 14, 60)):
        ws.column_dimensions[col].width = w
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def add_stores(source_settings: str | Path, target_settings: str | Path, malls: list[str]) -> list[str]:
    """Append malls to every naver_shop source's `stores` in target (created from
    source_settings if missing). Returns the names actually added."""
    target = Path(target_settings)
    raw = json.loads((target if target.exists() else Path(source_settings)).read_text(encoding="utf-8"))
    added: list[str] = []
    for spec in raw.get("sources", []):
        if spec.get("type") != "naver_shop":
            continue
        stores = spec.setdefault("stores", [])
        have = {_norm_mall(s) for s in stores}
        for m in malls:
            if _norm_mall(m) not in have:
                stores.append(m)
                have.add(_norm_mall(m))
                if m not in added:
                    added.append(m)
    if added:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return added
