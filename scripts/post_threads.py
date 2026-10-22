"""
Threads 자동 포스팅 (Meta Threads Graph API)
- 영상 Reel 우선, 없으면 이미지, 없으면 텍스트
필요: THREADS_ACCESS_TOKEN, THREADS_USER_ID
"""
import os, json, requests, time
from pathlib import Path

ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
USER_ID      = os.environ.get("THREADS_USER_ID", "")
IMAGE_HOST   = os.environ.get("IMAGE_HOST_URL", "").rstrip("/")
ACCOUNT_ID   = os.environ.get("ACCOUNT_ID", "sm")

if not all([ACCESS_TOKEN, USER_ID]):
    print("⚠️  THREADS_ACCESS_TOKEN / THREADS_USER_ID 미설정 — 건너뜀")
    exit(0)

meta_path = Path("scripts/sns_output") / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path("scripts/sns_output/meta.json")

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
threads_text = content.get("threads_post", "")
if not threads_text:
    threads_text = (
        f"{content.get('hook', '')}\n\n"
        f"{content.get('main_text', '')}\n\n"
        f"👉 무료 상담: forms.gle/t2sSNES5NYow77vz5\n\n"
        f"{content.get('hashtags', '#사주 #운세')}"
    )
text = threads_text[:500]

BASE = "https://graph.threads.net/v1.0"
date = meta.get("date", "")

params = {"access_token": ACCESS_TOKEN}

# 미디어 타입 결정
video_path_local = meta.get("video_shorts") or meta.get("video_path", "")
if video_path_local and IMAGE_HOST and Path(video_path_local).exists():
    video_filename = Path(video_path_local).name
    video_url = f"{IMAGE_HOST}/sns_output/{ACCOUNT_ID}/{video_filename}"
    container_params = {
        **params,
        "media_type": "VIDEO",
        "video_url": video_url,
        "text": text,
    }
    media_label = "영상"
elif IMAGE_HOST:
    image_url = f"{IMAGE_HOST}/sns_output/{ACCOUNT_ID}/card_sq_{date}.jpg"
    container_params = {
        **params,
        "media_type": "IMAGE",
        "image_url": image_url,
        "text": text,
    }
    media_label = "이미지"
else:
    container_params = {**params, "media_type": "TEXT", "text": text}
    media_label = "텍스트"

print(f"  📤 Threads {media_label} 포스팅...")
res1 = requests.post(f"{BASE}/{USER_ID}/threads", params=container_params)
data1 = res1.json()
container_id = data1.get("id", "")

if not container_id:
    print("❌ Threads 컨테이너 생성 실패:", data1)
    exit(1)

print(f"  컨테이너: {container_id} — 30초 대기...")
time.sleep(30)

res2 = requests.post(
    f"{BASE}/{USER_ID}/threads_publish",
    params={"creation_id": container_id, "access_token": ACCESS_TOKEN},
)
data2 = res2.json()

if res2.status_code == 200 and data2.get("id"):
    print(f"✅ Threads 포스팅 완료: {data2['id']}")
    meta["threads_posted"] = True
    meta["threads_media_id"] = data2["id"]
else:
    print("❌ Threads 포스팅 실패:", data2)
    meta["threads_posted"] = False

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

if not meta.get("threads_posted"):
    exit(1)
print("✅ Threads 완료")
