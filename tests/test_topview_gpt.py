import pytest

from shopping_shorts_sync.topview_gpt import (
    OPENAI_API_URL,
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

_MOCK_SCRIPT = "[0-3초] 와, 이게 진짜야? / [3-12초] 흡입력 최강 무선 청소기 / [12-15초] 지금 바로 구매하세요!"


def _mock_openai_response(requests_mock):
    requests_mock.post(
        OPENAI_API_URL,
        json={
            "choices": [{"message": {"content": _MOCK_SCRIPT}}]
        },
    )


def test_generate_script_returns_topview_script(requests_mock):
    _mock_openai_response(requests_mock)

    result = generate_script(**_PRODUCT, api_key="test-key")

    assert isinstance(result, TopviewScript)
    assert result.product_name == "무선 청소기 PRO"
    assert result.script == _MOCK_SCRIPT
    assert result.topview_payload["duration_seconds"] == 15
    assert result.topview_payload["product_url"] == _PRODUCT["product_url"]
    assert result.topview_payload["image_url"] == _PRODUCT["image_url"]


def test_generate_script_payload_contains_script(requests_mock):
    _mock_openai_response(requests_mock)
    result = generate_script(**_PRODUCT, api_key="test-key")
    assert result.topview_payload["script"] == _MOCK_SCRIPT


def test_missing_api_key_raises():
    with pytest.raises(TopviewGptError, match="OPENAI_API_KEY"):
        generate_script(**_PRODUCT, api_key="")


def test_api_error_in_body_raises(requests_mock):
    requests_mock.post(
        OPENAI_API_URL,
        json={"error": {"message": "quota exceeded"}},
    )
    with pytest.raises(TopviewGptError, match="quota exceeded"):
        generate_script(**_PRODUCT, api_key="test-key")


def test_http_error_raises(requests_mock):
    requests_mock.post(OPENAI_API_URL, status_code=401, json={"error": "Unauthorized"})
    with pytest.raises(Exception):
        generate_script(**_PRODUCT, api_key="bad-key")
