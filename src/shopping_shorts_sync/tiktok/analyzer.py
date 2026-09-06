from __future__ import annotations

import re

from .models import VideoMeta

_OEMBED_URL = "https://www.tiktok.com/oembed"

_MOCK_VIDEO: VideoMeta = VideoMeta(
    url="https://www.tiktok.com/@example/video/1234567890",
    title="피부과 의사들이 선택한 성분? 🔬 PDRN + 콜라겐 앰플 후기 #스킨케어 #뷰티 #쿠팡직구",
    thumbnail_url="https://example.com/mock-thumbnail.jpg",
    author="@beauty_lover",
    raw_description="피부과 의사들이 선택한 성분? 🔬 PDRN + 콜라겐 앰플 후기 #스킨케어 #뷰티 #쿠팡직구",
)


def fetch_oembed(url: str) -> dict:
    import urllib.request

    api_url = f"{_OEMBED_URL}?url={urllib.parse.quote(url, safe='')}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "shopping-shorts-sync/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        import json

        return json.loads(resp.read().decode("utf-8"))


def _clean_title(title: str) -> str:
    """Remove hashtags and extra whitespace."""
    return re.sub(r"#\S+", "", title).strip()


def extract_video_meta(url: str, dry_run: bool = False) -> VideoMeta:
    if dry_run:
        return VideoMeta(
            url=url,
            title=_MOCK_VIDEO.title,
            thumbnail_url=_MOCK_VIDEO.thumbnail_url,
            author=_MOCK_VIDEO.author,
            raw_description=_MOCK_VIDEO.raw_description,
        )

    import urllib.parse

    data = fetch_oembed(url)
    title = data.get("title", "")
    return VideoMeta(
        url=url,
        title=_clean_title(title),
        thumbnail_url=data.get("thumbnail_url", ""),
        author=data.get("author_name", ""),
        raw_description=title,
    )


def extract_hashtags(text: str) -> list[str]:
    return re.findall(r"#(\S+)", text)


def extract_price(text: str) -> str:
    """Find patterns like 67,900원 or 67900원."""
    match = re.search(r"(\d[\d,]+)원", text)
    if match:
        return match.group(0)
    return ""
