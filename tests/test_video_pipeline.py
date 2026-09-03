import dataclasses

import pytest

from shopping_shorts_sync.config import load_config
from shopping_shorts_sync.video import build_downloader, build_stitcher
from shopping_shorts_sync.video.mock_downloader import MockDownloader
from shopping_shorts_sync.video.mock_stitcher import MockStitcher
from shopping_shorts_sync.video.pipeline import VideoPipelineError, generate_stitched_video
from shopping_shorts_sync.video.stitcher import StitchError


def _config(**overrides):
    config = load_config(env_file="/nonexistent/.env")
    return dataclasses.replace(config, **overrides)


def test_build_downloader_mock_by_default():
    assert isinstance(build_downloader(_config()), MockDownloader)


def test_build_stitcher_mock_by_default():
    assert isinstance(build_stitcher(_config()), MockStitcher)


def test_mock_downloader_writes_deterministic_file(tmp_path):
    downloader = MockDownloader()
    out = tmp_path / "clip.mp4"
    downloader.download("https://youtube.com/watch?v=abc", out)

    assert out.exists()
    content_a = out.read_bytes()
    out2 = tmp_path / "clip2.mp4"
    downloader.download("https://youtube.com/watch?v=abc", out2)
    assert out2.read_bytes() == content_a


def test_mock_stitcher_requires_exactly_three_clips(tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"x")
    stitcher = MockStitcher()
    with pytest.raises(StitchError):
        stitcher.stitch([clip, clip], tmp_path / "out.mp4")


def test_mock_stitcher_combines_all_three_inputs(tmp_path):
    clips = []
    for i in range(3):
        clip = tmp_path / f"clip{i}.mp4"
        clip.write_bytes(f"CLIP{i}".encode("utf-8"))
        clips.append(clip)

    stitcher = MockStitcher()
    out = tmp_path / "stitched.mp4"
    stitcher.stitch(clips, out)

    content = out.read_bytes()
    assert b"CLIP0" in content
    assert b"CLIP1" in content
    assert b"CLIP2" in content


def test_generate_stitched_video_end_to_end_mock(tmp_path):
    config = _config(video_output_dir=str(tmp_path))
    urls = ["https://youtube.com/watch?v=a", "https://youtube.com/watch?v=b", "https://instagram.com/p/c/"]

    output_path = generate_stitched_video(urls, "product-1", config)

    assert output_path.exists()
    assert output_path == tmp_path / "product-1" / "stitched.mp4"


def test_generate_stitched_video_requires_exactly_three_urls(tmp_path):
    config = _config(video_output_dir=str(tmp_path))
    with pytest.raises(VideoPipelineError):
        generate_stitched_video(["only-one-url"], "product-1", config)
