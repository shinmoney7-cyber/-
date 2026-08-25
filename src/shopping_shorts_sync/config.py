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

    # 공통 Inpock 계정 (페이지별 계정이 없을 때 fallback)
    inpock_email: str
    inpock_password: str

    # 페이지별 계정 (비어 있으면 공통 계정 사용)
    inpock_email_harujin: str
    inpock_password_harujin: str
    inpock_email_shinjh: str
    inpock_password_shinjh: str

    inpock_headless: bool

    naver_client_id: str
    naver_client_secret: str

    playwright_chromium_path: str
    state_file_path: str
    log_level: str

    def inpock_credentials_for(self, page_slug: str) -> tuple[str, str]:
        """페이지별 전용 계정이 있으면 반환, 없으면 공통 계정 반환."""
        email_key = f"inpock_email_{page_slug}"
        pass_key = f"inpock_password_{page_slug}"
        page_email = getattr(self, email_key, "")
        page_password = getattr(self, pass_key, "")
        if page_email and page_password:
            return page_email, page_password
        return self.inpock_email, self.inpock_password

    def redacted_dict(self) -> dict:
        d = self.__dict__.copy()
        for key in list(d):
            if "password" in key or "secret" in key:
                if d.get(key):
                    d[key] = "***REDACTED***"
        return d


def load_config(env_file: str | None = None) -> Config:
    load_dotenv(env_file)

    def _get(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    return Config(
        coupang_access_key=_get("COUPANG_ACCESS_KEY"),
        coupang_secret_key=_get("COUPANG_SECRET_KEY"),
        coupang_api_mode=_get("COUPANG_API_MODE", "mock"),
        coupang_batch_size=int(_get("COUPANG_BATCH_SIZE", "50")),
        inpock_email=_get("INPOCK_EMAIL"),
        inpock_password=_get("INPOCK_PASSWORD"),
        inpock_email_harujin=_get("INPOCK_EMAIL_HARUJIN"),
        inpock_password_harujin=_get("INPOCK_PASSWORD_HARUJIN"),
        inpock_email_shinjh=_get("INPOCK_EMAIL_SHINJH"),
        inpock_password_shinjh=_get("INPOCK_PASSWORD_SHINJH"),
        inpock_headless=_get("INPOCK_HEADLESS", "true").strip().lower() in ("1", "true", "yes"),
        naver_client_id=_get("NAVER_CLIENT_ID"),
        naver_client_secret=_get("NAVER_CLIENT_SECRET"),
        playwright_chromium_path=_get("PLAYWRIGHT_CHROMIUM_PATH", ""),
        state_file_path=_get("STATE_FILE_PATH", "data/state.json"),
        log_level=_get("LOG_LEVEL", "INFO"),
    )
