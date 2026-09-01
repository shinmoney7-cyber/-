from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .models import Product

STATE_VERSION = 1


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class VideoRecord:
    candidate_id: int
    provider: str           # "higgsfield" | "topview" | "abocado"
    job_id: str | None = None
    video_url: str | None = None
    status: str = "pending"  # pending | ready | error
    generated_at: str | None = None
    error: str | None = None


@dataclass
class ProductState:
    coupang_url: str
    deeplink: str | None = None
    deeplink_generated_at: str | None = None
    target_page: str | None = None
    content_hash: str | None = None
    inpock_synced_at: str | None = None
    status: str = "new"
    last_error: str | None = None
    selected_script_id: int | None = None
    script_text: str | None = None
    script_applied_at: str | None = None
    videos: list[dict] = field(default_factory=list)


class StateStore:
    """JSON-file-backed idempotency tracker. Atomic writes via temp-file + os.replace."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._products: dict[str, ProductState] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        for product_id, entry in raw.get("products", {}).items():
            self._products[product_id] = ProductState(**entry)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STATE_VERSION,
            "products": {pid: asdict(state) for pid, state in self._products.items()},
        }
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=".state-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def get(self, product_id: str) -> ProductState | None:
        return self._products.get(product_id)

    def needs_deeplink(self, product: Product) -> bool:
        state = self._products.get(product.id)
        if state is None or not state.deeplink:
            return True
        return state.coupang_url != product.coupang_url

    def record_deeplink(self, product: Product, deeplink: str) -> None:
        state = self._products.setdefault(product.id, ProductState(coupang_url=product.coupang_url))
        state.coupang_url = product.coupang_url
        state.deeplink = deeplink
        state.deeplink_generated_at = _utcnow_iso()
        state.target_page = product.target_page
        state.status = "deeplink_ready"
        state.last_error = None

    def record_deeplink_error(self, product: Product, error: str) -> None:
        state = self._products.setdefault(product.id, ProductState(coupang_url=product.coupang_url))
        state.coupang_url = product.coupang_url
        state.status = "error"
        state.last_error = error

    def needs_inpock_sync(self, product: Product) -> bool:
        state = self._products.get(product.id)
        if state is None or not state.deeplink:
            return False  # nothing to sync yet, deeplink stage runs first
        current_hash = product.content_hash(state.deeplink)
        return state.content_hash != current_hash or not state.inpock_synced_at

    def record_inpock_sync(self, product: Product) -> None:
        state = self._products[product.id]
        state.content_hash = product.content_hash(state.deeplink)
        state.inpock_synced_at = _utcnow_iso()
        state.status = "synced"
        state.last_error = None

    def record_inpock_error(self, product: Product, error: str) -> None:
        state = self._products.setdefault(product.id, ProductState(coupang_url=product.coupang_url))
        state.status = "error"
        state.last_error = error

    def apply_script(self, product: Product, candidate_id: int, script_text: str) -> None:
        """Records the owner's selection of one of the 5 script candidates as
        immediately active for this product ("자동 연동"). Independent of the
        Coupang/Inpock sync status tracked above."""
        state = self._products.setdefault(product.id, ProductState(coupang_url=product.coupang_url))
        state.selected_script_id = candidate_id
        state.script_text = script_text
        state.script_applied_at = _utcnow_iso()

    def record_video(
        self,
        product: Product,
        candidate_id: int,
        provider: str,
        job_id: str | None = None,
        video_url: str | None = None,
        status: str = "ready",
        error: str | None = None,
    ) -> None:
        state = self._products.setdefault(product.id, ProductState(coupang_url=product.coupang_url))
        rec = VideoRecord(
            candidate_id=candidate_id,
            provider=provider,
            job_id=job_id,
            video_url=video_url,
            status=status,
            generated_at=_utcnow_iso(),
            error=error,
        )
        # Replace existing record for same candidate+provider, else append.
        new_list = [
            v for v in state.videos
            if not (v.get("candidate_id") == candidate_id and v.get("provider") == provider)
        ]
        new_list.append(asdict(rec))
        state.videos = new_list

    def get_videos(self, product_id: str) -> list[VideoRecord]:
        state = self._products.get(product_id)
        if not state:
            return []
        return [VideoRecord(**v) for v in state.videos]

    def reset(self, product_id: str) -> bool:
        return self._products.pop(product_id, None) is not None

    def all(self) -> dict[str, ProductState]:
        return dict(self._products)
