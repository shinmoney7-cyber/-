from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REDACT_KEYS = {"coupang_secret_key", "coupang_access_key", "inpock_password", "youtube_api_key", "typecast_api_key"}


@dataclass(frozen=True)
class Config:
    coupang_access_key: str
    coupang_secret_key: str
    coupang_api_mode: str
    coupang_batch_size: int

    inpock_email: str
    inpock_password: str
    inpock_headless: bool

    naver_client_id: str
    naver_client_secret: str

    youtube_api_key: str

    typecast_api_key: str
    typecast_mode: str
    typecast_actor_id: str
    typecast_speed: float

    playwright_chromium_path: str
    state_file_path: str
    scripts_dir: str
    log_level: str

    def redacted_dict(self) -> dict:
        d = self.__dict__.copy()
        for key in _REDACT_KEYS:
            if d.get(key):
                d[key] = "***REDACTED***"
        return d


def load_config(env_file: str | None = None) -> Config:
    load_dotenv(env_file)  # no-op if the file doesn't exist; real env vars still apply

    return Config(
        coupang_access_key=os.environ.get("COUPANG_ACCESS_KEY", ""),
        coupang_secret_key=os.environ.get("COUPANG_SECRET_KEY", ""),
        coupang_api_mode=os.environ.get("COUPANG_API_MODE", "mock"),
        coupang_batch_size=int(os.environ.get("COUPANG_BATCH_SIZE", "50")),
        inpock_email=os.environ.get("INPOCK_EMAIL", ""),
        inpock_password=os.environ.get("INPOCK_PASSWORD", ""),
        inpock_headless=os.environ.get("INPOCK_HEADLESS", "true").strip().lower() in ("1", "true", "yes"),
        naver_client_id=os.environ.get("NAVER_CLIENT_ID", ""),
        naver_client_secret=os.environ.get("NAVER_CLIENT_SECRET", ""),
        youtube_api_key=os.environ.get("YOUTUBE_API_KEY", ""),
        typecast_api_key=os.environ.get("TYPECAST_API_KEY", ""),
        typecast_mode=os.environ.get("TYPECAST_MODE", "mock"),
        typecast_actor_id=os.environ.get("TYPECAST_ACTOR_ID", "예슬"),
        typecast_speed=float(os.environ.get("TYPECAST_SPEED", "1.2")),
        playwright_chromium_path=os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium"),
        state_file_path=os.environ.get("STATE_FILE_PATH", "data/state.json"),
        scripts_dir=os.environ.get("SCRIPTS_DIR", "data/scripts"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
