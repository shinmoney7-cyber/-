"""AI-assisted AIDA script generation for product shorts.

Generates 5 script candidates per product using the Claude API.
Requires ANTHROPIC_API_KEY env var.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import requests

log = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class ScriptCandidate:
    id: int
    attention: str
    interest: str
    desire: str
    action: str

    @property
    def full_text(self) -> str:
        return f"{self.attention}\n{self.interest}\n{self.desire}\n{self.action}"


class ScriptAI:
    """Generate AIDA script candidates via Claude API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model

    def generate_candidates(
        self,
        product_name: str,
        category: str,
        thumbnail_url: str = "",
        platform: str = "tiktok",
        target_audience: str = "2030 여성",
        tone: str = "활기차고 친근한",
        count: int = 5,
    ) -> list[ScriptCandidate]:
        system_prompt = (
            "당신은 한국 쇼핑 숏폼 영상 대본 전문가입니다. "
            "AIDA(주의-흥미-욕망-행동) 구조로 15~30초 분량의 대본을 작성합니다. "
            "각 파트는 1~2문장으로 짧고 임팩트 있게 씁니다."
        )
        user_prompt = f"""
다음 상품의 쇼핑 숏폼 대본 후보 {count}개를 JSON 배열로 생성하세요.

상품명: {product_name}
카테고리: {category}
플랫폼: {platform}
타겟: {target_audience}
톤앤매너: {tone}

JSON 형식:
[
  {{
    "id": 1,
    "attention": "시청자 주의를 끄는 첫 문장",
    "interest": "상품 특징/장점 소개",
    "desire": "구매 욕구를 자극하는 감성 카피",
    "action": "CTA 문구 (링크 클릭/쿠팡 구매 유도)"
  }},
  ...
]

JSON만 출력하세요.
""".strip()

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        try:
            resp = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"].strip()

            # strip markdown fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            candidates_raw = json.loads(text)
            return [
                ScriptCandidate(
                    id=c.get("id", i + 1),
                    attention=c.get("attention", ""),
                    interest=c.get("interest", ""),
                    desire=c.get("desire", ""),
                    action=c.get("action", ""),
                )
                for i, c in enumerate(candidates_raw[:count])
            ]

        except Exception as exc:
            log.exception("script generation failed")
            return []

    def generate_hashtags(
        self,
        product_name: str,
        category: str,
        platform: str = "tiktok",
        count: int = 20,
    ) -> list[str]:
        """Generate platform-optimised hashtags for a product."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "messages": [{
                "role": "user",
                "content": (
                    f"{platform}용 해시태그 {count}개를 쉼표로 구분해서 출력하세요. "
                    f"#없이. 상품: {product_name}, 카테고리: {category}. "
                    f"인기 태그와 틈새 태그를 섞어 주세요."
                ),
            }],
        }

        try:
            resp = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"]
            return [t.strip().lstrip("#") for t in text.split(",") if t.strip()][:count]
        except Exception as exc:
            log.warning("hashtag generation failed: %s", exc)
            return []


    def generate_desire_script_15s(
        self,
        product_name: str,
        brand: str,
        category: str,
        sold_count: int = 0,
        sold_period: str = "7일",
        local_name: str = "",
        local_price_krw: int = 0,
        platform: str = "tiktok",
    ) -> str:
        """Generate 15-second desire/욕망-focused script (1.2x speed = ~40 words)."""
        display_name = local_name or product_name
        sold_str = f"{sold_count:,}" if sold_count else ""
        price_str = f"쿠팡 {local_price_krw:,}원" if local_price_krw else "쿠팡 최저가"

        system_prompt = (
            "당신은 한국 틱톡/숏폼 영상 대본 전문가입니다. "
            "15초, 1.2배속 기준 약 40~50자 분량의 짧은 대본을 작성합니다. "
            "욕망(FOMO, 사회적 증명, 변화 전후)을 극도로 자극하는 카피를 씁니다. "
            "이모지 1~2개 포함. 말줄임표나 과도한 느낌표 없이 자연스럽게."
        )
        prompt = f"""
상품명: {display_name} ({brand})
카테고리: {category}
{f'글로벌 판매: {sold_str}개 ({sold_period} 기준)' if sold_str else ''}
가격: {price_str}
플랫폼: {platform}

4파트 15초 대본을 작성하세요 (각 파트 하나의 짧은 문장):
[0-3초] 훅: 욕망/충격 유발 (예: "이거 없으면 손해!")
[3-8초] 욕구: 변화/효과/FOMO (예: "피부가 달라지는 걸 느꼈어요")
[8-12초] 증명: 숫자/사실 (예: "글로벌 100만개 판매")
[12-15초] CTA: "설명란 링크 → {price_str}"

대본만 출력 (JSON 불필요):
""".strip()

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            resp = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
        except Exception as exc:
            log.warning("15s desire script generation failed: %s", exc)
            return self._fallback_desire_script(display_name, brand, sold_str, sold_period, price_str)

    def _fallback_desire_script(
        self, name: str, brand: str, sold_str: str, period: str, price: str
    ) -> str:
        hook = f"이거 모르면 진짜 손해예요! ✨"
        desire = f"{name}, 써본 사람들은 다 알아요"
        proof = f"글로벌 {sold_str}개 팔린 {brand}" if sold_str else f"{brand} 인기 1위"
        cta = f"지금 설명란 링크 클릭! {price}"
        return f"{hook}\n{desire}\n{proof}\n{cta}"


class MockScriptAI(ScriptAI):
    def __init__(self):
        self.api_key = "mock"
        self.model = DEFAULT_MODEL

    def generate_candidates(self, product_name, category, **kwargs):
        log.info("[MOCK] ScriptAI: generating 5 candidates for %s", product_name)
        return [
            ScriptCandidate(
                id=i + 1,
                attention=f"[후보{i+1}] 이거 진짜 대박이에요! {product_name}",
                interest=f"사용해보니 {category} 중 최고예요",
                desire="지금 당장 사고 싶어지는 퀄리티",
                action="링크 클릭해서 쿠팡에서 확인하세요!",
            )
            for i in range(5)
        ]

    def generate_desire_script_15s(self, product_name, brand, category, sold_count=0,
                                    sold_period="7일", local_name="", local_price_krw=0, **kwargs):
        display = local_name or product_name
        sold = f"{sold_count:,}" if sold_count else "수백만"
        price = f"쿠팡 {local_price_krw:,}원" if local_price_krw else "쿠팡 최저가"
        return (
            f"이거 모르면 진짜 손해예요! ✨\n"
            f"{display}, 한번 써보면 못 끊어요\n"
            f"글로벌 {sold}개 팔린 {brand}\n"
            f"지금 설명란 링크 클릭! {price}"
        )

    def generate_hashtags(self, product_name, category, **kwargs):
        return ["쿠팡추천", "쇼핑추천", category.replace(" ", ""), product_name.replace(" ", "")]
