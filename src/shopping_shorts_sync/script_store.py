from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_CANDIDATE_COUNT = 5


class ScriptValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ScriptCandidate:
    """One AIDA-structured script candidate.

    Stage names follow the user's notes: attention (hook, ~3s), interest
    (~3-10s, what makes this different), desire (~10-20s, usage/result
    scene), action (~20-25s, CTA). full_text is the stages joined for
    convenience (e.g. for pasting into a video-generation tool later).
    """

    id: int
    attention: str
    interest: str
    desire: str
    action: str
    # Which of the 7 persuasion elements the desire stage uses (empty for
    # hand-authored candidates predating this field, e.g. the two example
    # fixtures). One of: desire, loss_aversion, social_proof, authority,
    # curiosity_gap, quantified_benefit, family_narrative.
    technique: str = ""

    @property
    def full_text(self) -> str:
        return "\n".join([self.attention, self.interest, self.desire, self.action])

    @staticmethod
    def from_dict(raw: dict) -> "ScriptCandidate":
        missing = [f for f in ("id", "attention", "interest", "desire", "action") if f not in raw]
        if missing:
            raise ScriptValidationError(f"script candidate missing field(s): {missing}")
        return ScriptCandidate(
            id=int(raw["id"]),
            attention=raw["attention"],
            interest=raw["interest"],
            desire=raw["desire"],
            action=raw["action"],
            technique=raw.get("technique", ""),
        )


@dataclass
class ScriptSet:
    product_id: str
    candidates: list[ScriptCandidate]
    selected_id: int | None = None

    def __post_init__(self):
        if len(self.candidates) != REQUIRED_CANDIDATE_COUNT:
            raise ScriptValidationError(
                f"product {self.product_id!r} must have exactly "
                f"{REQUIRED_CANDIDATE_COUNT} script candidates, got {len(self.candidates)}"
            )
        ids = [c.id for c in self.candidates]
        if len(set(ids)) != len(ids):
            raise ScriptValidationError(f"duplicate candidate ids in product {self.product_id!r}: {ids}")
        if self.selected_id is not None and self.selected_id not in ids:
            raise ScriptValidationError(
                f"selected_id {self.selected_id} is not among candidate ids {ids}"
            )

    def get_candidate(self, candidate_id: int) -> ScriptCandidate:
        for c in self.candidates:
            if c.id == candidate_id:
                return c
        raise ScriptValidationError(f"no candidate with id {candidate_id} in product {self.product_id!r}")

    def select(self, candidate_id: int) -> ScriptCandidate:
        candidate = self.get_candidate(candidate_id)  # raises if not found
        self.selected_id = candidate_id
        return candidate


def default_script_path(product_id: str, base_dir: str | Path = "data/scripts") -> Path:
    return Path(base_dir) / f"{product_id}.json"


def load_script_set(path: str | Path) -> ScriptSet:
    path = Path(path)
    if not path.exists():
        raise ScriptValidationError(f"script file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    candidates = [ScriptCandidate.from_dict(c) for c in raw.get("candidates", [])]
    return ScriptSet(
        product_id=raw["product_id"],
        candidates=candidates,
        selected_id=raw.get("selected_id"),
    )


def save_script_set(path: str | Path, script_set: ScriptSet) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "product_id": script_set.product_id,
        "candidates": [asdict(c) for c in script_set.candidates],
        "selected_id": script_set.selected_id,
    }

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".script-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
