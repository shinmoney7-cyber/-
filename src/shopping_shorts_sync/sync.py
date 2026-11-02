from __future__ import annotations

import logging

from .config import Config
from .coupang.client import CoupangPartnersClient
from .coupang.mock_client import MockCoupangClient
from .browser import launch_browser
from .inpock.mock_rpa import MockInpockRPAClient
from .inpock.rpa import InpockRPAClient, product_to_card
from .facebook.client import FacebookPageClient, MockFacebookPageClient
from .instagram.client import InstagramClient, next_scheduled_timestamp
from .instagram.dm_client import InstagramDMClient, MockInstagramDMClient
from .instagram.mock_client import MockInstagramClient
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
    """Returns (product, outcome, detail) tuples. outcome in {generated, skipped, error}."""
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
        except Exception as exc:  # noqa: BLE001 - one product's RPA failure must not abort the run
            logger.exception("inpock sync failed for product %s", product.id)
            state.record_inpock_error(product, str(exc))
            outcomes.append((product, "error", str(exc)))

    return outcomes


def build_instagram_caption(product: Product, deeplink: str, cta: str, disclaimer: str) -> str:
    tags = f"#{product.category.replace(' ', '')}" if product.category else ""
    parts = [product.name, "", cta]
    if tags:
        parts += ["", tags, "#쿠팡파트너스"]
    if disclaimer:
        parts += ["", disclaimer]
    return "\n".join(parts)


def build_instagram_client(config: Config, target_page: str):
    if config.instagram_api_mode == "live":
        user_id, access_token = config.instagram_credentials(target_page)
        return InstagramClient(user_id, access_token)
    return MockInstagramClient()


def build_dm_client(config: Config, target_page: str):
    if config.instagram_api_mode == "live":
        user_id, access_token = config.instagram_credentials(target_page)
        return InstagramDMClient(user_id, access_token)
    return MockInstagramDMClient()


def send_preview_dm(product: Product, caption: str, deeplink: str, config: Config) -> None:
    """DMs the account owner a preview of the scheduled post before it goes live."""
    owner_igsid = config.instagram_owner_igsid(product.target_page)
    if not owner_igsid:
        logger.warning("owner IGSID not configured for %s — skipping preview DM", product.target_page)
        return
    preview = (
        f"[미리보기 - {product.target_page}]\n"
        f"상품: {product.name}\n"
        f"링크: {deeplink}\n\n"
        f"--- 캡션 ---\n{caption}"
    )
    dm_client = build_dm_client(config, product.target_page)
    result = dm_client.send_text(owner_igsid, preview)
    if result.ok:
        logger.info("preview DM sent to owner (%s) for product %s", product.target_page, product.id)
    else:
        logger.warning("preview DM failed for %s: %s", product.id, result.error)


def run_instagram_stage(
    products: list[Product],
    config: Config,
    state: StateStore,
    force: bool = False,
    scheduled_publish_time: int | None = None,
    preview_dm: bool = True,
) -> list[tuple[Product, str, str | None]]:
    """Returns (product, outcome, detail) tuples. outcome in {posted, skipped, error}."""
    outcomes: list[tuple[Product, str, str | None]] = []

    for product in products:
        if not product.enabled:
            outcomes.append((product, "skipped", "disabled"))
            continue

        product_state = state.get(product.id)
        if product_state is None or not product_state.deeplink:
            outcomes.append((product, "skipped", "no deeplink yet"))
            continue

        if not product.thumbnail:
            outcomes.append((product, "skipped", "thumbnail required for Instagram post"))
            continue

        if not force and not state.needs_instagram_post(product):
            outcomes.append((product, "skipped", "already posted"))
            continue

        try:
            client = build_instagram_client(config, product.target_page)
            caption = build_instagram_caption(
                product,
                product_state.deeplink,
                config.instagram_default_cta,
                config.instagram_disclaimer,
            )
            if preview_dm:
                send_preview_dm(product, caption, product_state.deeplink, config)
            sched_ts = scheduled_publish_time or next_scheduled_timestamp(
                config.instagram_schedule_hour, config.instagram_schedule_minute
            )
            result = client.post_image(product.id, product.thumbnail, caption, sched_ts)
            if result.ok:
                state.record_instagram_post(product, result.media_id, result.scheduled_publish_time)
                detail = result.permalink or str(sched_ts)
                outcomes.append((product, "scheduled" if result.is_scheduled else "posted", detail))
            else:
                state.record_instagram_error(product, result.error or "unknown error")
                outcomes.append((product, "error", result.error))
        except Exception as exc:  # noqa: BLE001
            logger.exception("instagram post failed for product %s", product.id)
            state.record_instagram_error(product, str(exc))
            outcomes.append((product, "error", str(exc)))

    return outcomes


def resolve_thumbnails(
    products: list[Product],
    config: Config,
    products_path: str | None = None,
) -> list[Product]:
    """For every product whose thumbnail is empty, search Naver Shopping and
    use the first result's image URL. If products_path is given the resolved
    URL is also persisted back to the JSON file so the next run skips the lookup."""
    import dataclasses

    if not config.naver_client_id or not config.naver_client_secret:
        return products

    from .search.naver import NaverShopClient, NaverApiError
    from .input_loader import set_product_thumbnail

    try:
        naver = NaverShopClient(config.naver_client_id, config.naver_client_secret)
    except NaverApiError:
        return products

    resolved: list[Product] = []
    seen_names: dict[str, str] = {}  # name → image_url cache within this run

    for product in products:
        if product.thumbnail:
            resolved.append(product)
            continue

        try:
            if product.name in seen_names:
                image_url = seen_names[product.name]
            else:
                results = naver.search(product.name, limit=1)
                image_url = results[0].image_url if results else ""
                seen_names[product.name] = image_url

            if image_url:
                logger.info("auto-resolved thumbnail for %s: %s", product.id, image_url)
                product = dataclasses.replace(product, thumbnail=image_url)
                if products_path:
                    set_product_thumbnail(products_path, product.id, image_url)
        except Exception:
            logger.warning("thumbnail auto-resolve failed for %s", product.id)

        resolved.append(product)

    return resolved


def build_facebook_client(config: Config, target_page: str):
    if config.facebook_api_mode == "live":
        page_id, page_access_token = config.facebook_credentials(target_page)
        return FacebookPageClient(page_id, page_access_token)
    return MockFacebookPageClient()


def run_facebook_stage(
    products: list[Product],
    config: Config,
    state: StateStore,
    force: bool = False,
    scheduled_publish_time: int | None = None,
) -> list[tuple[Product, str, str | None]]:
    """Returns (product, outcome, detail) tuples. outcome in {scheduled, posted, skipped, error}."""
    outcomes: list[tuple[Product, str, str | None]] = []

    for product in products:
        if not product.enabled:
            outcomes.append((product, "skipped", "disabled"))
            continue

        product_state = state.get(product.id)
        if product_state is None or not product_state.deeplink:
            outcomes.append((product, "skipped", "no deeplink yet"))
            continue

        if not product.thumbnail:
            outcomes.append((product, "skipped", "thumbnail required for Facebook post"))
            continue

        if not force and not state.needs_facebook_post(product):
            outcomes.append((product, "skipped", "already posted"))
            continue

        try:
            client = build_facebook_client(config, product.target_page)
            caption = build_instagram_caption(
                product,
                product_state.deeplink,
                config.instagram_default_cta,
                config.instagram_disclaimer,
            )
            sched_ts = scheduled_publish_time or next_scheduled_timestamp(
                config.instagram_schedule_hour, config.instagram_schedule_minute
            )
            result = client.post_photo(product.id, product.thumbnail, caption, sched_ts)
            if result.ok:
                state.record_facebook_post(product, result.post_id, result.scheduled_publish_time)
                detail = str(sched_ts) if result.is_scheduled else result.post_id
                outcomes.append((product, "scheduled" if result.is_scheduled else "posted", detail))
            else:
                state.record_facebook_error(product, result.error or "unknown error")
                outcomes.append((product, "error", result.error))
        except Exception as exc:  # noqa: BLE001
            logger.exception("facebook post failed for product %s", product.id)
            state.record_facebook_error(product, str(exc))
            outcomes.append((product, "error", str(exc)))

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
        state.save()
        return deeplink_outcomes, inpock_outcomes

    with launch_browser(
        headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
    ) as browser:
        page = browser.new_page()
        rpa_client = InpockRPAClient(page, config.inpock_email, config.inpock_password)
        rpa_client.login()
        inpock_outcomes = run_inpock_stage(products, rpa_client, state, force_create=force_create)

    state.save()
    return deeplink_outcomes, inpock_outcomes
