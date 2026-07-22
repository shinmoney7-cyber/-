from __future__ import annotations

from ..config import Config
from .mock_client import MockTypecastClient
from .typecast_client import TypecastClient


def build_tts_client(config: Config):
    if config.typecast_mode == "live":
        return TypecastClient(config.typecast_api_key)
    return MockTypecastClient()
