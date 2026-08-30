from __future__ import annotations

import dataclasses
import logging

import click

from .config import load_config
from .input_loader import load_products
from .script_store import ScriptSet, default_script_path, load_script_set, save_script_set
from .scriptgen import generate_candidates, generate_hashtags
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
from .tts.voices import VOICE_CATALOG, get_voice
from .video.pipeline import generate_stitched_video


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
@click.option("--source", required=True, type=click.Choice(["naver", "youtube", "daiso", "oliveyoung", "instagram"]))
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
def pipeline():
    """One-shot: search -> Coupang auto-match -> script auto-generate -> deeplink.

    Chains `search match` (Coupang auto-matching + upsert), `script
    generate` (AIDA + 7-element auto script), and the deeplink stage
    (real Coupang Partners API in --live mode) into a single command, so
    a brand-new product goes from keyword to "ready for `script select`
    and `sync all`" in one call.
    """


@pipeline.command("new-product")
@click.option("--keyword", required=True)
@click.option("--source", required=True, type=click.Choice(["naver", "youtube", "daiso", "oliveyoung", "instagram"]))
@click.option("--index", required=True, type=int, help="0-based index into that source's results.")
@click.option("--target-page", required=True, type=click.Choice(["harujin", "shinjh"]))
@click.option("--category", required=True, help="e.g. 뷰티, 생활용품, 육아, 다이어트, 가전")
@click.option("--input", "input_path", required=True, type=click.Path(), help="products.json to upsert the match into.")
@click.option("--dry-run/--live", "dry_run", default=True, help="dry-run: mock search + mock Coupang match + mock deeplink API.")
@click.option("--headed/--headless", "headed", default=False)
@click.option("--force", is_flag=True, help="Overwrite an existing script file for this product if one exists.")
def pipeline_new_product(keyword, source, index, target_page, category, input_path, dry_run, headed, force):
    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(
        config,
        inpock_headless=not headed,
        coupang_api_mode="mock" if dry_run else "live",
    )

    results = search_one_source(source, keyword, config, dry_run=dry_run)
    if index >= len(results):
        raise click.ClickException(f"index {index} out of range, {source} returned {len(results)} result(s)")
    selected = results[index]

    product = match_and_upsert_product(selected, target_page, category, config, input_path, dry_run=dry_run)
    if product is None:
        click.echo(f"no coupang match found for {selected.name!r} -- stopping before script/deeplink stages")
        return
    click.echo(f"1/3 matched {selected.name!r} -> {product.coupang_url} (product {product.id})")

    script_path = default_script_path(product.id, base_dir=config.scripts_dir)
    if script_path.exists() and not force:
        click.echo(f"2/3 script already exists at {script_path}, leaving it as-is (use --force to regenerate)")
    else:
        candidates = generate_candidates(product.name, category)
        save_script_set(script_path, ScriptSet(product_id=product.id, candidates=candidates))
        click.echo(f"2/3 generated 5 script candidates -> {script_path}")

    state = StateStore(config.state_file_path)
    client = build_coupang_client(config)
    outcomes = run_deeplink_stage([product], client, state, force=True)
    state.save()
    for p, outcome, detail in outcomes:
        suffix = f" ({detail})" if detail else ""
        click.echo(f"3/3 deeplink [{outcome}] {p.id}{suffix}")

    from .scriptgen import AD_LABEL, AD_LABEL_POSITION

    click.echo(f"[필수] 영상 화면 {AD_LABEL_POSITION}에 '{AD_LABEL}' 문구를 반드시 삽입하세요.")
    click.echo(f"next: python -m shopping_shorts_sync script show --product-id {product.id}")


@cli.group()
def script():
    """5-candidate AIDA script generation/review/selection per product.

    `script generate` auto-writes exactly 5 candidates using the AIDA
    (attention-interest-desire-action) + 7-persuasion-element framework
    (desire itself, plus loss aversion / social proof / authority /
    curiosity gap / quantified benefit / family narrative). Candidates can
    still be hand-edited afterward (data/scripts/<product_id>.json).
    `script select` is the "선택 즉시 자동 연동" step: it marks one
    candidate as active and applies it to data/state.json immediately.
    """


@script.command("generate")
@click.option("--product-id", required=True)
@click.option("--name", required=True, help="Product name to write into the script.")
@click.option("--category", required=True, help="e.g. 뷰티, 생활용품, 육아, 다이어트, 가전")
@click.option("--file", "script_file", type=click.Path(), default=None)
@click.option("--force", is_flag=True, help="Overwrite an existing script file (loses any hand edits/selection).")
def script_generate(product_id, name, category, script_file, force):
    path = script_file or default_script_path(product_id, base_dir=load_config().scripts_dir)
    if path.exists() and not force:
        raise click.ClickException(f"{path} already exists (use --force to overwrite)")

    candidates = generate_candidates(name, category)
    script_set = ScriptSet(product_id=product_id, candidates=candidates)
    save_script_set(path, script_set)
    click.echo(f"generated 5 candidates -> {path}")
    for c in candidates:
        click.echo(f"  [{c.id}] ({c.technique}) {c.attention}")

    from .scriptgen import AD_LABEL, AD_LABEL_POSITION

    click.echo(f"\n[필수] 영상 제작 시 화면 {AD_LABEL_POSITION}에 '{AD_LABEL}' 문구를 반드시 삽입하세요.")


@script.command("hashtags")
@click.option("--name", required=True)
@click.option("--category", required=True)
def script_hashtags(name, category):
    from .scriptgen import AD_LABEL, AD_LABEL_POSITION, COUPANG_PARTNERS_DISCLOSURE

    click.echo(f"[필수] 영상 화면 {AD_LABEL_POSITION}에 '{AD_LABEL}' 문구 삽입 (모든 영상 공통)")
    click.echo(COUPANG_PARTNERS_DISCLOSURE)
    click.echo()
    for platform, tags in generate_hashtags(name, category).items():
        click.echo(f"{platform}: {' '.join(tags)}")


@script.command("show")
@click.option("--product-id", required=True)
@click.option("--file", "script_file", type=click.Path(exists=True), default=None)
def script_show(product_id, script_file):
    path = script_file or default_script_path(product_id, base_dir=load_config().scripts_dir)
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

    config = load_config()
    path = script_file or default_script_path(product_id, base_dir=config.scripts_dir)
    script_set = load_script_set(path)
    candidate = script_set.select(candidate_id)  # raises if candidate_id is invalid
    save_script_set(path, script_set)

    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found in {input_path}")

    state = StateStore(config.state_file_path)
    state.apply_script(product, candidate.id, candidate.full_text)
    state.save()
    click.echo(f"applied candidate {candidate.id} for {product_id}")


@cli.group()
def video():
    """Download 3 selected source videos and auto-stitch into one ("자동 짜깁기").

    Sources are YouTube/Instagram video URLs (see `search run --source
    youtube` / `--source instagram`). --live requires `yt-dlp` and
    `ffmpeg` on PATH -- see docs/CALIBRATION.md. Downloading and reusing
    someone else's video ("2차 창작") is a copyright judgment call the
    owner has made for themselves; this tool only handles the mechanics.
    """


@video.command("stitch")
@click.option("--product-id", required=True)
@click.option("--url", "urls", multiple=True, required=True, help="Exactly 3 source video URLs -- repeat --url for each.")
@click.option("--live/--dry-run", "live", default=False)
def video_stitch(product_id, urls, live):
    if len(urls) != 3:
        raise click.ClickException(f"exactly 3 --url values required, got {len(urls)}")

    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(config, video_mode="live" if live else "mock")

    output_path = generate_stitched_video(list(urls), product_id, config)

    state = StateStore(config.state_file_path)
    state.record_video(product_id, str(output_path), list(urls))
    state.save()
    click.echo(f"stitched video -> {output_path}")


@cli.group()
def tts():
    """Typecast TTS generation for a product's selected script.

    Requires a script already selected via `script select` first. Voice
    catalog is 20 fixed options (표준 + 경상도/전라도/충청도/강원도 satoori,
    각 남/여 x 20-30대/40-60대); only 예슬 (표준_여성_20-30대) is a
    confirmed real Typecast actor id -- see docs/CALIBRATION.md before
    --live use with any other voice.
    """


@tts.command("voices")
def tts_voices():
    for v in VOICE_CATALOG:
        flag = "" if v.calibrated else " (미검증, calibrate 필요)"
        click.echo(f"{v.label}: actor_id={v.actor_id}{flag}")


@tts.command("generate")
@click.option("--product-id", required=True)
@click.option("--voice-label", type=click.Choice([v.label for v in VOICE_CATALOG]), default=None, help="20개 보이스 카탈로그 중 선택. 생략 시 TYPECAST_ACTOR_ID 기본값 사용.")
@click.option("--live/--dry-run", "live", default=False, help="Call the real Typecast API instead of the mock client.")
def tts_generate(product_id, voice_label, live):
    from .tts import build_tts_client

    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(config, typecast_mode="live" if live else "mock")

    state = StateStore(config.state_file_path)
    product_state = state.get(product_id)
    if product_state is None or not product_state.script_text:
        raise click.ClickException(f"product {product_id!r} has no selected script yet -- run `script select` first")

    actor_id = get_voice(voice_label).actor_id if voice_label else config.typecast_actor_id

    client = build_tts_client(config)
    result = client.synthesize(product_state.script_text, actor_id=actor_id, speed=config.typecast_speed)

    state.record_voice(product_id, result.audio_url, actor_id)
    state.save()
    click.echo(f"voice generated ({actor_id}) -> {result.audio_url}")


@cli.group()
def publish():
    """Publish a product's stitched video to TikTok/YouTube/Instagram.

    Requires a stitched video (`video stitch`) and a selected script
    (`script select`) first. TikTok needs app-review approval before it can
    post anywhere but the developer's own test account; YouTube needs a
    one-time local OAuth consent to produce a token file; Instagram needs a
    **public HTTPS URL** for the video, not a local path -- see
    docs/CALIBRATION.md before --live use with any of the three.
    """


@publish.command("run")
@click.option("--product-id", required=True)
@click.option("--platform", required=True, type=click.Choice(["tiktok", "youtube", "instagram"]))
@click.option("--product-name", default=None, help="Used as the YouTube video title (max 100 chars). Defaults to --product-id.")
@click.option("--dry-run/--live", "dry_run", default=True, help="Dry-run skips the real API call and records a placeholder result.")
@click.option("--video-url", default=None, help="Public HTTPS URL for the video (Instagram --live only; overrides PUBLIC_BASE_URL).")
def publish_run(product_id, platform, product_name, dry_run, video_url):
    from .publisher import build_publisher, public_video_url

    config = load_config()
    _setup_logging(config)

    state = StateStore(config.state_file_path)
    product_state = state.get(product_id)
    if product_state is None or not product_state.stitched_video_path:
        raise click.ClickException(f"product {product_id!r} has no stitched video yet -- run `video stitch` first")
    if not product_state.script_text:
        raise click.ClickException(f"product {product_id!r} has no selected script yet -- run `script select` first")

    video_path = product_state.stitched_video_path
    if platform == "instagram" and not dry_run:
        video_path = video_url or public_video_url(config, product_id, video_path)
        if not video_path:
            raise click.ClickException(
                "PUBLIC_BASE_URL is not set -- Instagram needs a public HTTPS URL for "
                "the video, not a local path. Set PUBLIC_BASE_URL to the deployed "
                "webapp's base URL, or pass --video-url explicitly."
            )

    publisher = build_publisher(platform, config, dry_run=dry_run)
    result = publisher.publish(video_path, product_state.script_text, product_name or product_id)

    state.record_publish(product_id, platform, result)
    state.save()

    if result.success:
        click.echo(f"published to {platform}: {result.post_url or result.post_id}")
    else:
        raise click.ClickException(f"publish to {platform} failed: {result.error}")


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


@cli.command("web")
@click.option("--input", "input_path", required=True, type=click.Path(), help="products.json to back the dashboard.")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=5000, show_default=True, type=int)
@click.option("--debug", is_flag=True)
def web(input_path, host, port, debug):
    """Runs the mobile-friendly web dashboard (search -> product -> script -> hashtags -> approve)."""
    from .webapp import create_app

    app = create_app(products_path=input_path)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    cli()
