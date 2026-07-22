import hashlib
import hmac

from shopping_shorts_sync.coupang.signing import build_authorization_header


def test_authorization_header_format():
    header = build_authorization_header(
        method="POST",
        path_with_query="/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink",
        access_key="AK123",
        secret_key="SK456",
        signed_date="260722T120000Z",
    )

    assert header.startswith("CEA algorithm=HmacSHA256, ")
    assert "access-key=AK123" in header
    assert "signed-date=260722T120000Z" in header
    assert "signature=" in header


def test_signature_matches_hand_computed_hmac():
    signed_date = "260722T120000Z"
    method = "POST"
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    secret_key = "SK456"

    header = build_authorization_header(
        method=method,
        path_with_query=path,
        access_key="AK123",
        secret_key=secret_key,
        signed_date=signed_date,
    )

    expected_message = f"{signed_date}{method}{path}"
    expected_signature = hmac.new(
        secret_key.encode("utf-8"), expected_message.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    assert f"signature={expected_signature}" in header


def test_missing_credentials_raises():
    import pytest

    with pytest.raises(ValueError):
        build_authorization_header("POST", "/x", "", "secret")
