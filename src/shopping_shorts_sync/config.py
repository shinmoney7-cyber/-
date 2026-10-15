from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REDACT_KEYS = {
    "coupang_secret_key",
    "coupang_access_key",
    "inpock_password",
    "higgsfield_credential",
    "topview_api_key",
}


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

    video_provider: str
    video_duration: int
    video_output_dir: str
    higgsfield_credential: str
    higgsfield_base_url: str
    higgsfield_video_model: str
    topview_uid: str
    topview_api_key: str
    topview_base_url: str
    topview_video_model: str

    playwright_chromium_path: str
    state_file_path: str
    log_level: str

    def redacted_dict(self) -> dict:
        d = self.__dict__.copy()
        for key in _REDACT_KEYS:
            if d.get(key):
                d[key] = "***REDACTED***"
        return d


def _higgsfield_credential() -> str:
    """Same precedence as the official SDK: HF_KEY, else HF_API_KEY:HF_API_SECRET."""
    if os.environ.get("HF_KEY"):
        return os.environ["HF_KEY"]
    key = os.environ.get("HIGGSFIELD_API_KEY") or os.environ.get("HF_API_KEY", "")
    secret = os.environ.get("HIGGSFIELD_API_SECRET") or os.environ.get("HF_API_SECRET", "")
    return f"{key}:{secret}" if key and secret else ""


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
        video_provider=os.environ.get("VIDEO_PROVIDER", "higgsfield"),
        video_duration=int(os.environ.get("VIDEO_DURATION", "5")),
        video_output_dir=os.environ.get("VIDEO_OUTPUT_DIR", "data/videos"),
        higgsfield_credential=_higgsfield_credential(),
        higgsfield_base_url=os.environ.get("HIGGSFIELD_BASE_URL", "https://api.higgsfield.ai"),
        higgsfield_video_model=os.environ.get("HIGGSFIELD_VIDEO_MODEL", "higgsfield-ai/dop/standard"),
        topview_uid=os.environ.get("TOPVIEW_UID", ""),
        topview_api_key=os.environ.get("TOPVIEW_API_KEY", ""),
        topview_base_url=os.environ.get("TOPVIEW_BASE_URL", "https://api.topview.ai"),
        topview_video_model=os.environ.get("TOPVIEW_VIDEO_MODEL", "Topview Pro"),
        playwright_chromium_path=os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium"),
        state_file_path=os.environ.get("STATE_FILE_PATH", "data/state.json"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
