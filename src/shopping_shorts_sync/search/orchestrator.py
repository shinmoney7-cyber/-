from __future__ import annotations

from ..browser import launch_browser
from ..config import Config
from ..input_loader import upsert_product
from ..models import Product, derive_product_id
from .coupang_match import CoupangMatchRPAClient, MockCoupangMatchClient
from .daiso import DaisoRPAClient
from .mock import MockSearchClient
from .models import SearchResult
from .naver import NaverShopClient
from .oliveyoung import OliveYoungRPAClient


def search_all_sources(
    keyword: str, config: Config, dry_run: bool = True, limit: int = 5
) -> dict[str, list[SearchResult]]:
    """Searches Naver Shopping, Daiso Mall, and Olive Young for `keyword`,
    `limit` results each. dry_run uses deterministic mock clients for all
    three (no network, no browser)."""
    if dry_run:
        return {
            source: MockSearchClient(source).search(keyword, limit=limit)
            for source in ("naver", "daiso", "oliveyoung")
        }

    naver_client = NaverShopClient(config.naver_client_id, config.naver_client_secret)
    results = {"naver": naver_client.search(keyword, limit=limit)}

    with launch_browser(
        headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
    ) as browser:
        page = browser.new_page()
        results["daiso"] = DaisoRPAClient(page).search(keyword, limit=limit)
        results["oliveyoung"] = OliveYoungRPAClient(page).search(keyword, limit=limit)

    return results


def search_one_source(
    source: str, keyword: str, config: Config, dry_run: bool = True, limit: int = 5
) -> list[SearchResult]:
    if source not in ("naver", "daiso", "oliveyoung"):
        raise ValueError(f"unknown search source: {source!r}")

    if dry_run:
        return MockSearchClient(source).search(keyword, limit=limit)

    if source == "naver":
        return NaverShopClient(config.naver_client_id, config.naver_client_secret).search(
            keyword, limit=limit
        )

    rpa_client_cls = DaisoRPAClient if source == "daiso" else OliveYoungRPAClient
    with launch_browser(
        headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
    ) as browser:
        page = browser.new_page()
        return rpa_client_cls(page).search(keyword, limit=limit)


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
