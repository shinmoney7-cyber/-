from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..models import Product
from .selectors import (
    EditorSelectors,
    LoginSelectors,
    LOGIN_URL,
    PAGE_EDITOR_URL_TEMPLATE,
)

logger = logging.getLogger(__name__)

DEBUG_DIR = Path("debug")
_DEFAULT_TIMEOUT = 8000   # ms, 대부분의 액션
_NAV_TIMEOUT = 15000      # ms, 페이지 로드


class InpockRPAError(RuntimeError):
    pass


class SelectorNotFoundError(InpockRPAError):
    pass


@dataclass(frozen=True)
class LinkCard:
    title: str
    url: str
    thumbnail: str


# ──────────────────────────────────────────────────────────────────────────────
# 저수준 셀렉터 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _find(page, candidates: list[str], timeout: int = 2000) -> str | None:
    """후보 셀렉터 중 화면에 보이는 첫 번째를 반환. 없으면 None."""
    for sel in candidates:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return sel
        except Exception:
            pass
    return None


def _wait_for(page, candidates: list[str], timeout: int = _DEFAULT_TIMEOUT) -> str:
    """후보 셀렉터 중 하나가 나타날 때까지 기다림. 실패 시 SelectorNotFoundError."""
    import time
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        sel = _find(page, candidates, timeout=0)
        if sel:
            return sel
        page.wait_for_timeout(300)
    raise SelectorNotFoundError(
        f"화면에서 요소를 찾지 못했습니다. 후보: {candidates}"
    )


def _fill(page, candidates: list[str], value: str, timeout: int = _DEFAULT_TIMEOUT) -> None:
    sel = _wait_for(page, candidates, timeout)
    page.fill(sel, value)


def _click(page, candidates: list[str], timeout: int = _DEFAULT_TIMEOUT) -> None:
    sel = _wait_for(page, candidates, timeout)
    page.click(sel)


# ──────────────────────────────────────────────────────────────────────────────
# 메인 클라이언트
# ──────────────────────────────────────────────────────────────────────────────

class InpockRPAClient:
    """Inpock 링크 관리 UI를 Playwright로 자동화.

    login_url / page_editor_url_template 은 테스트 픽스처 오버라이드용.
    실제 사용 시에는 None 으로 두면 selectors.py 상수를 사용한다.
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
        self.login_url = login_url or LOGIN_URL
        self.page_editor_url_template = page_editor_url_template or PAGE_EDITOR_URL_TEMPLATE

    # ── 로그인 ────────────────────────────────────────────────────────────────

    def login(self) -> None:
        try:
            self.page.goto(self.login_url, timeout=_NAV_TIMEOUT)
            _fill(self.page, LoginSelectors.EMAIL_INPUT, self.email)
            _fill(self.page, LoginSelectors.PASSWORD_INPUT, self.password)
            _click(self.page, LoginSelectors.SUBMIT_BUTTON)
            # 로그인 성공 감지: 성공 인디케이터 요소 등장 OR 로그인 폼 소멸
            self._wait_for_login_success()
            logger.info("로그인 성공: %s", self.email)
        except SelectorNotFoundError:
            raise
        except Exception as exc:
            self._on_failure("login")
            raise InpockRPAError(f"로그인 실패: {exc}") from exc

    def _wait_for_login_success(self, timeout: int = _DEFAULT_TIMEOUT) -> None:
        """성공 인디케이터 또는 로그인 폼 소멸을 기다린다."""
        import time
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            # 성공 인디케이터 등장 확인
            for sel in LoginSelectors.LOGIN_SUCCESS_INDICATOR:
                try:
                    el = self.page.query_selector(sel)
                    if el and el.is_visible():
                        return
                except Exception:
                    pass
            # 로그인 폼이 사라졌는지 확인
            try:
                form_el = self.page.query_selector("input[type='email'], input[type='password']")
                if form_el is None:
                    return
            except Exception:
                pass
            self.page.wait_for_timeout(300)
        raise InpockRPAError("로그인 성공 인디케이터를 시간 내에 찾지 못했습니다")

    def logout(self) -> None:
        try:
            sel = _find(self.page, LoginSelectors.LOGOUT_BUTTON)
            if sel:
                self.page.click(sel)
                self.page.wait_for_url("**/login**", timeout=_DEFAULT_TIMEOUT)
                logger.info("로그아웃 완료")
            else:
                # 로그아웃 버튼을 못 찾으면 로그인 페이지로 직접 이동
                self.page.goto(self.login_url, timeout=_NAV_TIMEOUT)
        except Exception as exc:
            logger.warning("로그아웃 중 오류 (무시): %s", exc)
            self.page.goto(self.login_url, timeout=_NAV_TIMEOUT)

    # ── 페이지 이동 ───────────────────────────────────────────────────────────

    def goto_page_editor(self, page_slug: str) -> None:
        url = self.page_editor_url_template.format(page_slug=page_slug)
        try:
            self.page.goto(url, timeout=_NAV_TIMEOUT)
        except Exception as exc:
            self._on_failure(f"goto_page_editor_{page_slug}")
            raise InpockRPAError(f"{page_slug} 에디터 이동 실패: {exc}") from exc

    # ── 카드 탐색 ─────────────────────────────────────────────────────────────

    def find_existing_card(self, title: str):
        """제목이 일치하는 기존 카드 요소를 반환. 없으면 None."""
        try:
            for card_sel in EditorSelectors.EXISTING_CARD_ITEM:
                cards = self.page.query_selector_all(card_sel)
                if not cards:
                    continue
                for card in cards:
                    for title_sel in EditorSelectors.CARD_TITLE_TEXT:
                        title_el = card.query_selector(title_sel)
                        if title_el:
                            text = title_el.inner_text().strip()
                            if text == title.strip():
                                return card
        except Exception:
            pass
        return None

    # ── 카드 생성 ─────────────────────────────────────────────────────────────

    def create_card(self, card: LinkCard) -> None:
        try:
            _click(self.page, EditorSelectors.ADD_LINK_BUTTON)
            self.page.wait_for_timeout(500)

            _fill(self.page, EditorSelectors.TITLE_INPUT, card.title)
            _fill(self.page, EditorSelectors.URL_INPUT, card.url)

            # 썸네일은 선택사항 — 없으면 조용히 스킵
            if card.thumbnail:
                thumb_sel = _find(self.page, EditorSelectors.THUMBNAIL_URL_INPUT)
                if thumb_sel:
                    self.page.fill(thumb_sel, card.thumbnail)

            _click(self.page, EditorSelectors.SAVE_BUTTON)
            self.page.wait_for_timeout(800)
            logger.info("카드 생성 완료: %s", card.title)
        except SelectorNotFoundError:
            raise
        except Exception as exc:
            self._on_failure("create_card")
            raise InpockRPAError(f"카드 생성 실패: {exc}") from exc

    # ── 카드 수정 ─────────────────────────────────────────────────────────────

    def update_card(self, existing_element, card: LinkCard) -> None:
        try:
            # 수정 버튼 클릭 시도 — 없으면 카드 자체 클릭
            edit_btn = None
            for sel in EditorSelectors.CARD_EDIT_BUTTON:
                edit_btn = existing_element.query_selector(sel)
                if edit_btn:
                    break

            if edit_btn:
                edit_btn.click()
            else:
                existing_element.click()

            self.page.wait_for_timeout(500)

            # 제목 지우고 새 값 입력
            title_sel = _wait_for(self.page, EditorSelectors.TITLE_INPUT)
            self.page.triple_click(title_sel)
            self.page.fill(title_sel, card.title)

            url_sel = _wait_for(self.page, EditorSelectors.URL_INPUT)
            self.page.triple_click(url_sel)
            self.page.fill(url_sel, card.url)

            if card.thumbnail:
                thumb_sel = _find(self.page, EditorSelectors.THUMBNAIL_URL_INPUT)
                if thumb_sel:
                    self.page.triple_click(thumb_sel)
                    self.page.fill(thumb_sel, card.thumbnail)

            _click(self.page, EditorSelectors.SAVE_BUTTON)
            self.page.wait_for_timeout(800)
            logger.info("카드 수정 완료: %s", card.title)
        except SelectorNotFoundError:
            raise
        except Exception as exc:
            self._on_failure("update_card")
            raise InpockRPAError(f"카드 수정 실패: {exc}") from exc

    # ── 통합 sync ─────────────────────────────────────────────────────────────

    def sync_card(self, page_slug: str, card: LinkCard, force_create: bool = False) -> str:
        """'created' 또는 'updated' 반환."""
        self.goto_page_editor(page_slug)
        existing = None if force_create else self.find_existing_card(card.title)

        if existing is not None:
            self.update_card(existing, card)
            return "updated"

        self.create_card(card)
        return "created"

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────

    def _on_failure(self, label: str) -> None:
        if not self.screenshot_on_failure:
            return
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            path = DEBUG_DIR / f"{label}.png"
            self.page.screenshot(path=str(path))
            logger.info("실패 스크린샷 저장: %s", path)
        except Exception:
            logger.exception("스크린샷 저장 실패 (%s)", label)


def product_to_card(product: Product, deeplink: str) -> LinkCard:
    return LinkCard(title=product.name, url=deeplink, thumbnail=product.thumbnail)
