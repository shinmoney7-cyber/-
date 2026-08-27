from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..models import Product
from .selectors import EditorSelectors, LoginSelectors, LOGIN_URL, PAGE_EDITOR_URL_TEMPLATE

logger = logging.getLogger(__name__)

DEBUG_DIR = Path("debug")


class InpockRPAError(RuntimeError):
    pass


@dataclass(frozen=True)
class LinkCard:
    title: str
    url: str
    thumbnail: str


class InpockRPAClient:
    """Drives the Inpock creator manager UI to create/update link cards.

    Broken into small, independently-testable semantic steps rather than one
    monolithic script, so selector calibration (docs/CALIBRATION.md) only
    requires editing selectors.py, not this flow logic.
    """

    def __init__(
        self,
        page,
        email: str,
        password: str,
        screenshot_on_failure: bool = True,
        login_url: str | None = None,
        page_editor_url_template: str | None = None,
    ):
        self.page = page
        self.email = email
        self.password = password
        self.screenshot_on_failure = screenshot_on_failure
        # Overridable for testing against the local fixture site (see
        # tests/test_inpock_rpa.py); production code should leave these as
        # None so the real selectors.py constants are used.
        self.login_url = login_url or LOGIN_URL
        self.page_editor_url_template = page_editor_url_template or PAGE_EDITOR_URL_TEMPLATE

    def login(self) -> None:
        try:
            self.page.goto(self.login_url)
            self.page.fill(LoginSelectors.EMAIL_INPUT, self.email)
            self.page.fill(LoginSelectors.PASSWORD_INPUT, self.password)
            self.page.click(LoginSelectors.SUBMIT_BUTTON)
            self.page.wait_for_selector(LoginSelectors.LOGIN_SUCCESS_INDICATOR)
        except Exception as exc:
            self._on_failure("login")
            raise InpockRPAError(f"login failed: {exc}") from exc

    def goto_page_editor(self, page_slug: str) -> None:
        try:
            self.page.goto(self.page_editor_url_template.format(page_slug=page_slug))
        except Exception as exc:
            self._on_failure(f"goto_page_editor_{page_slug}")
            raise InpockRPAError(f"navigating to {page_slug} editor failed: {exc}") from exc

    def go_to_next_page(self) -> None:
        try:
            self.page.click(EditorSelectors.NEXT_PAGE_BUTTON)
        except Exception as exc:
            self._on_failure("go_to_next_page")
            raise InpockRPAError(f"next page navigation failed: {exc}") from exc

    def go_to_prev_page(self) -> None:
        try:
            self.page.click(EditorSelectors.PREV_PAGE_BUTTON)
        except Exception as exc:
            self._on_failure("go_to_prev_page")
            raise InpockRPAError(f"prev page navigation failed: {exc}") from exc

    def find_existing_card(self, title: str):
        """Best-effort DOM search for a card with a matching title.

        This is a secondary safety net only — not calibrated/trusted as the
        primary idempotency source (state_store.py is). Returns None on any
        uncertainty rather than guessing.
        """
        try:
            cards = self.page.query_selector_all(EditorSelectors.EXISTING_CARD_ITEM)
        except Exception:
            return None

        for card in cards:
            title_el = card.query_selector(EditorSelectors.CARD_TITLE_TEXT)
            if title_el and title_el.inner_text().strip() == title.strip():
                return card
        return None

    def create_card(self, card: LinkCard) -> None:
        try:
            self.page.click(EditorSelectors.ADD_LINK_BUTTON)
            self.page.fill(EditorSelectors.TITLE_INPUT, card.title)
            self.page.fill(EditorSelectors.URL_INPUT, card.url)
            self.page.fill(EditorSelectors.THUMBNAIL_URL_INPUT, card.thumbnail)
            self.page.click(EditorSelectors.SAVE_BUTTON)
        except Exception as exc:
            self._on_failure("create_card")
            raise InpockRPAError(f"creating link card failed: {exc}") from exc

    def update_card(self, existing_element, card: LinkCard) -> None:
        # NOTE: real update-in-place interaction (e.g. clicking an edit icon
        # on `existing_element`) is unconfirmed without live-site access.
        # For now, MVP treats update the same as create; calibrate once the
        # real editor's edit flow is known (see docs/CALIBRATION.md).
        self.create_card(card)

    def sync_card(self, page_slug: str, card: LinkCard, force_create: bool = False) -> str:
        """Returns 'created' or 'updated'."""
        self.goto_page_editor(page_slug)
        existing = self.find_existing_card(card.title)

        if existing is not None:
            self.update_card(existing, card)
            return "updated"

        if not force_create:
            logger.warning(
                "no existing card confidently found for %r on %s; selectors are uncalibrated "
                "so this may be a false negative. Creating anyway (pass force_create=True to "
                "silence this warning once calibrated).",
                card.title,
                page_slug,
            )
        self.create_card(card)
        return "created"

    def _on_failure(self, label: str) -> None:
        if not self.screenshot_on_failure:
            return
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(DEBUG_DIR / f"{label}.png"))
        except Exception:
            logger.exception("failed to capture debug screenshot for %s", label)


def product_to_card(product: Product, deeplink: str) -> LinkCard:
    return LinkCard(title=product.name, url=deeplink, thumbnail=product.thumbnail)
