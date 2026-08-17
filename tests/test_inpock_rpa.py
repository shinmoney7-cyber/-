"""Structural tests for InpockRPAClient.

Drives the client against fixtures/inpock_fixture_site/ — a hand-built
approximation of the real link.inpock.co.kr admin UI. These tests verify that
the Playwright flow logic executes correctly; they do NOT validate that the
real-site selectors are calibrated. See docs/CALIBRATION.md.
"""
from pathlib import Path

import pytest

from shopping_shorts_sync.browser import launch_browser
from shopping_shorts_sync.inpock.rpa import InpockRPAClient, LinkCard

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "inpock_fixture_site"
LOGIN_FILE_URL = FIXTURES / "login.html"
ADMIN_FILE_URL = FIXTURES / "admin.html"
EDIT_FILE_URL = FIXTURES / "edit.html"

LOGIN_URL = f"file://{LOGIN_FILE_URL}"
ADMIN_URL = f"file://{ADMIN_FILE_URL}"
EDIT_URL_TEMPLATE = f"file://{EDIT_FILE_URL}?link_id={{link_id}}"


@pytest.fixture
def rpa_client():
    with launch_browser(headless=True) as browser:
        page = browser.new_page()
        client = InpockRPAClient(
            page,
            email="test@example.com",
            password="hunter2",
            login_url=LOGIN_URL,
            admin_menu_url=ADMIN_URL,
            link_edit_url_template=EDIT_URL_TEMPLATE,
        )
        yield client


def test_login_via_account_button(rpa_client):
    """Login flow: click account button on login page, land on admin page."""
    rpa_client.login()
    assert rpa_client._is_on_admin()


def test_get_page_link_map_discovers_cards(rpa_client):
    """Admin page scanner finds link cards and extracts their link_ids."""
    rpa_client.page.goto(ADMIN_URL)
    link_map = rpa_client.get_page_link_map()
    # The fixture admin page exposes harujin's cards by default (link_id 1001, 1002)
    assert "1001" in link_map.values() or "1002" in link_map.values(), (
        f"Expected link_ids 1001/1002 in map, got: {link_map}"
    )


def test_edit_link_fills_form(rpa_client):
    """edit_link navigates to the edit page and fills the form fields."""
    card = LinkCard(title="테스트 상품", url="https://link.coupang.com/a/test", thumbnail="https://example.com/t.jpg")
    rpa_client.edit_link("1001", card)

    assert rpa_client.page.input_value("input[name='title']") == card.title
    assert rpa_client.page.input_value("input[name='url']") == card.url
    assert rpa_client.page.input_value("input[name='thumbnail']") == card.thumbnail


def test_sync_card_with_cached_link_id(rpa_client):
    """sync_card with a pre-known link_id skips the admin scan and goes straight to edit."""
    card = LinkCard(title="1. 제품A", url="https://link.coupang.com/a/x", thumbnail="")
    action, returned_id = rpa_client.sync_card("harujin", card, link_id="1001")
    assert action == "updated"
    assert returned_id == "1001"
    # Verify we landed on the edit page
    assert "edit" in rpa_client.page.url or "link_id" in rpa_client.page.url


def test_sync_card_discovers_existing_and_updates(rpa_client):
    """sync_card without a cached link_id scans the admin page, finds the card, and updates it."""
    card = LinkCard(title="1. 제품A", url="https://link.coupang.com/a/new", thumbnail="")
    action, link_id = rpa_client.sync_card("harujin", card)
    assert action == "updated"
    assert link_id is not None
