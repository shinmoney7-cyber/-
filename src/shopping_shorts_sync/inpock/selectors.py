"""Inpock DOM 셀렉터.

단일 확정 셀렉터 대신 후보 목록을 사용해 실제 사이트 DOM을 탐색한다.
find_element() / wait_for_element() 가 각 후보를 순서대로 시도하므로
사이트 업데이트에도 강건하게 동작한다.
"""
from __future__ import annotations

LOGIN_URL = "https://link.inpock.co.kr/login"
PAGE_EDITOR_URL_TEMPLATE = "https://link.inpock.co.kr/manage/{page_slug}"


class LoginSelectors:
    EMAIL_INPUT = [
        "input[type='email']",
        "input[name='email']",
        "input[placeholder*='이메일']",
        "input[placeholder*='아이디']",
        "input[autocomplete='email']",
        "input[autocomplete='username']",
        "#email",
        "#username",
    ]
    PASSWORD_INPUT = [
        "input[type='password']",
        "input[name='password']",
        "input[placeholder*='비밀번호']",
        "input[autocomplete='current-password']",
        "#password",
    ]
    SUBMIT_BUTTON = [
        "button[type='submit']",
        "button:has-text('로그인')",
        "button:has-text('로 그인')",
        "button:has-text('Login')",
        "input[type='submit']",
        "form button",
    ]
    # 로그인 성공 후 나타나는 요소 (URL 변화로도 감지)
    LOGIN_SUCCESS_INDICATOR = [
        "[class*='dashboard']",
        "[class*='manage']",
        "[class*='editor']",
        "button:has-text('로그아웃')",
        "a:has-text('로그아웃')",
        "nav[class*='header']",
        "#app-header",
        ".sidebar",
    ]
    LOGOUT_BUTTON = [
        "button:has-text('로그아웃')",
        "a:has-text('로그아웃')",
        "[aria-label*='로그아웃']",
        "button:has-text('Logout')",
    ]


class EditorSelectors:
    # 링크 추가 버튼
    ADD_LINK_BUTTON = [
        "button:has-text('링크 추가')",
        "button:has-text('+ 링크')",
        "button:has-text('추가')",
        "a:has-text('링크 추가')",
        "[data-testid='add-link']",
        "[aria-label*='추가']",
        "button.add-link",
        ".add-item button",
        "button[class*='add']",
    ]
    # 카드 제목 입력
    TITLE_INPUT = [
        "input[name='title']",
        "input[placeholder*='제목']",
        "input[placeholder*='타이틀']",
        "input[placeholder*='title' i]",
        "textarea[name='title']",
        "input[label*='제목']",
        "dialog input[type='text']:first-of-type",
        ".modal input[type='text']:first-of-type",
        "[class*='modal'] input:first-of-type",
    ]
    # URL 입력
    URL_INPUT = [
        "input[type='url']",
        "input[name='url']",
        "input[name='link']",
        "input[placeholder*='URL']",
        "input[placeholder*='링크']",
        "input[placeholder*='주소']",
        "input[placeholder*='http']",
        "dialog input[type='text']:nth-of-type(2)",
        ".modal input[type='text']:nth-of-type(2)",
    ]
    # 썸네일 URL (없는 경우 스킵)
    THUMBNAIL_URL_INPUT = [
        "input[name='thumbnail']",
        "input[name='image']",
        "input[name='imageUrl']",
        "input[placeholder*='이미지']",
        "input[placeholder*='thumbnail' i]",
    ]
    # 저장 버튼
    SAVE_BUTTON = [
        "button:has-text('저장')",
        "button:has-text('확인')",
        "button:has-text('등록')",
        "button:has-text('Save')",
        "button[type='submit']",
        "dialog button[type='submit']",
        ".modal button:last-of-type",
        "[class*='modal'] button:last-of-type",
    ]
    # 기존 카드 목록 — 중복 방지용 탐색에만 사용
    EXISTING_CARD_ITEM = [
        "[data-testid='link-card']",
        "[class*='link-card']",
        "[class*='card-item']",
        ".link-item",
        "[class*='link-item']",
        "li[class*='card']",
        "[class*='item']",
    ]
    CARD_TITLE_TEXT = [
        ".card-title",
        "[class*='title']",
        "p[class*='title']",
        "span[class*='title']",
        "h3",
        "h4",
        "strong",
    ]
    # 수정 버튼 (기존 카드 편집)
    CARD_EDIT_BUTTON = [
        "button:has-text('수정')",
        "button:has-text('편집')",
        "button:has-text('Edit')",
        "[aria-label*='수정']",
        "[aria-label*='편집']",
        "button[class*='edit']",
        "svg[class*='edit']",
    ]
