from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REDACT_KEYS = {
    "coupang_secret_key",
    "coupang_access_key",
    "inpock_password",
    "youtube_api_key",
    "typecast_api_key",
    "instagram_access_token",
    "naver_ad_secret_key",
    "tiktok_access_token",
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

    youtube_api_key: str

    naver_ad_api_key: str
    naver_ad_secret_key: str
    naver_ad_customer_id: str
    trend_history_path: str

    instagram_access_token: str
    instagram_ig_user_id: str

    typecast_api_key: str
    typecast_mode: str
    typecast_actor_id: str
    typecast_speed: float

    video_mode: str
    video_output_dir: str
    video_clip_seconds: float
    ytdlp_path: str
    ffmpeg_path: str

    tiktok_access_token: str
    youtube_client_secrets_file: str
    youtube_token_file: str
    public_base_url: str

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
    scripts_dir: str
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
        youtube_api_key=os.environ.get("YOUTUBE_API_KEY", ""),
        naver_ad_api_key=os.environ.get("NAVER_AD_API_KEY", ""),
        naver_ad_secret_key=os.environ.get("NAVER_AD_SECRET_KEY", ""),
        naver_ad_customer_id=os.environ.get("NAVER_AD_CUSTOMER_ID", ""),
        trend_history_path=os.environ.get("TREND_HISTORY_PATH", "data/trend_history.json"),
        instagram_access_token=os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""),
        instagram_ig_user_id=os.environ.get("INSTAGRAM_IG_USER_ID", ""),
        typecast_api_key=os.environ.get("TYPECAST_API_KEY", ""),
        typecast_mode=os.environ.get("TYPECAST_MODE", "mock"),
        typecast_actor_id=os.environ.get("TYPECAST_ACTOR_ID", "예슬"),
        typecast_speed=float(os.environ.get("TYPECAST_SPEED", "1.2")),
        video_mode=os.environ.get("VIDEO_MODE", "mock"),
        video_output_dir=os.environ.get("VIDEO_OUTPUT_DIR", "data/videos"),
        video_clip_seconds=float(os.environ.get("VIDEO_CLIP_SECONDS", "5.0")),
        ytdlp_path=os.environ.get("YTDLP_PATH", "yt-dlp"),
        ffmpeg_path=os.environ.get("FFMPEG_PATH", "ffmpeg"),
        tiktok_access_token=os.environ.get("TIKTOK_ACCESS_TOKEN", ""),
        youtube_client_secrets_file=os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE", ""),
        youtube_token_file=os.environ.get("YOUTUBE_TOKEN_FILE", "data/youtube_token.json"),
        public_base_url=os.environ.get("PUBLIC_BASE_URL", ""),
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
        scripts_dir=os.environ.get("SCRIPTS_DIR", "data/scripts"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
