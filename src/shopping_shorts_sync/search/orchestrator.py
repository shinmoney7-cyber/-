from __future__ import annotations

import logging

from ..browser import launch_browser
from ..config import Config
from ..input_loader import upsert_product
from ..models import Product, derive_product_id
from .coupang_match import CoupangMatchRPAClient, MockCoupangMatchClient
from .mock import MockSearchClient
from .models import SOURCES, SearchResult
from .naver import NaverShopClient
from .sites import build_rpa_client


logger = logging.getLogger(__name__)


def _validate_sources(sources) -> tuple[str, ...]:
    unknown = [s for s in sources if s not in SOURCES]
    if unknown:
        raise ValueError(f"unknown search source(s): {unknown!r}")
    return tuple(sources)


def search_all_sources(
    keyword: str,
    config: Config,
    dry_run: bool = True,
    limit: int = 5,
    sources: tuple[str, ...] | list[str] | None = None,
) -> dict[str, list[SearchResult]]:
    """Searches every mall in `sources` (default: all of SOURCES) for `keyword`,
    `limit` results each.

    dry_run uses deterministic mock clients (no network, no browser). In live
    mode a failure in one mall is logged and that mall returns no results, so
    the other malls still complete.
    """
    selected = _validate_sources(sources or SOURCES)

    if dry_run:
        return {s: MockSearchClient(s).search(keyword, limit=limit) for s in selected}

    results: dict[str, list[SearchResult]] = {}
    if "naver" in selected:
        try:
            naver_client = NaverShopClient(config.naver_client_id, config.naver_client_secret)
            results["naver"] = naver_client.search(keyword, limit=limit)
        except Exception:
            logger.exception("naver search failed")
            results["naver"] = []

    rpa_sources = [s for s in selected if s != "naver"]
    if rpa_sources:
        with launch_browser(
            headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
        ) as browser:
            page = browser.new_page()
            for source in rpa_sources:
                try:
                    results[source] = build_rpa_client(source, page).search(keyword, limit=limit)
                except Exception:
                    logger.exception("%s search failed", source)
                    results[source] = []

    return {s: results[s] for s in selected}


def search_one_source(
    source: str, keyword: str, config: Config, dry_run: bool = True, limit: int = 5
) -> list[SearchResult]:
    _validate_sources([source])

    if dry_run:
        return MockSearchClient(source).search(keyword, limit=limit)

    if source == "naver":
        return NaverShopClient(config.naver_client_id, config.naver_client_secret).search(
            keyword, limit=limit
        )

    with launch_browser(
        headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
    ) as browser:
        page = browser.new_page()
        return build_rpa_client(source, page).search(keyword, limit=limit)


def match_to_coupang(product_name: str, config: Config, dry_run: bool = True) -> str | None:
    """Best-effort top-1 match on coupang.com for `product_name`. Per the
    owner's explicit choice, this is applied automatically without a human
    confirmation step, accepting that a name-similarity match can
    occasionally point at the wrong product."""
    if dry_run:
        return MockCoupangMatchClient().find_top_match(product_name)

    with launch_browser(
        headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
    ) as browser:
        page = browser.new_page()
        return CoupangMatchRPAClient(page).find_top_match(product_name)


def match_and_upsert_product(
    result: SearchResult,
    target_page: str,
    category: str,
    config: Config,
    products_path: str,
    dry_run: bool = True,
) -> Product | None:
    """The "클릭 즉시 자동 연동" step: matches `result` to a Coupang product
    and upserts a new/updated Product row into `products_path`. Returns
    None (and upserts nothing) if no Coupang match was found."""
    coupang_url = match_to_coupang(result.name, config, dry_run=dry_run)
    if coupang_url is None:
        return None

    product = Product(
        id=derive_product_id(coupang_url),
        name=result.name,
        coupang_url=coupang_url,
        thumbnail=result.image_url,
        category=category,
        target_page=target_page,
        enabled=True,
    )
    upsert_product(products_path, product)
    return product
