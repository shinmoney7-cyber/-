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


@dataclass(frozen=True)
class CategoryKeywordRank:
    rank: int
    keyword: str
    prev_rank: int | None = None  # 어제(직전 조회) 순위, 히스토리가 있을 때만

    @property
    def rank_delta(self) -> int | None:
        """양수면 순위 상승(예: 어제 10위 -> 오늘 3위 = +7)."""
        if self.prev_rank is None:
            return None
        return self.prev_rank - self.rank
