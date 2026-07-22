from __future__ import annotations

import hashlib
from pathlib import Path


class MockDownloader:
    """No network, no yt-dlp. Writes a small deterministic placeholder file
    so downstream stitching has a real (if fake) file to operate on."""

    def download(self, url: str, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
        output_path.write_bytes(f"MOCK VIDEO CONTENT for {url} ({digest})".encode("utf-8"))
        return output_path
