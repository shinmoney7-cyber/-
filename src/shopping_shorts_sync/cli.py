from __future__ import annotations

import dataclasses
import json
import logging

import click

from .config import load_config
from .input_loader import load_products
from .script_store import default_script_path, load_script_set
from .search.orchestrator import match_and_upsert_product, match_to_coupang, search_all_sources, search_one_source
from .state_store import StateStore
from .sync import build_coupang_client, run_deeplink_stage, run_full_sync, run_inpock_stage
from .topview_gpt import TopviewGptError, generate_script, generate_script_gpt


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
@click.option("--source", required=True, type=click.Choice(["naver", "daiso", "oliveyoung", "google"]))
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


@cli.group("google-shorts")
def google_shorts_group():
    """구글 플로우: 검색 → Gemini 대본/자막/해시태그 → TopView 패키지 한번에."""


@google_shorts_group.command("run")
@click.option("--keyword", "-k", required=True, help="구글 쇼핑 검색어 (예: 선크림 SPF50)")
@click.option("--limit", default=5, show_default=True, help="검색 결과 최대 개수")
@click.option("--index", default=0, show_default=True, help="사용할 검색 결과 인덱스 (0부터)")
@click.option("--dry-run/--live", "dry_run", default=True,
              help="--dry-run: 모의 데이터 사용 (API 키 불필요) / --live: 실제 Google+Gemini API 호출")
@click.option("--no-coupang", "skip_coupang", is_flag=True,
              help="쿠팡 매칭 건너뛰기 — 구글 결과 URL을 그대로 사용")
@click.option("--engine", type=click.Choice(["gemini", "gpt"]), default="gemini", show_default=True,
              help="AI 엔진 선택: gemini (GOOGLE_API_KEY) 또는 gpt (OPENAI_API_KEY)")
@click.option("--model", default=None, show_default=False,
              help="AI 모델 지정 (기본값: gemini=gemini-2.0-flash, gpt=gpt-4o-mini)")
@click.option("--no-script", "no_script", is_flag=True,
              help="AI 대본 생성 없이 TopView 입력 정보만 출력 (TopView only 모드)")
@click.option("--json-out", "json_out", is_flag=True, help="TopView 패키지를 JSON으로 출력")
def google_shorts_run(keyword, limit, index, dry_run, skip_coupang, engine, model, no_script, json_out):
    """구글 쇼핑 검색 후 Gemini로 15초 숏츠 패키지를 생성합니다.

    \b
    예시:
      # 테스트 (API 키 없이)
      python -m shopping_shorts_sync google-shorts run -k "선크림"

      # 실제 실행
      python -m shopping_shorts_sync google-shorts run -k "선크림" --live

      # 쿠팡 매칭 없이 + JSON 출력
      python -m shopping_shorts_sync google-shorts run -k "선크림" --live --no-coupang --json-out
    """
    config = load_config()
    _setup_logging(config)

    # 1. 구글 쇼핑 검색
    click.echo(f"🔍 '{keyword}' 구글 쇼핑 검색 중...")
    hits = search_one_source("google", keyword, config, dry_run=dry_run, limit=limit)
    if not hits:
        raise click.ClickException("검색 결과가 없습니다. 다른 키워드를 시도해보세요.")

    if index >= len(hits):
        raise click.ClickException(
            f"index {index}가 범위를 벗어났습니다. 검색 결과는 {len(hits)}개입니다."
        )

    top = hits[index]
    click.echo(f"  선택: [{index}] {top.name}")
    if top.price:
        click.echo(f"  가격: {top.price}원")

    # 2. 쿠팡 매칭
    product_url = top.product_url
    if not skip_coupang:
        click.echo(f"🛒 쿠팡 딥링크 매칭 중...")
        coupang_url = match_to_coupang(top.name, config, dry_run=dry_run)
        if coupang_url:
            product_url = coupang_url
            click.echo(f"  쿠팡 링크: {coupang_url}")
        else:
            click.echo("  ⚠️  쿠팡 매칭 실패 → 구글 결과 URL 사용")

    # 3. AI 대본/자막/해시태그 생성 (no_script 모드면 건너뜀)
    if no_script:
        topview_payload = {
            "product_name": top.name,
            "product_url": product_url,
            "image_url": top.image_url,
            "price": top.price,
        }
        if json_out:
            click.echo(json.dumps(topview_payload, ensure_ascii=False, indent=2))
            return
        click.echo("\n" + "━" * 50)
        click.echo(f"📦  {top.name}  TopView 입력 정보")
        click.echo("━" * 50)
        click.echo(f"  제품명  : {top.name}")
        if top.price:
            click.echo(f"  가격    : {top.price}원")
        click.echo(f"  이미지  : {top.image_url}")
        click.echo(f"  URL     : {product_url}")
        click.echo("━" * 50)
        click.echo("💡 위 정보를 TopView.ai에 직접 붙여넣으세요.")
        return

    if engine == "gpt":
        gpt_model = model or "gpt-4o-mini"
        click.echo(f"✍️  OpenAI GPT({gpt_model})로 숏츠 패키지 생성 중...")
        try:
            result = generate_script_gpt(
                product_name=top.name,
                product_url=product_url,
                image_url=top.image_url,
                price=top.price,
                model=gpt_model,
                api_key=config.openai_api_key or None,
                dry_run=dry_run,
            )
        except TopviewGptError as exc:
            raise click.ClickException(str(exc))
    else:
        gemini_model = model or "gemini-2.0-flash"
        click.echo(f"✍️  Gemini({gemini_model})로 숏츠 패키지 생성 중...")
        try:
            result = generate_script(
                product_name=top.name,
                product_url=product_url,
                image_url=top.image_url,
                price=top.price,
                model=gemini_model,
                api_key=config.google_api_key or None,
                dry_run=dry_run,
            )
        except TopviewGptError as exc:
            raise click.ClickException(str(exc))

    # 4. 출력
    if json_out:
        click.echo(json.dumps(result.topview_payload, ensure_ascii=False, indent=2))
        return

    click.echo("\n" + "━" * 50)
    click.echo(f"🎬  {result.product_name}  쇼핑쇼츠 패키지")
    click.echo("━" * 50)

    click.echo("\n▶ 대본 (15초)")
    for scene_key in ("scene1", "scene2", "scene3"):
        sc = result.script.get(scene_key, {})
        time_ = sc.get("time", "")
        subtitle = sc.get("subtitle", "")
        action = sc.get("action", "")
        click.echo(f"  [{time_}]  자막: \"{subtitle}\"")
        if action:
            click.echo(f"            화면: {action}")

    click.echo("\n▶ 자막 목록")
    for i, sub in enumerate(result.subtitles, 1):
        click.echo(f"  {i}. {sub}")

    click.echo(f"\n▶ 배경음악\n  {result.bgm}")

    click.echo("\n▶ 해시태그")
    click.echo("  " + "  ".join(result.hashtags))

    click.echo(f"\n▶ TopView 입력 정보")
    click.echo(f"  이미지 URL : {result.image_url}")
    click.echo(f"  제품 URL   : {result.product_url}")
    click.echo("━" * 50)
    click.echo("💡 --json-out 옵션을 추가하면 JSON 형태로 출력됩니다.")


@google_shorts_group.command("search")
@click.option("--keyword", "-k", required=True, help="구글 쇼핑 검색어")
@click.option("--limit", default=5, show_default=True)
@click.option("--dry-run/--live", "dry_run", default=True)
def google_shorts_search(keyword, limit, dry_run):
    """구글 쇼핑 검색 결과만 확인합니다 (대본 생성 없음)."""
    config = load_config()
    hits = search_one_source("google", keyword, config, dry_run=dry_run, limit=limit)
    if not hits:
        click.echo("검색 결과 없음")
        return
    click.echo(f"── 구글 쇼핑: '{keyword}' ──")
    for i, h in enumerate(hits):
        price = f" / {h.price}원" if h.price else ""
        click.echo(f"  [{i}] {h.name}{price}")
        click.echo(f"      이미지: {h.image_url}")
        click.echo(f"      URL  : {h.product_url}")


if __name__ == "__main__":
    cli()
