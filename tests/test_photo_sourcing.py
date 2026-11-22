import importlib.util
import json
import re
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "photo_sourcing", Path(__file__).resolve().parents[1] / "tools" / "photo_sourcing.py"
)
ps = importlib.util.module_from_spec(spec)
sys.modules["photo_sourcing"] = ps
spec.loader.exec_module(ps)

WIKI = re.compile(r"https://commons\.wikimedia\.org/w/api\.php.*")


def wiki_page(title, lic, url, w=3000):
    return {"title": title, "imageinfo": [{
        "url": url, "thumburl": url, "descriptionurl": "https://commons.wikimedia.org/wiki/" + title,
        "width": w, "height": 2000,
        "extmetadata": {"LicenseShortName": {"value": lic}, "Artist": {"value": "<a>Kim</a>"}}}]}


def test_wiki_keeps_only_commercial_licences(requests_mock, monkeypatch):
    for k in ("KTO_API_KEY", "PEXELS_API_KEY", "PIXABAY_API_KEY", "UNSPLASH_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)
    requests_mock.get(WIKI, json={"query": {"pages": {
        "1": wiki_page("File:a.jpg", "CC BY-SA 4.0", "https://up.test/a.jpg"),
        "2": wiki_page("File:b.jpg", "CC BY 4.0", "https://up.test/b.jpg"),
        "3": wiki_page("File:c.jpg", "CC BY-NC 2.0", "https://up.test/c.jpg"),
        "4": wiki_page("File:d.jpg", "Public domain", "https://up.test/d.jpg"),
    }}})
    got = ps.search_wiki("Yufuin", 5)
    assert {p.url for p in got} == {"https://up.test/b.jpg", "https://up.test/d.jpg"}
    assert all(p.author == "Kim" for p in got)


def test_run_downloads_and_writes_credits(tmp_path, requests_mock, monkeypatch):
    for k in ("KTO_API_KEY", "PIXABAY_API_KEY", "UNSPLASH_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("PEXELS_API_KEY", "k")
    requests_mock.get(WIKI, json={"query": {"pages": {}}})
    requests_mock.get("https://api.pexels.com/v1/search", json={"photos": [
        {"src": {"original": "https://px.test/1.jpg"}, "url": "https://pexels.test/p/1",
         "width": 4000, "height": 6000, "alt": "onsen", "photographer": "Lee"}]})
    requests_mock.get("https://px.test/1.jpg", content=b"JPEG", headers={"Content-Type": "image/jpeg"})
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"scenes": [
        {"id": "01", "query_ko": "유후인 료칸", "query_en": "Yufuin ryokan"},
        {"id": "02", "query_ko": "", "query_en": ""},
    ]}), encoding="utf-8")
    rep = ps.run(plan, tmp_path / "photos")
    assert (tmp_path / "photos" / "01.jpg").read_bytes() == b"JPEG"
    assert rep["photos"][0]["license"] == "Pexels License"
    assert rep["missing"][0]["id"] == "02"
    assert "Photo: Lee / Pexels" in (tmp_path / "photos" / "credits.txt").read_text(encoding="utf-8")
