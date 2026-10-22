"""
페이스북 페이지 자동 포스팅 (Facebook Graph API v20.0)
- Reels 영상 우선, 없으면 이미지, 없으면 텍스트
필요: FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN
"""
import os, json, requests, time
from pathlib import Path

PAGE_ID    = os.environ.get("FACEBOOK_PAGE_ID", "")
PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
IMAGE_HOST = os.environ.get("IMAGE_HOST_URL", "").rstrip("/")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

if not all([PAGE_ID, PAGE_TOKEN]):
    print("⚠️  Facebook API 미설정 — 건너뜀")
    exit(0)

meta_path = Path("scripts/sns_output") / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path("scripts/sns_output/meta.json")

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
date    = meta.get("date", "")
post_text = content.get("facebook_post", "")
if not post_text:
    post_text = (
        f"🔮 {content.get('hook','')}\n\n"
        f"{content.get('main_text','')}\n\n"
        f"{content.get('cta','')} 👉 forms.gle/t2sSNES5NYow77vz5\n\n"
        f"{content.get('hashtags','#사주 #운세')}"
    )

BASE = f"https://graph.facebook.com/v20.0"
params_base = {"access_token": PAGE_TOKEN}

# 미디어 타입 결정
video_path_local = meta.get("video_shorts") or meta.get("video_path", "")
has_video = video_path_local and IMAGE_HOST and Path(video_path_local).exists()

if has_video:
    # ── Facebook Reels 영상 업로드 ─────────────────────────────
    video_filename = Path(video_path_local).name
    video_url = f"{IMAGE_HOST}/sns_output/{ACCOUNT_ID}/{video_filename}"
    print(f"  🎬 Facebook Reels 업로드...")

    # 1단계: 업로드 세션 시작
    init_res = requests.post(
        f"{BASE}/{PAGE_ID}/video_reels",
        params={**params_base, "upload_phase": "start"},
    )
    init_data = init_res.json()
    upload_session_id = init_data.get("upload_session_id", "")
    video_id          = init_data.get("video_id", "")
    upload_url        = init_data.get("upload_url", "")

    if upload_session_id and upload_url:
        # 2단계: 영상 파일 업로드 (URL 또는 바이너리)
        with open(video_path_local, "rb") as vf:
            video_bytes = vf.read()
        video_size = len(video_bytes)

        up_res = requests.put(
            upload_url,
            headers={
                "Authorization": f"OAuth {PAGE_TOKEN}",
                "Content-Type": "video/mp4",
                "offset": "0",
                "file_size": str(video_size),
            },
            data=video_bytes,
            timeout=300,
        )

        if up_res.status_code in (200, 201, 204):
            # 3단계: 게시
            pub_res = requests.post(
                f"{BASE}/{PAGE_ID}/video_reels",
                params={
                    **params_base,
                    "upload_phase": "finish",
                    "video_state": "PUBLISHED",
                    "upload_session_id": upload_session_id,
                    "description": post_text[:5000],
                    "title": content.get("hook", "오늘의 사주 운세")[:100],
                },
            )
            pub_data = pub_res.json()
            if pub_data.get("success"):
                print(f"✅ Facebook Reels 완료: {video_id}")
                meta["facebook_post_id"] = video_id
                meta["facebook_type"] = "reel"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                exit(0)
            else:
                print(f"  ⚠️ Reels 게시 실패 — 이미지 fallback: {pub_data}")
        else:
            print(f"  ⚠️ 영상 업로드 실패 ({up_res.status_code}) — 이미지 fallback")
    else:
        print(f"  ⚠️ 업로드 세션 실패 — 이미지 fallback: {init_data}")

# ── 이미지 포스트 ──────────────────────────────────────────────
if IMAGE_HOST:
    image_url = f"{IMAGE_HOST}/sns_output/{ACCOUNT_ID}/card_sq_{date}.jpg"
    print("  📷 Facebook 이미지 포스트...")
    res = requests.post(
        f"{BASE}/{PAGE_ID}/photos",
        params={
            **params_base,
            "url": image_url,
            "caption": post_text[:63206],
        }
    )
else:
    print("  📝 Facebook 텍스트 포스트...")
    res = requests.post(
        f"{BASE}/{PAGE_ID}/feed",
        params={**params_base, "message": post_text[:63206]},
    )

data = res.json()
post_id = data.get("post_id") or data.get("id", "")

if post_id:
    print(f"✅ Facebook 게시 완료: {post_id}")
    meta["facebook_post_id"] = post_id
    meta["facebook_type"] = "image" if IMAGE_HOST else "text"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
else:
    print("❌ Facebook 게시 실패:", data)
    exit(1)
