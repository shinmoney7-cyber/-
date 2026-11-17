from __future__ import annotations

from dataclasses import dataclass

# Every shopping mall this tool can search. Keep in sync with search/sites.py
# (tests/test_sites.py asserts the two match).
SOURCES = (
    "naver",        # Naver Shopping (official Open API)
    "daiso",        # 다이소몰 (RPA)
    "oliveyoung",   # 올리브영 (RPA)
    "11st",         # 11번가 (RPA)
    "gmarket",      # G마켓 (RPA)
    "auction",      # 옥션 (RPA)
    "ssg",          # SSG.COM (RPA)
    "lotteon",      # 롯데온 (RPA)
    "gsshop",       # GS SHOP (RPA)
    "hmall",        # 현대Hmall (RPA)
    "kurly",        # 마켓컬리 (RPA)
    "musinsa",      # 무신사 (RPA)
    "29cm",         # 29CM (RPA)
    "ohouse",       # 오늘의집 (RPA)
    "amazon",       # Amazon (RPA)
    "aliexpress",   # AliExpress (RPA)
)


@dataclass(frozen=True)
class SearchResult:
    source: str
    name: str
    image_url: str
    product_url: str
    price: str | None = None
