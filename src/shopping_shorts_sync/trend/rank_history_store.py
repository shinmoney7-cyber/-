"""Daily category-rank snapshots, so `trend category` can show rank
movement ("어제보다 몇 계단 상승") the way DataLab itself doesn't directly
expose -- it only returns a single day's ranking, no delta.

JSON-file-backed, atomic writes via temp-file + os.replace (same pattern
as state_store.py / trend/history_store.py).
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

from .models import CategoryKeywordRank


class RankHistoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._history: dict[str, dict[str, dict[str, int]]] = {}  # category_id -> {"YYYY-MM-DD": {keyword: rank}}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            self._history = json.load(f)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=".rank-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _prev_ranks(self, category_id: str, target_date_str: str) -> dict[str, int]:
        prev_day = (date.fromisoformat(target_date_str) - timedelta(days=1)).isoformat()
        return self._history.get(category_id, {}).get(prev_day, {})

    def record(self, category_id: str, target_date_str: str, ranks: list[CategoryKeywordRank]) -> None:
        snapshot = {r.keyword: r.rank for r in ranks}
        self._history.setdefault(category_id, {})[target_date_str] = snapshot

    def apply(
        self, category_id: str, target_date_str: str, ranks: list[CategoryKeywordRank]
    ) -> list[CategoryKeywordRank]:
        """Fills in `prev_rank` on each entry from the previous day's
        snapshot (if any), then records this call's ranks for next time."""
        prev_ranks = self._prev_ranks(category_id, target_date_str)
        enriched = [
            dataclasses.replace(r, prev_rank=prev_ranks.get(r.keyword)) for r in ranks
        ]
        self.record(category_id, target_date_str, ranks)
        return enriched
