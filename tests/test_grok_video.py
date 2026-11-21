import importlib.util
from pathlib import Path

import requests

spec = importlib.util.spec_from_file_location(
    "grok_video", Path(__file__).resolve().parents[1] / "tools" / "grok_video.py"
)
gv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gv)

BASE = "https://api.example.test/v1"


def test_local_image_becomes_data_uri(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"\x89PNG fake")
    ref = gv.image_reference(str(img))
    assert ref.startswith("data:image/png;base64,")
    assert gv.image_reference("https://x.test/a.jpg") == "https://x.test/a.jpg"


def test_find_video_url_nested():
    assert gv.find_video_url({"status": "done", "video": {"url": "https://cdn.test/v.mp4"}}) == "https://cdn.test/v.mp4"
    assert gv.find_video_url({"status": "processing"}) is None


def test_generate_polls_and_downloads(tmp_path, requests_mock):
    requests_mock.post(f"{BASE}/videos/generations", json={"request_id": "r1"})
    requests_mock.get(f"{BASE}/videos/r1", [
        {"json": {"status": "processing"}},
        {"json": {"status": "done", "video": {"url": "https://cdn.test/v.mp4"}}},
    ])
    requests_mock.get("https://cdn.test/v.mp4", content=b"MP4DATA")
    out = gv.generate("https://x.test/a.jpg", "water ripples", tmp_path / "o.mp4",
                      model="m", duration=6, image_field="image_url", aspect_ratio=None,
                      base=BASE, key="k", poll_seconds=0)
    assert out.read_bytes() == b"MP4DATA"
    body = requests_mock.request_history[0].json()
    assert body["image_url"] == "https://x.test/a.jpg" and body["duration"] == 6
    assert requests_mock.request_history[0].headers["Authorization"] == "Bearer k"


def test_generate_raises_on_failure(tmp_path, requests_mock):
    requests_mock.post(f"{BASE}/videos/generations", json={"request_id": "r2"})
    requests_mock.get(f"{BASE}/videos/r2", json={"status": "failed"})
    try:
        gv.generate("https://x.test/a.jpg", "p", tmp_path / "o.mp4", model="m", duration=6,
                    image_field="image_url", aspect_ratio=None, base=BASE, key="k", poll_seconds=0)
    except RuntimeError as e:
        assert "failed" in str(e)
    else:
        raise AssertionError("expected RuntimeError")
