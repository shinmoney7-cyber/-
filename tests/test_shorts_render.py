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
