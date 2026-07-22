import json
import dataclasses

from shopping_shorts_sync.config import load_config
from shopping_shorts_sync.input_loader import load_products
from shopping_shorts_sync.search.orchestrator import (
    match_and_upsert_product,
    search_all_sources,
    search_one_source,
)


def _config():
    return load_config(env_file="/nonexistent/.env")


def test_search_all_sources_dry_run_returns_all_four():
    results = search_all_sources("무선 청소기", _config(), dry_run=True, limit=3)
    assert set(results.keys()) == {"naver", "daiso", "oliveyoung", "youtube"}
    assert all(len(v) == 3 for v in results.values())


def test_search_one_source_dry_run():
    results = search_one_source("daiso", "청소기", _config(), dry_run=True, limit=2)
    assert len(results) == 2
    assert all(r.source == "daiso" for r in results)


def test_match_and_upsert_product_dry_run(tmp_path):
    products_path = tmp_path / "products.json"
    products_path.write_text("[]", encoding="utf-8")

    results = search_one_source("daiso", "청소기", _config(), dry_run=True, limit=1)
    result = results[0]

    product = match_and_upsert_product(
        result,
        target_page="harujin",
        category="생활용품",
        config=_config(),
        products_path=str(products_path),
        dry_run=True,
    )

    assert product is not None
    assert product.name == result.name
    assert product.thumbnail == result.image_url
    assert product.target_page == "harujin"

    reloaded = load_products(products_path)
    assert len(reloaded) == 1
    assert reloaded[0].id == product.id


def test_match_and_upsert_product_upserts_not_duplicates(tmp_path):
    products_path = tmp_path / "products.json"
    products_path.write_text("[]", encoding="utf-8")

    config = _config()
    result = search_one_source("daiso", "청소기", config, dry_run=True, limit=1)[0]

    first = match_and_upsert_product(result, "harujin", "생활용품", config, str(products_path), dry_run=True)
    second = match_and_upsert_product(result, "harujin", "생활용품", config, str(products_path), dry_run=True)

    assert first.id == second.id
    reloaded = load_products(products_path)
    assert len(reloaded) == 1
