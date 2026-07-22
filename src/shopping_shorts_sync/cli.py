from __future__ import annotations

import dataclasses
import logging

import click

from .config import load_config
from .input_loader import load_products
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
        from .inpock.browser import launch_browser
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
