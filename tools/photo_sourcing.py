"""Find and download travel photos that may be used in monetized shorts.

Only sources whose licence allows commercial use are searched, and every
downloaded photo is recorded with its licence, author and source page so the
attribution can go into the video description.

    python tools/photo_sourcing.py out/2026-11-24_#01/photo_plan.json out/2026-11-24_#01/photos

photo_plan.json:
    {"scenes": [
        {"id": "01", "query_ko": "유후인 료칸 노천탕", "query_en": "Yufuin onsen ryokan", "orientation": "portrait"},
        ...
    ]}

Sources (each is skipped when its key is missing):
- KTO   한국관광공사 관광사진 갤러리 (TourAPI, 공공누리)   env KTO_API_KEY (data.go.kr)
- WIKI  Wikimedia Commons, only CC0 / Public domain / CC BY  (no key)
- PEXELS                                              env PEXELS_API_KEY
- PIXABAY                                             env PIXABAY_API_KEY
- UNSPLASH                                            env UNSPLASH_ACCESS_KEY

Photos from blogs, booking sites, other people's SNS or hotel websites are NOT
downloaded: their copyright holders have not licensed them for reuse. For a
specific hotel, ask the hotel for photos (see the request text in the output).
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

UA = {"User-Agent": "cheonggyul-trip-photo-sourcing/1.0 (travel shorts; contact via repository owner)"}
MIN_WIDTH = 1600

# Licences that allow commercial reuse. CC BY-SA / NC / ND are excluded on purpose:
# NC forbids commercial use, ND forbids edits (cropping/zooming), SA would bind the video's licence.
ALLOWED_WIKI = re.compile(r"^(cc0|cc-zero|public domain|pd|cc by \d(\.\d)?|cc-by-\d(\.\d)?)", re.I)
BLOCKED_WIKI = re.compile(r"(sa|nc|nd)\b", re.I)


@dataclass
class Photo:
    source: str
    url: str
    page_url: str
    width: int
    height: int
    title: str
    author: str
    license: str
    attribution: str


def _get(session, url, **kw):
    r = session.get(url, headers=UA, timeout=30, **kw)
    r.raise_for_status()
    return r


def search_kto(q: str, n: int, session=requests) -> list[Photo]:
    key = os.environ.get("KTO_API_KEY")
    if not key:
        return []
    r = _get(session, "https://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1", params={
        "serviceKey": key, "MobileOS": "ETC", "MobileApp": "cheonggyultrip", "_type": "json",
        "keyword": q, "numOfRows": n, "pageNo": 1, "arrange": "A"})
    items = (((r.json().get("response") or {}).get("body") or {}).get("items") or {}).get("item") or []
    if isinstance(items, dict):
        items = [items]
    out = []
    for it in items:
        url = it.get("galWebImageUrl")
        if not url:
            continue
        author = it.get("galPhotographer") or "한국관광공사"
        out.append(Photo("KTO", url, "https://api.visitkorea.or.kr", 0, 0, it.get("galTitle", ""), author,
                         "공공누리 제1유형(출처표시) - 갤러리 표기 확인",
                         f"사진: 한국관광공사 ({author}) - 공공누리 제1유형"))
    return out


def search_wiki(q: str, n: int, session=requests) -> list[Photo]:
    r = _get(session, "https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{q} filetype:bitmap", "gsrlimit": n * 3, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 2400})
    pages = (r.json().get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if not ALLOWED_WIKI.match(lic) or BLOCKED_WIKI.search(lic.replace("cc-by-", "cc by ")):
            continue
        author = re.sub("<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip() or "Unknown"
        out.append(Photo("WIKI", info.get("thumburl") or info.get("url"), info.get("descriptionurl", ""),
                         info.get("width", 0), info.get("height", 0), p.get("title", ""), author, lic,
                         f"Photo: {author} / Wikimedia Commons ({lic})"))
        if len(out) >= n:
            break
    return out


def search_pexels(q: str, n: int, orientation: str, session=requests) -> list[Photo]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    r = session.get("https://api.pexels.com/v1/search", headers={**UA, "Authorization": key}, timeout=30,
                    params={"query": q, "per_page": n, "orientation": orientation})
    r.raise_for_status()
    return [Photo("PEXELS", p["src"]["original"], p["url"], p["width"], p["height"], p.get("alt", ""),
                  p["photographer"], "Pexels License", f"Photo: {p['photographer']} / Pexels")
            for p in r.json().get("photos", [])]


def search_pixabay(q: str, n: int, orientation: str, session=requests) -> list[Photo]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    r = _get(session, "https://pixabay.com/api/", params={
        "key": key, "q": q, "image_type": "photo", "per_page": max(3, n), "safesearch": "true",
        "orientation": "vertical" if orientation == "portrait" else "horizontal"})
    return [Photo("PIXABAY", h["largeImageURL"], h["pageURL"], h["imageWidth"], h["imageHeight"],
                  h.get("tags", ""), h["user"], "Pixabay Content License", f"Photo: {h['user']} / Pixabay")
            for h in r.json().get("hits", [])][:n]


def search_unsplash(q: str, n: int, orientation: str, session=requests) -> list[Photo]:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        return []
    r = _get(session, "https://api.unsplash.com/search/photos", params={
        "query": q, "per_page": n, "orientation": orientation, "client_id": key})
    return [Photo("UNSPLASH", p["urls"]["full"], p["links"]["html"], p["width"], p["height"],
                  p.get("alt_description") or "", p["user"]["name"], "Unsplash License",
                  f"Photo: {p['user']['name']} / Unsplash")
            for p in r.json().get("results", [])]


def candidates(scene: dict, per_source: int = 3, session=requests) -> list[Photo]:
    ko, en = scene.get("query_ko", ""), scene.get("query_en") or scene.get("query_ko", "")
    orient = scene.get("orientation", "portrait")
    found: list[Photo] = []
    for fn, args in ((search_kto, (ko, per_source)), (search_wiki, (en, per_source)),
                     (search_pexels, (en, per_source, orient)), (search_pixabay, (en, per_source, orient)),
                     (search_unsplash, (en, per_source, orient))):
        if not args[0]:
            continue
        try:
            found += fn(*args, session=session)
        except requests.RequestException as e:
            print(f"[{fn.__name__}] {scene.get('id')}: {e}", file=sys.stderr)
    # Korean public photos first, then larger images; drop small ones when the size is known.
    found = [p for p in found if p.width == 0 or p.width >= MIN_WIDTH or p.height >= MIN_WIDTH]
    found.sort(key=lambda p: (p.source != "KTO", -(p.width * p.height)))
    return found


def run(plan_path: Path, out_dir: Path, session=requests) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"photos": [], "missing": []}
    for scene in plan["scenes"]:
        sid = scene["id"]
        chosen = None
        for cand in candidates(scene, session=session):
            try:
                img = _get(session, cand.url)
            except requests.RequestException:
                continue
            ext = ".png" if "png" in img.headers.get("Content-Type", "") else ".jpg"
            (out_dir / f"{sid}{ext}").write_bytes(img.content)
            chosen = {"id": sid, "file": f"{sid}{ext}", **asdict(cand)}
            break
        if chosen:
            report["photos"].append(chosen)
        else:
            report["missing"].append({"id": sid, "query": scene.get("query_ko") or scene.get("query_en"),
                                      "next_step": "직접 촬영 또는 숙소·관광지에 사진 사용 허락 요청"})
    (out_dir / "credits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = sorted({p["attribution"] for p in report["photos"]})
    (out_dir / "credits.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    rep = run(Path(argv[0]), Path(argv[1]))
    print(f"downloaded {len(rep['photos'])}, missing {len(rep['missing'])}")
    for m in rep["missing"]:
        print(f"  - {m['id']}: {m['query']} -> {m['next_step']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
