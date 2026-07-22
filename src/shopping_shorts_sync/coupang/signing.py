"""HMAC request signing for the Coupang Partners Open API.

NOTE: the exact header format below (``CEA algorithm=HmacSHA256, ...``) matches
the scheme Coupang's other open APIs are documented to use, but has not been
verified against the real Partners API response (no API key has been issued
yet). Re-check this against the official docs once real credentials arrive —
see docs/CALIBRATION.md.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

SIGNED_DATE_FORMAT = "%y%m%dT%H%M%SZ"


def signed_date_now() -> str:
    return datetime.now(timezone.utc).strftime(SIGNED_DATE_FORMAT)


def build_authorization_header(
    method: str,
    path_with_query: str,
    access_key: str,
    secret_key: str,
    signed_date: str | None = None,
) -> str:
    if not access_key or not secret_key:
        raise ValueError("access_key and secret_key are required to sign a request")

    signed_date = signed_date or signed_date_now()
    message = f"{signed_date}{method.upper()}{path_with_query}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return (
        f"CEA algorithm=HmacSHA256, access-key={access_key}, "
        f"signed-date={signed_date}, signature={signature}"
    )
