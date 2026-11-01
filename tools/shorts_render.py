"""Render a vertical travel short from still photos using a JSON scene spec.

Each photo scene gets a camera move (zoom / pan / tilt via start and end
framing), an optional water-ripple effect for pools, and a caption. Info cards
and an end card are drawn on top of a blurred photo or a plain background.

Usage:
    python tools/shorts_render.py spec.json out.mp4

Spec (paths are relative to the spec file):
{
  "size": [720, 1280], "fps": 30, "transition": 0.3,
  "font": "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
  "badge": "광고 · 제휴링크 포함",          # top-left on every scene (optional)
  "watermark": "샘플 · 업로드 금지",        # centre overlay (optional)
  "scenes": [
    {"image": "pool.jpg", "dur": 3,
     "from": {"z": 1.0, "cx": 0.5, "cy": 0.5}, "to": {"z": 1.3, "cx": 0.4, "cy": 0.6},
     "text": "캡션", "text_pos": "bottom",
     "ripple": {"y0": 0.62, "amp": 6}},
    {"card": true, "bg": "pool.jpg", "dur": 3, "title": "제목", "lines": ["줄1", "줄2"]},
    {"end": true, "dur": 2.5, "title": "청귤트립", "lines": ["프로필 링크 #P5"]}
  ]
}

"z" is relative to the largest 9:16 window that fits inside the photo
(z=1 shows that whole window). "cx"/"cy" are the window centre as fractions
of the photo; the window is clamped so it never leaves the photo.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

GREEN = (124, 179, 66)
ORANGE = (255, 167, 38)
INK = (38, 50, 56)
CREAM = (255, 253, 245)


def ease(t: float) -> float:
    return t * t * (3 - 2 * t)


def ripple(img: np.ndarray, t: float, y0: float, amp: float) -> np.ndarray:
    h, w, _ = img.shape
    start = int(h * y0)
    if start >= h:
        return img
    out = img.copy()
    ys = np.arange(start, h)
    depth = (ys - start) / max(1, h - start)
    shift = (amp * np.sin(ys / 9.0 + t * 6.0) * (0.3 + 0.7 * depth)).astype(int)
    xs = np.arange(w)
    idx = (xs[None, :] + shift[:, None]) % w
    out[start:] = img[ys[:, None], idx]
    return out


def frame_window(iw: int, ih: int, aspect: float, z: float, cx: float, cy: float):
    if iw / ih > aspect:
        bh, bw = ih, ih * aspect
    else:
        bw, bh = iw, iw / aspect
    w, h = bw / z, bh / z
    x = min(max(cx * iw - w / 2, 0), iw - w)
    y = min(max(cy * ih - h / 2, 0), ih - h)
    return x, y, w, h


class Renderer:
    def __init__(self, spec: dict, base: Path):
        self.spec = spec
        self.base = base
        self.W, self.H = spec.get("size", [720, 1280])
        self.fps = spec.get("fps", 30)
        self.font_path = spec.get("font", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
        self._fonts: dict[int, ImageFont.FreeTypeFont] = {}
        self._images: dict[str, Image.Image] = {}

    def font(self, size: int):
        if size not in self._fonts:
            self._fonts[size] = ImageFont.truetype(self.font_path, size)
        return self._fonts[size]

    def image(self, rel: str) -> Image.Image:
        if rel not in self._images:
            self._images[rel] = Image.open(self.base / rel).convert("RGB")
        return self._images[rel]

    def text_center(self, draw, y, text, size, fill=(255, 255, 255), stroke=6, stroke_fill=INK):
        f = self.font(size)
        # shrink to fit width
        while draw.textlength(text, font=f) > self.W * 0.92 and size > 20:
            size -= 2
            f = self.font(size)
        x = (self.W - draw.textlength(text, font=f)) / 2
        draw.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)

    def overlays(self, im: Image.Image):
        d = ImageDraw.Draw(im, "RGBA")
        badge = self.spec.get("badge")
        if badge:
            f = self.font(26)
            tw = d.textlength(badge, font=f)
            d.rectangle([16, 32, 32 + tw, 74], fill=(0, 0, 0, 90))
            d.text((24, 38), badge, font=f, fill=(255, 255, 255, 230))
        wm = self.spec.get("watermark")
        if wm:
            f = self.font(64)
            tw = d.textlength(wm, font=f)
            d.text(((self.W - tw) / 2, self.H * 0.62), wm, font=f, fill=(255, 255, 255, 90))

    def photo_frame(self, sc: dict, t: float) -> Image.Image:
        src = self.image(sc["image"])
        arr = np.asarray(src)
        rp = sc.get("ripple")
        if rp:
            arr = ripple(arr, t, rp.get("y0", 0.6), rp.get("amp", 6))
        a, b = sc.get("from", {}), sc.get("to", {})
        k = ease(min(1.0, t / sc["dur"]))
        z = a.get("z", 1.0) + (b.get("z", a.get("z", 1.0)) - a.get("z", 1.0)) * k
        cx = a.get("cx", 0.5) + (b.get("cx", a.get("cx", 0.5)) - a.get("cx", 0.5)) * k
        cy = a.get("cy", 0.5) + (b.get("cy", a.get("cy", 0.5)) - a.get("cy", 0.5)) * k
        ih, iw = arr.shape[:2]
        x, y, w, h = frame_window(iw, ih, self.W / self.H, z, cx, cy)
        im = Image.fromarray(arr).resize(
            (self.W, self.H), Image.LANCZOS, box=(x, y, x + w, y + h)
        )
        if sc.get("text"):
            d = ImageDraw.Draw(im)
            pos = {"top": 0.13, "middle": 0.42, "bottom": 0.74}[sc.get("text_pos", "bottom")]
            self.text_center(d, self.H * pos, sc["text"], sc.get("text_size", 56))
            if sc.get("sub"):
                self.text_center(d, self.H * pos + 80, sc["sub"], 40, fill=ORANGE, stroke=5)
        return im

    def card_frame(self, sc: dict, t: float) -> Image.Image:
        if sc.get("bg"):
            bg = self.photo_frame({"image": sc["bg"], "dur": sc["dur"],
                                   "from": {"z": 1.0}, "to": {"z": 1.08}}, t)
            im = bg.filter(ImageFilter.GaussianBlur(14))
            im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), 0.35)
            color, sub = (255, 255, 255), (255, 255, 255)
        else:
            im = Image.new("RGB", (self.W, self.H), CREAM)
            color, sub = GREEN, INK
        d = ImageDraw.Draw(im)
        lines = sc.get("lines", [])
        top = self.H * (0.30 if not sc.get("end") else 0.36)
        size = 104 if sc.get("end") else 64
        stroke = 0 if not sc.get("bg") else 5
        self.text_center(d, top, sc.get("title", ""), size,
                         fill=GREEN if sc.get("end") else color, stroke=stroke)
        y = top + size + 50
        for i, line in enumerate(lines):
            # reveal lines one by one over the first 60% of the card
            if t < sc["dur"] * 0.6 * i / max(1, len(lines)):
                break
            fill = ORANGE if (sc.get("end") and i == 0) else sub
            self.text_center(d, y, line, 46 if not sc.get("end") else (46 if i == 0 else 36),
                             fill=fill, stroke=stroke)
            y += 78
        return im

    def scene_frames(self, sc: dict):
        n = int(round(sc["dur"] * self.fps))
        for i in range(n):
            t = i / self.fps
            im = self.card_frame(sc, t) if (sc.get("card") or sc.get("end")) else self.photo_frame(sc, t)
            self.overlays(im)
            yield np.asarray(im)

    def render(self, out: Path):
        tr = int(round(self.spec.get("transition", 0.3) * self.fps))
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{self.W}x{self.H}", "-r", str(self.fps), "-i", "-"]
        audio = self.spec.get("audio")
        if audio:
            cmd += ["-i", str(self.base / audio), "-shortest", "-c:a", "aac"]
        cmd += ["-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        scenes = self.spec["scenes"]
        prev_tail: list[np.ndarray] = []
        total = 0
        for si, sc in enumerate(scenes):
            n = int(round(sc["dur"] * self.fps))
            last = si == len(scenes) - 1
            new_tail: list[np.ndarray] = []
            for i, f in enumerate(self.scene_frames(sc)):
                # crossfade: blend this scene's first frames over the previous scene's last frames
                if i < len(prev_tail):
                    a = (i + 1) / (len(prev_tail) + 1)
                    f = (prev_tail[i] * (1 - a) + f * a).astype(np.uint8)
                if not last and tr and i >= n - tr:
                    new_tail.append(f)
                    continue
                proc.stdin.write(f.tobytes())
                total += 1
            prev_tail = new_tail
        proc.stdin.close()
        proc.wait()
        return total / self.fps


def main():
    spec_path = Path(sys.argv[1])
    out = Path(sys.argv[2])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    dur = Renderer(spec, spec_path.parent).render(out)
    print(f"rendered {out} ({dur:.1f}s)")


if __name__ == "__main__":
    main()
