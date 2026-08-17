from __future__ import annotations

from .rpa_common import GenericSearchRPAClient
from .selectors import OliveYoungSelectors


class OliveYoungRPAClient(GenericSearchRPAClient):
    def __init__(self, page, search_url_template: str | None = None, **kwargs):
        super().__init__(
            page,
            source="oliveyoung",
            search_url_template=search_url_template or OliveYoungSelectors.SEARCH_URL_TEMPLATE,
            result_item_selector=OliveYoungSelectors.RESULT_ITEM,
            item_name_selector=OliveYoungSelectors.ITEM_NAME,
            item_image_selector=OliveYoungSelectors.ITEM_IMAGE,
            item_link_selector=OliveYoungSelectors.ITEM_LINK,
            item_price_selector=OliveYoungSelectors.ITEM_PRICE,
            **kwargs,
        )
