"""RPA search selectors for sites with no public product-search API.

Every value here is a best-effort placeholder, NOT verified against the
real sites: this project's build environment had network egress to
daisomall.co.kr, oliveyoung.co.kr, and coupang.com all blocked by policy,
so none of these live DOMs could be inspected. Before running against the
real sites, follow docs/CALIBRATION.md to replace every
`# TODO CALIBRATE` value.
"""
from __future__ import annotations


class DaisoSelectors:
    SEARCH_URL_TEMPLATE = "https://www.daisomall.co.kr/search?keyword={keyword}"  # TODO CALIBRATE
    RESULT_ITEM = ".product-item"  # TODO CALIBRATE
    ITEM_NAME = ".product-name"  # TODO CALIBRATE
    ITEM_IMAGE = "img.product-thumb"  # TODO CALIBRATE
    ITEM_LINK = "a.product-link"  # TODO CALIBRATE
    ITEM_PRICE = ".product-price"  # TODO CALIBRATE


class OliveYoungSelectors:
    SEARCH_URL_TEMPLATE = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query={keyword}"  # TODO CALIBRATE
    RESULT_ITEM = ".prd_info"  # TODO CALIBRATE
    ITEM_NAME = ".tx_name"  # TODO CALIBRATE
    ITEM_IMAGE = "img.prd_thumb"  # TODO CALIBRATE
    ITEM_LINK = "a.prd_link"  # TODO CALIBRATE
    ITEM_PRICE = ".tx_cur .tx_num"  # TODO CALIBRATE


class CoupangSearchSelectors:
    SEARCH_URL_TEMPLATE = "https://www.coupang.com/np/search?q={keyword}"  # TODO CALIBRATE
    RESULT_ITEM = "ul#productList li.search-product"  # TODO CALIBRATE
    ITEM_LINK = "a.search-product-link"  # TODO CALIBRATE
