from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from shopping_shorts_sync.cli import cli
from shopping_shorts_sync.tiktok.analyzer import extract_hashtags, extract_price, extract_video_meta
from shopping_shorts_sync.tiktok.config_gen import generate_remotion_config
from shopping_shorts_sync.tiktok.models import VideoMeta


def _meta(title="피부과 의사들이 선택한 성분?", description="#스킨케어 #PDRN 67,900원") -> VideoMeta:
    return VideoMeta(
        url="https://www.tiktok.com/@test/video/1",
        title=title,
        thumbnail_url="https://example.com/thumb.jpg",
        author="@test",
        raw_description=description,
    )


def test_extract_hashtags():
    tags = extract_hashtags("좋은 제품 #스킨케어 #뷰티 #쿠팡")
    assert tags == ["스킨케어", "뷰티", "쿠팡"]


def test_extract_price_with_comma():
    assert extract_price("지금 67,900원에 구매") == "67,900원"


def test_extract_price_without_comma():
    assert extract_price("단 30000원!") == "30000원"


def test_extract_price_missing():
    assert extract_price("가격 없음") == ""


def test_extract_video_meta_dry_run():
    meta = extract_video_meta("https://www.tiktok.com/@x/video/999", dry_run=True)
    assert meta.url == "https://www.tiktok.com/@x/video/999"
    assert meta.title  # non-empty
    assert meta.thumbnail_url


def test_generate_remotion_config_has_required_keys():
    cfg = generate_remotion_config(_meta())
    d = cfg.to_dict()
    for key in ("hookLine1", "hookLine2", "hookSub", "productName", "benefits", "price"):
        assert key in d, f"missing key: {key}"
    assert isinstance(d["benefits"], list)
    assert len(d["benefits"]) > 0


def test_generate_remotion_config_price_override():
    cfg = generate_remotion_config(_meta(), override_price="99,000원")
    assert cfg.price == "99,000원"


def test_generate_remotion_config_extracts_price_from_description():
    meta = _meta(description="PDRN 앰플 #뷰티 67,900원 할인")
    cfg = generate_remotion_config(meta)
    assert cfg.price == "67,900원"


def test_cli_tiktok_analyze_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["tiktok", "analyze", "--url", "https://www.tiktok.com/@x/video/1", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "hookLine1" in result.output


def test_cli_tiktok_to_config_dry_run(tmp_path):
    out = tmp_path / "config.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tiktok", "to-config",
            "--url", "https://www.tiktok.com/@x/video/1",
            "--output", str(out),
            "--price", "67,900원",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["price"] == "67,900원"
    assert "hookLine1" in data
