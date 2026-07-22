import pytest

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


def test_apply_script_records_selection(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.apply_script(PRODUCT, candidate_id=3, script_text="hook\ninterest\ndesire\naction")

    state = store.get("p1")
    assert state.selected_script_id == 3
    assert state.script_text == "hook\ninterest\ndesire\naction"
    assert state.script_applied_at is not None


def test_apply_script_survives_save_reload(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.apply_script(PRODUCT, candidate_id=2, script_text="x")
    store.save()

    reloaded = StateStore(path)
    assert reloaded.get("p1").selected_script_id == 2


def test_record_voice_requires_existing_entry(tmp_path):
    store = StateStore(tmp_path / "state.json")
    with pytest.raises(KeyError):
        store.record_voice("p1", "https://example.com/a.mp3", "예슬")


def test_record_voice_after_script_selected(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.apply_script(PRODUCT, candidate_id=1, script_text="x")
    store.record_voice("p1", "https://example.com/a.mp3", "예슬")

    state = store.get("p1")
    assert state.voice_audio_url == "https://example.com/a.mp3"
    assert state.voice_actor_id == "예슬"
    assert state.voice_generated_at is not None


def test_approve_requires_a_selected_script_first(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.record_deeplink(PRODUCT, "https://link.coupang.com/a/x")
    try:
        store.approve(PRODUCT)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_approve_after_script_selected(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.apply_script(PRODUCT, candidate_id=1, script_text="x")
    store.approve(PRODUCT)
    assert store.get("p1").approved_at is not None


def test_unapprove_clears_approval(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.apply_script(PRODUCT, candidate_id=1, script_text="x")
    store.approve(PRODUCT)
    store.unapprove("p1")
    assert store.get("p1").approved_at is None
