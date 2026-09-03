from __future__ import annotations

import hashlib

from .models import KeywordTrend

_COMP_LEVELS = ("낮음", "중간", "높음")


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
