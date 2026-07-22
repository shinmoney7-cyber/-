from __future__ import annotations

from ..models import Product
from .rpa import LinkCard, product_to_card


class MockInpockRPAClient:
    """Drop-in stand-in for InpockRPAClient. No browser, no network.

    Records every sync call in-memory so orchestrator tests can assert on
    what would have been synced, without touching Playwright at all.
    """

    def __init__(self):
        self.synced_cards: list[tuple[str, LinkCard]] = []

    def login(self) -> None:
        pass

    def sync_card(self, page_slug: str, card: LinkCard, force_create: bool = False) -> str:
        self.synced_cards.append((page_slug, card))
        return "created"


def sync_product(client, product: Product, deeplink: str) -> str:
    card = product_to_card(product, deeplink)
    return client.sync_card(product.target_page, card)
