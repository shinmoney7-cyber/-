from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import Item


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SeenDB:
    """Every product we've ever seen per source, with last price — the baseline
    for 신규 감지 and 가격 하락 감지. Atomic writes."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.items: dict[str, dict] = {}
        if self.path.exists():
            self.items = json.loads(self.path.read_text(encoding="utf-8")).get("items", {})

    def count(self, source: str | None = None) -> int:
        if source is None:
            return len(self.items)
        return sum(1 for k in self.items if k.startswith(source + ":"))

    def has_source(self, source: str) -> bool:
        return any(k.startswith(source + ":") for k in self.items)

    def get(self, item: Item) -> dict | None:
        return self.items.get(item.key)

    def upsert(self, item: Item) -> None:
        entry = self.items.get(item.key)
        if entry is None:
            self.items[item.key] = {"price": item.price, "first_seen": _now(), "last_seen": _now(),
                                    "brand": item.brand, "name": item.name}
        else:
            entry["price"] = item.price
            entry["last_seen"] = _now()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".seen-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "items": self.items}, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
