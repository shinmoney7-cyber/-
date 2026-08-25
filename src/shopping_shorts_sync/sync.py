from __future__ import annotations

import logging
from itertools import groupby

from .config import Config
from .coupang.client import CoupangPartnersClient
from .coupang.mock_client import MockCoupangClient
from .browser import launch_browser
from .inpock.mock_rpa import MockInpockRPAClient
from .inpock.rpa import InpockRPAClient, product_to_card
from .models import Product
from .state_store import StateStore

logger = logging.getLogger(__name__)


def build_coupang_client(config: Config):
    if config.coupang_api_mode == "live":
        return CoupangPartnersClient(
            config.coupang_access_key,
            config.coupang_secret_key,
            batch_size=config.coupang_batch_size,
        )
    return MockCoupangClient()


def run_deeplink_stage(
    products: list[Product], client, state: StateStore, force: bool = False
) -> list[tuple[Product, str, str | None]]:
    """(product, outcome, detail) 리스트 반환. outcome: generated | skipped | error"""
    to_process = [p for p in products if p.enabled and (force or state.needs_deeplink(p))]
    outcomes: list[tuple[Product, str, str | None]] = []

    skipped_ids = {p.id for p in products} - {p.id for p in to_process}
    for p in products:
        if p.id in skipped_ids:
            outcomes.append((p, "skipped", None))

    if not to_process:
        return outcomes

    results = client.get_deeplinks([p.coupang_url for p in to_process])
    result_by_url = {r.original_url: r for r in results}

    for p in to_process:
        result = result_by_url.get(p.coupang_url)
        if result is None or not result.ok:
            error = result.error if result else "no result returned for this coupang_url"
            state.record_deeplink_error(p, error)
            outcomes.append((p, "error", error))
        else:
            state.record_deeplink(p, result.shorten_url)
            outcomes.append((p, "generated", result.shorten_url))

    return outcomes


def run_inpock_stage(
    products: list[Product], rpa_client, state: StateStore, force_create: bool = False
) -> list[tuple[Product, str, str | None]]:
    """Returns (product, outcome, detail) tuples. outcome in {created, updated, skipped, error}."""
    # Assign sequential 1-based numbers per target_page for enabled products.
    page_counters: dict[str, int] = {}
    page_numbers: dict[str, int] = {}
    for product in products:
        if product.enabled:
            page_counters[product.target_page] = page_counters.get(product.target_page, 0) + 1
            page_numbers[product.id] = page_counters[product.target_page]

    outcomes: list[tuple[Product, str, str | None]] = []

    for product in products:
        if not product.enabled:
            outcomes.append((product, "skipped", "disabled"))
            continue

        product_state = state.get(product.id)
        if product_state is None or not product_state.deeplink:
            outcomes.append((product, "skipped", "no deeplink yet"))
            continue

        number = page_numbers.get(product.id)
        if not state.needs_inpock_sync(product, number=number):
            outcomes.append((product, "skipped", "already in sync"))
            continue

        try:
            card = product_to_card(product, product_state.deeplink, number=number)
            action = rpa_client.sync_card(product.target_page, card, force_create=force_create)
            state.record_inpock_sync(product, number=number)
            outcomes.append((product, action, None))
        except Exception as exc:
            logger.exception("inpock sync failed for product %s", product.id)
            state.record_inpock_error(product, str(exc))
            outcomes.append((product, "error", str(exc)))

    return outcomes


def _run_inpock_live(
    products: list[Product],
    config: Config,
    state: StateStore,
    force_create: bool = False,
) -> list[tuple[Product, str, str | None]]:
    """2계정 지원: target_page 별로 묶어 각 계정으로 로그인 후 동기화."""
    outcomes: list[tuple[Product, str, str | None]] = []

    # target_page 기준으로 그룹화 (순서 유지)
    by_page: dict[str, list[Product]] = {}
    for p in products:
        by_page.setdefault(p.target_page, []).append(p)

    def _chromium_path() -> str | None:
        return config.playwright_chromium_path or None

    with launch_browser(headless=config.inpock_headless, chromium_path=_chromium_path()) as browser:
        page = browser.new_page()
        current_email: str | None = None
        rpa_client: InpockRPAClient | None = None

        for page_slug, page_products in by_page.items():
            email, password = config.inpock_credentials_for(page_slug)

            if email != current_email:
                # 계정 전환 필요
                if current_email is not None and rpa_client is not None:
                    logger.info("계정 전환: %s → %s", current_email, email)
                    rpa_client.logout()

                rpa_client = InpockRPAClient(page, email, password)
                rpa_client.login()
                current_email = email
            else:
                # 같은 계정 — rpa_client 재사용, 로그인 불필요
                assert rpa_client is not None

            page_outcomes = run_inpock_stage(
                page_products, rpa_client, state, force_create=force_create
            )
            outcomes.extend(page_outcomes)

    return outcomes


def run_full_sync(
    products: list[Product],
    config: Config,
    dry_run: bool = True,
    force: bool = False,
    force_create: bool = False,
):
    state = StateStore(config.state_file_path)
    coupang_client = build_coupang_client(config)

    deeplink_outcomes = run_deeplink_stage(products, coupang_client, state, force=force)
    state.save()

    if dry_run:
        rpa_client = MockInpockRPAClient()
        inpock_outcomes = run_inpock_stage(products, rpa_client, state, force_create=force_create)
    else:
        inpock_outcomes = _run_inpock_live(products, config, state, force_create=force_create)

    state.save()
    return deeplink_outcomes, inpock_outcomes
