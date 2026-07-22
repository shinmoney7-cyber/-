from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Product


class InputLoadError(ValueError):
    pass


def load_products(path: str | Path) -> list[Product]:
    path = Path(path)
    if not path.exists():
        raise InputLoadError(f"input file not found: {path}")

    if path.suffix.lower() == ".json":
        rows = _load_json_rows(path)
    elif path.suffix.lower() == ".csv":
        rows = _load_csv_rows(path)
    else:
        raise InputLoadError(f"unsupported input file extension: {path.suffix}")

    products: list[Product] = []
    seen_ids: set[str] = set()
    for i, row in enumerate(rows):
        try:
            product = Product.from_dict(row)
        except Exception as exc:
            raise InputLoadError(f"row {i} in {path}: {exc}") from exc

        if product.id in seen_ids:
            raise InputLoadError(f"duplicate product id {product.id!r} in {path}")
        seen_ids.add(product.id)
        products.append(product)

    return products


def _load_json_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise InputLoadError(f"{path} must contain a JSON array of product objects")
    return data


def _load_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
