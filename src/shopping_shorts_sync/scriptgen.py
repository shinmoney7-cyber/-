"""Automatic AIDA script generation from the owner's handwritten framework.

Structure (from the owner's notes): every candidate follows AIDA —
attention (hook, ~0-3s), interest (~3-10s, one differentiator), desire
(~10-20s, usage/result scene), action (~20-25s, one clear CTA). The
"desire" stage is built from one of 7 persuasion elements: the category's
base desire itself, plus 6 techniques (loss aversion, social proof,
authority, curiosity gap, quantified benefit, family narrative). Which 5
of the 7 appear, and in what order, is category-tuned since some
techniques fit some categories better (e.g. family narrative for 육아).

This is a deterministic template generator, not an LLM call — same
product name/category always produces the same 5 candidates, so it's
safe to regenerate without surprising anyone who already picked a
candidate.
"""
from __future__ import annotations

from .script_store import REQUIRED_CANDIDATE_COUNT, ScriptCandidate

# 쿠팡 파트너스 운영정책상 고지 문구 (수수료 수령 사실을 명시해야 함). 텍스트/설명란 표기용.
COUPANG_PARTNERS_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
)

# 영상 화면 자체에 얹는 표기. owner's notes: "동영상 생성시 화면 상단 오른쪽에 [광고]
# 문구 꼭 삽입" -- 이건 위 텍스트 고지와 별개로, 모든 영상 미리보기/완성본에 빠짐없이
# 들어가야 하는 온스크린 오버레이이므로 상수로 고정해서 어디서든 같은 문구를 쓴다.
AD_LABEL = "[광고]"
AD_LABEL_POSITION = "top-right"

CATEGORY_DESIRES: dict[str, list[str]] = {
    "뷰티": [
        "예뻐지고 싶다",
        "더 어려 보이고 싶다",
        "피부 좋아졌다는 말을 듣고 싶다",
        "미모 경쟁에서 뒤처지고 싶지 않다",
        "좋은 인상을 주고 싶다",
    ],
    "생활용품": [
        "귀찮음을 없애고 싶다",
        "집안일을 줄이고 싶다",
        "집안일을 쉽게 하고 싶다",
        "청소를 덜 하고 싶다",
    ],
    "육아": [
        "가족을 더 잘 챙기고 싶다",
        "아이에게 좋은 것만 주고 싶다",
        "안전하게 키우고 싶다",
        "부모 역할을 잘하고 싶다",
    ],
    "다이어트": [
        "더 나은 몸으로 살 빼고 싶다",
        "몸매 열등감을 해소하고 싶다",
        "오래 살고 싶다",
    ],
    "가전": [
        "편리해지고 싶다",
        "시간을 아끼고 싶다",
        "귀찮은 걸 자동화하고 싶다",
        "더 스마트하게 살고 싶다",
    ],
}

# 사용자 노트에 등장한 표기 변형 -> 표준 카테고리 키.
_CATEGORY_ALIASES: dict[str, str] = {
    "뷰티": "뷰티",
    "화장품": "뷰티",
    "뷰티/화장품": "뷰티",
    "생활": "생활용품",
    "생활용품": "생활용품",
    "육아": "육아",
    "육아용품": "육아",
    "다이어트": "다이어트",
    "건강": "다이어트",
    "다이어트/건강": "다이어트",
    "가전": "가전",
    "it": "가전",
    "전자기기": "가전",
    "전자기기/it": "가전",
}

_DEFAULT_DESIRES = ["더 나은 선택을 하고 싶다", "지금보다 편해지고 싶다"]

# 카테고리별로 어떤 기법 5개를 어떤 순서로 쓸지 (7개 중 5개 선택).
_DEFAULT_TECHNIQUE_ORDER = ["desire", "loss_aversion", "social_proof", "authority", "curiosity_gap"]
_CATEGORY_TECHNIQUE_ORDER: dict[str, list[str]] = {
    "뷰티": ["desire", "social_proof", "loss_aversion", "authority", "curiosity_gap"],
    "생활용품": ["desire", "loss_aversion", "quantified_benefit", "social_proof", "curiosity_gap"],
    "육아": ["desire", "family_narrative", "authority", "loss_aversion", "social_proof"],
    "다이어트": ["desire", "quantified_benefit", "social_proof", "loss_aversion", "authority"],
    "가전": ["desire", "quantified_benefit", "curiosity_gap", "authority", "loss_aversion"],
}

_ATTENTION_TEMPLATES = [
    "{name} 이거 안 써보신 분?",
    "{name} 써보고 진짜 후회 없었어요",
    "요즘 다들 이거 하나씩은 있더라고요, {name}",
    "{name}, 이거 모르면 손해예요",
    "장바구니에 담아놓고 고민만 하던 제품, {name}",
]

_INTEREST_TEMPLATES = [
    "다른 {category} 제품이랑 다른 거 딱 하나, 이건 확실히 달라요",
    "비슷한 제품 다 써봤는데 {name}만 이 부분이 남달라요",
    "가격 대비 차이가 여기서 확 갈려요",
    "다들 비슷해 보여도 실제로 써보면 이게 제일 다르더라고요",
    "이 가격에 이 정도 되는 건 {name}밖에 없었어요",
]

_ACTION_TEMPLATES = [
    "아래 쇼핑태그 눌러서 확인하세요",
    "'{name}' 검색하고 나오는 화면에서 바로 눌러보세요",
    "구독하고 다음 후기도 받아보세요",
    "이 링크로 지금 바로 주문하세요",
    "더 궁금하시면 '추가로 보기' 눌러서 확인하세요",
]


def _resolve_category(category: str) -> tuple[str, list[str]]:
    key = _CATEGORY_ALIASES.get(category.strip().lower(), category.strip())
    if key in CATEGORY_DESIRES:
        return key, CATEGORY_DESIRES[key]
    return key, _DEFAULT_DESIRES


def _technique_order_for(category_key: str) -> list[str]:
    return _CATEGORY_TECHNIQUE_ORDER.get(category_key, _DEFAULT_TECHNIQUE_ORDER)


def _desire_line(technique: str, name: str, desire: str) -> str:
    builders = {
        "desire": lambda: f"'{desire}'는 마음으로 써봤는데, {name} 하나로 완전 해결했어요",
        "loss_aversion": lambda: f"'{desire}'는 마음, 이거 몰라서 여태 손해봤어요. {name} 하나로 끝냈어요",
        "social_proof": lambda: f"'{desire}'는 분 많으실 텐데, 주변에서 다들 쓰길래 저도 {name} 써봤더니 진짜 되더라고요",
        "authority": lambda: f"'{desire}'는 마음, 관련 분야 전문가가 알려준 방법이에요. {name}로 직접 확인했어요",
        "curiosity_gap": lambda: f"'{desire}'는 분들 아직 이 방법 모르실 텐데, {name} 하나로 되는 거 보여드릴게요",
        "quantified_benefit": lambda: f"'{desire}'는 마음이었는데, {name} 쓰고 나서 체감이 확 달라졌어요",
        "family_narrative": lambda: f"'{desire}'는 마음으로 가족 생각하면서 고른 건데, {name} 덕분에 이제 걱정 안 해요",
    }
    return builders[technique]()


def generate_candidates(product_name: str, category: str) -> list[ScriptCandidate]:
    """Generates exactly REQUIRED_CANDIDATE_COUNT AIDA candidates for a
    product, each tagged with which of the 7 persuasion elements its
    desire stage uses. Deterministic: same inputs -> same output."""
    category_key, desires = _resolve_category(category)
    techniques = _technique_order_for(category_key)

    candidates: list[ScriptCandidate] = []
    for i in range(REQUIRED_CANDIDATE_COUNT):
        technique = techniques[i % len(techniques)]
        desire_phrase = desires[i % len(desires)]
        candidates.append(
            ScriptCandidate(
                id=i + 1,
                attention=_ATTENTION_TEMPLATES[i].format(name=product_name),
                interest=_INTEREST_TEMPLATES[i].format(name=product_name, category=category or category_key),
                desire=_desire_line(technique, product_name, desire_phrase),
                action=_ACTION_TEMPLATES[i].format(name=product_name),
                technique=technique,
            )
        )
    return candidates


_PLATFORM_TAGS: dict[str, list[str]] = {
    "instagram": ["#쿠팡파트너스", "#내돈내산", "#추천템"],
    "threads": ["#쿠팡파트너스", "#추천템"],
    "youtube": ["#쿠팡파트너스", "#쇼츠", "#추천템"],
    "tiktok": ["#쿠팡파트너스", "#추천템", "#가성비"],
    "naver_clip": ["#쿠팡파트너스", "#네이버클립", "#추천템"],
    "toss": ["#쿠팡파트너스", "#추천템"],
    "danggeun": ["#쿠팡파트너스", "#동네추천"],
    "naver_blog": ["#쿠팡파트너스", "#내돈내산", "#솔직후기"],
}


def generate_hashtags(product_name: str, category: str) -> dict[str, list[str]]:
    """Per-platform hashtag sets. Every platform's set always includes the
    disclosure hashtag; callers should still show COUPANG_PARTNERS_DISCLOSURE
    as plain text too, since a hashtag alone doesn't satisfy the Coupang
    Partners disclosure requirement."""
    category_key, _ = _resolve_category(category)
    name_tag = "#" + product_name.replace(" ", "")
    category_tag = "#" + category_key.replace("/", "")
    return {
        platform: [name_tag, category_tag, *base_tags]
        for platform, base_tags in _PLATFORM_TAGS.items()
    }
