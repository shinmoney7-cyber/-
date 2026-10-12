"""
인스타그램 자동 포스팅 (Instagram Graph API)
필요: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID
페이스북 개발자 앱 → Instagram Basic Display / Graph API
"""
import os, json, requests

ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
USER_ID = os.environ.get("INSTAGRAM_USER_ID", "")
# 이미지는 공개 URL 필요 — GitHub Pages or Cloudflare R2 사용
IMAGE_HOST_URL = os.environ.get("IMAGE_HOST_URL", "")

if not all([ACCESS_TOKEN, USER_ID]):
    print("⚠️  Instagram API 미설정 — 건너뜀")
    exit(0)

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
caption = content.get("instagram_caption", "")
if not caption:
    caption = f"{content.get('hook', '')} {content.get('main_text', '')} {content.get('hashtags', '')}"

# Instagram Graph API는 이미지 공개 URL 필요
# 이미지가 GitHub Pages에 있거나 별도 호스팅 필요
# IMAGE_HOST_URL 미설정 시 텍스트만 fallback
if not IMAGE_HOST_URL:
    print("⚠️  IMAGE_HOST_URL 미설정 — 이미지 없이 텍스트 캡션만 준비됨")
    print(f"캡션 (수동 게시용):\n{caption}")
    meta["instagram_caption_ready"] = caption
    with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    exit(0)

image_url = f"{IMAGE_HOST_URL}/card_sq_{meta['date']}.jpg"

# 1. 미디어 컨테이너 생성
container_res = requests.post(
    f"https://graph.instagram.com/v20.0/{USER_ID}/media",
    params={
        "image_url": image_url,
        "caption": caption[:2200],  # Instagram 최대 2200자
        "access_token": ACCESS_TOKEN,
    }
)
container_data = container_res.json()
container_id = container_data.get("id", "")

if not container_id:
    print("❌ Instagram 컨테이너 생성 실패:", container_data)
    exit(1)

print(f"✅ Instagram 컨테이너 생성: {container_id}")

# 2. 게시
publish_res = requests.post(
    f"https://graph.instagram.com/v20.0/{USER_ID}/media_publish",
    params={
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN,
    }
)
publish_data = publish_res.json()
media_id = publish_data.get("id", "")

if media_id:
    print(f"✅ Instagram 게시 완료: {media_id}")
    meta["instagram_media_id"] = media_id
    with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
else:
    print("❌ Instagram 게시 실패:", publish_data)
    exit(1)
