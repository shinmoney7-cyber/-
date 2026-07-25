from __future__ import annotations

import json
from typing import Protocol

from .models import Product
from .script_store import REQUIRED_CANDIDATE_COUNT, ScriptCandidate, ScriptSet

_SYSTEM_PROMPT = """\
너는 한국 숏폼 쇼핑 콘텐츠 대본 전문 작가다.
AIDA(주의-흥미-욕망-행동) 구조로 정확히 {n}개의 대본 후보를 작성한다.

각 단계의 역할과 시간 제한:
- attention (~3초): 시청자가 공감하는 일상적 불편함이나 상황을 1인칭 과거형으로 시작한다.
- interest (~3~10초): "다른 X랑 다르게" 또는 "다른 제품은..." 형식으로 이 상품의 차별점을 설명한다.
- desire (~10~20초): 직접 써본 결과를 구체적 감각 또는 수치로 묘사한다. "직접 써봤는데", "직접 해봤는데" 등으로 시작 권장.
- action (~20~25초): 구매 또는 팔로우를 유도하는 CTA. "아래 쇼핑태그 눌러주세요" 또는 "팔로우하고 놓치지 마세요" 패턴 사용.

5개 후보는 전략적으로 다양하게:
- 1~2번: 불편함 → 해결 각도
- 3번: 비교 우위 각도
- 4번: 전후(Before/After) 변화 각도
- 5번: 가성비/타이밍 각도

출력 형식은 반드시 아래 JSON만 반환한다. 다른 텍스트 없이:
{{
  "candidates": [
    {{"id": 1, "attention": "...", "interest": "...", "desire": "...", "action": "..."}},
    ...
  ]
}}
"""

_USER_PROMPT = """\
상품명: {name}
카테고리: {category}
썸네일: {thumbnail}
"""


class ScriptGeneratorProtocol(Protocol):
    def generate(self, product: Product) -> ScriptSet: ...


class OpenAIScriptGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("openai package is required: pip install 'openai>=1.0'") from exc
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(self, product: Product) -> ScriptSet:
        system = _SYSTEM_PROMPT.format(n=REQUIRED_CANDIDATE_COUNT)
        user = _USER_PROMPT.format(
            name=product.name,
            category=product.category or "미분류",
            thumbnail=product.thumbnail or "(없음)",
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.9,
        )

        raw = json.loads(response.choices[0].message.content)
        candidates = [ScriptCandidate.from_dict(c) for c in raw["candidates"]]
        return ScriptSet(product_id=product.id, candidates=candidates)


class MockScriptGenerator:
    """Deterministic generator for tests and --dry-run, no API calls."""

    _TEMPLATES = [
        ("불편함 각도: {name}이 필요했던 상황", "다른 제품이랑 다르게 {name}은 효과가 확실해요", "직접 써봤는데 차이가 바로 느껴졌어요", "아래 쇼핑태그 눌러주세요, 지금 구매하세요"),
        ("매일 {category} 때문에 스트레스였다", "다른 {category} 제품은 효과가 오래 안 가는데", "직접 해봤는데 하루 종일 효과가 유지됐어요", "아래 쇼핑태그 눌러주세요, 지금 구매하세요"),
        ("{name} 써보기 전엔 몰랐다", "비슷한 제품들이랑 비교해봤는데 압도적이에요", "직접 비교해봤는데 {name}이 제일 낫더라고요", "팔로우하고 놓치지 마세요"),
        ("{category} 제품 수십 개 써봤는데", "{name}은 성분부터 달라요", "직접 전후 비교 사진 찍어봤는데 차이가 확실해요", "아래 쇼핑태그 눌러주세요, 지금 구매하세요"),
        ("이 가격에 이 퀄리티 실화야?", "{name} 지금 이 가격 절대 안 올라요", "직접 써보고 주변에 다 추천하고 있어요", "지금 바로 구매하세요, 품절 전에"),
    ]

    def generate(self, product: Product) -> ScriptSet:
        candidates = [
            ScriptCandidate(
                id=i + 1,
                attention=att.format(name=product.name, category=product.category or "상품"),
                interest=interest.format(name=product.name, category=product.category or "상품"),
                desire=desire.format(name=product.name, category=product.category or "상품"),
                action=action,
            )
            for i, (att, interest, desire, action) in enumerate(self._TEMPLATES)
        ]
        return ScriptSet(product_id=product.id, candidates=candidates)


def build_script_generator(api_key: str, model: str, dry_run: bool) -> ScriptGeneratorProtocol:
    if dry_run:
        return MockScriptGenerator()
    return OpenAIScriptGenerator(api_key=api_key, model=model)
