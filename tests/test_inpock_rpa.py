"""Structural test only.

Drives InpockRPAClient against fixtures/inpock_fixture_site/ — a hand-built
approximation of an Inpock login/editor page, NOT the real
link.inpock.co.kr site (this project's build environment had network
access to that host blocked by policy, so the real DOM was never
inspected). This proves the Playwright flow logic executes correctly
against a stand-in; it does NOT validate real-site selectors. See
docs/CALIBRATION.md before trusting this against production.
"""
from pathlib import Path

import pytest

from shopping_shorts_sync.inpock.browser import launch_browser
from shopping_shorts_sync.inpock.rpa import InpockRPAClient, LinkCard

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "inpock_fixture_site"
LOGIN_FILE_URL = f"file://{FIXTURES / 'login.html'}"
EDITOR_FILE_URL = f"file://{FIXTURES / 'editor.html'}"


@pytest.fixture
def rpa_client():
    with launch_browser(headless=True) as browser:
        page = browser.new_page()
        client = InpockRPAClient(
            page,
            email="test@example.com",
            password="hunter2",
            login_url=LOGIN_FILE_URL,
            page_editor_url_template=EDITOR_FILE_URL,
        )
        yield client


def test_login_flow_reaches_success_indicator(rpa_client):
    rpa_client.login_url = LOGIN_FILE_URL
    rpa_client.login()
    assert rpa_client.page.query_selector("#dashboard") is not None


def test_create_card_appends_to_dom(rpa_client):
    rpa_client.goto_page_editor("harujin")
    card = LinkCard(title="Test Product", url="https://link.coupang.com/a/x", thumbnail="https://example.com/x.jpg")
    rpa_client.create_card(card)

    cards = rpa_client.page.query_selector_all("[data-testid='link-card']")
    assert len(cards) == 1
    assert "Test Product" in cards[0].inner_text()


def test_find_existing_card_after_create(rpa_client):
    rpa_client.goto_page_editor("harujin")
    card = LinkCard(title="Findable Product", url="https://link.coupang.com/a/y", thumbnail="")
    rpa_client.create_card(card)

    found = rpa_client.find_existing_card("Findable Product")
    assert found is not None

    not_found = rpa_client.find_existing_card("Nonexistent Product")
    assert not_found is None


def test_sync_card_creates_when_no_existing_card(rpa_client):
    rpa_client.goto_page_editor("harujin")
    card = LinkCard(title="Fresh Product", url="https://link.coupang.com/a/z", thumbnail="")
    action = rpa_client.sync_card("harujin", card, force_create=True)
    assert action == "created"
