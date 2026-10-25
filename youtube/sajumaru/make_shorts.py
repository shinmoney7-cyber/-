"""사주마루 유튜브 쇼츠 생성기.

instagram/sajumaru/images 의 카드 이미지를 1080x1920 세로 영상으로 만든다.
카드가 천천히 확대되고, 여러 장이면 크로스페이드로 넘어간다. 배경음은 저작권 문제가
없도록 ffmpeg 로 합성한 잔잔한 화음이다.

사용법:
  python youtube/sajumaru/make_shorts.py
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
CARDS = HERE.parent.parent / "instagram" / "sajumaru" / "images"
W, H = 1080, 1920
TOP, BOTTOM = (14, 18, 44), (34, 28, 66)
FPS = 30
FADE = 0.8


def vertical_frame(card_path: Path, out: Path) -> None:
    """카드(1080x1350)를 배경 그라데이션 위 세로 화면 가운데에 놓는다."""
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        c = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    card = Image.open(card_path)
    img.paste(card, (0, (H - card.height) // 2))
    img.save(out, quality=95)


def render(short: dict, workdir: Path, out: Path) -> None:
    per = short.get("seconds_per_card", 12 if len(short["cards"]) == 1 else 4.5)
    frames = []
    for i, name in enumerate(short["cards"]):
        frame = workdir / f"{short['file']}-{i}.jpg"
        vertical_frame(CARDS / f"{name}.jpg", frame)
        frames.append(frame)

    n = len(frames)
    total = per * n - FADE * (n - 1)
    inputs, filters = [], []
    for i, frame in enumerate(frames):
        inputs += ["-loop", "1", "-t", f"{per}", "-i", str(frame)]
        d = int(per * FPS)
        filters.append(
            f"[{i}:v]scale=2160:-1,zoompan=z='1+0.04*on/{d}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={d}:s={W}x{H}:fps={FPS},setsar=1[v{i}]"
        )
    last = "v0"
    for i in range(1, n):
        offset = per * i - FADE * i
        filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset}[x{i}]")
        last = f"x{i}"
    filters.append(f"[{last}]fade=t=in:d=0.5,fade=t=out:st={total - 0.7}:d=0.7,format=yuv420p[vout]")

    # A단조 계열 화음 + 느린 떨림 — 작게, 앞뒤로 페이드
    pad = (
        "0.05*sin(2*PI*220*t)*(1+0.3*sin(2*PI*0.2*t))"
        "+0.035*sin(2*PI*261.63*t)+0.035*sin(2*PI*329.63*t)+0.02*sin(2*PI*440*t)"
    )
    inputs += ["-f", "lavfi", "-t", f"{total}", "-i", f"aevalsrc={pad}:s=44100"]
    filters.append(f"[{n}:a]afade=t=in:d=1.5,afade=t=out:st={total - 1.5}:d=1.5,volume=0.6[aout]")

    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[vout]", "-map", "[aout]", "-t", f"{total}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)],
        check=True,
    )


def main():
    shorts = json.loads((HERE / "shorts.json").read_text(encoding="utf-8"))
    out_dir = HERE / "videos"
    out_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for short in shorts:
            render(short, Path(tmp), out_dir / f"{short['file']}.mp4")
            print(short["file"])


if __name__ == "__main__":
    main()
