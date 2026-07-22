from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REDACT_KEYS = {"coupang_secret_key", "coupang_access_key", "inpock_password"}


@dataclass(frozen=True)
class Config:
    coupang_access_key: str
    coupang_secret_key: str
    coupang_api_mode: str
    coupang_batch_size: int

    inpock_email: str
    inpock_password: str
    inpock_headless: bool

    playwright_chromium_path: str
    state_file_path: str
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
        playwright_chromium_path=os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium"),
        state_file_path=os.environ.get("STATE_FILE_PATH", "data/state.json"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
