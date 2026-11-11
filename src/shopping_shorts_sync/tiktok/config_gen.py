from __future__ import annotations

import re

from .analyzer import extract_hashtags, extract_price
from .models import RemotionConfig, VideoMeta

_BENEFIT_PLACEHOLDERS = [
    "주요 성분 효과",
    "피부 개선 효과",
    "전문가 인증",
    "4주 후 눈에 띄는 변화",
]


def _split_hook(title: str) -> tuple[str, str]:
    """Split title into two hook lines at natural break points."""
    # Try to split on ?, !, or midpoint
    for sep in ("?", "!", "。", "…"):
        parts = title.split(sep, 1)
        if len(parts) == 2 and parts[0].strip():
            return parts[0].strip() + sep, parts[1].strip()

    words = title.split()
    mid = max(1, len(words) // 2)
    return " ".join(words[:mid]), " ".join(words[mid:])


def _guess_product_name(meta: VideoMeta) -> str:
    tags = extract_hashtags(meta.raw_description)
    # Use the first hashtag that looks like a product name (contains Korean)
    for tag in tags:
        if re.search(r"[가-힣]", tag) and len(tag) >= 2:
            return tag
    # Fall back to first 10 chars of title
    return meta.title[:10] if meta.title else "상품명"


def _guess_hook_sub(raw_description: str) -> str:
    tags = extract_hashtags(raw_description)
    # Pick 2 meaningful hashtags for the hook sub
    meaningful = [t for t in tags if re.search(r"[가-힣A-Za-z]", t)][:2]
    if meaningful:
        return " ".join(f"#{t}" for t in meaningful)
    return "🔍 지금 바로 확인"


def generate_remotion_config(meta: VideoMeta, override_price: str = "") -> RemotionConfig:
    hook_line1, hook_line2 = _split_hook(meta.title or "이 제품")
    price = override_price or extract_price(meta.raw_description) or "가격 확인"

    return RemotionConfig(
        hook_line1=hook_line1,
        hook_line2=hook_line2 or "지금 확인하세요",
        hook_sub=_guess_hook_sub(meta.raw_description),
        product_name=_guess_product_name(meta),
        benefits=list(_BENEFIT_PLACEHOLDERS),
        price=price,
        thumbnail_url=meta.thumbnail_url,
    )
