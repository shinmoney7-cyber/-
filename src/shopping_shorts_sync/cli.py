from __future__ import annotations

import dataclasses
import logging

import click

from .config import load_config
from .input_loader import load_products
from .models import TARGET_PAGES
from .script_store import default_script_path, load_script_set
from .search.orchestrator import match_and_upsert_product, search_all_sources, search_one_source
from .state_store import StateStore
from .sync import (
    build_coupang_client,
    run_deeplink_stage,
    run_full_sync,
    run_inpock_stage,
    _run_inpock_live,
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
    """Coupang Partners deeplink 생성 → Inpock 링크카드 동기화."""


# ── deeplink ─────────────────────────────────────────────────────────────────

@cli.group()
def deeplink():
    """Coupang Partners deeplink 작업."""


@deeplink.command("generate")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--live/--dry-run", "live", default=False,
              help="실제 Coupang API 호출. 기본은 mock.")
@click.option("--force", is_flag=True, help="이미 생성된 딥링크도 재생성.")
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


# ── inpock ───────────────────────────────────────────────────────────────────

@cli.group()
def inpock():
    """Inpock 링크카드 동기화."""


@inpock.command("sync")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option(
    "--page", "page_filter",
    type=click.Choice(list(TARGET_PAGES)),
    default=None,
    help="특정 페이지만 동기화. 생략 시 전체(harujin + shinjh).",
)
@click.option("--dry-run/--live", "dry_run", default=True,
              help="--live 시 실제 브라우저로 Inpock 자동화.")
@click.option("--headed/--headless", "headed", default=False,
              help="--headed 로 브라우저 창 띄워서 진행 상황 확인.")
@click.option("--force-create", is_flag=True, help="기존 카드 탐색 없이 항상 새로 생성.")
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
        outcomes = _run_inpock_live(products, config, state, force_create=force_create)

    state.save()
    _print_outcomes("inpock sync", outcomes)


# ── sync all (full pipeline) ──────────────────────────────────────────────────

@cli.group("sync")
def sync_group():
    """딥링크 생성 + Inpock 동기화 풀 파이프라인."""


@sync_group.command("all")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--dry-run/--live", "dry_run", default=True)
@click.option("--headed/--headless", "headed", default=False)
@click.option("--force", is_flag=True, help="딥링크도 강제 재생성.")
@click.option("--force-create", is_flag=True, help="Inpock 카드 기존 탐색 생략, 항상 새로 생성.")
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


# ── search ────────────────────────────────────────────────────────────────────

@cli.group()
def search():
    """Naver/Daiso/Olive Young 검색 후 Coupang 매칭."""


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
@click.option("--keyword", required=True)
@click.option("--source", required=True, type=click.Choice(["naver", "daiso", "oliveyoung"]))
@click.option("--index", required=True, type=int)
@click.option("--target-page", required=True, type=click.Choice(list(TARGET_PAGES)))
@click.option("--category", required=True)
@click.option("--input", "input_path", required=True, type=click.Path())
@click.option("--dry-run/--live", "dry_run", default=True)
@click.option("--headed/--headless", "headed", default=False)
def search_match(keyword, source, index, target_page, category, input_path, dry_run, headed):
    config = load_config()
    _setup_logging(config)
    config = dataclasses.replace(config, inpock_headless=not headed)

    results = search_one_source(source, keyword, config, dry_run=dry_run)
    if index >= len(results):
        raise click.ClickException(f"index {index} 범위 초과, {source} 결과: {len(results)}개")
    selected = results[index]

    product = match_and_upsert_product(
        selected, target_page, category, config, input_path, dry_run=dry_run
    )
    if product is None:
        click.echo(f"{selected.name!r}에 대한 Coupang 매칭 결과 없음")
        return

    click.echo(f"매칭: {selected.name!r} → {product.coupang_url}")
    click.echo(f"{input_path} 에 product {product.id} 추가/갱신 완료")


# ── script ────────────────────────────────────────────────────────────────────

@cli.group()
def script():
    """AIDA 스크립트 후보 조회/선택."""


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
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--file", "script_file", type=click.Path(exists=True), default=None)
def script_select(product_id, candidate_id, input_path, script_file):
    from .script_store import save_script_set

    path = script_file or default_script_path(product_id)
    script_set = load_script_set(path)
    candidate = script_set.select(candidate_id)
    save_script_set(path, script_set)

    config = load_config()
    products = {p.id: p for p in load_products(input_path)}
    product = products.get(product_id)
    if product is None:
        raise click.ClickException(f"product {product_id!r} 을 {input_path} 에서 찾을 수 없음")

    state = StateStore(config.state_file_path)
    state.apply_script(product, candidate.id, candidate.full_text)
    state.save()
    click.echo(f"{product_id} 에 candidate {candidate.id} 적용 완료")


# ── state ─────────────────────────────────────────────────────────────────────

@cli.group()
def state():
    """로컬 동기화 상태 파일 조회/초기화."""


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
