from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REDACT_KEYS = {
    "coupang_secret_key",
    "coupang_access_key",
    "inpock_password",
    "instagram_harujin_access_token",
    "instagram_shinjh_access_token",
    "facebook_harujin_page_access_token",
    "facebook_shinjh_page_access_token",
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

    instagram_harujin_user_id: str
    instagram_harujin_access_token: str
    instagram_shinjh_user_id: str
    instagram_shinjh_access_token: str
    instagram_default_cta: str
    instagram_disclaimer: str
    instagram_api_mode: str  # "mock" | "live"
    instagram_schedule_hour: int  # KST hour for default scheduled posting
    instagram_schedule_minute: int
    instagram_webhook_verify_token: str  # arbitrary secret set in Meta webhook config
    instagram_dm_message_template: str  # {deeplink} placeholder
    # Owner's IGSID for preview DMs before scheduling (find via GET /me on the Graph API)
    instagram_harujin_owner_igsid: str
    instagram_shinjh_owner_igsid: str

    # Facebook Page credentials (Page Access Token, not User Access Token).
    # Requires pages_manage_posts + pages_read_engagement permissions.
    facebook_harujin_page_id: str
    facebook_harujin_page_access_token: str
    facebook_shinjh_page_id: str
    facebook_shinjh_page_access_token: str
    facebook_api_mode: str  # "mock" | "live"

    playwright_chromium_path: str
    state_file_path: str
    log_level: str

    def facebook_credentials(self, target_page: str) -> tuple[str, str]:
        """Returns (page_id, page_access_token) for the given target page."""
        if target_page == "harujin":
            return self.facebook_harujin_page_id, self.facebook_harujin_page_access_token
        if target_page == "shinjh":
            return self.facebook_shinjh_page_id, self.facebook_shinjh_page_access_token
        raise ValueError(f"unknown target_page: {target_page!r}")

    def instagram_owner_igsid(self, target_page: str) -> str:
        """Returns the owner's IGSID for the given page (used to send preview DMs)."""
        if target_page == "harujin":
            return self.instagram_harujin_owner_igsid
        if target_page == "shinjh":
            return self.instagram_shinjh_owner_igsid
        raise ValueError(f"unknown target_page: {target_page!r}")

    def instagram_credentials(self, target_page: str) -> tuple[str, str]:
        """Returns (user_id, access_token) for the given target page."""
        if target_page == "harujin":
            return self.instagram_harujin_user_id, self.instagram_harujin_access_token
        if target_page == "shinjh":
            return self.instagram_shinjh_user_id, self.instagram_shinjh_access_token
        raise ValueError(f"unknown target_page: {target_page!r}")

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
        instagram_harujin_user_id=os.environ.get("INSTAGRAM_HARUJIN_USER_ID", ""),
        instagram_harujin_access_token=os.environ.get("INSTAGRAM_HARUJIN_ACCESS_TOKEN", ""),
        instagram_shinjh_user_id=os.environ.get("INSTAGRAM_SHINJH_USER_ID", ""),
        instagram_shinjh_access_token=os.environ.get("INSTAGRAM_SHINJH_ACCESS_TOKEN", ""),
        instagram_default_cta=os.environ.get(
            "INSTAGRAM_DEFAULT_CTA",
            "프로필 링크에서 구매하기 👆",
        ),
        instagram_disclaimer=os.environ.get(
            "INSTAGRAM_DISCLAIMER",
            "이 포스팅은 쿠팡파트너스 활동의 일환으로 일정액의 수수료를 제공받을 수 있습니다.",
        ),
        instagram_api_mode=os.environ.get("INSTAGRAM_API_MODE", "mock"),
        instagram_schedule_hour=int(os.environ.get("INSTAGRAM_SCHEDULE_HOUR", "9")),
        instagram_schedule_minute=int(os.environ.get("INSTAGRAM_SCHEDULE_MINUTE", "0")),
        instagram_webhook_verify_token=os.environ.get("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", ""),
        instagram_dm_message_template=os.environ.get(
            "INSTAGRAM_DM_MESSAGE_TEMPLATE",
            "안녕하세요 😊 요청하신 링크입니다!\n\n{deeplink}",
        ),
        instagram_harujin_owner_igsid=os.environ.get("INSTAGRAM_HARUJIN_OWNER_IGSID", ""),
        instagram_shinjh_owner_igsid=os.environ.get("INSTAGRAM_SHINJH_OWNER_IGSID", ""),
        facebook_harujin_page_id=os.environ.get("FACEBOOK_HARUJIN_PAGE_ID", ""),
        facebook_harujin_page_access_token=os.environ.get("FACEBOOK_HARUJIN_PAGE_ACCESS_TOKEN", ""),
        facebook_shinjh_page_id=os.environ.get("FACEBOOK_SHINJH_PAGE_ID", ""),
        facebook_shinjh_page_access_token=os.environ.get("FACEBOOK_SHINJH_PAGE_ACCESS_TOKEN", ""),
        facebook_api_mode=os.environ.get("FACEBOOK_API_MODE", "mock"),
        playwright_chromium_path=os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium"),
        state_file_path=os.environ.get("STATE_FILE_PATH", "data/state.json"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
