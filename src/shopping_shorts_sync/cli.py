from __future__ import annotations

import dataclasses
import logging

import click

from .config import load_config
from .input_loader import load_products
from .script_store import default_script_path, load_script_set
from .search.orchestrator import match_and_upsert_product, search_all_sources, search_one_source
from .state_store import StateStore
from .sync import (
    build_coupang_client,
    build_instagram_caption,
    resolve_thumbnails,
    run_deeplink_stage,
    run_facebook_stage,
    run_full_sync,
    run_inpock_stage,
    run_instagram_stage,
)


def _setup_logging(config):
    logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))


def _print_outcomes(label: str, outcomes) -> None:
    click.echo(f"-- {label} --")
    for product, outcome, detail in outcomes:
        suffix = f" ({detail})" if detail else ""
        click.echo(f"  [{outcome}] {product.id} - {product.name}{suffix}")


@click.group()
def cli():
    """Coupang Partners deeplink generation -> Inpock link-card sync."""


@cli.group()
def deeplink():
    """Coupang Partners deeplink operations."""


@deeplink.command("generate")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--live/--dry-run", "live", default=False, help="Call the real Coupang API instead of the mock client.")
@click.option("--force", is_flag=True, help="Regenerate deeplinks even if state says they're already up to date.")
def deeplink_generate(input_path, live, force):
    config = load_config()
    _setup_logging(config)
    if live:
        config = dataclasses.replace(config, coupang_api_mode="live")
    else:
        config = dataclasses.replace(config, coupang_api_mode="mock")

    products = load_products(input_path)
    state = StateStore(config.state_file_path)
    client = build_coupang_client(config)

    outcomes = run_deeplink_stage(products, client, state, force=force)
    state.save()
    _print_outcomes("deeplink generate", outcomes)


@cli.group()
def inpock():
    """Inpock link-card sync operations."""


@inpock.command("sync")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--page", "page_filter", type=click.Choice(["harujin", "shinjh"]), default=None)
@click.option("--dry-run/--live", "dry_run", default=True, help="Dry-run uses a mock RPA client; --live drives a real browser.")
@click.option("--headed/--headless", "headed", default=False)
@click.option("--force-create", is_flag=True, help="Skip the existing-card lookup and always create a new card.")
def inpock_sync(input_path, page_filter, dry_run, headed, force_create):
    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(config, inpock_headless=not headed)

    products = load_products(input_path)
    if page_filter:
        products = [p for p in products if p.target_page == page_filter]

    state = StateStore(config.state_file_path)

    if dry_run:
        from .inpock.mock_rpa import MockInpockRPAClient

        rpa_client = MockInpockRPAClient()
        outcomes = run_inpock_stage(products, rpa_client, state, force_create=force_create)
    else:
        from .browser import launch_browser
        from .inpock.rpa import InpockRPAClient

        with launch_browser(
            headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
        ) as browser:
            page = browser.new_page()
            rpa_client = InpockRPAClient(page, config.inpock_email, config.inpock_password)
            rpa_client.login()
            outcomes = run_inpock_stage(products, rpa_client, state, force_create=force_create)

    state.save()
    _print_outcomes("inpock sync", outcomes)


@cli.group("sync")
def sync_group():
    """Full pipeline: Coupang deeplink generation followed by Inpock sync."""


@sync_group.command("all")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--dry-run/--live", "dry_run", default=True)
@click.option("--headed/--headless", "headed", default=False)
@click.option("--force", is_flag=True, help="Regenerate deeplinks even if already up to date.")
@click.option("--force-create", is_flag=True, help="Skip the existing-card lookup in the Inpock stage.")
def sync_all(input_path, dry_run, headed, force, force_create):
    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(
        config,
        coupang_api_mode="mock" if dry_run else "live",
        inpock_headless=not headed,
    )

    products = load_products(input_path)
    deeplink_outcomes, inpock_outcomes = run_full_sync(
        products, config, dry_run=dry_run, force=force, force_create=force_create
    )
    _print_outcomes("deeplink generate", deeplink_outcomes)
    _print_outcomes("inpock sync", inpock_outcomes)


@cli.group()
def search():
    """Search Naver/Daiso/Olive Young and auto-match results to a Coupang product.

    Daiso/Olive Young (RPA) and the Coupang matching step all use
    best-effort, uncalibrated selectors -- see docs/CALIBRATION.md before
    running --live against the real sites.
    """


@search.command("run")
@click.option("--keyword", required=True)
@click.option("--limit", default=5, show_default=True)
@click.option("--dry-run/--live", "dry_run", default=True)
@click.option("--headed/--headless", "headed", default=False)
def search_run(keyword, limit, dry_run, headed):
    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(config, inpock_headless=not headed)

    results = search_all_sources(keyword, config, dry_run=dry_run, limit=limit)
    for source, items in results.items():
        click.echo(f"-- {source} --")
        for i, item in enumerate(items):
            price = f" ({item.price})" if item.price else ""
            click.echo(f"  [{i}] {item.name}{price}")
            click.echo(f"      image: {item.image_url}")
            click.echo(f"      url:   {item.product_url}")


@search.command("match")
@click.option("--keyword", required=True, help="Same keyword used with `search run`.")
@click.option("--source", required=True, type=click.Choice(["naver", "daiso", "oliveyoung"]))
@click.option("--index", required=True, type=int, help="0-based index into that source's results.")
@click.option("--target-page", required=True, type=click.Choice(["harujin", "shinjh"]))
@click.option("--category", required=True)
@click.option("--input", "input_path", required=True, type=click.Path(), help="products.json to upsert the match into.")
@click.option("--dry-run/--live", "dry_run", default=True)
@click.option("--headed/--headless", "headed", default=False)
def search_match(keyword, source, index, target_page, category, input_path, dry_run, headed):
    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(config, inpock_headless=not headed)

    results = search_one_source(source, keyword, config, dry_run=dry_run)
    if index >= len(results):
        raise click.ClickException(f"index {index} out of range, {source} returned {len(results)} result(s)")
    selected = results[index]

    product = match_and_upsert_product(
        selected, target_page, category, config, input_path, dry_run=dry_run
    )
    if product is None:
        click.echo(f"no coupang match found for {selected.name!r}")
        return

    click.echo(f"matched {selected.name!r} -> {product.coupang_url}")
    click.echo(f"upserted product {product.id} into {input_path}")


@cli.group()
def script():
    """5-candidate AIDA script review/selection per product.

    Candidates are authored by hand (data/scripts/<product_id>.json, exactly
    5 entries) rather than generated by this tool. `script select` is the
    "선택 즉시 자동 연동" step: it marks one candidate as active and applies
    it to data/state.json immediately.
    """


@script.command("show")
@click.option("--product-id", required=True)
@click.option("--file", "script_file", type=click.Path(exists=True), default=None)
def script_show(product_id, script_file):
    path = script_file or default_script_path(product_id)
    script_set = load_script_set(path)
    for candidate in script_set.candidates:
        marker = " (selected)" if candidate.id == script_set.selected_id else ""
        click.echo(f"--- candidate {candidate.id}{marker} ---")
        click.echo(f"  attention: {candidate.attention}")
        click.echo(f"  interest:  {candidate.interest}")
        click.echo(f"  desire:    {candidate.desire}")
        click.echo(f"  action:    {candidate.action}")


@script.command("select")
@click.option("--product-id", required=True)
@click.option("--candidate-id", required=True, type=int)
@click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="Product list file (same one used for deeplink/inpock sync).")
@click.option("--file", "script_file", type=click.Path(exists=True), default=None)
def script_select(product_id, candidate_id, input_path, script_file):
    from .script_store import save_script_set

    path = script_file or default_script_path(product_id)
    script_set = load_script_set(path)
    candidate = script_set.select(candidate_id)  # raises if candidate_id is invalid
    save_script_set(path, script_set)

    config = load_config()
    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found in {input_path}")

    state = StateStore(config.state_file_path)
    state.apply_script(product, candidate.id, candidate.full_text)
    state.save()
    click.echo(f"applied candidate {candidate.id} for {product_id}")


@cli.group()
def vending():
    """'2종 자판기': new-product/price-drop alerts + 품번 matching sourcing sheet.

    Site endpoints are uncalibrated -- see docs/VENDING.md before --live.
    """


@vending.command("run")
@click.option("--settings", "settings_path", default="data/vending/settings.json", show_default=True,
              help="Falls back to data/vending/settings.example.json if missing.")
@click.option("--blacklist", "blacklist_path", default="data/vending/blacklist.txt", show_default=True)
@click.option("--db", "db_path", default="data/vending/seen.json", show_default=True)
@click.option("--out-dir", default="output", show_default=True)
@click.option("--dry-run/--live", "dry_run", default=True, help="Dry-run reads fixtures/vending/*.json, no network.")
@click.option("--discord/--console", "discord", default=False, help="Send alerts to the Discord webhook.")
@click.option("--loop", "loop_min", type=int, default=0, help="Repeat every N minutes (0 = run once).")
@click.option("--listings", "listings_path", default="data/vending/listings.csv", show_default=True,
              help="위탁 판매중 상품 목록 (STEP 3 품절/마진 감시). Dry-run falls back to the example.")
def vending_run(settings_path, blacklist_path, db_path, out_dir, dry_run, discord, loop_min, listings_path):
    import os
    import time
    from pathlib import Path

    from .vending.db import SeenDB
    from .vending.notify import ConsoleNotifier, DiscordNotifier
    from .vending.runner import run_cycle
    from .vending.settings import load_blacklist, load_settings
    from .vending.sources import build_sources

    config = load_config()
    _setup_logging(config)
    if not Path(settings_path).exists():
        settings_path = "data/vending/settings.example.json"
    settings = load_settings(settings_path)
    blacklist = load_blacklist(blacklist_path)

    fixture_dir = "fixtures/vending" if dry_run else None
    cache_dir = None if dry_run else "data/vending/cache"
    sources = build_sources(settings.sources, fixture_dir, settings.request_delay_sec,
                            cache_dir, settings.cache_ttl_minutes)
    notifier = (DiscordNotifier(os.environ.get("VENDING_DISCORD_WEBHOOK_URL", ""))
                if discord else ConsoleNotifier(click.echo))

    from .vending.listings import load_listings

    if dry_run and not Path(listings_path).exists():
        listings_path = "data/vending/listings.example.csv"
    listings = load_listings(listings_path)

    while True:
        db = SeenDB(db_path)
        run_cycle(settings, sources, db, blacklist, notifier, out_dir, echo=click.echo, listings=listings)
        if loop_min <= 0:
            break
        click.echo(f"\n다음 사이클: {loop_min}분 후 (Ctrl+C로 종료)")
        time.sleep(loop_min * 60)


@vending.command("discover")
@click.option("--settings", "settings_path", default="data/vending/settings.json", show_default=True)
@click.option("--out-dir", default="output", show_default=True)
@click.option("--limit", type=int, default=0, help="Max 품번 to search (0 = all). Naver API allows 25,000 calls/day.")
@click.option("--top", type=int, default=20, show_default=True)
@click.option("--dry-run/--live", "dry_run", default=True, help="Dry-run uses fixtures/vending/naver_search.json.")
@click.option("--apply", "apply_", is_flag=True,
              help="Append new candidates to the naver_shop stores list in data/vending/settings.json.")
@click.option("--min-profitable", type=int, default=2, show_default=True,
              help="--apply only adds sellers with at least this many profitable 품번.")
def vending_discover(settings_path, out_dir, limit, top, dry_run, apply_, min_profitable):
    """소싱처 발굴: rank Naver sellers that sell market 품번 below market price."""
    import os
    from datetime import datetime
    from pathlib import Path

    from .vending.discover import FixtureSearcher, NaverSearcher, rank_malls, search_codes, write_discovery_xlsx
    from .vending.settings import load_settings
    from .vending.sources import build_sources

    config = load_config()
    _setup_logging(config)
    if not Path(settings_path).exists():
        settings_path = "data/vending/settings.example.json"
    settings = load_settings(settings_path)

    fixture_dir = "fixtures/vending" if dry_run else None
    cache_dir = None if dry_run else "data/vending/cache"
    market_sources = build_sources(settings.market_sources, fixture_dir, settings.request_delay_sec,
                                   cache_dir, settings.cache_ttl_minutes)
    excluded = {b.replace(" ", "") for b in settings.excluded_brands}
    brands = [b for b in settings.brands if b.lower().replace(" ", "") not in excluded]
    market_items = []
    for src in market_sources:
        for brand in brands:
            try:
                market_items.extend(src.fetch_brand(brand))
            except Exception as exc:
                click.echo(f"  [{src.name}] {brand}: 수집 실패 ({exc})")

    searcher = (FixtureSearcher("fixtures/vending/naver_search.json") if dry_run
                else NaverSearcher(os.environ.get("NAVER_CLIENT_ID", ""), os.environ.get("NAVER_CLIENT_SECRET", "")))
    results = search_codes(market_items, searcher, limit or None, echo=click.echo)
    known = [s for spec in settings.sources if spec.type == "naver_shop" for s in spec.stores]
    ranking = rank_malls(results, settings, known)

    click.echo(f"\n[소싱처 순위] 상위 {min(top, len(ranking))}곳 (수익 품번 / 시세보다 싼 품번 / 평균 할인율)")
    for i, st in enumerate(ranking[:top], 1):
        tag = "기존" if st.known else "★신규"
        click.echo(f"  {i:>2}. [{tag}] {st.mall}: {st.codes_profitable} / {st.codes_cheaper} / {st.avg_discount:.0%}"
                   + (f"  예) {st.examples[0]}" if st.examples else ""))
    new = [st.mall for st in ranking if not st.known and st.codes_profitable]
    if new:
        click.echo(f"\n  stores 목록에 추가할 후보: {json_list(new)}")
    path = write_discovery_xlsx(ranking, results, Path(out_dir) / f"discover_{datetime.now():%Y%m%d_%H%M}.xlsx")
    click.echo(f"  -> {path}")

    if apply_:
        from .vending.discover import add_stores

        chosen = [st.mall for st in ranking if not st.known and st.codes_profitable >= min_profitable]
        target = "data/vending/settings.json"
        added = add_stores(settings_path, target, chosen)
        click.echo(f"\n  {target}에 소싱처 {len(added)}곳 추가: {json_list(added)}" if added
                   else f"\n  추가할 소싱처 없음 (수익 품번 {min_profitable}개 이상 기준)")


@vending.command("outlet")
@click.option("--input", "input_path", default="data/vending/outlet_finds.csv", show_default=True,
              help="매장에서 기록한 CSV (날짜,매장,브랜드,품번,상품명,가격,사이즈,수량). Falls back to the example.")
@click.option("--settings", "settings_path", default="data/vending/settings.json", show_default=True)
@click.option("--out-dir", default="output", show_default=True)
@click.option("--min-sellers", type=int, default=2, show_default=True,
              help="'매입' requires at least this many online sellers (else '보류').")
@click.option("--dry-run/--live", "dry_run", default=True, help="Dry-run uses fixtures/vending/naver_search.json.")
def vending_outlet(input_path, settings_path, out_dir, min_sellers, dry_run):
    """오프라인 아울렛 매입 판단: outlet price vs Naver online lowest price per 품번."""
    import os
    from datetime import datetime
    from pathlib import Path

    from .vending.discover import FixtureSearcher, NaverSearcher
    from .vending.outlet import judge, load_finds, write_outlet_xlsx
    from .vending.settings import load_settings

    if not Path(input_path).exists():
        input_path = "data/vending/outlet_finds.example.csv"
    if not Path(settings_path).exists():
        settings_path = "data/vending/settings.example.json"
    settings = load_settings(settings_path)
    finds = load_finds(input_path)
    searcher = (FixtureSearcher("fixtures/vending/naver_search.json") if dry_run
                else NaverSearcher(os.environ.get("NAVER_CLIENT_ID", ""), os.environ.get("NAVER_CLIENT_SECRET", "")))

    click.echo(f"[아울렛 매입 판단] {len(finds)}개 품목 / 판매가 = 온라인 최저가 - {settings.undercut:,}원, "
               f"수수료 {settings.market_fee_rate:.1%}, 배송비 {settings.shipping_cost:,}원")
    verdicts = judge(finds, searcher, settings, min_sellers, echo=click.echo)
    for v in verdicts:
        if v.online_low is None:
            click.echo(f"  [{v.verdict}] {v.find.store} | {v.find.brand} {v.find.style_code} - {v.reason}")
    buy = [v for v in verdicts if v.verdict == "매입"]
    total = sum(v.margin * v.find.qty for v in buy)
    click.echo(f"\n  매입 {len(buy)}개 / 보류 {sum(v.verdict == '보류' for v in verdicts)}개 / "
               f"비추천 {sum(v.verdict == '비추천' for v in verdicts)}개 · 매입 시 예상 총마진 {total:,}원")
    path = write_outlet_xlsx(verdicts, Path(out_dir) / f"outlet_{datetime.now():%Y%m%d_%H%M}.xlsx")
    click.echo(f"  -> {path}")


@vending.group("stock")
def vending_stock():
    """사입 재고장: 입고/판매/반품/폐기 기록 + 재고 현황/손익 엑셀."""


_LEDGER = "data/vending/inventory.csv"


@vending_stock.command("add")
@click.argument("kind", type=click.Choice(["입고", "판매", "반품", "폐기", "조정"]))
@click.option("--code", "style_code", required=True, help="품번")
@click.option("--size", default="", help="사이즈 (신발은 꼭: 250, 265 ...)")
@click.option("--qty", type=int, required=True)
@click.option("--price", type=int, default=0, help="입고=매입가, 판매/반품=판매가")
@click.option("--brand", default="")
@click.option("--name", default="")
@click.option("--partner", default="", help="매장/판매처")
@click.option("--memo", default="")
@click.option("--date", "on", default=None, help="YYYY-MM-DD (default: today)")
@click.option("--ledger", default=_LEDGER, show_default=True)
def stock_add(kind, style_code, size, qty, price, brand, name, partner, memo, on, ledger):
    """예) vending stock add 판매 --code BV2654-063 --qty 1 --price 68900"""
    from datetime import date

    from .vending.inventory import Tx, _date, _norm_size, append_ledger, build_stock, load_ledger
    from .vending.settings import load_settings

    tx = Tx(_date(on) if on else date.today(), kind, style_code, brand, name, qty, price, partner, memo,
            _norm_size(size))
    settings = load_settings(_settings_path("data/vending/settings.json"))
    build_stock(load_ledger(ledger) + [tx], settings)  # validates (e.g. selling more than in stock)
    append_ledger(ledger, [tx])
    click.echo(f"기록: {tx.date} {kind} {style_code}{' ' + tx.size if tx.size else ''} x{qty} @ {price:,}")


@vending_stock.command("import-outlet")
@click.option("--file", "xlsx_path", required=True, type=click.Path(exists=True), help="vending outlet 결과 엑셀")
@click.option("--date", "on", default=None, help="입고일 YYYY-MM-DD (default: today)")
@click.option("--ledger", default=_LEDGER, show_default=True)
def stock_import_outlet(xlsx_path, on, ledger):
    """아울렛 매입 판단 엑셀에서 '매입' 행을 입고로 기록."""
    from datetime import date

    from .vending.inventory import _date, append_ledger, txs_from_outlet_xlsx

    txs = txs_from_outlet_xlsx(xlsx_path, _date(on) if on else date.today())
    append_ledger(ledger, txs)
    for t in txs:
        click.echo(f"입고: {t.style_code} {t.brand} x{t.qty} @ {t.price:,} ({t.partner})")
    click.echo(f"{len(txs)}건 입고 기록 -> {ledger}")


@vending_stock.command("report")
@click.option("--ledger", default=_LEDGER, show_default=True, help="Dry-run falls back to the example ledger.")
@click.option("--settings", "settings_path", default="data/vending/settings.json", show_default=True)
@click.option("--out-dir", default="output", show_default=True)
@click.option("--stale-days", type=int, default=30, show_default=True, help="이 일수 이상 보유하면 처분 추천")
@click.option("--today", default=None, help="기준일 YYYY-MM-DD (default: today)")
@click.option("--dry-run/--live", "dry_run", default=True, help="Live looks up Naver online lowest prices.")
@click.option("--no-market", is_flag=True, help="Skip the online price lookup.")
@click.option("--category", default=None, type=click.Choice(["신발", "의류", "가방", "잡화", "기타"]),
              help="이 카테고리만 표시")
def stock_report(ledger, settings_path, out_dir, stale_days, today, dry_run, no_market, category):
    """재고 현황 (손실 위험 / 처분 추천 / 마진 축소) + 품번별 실현손익 엑셀."""
    import os
    from datetime import date, datetime
    from pathlib import Path

    from .vending.discover import FixtureSearcher, NaverSearcher
    from .vending.inventory import InventoryError, _date, assess, build_stock, load_ledger, write_stock_xlsx
    from .vending.settings import load_settings

    if dry_run and not Path(ledger).exists():
        ledger = "data/vending/inventory.example.csv"
    settings = load_settings(_settings_path(settings_path))
    ref = _date(today) if today else date.today()
    try:
        lines = build_stock(load_ledger(ledger), settings)
    except InventoryError as exc:
        raise click.ClickException(str(exc)) from exc
    searcher = None
    if not no_market:
        searcher = (FixtureSearcher("fixtures/vending/naver_search.json") if dry_run
                    else NaverSearcher(os.environ.get("NAVER_CLIENT_ID", ""), os.environ.get("NAVER_CLIENT_SECRET", "")))
    if category:
        lines = {k: l for k, l in lines.items() if l.category == category}
    active = assess(lines, settings, ref, searcher, stale_days)

    click.echo(f"[재고 현황] {ref} 기준 / 품목(품번×사이즈) {len(active)}개 / 재고 {sum(l.qty for l in active)}개 / "
               f"재고 금액 {sum(l.stock_cost for l in active):,}원")
    for l in active:
        mk = f" | 최저가 {l.market_low:,}" if l.market_low else ""
        sz = f" {l.size}" if l.size else ""
        click.echo(f"  [{l.flag}] [{l.category}] {l.brand} {l.style_code}{sz} x{l.qty} @ {l.avg_cost:,} | {l.holding_days(ref)}일{mk} - {l.advice}")
    realized = sum(l.realized for l in lines.values())
    click.echo(f"\n  누적 실현손익 {realized:,}원 (매출 {sum(l.revenue for l in lines.values()):,} / "
               f"폐기손실 {sum(l.written_off for l in lines.values()):,})")
    path = write_stock_xlsx(active, lines, ref, Path(out_dir) / f"stock_{datetime.now():%Y%m%d_%H%M}.xlsx")
    click.echo(f"  -> {path}")


def _settings_path(path):
    from pathlib import Path

    return path if Path(path).exists() else "data/vending/settings.example.json"


def json_list(names):
    import json

    return json.dumps(names, ensure_ascii=False)


@cli.group()
def instagram():
    """Instagram feed posting via Meta Graph API.

    Each target_page (harujin, shinjh) maps to its own Instagram Business/Creator
    account configured via INSTAGRAM_{PAGE}_USER_ID and INSTAGRAM_{PAGE}_ACCESS_TOKEN.
    CTA and the legal disclaimer are inserted into every caption automatically.
    Run --dry-run first to preview captions without calling the API.
    """


@instagram.command("post")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--page", "page_filter", type=click.Choice(["harujin", "shinjh"]), default=None)
@click.option("--dry-run/--live", "dry_run", default=True, help="--dry-run: mock client, shows captions; --live: calls Meta Graph API.")
@click.option("--force", is_flag=True, help="Re-schedule even if state says already posted.")
@click.option("--preview-only", is_flag=True, help="Print captions without posting.")
@click.option(
    "--schedule",
    "schedule_str",
    default=None,
    metavar="YYYY-MM-DD HH:MM",
    help="KST datetime to schedule the post. Omit to use the default (next 09:00 KST).",
)
@click.option(
    "--preview-dm/--no-preview-dm",
    "preview_dm",
    default=True,
    help="DM the account owner a preview before scheduling (default: on).",
)
def instagram_post(input_path, page_filter, dry_run, force, preview_only, schedule_str, preview_dm):
    from .instagram.client import parse_schedule_time

    config = load_config()
    _setup_logging(config)
    if not dry_run:
        import dataclasses
        config = dataclasses.replace(config, instagram_api_mode="live")

    products = load_products(input_path)
    if page_filter:
        products = [p for p in products if p.target_page == page_filter]

    scheduled_publish_time: int | None = None
    if schedule_str:
        try:
            scheduled_publish_time = parse_schedule_time(schedule_str)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    products = resolve_thumbnails(products, config, products_path=input_path)

    if preview_only:
        from .state_store import StateStore
        store = StateStore(config.state_file_path)
        for product in products:
            if not product.enabled:
                continue
            product_state = store.get(product.id)
            deeplink = product_state.deeplink if product_state else "(딥링크 없음)"
            caption = build_instagram_caption(
                product, deeplink or "", config.instagram_default_cta, config.instagram_disclaimer
            )
            click.echo(f"=== {product.id} [{product.target_page}] ===")
            click.echo(caption)
            click.echo()
        return

    from .state_store import StateStore
    store = StateStore(config.state_file_path)
    outcomes = run_instagram_stage(
        products,
        config,
        store,
        force=force,
        scheduled_publish_time=scheduled_publish_time,
        preview_dm=preview_dm,
    )
    store.save()
    _print_outcomes("instagram post", outcomes)


@instagram.command("webhook")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="products.json — keyword map is built from this file at startup.")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8080, show_default=True)
@click.option("--dry-run/--live", "dry_run", default=True, help="--dry-run: mock DM client (no messages sent); --live: calls Meta Graph API.")
def instagram_webhook(input_path, host, port, dry_run):
    """Run the Instagram comment-webhook server.

    \b
    Register this URL in Meta for Developers → Webhooks → Instagram:
      https://<your-public-host>/instagram/webhook
    Subscribe to the `comments` field.
    Set INSTAGRAM_WEBHOOK_VERIFY_TOKEN to the same secret used in Meta's dashboard.

    When a follower comments a registered keyword (set per-product in products.json
    via `instagram_keyword`) the server DMs them the Coupang deeplink automatically.
    """
    try:
        import uvicorn
    except ImportError:
        raise click.ClickException("uvicorn is required: pip install uvicorn")

    from .instagram.webhook import create_app

    config = load_config()
    _setup_logging(config)

    if not dry_run:
        import dataclasses
        config = dataclasses.replace(config, instagram_api_mode="live")

    if not config.instagram_webhook_verify_token:
        click.echo("WARNING: INSTAGRAM_WEBHOOK_VERIFY_TOKEN is not set — webhook verification will fail.", err=True)

    app = create_app(config, input_path)
    click.echo(f"Starting webhook server on {host}:{port} ({'live' if not dry_run else 'dry-run'} mode)")
    click.echo(f"Register callback: https://<your-host>/instagram/webhook")
    uvicorn.run(app, host=host, port=port)


@cli.group()
def facebook():
    """Facebook Page photo posting via Meta Graph API.

    Each target_page (harujin, shinjh) maps to its own Facebook Page configured
    via FACEBOOK_{PAGE}_PAGE_ID and FACEBOOK_{PAGE}_PAGE_ACCESS_TOKEN.
    CTA and the legal disclaimer are inserted into every caption automatically.
    Run --dry-run first to preview captions without calling the API.
    """


@facebook.command("post")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--page", "page_filter", type=click.Choice(["harujin", "shinjh"]), default=None)
@click.option("--dry-run/--live", "dry_run", default=True, help="--dry-run: mock client, shows captions; --live: calls Facebook Graph API.")
@click.option("--force", is_flag=True, help="Re-post even if state says already posted.")
@click.option("--preview-only", is_flag=True, help="Print captions without posting.")
@click.option(
    "--schedule",
    "schedule_str",
    default=None,
    metavar="YYYY-MM-DD HH:MM",
    help="KST datetime to schedule the post. Omit to use the default (next 09:00 KST).",
)
def facebook_post(input_path, page_filter, dry_run, force, preview_only, schedule_str):
    from .instagram.client import parse_schedule_time
    from .state_store import StateStore

    config = load_config()
    _setup_logging(config)
    if not dry_run:
        import dataclasses
        config = dataclasses.replace(config, facebook_api_mode="live")

    products = load_products(input_path)
    if page_filter:
        products = [p for p in products if p.target_page == page_filter]

    scheduled_publish_time: int | None = None
    if schedule_str:
        try:
            scheduled_publish_time = parse_schedule_time(schedule_str)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    products = resolve_thumbnails(products, config, products_path=input_path)

    if preview_only:
        store = StateStore(config.state_file_path)
        for product in products:
            if not product.enabled:
                continue
            product_state = store.get(product.id)
            deeplink = product_state.deeplink if product_state else "(딥링크 없음)"
            caption = build_instagram_caption(
                product, deeplink or "", config.instagram_default_cta, config.instagram_disclaimer
            )
            click.echo(f"=== {product.id} [{product.target_page}] ===")
            click.echo(caption)
            click.echo()
        return

    store = StateStore(config.state_file_path)
    outcomes = run_facebook_stage(
        products,
        config,
        store,
        force=force,
        scheduled_publish_time=scheduled_publish_time,
    )
    store.save()
    _print_outcomes("facebook post", outcomes)


@cli.group()
def state():
    """Inspect or reset the local sync state file."""


@state.command("show")
def state_show():
    config = load_config()
    store = StateStore(config.state_file_path)
    for product_id, product_state in store.all().items():
        click.echo(f"{product_id}: {product_state}")


@state.command("reset")
@click.option("--product-id", required=True)
def state_reset(product_id):
    config = load_config()
    store = StateStore(config.state_file_path)
    removed = store.reset(product_id)
    store.save()
    click.echo(f"removed: {removed}")


if __name__ == "__main__":
    cli()
