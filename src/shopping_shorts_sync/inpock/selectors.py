"""All Inpock DOM selectors, isolated in one place.

Values marked # TODO CALIBRATE have not been verified against the live
link.inpock.co.kr site. Run `sss inpock sync --live --headed` against your
real account and update any selector that causes a step to fail. See
docs/CALIBRATION.md for the workflow.

What IS known from direct observation:
- Login URL: /user/login  (shows previously-authenticated account buttons)
- Admin URL: /admin/menu  (block list for the current page)
- Edit URL:  /admin/block/link/edit?link_id=<id>  (per-link edit form)
- Account switcher in the left sidebar for switching between harujin / shinjh
- Clicking the link thumbnail navigates to the edit URL above
"""
from __future__ import annotations

LOGIN_URL = "https://link.inpock.co.kr/user/login"
ADMIN_MENU_URL = "https://link.inpock.co.kr/admin/menu"
LINK_EDIT_URL_TEMPLATE = "https://link.inpock.co.kr/admin/block/link/edit?link_id={link_id}"


class LoginSelectors:
    # /user/login has a standard 아이디 + 비밀번호 form (confirmed from live site screenshot).
    # The label says "아이디" (account ID), input is a plain text field.
    ID_INPUT = "input[name='id'], input[name='username'], input[type='text']"  # TODO CALIBRATE: confirm name attr
    PASSWORD_INPUT = "input[type='password']"
    # Orange "로그인" button confirmed from live site screenshot — matched by text content
    LOGIN_BUTTON = "button:has-text('로그인')"

    # Element present after a successful admin login.
    LOGIN_SUCCESS_INDICATOR = "nav, [class*='sidebar'], [class*='admin']"  # TODO CALIBRATE


class AdminSelectors:
    # Sidebar links / buttons for switching the active page (harujin, shinjh, …).
    # The element's inner text should contain the page slug.
    PAGE_SWITCHER_ITEM = "nav a, nav button, [class*='sidebar'] a, [class*='sidebar'] button"  # TODO CALIBRATE

    # Anchor tags that link to the per-link edit page.  Used to discover all
    # existing link cards and their link_ids on the currently-displayed page.
    # Pattern observed: href="/admin/block/link/edit?link_id=7074950"
    LINK_EDIT_ANCHOR = "a[href*='/admin/block/link/edit']"  # TODO CALIBRATE: confirm href pattern

    # Button to add a new link block on the admin page.
    ADD_LINK_BUTTON = "button"  # TODO CALIBRATE: e.g. "button:has-text('추가')" or "[class*='add-block']"


class LinkEditSelectors:
    # Form fields on /admin/block/link/edit
    TITLE_INPUT = "input[name='title'], input[placeholder*='제목'], input[id*='title']"  # TODO CALIBRATE
    URL_INPUT = "input[name='url'], input[type='url'], input[placeholder*='http']"  # TODO CALIBRATE
    THUMBNAIL_URL_INPUT = (
        "input[name='thumbnail'], input[name='image_url'], input[placeholder*='이미지']"  # TODO CALIBRATE
    )
    # Save button on the edit page ("수정 완료")
    SAVE_BUTTON = "button[type='submit'], button[class*='submit']"  # TODO CALIBRATE: "button:has-text('수정 완료')"
