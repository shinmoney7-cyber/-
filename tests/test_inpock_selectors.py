from shopping_shorts_sync.inpock.selectors import PUBLIC_PAGE_URLS


def test_public_page_urls_cover_both_target_pages():
    assert PUBLIC_PAGE_URLS == {
        "harujin": "https://link.inpock.co.kr/harujin",
        "shinjh": "https://link.inpock.co.kr/shinjh",
    }
