"""HMAC request signing for the Naver 검색광고(SearchAd) API.

Spec per Naver's SearchAd API developer guide (searchad.naver.com ->
도구 -> API 사용 관리): sign `f"{timestamp}.{method}.{uri}"` (uri is the
path only, no domain/query string) with the issued secret key, base64
the result. Verified working end-to-end against the live API (deployed
on Render) -- see docs/CALIBRATION.md.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time


def timestamp_now_ms() -> str:
    return str(int(time.time() * 1000))


def build_signature(secret_key: str, timestamp: str, method: str, uri: str) -> str:
    if not secret_key:
        raise ValueError("secret_key is required to sign a request")

    message = f"{timestamp}.{method.upper()}.{uri}"
    digest = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def build_headers(api_key: str, secret_key: str, customer_id: str, method: str, uri: str) -> dict:
    if not api_key or not customer_id:
        raise ValueError("api_key and customer_id are required to sign a request")

    timestamp = timestamp_now_ms()
    return {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": customer_id,
        "X-Signature": build_signature(secret_key, timestamp, method, uri),
    }
