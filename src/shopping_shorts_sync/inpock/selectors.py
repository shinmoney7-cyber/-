"""All Inpock DOM selectors, isolated in one place.

Every value here is a best-effort placeholder, NOT verified against the real
link.inpock.co.kr site: this project's build environment had network egress
to that host blocked by policy, so the live DOM could never be inspected.
Before running against a real account, follow docs/CALIBRATION.md to replace
every `# TODO CALIBRATE` value with the real selector.
"""
from __future__ import annotations

LOGIN_URL = "https://link.inpock.co.kr/login"  # TODO CALIBRATE: confirm real login URL

# TODO CALIBRATE: confirm the real per-page editor URL pattern (may not be a
# simple template — could require clicking a page switcher in the dashboard).
PAGE_EDITOR_URL_TEMPLATE = "https://link.inpock.co.kr/manage/{page_slug}"


class LoginSelectors:
    EMAIL_INPUT = "input[type='email'], input[name='email']"  # TODO CALIBRATE
    PASSWORD_INPUT = "input[type='password'], input[name='password']"  # TODO CALIBRATE
    SUBMIT_BUTTON = "button[type='submit']"  # TODO CALIBRATE
    LOGIN_SUCCESS_INDICATOR = "#dashboard"  # TODO CALIBRATE


class EditorSelectors:
    ADD_LINK_BUTTON = "#add-link-button"  # TODO CALIBRATE
    TITLE_INPUT = "input[name='title']"  # TODO CALIBRATE
    URL_INPUT = "input[name='url']"  # TODO CALIBRATE
    THUMBNAIL_URL_INPUT = "input[name='thumbnail']"  # TODO CALIBRATE
    SAVE_BUTTON = "#save-button"  # TODO CALIBRATE

    # Secondary/best-effort: used only to try to detect an already-existing
    # card so we don't blindly duplicate. Not trusted as the primary
    # idempotency source (state_store.py is) until calibrated.
    EXISTING_CARD_ITEM = "[data-testid='link-card']"  # TODO CALIBRATE
    CARD_TITLE_TEXT = ".card-title"  # TODO CALIBRATE
