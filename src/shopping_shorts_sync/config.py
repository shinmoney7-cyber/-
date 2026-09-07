from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REDACT_KEYS = {
    "coupang_secret_key", "coupang_access_key", "inpock_password",
    "tiktok_access_token", "tiktok_client_secret",
    "youtube_client_secret", "youtube_refresh_token",
    "instagram_access_token",
    "naver_blog_access_token",
    "email_password",
    "higgs_api_key",
    "anthropic_api_key",
}


@dataclass(frozen=True)
class Config:
    # Coupang Partners
    coupang_access_key: str
    coupang_secret_key: str
    coupang_api_mode: str
    coupang_batch_size: int

    # Inpock
    inpock_email: str
    inpock_password: str
    inpock_headless: bool

    # Naver Shopping Search
    naver_client_id: str
    naver_client_secret: str

    # TikTok Content Posting API
    tiktok_client_key: str
    tiktok_client_secret: str
    tiktok_access_token: str

    # YouTube Data API v3
    youtube_client_id: str
    youtube_client_secret: str
    youtube_refresh_token: str
    youtube_channel_id: str

    # Instagram Graph API
    instagram_access_token: str
    instagram_business_account_id: str

    # Naver Blog API
    naver_blog_client_id: str
    naver_blog_client_secret: str
    naver_blog_access_token: str
    naver_blog_id: str

    # Email (Gmail SMTP)
    email_sender: str
    email_password: str
    email_smtp_host: str
    email_smtp_port: int
    email_recipients: list

    # Higgs API (video generation)
    higgs_api_key: str

    # Claude API (script generation)
    anthropic_api_key: str

    # Price monitor
    price_monitor_interval_hours: int
    price_drop_threshold_pct: float
    price_history_path: str

    # General
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
    load_dotenv(env_file)

    recipients_raw = os.environ.get("EMAIL_RECIPIENTS", "")
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

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

        tiktok_client_key=os.environ.get("TIKTOK_CLIENT_KEY", ""),
        tiktok_client_secret=os.environ.get("TIKTOK_CLIENT_SECRET", ""),
        tiktok_access_token=os.environ.get("TIKTOK_ACCESS_TOKEN", ""),

        youtube_client_id=os.environ.get("YOUTUBE_CLIENT_ID", ""),
        youtube_client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
        youtube_refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
        youtube_channel_id=os.environ.get("YOUTUBE_CHANNEL_ID", ""),

        instagram_access_token=os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""),
        instagram_business_account_id=os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", ""),

        naver_blog_client_id=os.environ.get("NAVER_BLOG_CLIENT_ID", ""),
        naver_blog_client_secret=os.environ.get("NAVER_BLOG_CLIENT_SECRET", ""),
        naver_blog_access_token=os.environ.get("NAVER_BLOG_ACCESS_TOKEN", ""),
        naver_blog_id=os.environ.get("NAVER_BLOG_ID", ""),

        email_sender=os.environ.get("EMAIL_SENDER", ""),
        email_password=os.environ.get("EMAIL_PASSWORD", ""),
        email_smtp_host=os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com"),
        email_smtp_port=int(os.environ.get("EMAIL_SMTP_PORT", "587")),
        email_recipients=recipients,

        higgs_api_key=os.environ.get("HIGGS_API_KEY", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),

        price_monitor_interval_hours=int(os.environ.get("PRICE_MONITOR_INTERVAL_HOURS", "6")),
        price_drop_threshold_pct=float(os.environ.get("PRICE_DROP_THRESHOLD_PCT", "10")),
        price_history_path=os.environ.get("PRICE_HISTORY_PATH", "data/price_history.json"),

        playwright_chromium_path=os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium"),
        state_file_path=os.environ.get("STATE_FILE_PATH", "data/state.json"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
