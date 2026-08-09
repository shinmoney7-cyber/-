from __future__ import annotations

import abc
import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# Target: 1080×1920 H.264/AAC MP4 (Instagram Reels spec)
VIDEO_W = 1080
VIDEO_H = 1920
VIDEO_FPS = 30
VIDEO_DURATION_S = 30  # default short duration


class VideoRenderer(abc.ABC):
    @abc.abstractmethod
    def render(
        self,
        image_paths: list[str],
        audio_path: str | None,
        output_path: str,
        *,
        duration_per_image: float | None = None,
        total_duration: float = VIDEO_DURATION_S,
    ) -> str:
        """Combine images + optional audio into a 1080×1920 MP4. Returns output_path."""

    @abc.abstractmethod
    def extract_thumbnail(self, video_path: str, output_path: str, *, at_second: float = 0.5) -> str:
        """Extract a single frame as JPEG thumbnail. Returns output_path."""


class FFmpegRenderer(VideoRenderer):
    """Renders shorts via FFmpeg. Requires ffmpeg in PATH."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self._ffmpeg = ffmpeg_path

    def _require_ffmpeg(self) -> None:
        if not shutil.which(self._ffmpeg):
            raise RuntimeError(
                f"ffmpeg not found at {self._ffmpeg!r}. "
                "Install ffmpeg or set FFMPEG_PATH in .env."
            )

    def render(
        self,
        image_paths: list[str],
        audio_path: str | None,
        output_path: str,
        *,
        duration_per_image: float | None = None,
        total_duration: float = VIDEO_DURATION_S,
    ) -> str:
        self._require_ffmpeg()
        if not image_paths:
            raise ValueError("at least one image is required")

        n = len(image_paths)
        dur_each = duration_per_image or total_duration / n
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Build concat input file
            concat_file = os.path.join(tmpdir, "concat.txt")
            with open(concat_file, "w", encoding="utf-8") as cf:
                for img in image_paths:
                    abs_img = os.path.abspath(img)
                    cf.write(f"file '{abs_img}'\n")
                    cf.write(f"duration {dur_each:.3f}\n")
                # Repeat last frame to avoid ffmpeg trimming the last segment
                cf.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

            cmd = [
                self._ffmpeg, "-y",
                "-f", "concat", "-safe", "0", "-i", concat_file,
            ]

            if audio_path and os.path.exists(audio_path):
                cmd += ["-i", audio_path, "-shortest"]

            cmd += [
                "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
                       f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2:black",
                "-r", str(VIDEO_FPS),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ]

            if audio_path and os.path.exists(audio_path):
                cmd += ["-c:a", "aac", "-b:a", "128k"]

            cmd.append(output_path)

            logger.info("ffmpeg: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg failed (code {result.returncode}):\n{result.stderr[-1000:]}"
                )

        logger.info("video rendered: %s", output_path)
        return output_path

    def extract_thumbnail(self, video_path: str, output_path: str, *, at_second: float = 0.5) -> str:
        self._require_ffmpeg()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        cmd = [
            self._ffmpeg, "-y",
            "-ss", str(at_second),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg thumbnail failed: {result.stderr[-500:]}")
        return output_path


class MockVideoRenderer(VideoRenderer):
    """Creates a tiny stub MP4 without calling ffmpeg."""

    # Minimal valid MP4 container (ftyp + mdat box, ~40 bytes)
    _STUB_MP4 = (
        b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41"
        b"\x00\x00\x00\x08mdat"
    )

    def render(self, image_paths, audio_path, output_path, **_) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(self._STUB_MP4)
        logger.info("mock video rendered: %s", output_path)
        return output_path

    def extract_thumbnail(self, video_path: str, output_path: str, **_) -> str:
        # Reuse the 1×1 JPEG stub
        from .images import MockImageGenerator
        from .images import ImageSpec
        MockImageGenerator().generate(
            ImageSpec(role="hook", headline="", body="", product_name=""), output_path
        )
        return output_path
