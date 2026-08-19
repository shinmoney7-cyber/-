from __future__ import annotations

import abc
import logging
import os

import requests

logger = logging.getLogger(__name__)

# Naver Clova Voice API endpoint
_CLOVA_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"
_DEFAULT_SPEAKER = "nara"
_DEFAULT_SPEED = 0
_DEFAULT_PITCH = 0
_DEFAULT_VOLUME = 5
_DEFAULT_FORMAT = "mp3"


class TTSClient(abc.ABC):
    @abc.abstractmethod
    def synthesize(self, text: str, output_path: str) -> str:
        """Write synthesized audio to output_path and return the path."""


class NaverClovaTTS(TTSClient):
    """Korean TTS via Naver Clova Voice (HyperCLOVA studio)."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        speaker: str = _DEFAULT_SPEAKER,
        speed: int = _DEFAULT_SPEED,
        pitch: int = _DEFAULT_PITCH,
        volume: int = _DEFAULT_VOLUME,
        audio_format: str = _DEFAULT_FORMAT,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._speaker = speaker
        self._speed = speed
        self._pitch = pitch
        self._volume = volume
        self._format = audio_format

    def synthesize(self, text: str, output_path: str) -> str:
        headers = {
            "X-NCP-APIGW-API-KEY-ID": self._client_id,
            "X-NCP-APIGW-API-KEY": self._client_secret,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "speaker": self._speaker,
            "volume": str(self._volume),
            "speed": str(self._speed),
            "pitch": str(self._pitch),
            "format": self._format,
            "text": text,
        }
        resp = requests.post(_CLOVA_URL, headers=headers, data=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Clova TTS failed [{resp.status_code}]: {resp.text[:200]}")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)
        logger.info("tts written: %s (%d bytes)", output_path, len(resp.content))
        return output_path


class MockTTSClient(TTSClient):
    """Writes a silent dummy audio file without calling any API."""

    # 1-second silent MP3 (44-byte MPEG header + silence data)
    _SILENT_MP3 = bytes([
        0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])

    def synthesize(self, text: str, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(self._SILENT_MP3 * 100)
        logger.info("mock tts written: %s", output_path)
        return output_path
