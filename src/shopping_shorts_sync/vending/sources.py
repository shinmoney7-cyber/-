"""Listing sources.

JsonHttpSource is generic: url template + dotted field mapping from config.
None of the site mappings in data/vending/settings.example.json were verified
against the live sites (this project's build environment has no outbound
access to them) — calibrate per docs/VENDING.md before relying on live runs.
Respect each site's terms of service and robots rules; keep request_delay_sec
conservative.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import requests

from .models import Item
from .settings import SourceSpec

log = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


class Source(Protocol):
    name: str

    def fetch_brand(self, brand: str) -> list[Item]: ...


def dig(obj, path: str):
    """Dotted-path lookup supporting list indexes: 'data.list', 'images.0.url'."""
    if not path:
        return None
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _to_int(value) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


def parse_items(source: str, payload, spec_fields: dict, list_path: str, brand: str) -> list[Item]:
    rows = dig(payload, list_path) if list_path else payload
    items = []
    for raw in rows or []:
        product_no = dig(raw, spec_fields.get("product_no", ""))
        if product_no is None:
            continue
        sold_out = dig(raw, spec_fields.get("sold_out", ""))
        items.append(
            Item(
                source=source,
                product_no=str(product_no),
                brand=str(dig(raw, spec_fields.get("brand", "")) or brand),
                name=str(dig(raw, spec_fields.get("name", "")) or ""),
                price=_to_int(dig(raw, spec_fields.get("price", ""))),
                url=str(dig(raw, spec_fields.get("url", "")) or ""),
                image=str(dig(raw, spec_fields.get("image", "")) or ""),
                style_code=str(dig(raw, spec_fields.get("style_code", "")) or ""),
                sizes=str(dig(raw, spec_fields.get("sizes", "")) or ""),
                store=str(dig(raw, spec_fields.get("store", "")) or ""),
                sold_out=bool(sold_out) if sold_out is not None else False,
            )
        )
    return items


class JsonHttpSource:
    def __init__(self, spec: SourceSpec, delay_sec: float = 1.0, session: requests.Session | None = None):
        self.spec = spec
        self.name = spec.name
        self.delay_sec = delay_sec
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_UA, **spec.headers})
        self._warmed = False

    def warmup(self) -> int | None:
        """Hit the site's front page once so cookies are set (세션 워밍업)."""
        if not self.spec.warmup_url:
            return None
        resp = self.session.get(self.spec.warmup_url, timeout=15)
        self._warmed = True
        return resp.status_code

    def fetch_brand(self, brand: str) -> list[Item]:
        brand_id = self.spec.brand_ids.get(brand)
        if brand_id is None:
            return []
        if not self._warmed:
            self.warmup()
        items: list[Item] = []
        for page in range(1, self.spec.max_pages + 1):
            url = self.spec.url.format(brand_id=brand_id, page=page)
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            page_items = parse_items(self.name, resp.json(), self.spec.fields, self.spec.list_path, brand)
            items.extend(page_items)
            if not page_items:
                break
            time.sleep(self.delay_sec)
        return items


class FixtureSource:
    """Offline stand-in: reads fixtures/vending/<source>.json -> {brand: [item dicts]}."""

    def __init__(self, name: str, fixture_dir: str | Path):
        self.name = name
        path = Path(fixture_dir) / f"{name}.json"
        self._data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def warmup(self) -> int | None:
        return 200

    def fetch_brand(self, brand: str) -> list[Item]:
        return [Item.from_dict({"source": self.name, "brand": brand, **d}) for d in self._data.get(brand, [])]


class CachedSource:
    """Per-source, per-brand JSON cache with TTL (STEP 1 '캐시 로드 (65분 전)')."""

    def __init__(self, inner, cache_dir: str | Path, ttl_minutes: int):
        self.inner = inner
        self.name = inner.name
        self.cache_dir = Path(cache_dir)
        self.ttl_sec = ttl_minutes * 60
        self.last_hit_age_min: int | None = None

    def warmup(self):
        return getattr(self.inner, "warmup", lambda: None)()

    def _path(self, brand: str) -> Path:
        safe = "".join(ch if ch.isalnum() else "_" for ch in brand)
        return self.cache_dir / self.name / f"{safe}.json"

    def fetch_brand(self, brand: str) -> list[Item]:
        path = self._path(brand)
        now = time.time()
        if path.exists():
            cached = json.loads(path.read_text(encoding="utf-8"))
            age = now - cached["fetched_at"]
            if age < self.ttl_sec:
                self.last_hit_age_min = int(age // 60)
                return [Item.from_dict(d) for d in cached["items"]]
        self.last_hit_age_min = None
        items = self.inner.fetch_brand(brand)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"fetched_at": now, "items": [i.to_dict() for i in items]}, ensure_ascii=False),
            encoding="utf-8",
        )
        return items


def build_sources(specs, fixture_dir: str | Path | None, delay_sec: float, cache_dir=None, ttl_minutes: int = 0):
    out = []
    for spec in specs:
        src = FixtureSource(spec.name, fixture_dir) if fixture_dir else JsonHttpSource(spec, delay_sec)
        if cache_dir and ttl_minutes > 0:
            src = CachedSource(src, cache_dir, ttl_minutes)
        out.append(src)
    return out
