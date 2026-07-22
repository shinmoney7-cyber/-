"""Typecast (typecast.ai) TTS API client.

The request/response shape below is best-effort from Typecast's public API
docs as of this project's last update, NOT exercised against the live API
in this environment (network to typecast.ai is blocked here, same as
Naver/Coupang/Daiso/OliveYoung — see docs/CALIBRATION.md). Before --live
use: confirm the endpoint path, auth header, and response field names
against the current Typecast API docs / a real API key, and update
SPEAK_ENDPOINT / the response parsing below if they differ.
"""
from __future__ import annotations

import time

import requests

from .models import TTSResult

BASE_URL = "https://typecast.ai/api"
SPEAK_ENDPOINT = f"{BASE_URL}/speak"
POLL_INTERVAL_SECONDS = 2.0
MAX_POLL_ATTEMPTS = 30


class TypecastApiError(RuntimeError):
    pass


class TypecastClient:
    def __init__(self, api_key: str, timeout: float = 15.0):
        if not api_key:
            raise TypecastApiError("TYPECAST_API_KEY is required in live mode")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def synthesize(self, text: str, actor_id: str, speed: float = 1.2) -> TTSResult:
        response = requests.post(
            SPEAK_ENDPOINT,
            json={"text": text, "lang": "auto", "actor_id": actor_id, "speed_x": speed},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()

        # Typecast's speak endpoint is async: it returns a poll URL first,
        # and the audio download URL only appears once status == "done".
        poll_url = body.get("result", {}).get("speak_v2_url") or body.get("speak_v2_url")
        if poll_url:
            body = self._poll(poll_url)

        audio_url = (
            body.get("result", {}).get("audio_download_url")
            or body.get("audio_download_url")
        )
        if not audio_url:
            raise TypecastApiError(f"no audio_download_url in Typecast response: {body!r}")
        return TTSResult(audio_url=audio_url, actor_id=actor_id)

    def _poll(self, poll_url: str) -> dict:
        for _ in range(MAX_POLL_ATTEMPTS):
            response = requests.get(poll_url, headers=self._headers(), timeout=self.timeout)
            response.raise_for_status()
            body = response.json()
            status = body.get("result", {}).get("status") or body.get("status")
            if status == "done":
                return body
            if status == "failed":
                raise TypecastApiError(f"Typecast synthesis failed: {body!r}")
            time.sleep(POLL_INTERVAL_SECONDS)
        raise TypecastApiError(f"Typecast synthesis timed out polling {poll_url}")
