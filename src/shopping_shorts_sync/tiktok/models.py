from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VideoMeta:
    url: str
    title: str
    thumbnail_url: str
    author: str
    raw_description: str = ""


@dataclass
class RemotionConfig:
    hook_line1: str
    hook_line2: str
    hook_sub: str
    product_name: str
    benefits: list[str]
    price: str
    thumbnail_url: str = ""

    def to_dict(self) -> dict:
        return {
            "hookLine1": self.hook_line1,
            "hookLine2": self.hook_line2,
            "hookSub": self.hook_sub,
            "productName": self.product_name,
            "benefits": self.benefits,
            "price": self.price,
        }
