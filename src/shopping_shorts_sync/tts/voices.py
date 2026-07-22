"""The 20-voice catalog from the owner's notes: standard + 4 satoori
dialects (경상도/전라도/충청도/강원도), each in 2 genders x 2 age bands.

Only "예슬" (표준_여성_20-30대) is a real, confirmed Typecast actor name —
it's the voice named explicitly in the owner's notes and used as the
config default. The other 19 actor_ids are placeholders and must be
calibrated against the real Typecast actor list before --live use (same
convention as the RPA selectors in docs/CALIBRATION.md).
"""
from __future__ import annotations

from dataclasses import dataclass

REGIONS = ["표준", "경상도", "전라도", "충청도", "강원도"]
GENDERS = ["여성", "남성"]
AGE_BANDS = ["20-30대", "40-60대"]


@dataclass(frozen=True)
class Voice:
    label: str
    actor_id: str
    region: str
    gender: str
    age_band: str
    calibrated: bool


def _build_catalog() -> list[Voice]:
    catalog = []
    for region in REGIONS:
        for gender in GENDERS:
            for age_band in AGE_BANDS:
                label = f"{region}_{gender}_{age_band}"
                if region == "표준" and gender == "여성" and age_band == "20-30대":
                    catalog.append(Voice(label, "예슬", region, gender, age_band, calibrated=True))
                else:
                    slug = label.replace("-", "").replace("대", "")
                    catalog.append(Voice(label, f"TODO_CALIBRATE_{slug}", region, gender, age_band, calibrated=False))
    return catalog


VOICE_CATALOG: list[Voice] = _build_catalog()
assert len(VOICE_CATALOG) == 20

_BY_LABEL = {v.label: v for v in VOICE_CATALOG}


def get_voice(label: str) -> Voice:
    if label not in _BY_LABEL:
        raise KeyError(f"unknown voice label: {label!r}")
    return _BY_LABEL[label]
