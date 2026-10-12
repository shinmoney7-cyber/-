"""
페이스북 페이지 자동 포스팅 (Facebook Graph API)
필요: FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN
"""
import os, json, requests

PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "")
PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
IMAGE_HOST_URL = os.environ.get("IMAGE_HOST_URL", "")

if not all([PAGE_ID, PAGE_TOKEN]):
    print("⚠️  Facebook API 미설정 — 건너뜀")
    exit(0)

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
post_text = content.get("facebook_post", "")
if not post_text:
    post_text = f"🔮 {content.get('hook', '')} {content.get('main_text', '')} {content.get('cta', '')} {content.get('hashtags', '')}"

BASE_URL = "https://graph.facebook.com/v20.0"

if IMAGE_HOST_URL:
    # 이미지 포함 포스트
    image_url = f"{IMAGE_HOST_URL}/card_sq_{meta['date']}.jpg"
    res = requests.post(
        f"{BASE_URL}/{PAGE_ID}/photos",
        params={
            "url": image_url,
            "caption": post_text[:63206],
            "access_token": PAGE_TOKEN,
        }
    )
else:
    # 텍스트만 포스트
    res = requests.post(
        f"{BASE_URL}/{PAGE_ID}/feed",
        params={
            "message": post_text[:63206],
            "access_token": PAGE_TOKEN,
        }
    )

data = res.json()
post_id = data.get("post_id") or data.get("id", "")

if post_id:
    print(f"✅ Facebook 게시 완료: {post_id}")
    meta["facebook_post_id"] = post_id
    with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
else:
    print("❌ Facebook 게시 실패:", data)
    exit(1)
