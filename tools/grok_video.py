"""Turn a still photo into a short clip with xAI Grok Imagine (image-to-video).

Usage:
    export XAI_API_KEY=...            # never commit the key
    python tools/grok_video.py photo.jpg "Only the water gently ripples..." out.mp4 \
        [--duration 6] [--model grok-imagine-video] [--dry-run]

Flow (xAI REST API, asynchronous):
    POST {base}/videos/generations  -> {"request_id": ...}
    GET  {base}/videos/{request_id} -> poll until status is done, then download the video URL

The exact request field names can change between model versions. They are
kept configurable (--image-field, --model, XAI_API_BASE) so you can match the
current xAI API reference without editing code. Check it once before the
first paid run, and use --dry-run to see the request body without calling the API.
Each call is billed per generated second by xAI.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

DEFAULT_BASE = "https://api.x.ai/v1"
DONE = {"done", "completed", "succeeded", "success"}
FAILED = {"failed", "error", "expired", "cancelled", "canceled"}


def image_reference(src: str) -> str:
    """Public URLs are passed through; local files become a base64 data URI."""
    if src.startswith(("http://", "https://", "data:")):
        return src
    path = Path(src)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def build_payload(image: str, prompt: str, model: str, duration: float,
                  image_field: str, aspect_ratio: str | None) -> dict:
    body = {"model": model, "prompt": prompt, "duration": duration, image_field: image_reference(image)}
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    return body


def find_video_url(obj) -> str | None:
    """Search a status response for the generated video URL, wherever it is nested."""
    if isinstance(obj, dict):
        for key in ("video_url", "url"):
            v = obj.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
        for v in obj.values():
            found = find_video_url(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_video_url(v)
            if found:
                return found
    return None


def generate(image: str, prompt: str, out: Path, *, model: str, duration: float,
             image_field: str, aspect_ratio: str | None, base: str, key: str,
             poll_seconds: float = 5.0, timeout: float = 600.0, session=requests) -> Path:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = build_payload(image, prompt, model, duration, image_field, aspect_ratio)
    r = session.post(f"{base}/videos/generations", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    request_id = r.json().get("request_id") or r.json().get("id")
    if not request_id:
        raise RuntimeError(f"no request_id in response: {r.text[:300]}")
    deadline = time.monotonic() + timeout
    while True:
        s = session.get(f"{base}/videos/{request_id}", headers=headers, timeout=60)
        s.raise_for_status()
        data = s.json()
        status = str(data.get("status", "")).lower()
        url = find_video_url(data)
        if status in FAILED:
            raise RuntimeError(f"generation {request_id} {status}: {json.dumps(data)[:300]}")
        if url and (status in DONE or not status):
            break
        if time.monotonic() > deadline:
            raise TimeoutError(f"generation {request_id} still '{status}' after {timeout}s")
        time.sleep(poll_seconds)
    video = session.get(url, timeout=300)
    video.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(video.content)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="local photo path or public image URL")
    ap.add_argument("prompt", help="English motion prompt (see docs/travel-shorts/CODEX.md)")
    ap.add_argument("out", type=Path, help="output .mp4 path")
    ap.add_argument("--duration", type=float, default=6)
    ap.add_argument("--model", default=os.environ.get("XAI_VIDEO_MODEL", "grok-imagine-video"))
    ap.add_argument("--image-field", default=os.environ.get("XAI_IMAGE_FIELD", "image_url"))
    ap.add_argument("--aspect-ratio", default=None, help="e.g. 9:16 (image-to-video may follow the photo instead)")
    ap.add_argument("--dry-run", action="store_true", help="print the request body without calling the API")
    a = ap.parse_args(argv)

    if a.dry_run:
        body = build_payload(a.image, a.prompt, a.model, a.duration, a.image_field, a.aspect_ratio)
        ref = body[a.image_field]
        if ref.startswith("data:"):
            body[a.image_field] = ref[:40] + f"...({len(ref)} chars)"
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    key = os.environ.get("XAI_API_KEY")
    if not key:
        print("XAI_API_KEY is not set", file=sys.stderr)
        return 2
    path = generate(a.image, a.prompt, a.out, model=a.model, duration=a.duration,
                    image_field=a.image_field, aspect_ratio=a.aspect_ratio,
                    base=os.environ.get("XAI_API_BASE", DEFAULT_BASE), key=key)
    print(f"saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
