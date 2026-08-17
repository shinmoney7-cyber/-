from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..models import Product
from .selectors import (
    ADMIN_MENU_URL,
    LINK_EDIT_URL_TEMPLATE,
    LOGIN_URL,
    AdminSelectors,
    LinkEditSelectors,
    LoginSelectors,
)

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

    Calibration status: URLs confirmed from live site screenshots. DOM
    selectors are best-effort — follow docs/CALIBRATION.md before the first
    live run.
    """

    def __init__(
        self,
        page,
        email: str,
        password: str,
        screenshot_on_failure: bool = True,
        login_url: str | None = None,
        admin_menu_url: str | None = None,
        link_edit_url_template: str | None = None,
    ):
        self.page = page
        self.email = email
        self.password = password
        self.screenshot_on_failure = screenshot_on_failure
        # Overridable for testing against a local fixture site.
        self.login_url = login_url or LOGIN_URL
        self.admin_menu_url = admin_menu_url or ADMIN_MENU_URL
        self.link_edit_url_template = link_edit_url_template or LINK_EDIT_URL_TEMPLATE

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def _is_on_admin(self) -> bool:
        url = self.page.url
        # Production: on the inpock admin subdomain
        if "/admin" in url and "inpock.co.kr" in url:
            return True
        # Test fixture: URL starts with the configured admin URL
        return bool(self.admin_menu_url) and url.startswith(self.admin_menu_url)

    def login(self) -> None:
        """Log in to Inpock.

        The real /user/login page shows an ACCOUNT PICKER listing registered
        accounts (harujin, shinjh, …).  Clicking an account navigates to the
        standard 아이디/비밀번호 form with the 아이디 field pre-filled.

        Flow:
          1. Navigate to /user/login.
          2. Click the account button matching ``self.email`` (the account slug,
             e.g. "harujin") by text content.
          3. Wait for the password input to appear.
          4. Fill the password and click 로그인.
          5. Wait for redirect to /admin/**.

        If no account picker item is found (e.g. a simple test fixture), falls
        back to filling both ID and password fields directly.

        ``self.email`` should contain the Inpock account slug (e.g. "harujin"),
        not an email address.  Set INPOCK_ACCOUNT=harujin in your .env.
        """
        try:
            self.page.goto(self.admin_menu_url, wait_until="domcontentloaded", timeout=10_000)
            if self._is_on_admin():
                logger.info("inpock: session already active, skipping login")
                return
        except Exception:
            pass

        try:
            self.page.goto(self.login_url, wait_until="domcontentloaded")

            # Step 1: try account picker — click the item that contains the account slug.
            try:
                self.page.locator(f"text={self.email}").first.click(timeout=3_000)
                logger.info("inpock: clicked account picker item for %r", self.email)
                self.page.wait_for_selector(LoginSelectors.PASSWORD_INPUT, timeout=5_000)
            except Exception:
                # No picker found (or picker click failed) — fall back to direct form fill.
                logger.debug("inpock: account picker not found, falling back to direct form fill")
                try:
                    self.page.fill(LoginSelectors.ID_INPUT, self.email)
                except Exception:
                    pass

            self.page.fill(LoginSelectors.PASSWORD_INPUT, self.password)
            self.page.click(LoginSelectors.LOGIN_BUTTON)
            # After login, site may redirect to /inpockhome (not /admin directly).
            # Wait for navigation to settle, then go to admin explicitly.
            self.page.wait_for_load_state("domcontentloaded", timeout=15_000)
            if "login" in self.page.url:
                raise InpockRPAError("login failed: still on login page after submit — check credentials")
            if not self._is_on_admin():
                self.page.goto(self.admin_menu_url, wait_until="domcontentloaded", timeout=10_000)
            logger.info("inpock: login successful, url=%s", self.page.url)
        except Exception as exc:
            self._on_failure("login")
            raise InpockRPAError(f"login failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Admin navigation
    # ------------------------------------------------------------------

    def goto_admin(self, page_slug: str) -> None:
        """Navigate to the admin page and switch to the specified page."""
        if not self._is_on_admin():
            self.page.goto(self.admin_menu_url)
        self._switch_to_page(page_slug)

    def _switch_to_page(self, page_slug: str) -> None:
        """Click the sidebar item for page_slug to make that page's blocks active.

        TODO CALIBRATE: AdminSelectors.PAGE_SWITCHER_ITEM should match only the
        sidebar page-switcher items, not every nav link on the page.
        """
        try:
            items = self.page.query_selector_all(AdminSelectors.PAGE_SWITCHER_ITEM)
            for item in items:
                text = item.inner_text().strip().lower()
                if page_slug.lower() in text:
                    item.click()
                    self.page.wait_for_timeout(1_000)
                    logger.info("inpock: switched to page %r", page_slug)
                    return
            logger.warning(
                "inpock: page switcher item for %r not found; staying on current page "
                "(AdminSelectors.PAGE_SWITCHER_ITEM may need calibration)",
                page_slug,
            )
        except Exception as exc:
            self._on_failure(f"switch_to_page_{page_slug}")
            raise InpockRPAError(f"switching to page {page_slug!r} failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Link card discovery
    # ------------------------------------------------------------------

    def _get_card_title_near_anchor(self, anchor) -> str:
        """Extract the displayed title text of the link card that contains this anchor.

        Walks up the DOM from the anchor, looking for a text node that looks like
        a card title. Returns an empty string on any failure.

        TODO CALIBRATE: if titles are still not matched, inspect the DOM around
        an anchor element and update the JavaScript in this method.
        """
        try:
            title: str = anchor.evaluate(
                """el => {
                    // Walk up to a container element that has meaningful text
                    let node = el;
                    for (let i = 0; i < 6; i++) {
                        if (!node.parentElement) break;
                        node = node.parentElement;
                        // Prefer an explicit title/name child element
                        const titleEl = node.querySelector(
                            '[class*="title"], [class*="name"], p, span, h2, h3'
                        );
                        if (titleEl) {
                            const t = titleEl.innerText.trim();
                            if (t) return t;
                        }
                    }
                    // Fallback: inner text of the anchor's immediate parent
                    if (el.parentElement) return el.parentElement.innerText.trim();
                    return '';
                }"""
            )
            return (title or "").strip()
        except Exception:
            return ""

    def get_page_link_map(self) -> dict[str, str]:
        """Return {card_title: link_id} for all link cards visible on the current admin page.

        Discovers cards by looking for anchor elements whose href contains
        '/admin/block/link/edit?link_id='. Titles are extracted from the surrounding DOM.

        TODO CALIBRATE: if AdminSelectors.LINK_EDIT_ANCHOR produces no results, open
        the admin page in a headed browser and inspect the thumbnail anchor's href.
        """
        result: dict[str, str] = {}
        try:
            anchors = self.page.query_selector_all(AdminSelectors.LINK_EDIT_ANCHOR)
            for anchor in anchors:
                href = anchor.get_attribute("href") or ""
                if "link_id=" not in href:
                    continue
                link_id = href.split("link_id=")[-1].split("&")[0].strip()
                if not link_id:
                    continue
                title = self._get_card_title_near_anchor(anchor)
                result[title] = link_id
                logger.debug("inpock: discovered card title=%r link_id=%s", title, link_id)
        except Exception:
            logger.exception("inpock: failed to scan page link IDs")

        if not result:
            # Save page HTML + screenshot so we can calibrate the selectors.
            try:
                DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(DEBUG_DIR / "admin_scan_empty.png"))
                (DEBUG_DIR / "admin_scan_empty.html").write_text(
                    self.page.content(), encoding="utf-8"
                )
                logger.warning(
                    "inpock: link map empty — debug files saved to %s/ "
                    "(check admin_scan_empty.html for correct LINK_EDIT_ANCHOR selector)",
                    DEBUG_DIR,
                )
            except Exception:
                pass

        return result

    def _find_link_id_for_card(self, card: LinkCard, existing: dict[str, str]) -> str | None:
        """Match `card` against the existing title→link_id map.

        Tries exact match first, then a partial match for renamed-numbered titles
        (e.g. "1. 상품명" vs "상품명").
        """
        if card.title in existing:
            return existing[card.title]

        # Partial match: strip the number prefix and compare the base name
        base = card.title.split(". ", 1)[-1] if ". " in card.title else card.title
        for title, link_id in existing.items():
            candidate_base = title.split(". ", 1)[-1] if ". " in title else title
            if base == candidate_base:
                logger.info(
                    "inpock: partial title match: card %r matches existing %r (link_id=%s)",
                    card.title,
                    title,
                    link_id,
                )
                return link_id
        return None

    # ------------------------------------------------------------------
    # Edit / create
    # ------------------------------------------------------------------

    def edit_link(self, link_id: str, card: LinkCard) -> None:
        """Navigate to the edit URL and update the card's title, URL, and thumbnail."""
        url = self.link_edit_url_template.format(link_id=link_id)
        try:
            self.page.goto(url)
            self.page.fill(LinkEditSelectors.TITLE_INPUT, card.title)
            self.page.fill(LinkEditSelectors.URL_INPUT, card.url)
            if card.thumbnail:
                try:
                    self.page.fill(LinkEditSelectors.THUMBNAIL_URL_INPUT, card.thumbnail)
                except Exception:
                    logger.warning("inpock: could not fill thumbnail for link_id=%s (selector may need calibration)", link_id)
            self.page.click(LinkEditSelectors.SAVE_BUTTON)
            self.page.wait_for_timeout(1_000)
        except Exception as exc:
            self._on_failure(f"edit_link_{link_id}")
            raise InpockRPAError(f"editing link {link_id} failed: {exc}") from exc

    def create_link(self, page_slug: str, card: LinkCard) -> str | None:
        """Click the add-link button and fill the creation form.

        Returns the new link_id if it can be discovered after creation, else None.

        TODO CALIBRATE: AdminSelectors.ADD_LINK_BUTTON must point to the correct
        "+ 링크 추가" button. The creation form selectors may differ from the edit
        form — verify with docs/CALIBRATION.md.
        """
        try:
            self.page.click(AdminSelectors.ADD_LINK_BUTTON)
            self.page.wait_for_selector(LinkEditSelectors.TITLE_INPUT, timeout=5_000)
            self.page.fill(LinkEditSelectors.TITLE_INPUT, card.title)
            self.page.fill(LinkEditSelectors.URL_INPUT, card.url)
            if card.thumbnail:
                try:
                    self.page.fill(LinkEditSelectors.THUMBNAIL_URL_INPUT, card.thumbnail)
                except Exception:
                    logger.warning("inpock: could not fill thumbnail on create form")
            self.page.click(LinkEditSelectors.SAVE_BUTTON)
            self.page.wait_for_timeout(1_500)
        except Exception as exc:
            self._on_failure("create_link")
            raise InpockRPAError(f"creating link card failed: {exc}") from exc

        # Re-scan the page to find the freshly-created link_id
        try:
            self.page.goto(self.admin_menu_url)
            self._switch_to_page(page_slug)
            ids = self.get_page_link_map()
            return ids.get(card.title)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def sync_card(
        self,
        page_slug: str,
        card: LinkCard,
        force_create: bool = False,
        link_id: str | None = None,
    ) -> tuple[str, str | None]:
        """Create or update a link card.

        Returns ``(action, link_id)`` where action is ``"created"`` or ``"updated"``.

        If ``link_id`` is provided (cached from a previous run) we skip the
        admin-page scan and navigate directly to the edit URL.
        """
        if link_id:
            self.edit_link(link_id, card)
            return ("updated", link_id)

        self.goto_admin(page_slug)
        existing = self.get_page_link_map()

        found_id = self._find_link_id_for_card(card, existing) if not force_create else None

        if found_id:
            self.edit_link(found_id, card)
            return ("updated", found_id)

        if not force_create:
            raise InpockRPAError(
                f"no existing card found for {card.title!r} on {page_slug} "
                "and force_create is not set. "
                "Check debug/admin_scan_empty.html for the correct LINK_EDIT_ANCHOR selector, "
                "or re-run with --force-create to create a new card."
            )
        new_id = self.create_link(page_slug, card)
        return ("created", new_id)

    def _on_failure(self, label: str) -> None:
        if not self.screenshot_on_failure:
            return
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(DEBUG_DIR / f"{label}.png"))
        except Exception:
            logger.exception("failed to capture debug screenshot for %s", label)


def product_to_card(product: Product, deeplink: str, number: int | None = None) -> LinkCard:
    title = f"{number}. {product.name}" if number is not None else product.name
    return LinkCard(title=title, url=deeplink, thumbnail=product.thumbnail)
