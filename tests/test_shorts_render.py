import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "shorts_render", Path(__file__).resolve().parents[1] / "tools" / "shorts_render.py"
)
sr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sr)


def test_frame_window_stays_inside_landscape_photo():
    x, y, w, h = sr.frame_window(800, 700, 9 / 16, 1.0, 0.0, 0.5)
    assert x == 0 and y == 0 and h == 700
    assert abs(w / h - 9 / 16) < 1e-9
    x, y, w, h = sr.frame_window(800, 700, 9 / 16, 2.0, 1.0, 1.0)
    assert x + w <= 800 and y + h <= 700


def test_ripple_only_moves_rows_below_waterline():
    img = np.random.default_rng(0).integers(0, 255, (100, 50, 3), dtype=np.uint8)
    out = sr.ripple(img, 0.5, 0.6, 5)
    assert np.array_equal(out[:60], img[:60])
    assert out.shape == img.shape


def test_video_scene_is_cropped_trimmed_and_captioned(tmp_path):
    import json
    import subprocess

    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=size=320x240:rate=30:duration=2", "-pix_fmt", "yuv420p", str(clip)], check=True)
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({
        "size": [180, 320], "fps": 10, "transition": 0.2, "badge": "광고",
        "scenes": [
            {"video": "clip.mp4", "start": 0.5, "dur": 1.0, "text": "Grok"},
            {"end": True, "dur": 0.5, "title": "청귤트립", "lines": ["#01"]},
        ],
    }), encoding="utf-8")
    out = tmp_path / "out.mp4"
    r = sr.Renderer(json.loads(spec_file.read_text(encoding="utf-8")), tmp_path)
    frames = list(r.scene_frames(r.spec["scenes"][0]))
    assert len(frames) == 10 and frames[0].shape == (320, 180, 3)
    dur = r.render(out)
    assert out.exists() and abs(dur - 1.3) < 0.15
