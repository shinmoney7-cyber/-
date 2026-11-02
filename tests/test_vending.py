import json

from shopping_shorts_sync.vending.db import SeenDB
from shopping_shorts_sync.vending.detect import detect, is_blocked
from shopping_shorts_sync.vending.models import Item, normalize_style_code
from shopping_shorts_sync.vending.notify import ConsoleNotifier, DiscordNotifier
from shopping_shorts_sync.vending.pricing import apply_coupons, coupon_warning, list_price, net_margin
from shopping_shorts_sync.vending.runner import run_cycle
from shopping_shorts_sync.vending.settings import Coupon, load_blacklist, load_settings
from shopping_shorts_sync.vending.sheet import build_opportunities, write_xlsx
from shopping_shorts_sync.vending.sources import CachedSource, FixtureSource, parse_items

SETTINGS = "data/vending/settings.example.json"
COUPONS = [Coupon(0.05, 50000), Coupon(0.10, 200000)]


def item(no, price, **kw):
    return Item(source=kw.pop("source", "musinsa"), product_no=no, brand=kw.pop("brand", "나이키"),
                name=kw.pop("name", f"상품{no}"), price=price, **kw)


def test_style_code_normalization():
    assert normalize_style_code("BV2654-063") == normalize_style_code("bv2654 063") == "BV2654063"
    assert normalize_style_code(None) == ""


def test_stacked_coupons_with_caps():
    assert apply_coupons(100000, COUPONS) == 85500
    # 5% of 2,000,000 = 100,000 -> capped at 50,000; 10% of 1,950,000 = 195,000 (under cap)
    assert apply_coupons(2000000, COUPONS) == 1755000
    # second cap kicks in
    assert apply_coupons(5000000, COUPONS) == 5000000 - 50000 - 200000


def test_coupon_warning_only_when_above_conservative():
    assert coupon_warning(COUPONS, [Coupon(0.03, 1), Coupon(0.07, 1)]) is not None
    assert coupon_warning([Coupon(0.03, 1)], [Coupon(0.03, 1), Coupon(0.07, 1)]) is None


def test_margin_and_list_price():
    assert list_price(469000, 100) == 468900
    assert net_margin(100000, 80000, 0.05, 3000) == 12000


def test_detect_baseline_then_new_and_price_drop(tmp_path):
    db = SeenDB(tmp_path / "seen.json")
    assert detect([item("1", 100000)], db, 0.1, baseline=True) == []
    events = detect([item("1", 85000), item("2", 50000), item("3", 1, sold_out=True)], db, 0.1, baseline=False)
    kinds = {(e.kind, e.item.product_no) for e in events}
    assert kinds == {("price_drop", "1"), ("new", "2")}
    drop = next(e for e in events if e.kind == "price_drop")
    assert drop.prev_price == 100000 and round(drop.drop_rate, 2) == 0.15
    # small drop below threshold is not an alert
    assert detect([item("1", 84000)], db, 0.1, baseline=False) == []
    db.save()
    assert SeenDB(tmp_path / "seen.json").count("musinsa") == 3


def test_blacklist_and_excluded_brands(tmp_path):
    bl = tmp_path / "bl.txt"
    bl.write_text("# c\n111\nmusinsa:222\n", encoding="utf-8")
    blacklist = load_blacklist(bl)
    assert is_blocked(item("111", 1), blacklist, [])
    assert is_blocked(item("222", 1), blacklist, [])
    assert not is_blocked(item("222", 1, source="cm29"), blacklist, [])
    assert is_blocked(item("9", 1, brand="BAPE"), set(), ["bape"])
    assert load_blacklist(tmp_path / "missing.txt") == set()


def test_parse_items_field_mapping():
    payload = {"data": {"list": [
        {"goodsNo": 12, "goodsName": "후디", "price": "79,000원", "isSoldOut": False, "img": [{"u": "x.jpg"}]},
        {"goodsName": "번호 없음은 건너뜀"},
    ]}}
    fields = {"product_no": "goodsNo", "name": "goodsName", "price": "price", "sold_out": "isSoldOut", "image": "img.0.u"}
    items = parse_items("musinsa", payload, fields, "data.list", "나이키")
    assert len(items) == 1
    assert items[0].product_no == "12" and items[0].price == 79000 and items[0].image == "x.jpg"
    assert items[0].brand == "나이키"


def test_build_opportunities_matches_by_style_code():
    s = load_settings(SETTINGS)
    sourcing = [
        item("a", 420000, style_code="K1S151100026", source="naver_direct", store="FABSTYLE"),
        item("b", 398000, style_code="K1S15 1100026", source="okmall"),    # cheaper, same 품번
        item("c", 890000, style_code="8115106F1", source="naver_direct"),  # market too cheap even after coupons
        item("d", 100, style_code="NOMATCH", source="naver_direct"),
        item("e", 2865000, style_code="591970 VCQR1", source="naver_direct", store="메종파르코"),
    ]
    market = [
        item("m1", 469000, style_code="K1S151100026", source="musinsa"),
        item("m2", 489000, style_code="K1S151100026", source="cm29"),
        item("m3", 760000, style_code="8115106F1", source="musinsa"),
        item("m4", 3576000, style_code="591970VCQR11000", source="cm29"),  # prefix match (color suffix)
    ]
    opps = {o.style_code: o for o in build_opportunities(sourcing, market, s)}
    assert set(opps) == {"K1S15 1100026", "591970 VCQR1"}
    o = opps["K1S15 1100026"]
    assert o.source == "오케이몰" and o.market == "무신사"
    assert o.our_cost == apply_coupons(398000, s.coupons)
    assert o.sell_price == 468900 and o.margin >= s.min_margin
    assert opps["591970 VCQR1"].store == "메종파르코" and opps["591970 VCQR1"].market == "29cm"


def test_extract_style_code_from_titles():
    from shopping_shorts_sync.vending.sources import extract_style_code

    assert normalize_style_code(extract_style_code("보테가 베네타 미니 카세트 591970 VCQR1 네이버직구")) == "591970VCQR1"
    assert normalize_style_code(extract_style_code("(W) 셀린느 트리옹프 2W99C6760.07K")) == "2W99C676007K"
    assert extract_style_code("나이키 후디 블랙") == ""


def test_naver_store_source_filters_by_mall(requests_mock):
    from shopping_shorts_sync.vending.settings import SourceSpec
    from shopping_shorts_sync.vending.sources import NaverStoreSource

    requests_mock.get(NaverStoreSource.API_URL, json={"items": [
        {"title": "<b>톰브라운</b> 가디건 MKC171A 00219", "lprice": "1617200", "mallName": "럭스보이", "productId": "1"},
        {"title": "톰브라운 가디건 MKC171A 00219", "lprice": "1500000", "mallName": "모르는스토어", "productId": "2"},
    ]})
    spec = SourceSpec(name="naver_direct", url="", list_path="", fields={}, type="naver_shop",
                      stores=["럭스 보이"])
    items = NaverStoreSource(spec, "id", "secret").fetch_brand("톰브라운")
    assert [i.product_no for i in items] == ["1"]
    assert items[0].store == "럭스보이" and items[0].price == 1617200
    assert normalize_style_code(items[0].style_code) == "MKC171A00219"
    assert requests_mock.last_request.headers["X-Naver-Client-Id"] == "id"


def test_write_xlsx(tmp_path):
    from openpyxl import load_workbook

    s = load_settings(SETTINGS)
    opps = build_opportunities([item("a", 100000, style_code="X1", source="naver_direct", store="S")],
                               [item("n", 200000, style_code="X1", source="musinsa")], s)
    path = write_xlsx(opps, tmp_path / "out.xlsx")
    rows = list(load_workbook(path).active.iter_rows(values_only=True))
    assert rows[0][3] == "품번" and rows[1][3] == "X1"


def test_cached_source_reuses_within_ttl(tmp_path):
    class Counting:
        name = "x"
        calls = 0

        def fetch_brand(self, brand):
            self.calls += 1
            return [item("1", 1000, source="x")]

    inner = Counting()
    src = CachedSource(inner, tmp_path, ttl_minutes=60)
    src.fetch_brand("나이키")
    assert src.fetch_brand("나이키")[0].product_no == "1"
    assert inner.calls == 1 and src.last_hit_age_min == 0


def test_full_cycle_with_fixtures(tmp_path):
    from shopping_shorts_sync.vending.sources import build_sources

    s = load_settings(SETTINGS)
    sources = build_sources(s.sources, "fixtures/vending", s.request_delay_sec)
    lines = []
    notifier = ConsoleNotifier(lines.append)

    first = run_cycle(s, sources, SeenDB(tmp_path / "seen.json"), set(), notifier, tmp_path, echo=lines.append)
    assert first.events == []  # baseline run
    assert first.sheet_path and first.sheet_path.exists()
    assert {o.source for o in first.opportunities} <= {"네이버직구", "오케이몰"}
    assert all(o.brand != "bape" for o in first.opportunities)
    # naver_direct has detect=false -> never written to the seen DB
    assert SeenDB(tmp_path / "seen.json").count("naver_direct") == 0

    # simulate a price drop + a new product on the next cycle
    db = SeenDB(tmp_path / "seen.json")
    db.items["musinsa:6601"]["price"] = 109000
    del db.items["cm29:29-2"]
    db.save()
    second = run_cycle(s, sources, SeenDB(tmp_path / "seen.json"), set(), notifier, tmp_path, echo=lines.append)
    kinds = sorted((e.kind, e.item.product_no) for e in second.events)
    assert kinds == [("new", "29-2"), ("price_drop", "6601")]
    assert all(e.our_cost is not None for e in second.events)
    assert len(notifier.sent) == 2
    assert all(any(f"[STEP {n}]" in l for l in lines) for n in (0, 1, 2))


def test_discord_notifier_batches_embeds(requests_mock):
    url = "https://discord.example/webhook"
    requests_mock.post(url, status_code=204)
    from shopping_shorts_sync.vending.detect import Event

    events = [Event("new", item(str(i), 1000)) for i in range(12)]
    DiscordNotifier(url).send(events)
    assert requests_mock.call_count == 2
    body = requests_mock.request_history[0].json()
    assert len(body["embeds"]) == 10 and body["username"] == "Kick Monitor"


def _discovery(tmp_path=None):
    from shopping_shorts_sync.vending.discover import FixtureSearcher, rank_malls, search_codes
    from shopping_shorts_sync.vending.sources import build_sources

    s = load_settings(SETTINGS)
    market = [i for src in build_sources(s.market_sources, "fixtures/vending", 0)
              for b in s.brands for i in src.fetch_brand(b)]
    results = search_codes(market, FixtureSearcher("fixtures/vending/naver_search.json"), echo=lambda *_: None)
    known = [x for spec in s.sources if spec.type == "naver_shop" for x in spec.stores]
    return s, results, rank_malls(results, s, known)


def test_discovery_filters_and_ranks_sellers():
    s, results, ranking = _discovery()
    malls = {st.mall for st in ranking}
    assert "무신사" not in malls          # market platform never suggested
    assert "네이버" not in malls          # price-comparison bundle skipped
    assert "다른상품샵" not in malls      # title lacks the 품번
    top = ranking[0]
    assert not top.known and top.codes_profitable == 3
    assert {st.mall for st in ranking[:2]} == {"밀라노스토어", "유로부티크"}
    known = {st.mall: st.known for st in ranking}
    assert known["나우NOW"] is True and known["명품창고A"] is False
    # cheapest listing first per 품번
    stone = next(r for r in results if r.style_code == "K2S155100026")
    assert stone.listings[0].mall == "밀라노스토어"


def test_discovery_xlsx_and_add_stores(tmp_path):
    from openpyxl import load_workbook

    from shopping_shorts_sync.vending.discover import add_stores, write_discovery_xlsx

    _, results, ranking = _discovery()
    path = write_discovery_xlsx(ranking, results, tmp_path / "d.xlsx")
    wb = load_workbook(path)
    assert wb.sheetnames == ["소싱처 순위", "품번별 최저가"]
    assert wb["소싱처 순위"]["C2"].value == "★신규 후보"

    target = tmp_path / "settings.json"
    assert add_stores(SETTINGS, target, ["밀라노스토어", "럭스 보이"]) == ["밀라노스토어"]  # 럭스보이 already known
    assert add_stores(SETTINGS, target, ["밀라노스토어"]) == []                          # idempotent
    stores = load_settings(target).sources[0].stores
    assert stores[-1] == "밀라노스토어"
