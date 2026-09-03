"""Naver DataLab Open API -- 쇼핑인사이트 분야별 인기검색어 순위.

developers.naver.com에 이미 등록된 앱의 `NAVER_CLIENT_ID`/
`NAVER_CLIENT_SECRET`을 그대로 쓴다(검색 API와 같은 자격증명) -- 단,
데이터랩(쇼핑인사이트) API는 그 앱에 별도로 "API 이용 신청"을 해야
호출이 될 수 있다(개발자센터 -> 해당 앱 -> API 설정에서 "데이터랩
(쇼핑인사이트)" 추가).

이 개발 환경은 openapi.naver.com 접속이 막혀 있어 실제로 호출해보지
못했다 -- 요청/응답 필드명은 공개된 문서 기준 최선의 추정이며, 실제
배포본에서 `--live`로 한 번 확인 후 다르면 이 파일을 고칠 것. see
docs/CALIBRATION.md.
"""
from __future__ import annotations

from datetime import date, timedelta

import requests

from .models import CategoryKeywordRank

API_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keyword/rank"


class NaverDatalabApiError(RuntimeError):
    pass


class NaverDatalabCategoryRankClient:
    def __init__(self, client_id: str, client_secret: str, timeout: float = 10.0):
        client_id = client_id.strip()
        client_secret = client_secret.strip()
        if not client_id or not client_secret:
            raise NaverDatalabApiError("NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are required in live mode")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    def category_rank(self, category_id: str, target_date: date | None = None, count: int = 20) -> list[CategoryKeywordRank]:
        """`category_id`: trend.categories.CATEGORIES의 키. `target_date`
        기본값은 어제(오늘 날짜는 아직 집계가 안 끝났을 수 있어서)."""
        target_date = target_date or (date.today() - timedelta(days=1))
        date_str = target_date.strftime("%Y-%m-%d")

        response = requests.post(
            API_URL,
            json={
                "startDate": date_str,
                "endDate": date_str,
                "timeUnit": "date",
                "category": category_id,
                "page": 1,
                "count": count,
            },
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        if not response.ok:
            raise NaverDatalabApiError(f"{response.status_code} from category/keyword/rank: {response.text}")
        body = response.json()

        results = []
        for item in body.get("ranks", []):
            results.append(CategoryKeywordRank(rank=item.get("rank"), keyword=item.get("keyword", "")))
        return results
