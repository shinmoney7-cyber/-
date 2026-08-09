from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REDACT_KEYS = {
    "coupang_secret_key",
    "coupang_access_key",
    "inpock_password",
    "meta_mom_moneytip_access_token",
    "meta_showpingkkultem_access_token",
    "meta_haru_moneytip_access_token",
    "meta_app_secret",
    "naver_tts_client_secret",
}


@dataclass(frozen=True)
class Config:
    # ── Coupang Partners ───────────────────────────────────────────────────
    coupang_access_key: str
    coupang_secret_key: str
    coupang_api_mode: str
    coupang_batch_size: int

    # ── Inpock RPA ─────────────────────────────────────────────────────────
    inpock_email: str
    inpock_password: str
    inpock_headless: bool

    # ── Naver Shopping search ──────────────────────────────────────────────
    naver_client_id: str
    naver_client_secret: str

    # ── Playwright ─────────────────────────────────────────────────────────
    playwright_chromium_path: str
    state_file_path: str
    log_level: str

    # ── Meta Developer App ─────────────────────────────────────────────────
    meta_app_id: str
    meta_app_secret: str
    meta_api_version: str
    meta_api_mode: str             # mock | live

    # ── Meta accounts ──────────────────────────────────────────────────────
    meta_mom_moneytip_ig_user_id: str
    meta_mom_moneytip_threads_user_id: str
    meta_mom_moneytip_access_token: str

    meta_showpingkkultem_ig_user_id: str
    meta_showpingkkultem_threads_user_id: str
    meta_showpingkkultem_access_token: str

    meta_haru_moneytip_ig_user_id: str
    meta_haru_moneytip_threads_user_id: str
    meta_haru_moneytip_access_token: str

    # ── Video storage ──────────────────────────────────────────────────────
    meta_video_bucket_url: str

    # ── TTS (Naver Clova Voice) ────────────────────────────────────────────
    naver_tts_client_id: str
    naver_tts_client_secret: str
    naver_tts_speaker: str

    # ── Content output ─────────────────────────────────────────────────────
    content_output_dir: str
    publish_state_file_path: str

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
        playwright_chromium_path=os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium"),
        state_file_path=os.environ.get("STATE_FILE_PATH", "data/state.json"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        # Meta
        meta_app_id=os.environ.get("META_APP_ID", ""),
        meta_app_secret=os.environ.get("META_APP_SECRET", ""),
        meta_api_version=os.environ.get("META_API_VERSION", "v21.0"),
        meta_api_mode=os.environ.get("META_API_MODE", "mock"),
        # Accounts
        meta_mom_moneytip_ig_user_id=os.environ.get("META_MOM_MONEYTIP_IG_USER_ID", ""),
        meta_mom_moneytip_threads_user_id=os.environ.get("META_MOM_MONEYTIP_THREADS_USER_ID", ""),
        meta_mom_moneytip_access_token=os.environ.get("META_MOM_MONEYTIP_ACCESS_TOKEN", ""),
        meta_showpingkkultem_ig_user_id=os.environ.get("META_SHOWPINGKKULTEM_IG_USER_ID", ""),
        meta_showpingkkultem_threads_user_id=os.environ.get("META_SHOWPINGKKULTEM_THREADS_USER_ID", ""),
        meta_showpingkkultem_access_token=os.environ.get("META_SHOWPINGKKULTEM_ACCESS_TOKEN", ""),
        meta_haru_moneytip_ig_user_id=os.environ.get("META_HARU_MONEYTIP_IG_USER_ID", ""),
        meta_haru_moneytip_threads_user_id=os.environ.get("META_HARU_MONEYTIP_THREADS_USER_ID", ""),
        meta_haru_moneytip_access_token=os.environ.get("META_HARU_MONEYTIP_ACCESS_TOKEN", ""),
        # Storage
        meta_video_bucket_url=os.environ.get("META_VIDEO_BUCKET_URL", ""),
        # TTS
        naver_tts_client_id=os.environ.get("NAVER_TTS_CLIENT_ID", ""),
        naver_tts_client_secret=os.environ.get("NAVER_TTS_CLIENT_SECRET", ""),
        naver_tts_speaker=os.environ.get("NAVER_TTS_SPEAKER", "nara"),
        # Content
        content_output_dir=os.environ.get("CONTENT_OUTPUT_DIR", "data/content"),
        publish_state_file_path=os.environ.get("PUBLISH_STATE_FILE_PATH", "data/publish_state.json"),
    )
