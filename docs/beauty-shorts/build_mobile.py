"""Build mobile.html from mobile.src.html.

Copies the script data and drawing code from studio.html (so both apps draw
scenes the same way) and embeds the fixed model's reference photos as data
URIs, placed per scene as listed in photos/README.md.

    python docs/beauty-shorts/build_mobile.py
"""
import base64
import json
from pathlib import Path

HERE = Path(__file__).parent
REF = HERE / "photos" / "reference"

# model photos the app offers (phase: 메이크업 전/후); 가디건 세트 = 현재 뷰티 모델, 맨 앞
MODELS = [
    ("cardigan_bare_loose", "ref_cardigan_bare_loose.webp", "전", "풀어 내린 머리", "하늘색 가디건 · 미소"),
    ("cardigan_bare_tied", "ref_cardigan_bare_tied.webp", "전", "묶은 머리", "라벤더 가디건 · 정면"),
    ("cardigan_makeup_smile", "ref_cardigan_makeup_smile.webp", "후", "풀어 내린 머리", "하늘색 가디건 · 웃음"),
    ("cardigan_makeup_tied", "ref_cardigan_makeup_tied.webp", "후", "묶은 머리", "라벤더 가디건 · 미소"),
    ("cardigan_makeup_blonde", "ref_cardigan_makeup_blonde.webp", "후", "풀어 내린 머리", "금발 · 하늘색 가디건 · 웃음"),
    ("bare_loose", "ref_bare_loose.webp", "전", "풀어 내린 머리", "블라우스 · 정면"),
    ("bare", "ref_bare.webp", "전", "풀어 내린 머리", "블라우스 · 미소"),
    ("bare_tshirt_tied", "ref_bare_tshirt_tied.webp", "전", "묶은 머리", "티셔츠 · 볼에 손"),
    ("makeup_1", "ref_makeup_1.webp", "후", "풀어 내린 머리", "블라우스 · 정면"),
    ("makeup_2", "ref_makeup_2.webp", "후", "풀어 내린 머리", "블라우스 · 웨이브"),
    ("makeup_smile", "ref_makeup_smile.webp", "후", "풀어 내린 머리", "블라우스 · 웃음"),
    ("makeup_smile_tied", "ref_makeup_smile_tied.webp", "후", "묶은 머리", "블라우스 · 웃음"),
]

# default photo per scene key ("A-0" = A안 1번); the user can change it in the app
SCENE_PHOTOS = {
    "A-0": "ref_cardigan_bare_loose.webp",
    "A-3": "ref_cardigan_bare_tied.webp",
    "A-4": "ref_cardigan_makeup_smile.webp",
    "A-5": "ref_cardigan_makeup_tied.webp",
    "B-3": "ref_cardigan_bare_loose.webp",
    "B-4": "ref_cardigan_makeup_smile.webp",
    "C-0": "ref_bare_loose.webp",
    "C-2": "ref_bare.webp",
    "C-3": "ref_cardigan_makeup_tied.webp",
}


def between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


def main():
    studio = (HERE / "studio.html").read_text(encoding="utf-8")
    data = between(studio, "const VERSIONS = {", "let state = ")
    data += "const risky = text => RISKY.filter(w => text.includes(w));\n"
    draw = between(studio, "/* ---------- drawing ---------- */", "/* ---------- UI ---------- */")

    by_file = {f: mid for mid, f, *_ in MODELS}
    models = json.dumps([
        {"id": mid, "phase": phase, "hair": hair, "look": look,
         "src": "data:image/webp;base64," + base64.b64encode((REF / f).read_bytes()).decode()}
        for mid, f, phase, hair, look in MODELS
    ], ensure_ascii=False)
    scenes = json.dumps({k: by_file[v] for k, v in SCENE_PHOTOS.items()})

    src = (HERE / "mobile.src.html").read_text(encoding="utf-8")
    out = src.replace("/*@DATA@*/", data).replace("/*@MODELS@*/", models).replace("/*@SCENES@*/", scenes).replace("/*@DRAW@*/", draw)
    (HERE / "mobile.html").write_text(out, encoding="utf-8")
    print(f"mobile.html: {len(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
