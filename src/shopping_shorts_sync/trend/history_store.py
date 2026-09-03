"""Monthly keyword-volume snapshots, so `trend search` can show growth vs
the previous month the way 아이템스카우트류 tools do -- the Naver SearchAd
API itself only returns a single current snapshot, with no history.

JSON-file-backed, atomic writes via temp-file + os.replace (same pattern
as state_store.py).
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import KeywordTrend


def current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _prev_month(month: str) -> str:
    year, mon = (int(x) for x in month.split("-"))
    if mon == 1:
        return f"{year - 1}-12"
    return f"{year}-{mon - 1:02d}"


class TrendHistoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._history: dict[str, dict[str, int]] = {}  # keyword -> {"YYYY-MM": total_count}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            self._history = json.load(f)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=".trend-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def growth_pct(self, keyword: str, month: str, current_total: int) -> float | None:
        prev_total = self._history.get(keyword, {}).get(_prev_month(month))
        if not prev_total:
            return None
        return round((current_total - prev_total) / prev_total * 100, 1)

    def record(self, keyword: str, month: str, total_count: int) -> None:
        self._history.setdefault(keyword, {})[month] = total_count

    def apply(self, trends: list[KeywordTrend], month: str | None = None) -> list[KeywordTrend]:
        """Fills in `growth_pct` on each trend from a previous call's
        snapshot (if any), then records this call's totals for next time."""
        month = month or current_month()
        enriched = []
        for trend in trends:
            growth = self.growth_pct(trend.keyword, month, trend.monthly_total_count)
            enriched.append(dataclasses.replace(trend, growth_pct=growth))
            self.record(trend.keyword, month, trend.monthly_total_count)
        return enriched
