from __future__ import annotations

import os
from contextlib import contextmanager

DEFAULT_CHROMIUM_PATH = "/opt/pw-browsers/chromium"


@contextmanager
def launch_browser(headless: bool = True, chromium_path: str | None = None):
    """Launches the pre-installed Chromium via Playwright's sync API.

    Never runs `playwright install` — this environment ships Chromium
    already, pointed at by PLAYWRIGHT_CHROMIUM_PATH (falls back to the
    default bundled path).
    """
    from playwright.sync_api import sync_playwright

    env_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", DEFAULT_CHROMIUM_PATH)
    executable_path = chromium_path or env_path or None

    with sync_playwright() as pw:
        launch_kwargs: dict = {"headless": headless}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        browser = pw.chromium.launch(**launch_kwargs)
        try:
            yield browser
        finally:
            browser.close()
