import json
from pathlib import Path

import pytest

from shopping_shorts_sync.coupang.client import (
    API_HOST,
    DEEPLINK_PATH,
    CoupangApiError,
    CoupangPartnersClient,
)
from shopping_shorts_sync.coupang.mock_client import MockCoupangClient

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_get_deeplinks_success(requests_mock):
    fixture = load_fixture("coupang_deeplink_success.json")
    requests_mock.post(f"{API_HOST}{DEEPLINK_PATH}", json=fixture)

    client = CoupangPartnersClient(access_key="AK", secret_key="SK")
    urls = [item["originalUrl"] for item in fixture["data"]]
    results = client.get_deeplinks(urls)

    assert len(results) == 2
    assert all(r.ok for r in results)
    assert results[0].shorten_url == "https://link.coupang.com/a/mockAbC123"


def test_get_deeplinks_per_item_error_does_not_raise(requests_mock):
    fixture = load_fixture("coupang_deeplink_error.json")
    requests_mock.post(f"{API_HOST}{DEEPLINK_PATH}", json=fixture)

    client = CoupangPartnersClient(access_key="AK", secret_key="SK")
    results = client.get_deeplinks(["https://www.coupang.com/vp/products/0000000000"])

    assert len(results) == 1
    assert results[0].ok is False
    assert results[0].error


def test_get_deeplinks_batches_requests(requests_mock):
    fixture = load_fixture("coupang_deeplink_success.json")
    requests_mock.post(f"{API_HOST}{DEEPLINK_PATH}", json=fixture)

    client = CoupangPartnersClient(access_key="AK", secret_key="SK", batch_size=1)
    client.get_deeplinks(["url-a", "url-b", "url-c"])

    assert requests_mock.call_count == 3


def test_non_zero_rcode_raises(requests_mock):
    requests_mock.post(
        f"{API_HOST}{DEEPLINK_PATH}", json={"rCode": "1", "rMessage": "bad request", "data": []}
    )
    client = CoupangPartnersClient(access_key="AK", secret_key="SK")
    with pytest.raises(CoupangApiError):
        client.get_deeplinks(["https://www.coupang.com/vp/products/1"])


def test_missing_credentials_raises():
    with pytest.raises(CoupangApiError):
        CoupangPartnersClient(access_key="", secret_key="")


def test_mock_client_is_deterministic():
    client = MockCoupangClient()
    url = "https://www.coupang.com/vp/products/1"
    first = client.get_deeplinks([url])[0].shorten_url
    second = client.get_deeplinks([url])[0].shorten_url
    assert first == second
