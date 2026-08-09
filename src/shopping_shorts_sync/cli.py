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
from .meta.accounts import AccountConfig, MultiAccountPublisher, ACCOUNTS
from .meta.mock_client import MockMultiAccountPublisher
from .publish_store import PublishStore, PipelineStatus
from .content.pipeline import build_pipeline, ProductBrief


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


def _build_account_configs(config) -> list[AccountConfig]:
    return [
        AccountConfig(
            name="mom_moneytip",
            ig_user_id=config.meta_mom_moneytip_ig_user_id,
            threads_user_id=config.meta_mom_moneytip_threads_user_id,
            access_token=config.meta_mom_moneytip_access_token,
        ),
        AccountConfig(
            name="showpingkkultem",
            ig_user_id=config.meta_showpingkkultem_ig_user_id,
            threads_user_id=config.meta_showpingkkultem_threads_user_id,
            access_token=config.meta_showpingkkultem_access_token,
        ),
        AccountConfig(
            name="haru_moneytip",
            ig_user_id=config.meta_haru_moneytip_ig_user_id,
            threads_user_id=config.meta_haru_moneytip_threads_user_id,
            access_token=config.meta_haru_moneytip_access_token,
        ),
    ]


def _build_publisher(config, dry_run: bool) -> MultiAccountPublisher:
    accounts = _build_account_configs(config)
    if dry_run or config.meta_api_mode != "live":
        return MockMultiAccountPublisher(accounts, api_version=config.meta_api_version)
    return MultiAccountPublisher(accounts, api_version=config.meta_api_version)


# ── publish 커맨드 그룹 ────────────────────────────────────────────────────


@cli.group()
def publish():
    """콘텐츠 생성 → 영상 업로드 → Instagram·Threads 게시 파이프라인."""


@publish.command("run")
@click.option("--product-id", required=True, help="products.json 내 상품 ID.")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--hook", required=True, help="3초 후킹 문구.")
@click.option("--problem", required=True, help="문제 제기/공감 문구.")
@click.option("--feature1", required=True, help="핵심 기능 1.")
@click.option("--feature2", required=True, help="핵심 기능 2.")
@click.option("--proof", required=True, help="검증 가능한 신뢰 근거.")
@click.option("--cta", required=True, help="행동 유도 문구.")
@click.option("--inpock-url", required=True, help="상품에 정확히 대응하는 인포크 URL.")
@click.option("--duration", default=30, type=click.Choice(["15", "30", "50"]), help="대본 길이(초).")
@click.option("--dry-run/--live", "dry_run", default=True,
              help="--dry-run: mock 클라이언트 사용 (API 미호출). --live: 실제 API 호출.")
@click.option("--skip-approve", is_flag=True, help="미리보기 없이 바로 게시 (자동화 전용).")
def publish_run(product_id, input_path, hook, problem, feature1, feature2, proof, cta,
                inpock_url, duration, dry_run, skip_approve):
    """상품 브리프를 입력받아 콘텐츠 생성 → 3개 계정 × 2 플랫폼 게시 전 과정을 실행한다."""
    config = load_config()
    _setup_logging(config)

    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} not found in {input_path}")
    if not inpock_url:
        raise click.ClickException("LINK_BLOCKED: --inpock-url 이 없으면 진행할 수 없습니다.")

    pub_store = PublishStore(config.publish_state_file_path)
    rec = pub_store.create(product.id, product.name, product.category)
    rec.set_status(PipelineStatus.FACT_CHECKED)
    rec.inpock_url = inpock_url
    pub_store.save()

    brief = ProductBrief(
        product_id=product.id,
        name=product.name,
        category=product.category,
        hook=hook,
        problem=problem,
        feature_1=feature1,
        feature_2=feature2,
        proof=proof,
        cta=cta,
        inpock_url=inpock_url,
    )
    rec.set_status(PipelineStatus.SCRIPTED)
    pub_store.save()

    # ── 콘텐츠 생성 ──────────────────────────────────────────────────────
    pipeline = build_pipeline(config, dry_run=dry_run)
    click.echo(f"[콘텐츠 생성] {product.name} ({'dry-run' if dry_run else 'live'})")
    try:
        assets = pipeline.run(brief, script_duration=int(duration))
    except Exception as exc:
        rec.add_error(f"content pipeline failed: {exc}")
        rec.set_status(PipelineStatus.FAILED)
        pub_store.save()
        raise click.ClickException(f"콘텐츠 생성 실패: {exc}") from exc

    rec.set_status(PipelineStatus.ASSETS_READY)
    rec.video_path = assets.video_path
    rec.thumbnail_path = assets.thumbnail_path
    rec.captions = assets.captions
    pub_store.save()

    rec.set_status(PipelineStatus.RENDERED)
    pub_store.save()

    if assets.video_url:
        rec.video_url = assets.video_url
        rec.set_status(PipelineStatus.LINK_READY)
        pub_store.save()

    # ── 미리보기 및 승인 ──────────────────────────────────────────────────
    if not skip_approve:
        click.echo("\n── 게시 미리보기 ──────────────────────────────────────────")
        click.echo(f"  상품: {product.name}")
        click.echo(f"  영상: {assets.video_path}")
        click.echo(f"  URL : {assets.video_url}")
        click.echo(f"  인포크: {inpock_url}")
        for account, caption in assets.captions.items():
            click.echo(f"\n  [{account}]\n{caption[:120]}…")
        click.echo()
        click.confirm("위 내용으로 6개 목적지(3계정 × Instagram+Threads)에 게시하시겠습니까?",
                      abort=True)

    rec.set_status(PipelineStatus.APPROVED)
    pub_store.save()

    # ── 게시 ─────────────────────────────────────────────────────────────
    if not assets.video_url:
        raise click.ClickException("영상 URL이 없어 게시할 수 없습니다. 스토리지를 확인하세요.")

    publisher = _build_publisher(config, dry_run)
    click.echo(f"\n[게시 시작] {'dry-run' if dry_run else 'live'}")
    results = publisher.publish(assets.video_url, assets.captions)

    for result in results:
        rec.record_destination(result.account, result.platform, result)
        icon = "✅" if result.ok else "❌"
        detail = result.post_url or result.error or ""
        click.echo(f"  {icon} {result.account} / {result.platform}: {detail}")

    if rec.all_published():
        rec.set_status(PipelineStatus.PUBLISHED)
    else:
        rec.add_error("일부 목적지 게시 실패")
        rec.set_status(PipelineStatus.FAILED)
    pub_store.save()

    # ── 검증 ─────────────────────────────────────────────────────────────
    # 실제 게시 확인: post_id 가 있을 때만 검증 완료로 표시
    all_verified = True
    for result in results:
        if result.ok and result.post_id:
            rec.verify_destination(result.account, result.platform, result.post_url)
        else:
            all_verified = False

    if all_verified:
        rec.set_status(PipelineStatus.VERIFIED)
    pub_store.save()

    # ── 결과 출력 ─────────────────────────────────────────────────────────
    click.echo(f"\n최종 상태: {rec.pipeline_status}")
    _print_publish_table(rec.summary_rows())


def _print_publish_table(rows: list[dict]) -> None:
    headers = ["destination", "status", "post_url", "error"]
    click.echo("\n── 게시 결과 ──────────────────────────────────────────────")
    for row in rows:
        dest = row.get("destination", "")
        status = row.get("status", "")
        url = (row.get("post_url") or "")[:60]
        err = (row.get("error") or "")[:60]
        click.echo(f"  {dest:<35} [{status:<9}] {url or err}")


@publish.command("status")
@click.option("--product-id", default=None)
def publish_status(product_id):
    """게시 파이프라인 상태를 조회한다."""
    config = load_config()
    store = PublishStore(config.publish_state_file_path)
    records = store.all()
    if product_id:
        rec = records.get(product_id)
        if rec is None:
            click.echo(f"상품 {product_id!r} 의 게시 이력이 없습니다.")
            return
        _print_publish_table(rec.summary_rows())
        return
    for pid, rec in records.items():
        click.echo(f"{pid} ({rec.product_name}): {rec.pipeline_status}")


@publish.command("reset")
@click.option("--product-id", required=True)
def publish_reset(product_id):
    """특정 상품의 게시 이력을 초기화한다."""
    config = load_config()
    store = PublishStore(config.publish_state_file_path)
    removed = store.reset(product_id)
    store.save()
    click.echo(f"{'삭제됨' if removed else '이력 없음'}: {product_id}")


# ── meta 커맨드 그룹 ──────────────────────────────────────────────────────


@cli.group()
def meta():
    """Meta 계정 연결 검증 및 토큰 갱신."""


@meta.command("verify-accounts")
@click.option("--dry-run/--live", "dry_run", default=True)
def meta_verify_accounts(dry_run):
    """3개 계정 × Instagram+Threads 연결 상태를 확인한다."""
    config = load_config()
    publisher = _build_publisher(config, dry_run)
    statuses = publisher.verify_accounts()
    for s in statuses:
        icon = "✅" if s.get("ok") else "❌"
        acct = s.get("account", "")
        plat = s.get("platform", "")
        detail = s.get("user_id") or s.get("error", "")
        click.echo(f"  {icon} {acct:<20} {plat:<10} {detail}")


@meta.command("refresh-tokens")
@click.option("--dry-run/--live", "dry_run", default=True)
def meta_refresh_tokens(dry_run):
    """장기 액세스 토큰을 갱신한다 (60일마다 필요)."""
    if dry_run:
        click.echo("[dry-run] 토큰 갱신 시뮬레이션 — 실제 API 미호출")
        return

    config = load_config()
    from .meta.instagram import InstagramClient
    from .meta.threads import ThreadsClient

    accounts = _build_account_configs(config)
    for account in accounts:
        try:
            ig = InstagramClient(account.access_token, api_version=config.meta_api_version)
            result = ig.refresh_long_lived_token(config.meta_app_secret)
            click.echo(f"✅ {account.name}/instagram token refreshed, expires_in={result.get('expires_in')}s")
        except Exception as exc:
            click.echo(f"❌ {account.name}/instagram refresh failed: {exc}")

        try:
            t = ThreadsClient(account.access_token, api_version=config.meta_api_version)
            result = t.refresh_long_lived_token()
            click.echo(f"✅ {account.name}/threads token refreshed, expires_in={result.get('expires_in')}s")
        except Exception as exc:
            click.echo(f"❌ {account.name}/threads refresh failed: {exc}")


if __name__ == "__main__":
    cli()
