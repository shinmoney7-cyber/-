from __future__ import annotations

from pathlib import Path

from .stitcher import EXPECTED_CLIP_COUNT, StitchError


class MockStitcher:
    """No ffmpeg, no real trimming. Concatenates the raw bytes of the 3
    (mock) clip files so the output is still deterministic and dependent
    on all 3 inputs, without needing ffmpeg installed."""

    def stitch(self, clip_paths: list[Path], output_path: Path, clip_seconds: float = 5.0) -> Path:
        if len(clip_paths) != EXPECTED_CLIP_COUNT:
            raise StitchError(f"expected exactly {EXPECTED_CLIP_COUNT} clips, got {len(clip_paths)}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        parts = [b"MOCK STITCHED VIDEO"]
        for clip in clip_paths:
            parts.append(Path(clip).read_bytes())
        output_path.write_bytes(b"\n---clip---\n".join(parts))
        return output_path
