from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class DetailPageSpecError(ValueError):
    pass


@dataclass(frozen=True)
class Feature:
    title: str
    body: str
    image: str | None = None  # path relative to the spec file


@dataclass(frozen=True)
class Colorway:
    name: str
    images: list[str]  # paths relative to the spec file, in display order


@dataclass(frozen=True)
class SizeTable:
    headers: list[str]
    rows: list[list[str]]


@dataclass(frozen=True)
class DetailPageSpec:
    product_id: str
    name: str
    headline: str
    colorways: list[Colorway]
    features: list[Feature] = field(default_factory=list)
    price: int | None = None
    brand: str | None = None
    material: str | None = None
    size_table: SizeTable | None = None
    notices: list[str] = field(default_factory=list)
    cta_text: str = "지금 구매하기"
    cta_url: str | None = None
    base_dir: Path = Path(".")

    def all_image_paths(self) -> list[Path]:
        """Every image the page needs, as absolute paths (for existence checks and copying)."""
        paths = [self.base_dir / img for c in self.colorways for img in c.images]
        paths += [self.base_dir / f.image for f in self.features if f.image]
        return paths


def _require_str(raw: dict, key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DetailPageSpecError(f"{where}: '{key}' must be a non-empty string")
    return value.strip()


def _optional_str(raw: dict, key: str) -> str | None:
    value = raw.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise DetailPageSpecError(f"'{key}' must be a string")
    return value.strip()


def _parse_size_table(raw) -> SizeTable | None:
    if raw is None:
        return None
    headers = raw.get("headers")
    rows = raw.get("rows")
    if not isinstance(headers, list) or not headers or not all(isinstance(h, str) for h in headers):
        raise DetailPageSpecError("size_table.headers must be a non-empty list of strings")
    if not isinstance(rows, list) or not rows:
        raise DetailPageSpecError("size_table.rows must be a non-empty list")
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(headers):
            raise DetailPageSpecError(
                f"size_table.rows[{i}] must have exactly {len(headers)} cells (one per header)"
            )
    return SizeTable(headers=list(headers), rows=[[str(c) for c in row] for row in rows])


def load_detail_spec(path: str | Path) -> DetailPageSpec:
    path = Path(path)
    if not path.exists():
        raise DetailPageSpecError(f"spec file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DetailPageSpecError(f"{path}: invalid JSON: {exc}") from exc

    where = str(path)
    product_id = _require_str(raw, "product_id", where)
    name = _require_str(raw, "name", where)
    headline = _require_str(raw, "headline", where)

    colorways_raw = raw.get("colorways")
    if not isinstance(colorways_raw, list) or not colorways_raw:
        raise DetailPageSpecError(f"{where}: 'colorways' must be a non-empty list")
    colorways = []
    for i, c in enumerate(colorways_raw):
        cname = _require_str(c, "name", f"colorways[{i}]")
        images = c.get("images")
        if not isinstance(images, list) or not images or not all(isinstance(x, str) for x in images):
            raise DetailPageSpecError(f"colorways[{i}].images must be a non-empty list of paths")
        colorways.append(Colorway(name=cname, images=images))

    features = []
    for i, f in enumerate(raw.get("features", []) or []):
        features.append(
            Feature(
                title=_require_str(f, "title", f"features[{i}]"),
                body=_require_str(f, "body", f"features[{i}]"),
                image=_optional_str(f, "image"),
            )
        )

    price = raw.get("price")
    if price is not None:
        if not isinstance(price, int) or isinstance(price, bool) or price < 0:
            raise DetailPageSpecError("'price' must be a non-negative integer (KRW)")

    notices = raw.get("notices", []) or []
    if not all(isinstance(n, str) for n in notices):
        raise DetailPageSpecError("'notices' must be a list of strings")

    return DetailPageSpec(
        product_id=product_id,
        name=name,
        headline=headline,
        colorways=colorways,
        features=features,
        price=price,
        brand=_optional_str(raw, "brand"),
        material=_optional_str(raw, "material"),
        size_table=_parse_size_table(raw.get("size_table")),
        notices=list(notices),
        cta_text=_optional_str(raw, "cta_text") or "지금 구매하기",
        cta_url=_optional_str(raw, "cta_url"),
        base_dir=path.parent,
    )


def check_images_exist(spec: DetailPageSpec) -> None:
    missing = [str(p) for p in spec.all_image_paths() if not p.is_file()]
    if missing:
        raise DetailPageSpecError("image file(s) not found: " + ", ".join(missing))
