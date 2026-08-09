from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

PUBLISH_STATE_VERSION = 1


class PipelineStatus(str, Enum):
    """Full content-to-publish pipeline states in order."""
    DISCOVERED = "DISCOVERED"
    FACT_CHECKED = "FACT_CHECKED"
    SCRIPTED = "SCRIPTED"
    ASSETS_READY = "ASSETS_READY"
    RENDERED = "RENDERED"
    LINK_READY = "LINK_READY"
    APPROVED = "APPROVED"
    UPLOADED = "UPLOADED"
    PUBLISHED = "PUBLISHED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    LINK_BLOCKED = "LINK_BLOCKED"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class DestinationRecord:
    account: str
    platform: str          # instagram | threads
    post_id: str | None = None
    post_url: str | None = None
    published_at: str | None = None
    status: str = "pending"  # pending | published | verified | failed
    error: str | None = None


@dataclass
class PublishRecord:
    product_id: str
    product_name: str
    category: str
    pipeline_status: str = PipelineStatus.DISCOVERED.value
    inpock_url: str | None = None
    video_path: str | None = None
    video_url: str | None = None
    thumbnail_path: str | None = None
    captions: dict[str, str] = field(default_factory=dict)
    destinations: dict[str, dict] = field(default_factory=dict)  # key: "account_platform"
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)
    errors: list[str] = field(default_factory=list)

    def set_status(self, status: PipelineStatus) -> None:
        self.pipeline_status = status.value
        self.updated_at = _utcnow_iso()

    def record_destination(self, account: str, platform: str, result) -> None:
        key = f"{account}_{platform}"
        dest = DestinationRecord(
            account=account,
            platform=platform,
            post_id=result.post_id,
            post_url=result.post_url,
            published_at=_utcnow_iso() if result.ok else None,
            status="published" if result.ok else "failed",
            error=result.error,
        )
        self.destinations[key] = asdict(dest)
        self.updated_at = _utcnow_iso()

    def verify_destination(self, account: str, platform: str, verified_url: str | None) -> None:
        key = f"{account}_{platform}"
        if key in self.destinations:
            self.destinations[key]["status"] = "verified"
            if verified_url:
                self.destinations[key]["post_url"] = verified_url
        self.updated_at = _utcnow_iso()

    def all_published(self) -> bool:
        return bool(self.destinations) and all(
            d.get("status") in ("published", "verified")
            for d in self.destinations.values()
        )

    def all_verified(self) -> bool:
        return bool(self.destinations) and all(
            d.get("status") == "verified"
            for d in self.destinations.values()
        )

    def add_error(self, message: str) -> None:
        self.errors.append(f"[{_utcnow_iso()}] {message}")
        self.updated_at = _utcnow_iso()

    def summary_rows(self) -> list[dict]:
        rows = []
        for key, dest in self.destinations.items():
            rows.append({
                "product_id": self.product_id,
                "product_name": self.product_name,
                "category": self.category,
                "pipeline": self.pipeline_status,
                "destination": key,
                "status": dest.get("status"),
                "post_url": dest.get("post_url"),
                "error": dest.get("error"),
            })
        if not rows:
            rows.append({
                "product_id": self.product_id,
                "product_name": self.product_name,
                "category": self.category,
                "pipeline": self.pipeline_status,
                "destination": "(none)",
                "status": "-",
                "post_url": None,
                "error": "; ".join(self.errors) if self.errors else None,
            })
        return rows


class PublishStore:
    """JSON-file-backed store for the full content-to-publish pipeline state.

    Atomic writes via temp-file + os.replace (same pattern as StateStore).
    """

    def __init__(self, path: str | Path = "data/publish_state.json"):
        self.path = Path(path)
        self._records: dict[str, PublishRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        for pid, entry in raw.get("records", {}).items():
            # Convert dict to dataclass, ignoring unknown keys for forward compat
            known = {k: v for k, v in entry.items() if k in PublishRecord.__dataclass_fields__}
            self._records[pid] = PublishRecord(**known)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": PUBLISH_STATE_VERSION,
            "records": {pid: asdict(rec) for pid, rec in self._records.items()},
        }
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".pub-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def get(self, product_id: str) -> PublishRecord | None:
        return self._records.get(product_id)

    def upsert(self, record: PublishRecord) -> None:
        self._records[record.product_id] = record

    def create(self, product_id: str, product_name: str, category: str) -> PublishRecord:
        if product_id not in self._records:
            rec = PublishRecord(product_id=product_id, product_name=product_name, category=category)
            self._records[product_id] = rec
        return self._records[product_id]

    def all(self) -> dict[str, PublishRecord]:
        return dict(self._records)

    def reset(self, product_id: str) -> bool:
        return self._records.pop(product_id, None) is not None
