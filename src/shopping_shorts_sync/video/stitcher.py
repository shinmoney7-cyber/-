"""ffmpeg-based clip trimming + concatenation ("자동 짜깁기").

Trims each of the 3 input clips to `clip_seconds` from its start, then
concatenates them in the given order into one output file. Requires the
`ffmpeg` CLI on PATH (or FFMPEG_PATH). Not exercised against real video
files in this environment (no network to fetch a real source clip to test
with) -- verify with a real yt-dlp download before relying on --live (see
docs/CALIBRATION.md).
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

EXPECTED_CLIP_COUNT = 3


class StitchError(RuntimeError):
    pass


class FfmpegStitcher:
    def __init__(self, ffmpeg_path: str = "ffmpeg", timeout: float = 120.0):
        self.ffmpeg_path = ffmpeg_path
        self.timeout = timeout

    def stitch(self, clip_paths: list[Path], output_path: Path, clip_seconds: float = 5.0) -> Path:
        if len(clip_paths) != EXPECTED_CLIP_COUNT:
            raise StitchError(f"expected exactly {EXPECTED_CLIP_COUNT} clips, got {len(clip_paths)}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            trimmed = []
            for i, clip in enumerate(clip_paths):
                trimmed_path = Path(tmp_dir) / f"trimmed_{i}.mp4"
                self._trim(Path(clip), trimmed_path, clip_seconds)
                trimmed.append(trimmed_path)

            concat_list = Path(tmp_dir) / "concat.txt"
            concat_list.write_text("".join(f"file '{p}'\n" for p in trimmed), encoding="utf-8")

            try:
                subprocess.run(
                    [
                        self.ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                        "-i", str(concat_list), "-c", "copy", str(output_path),
                    ],
                    check=True, timeout=self.timeout, capture_output=True,
                )
            except FileNotFoundError as exc:
                raise StitchError(f"ffmpeg not found on PATH (checked {self.ffmpeg_path!r})") from exc
            except subprocess.TimeoutExpired as exc:
                raise StitchError("ffmpeg concat timed out") from exc
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
                raise StitchError(f"ffmpeg concat failed: {stderr[:500]}") from exc

        return output_path

    def _trim(self, clip_path: Path, out_path: Path, seconds: float) -> None:
        try:
            subprocess.run(
                [self.ffmpeg_path, "-y", "-i", str(clip_path), "-t", str(seconds), "-c", "copy", str(out_path)],
                check=True, timeout=self.timeout, capture_output=True,
            )
        except FileNotFoundError as exc:
            raise StitchError(f"ffmpeg not found on PATH (checked {self.ffmpeg_path!r})") from exc
        except subprocess.TimeoutExpired as exc:
            raise StitchError(f"ffmpeg trim timed out for {clip_path}") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            raise StitchError(f"ffmpeg trim failed for {clip_path}: {stderr[:500]}") from exc
