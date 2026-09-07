from __future__ import annotations

import dataclasses
import logging

import click

from .config import load_config
from .input_loader import load_products
from .script_store import default_script_path, load_script_set
from .search.orchestrator import match_and_upsert_product, search_all_sources, search_one_source
from .state_store import StateStore
from .sync import build_coupang_client, run_deeplink_stage, run_full_sync, run_inpock_stage


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


# ===========================================================================
# PLATFORM PUBLISH COMMANDS
# ===========================================================================

def _build_publish_orchestrator(config, dry_run: bool = True):
    """Build a PublishOrchestrator from config. Uses mock clients when dry_run=True."""
    from .publish.orchestrator import PublishOrchestrator

    if dry_run:
        from .platforms.tiktok import MockTikTokClient
        from .platforms.youtube import MockYouTubeClient
        from .platforms.instagram import MockInstagramClient
        from .platforms.naver_blog import MockNaverBlogClient
        from .platforms.email_sender import MockEmailSender
        return PublishOrchestrator(
            tiktok=MockTikTokClient(),
            youtube=MockYouTubeClient(),
            instagram=MockInstagramClient(),
            naver_blog=MockNaverBlogClient(),
            email_sender=MockEmailSender(),
            email_recipients=config.email_recipients or ["mock@example.com"],
        )

    from .platforms.tiktok import TikTokClient
    from .platforms.youtube import YouTubeClient
    from .platforms.instagram import InstagramClient
    from .platforms.naver_blog import NaverBlogClient
    from .platforms.email_sender import EmailSender

    tiktok = TikTokClient(config.tiktok_access_token, config.tiktok_client_key, config.tiktok_client_secret) if config.tiktok_access_token else None
    youtube = YouTubeClient(config.youtube_client_id, config.youtube_client_secret, config.youtube_refresh_token, config.youtube_channel_id) if config.youtube_refresh_token else None
    instagram = InstagramClient(config.instagram_access_token, config.instagram_business_account_id) if config.instagram_access_token else None
    naver_blog = NaverBlogClient(config.naver_blog_client_id, config.naver_blog_client_secret, config.naver_blog_access_token, config.naver_blog_id) if config.naver_blog_access_token else None
    email_sender = EmailSender(config.email_sender, config.email_password, config.email_smtp_host, config.email_smtp_port) if config.email_sender else None

    return PublishOrchestrator(
        tiktok=tiktok,
        youtube=youtube,
        instagram=instagram,
        naver_blog=naver_blog,
        email_sender=email_sender,
        email_recipients=config.email_recipients,
    )


@cli.group()
def publish():
    """Publish product shorts to social platforms (TikTok / YouTube / Instagram / Naver Blog / Email)."""


@publish.command("all")
@click.option("--product-id", required=True, help="Product ID from products.json")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--video", "video_path", required=True, type=click.Path(exists=True), help="Local .mp4 file to publish.")
@click.option("--video-cdn-url", default="", help="Public CDN URL of the video (required for Instagram).")
@click.option("--platforms", default="", help="Comma-separated platform list. Empty = all.")
@click.option("--tags", default="", help="Comma-separated hashtags (no #).")
@click.option("--dry-run/--live", "dry_run", default=True)
def publish_all(product_id, input_path, video_path, video_cdn_url, platforms, tags, dry_run):
    """Publish to all configured platforms."""
    config = load_config()
    _setup_logging(config)

    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found")

    state = StateStore(config.state_file_path)
    product_state = state.all().get(product_id, {})
    deeplink = product_state.get("deeplink", product.coupang_url)
    script_text = product_state.get("script_text", product.name)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] if platforms else None

    orchestrator = _build_publish_orchestrator(config, dry_run=dry_run)
    summary = orchestrator.publish_product(
        product_id=product.id,
        product_name=product.name,
        category=product.category,
        coupang_deeplink=deeplink,
        thumbnail_url=product.thumbnail,
        script_text=script_text,
        video_path=video_path,
        video_cdn_url=video_cdn_url,
        tags=tag_list,
        platforms=platform_list,
    )
    click.echo(str(summary))


@publish.command("tiktok")
@click.option("--product-id", required=True)
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--video", "video_path", required=True, type=click.Path(exists=True))
@click.option("--tags", default="")
@click.option("--dry-run/--live", "dry_run", default=True)
def publish_tiktok(product_id, input_path, video_path, tags, dry_run):
    """Publish to TikTok only."""
    config = load_config()
    _setup_logging(config)
    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    orchestrator = _build_publish_orchestrator(config, dry_run=dry_run)
    summary = orchestrator.publish_product(
        product_id=product.id, product_name=product.name, category=product.category,
        coupang_deeplink=product.coupang_url, thumbnail_url=product.thumbnail,
        script_text=product.name, video_path=video_path, tags=tag_list,
        platforms=["tiktok"],
    )
    click.echo(str(summary))


@publish.command("youtube")
@click.option("--product-id", required=True)
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--video", "video_path", required=True, type=click.Path(exists=True))
@click.option("--tags", default="")
@click.option("--dry-run/--live", "dry_run", default=True)
def publish_youtube(product_id, input_path, video_path, tags, dry_run):
    """Publish as YouTube Short."""
    config = load_config()
    _setup_logging(config)
    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    orchestrator = _build_publish_orchestrator(config, dry_run=dry_run)
    summary = orchestrator.publish_product(
        product_id=product.id, product_name=product.name, category=product.category,
        coupang_deeplink=product.coupang_url, thumbnail_url=product.thumbnail,
        script_text=product.name, video_path=video_path, tags=tag_list,
        platforms=["youtube"],
    )
    click.echo(str(summary))


@publish.command("naver-blog")
@click.option("--product-id", required=True)
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--tags", default="")
@click.option("--dry-run/--live", "dry_run", default=True)
def publish_naver_blog(product_id, input_path, tags, dry_run):
    """Post product review to Naver Blog."""
    config = load_config()
    _setup_logging(config)
    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found")
    state = StateStore(config.state_file_path)
    product_state = state.all().get(product_id, {})
    deeplink = product_state.get("deeplink", product.coupang_url)
    script_text = product_state.get("script_text", product.name)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    orchestrator = _build_publish_orchestrator(config, dry_run=dry_run)
    summary = orchestrator.publish_product(
        product_id=product.id, product_name=product.name, category=product.category,
        coupang_deeplink=deeplink, thumbnail_url=product.thumbnail,
        script_text=script_text, video_path="", tags=tag_list,
        platforms=["naver_blog"],
    )
    click.echo(str(summary))


@publish.command("email")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--subject", default="오늘의 쇼핑 추천")
@click.option("--dry-run/--live", "dry_run", default=True)
def publish_email(input_path, subject, dry_run):
    """Send email newsletter for all enabled products."""
    config = load_config()
    _setup_logging(config)

    import json
    products_raw = json.loads(open(input_path).read())
    if isinstance(products_raw, list):
        enabled = [p for p in products_raw if p.get("enabled", True)]
    else:
        enabled = [products_raw]

    state = StateStore(config.state_file_path)
    state_data = state.all()
    for p in enabled:
        pid = p.get("id", "")
        p["deeplink"] = state_data.get(pid, {}).get("deeplink", p.get("coupang_url", ""))

    orchestrator = _build_publish_orchestrator(config, dry_run=dry_run)
    result = orchestrator._publish_email(enabled, subject)
    click.echo(f"[email] {'OK' if result.success else f'FAIL ({result.error})'}")


# ===========================================================================
# VIDEO GENERATION COMMANDS
# ===========================================================================

@cli.group()
def video():
    """Generate vertical product videos using Higgs AI."""


@video.command("generate")
@click.option("--product-id", required=True)
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output-dir", default="data/videos", show_default=True)
@click.option("--dry-run/--live", "dry_run", default=True)
def video_generate(product_id, input_path, output_dir, dry_run):
    """Generate a 9:16 short video for a product."""
    config = load_config()
    _setup_logging(config)

    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found")

    state = StateStore(config.state_file_path)
    script_text = state.all().get(product_id, {}).get("script_text", product.name)
    output_path = f"{output_dir}/{product_id}.mp4"

    if dry_run:
        from .content.video_pipeline import MockVideoPipeline
        pipeline = MockVideoPipeline()
    else:
        from .content.video_pipeline import VideoPipeline
        if not config.higgs_api_key:
            raise click.ClickException("HIGGS_API_KEY not set in .env")
        pipeline = VideoPipeline(config.higgs_api_key)

    result = pipeline.generate_and_download(
        product_name=product.name,
        script_text=script_text,
        product_image_url=product.thumbnail,
        output_path=output_path,
    )
    if result:
        click.echo(f"video saved: {result}")
    else:
        click.echo("video generation failed", err=True)


@video.command("script")
@click.option("--product-id", required=True)
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--platform", default="tiktok", type=click.Choice(["tiktok", "youtube", "instagram"]))
@click.option("--dry-run/--live", "dry_run", default=True)
def video_script(product_id, input_path, platform, dry_run):
    """Auto-generate 5 AIDA script candidates with AI."""
    config = load_config()
    _setup_logging(config)

    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found")

    if dry_run:
        from .content.script_ai import MockScriptAI
        ai = MockScriptAI()
    else:
        from .content.script_ai import ScriptAI
        if not config.anthropic_api_key:
            raise click.ClickException("ANTHROPIC_API_KEY not set in .env")
        ai = ScriptAI(config.anthropic_api_key)

    candidates = ai.generate_candidates(
        product_name=product.name,
        category=product.category,
        thumbnail_url=product.thumbnail,
        platform=platform,
    )
    hashtags = ai.generate_hashtags(product.name, product.category, platform)

    for c in candidates:
        click.echo(f"\n--- 후보 {c.id} ---")
        click.echo(f"  주의(A): {c.attention}")
        click.echo(f"  흥미(I): {c.interest}")
        click.echo(f"  욕망(D): {c.desire}")
        click.echo(f"  행동(A): {c.action}")

    if hashtags:
        click.echo(f"\n추천 해시태그: #{' #'.join(hashtags)}")

    click.echo(f"\n선택하려면: python -m shopping_shorts_sync script select --product-id {product_id} --candidate-id <번호> --input {input_path}")


# ===========================================================================
# COUPANG PRICE MONITOR
# ===========================================================================

@cli.group("monitor")
def monitor_group():
    """Coupang price monitoring and drop alerts."""


@monitor_group.command("prices")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--dry-run/--live", "dry_run", default=True)
@click.option("--headed/--headless", "headed", default=False)
def monitor_prices(input_path, dry_run, headed):
    """Check prices for all products and report drops."""
    import json
    config = load_config()
    _setup_logging(config)

    products_raw = json.loads(open(input_path).read())
    if not isinstance(products_raw, list):
        products_raw = [products_raw]

    from .coupang.price_monitor import PriceMonitor
    monitor = PriceMonitor(
        chromium_path=config.playwright_chromium_path,
        price_history_path=config.price_history_path,
        drop_threshold_pct=config.price_drop_threshold_pct,
        headless=not headed,
    )

    results = monitor.check_all(products_raw, dry_run=dry_run)
    alerts = []
    for snapshot, alert in results:
        price_str = f"₩{snapshot.price:,}" if snapshot.price else "N/A"
        rocket = " 🚀" if snapshot.rocket else ""
        click.echo(f"  {snapshot.product_name}: {price_str}{rocket}")
        if alert:
            alerts.append(alert)
            click.echo(f"    ⚡ 가격 하락! ₩{alert.old_price:,} -> ₩{alert.new_price:,} (-{alert.drop_pct}%)")

    if alerts:
        click.echo(f"\n총 {len(alerts)}개 상품 가격 하락 감지")
    else:
        click.echo("\n가격 변동 없음")


@monitor_group.command("history")
@click.option("--product-id", required=True)
def monitor_history(product_id):
    """Show price history for a product."""
    import json
    config = load_config()
    from .coupang.price_monitor import PriceMonitor
    monitor = PriceMonitor(
        chromium_path=config.playwright_chromium_path,
        price_history_path=config.price_history_path,
    )
    history = monitor.get_history(product_id)
    if not history:
        click.echo(f"가격 이력 없음: {product_id}")
        return
    for entry in history[-20:]:
        price_str = f"₩{entry['price']:,}" if entry.get("price") else "N/A"
        click.echo(f"  {entry['checked_at'][:16]}  {price_str}")


if __name__ == "__main__":
    cli()
