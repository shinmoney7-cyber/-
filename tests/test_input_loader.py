import pytest

from shopping_shorts_sync.input_loader import InputLoadError, load_products


def test_load_example_json():
    products = load_products("data/products.example.json")
    assert len(products) == 2
    assert {p.target_page for p in products} == {"harujin", "shinjh"}


def test_load_example_csv():
    products = load_products("data/products.example.csv")
    assert len(products) == 2
    assert products[0].id == "harujin-vacuum-01"


def test_invalid_target_page_rejected(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(
        '[{"name": "x", "coupang_url": "https://www.coupang.com/vp/products/1", '
        '"target_page": "not-a-real-page"}]',
        encoding="utf-8",
    )
    with pytest.raises(InputLoadError):
        load_products(bad_file)


def test_duplicate_ids_rejected(tmp_path):
    bad_file = tmp_path / "dup.json"
    bad_file.write_text(
        '[{"id": "a", "name": "x", "coupang_url": "https://www.coupang.com/vp/products/1", '
        '"target_page": "harujin"}, '
        '{"id": "a", "name": "y", "coupang_url": "https://www.coupang.com/vp/products/2", '
        '"target_page": "shinjh"}]',
        encoding="utf-8",
    )
    with pytest.raises(InputLoadError):
        load_products(bad_file)


def test_missing_file_raises():
    with pytest.raises(InputLoadError):
        load_products("data/does_not_exist.json")


def test_id_auto_derived_when_omitted(tmp_path):
    f = tmp_path / "noid.json"
    f.write_text(
        '[{"name": "x", "coupang_url": "https://www.coupang.com/vp/products/1?itemId=1", '
        '"target_page": "harujin"}]',
        encoding="utf-8",
    )
    products = load_products(f)
    assert products[0].id  # non-empty, deterministically derived
