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
            self._debug_shot("login_1_picker_page")
            logger.info("inpock: login page loaded, url=%s", self.page.url)

            # Step 1: try account picker — find a button/li/a whose text IS the account slug.
            picker_clicked = False
            try:
                # Use get_by_text for precise matching inside clickable elements
                for selector in (f"button:has-text('{self.email}')", f"li:has-text('{self.email}')", f"a:has-text('{self.email}')"):
                    locator = self.page.locator(selector).first
                    if locator.count() > 0:
                        locator.click(timeout=3_000)
                        picker_clicked = True
                        logger.info("inpock: clicked account picker (%s) for %r", selector, self.email)
                        break
                if not picker_clicked:
                    # Broad text fallback
                    self.page.locator(f"text={self.email}").first.click(timeout=3_000)
                    picker_clicked = True
                    logger.info("inpock: clicked account picker (text=) for %r", self.email)
            except Exception as pick_exc:
                logger.debug("inpock: account picker click failed (%s), trying direct form fill", pick_exc)

            self._debug_shot("login_2_after_picker")

            if picker_clicked:
                # Wait for the password form to appear after the picker click.
                try:
                    self.page.wait_for_selector(LoginSelectors.PASSWORD_INPUT, timeout=7_000)
                    logger.info("inpock: password form appeared after picker click")
                except Exception:
                    logger.warning("inpock: password form did not appear within 7s after picker click")
            else:
                # Direct form: fill both ID and password.
                try:
                    self.page.fill(LoginSelectors.ID_INPUT, self.email)
                except Exception:
                    pass

            self._debug_shot("login_3_before_submit")
            self.page.fill(LoginSelectors.PASSWORD_INPUT, self.password)
            self.page.click(LoginSelectors.LOGIN_BUTTON)
            # After login, site may redirect to /inpockhome (not /admin directly).
            # Wait for navigation to settle, then go to admin explicitly.
            self.page.wait_for_load_state("domcontentloaded", timeout=15_000)
            self._debug_shot("login_4_after_submit")
            logger.info("inpock: post-submit url=%s", self.page.url)

            # Some flows show a post-auth account-picker as a SECOND step after
            # the initial credential form (e.g. fresh session → email/pw → picker → admin).
            if "login" in self.page.url:
                logger.info("inpock: still on login URL — checking for post-auth account picker")
                post_picker_clicked = False
                try:
                    for selector in (
                        f"button:has-text('{self.email}')",
                        f"li:has-text('{self.email}')",
                        f"a:has-text('{self.email}')",
                    ):
                        locator = self.page.locator(selector).first
                        if locator.count() > 0:
                            locator.click(timeout=3_000)
                            post_picker_clicked = True
                            logger.info("inpock: clicked post-auth account picker (%s) for %r", selector, self.email)
                            break
                    if not post_picker_clicked:
                        self.page.locator(f"text={self.email}").first.click(timeout=3_000)
                        post_picker_clicked = True
                        logger.info("inpock: clicked post-auth account picker (text=) for %r", self.email)
                except Exception as pick_exc:
                    logger.debug("inpock: post-auth picker click failed: %s", pick_exc)

                if post_picker_clicked:
                    self.page.wait_for_load_state("domcontentloaded", timeout=15_000)
                    self._debug_shot("login_5_after_second_picker")
                    logger.info("inpock: post-second-picker url=%s", self.page.url)

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
            self.page.goto(self.admin_menu_url, wait_until="domcontentloaded")
        # Give the Next.js SPA time to render after navigation.
        try:
            self.page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        self._debug_shot(f"goto_admin_{page_slug}")
        self._switch_to_page(page_slug)

    def _switch_to_page(self, page_slug: str) -> None:
        """Click the sidebar item for page_slug to make that page's blocks active.

        Tries multiple selector strategies to find the account switcher element.
        TODO CALIBRATE: if page switching still fails, inspect the sidebar DOM and
        update AdminSelectors.PAGE_SWITCHER_ITEM.
        """
        try:
            # Strategy 1: configured selector (broad nav/sidebar scan)
            items = self.page.query_selector_all(AdminSelectors.PAGE_SWITCHER_ITEM)
            for item in items:
                text = item.inner_text().strip().lower()
                if page_slug.lower() in text:
                    item.click()
                    self.page.wait_for_timeout(1_500)
                    logger.info("inpock: switched to page %r via PAGE_SWITCHER_ITEM", page_slug)
                    return

            # Strategy 2: any clickable element whose visible text is exactly the slug
            for tag in ("button", "a", "li", "span", "div"):
                try:
                    loc = self.page.locator(f"{tag}:has-text('{page_slug}')").first
                    if loc.count() > 0:
                        loc.click(timeout=2_000)
                        self.page.wait_for_timeout(1_500)
                        logger.info("inpock: switched to page %r via <%s> text match", page_slug, tag)
                        return
                except Exception:
                    continue

            # Strategy 3: text= locator (Playwright's full-text search)
            try:
                self.page.locator(f"text={page_slug}").first.click(timeout=2_000)
                self.page.wait_for_timeout(1_500)
                logger.info("inpock: switched to page %r via text= locator", page_slug)
                return
            except Exception:
                pass

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
        'link_id='. Titles are extracted from the surrounding DOM.

        TODO CALIBRATE: if this returns empty, open debug/admin_scan_empty.html,
        search for 'link_id' and check the href/data-attribute pattern on card elements.
        """
        # Wait for the Next.js SPA to finish rendering before scanning.
        try:
            self.page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        self.page.wait_for_timeout(2_000)

        result: dict[str, str] = {}

        # Strategy 1: JS evaluation — finds ALL anchors with link_id in href regardless of selector
        try:
            js_links: list[dict] = self.page.evaluate(
                """() => {
                    const out = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.getAttribute('href') || '';
                        if (href.includes('link_id=')) {
                            // Walk up to find a title element near this anchor
                            let title = '';
                            let node = a;
                            for (let i = 0; i < 8; i++) {
                                if (!node.parentElement) break;
                                node = node.parentElement;
                                const el = node.querySelector(
                                    '[class*="title"],[class*="name"],[class*="label"],p,span,h2,h3,h4'
                                );
                                if (el) { title = el.innerText.trim(); if (title) break; }
                            }
                            if (!title && a.parentElement) title = a.parentElement.innerText.trim();
                            out.push({href, title});
                        }
                    });
                    return out;
                }"""
            )
            for item in js_links:
                href = item.get("href", "")
                link_id = href.split("link_id=")[-1].split("&")[0].strip()
                if not link_id:
                    continue
                title = (item.get("title") or "").strip()
                result[title] = link_id
                logger.debug("inpock: JS-discovered card title=%r link_id=%s", title, link_id)
        except Exception:
            logger.exception("inpock: JS link scan failed, falling back to CSS selector")

        # Strategy 2: CSS selector fallback (catches elements missed by Strategy 1)
        if not result:
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
                    logger.debug("inpock: CSS-discovered card title=%r link_id=%s", title, link_id)
            except Exception:
                logger.exception("inpock: CSS link scan failed")

        if not result:
            # Save page HTML + screenshot and log all hrefs for selector calibration.
            try:
                DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(DEBUG_DIR / "admin_scan_empty.png"))
                html_content = self.page.content()
                (DEBUG_DIR / "admin_scan_empty.html").write_text(html_content, encoding="utf-8")
                # Log a sample of all hrefs visible on the page to help calibrate
                try:
                    all_hrefs: list[str] = self.page.evaluate(
                        "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href')).filter(Boolean)"
                    )
                    admin_hrefs = [h for h in all_hrefs if "admin" in h or "block" in h or "link" in h]
                    logger.warning(
                        "inpock: link map empty — current URL=%s | admin-related hrefs found: %s",
                        self.page.url,
                        admin_hrefs[:20] or "(none — page may not have rendered yet)",
                    )
                except Exception:
                    pass
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

    def _debug_shot(self, label: str) -> None:
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(DEBUG_DIR / f"{label}.png"))
        except Exception:
            pass

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
