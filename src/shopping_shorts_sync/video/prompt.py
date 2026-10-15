from __future__ import annotations

from dataclasses import dataclass

from ..models import Product
from ..script_store import ScriptCandidate

# One clip per AIDA stage. Visual direction is English (video models follow it
# more reliably); the Korean script line is kept as the on-screen caption /
# voice-over text for editing afterwards.
_STAGE_DIRECTIONS = {
    "attention": "Vertical 9:16 shopping short opening hook. Fast push-in on the product, dramatic lighting, scroll-stopping first frame.",
    "interest": "Vertical 9:16 product close-up. Slow orbit around the product highlighting what makes it different, clean studio background.",
    "desire": "Vertical 9:16 lifestyle usage scene. The product being used naturally at home, satisfying result shot, warm natural light.",
    "action": "Vertical 9:16 closing hero shot. Product centered and still, gentle camera pull-back, space at the bottom for a call-to-action caption.",
}


@dataclass(frozen=True)
class Scene:
    stage: str
    caption: str
    prompt: str


def build_scenes(product: Product, candidate: ScriptCandidate) -> list[Scene]:
    scenes = []
    for stage, direction in _STAGE_DIRECTIONS.items():
        caption = getattr(candidate, stage)
        prompt = (
            f"{direction} Product: {product.name}"
            + (f" ({product.category})" if product.category else "")
            + f". Mood of this line: \"{caption}\". Keep the product's shape, color and label identical to the reference image. No text overlays."
        )
        scenes.append(Scene(stage=stage, caption=caption, prompt=prompt))
    return scenes
