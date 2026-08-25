from __future__ import annotations

import shutil
import os
from contextlib import contextmanager

# 환경별 Chromium 후보 경로 (앞에서부터 순서대로 탐색)
_CHROMIUM_CANDIDATES = [
    "/opt/pw-browsers/chromium",                                              # CCR 클라우드
    "/opt/homebrew/bin/chromium",                                             # Mac Homebrew
    "/Applications/Chromium.app/Contents/MacOS/Chromium",                    # Mac 앱
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",          # Mac Chrome
    "/usr/bin/chromium-browser",                                              # Linux
    "/usr/bin/chromium",                                                      # Linux alt
    "/usr/bin/google-chrome",                                                 # Linux Chrome
]


def _resolve_chromium(explicit_path: str | None = None) -> str | None:
    if explicit_path:
        return explicit_path
    env_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "")
    if env_path:
        return env_path
    for candidate in _CHROMIUM_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    # 마지막으로 PATH 에서 탐색
    return shutil.which("chromium") or shutil.which("google-chrome") or None


@contextmanager
def launch_browser(headless: bool = True, chromium_path: str | None = None):
    """Playwright Chromium을 실행. 경로를 명시하지 않으면 환경에 맞게 자동 탐색.

    playwright install 을 실행하지 않는다 — 이미 설치된 Chromium을 사용.
    Mac 로컬에서 실행 시 chromium 또는 Google Chrome 을 자동으로 찾는다.
    """
    from playwright.sync_api import sync_playwright

    resolved = _resolve_chromium(chromium_path)

    with sync_playwright() as pw:
        if resolved:
            browser = pw.chromium.launch(headless=headless, executable_path=resolved)
        else:
            # Playwright 번들 Chromium 사용 (playwright install 이 완료된 경우)
            browser = pw.chromium.launch(headless=headless)
        try:
            yield browser
        finally:
            browser.close()
