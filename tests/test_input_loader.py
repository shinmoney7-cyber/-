import pytest

from shopping_shorts_sync.input_loader import InputLoadError, load_products, upsert_product
from shopping_shorts_sync.models import Product


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


def _product(id_="p1", name="Test"):
    return Product(
        id=id_,
        name=name,
        coupang_url="https://www.coupang.com/vp/products/1",
        thumbnail="https://example.com/x.jpg",
        category="test",
        target_page="harujin",
    )


def test_upsert_product_creates_new_file(tmp_path):
    path = tmp_path / "products.json"
    upsert_product(path, _product())

    products = load_products(path)
    assert len(products) == 1
    assert products[0].id == "p1"


def test_upsert_product_appends_to_existing(tmp_path):
    path = tmp_path / "products.json"
    upsert_product(path, _product(id_="p1"))
    upsert_product(path, _product(id_="p2"))

    products = load_products(path)
    assert {p.id for p in products} == {"p1", "p2"}


def test_upsert_product_replaces_matching_id(tmp_path):
    path = tmp_path / "products.json"
    upsert_product(path, _product(id_="p1", name="Old Name"))
    upsert_product(path, _product(id_="p1", name="New Name"))

    products = load_products(path)
    assert len(products) == 1
    assert products[0].name == "New Name"


def test_upsert_product_rejects_csv():
    with pytest.raises(InputLoadError):
        upsert_product("data/products.example.csv", _product())
