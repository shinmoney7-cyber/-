from __future__ import annotations

from .rpa_common import GenericSearchRPAClient
from .selectors import DaisoSelectors


class DaisoRPAClient(GenericSearchRPAClient):
    def __init__(self, page, search_url_template: str | None = None, **kwargs):
        super().__init__(
            page,
            source="daiso",
            search_url_template=search_url_template or DaisoSelectors.SEARCH_URL_TEMPLATE,
            result_item_selector=DaisoSelectors.RESULT_ITEM,
            item_name_selector=DaisoSelectors.ITEM_NAME,
            item_image_selector=DaisoSelectors.ITEM_IMAGE,
            item_link_selector=DaisoSelectors.ITEM_LINK,
            item_price_selector=DaisoSelectors.ITEM_PRICE,
            **kwargs,
        )
