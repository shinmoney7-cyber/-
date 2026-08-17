import dataclasses

from shopping_shorts_sync.config import load_config
from shopping_shorts_sync.input_loader import load_products
from shopping_shorts_sync.sync import run_full_sync


def _dry_run_config(tmp_path):
    config = load_config(env_file="/nonexistent/.env")
    return dataclasses.replace(
        config,
        coupang_api_mode="mock",
        state_file_path=str(tmp_path / "state.json"),
    )


def test_full_sync_first_run_generates_and_syncs_everything(tmp_path):
    products = load_products("data/products.example.json")
    config = _dry_run_config(tmp_path)

    deeplink_outcomes, inpock_outcomes = run_full_sync(products, config, dry_run=True)

    assert {o[1] for o in deeplink_outcomes} == {"generated"}
    assert {o[1] for o in inpock_outcomes} == {"created"}


def test_full_sync_second_run_is_a_no_op(tmp_path):
    products = load_products("data/products.example.json")
    config = _dry_run_config(tmp_path)

    run_full_sync(products, config, dry_run=True)
    deeplink_outcomes, inpock_outcomes = run_full_sync(products, config, dry_run=True)

    assert {o[1] for o in deeplink_outcomes} == {"skipped"}
    assert {o[1] for o in inpock_outcomes} == {"skipped"}


def test_full_sync_disabled_product_is_skipped(tmp_path):
    products = load_products("data/products.example.json")
    products = [dataclasses.replace(p, enabled=False) for p in products]
    config = _dry_run_config(tmp_path)

    deeplink_outcomes, inpock_outcomes = run_full_sync(products, config, dry_run=True)

    assert {o[1] for o in deeplink_outcomes} == {"skipped"}
    assert {o[1] for o in inpock_outcomes} == {"skipped"}


def test_full_sync_force_regenerates_deeplinks(tmp_path):
    products = load_products("data/products.example.json")
    config = _dry_run_config(tmp_path)

    run_full_sync(products, config, dry_run=True)
    deeplink_outcomes, _ = run_full_sync(products, config, dry_run=True, force=True)

    assert {o[1] for o in deeplink_outcomes} == {"generated"}
