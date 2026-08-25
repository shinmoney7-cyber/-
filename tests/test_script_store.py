import pytest

from shopping_shorts_sync.script_store import (
    ScriptSet,
    ScriptValidationError,
    load_script_set,
    save_script_set,
)


def _candidate(i):
    return {
        "id": i,
        "attention": f"attention {i}",
        "interest": f"interest {i}",
        "desire": f"desire {i}",
        "action": f"action {i}",
    }


def test_load_example_fixture():
    script_set = load_script_set("data/scripts/harujin-vacuum-01.json")
    assert len(script_set.candidates) == 5
    assert script_set.selected_id == 3  # candidate 3 이미 선택됨


def test_exactly_five_candidates_required():
    with pytest.raises(ScriptValidationError):
        ScriptSet(product_id="x", candidates=[])


def test_duplicate_candidate_ids_rejected():
    candidates = [_candidate(1) for _ in range(5)]
    from shopping_shorts_sync.script_store import ScriptCandidate

    with pytest.raises(ScriptValidationError):
        ScriptSet(
            product_id="x",
            candidates=[ScriptCandidate.from_dict(c) for c in candidates],
        )


def test_select_marks_selected_id():
    from shopping_shorts_sync.script_store import ScriptCandidate

    candidates = [ScriptCandidate.from_dict(_candidate(i)) for i in range(1, 6)]
    script_set = ScriptSet(product_id="x", candidates=candidates)

    selected = script_set.select(3)
    assert selected.id == 3
    assert script_set.selected_id == 3


def test_select_invalid_id_raises():
    from shopping_shorts_sync.script_store import ScriptCandidate

    candidates = [ScriptCandidate.from_dict(_candidate(i)) for i in range(1, 6)]
    script_set = ScriptSet(product_id="x", candidates=candidates)

    with pytest.raises(ScriptValidationError):
        script_set.select(99)


def test_save_and_reload_round_trip(tmp_path):
    from shopping_shorts_sync.script_store import ScriptCandidate

    candidates = [ScriptCandidate.from_dict(_candidate(i)) for i in range(1, 6)]
    script_set = ScriptSet(product_id="x", candidates=candidates)
    script_set.select(2)

    path = tmp_path / "x.json"
    save_script_set(path, script_set)

    reloaded = load_script_set(path)
    assert reloaded.selected_id == 2
    assert reloaded.get_candidate(2).attention == "attention 2"


def test_full_text_joins_all_stages():
    from shopping_shorts_sync.script_store import ScriptCandidate

    candidate = ScriptCandidate.from_dict(_candidate(1))
    assert candidate.full_text == "attention 1\ninterest 1\ndesire 1\naction 1"
