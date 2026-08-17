from __future__ import annotations

import os
from contextlib import contextmanager

DEFAULT_CHROMIUM_PATH = "/opt/pw-browsers/chromium"


@contextmanager
def launch_browser(headless: bool = True, chromium_path: str | None = None):
    """Launch a fresh (cookie-less) Chromium instance via Playwright's sync API."""
    from playwright.sync_api import sync_playwright

    executable_path = chromium_path or os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", DEFAULT_CHROMIUM_PATH)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, executable_path=executable_path)
        try:
            yield browser
        finally:
            browser.close()


@contextmanager
def launch_persistent_context(
    user_data_dir: str,
    headless: bool = True,
    chromium_path: str | None = None,
):
    """Launch a persistent-context Chromium that keeps cookies / session between runs.

    Use this for the Inpock RPA so Google OAuth credentials are cached after
    the first run and subsequent runs skip the login prompt.

    The returned object is a Playwright ``BrowserContext`` (not a ``Browser``).
    Call ``context.new_page()`` to get a page, then pass it to InpockRPAClient.
    """
    from playwright.sync_api import sync_playwright

    executable_path = chromium_path or os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", DEFAULT_CHROMIUM_PATH)

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            executable_path=executable_path,
            args=["--disable-save-password-bubble", "--disable-features=PasswordLeakDetection"],
        )
        try:
            yield context
        finally:
            context.close()
