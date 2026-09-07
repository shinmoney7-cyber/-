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

    def generate_hashtags(self, product_name, category, **kwargs):
        return ["쿠팡추천", "쇼핑추천", category.replace(" ", ""), product_name.replace(" ", "")]
