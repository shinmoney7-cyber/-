from __future__ import annotations

import json
from pathlib import Path

from ..models import Product
from .prompt import Scene

HIX_IMAGE_TO_VIDEO_URL = "https://hix.ai/image-to-video"


def export_hix_pack(product: Product, script_id: int, scenes: list[Scene], duration: int, out_dir: str | Path) -> Path:
    """HIX AI has no public developer API, so instead of calling it this writes
    a prompt pack (image + one prompt per AIDA scene) to paste into the HIX AI
    image-to-video web tool by hand. Returns the markdown file path."""
    out_dir = Path(out_dir) / product.id
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "product_id": product.id,
        "product_name": product.name,
        "script_id": script_id,
        "image": product.thumbnail,
        "duration_seconds": duration,
        "aspect_ratio": "9:16",
        "tool_url": HIX_IMAGE_TO_VIDEO_URL,
        "scenes": [{"stage": s.stage, "caption": s.caption, "prompt": s.prompt} for s in scenes],
    }
    (out_dir / "hix_prompts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# HIX AI 영상 프롬프트 - {product.name}",
        "",
        f"1. {HIX_IMAGE_TO_VIDEO_URL} 접속",
        f"2. 이미지 업로드: {product.thumbnail}",
        f"3. 비율 9:16, 길이 {duration}초로 설정 후 아래 씬 프롬프트를 하나씩 붙여넣어 생성",
        "",
    ]
    for i, s in enumerate(scenes, start=1):
        lines += [f"## 씬 {i} - {s.stage}", "", f"자막: {s.caption}", "", "```", s.prompt, "```", ""]
    md_path = out_dir / "hix_prompts.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
