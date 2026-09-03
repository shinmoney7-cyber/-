from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordTrend:
    keyword: str
    monthly_pc_count: int
    monthly_mobile_count: int
    comp_idx: str | None  # 네이버가 주는 경쟁정도: "낮음"/"중간"/"높음"
    growth_pct: float | None = None  # 전월 대비 증가율(%), 히스토리가 있을 때만

    @property
    def monthly_total_count(self) -> int:
        return self.monthly_pc_count + self.monthly_mobile_count
