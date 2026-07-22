"""Structural tests only — see fixtures/*_fixture_site/*.html docstrings.

These prove the Playwright search flow works against a hand-built stand-in
page; they do NOT validate the real daisomall.co.kr / oliveyoung.co.kr /
coupang.com selectors (network to all three was blocked in this build
environment). See docs/CALIBRATION.md before trusting this against
production.
"""
from pathlib import Path

import pytest

from shopping_shorts_sync.browser import launch_browser
from shopping_shorts_sync.search.coupang_match import CoupangMatchRPAClient
from shopping_shorts_sync.search.daiso import DaisoRPAClient
from shopping_shorts_sync.search.oliveyoung import OliveYoungRPAClient

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
DAISO_URL = f"file://{FIXTURES / 'daiso_fixture_site' / 'search.html'}"
OLIVEYOUNG_URL = f"file://{FIXTURES / 'oliveyoung_fixture_site' / 'search.html'}"
COUPANG_URL = f"file://{FIXTURES / 'coupang_fixture_site' / 'search.html'}"


@pytest.fixture
def page():
    with launch_browser(headless=True) as browser:
        yield browser.new_page()


def test_daiso_search_extracts_results(page):
    client = DaisoRPAClient(page, search_url_template=DAISO_URL)
    results = client.search("keyword", limit=5)

    assert len(results) == 2
    assert results[0].source == "daiso"
    assert results[0].name == "가습기 필터"
    assert results[0].image_url == "https://example.com/daiso/1.jpg"
    assert results[0].product_url == "/products/1"
    assert results[0].price == "3,000"


def test_daiso_search_respects_limit(page):
    client = DaisoRPAClient(page, search_url_template=DAISO_URL)
    assert len(client.search("keyword", limit=1)) == 1


def test_oliveyoung_search_extracts_results(page):
    client = OliveYoungRPAClient(page, search_url_template=OLIVEYOUNG_URL)
    results = client.search("keyword", limit=5)

    assert len(results) == 2
    assert results[0].source == "oliveyoung"
    assert results[0].name == "수분 세럼 ABC"
    assert results[0].price == "15,000"


def test_coupang_match_returns_top_result(page):
    client = CoupangMatchRPAClient(page, search_url_template=COUPANG_URL)
    url = client.find_top_match("무선 청소기")
    assert url == "https://www.coupang.com/vp/products/111111"


def test_coupang_match_absolutizes_relative_href(page):
    # the fixture already returns a relative-looking path in the first two
    # test cases only if hrefs are relative; here we directly check the
    # absolutization logic by pointing at a page with a relative href.
    client = CoupangMatchRPAClient(page, search_url_template=COUPANG_URL)
    url = client.find_top_match("anything")
    assert url.startswith("https://www.coupang.com/")
