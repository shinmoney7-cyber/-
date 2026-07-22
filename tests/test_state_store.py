from shopping_shorts_sync.models import Product
from shopping_shorts_sync.state_store import StateStore

PRODUCT = Product(
    id="p1",
    name="Test Product",
    coupang_url="https://www.coupang.com/vp/products/1",
    thumbnail="https://example.com/x.jpg",
    category="test",
    target_page="harujin",
)


def test_needs_deeplink_initially_true(tmp_path):
    store = StateStore(tmp_path / "state.json")
    assert store.needs_deeplink(PRODUCT) is True


def test_record_deeplink_then_no_longer_needed(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.record_deeplink(PRODUCT, "https://link.coupang.com/a/x")
    assert store.needs_deeplink(PRODUCT) is False


def test_needs_deeplink_true_again_if_url_changes(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.record_deeplink(PRODUCT, "https://link.coupang.com/a/x")
    changed = Product(**{**PRODUCT.__dict__, "coupang_url": "https://www.coupang.com/vp/products/2"})
    assert store.needs_deeplink(changed) is True


def test_needs_inpock_sync_false_before_deeplink(tmp_path):
    store = StateStore(tmp_path / "state.json")
    assert store.needs_inpock_sync(PRODUCT) is False


def test_needs_inpock_sync_true_after_deeplink_then_false_after_sync(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.record_deeplink(PRODUCT, "https://link.coupang.com/a/x")
    assert store.needs_inpock_sync(PRODUCT) is True

    store.record_inpock_sync(PRODUCT)
    assert store.needs_inpock_sync(PRODUCT) is False


def test_needs_inpock_sync_true_again_if_content_changes(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.record_deeplink(PRODUCT, "https://link.coupang.com/a/x")
    store.record_inpock_sync(PRODUCT)

    changed = Product(**{**PRODUCT.__dict__, "name": "New Name"})
    assert store.needs_inpock_sync(changed) is True


def test_save_and_reload_round_trip(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.record_deeplink(PRODUCT, "https://link.coupang.com/a/x")
    store.record_inpock_sync(PRODUCT)
    store.save()

    reloaded = StateStore(path)
    assert reloaded.get("p1").deeplink == "https://link.coupang.com/a/x"
    assert reloaded.get("p1").status == "synced"


def test_reset_removes_entry(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.record_deeplink(PRODUCT, "https://link.coupang.com/a/x")
    assert store.reset("p1") is True
    assert store.get("p1") is None
    assert store.reset("p1") is False
