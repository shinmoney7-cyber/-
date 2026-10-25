"""사주마루(@sajumaru77) 인스타그램 피드 카드 이미지 생성기.

Buffer 초안에는 이미지가 없어서 인스타그램 게시가 막혀 있었다. 초안마다 1080x1350(4:5)
카드를 만들어 images/ 에 저장하고, 공개 저장소의 raw URL을 Buffer 게시물 이미지로 쓴다.

폰트는 저장소에 넣지 않는다 (google/fonts 저장소에서 받아 --fonts 로 지정):
  NotoSansKR.ttf, NotoSerifKR.ttf  (가변 폰트)

사용법:
  python instagram/sajumaru/make_cards.py --fonts <폰트 폴더>
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
W, H = 1080, 1350

GOLD = (222, 186, 112)
WHITE = (246, 242, 232)
MUTED = (178, 176, 200)

# 오행별 강조색
ELEMENT = {
    "火": ((232, 92, 72), "화"),
    "水": ((86, 156, 236), "수"),
    "木": ((88, 186, 120), "목"),
    "金": ((214, 214, 226), "금"),
    "土": ((206, 160, 92), "토"),
    "月": ((222, 186, 112), "달"),
    "日": ((246, 196, 92), "해"),
    "命": ((222, 186, 112), "명"),
}


class Fonts:
    def __init__(self, font_dir: Path):
        self.sans = font_dir / "NotoSansKR.ttf"
        self.serif = font_dir / "NotoSerifKR.ttf"

    def get(self, kind: str, size: int, weight: int) -> ImageFont.FreeTypeFont:
        font = ImageFont.truetype(str(self.serif if kind == "serif" else self.sans), size)
        try:
            font.set_variation_by_axes([weight])
        except OSError:
            pass
        return font


def background(seed: int) -> Image.Image:
    img = Image.new("RGB", (W, H))
    top, bottom = (14, 18, 44), (34, 28, 66)
    px = img.load()
    for y in range(H):
        t = y / H
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for _ in range(140):
        x, y = rnd.randrange(W), rnd.randrange(H)
        r = rnd.choice([1, 1, 1, 2])
        a = rnd.randrange(90, 200)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(a, a, min(255, a + 20)))
    return img


def glow_circle(img: Image.Image, center, radius, color):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse([cx - radius - 30, cy - radius - 30, cx + radius + 30, cy + radius + 30], fill=color + (70,))
    layer = layer.filter(ImageFilter.GaussianBlur(40))
    img.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=color, width=6)
    d.ellipse([cx - radius + 16, cy - radius + 16, cx + radius - 16, cy + radius - 16], outline=color + (0,), width=0)


def wrap(draw, text, font, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def centered(draw, y, text, font, fill, max_w=920, spacing=1.35):
    for line in wrap(draw, text, font, max_w):
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=fill)
        y += int(font.size * spacing)
    return y


def render(card: dict, fonts: Fonts, seed: int) -> Image.Image:
    img = background(seed)
    d = ImageDraw.Draw(img)
    color, _ = ELEMENT[card["element"]]

    # 상단 브랜드
    centered(d, 70, "사 주 마 루", fonts.get("serif", 34, 700), GOLD)
    d.line([(W / 2 - 60, 128), (W / 2 + 60, 128)], fill=GOLD, width=2)
    if card.get("kicker"):
        centered(d, 148, card["kicker"], fonts.get("sans", 30, 500), MUTED)

    # 오행 원
    cy = 350
    glow_circle(img, (W // 2, cy), 120, color)
    d = ImageDraw.Draw(img)
    hanja = fonts.get("serif", 150, 800)
    tw = d.textlength(card["element"], font=hanja)
    bbox = d.textbbox((0, 0), card["element"], font=hanja)
    d.text(((W - tw) / 2, cy - (bbox[1] + bbox[3]) / 2), card["element"], font=hanja, fill=color)

    # 제목
    y = centered(d, 530, card["title"], fonts.get("serif", 72, 800), WHITE, spacing=1.3)
    if card.get("subtitle"):
        y = centered(d, y + 14, card["subtitle"], fonts.get("sans", 36, 500), GOLD) + 10

    # 본문 박스
    points = card.get("points", [])
    if points:
        y += 30
        body = fonts.get("sans", 38, 500)
        line_h = 66
        box_h = line_h * len(points) + 60
        box = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle(
            [90, y, W - 90, y + box_h], radius=28, fill=(255, 255, 255, 18), outline=color + (150,), width=2
        )
        img.paste(box, (0, 0), box)
        d = ImageDraw.Draw(img)
        py = y + 30
        for p in points:
            d.ellipse([140, py + 22, 154, py + 36], fill=color)
            d.text((178, py + 2), p, font=body, fill=WHITE)
            py += line_h
        y += box_h

    # 하단 CTA
    footer = card.get("footer", "무료 사주 신청은 프로필 링크에서")
    d.line([(90, H - 150), (W - 90, H - 150)], fill=(255, 255, 255, 40), width=1)
    centered(d, H - 125, footer, fonts.get("sans", 32, 600), GOLD)
    centered(d, H - 75, "@sajumaru77", fonts.get("sans", 26, 400), MUTED)
    if card.get("page"):
        d.text((W - 150, 72), card["page"], font=fonts.get("sans", 28, 600), fill=MUTED)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", type=Path, required=True)
    args = ap.parse_args()
    fonts = Fonts(args.fonts)
    cards = json.loads((HERE / "cards.json").read_text(encoding="utf-8"))
    out = HERE / "images"
    out.mkdir(exist_ok=True)
    for i, card in enumerate(cards):
        render(card, fonts, seed=i).save(out / f"{card['file']}.jpg", quality=92)
        print(card["file"])


if __name__ == "__main__":
    main()
