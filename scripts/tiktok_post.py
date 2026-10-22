"""
TikTok Content Posting API — 영상/포토 업로드
- video_gen.py 생성 MP4 영상 우선
- 없으면 이미지 카드 포토 포스트
필요: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
"""
import os, json, requests, time
from pathlib import Path

CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("TIKTOK_REFRESH_TOKEN", "")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

if not all([CLIENT_KEY, CLIENT_SECRET, REFRESH_TOKEN]):
    print("⚠️  TikTok API 미설정 — 건너뜀")
    exit(0)

meta_path = Path("scripts/sns_output") / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path("scripts/tiktok_output/meta.json")
if not meta_path.exists():
    meta_path = Path("scripts/sns_output/meta.json")

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
caption = content.get("tiktok_script", content.get("hook", ""))[:4000]
if not caption:
    caption = f"{content.get('hook','')} {content.get('cta','')}"

# 1. Access Token 갱신
token_res = requests.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    data={
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
token_data = token_res.json()
access_token = token_data.get("access_token", "")
new_refresh = token_data.get("refresh_token", REFRESH_TOKEN)

if not access_token:
    print("❌ TikTok Access Token 갱신 실패:", token_data)
    exit(1)

print("✅ TikTok Access Token 갱신 완료")
if new_refresh != REFRESH_TOKEN:
    print("⚠️  TIKTOK_REFRESH_TOKEN 갱신됨 — GitHub Secret 수동 업데이트 필요")

HEADERS = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json; charset=UTF-8",
}

# 2. 영상 파일 확인
video_path = meta.get("video_shorts") or meta.get("video_path", "")
has_video = video_path and Path(video_path).exists()

if has_video:
    # ── 영상 업로드 (VIDEO) ────────────────────────────────
    print(f"  🎬 TikTok 영상 업로드: {Path(video_path).name}")
    video_size = Path(video_path).stat().st_size

    init_res = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=HEADERS,
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "is_aigc": True,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        },
    )
    init_data = init_res.json()
    upload_url = init_data.get("data", {}).get("upload_url", "")
    publish_id = init_data.get("data", {}).get("publish_id", "")

    if not upload_url:
        print("❌ TikTok 영상 업로드 초기화 실패:", init_data)
        has_video = False  # 이미지 fallback
    else:
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        upload_res = requests.put(
            upload_url,
            headers={
                "Content-Range": f"bytes 0-{video_size-1}/{video_size}",
                "Content-Type": "video/mp4",
            },
            data=video_bytes,
            timeout=300,
        )

        if upload_res.status_code in (200, 201):
            print(f"  ✅ TikTok 영상 업로드 완료 — publish_id: {publish_id}")
            meta["tiktok_publish_id"] = publish_id
            meta["tiktok_type"] = "video"
        else:
            print(f"  ❌ 영상 업로드 실패: {upload_res.status_code}")
            has_video = False

if not has_video:
    # ── 이미지 포토 포스트 fallback ──────────────────────────
    print("  📸 TikTok 이미지 포스트 시도...")
    init_res = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/content/init/",
        headers=HEADERS,
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "is_aigc": True,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "photo_cover_index": 0,
                "photo_images": [],
            },
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
        },
    )
    init_data = init_res.json()
    publish_id = init_data.get("data", {}).get("publish_id", "")
    if publish_id:
        print(f"  ✅ TikTok 포토 드래프트 생성: {publish_id}")
        meta["tiktok_publish_id"] = publish_id
        meta["tiktok_type"] = "photo"
    else:
        print("❌ TikTok 게시 실패:", init_data)
        exit(1)

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print("✅ TikTok 완료")
