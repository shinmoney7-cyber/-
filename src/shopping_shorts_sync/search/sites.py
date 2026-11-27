"""Per-mall search configuration for every RPA-searched shopping mall.

Only the search URL and result-card selectors differ per mall; the
navigate/extract flow lives in rpa_common.GenericSearchRPAClient.

IMPORTANT: every URL and selector below marked `TODO CALIBRATE` is an
unverified placeholder. The build environment could not reach these sites,
so none of them has been opened. Calibrate each mall per docs/CALIBRATION.md
before running with --live. Naver uses its official API (search/naver.py)
and is not listed here. Daiso and Olive Young keep their own modules
(daiso.py, oliveyoung.py) for backwards compatibility.
"""
from __future__ import annotations

from dataclasses import dataclass

from .daiso import DaisoRPAClient
from .oliveyoung import OliveYoungRPAClient
from .rpa_common import GenericSearchRPAClient


@dataclass(frozen=True)
class MallSpec:
    label: str
    search_url_template: str  # must contain {keyword}
    result_item: str
    item_name: str
    item_image: str
    item_link: str
    item_price: str | None = None


# Shared placeholder selectors. Replace per mall during calibration.
_PLACEHOLDER = dict(
    result_item="li.item",  # TODO CALIBRATE
    item_name=".item-name",  # TODO CALIBRATE
    item_image="img",  # TODO CALIBRATE
    item_link="a",  # TODO CALIBRATE
    item_price=".item-price",  # TODO CALIBRATE
)


def _spec(label: str, url: str) -> MallSpec:
    return MallSpec(label=label, search_url_template=url, **_PLACEHOLDER)


# Mall ids that use a generic RPA client with the specs below.
MALL_SPECS: dict[str, MallSpec] = {
    "11st": _spec("11번가", "https://search.11st.co.kr/Search.tmall?kwd={keyword}"),  # TODO CALIBRATE
    "gmarket": _spec("G마켓", "https://browse.gmarket.co.kr/search?keyword={keyword}"),  # TODO CALIBRATE
    "auction": _spec("옥션", "https://browse.auction.co.kr/search?keyword={keyword}"),  # TODO CALIBRATE
    "ssg": _spec("SSG.COM", "https://www.ssg.com/search.ssg?target=all&query={keyword}"),  # TODO CALIBRATE
    "lotteon": _spec("롯데온", "https://www.lotteon.com/search/search/search.ecn?render=search&platform=pc&query={keyword}"),  # TODO CALIBRATE
    "gsshop": _spec("GS SHOP", "https://www.gsshop.com/shop/search/main.gs?tq={keyword}"),  # TODO CALIBRATE
    "hmall": _spec("현대Hmall", "https://www.hmall.com/search?keyword={keyword}"),  # TODO CALIBRATE
    "kurly": _spec("마켓컬리", "https://www.kurly.com/search?sword={keyword}"),  # TODO CALIBRATE
    "musinsa": _spec("무신사", "https://www.musinsa.com/search/musinsa/goods?keyword={keyword}"),  # TODO CALIBRATE
    "29cm": _spec("29CM", "https://search.29cm.co.kr/?keyword={keyword}"),  # TODO CALIBRATE
    "ohouse": _spec("오늘의집", "https://ohou.se/search?query={keyword}"),  # TODO CALIBRATE
    "amazon": _spec("Amazon", "https://www.amazon.com/s?k={keyword}"),  # TODO CALIBRATE
    "aliexpress": _spec("AliExpress", "https://www.aliexpress.com/w/wholesale-{keyword}.html"),  # TODO CALIBRATE
}

# Malls with their own RPA module (already calibrated-or-pending in selectors.py).
DEDICATED_RPA = {"daiso": DaisoRPAClient, "oliveyoung": OliveYoungRPAClient}

RPA_SOURCES = tuple(DEDICATED_RPA) + tuple(MALL_SPECS)


def build_rpa_client(source: str, page):
    """Returns a search client for an RPA-searched mall, bound to `page`."""
    if source in DEDICATED_RPA:
        return DEDICATED_RPA[source](page)
    spec = MALL_SPECS.get(source)
    if spec is None:
        raise ValueError(f"no RPA config for search source: {source!r}")
    return GenericSearchRPAClient(
        page,
        source=source,
        search_url_template=spec.search_url_template,
        result_item_selector=spec.result_item,
        item_name_selector=spec.item_name,
        item_image_selector=spec.item_image,
        item_link_selector=spec.item_link,
        item_price_selector=spec.item_price,
    )
