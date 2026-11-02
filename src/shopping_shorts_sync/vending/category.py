"""상품명/브랜드 -> 카테고리 (신발 / 가방 / 의류 / 잡화). Keyword based, first match wins."""
from __future__ import annotations

import re

SHOES = "신발"
CATEGORIES = (SHOES, "가방", "의류", "잡화")

_KEYWORDS = [
    (SHOES, ["운동화", "스니커즈", "스니커", "신발", "슈즈", "슈 ", "러닝화", "워킹화", "등산화", "트레킹화", "부츠", "워커",
             "로퍼", "더비", "옥스퍼드", "샌들", "슬리퍼", "슬라이드", "뮬", "클로그", "플립플랍", "쪼리", "에스파드리유",
             "덩크", "에어포스", "에어맥스", "조던", "척테일러", "척70", "올드스쿨", "슬립온", "삼바", "가젤", "스탠스미스",
             "슈퍼스타", "젤카야노", "젤 ", "고워크", "xt-6", "xt6", "스피드캣", "sneaker", "shoe", "boot", "sandal", "slide"]),
    ("가방", ["가방", "백팩", "토트", "숄더백", "크로스백", "클러치", "파우치", "카세트백", "호보", "버킷백", "메신저백", "더플", "bag"]),
    ("의류", ["후디", "후드", "맨투맨", "스웨트", "티셔츠", "반팔", "긴팔", "셔츠", "피케", "니트", "가디건", "자켓", "재킷",
             "점퍼", "패딩", "코트", "베스트", "조끼", "팬츠", "바지", "청바지", "데님", "슬랙스", "쇼츠", "반바지", "스커트",
             "원피스", "레깅스", "트레이닝", "트랙탑", "오버셔츠", "블루종", "아노락", "바람막이", "플리스"]),
    ("잡화", ["모자", "캡", "비니", "버킷햇", "양말", "벨트", "지갑", "카드홀더", "키링", "머플러", "스카프", "장갑", "선글라스"]),
]
# brands that are (almost) only footwear
_SHOE_BRANDS = {"크록스", "crocs", "스케쳐스", "skechers", "컨버스", "converse", "반스", "vans", "아식스", "asics",
                "살로몬", "salomon", "호카", "hoka", "버켄스탁", "birkenstock", "닥터마틴", "drmartens", "어그", "ugg"}
# 뉴발란스 990/993/530/2002R..., 나이키 DD1391-100 style shoe codes are too ambiguous to rely on alone
_NB_SHOE_MODEL = re.compile(r"\b(m|u|w|ml|mr|wl|gc|pc)?\d{3,4}[a-z]{0,3}\b", re.I)


def classify(name: str, brand: str = "") -> str:
    text = f" {name or ''} ".lower()
    for cat, words in _KEYWORDS:
        if any(w.lower() in text for w in words):
            return cat
    b = (brand or "").lower().replace(" ", "")
    if b in _SHOE_BRANDS:
        return SHOES
    if b in ("뉴발란스", "newbalance") and _NB_SHOE_MODEL.search(name or ""):
        return SHOES
    return "기타"


def is_shoe(name: str, brand: str = "") -> bool:
    return classify(name, brand) == SHOES
