import json

import pytest

from shopping_shorts_sync.topview_gpt import (
    GEMINI_API_URL,
    TopviewGptError,
    TopviewScript,
    generate_script,
)

_PRODUCT = dict(
    product_name="무선 청소기 PRO",
    product_url="https://link.coupang.com/a/abc",
    image_url="https://example.com/cleaner.jpg",
    price="59000",
)

_MOCK_DATA = {
    "script": {
        "scene1": {"time": "0-3초", "action": "먼지 앞에 청소기", "subtitle": "이거 실화임?", "hook": "강한 흡입력"},
        "scene2": {"time": "3-12초", "action": "카펫·소파·틈새 청소", "subtitle": "흡입력 25,000Pa / 배터리 60분", "key_points": ["강력 흡입", "60분 지속"]},
        "scene3": {"time": "12-15초", "action": "링크 클릭 유도", "subtitle": "지금 59,000원", "cta": "지금 바로 구매"},
    },
    "subtitles": ["이거 실화임?", "흡입력 25,000Pa / 배터리 60분", "지금 59,000원"],
    "bgm": "경쾌한 비트 BPM 120, 팝 분위기",
    "hashtags": [
        "#무선청소기", "#청소기추천", "#쇼핑", "#할인", "#가성비",
        "#홈리빙", "#청소", "#생활가전", "#숏츠", "#쿠팡",
    ],
}

_MOCK_URL = GEMINI_API_URL.format(model="gemini-2.0-flash")


def _gemini_response(data: dict) -> dict:
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(data, ensure_ascii=False)}]}}
        ]
    }


def test_generate_script_returns_topview_script(requests_mock):
    requests_mock.post(_MOCK_URL, json=_gemini_response(_MOCK_DATA))

    result = generate_script(**_PRODUCT, api_key="test-key")

    assert isinstance(result, TopviewScript)
    assert result.product_name == "무선 청소기 PRO"
    assert result.subtitles == _MOCK_DATA["subtitles"]
    assert result.bgm == _MOCK_DATA["bgm"]
    assert len(result.hashtags) == 10
    assert result.topview_payload["duration_seconds"] == 15


def test_payload_contains_all_scenes(requests_mock):
    requests_mock.post(_MOCK_URL, json=_gemini_response(_MOCK_DATA))
    result = generate_script(**_PRODUCT, api_key="test-key")

    payload = result.topview_payload
    assert "script_scene1" in payload
    assert "script_scene2" in payload
    assert "script_scene3" in payload
    assert payload["subtitles"] == _MOCK_DATA["subtitles"]
    assert payload["hashtags"] == _MOCK_DATA["hashtags"]


def test_missing_api_key_raises():
    with pytest.raises(TopviewGptError, match="GOOGLE_API_KEY"):
        generate_script(**_PRODUCT, api_key="")


def test_gemini_error_in_body_raises(requests_mock):
    requests_mock.post(_MOCK_URL, json={"error": {"message": "quota exceeded"}})
    with pytest.raises(TopviewGptError, match="quota exceeded"):
        generate_script(**_PRODUCT, api_key="test-key")


def test_invalid_json_from_gemini_raises(requests_mock):
    bad_response = {
        "candidates": [{"content": {"parts": [{"text": "not json at all"}]}}]
    }
    requests_mock.post(_MOCK_URL, json=bad_response)
    with pytest.raises(TopviewGptError, match="non-JSON"):
        generate_script(**_PRODUCT, api_key="test-key")


def test_http_error_raises(requests_mock):
    requests_mock.post(_MOCK_URL, status_code=403, json={"error": "Forbidden"})
    with pytest.raises(Exception):
        generate_script(**_PRODUCT, api_key="bad-key")
