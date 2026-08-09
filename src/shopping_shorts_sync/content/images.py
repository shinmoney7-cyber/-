from __future__ import annotations

import abc
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 9:16 shorts canvas
CANVAS_W = 1080
CANVAS_H = 1920


@dataclass
class ImageSpec:
    role: str        # hook | mechanism | proof_cta
    headline: str
    body: str
    product_name: str


class ImageGenerator(abc.ABC):
    @abc.abstractmethod
    def generate(self, spec: ImageSpec, output_path: str) -> str:
        """Generate a 1080×1920 JPG and return its path."""


class PillowImageGenerator(ImageGenerator):
    """Generates simple branded overlay images using Pillow."""

    _BG_COLORS = {
        "hook": (20, 20, 20),
        "mechanism": (15, 40, 70),
        "proof_cta": (10, 60, 30),
    }
    _TEXT_COLOR = (255, 255, 255)
    _ACCENT_COLOR = (255, 200, 0)

    def generate(self, spec: ImageSpec, output_path: str) -> str:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as e:
            raise RuntimeError("Pillow is required for image generation. pip install Pillow") from e

        bg_color = self._BG_COLORS.get(spec.role, (30, 30, 30))
        img = Image.new("RGB", (CANVAS_W, CANVAS_H), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Simple text rendering with system font fallback
        try:
            font_lg = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 72)
            font_md = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 48)
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 36)
        except OSError:
            font_lg = ImageFont.load_default()
            font_md = font_lg
            font_sm = font_lg

        # Role badge
        draw.rectangle([60, 80, 300, 140], fill=self._ACCENT_COLOR)
        role_label = {"hook": "HOOK", "mechanism": "FEATURE", "proof_cta": "CTA"}.get(spec.role, spec.role.upper())
        draw.text((70, 88), role_label, fill=(0, 0, 0), font=font_sm)

        # Product name
        draw.text((60, 200), spec.product_name[:30], fill=self._ACCENT_COLOR, font=font_md)

        # Headline
        _draw_wrapped(draw, spec.headline, x=60, y=340, max_width=960, font=font_lg, fill=self._TEXT_COLOR, line_spacing=90)

        # Body
        _draw_wrapped(draw, spec.body, x=60, y=800, max_width=960, font=font_md, fill=(200, 200, 200), line_spacing=65)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "JPEG", quality=90)
        logger.info("image generated: %s (%s)", output_path, spec.role)
        return output_path


def _draw_wrapped(draw, text: str, x: int, y: int, max_width: int, font, fill, line_spacing: int):
    words = text.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        # Rough width estimate: each character ~= font_size * 0.6 for CJK
        if len(test) * (font.size if hasattr(font, "size") else 40) * 0.65 > max_width:
            draw.text((x, y), line, fill=fill, font=font)
            y += line_spacing
            line = word
        else:
            line = test
    if line:
        draw.text((x, y), line, fill=fill, font=font)


class MockImageGenerator(ImageGenerator):
    """Creates tiny placeholder images without Pillow (pure stdlib)."""

    # 1×1 white JPEG (631 bytes)
    _STUB_JPEG = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
        b"C  .DwDw=;=wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f"
        b"\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00"
        b"\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03"
        b"\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1"
        b"\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFG"
        b"HIJKLMNOPQRSTUVWXYZ\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd0\x00"
        b"\x00\x00\x00\xff\xd9"
    )

    def generate(self, spec: ImageSpec, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(self._STUB_JPEG)
        logger.info("mock image generated: %s (%s)", output_path, spec.role)
        return output_path
