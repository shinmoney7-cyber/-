from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from shopping_shorts_sync.detailpage import (
    DetailPageSpecError,
    build_detail_page,
    load_detail_spec,
    render_html,
)
from shopping_shorts_sync.detailpage.spec import check_images_exist

# A valid 1x1 PNG, so the screenshot test has a real image to load.
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _write_spec(tmp_path: Path, **overrides) -> Path:
    images = tmp_path / "imgs"
    images.mkdir(exist_ok=True)
    for name in ("black_full01.png", "black_upper01.png", "feature.png"):
        (images / name).write_bytes(TINY_PNG)

    spec = {
        "product_id": "fleece-01",
        "name": "후리스 자켓 <테스트>",
        "headline": "가볍고 따뜻한 데일리 후리스",
        "brand": "온크트리",
        "price": 39000,
        "material": "폴리 100%",
        "colorways": [
            {"name": "블랙", "images": ["imgs/black_full01.png", "imgs/black_upper01.png"]},
        ],
        "features": [
            {"title": "보온성", "body": "두께감 있는 기모 & 안감", "image": "imgs/feature.png"},
            {"title": "가벼움", "body": "무게 부담 없이 입는 후리스"},
        ],
        "size_table": {
            "headers": ["사이즈", "어깨", "총장"],
            "rows": [["FREE", "52", "70"]],
        },
        "notices": ["모니터 환경에 따라 색상 차이가 있을 수 있습니다."],
        "cta_url": "https://example.com/buy",
    }
    spec.update(overrides)
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_spec_resolves_base_dir_and_images(tmp_path):
    spec = load_detail_spec(_write_spec(tmp_path))
    assert spec.product_id == "fleece-01"
    assert spec.price == 39000
    assert spec.base_dir == tmp_path
    check_images_exist(spec)  # does not raise


def test_missing_image_is_reported(tmp_path):
    path = _write_spec(
        tmp_path,
        colorways=[{"name": "블랙", "images": ["imgs/does_not_exist.png"]}],
    )
    spec = load_detail_spec(path)
    with pytest.raises(DetailPageSpecError, match="does_not_exist.png"):
        check_images_exist(spec)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"name": ""}, "'name'"),
        ({"colorways": []}, "'colorways'"),
        ({"colorways": [{"name": "블랙", "images": []}]}, "images"),
        ({"price": -1}, "'price'"),
        ({"price": "39000"}, "'price'"),
        ({"size_table": {"headers": ["사이즈", "총장"], "rows": [["FREE"]]}}, "size_table.rows[0]"),
    ],
)
def test_invalid_spec_is_rejected(tmp_path, overrides, message):
    with pytest.raises(DetailPageSpecError, match=message.replace("[", r"\[")):
        load_detail_spec(_write_spec(tmp_path, **overrides))


def test_invalid_json_is_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(DetailPageSpecError, match="invalid JSON"):
        load_detail_spec(bad)


def test_render_escapes_user_text(tmp_path):
    spec = load_detail_spec(_write_spec(tmp_path))
    html = render_html(
        spec,
        asset_map={
            "imgs/black_full01.png": "assets/01_black_full01.png",
            "imgs/black_upper01.png": "assets/02_black_upper01.png",
            "imgs/feature.png": "assets/03_feature.png",
        },
    )
    assert "후리스 자켓 &lt;테스트&gt;" in html
    assert "<테스트>" not in html
    assert "39,000원" in html
    assert "폴리 100%" in html
    assert 'href="https://example.com/buy"' in html


def test_build_copies_assets_and_writes_index(tmp_path):
    spec = load_detail_spec(_write_spec(tmp_path))
    out = tmp_path / "out"
    result = build_detail_page(spec, out)

    assert result.html_path == out / "index.html"
    html = result.html_path.read_text(encoding="utf-8")
    assert 'src="assets/01_black_full01.png"' in html
    assert 'src="assets/03_feature.png"' in html
    assert (out / "assets" / "01_black_full01.png").read_bytes() == TINY_PNG
    assert (out / "assets" / "03_feature.png").is_file()


def test_build_without_optional_sections(tmp_path):
    path = _write_spec(
        tmp_path,
        price=None,
        brand=None,
        material=None,
        size_table=None,
        notices=[],
        cta_url=None,
        features=[],
    )
    spec = load_detail_spec(path)
    result = build_detail_page(spec, tmp_path / "out")
    html = result.html_path.read_text(encoding="utf-8")
    assert "사이즈 &amp; 소재" not in html
    assert "유의사항" not in html
    assert 'class="cta"' not in html


def test_screenshot_renders_png(tmp_path):
    chromium = Path("/opt/pw-browsers/chromium")
    if not chromium.exists():
        pytest.skip("pre-installed Chromium not available")
    pytest.importorskip("playwright")

    from shopping_shorts_sync.detailpage.screenshot import screenshot_detail_page

    spec = load_detail_spec(_write_spec(tmp_path))
    result = build_detail_page(spec, tmp_path / "out")
    png = screenshot_detail_page(
        result.html_path,
        tmp_path / "out" / "fleece-01.png",
        chromium_path=str(chromium),
        device_scale_factor=1,
    )
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
