"""TopView.ai + Google Gemini integration.

Uses the same GOOGLE_API_KEY as GoogleShopClient — no separate API key needed.
Generates a 15-second shopping-shorts script, subtitles, hashtags, and BGM
suggestion via Gemini, then formats everything as a TopView-ready payload.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import requests

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/{model}:generateContent"
)
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

_SYSTEM_PROMPT = """당신은 인스타 릴스·유튜브 쇼츠·틱톡용 15초 쇼핑 숏츠 콘텐츠 전문가입니다.
제품 정보를 받으면 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

{
  "script": {
    "scene1": {"time": "0-3초", "action": "화면 구성 설명", "subtitle": "자막 텍스트", "hook": "후킹 포인트"},
    "scene2": {"time": "3-12초", "action": "화면 구성 설명", "subtitle": "자막 텍스트", "key_points": ["포인트1", "포인트2"]},
    "scene3": {"time": "12-15초", "action": "화면 구성 설명", "subtitle": "자막 텍스트", "cta": "CTA 문구"}
  },
  "subtitles": ["씬1 자막", "씬2 자막", "씬3 자막"],
  "bgm": "배경음악 분위기 설명 (예: 경쾌한 비트 BPM 120, 팝/일렉트로닉 분위기)",
  "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5",
               "#해시태그6", "#해시태그7", "#해시태그8", "#해시태그9", "#해시태그10"]
}"""


class TopviewGptError(RuntimeError):
    pass


@dataclass
class TopviewScript:
    product_name: str
    product_url: str
    image_url: str
    script: dict           # 씬별 구조화 대본
    subtitles: list[str]   # 씬별 자막
    bgm: str               # 배경음악 제안
    hashtags: list[str]    # 해시태그 10개+
    topview_payload: dict  # TopView 입력용 패키지


def _mock_script(product_name: str, product_url: str, image_url: str) -> TopviewScript:
    script = {
        "scene1": {"time": "0-3초", "action": "제품 클로즈업", "subtitle": f"이거 실화?", "hook": "강한 후킹"},
        "scene2": {"time": "3-12초", "action": "사용 장면", "subtitle": f"{product_name} 핵심 포인트", "key_points": ["품질", "가성비"]},
        "scene3": {"time": "12-15초", "action": "링크 유도", "subtitle": "지금 바로 구매", "cta": "링크 클릭"},
    }
    subtitles = ["이거 실화?", f"{product_name} 핵심 포인트", "지금 바로 구매"]
    hashtags = ["#쇼핑", "#할인", "#추천", "#숏츠", "#틱톡", "#인스타", "#가성비", "#리뷰", "#언박싱", "#구매"]
    bgm = "경쾌한 팝 비트 BPM 120 (dry-run 모의 데이터)"
    return TopviewScript(
        product_name=product_name, product_url=product_url, image_url=image_url,
        script=script, subtitles=subtitles, bgm=bgm, hashtags=hashtags,
        topview_payload={"product_name": product_name, "product_url": product_url,
                         "image_url": image_url, "script": script, "subtitles": subtitles,
                         "bgm": bgm, "hashtags": hashtags, "duration_seconds": 15},
    )


def generate_script(
    product_name: str,
    product_url: str,
    image_url: str,
    price: str | None = None,
    model: str = "gemini-2.0-flash",
    api_key: str | None = None,
    timeout: float = 30.0,
    dry_run: bool = False,
) -> TopviewScript:
    """Gemini로 15초 쇼핑 숏츠 패키지(대본·자막·해시태그·BGM)를 생성합니다.

    GOOGLE_API_KEY 하나만 있으면 됩니다 — OpenAI 키 불필요.
    dry_run=True 이면 API를 호출하지 않고 모의 데이터를 반환합니다.
    """
    if dry_run:
        return _mock_script(product_name, product_url, image_url)

    key = api_key or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise TopviewGptError("GOOGLE_API_KEY is required")

    price_line = f"가격: {price}원" if price else "가격: 미정"
    user_text = (
        f"제품명: {product_name}\n"
        f"제품 URL: {product_url}\n"
        f"이미지 URL: {image_url}\n"
        f"{price_line}\n\n"
        "위 제품의 15초 쇼핑 숏츠 패키지를 JSON으로 만들어주세요."
    )

    url = GEMINI_API_URL.format(model=model)
    response = requests.post(
        url,
        params={"key": key},
        json={
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()

    if "error" in body:
        raise TopviewGptError(body["error"].get("message", "unknown Gemini error"))

    raw_text = body["candidates"][0]["content"]["parts"][0]["text"]

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise TopviewGptError(f"Gemini returned non-JSON: {raw_text[:200]}") from exc

    script = data.get("script", {})
    subtitles = data.get("subtitles", [])
    bgm = data.get("bgm", "")
    hashtags = data.get("hashtags", [])

    topview_payload = {
        "product_name": product_name,
        "product_url": product_url,
        "image_url": image_url,
        "script_scene1": script.get("scene1", {}),
        "script_scene2": script.get("scene2", {}),
        "script_scene3": script.get("scene3", {}),
        "subtitles": subtitles,
        "bgm": bgm,
        "hashtags": hashtags,
        "duration_seconds": 15,
    }

    return TopviewScript(
        product_name=product_name,
        product_url=product_url,
        image_url=image_url,
        script=script,
        subtitles=subtitles,
        bgm=bgm,
        hashtags=hashtags,
        topview_payload=topview_payload,
    )


def generate_script_gpt(
    product_name: str,
    product_url: str,
    image_url: str,
    price: str | None = None,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    timeout: float = 30.0,
    dry_run: bool = False,
) -> TopviewScript:
    """OpenAI GPT로 15초 쇼핑 숏츠 패키지를 생성합니다.

    OPENAI_API_KEY가 필요합니다.
    dry_run=True 이면 API를 호출하지 않고 모의 데이터를 반환합니다.
    """
    if dry_run:
        return _mock_script(product_name, product_url, image_url)

    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise TopviewGptError("OPENAI_API_KEY is required")

    price_line = f"가격: {price}원" if price else "가격: 미정"
    user_text = (
        f"제품명: {product_name}\n"
        f"제품 URL: {product_url}\n"
        f"이미지 URL: {image_url}\n"
        f"{price_line}\n\n"
        "위 제품의 15초 쇼핑 숏츠 패키지를 JSON으로 만들어주세요."
    )

    response = requests.post(
        OPENAI_API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.8,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()

    if "error" in body:
        raise TopviewGptError(body["error"].get("message", "unknown OpenAI error"))

    raw_text = body["choices"][0]["message"]["content"]

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise TopviewGptError(f"OpenAI returned non-JSON: {raw_text[:200]}") from exc

    script = data.get("script", {})
    subtitles = data.get("subtitles", [])
    bgm = data.get("bgm", "")
    hashtags = data.get("hashtags", [])

    topview_payload = {
        "product_name": product_name,
        "product_url": product_url,
        "image_url": image_url,
        "script_scene1": script.get("scene1", {}),
        "script_scene2": script.get("scene2", {}),
        "script_scene3": script.get("scene3", {}),
        "subtitles": subtitles,
        "bgm": bgm,
        "hashtags": hashtags,
        "duration_seconds": 15,
    }

    return TopviewScript(
        product_name=product_name,
        product_url=product_url,
        image_url=image_url,
        script=script,
        subtitles=subtitles,
        bgm=bgm,
        hashtags=hashtags,
        topview_payload=topview_payload,
    )
