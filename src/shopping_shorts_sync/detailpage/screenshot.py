from __future__ import annotations

from pathlib import Path

from ..browser import launch_browser
from .render import PAGE_WIDTH_PX


def screenshot_detail_page(
    html_path: str | Path,
    png_path: str | Path,
    *,
    chromium_path: str | None = None,
    device_scale_factor: int = 2,
) -> Path:
    """Render the built page to one full-length PNG with the pre-installed Chromium.

    Images are loaded from the local assets folder; we wait for every <img> to finish
    so lazy-loaded images are not captured blank.
    """
    html_path = Path(html_path).resolve()
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    with launch_browser(headless=True, chromium_path=chromium_path) as browser:
        page = browser.new_page(
            viewport={"width": PAGE_WIDTH_PX, "height": 900},
            device_scale_factor=device_scale_factor,
        )
        page.goto(html_path.as_uri(), wait_until="load")
        page.evaluate(
            """() => Promise.all([...document.images].map(img =>
                img.complete ? null : new Promise(res => { img.onload = img.onerror = res; })))"""
        )
        page.screenshot(path=str(png_path), full_page=True)
        page.close()
    return png_path
