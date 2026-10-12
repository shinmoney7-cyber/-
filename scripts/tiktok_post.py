"""
TikTok Content Posting API — 드래프트 업로드
사전 설정 필요:
  GitHub Secrets: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
  TikTok Developer: https://developers.tiktok.com
"""
import os
import json
import requests

CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("TIKTOK_REFRESH_TOKEN", "")

if not all([CLIENT_KEY, CLIENT_SECRET, REFRESH_TOKEN]):
    print("⚠️  TikTok API 미설정 — 이메일 알림만 전송")
    exit(0)

# 메타데이터 로드
with open("scripts/tiktok_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

# 1. Access Token 갱신
token_res = requests.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    data={
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
token_data = token_res.json()
access_token = token_data.get("access_token", "")
new_refresh = token_data.get("refresh_token", REFRESH_TOKEN)

if not access_token:
    print("❌ Access Token 갱신 실패:", token_data)
    exit(1)

print("✅ Access Token 갱신 완료")

# refresh token 변경 시 콘솔에 출력 (GitHub Secret 수동 업데이트 필요)
if new_refresh != REFRESH_TOKEN:
    print(f"⚠️  TIKTOK_REFRESH_TOKEN 갱신됨 — GitHub Secret 업데이트 필요")

# 2. Photo Post 초기화
caption = meta["caption"][:4000]

init_res = requests.post(
    "https://open.tiktokapis.com/v2/post/publish/content/init/",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    },
    json={
        "post_info": {
            "title": caption,
            "privacy_level": "SELF_ONLY",  # 드래프트: 본인만 보기
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "is_aigc": True,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "photo_cover_index": 0,
            "photo_images": [],  # 아래에서 업로드 후 추가
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO"
    }
)

init_data = init_res.json()
print("포스트 초기화:", init_data)

# 이미지 파일 업로드 필요 시 처리 (TikTok API photo upload 절차)
publish_id = init_data.get("data", {}).get("publish_id", "")
if publish_id:
    print(f"✅ TikTok 드래프트 생성 완료 — publish_id: {publish_id}")
    meta["tiktok_publish_id"] = publish_id
    with open("scripts/tiktok_output/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
else:
    print("❌ TikTok 게시 실패:", init_data)
    exit(1)
