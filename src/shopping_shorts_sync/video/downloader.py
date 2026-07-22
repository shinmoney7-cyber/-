"""yt-dlp-based video downloader.

Real downloads require the `yt-dlp` CLI on PATH (or YTDLP_PATH). This
project has no network access to actually run yt-dlp against a real URL,
so this has not been exercised end-to-end -- verify it works in an
environment with real network access before relying on it (same
"not exercised live" caveat as the RPA/API clients -- see
docs/CALIBRATION.md).

Downloading someone else's video and reusing it as source material is a
copyright / "2차 창작" judgment call the owner has explicitly made for
themselves; this module only handles the download mechanics.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class DownloadError(RuntimeError):
    pass


class YtDlpDownloader:
    def __init__(self, ytdlp_path: str = "yt-dlp", timeout: float = 120.0):
        self.ytdlp_path = ytdlp_path
        self.timeout = timeout

    def download(self, url: str, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [self.ytdlp_path, "-f", "mp4", "-o", str(output_path), url],
                check=True,
                timeout=self.timeout,
                capture_output=True,
            )
        except FileNotFoundError as exc:
            raise DownloadError(f"yt-dlp not found on PATH (checked {self.ytdlp_path!r})") from exc
        except subprocess.TimeoutExpired as exc:
            raise DownloadError(f"yt-dlp timed out downloading {url}") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            raise DownloadError(f"yt-dlp failed for {url}: {stderr[:500]}") from exc

        if not output_path.exists():
            raise DownloadError(f"yt-dlp reported success but {output_path} is missing")
        return output_path
