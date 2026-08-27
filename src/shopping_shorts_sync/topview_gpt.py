"""TopView.ai + OpenAI GPT integration.

Generates a 15-second shopping-shorts script via GPT, then formats it as a
TopView-ready payload. TopView.ai has no public API; the payload is returned
for manual submission or RPA-based upload.

Requires: OPENAI_API_KEY environment variable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

_SYSTEM_PROMPT = (
    "당신은 인스타 릴스·유튜브 쇼츠·틱톡용 15초 쇼핑 숏츠 대본 전문가입니다. "
    "사용자가 제품 정보를 주면 15초 안에 끝나는 한국어 대본을 만들어주세요. "
    "형식: [0-3초] 인트로 후킹 / [3-12초] 제품 핵심 포인트 / [12-15초] CTA. "
    "자막 텍스트, 배경음악 분위기, 화면 구성을 간략히 포함하세요."
)


class TopviewGptError(RuntimeError):
    pass


@dataclass
class TopviewScript:
    product_name: str
    product_url: str
    image_url: str
    script: str          # GPT가 생성한 15초 대본
    topview_payload: dict  # TopView 입력용 딕셔너리


def generate_script(
    product_name: str,
    product_url: str,
    image_url: str,
    price: str | None = None,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    timeout: float = 30.0,
) -> TopviewScript:
    """GPT로 15초 쇼핑 숏츠 대본을 생성하고 TopView 입력 패키지를 반환합니다."""
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise TopviewGptError("OPENAI_API_KEY is required")

    price_line = f"가격: {price}원" if price else ""
    user_content = (
        f"제품명: {product_name}\n"
        f"제품 URL: {product_url}\n"
        f"이미지 URL: {image_url}\n"
        f"{price_line}\n"
        "위 제품의 15초 쇼핑 숏츠 대본을 작성해주세요."
    )

    response = requests.post(
        OPENAI_API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 600,
            "temperature": 0.8,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()

    if "error" in body:
        raise TopviewGptError(body["error"].get("message", "unknown OpenAI error"))

    script_text = body["choices"][0]["message"]["content"].strip()

    topview_payload = {
        "product_name": product_name,
        "product_url": product_url,
        "image_url": image_url,
        "script": script_text,
        "duration_seconds": 15,
    }

    return TopviewScript(
        product_name=product_name,
        product_url=product_url,
        image_url=image_url,
        script=script_text,
        topview_payload=topview_payload,
    )
