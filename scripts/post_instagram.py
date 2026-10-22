"""
인스타그램 자동 포스팅 (Instagram Graph API)
- 영상(Reels) 우선, 없으면 이미지 카드
- Reels: 최대 도달률 + 알고리즘 부스트
필요: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID
"""
import os, json, requests, time
from pathlib import Path

ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
USER_ID = os.environ.get("INSTAGRAM_USER_ID", "")
IMAGE_HOST_URL = os.environ.get("IMAGE_HOST_URL", "").rstrip("/")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

if not all([ACCESS_TOKEN, USER_ID]):
    print("⚠️  Instagram API 미설정 — 건너뜀")
    exit(0)

meta_path = Path("scripts/sns_output") / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path("scripts/sns_output/meta.json")

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
caption = content.get("instagram_caption", "")
if not caption:
    caption = f"{content.get('hook', '')}\n\n{content.get('main_text', '')}\n\n{content.get('hashtags', '')}"
caption = caption[:2200]

BASE = f"https://graph.instagram.com/v20.0"


def wait_container(container_id: str, max_wait: int = 60) -> bool:
    for _ in range(max_wait // 5):
        r = requests.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code,status", "access_token": ACCESS_TOKEN},
        )
        status = r.json().get("status_code", "")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            print(f"  ❌ 컨테이너 오류: {r.json()}")
            return False
        time.sleep(5)
    return False


def post_reels(video_url: str) -> bool:
    print("  🎬 Reels 업로드 시도...")
    r = requests.post(
        f"{BASE}/{USER_ID}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": ACCESS_TOKEN,
        },
    )
    data = r.json()
    cid = data.get("id", "")
    if not cid:
        print(f"  ❌ Reels 컨테이너 실패: {data}")
        return False

    print(f"  ⏳ Reels 인코딩 대기 ({cid})...")
    if not wait_container(cid, max_wait=120):
        print("  ❌ Reels 인코딩 타임아웃")
        return False

    pub = requests.post(
        f"{BASE}/{USER_ID}/media_publish",
        params={"creation_id": cid, "access_token": ACCESS_TOKEN},
    )
    pub_data = pub.json()
    media_id = pub_data.get("id", "")
    if media_id:
        print(f"  ✅ Instagram Reels 게시: {media_id}")
        meta["instagram_reels_id"] = media_id
        return True
    print(f"  ❌ Reels 게시 실패: {pub_data}")
    return False


def post_image(image_url: str) -> bool:
    print("  🖼️  이미지 게시 시도...")
    r = requests.post(
        f"{BASE}/{USER_ID}/media",
        params={"image_url": image_url, "caption": caption, "access_token": ACCESS_TOKEN},
    )
    data = r.json()
    cid = data.get("id", "")
    if not cid:
        print(f"  ❌ 이미지 컨테이너 실패: {data}")
        return False

    pub = requests.post(
        f"{BASE}/{USER_ID}/media_publish",
        params={"creation_id": cid, "access_token": ACCESS_TOKEN},
    )
    pub_data = pub.json()
    media_id = pub_data.get("id", "")
    if media_id:
        print(f"  ✅ Instagram 이미지 게시: {media_id}")
        meta["instagram_media_id"] = media_id
        return True
    print(f"  ❌ 이미지 게시 실패: {pub_data}")
    return False


success = False

# 1순위: Reels 영상 (video_path가 있고 IMAGE_HOST_URL 설정된 경우)
video_path = meta.get("video_shorts") or meta.get("video_path", "")
if video_path and IMAGE_HOST_URL:
    video_filename = Path(video_path).name
    video_url = f"{IMAGE_HOST_URL}/sns_output/{ACCOUNT_ID}/{video_filename}"
    success = post_reels(video_url)

# 2순위: 이미지 카드
if not success and IMAGE_HOST_URL:
    date = meta.get("date", "")
    image_url = f"{IMAGE_HOST_URL}/sns_output/{ACCOUNT_ID}/card_sq_{date}.jpg"
    success = post_image(image_url)

if not success:
    print("  ⚠️  이미지/영상 게시 실패 — 캡션만 저장")
    meta["instagram_caption_ready"] = caption

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

if success:
    print("✅ Instagram 완료")
else:
    exit(1)
