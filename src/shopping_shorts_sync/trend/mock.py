from __future__ import annotations

import hashlib
from datetime import date

from .models import CategoryKeywordRank, KeywordTrend

_COMP_LEVELS = ("낮음", "중간", "높음")
_MOCK_KEYWORD_POOL = [
    "겨울코트", "무선청소기", "캠핑의자", "홍삼스틱", "샤인머스캣",
    "블루투스이어폰", "러닝화", "아기띠", "에어프라이어", "제습기",
    "캣타워", "전기요", "가습기", "노트북거치대", "폼롤러",
    "핸드크림", "선크림", "텀블러", "우산", "담요",
]


class MockKeywordTrendClient:
    """Drop-in stand-in for NaverAdKeywordClient. No network. Produces
    deterministic fake volumes so repeated searches for the same keyword
    are stable (same pattern as search/mock.py)."""

    def search(self, keywords: list[str]) -> list[KeywordTrend]:
        results = []
        for keyword in keywords:
            digest = hashlib.sha256(keyword.encode("utf-8")).hexdigest()
            pc = int(digest[:4], 16) % 5000
            mobile = int(digest[4:8], 16) % 15000
            comp_idx = _COMP_LEVELS[int(digest[8:10], 16) % len(_COMP_LEVELS)]
            results.append(
                KeywordTrend(
                    keyword=keyword,
                    monthly_pc_count=pc,
                    monthly_mobile_count=mobile,
                    comp_idx=comp_idx,
                )
            )
        return results


class MockCategoryRankClient:
    """Drop-in stand-in for NaverDatalabCategoryRankClient. Shuffles a fixed
    keyword pool deterministically per (category_id, day) so repeated calls
    on the same day are stable but the order visibly differs day to day
    (useful for seeing rank_delta show up in dry-run)."""

    def category_rank(
        self, category_id: str, target_date: date | None = None, count: int = 20
    ) -> list[CategoryKeywordRank]:
        target_date = target_date or date.today()
        seed = f"{category_id}:{target_date.isoformat()}"
        pool = list(_MOCK_KEYWORD_POOL)
        # Deterministic shuffle keyed by seed, no `random` module needed.
        pool.sort(key=lambda kw: hashlib.sha256(f"{seed}:{kw}".encode("utf-8")).hexdigest())
        return [CategoryKeywordRank(rank=i + 1, keyword=kw) for i, kw in enumerate(pool[:count])]
