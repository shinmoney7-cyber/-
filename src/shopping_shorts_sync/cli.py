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
def vending_run(settings_path, blacklist_path, db_path, out_dir, dry_run, discord, loop_min):
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

    while True:
        db = SeenDB(db_path)
        run_cycle(settings, sources, db, blacklist, notifier, out_dir, echo=click.echo)
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
