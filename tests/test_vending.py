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
        item("a", 420000, style_code="K1S151100026", source="musinsa"),
        item("b", 398000, style_code="K1S15 1100026", source="okmall"),   # cheaper, same 품번
        item("c", 890000, style_code="8115106F1"),                          # competitor too cheap even after coupons
        item("d", 100, style_code="NOMATCH"),
    ]
    stores = [
        item("n1", 469000, style_code="K1S151100026", source="naver_store", store="FABSTYLE"),
        item("n2", 489000, style_code="K1S151100026", source="naver_store", store="럭스보이"),
        item("n3", 760000, style_code="8115106F1", source="naver_store"),
    ]
    opps = build_opportunities(sourcing, stores, s)
    assert len(opps) == 1
    o = opps[0]
    assert o.source == "okmall" and o.store == "FABSTYLE"
    assert o.our_cost == apply_coupons(398000, s.coupons)
    assert o.sell_price == 468900
    assert o.margin >= s.min_margin


def test_write_xlsx(tmp_path):
    from openpyxl import load_workbook

    s = load_settings(SETTINGS)
    opps = build_opportunities([item("a", 100000, style_code="X1")],
                               [item("n", 200000, style_code="X1", source="naver_store", store="S")], s)
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
    s = load_settings(SETTINGS)
    sourcing = [FixtureSource(spec.name, "fixtures/vending") for spec in s.sourcing_sources]
    stores = [FixtureSource(spec.name, "fixtures/vending") for spec in s.store_sources]
    lines = []
    notifier = ConsoleNotifier(lines.append)

    first = run_cycle(s, sourcing, stores, SeenDB(tmp_path / "seen.json"), set(), notifier, tmp_path, echo=lines.append)
    assert first.events == []  # baseline run
    assert first.sheet_path and first.sheet_path.exists()
    assert all(o.brand != "bape" for o in first.opportunities)

    # simulate a price drop + a new product on the next cycle
    db = SeenDB(tmp_path / "seen.json")
    db.items["musinsa:6601"]["price"] = 99000
    del db.items["musinsa:5501"]
    db.save()
    second = run_cycle(s, sourcing, stores, SeenDB(tmp_path / "seen.json"), set(), notifier, tmp_path, echo=lines.append)
    kinds = sorted((e.kind, e.item.product_no) for e in second.events)
    assert kinds == [("new", "5501"), ("price_drop", "6601")]
    assert all(e.our_cost is not None for e in second.events)
    assert len(notifier.sent) == 2
    assert any("[STEP 0]" in l for l in lines) and any("[STEP 2]" in l for l in lines)


def test_discord_notifier_batches_embeds(requests_mock):
    url = "https://discord.example/webhook"
    requests_mock.post(url, status_code=204)
    from shopping_shorts_sync.vending.detect import Event

    events = [Event("new", item(str(i), 1000)) for i in range(12)]
    DiscordNotifier(url).send(events)
    assert requests_mock.call_count == 2
    body = requests_mock.request_history[0].json()
    assert len(body["embeds"]) == 10 and body["username"] == "Kick Monitor"
