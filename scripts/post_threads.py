"""
Threads 자동 포스팅 (Meta Threads Graph API)
필요 시크릿: THREADS_ACCESS_TOKEN, THREADS_USER_ID
Instagram Graph API와 동일 앱으로 발급 가능
"""
import os, json, requests, time

ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
USER_ID      = os.environ.get("THREADS_USER_ID", "")
IMAGE_HOST   = os.environ.get("IMAGE_HOST_URL", "")

if not all([ACCESS_TOKEN, USER_ID]):
    print("⚠️  THREADS_ACCESS_TOKEN / THREADS_USER_ID 미설정 — 건너뜀")
    exit(0)

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
caption = (
    f"{content.get('hook', '')}\n\n"
    f"{content.get('main_text', '')}\n\n"
    f"{content.get('cta', '지금 확인하기 → sajumaru.com')}\n\n"
    f"{content.get('hashtags', '#사주 #운세 #사주마루')}"
)

BASE = "https://graph.threads.net/v1.0"

# 1. 미디어 컨테이너 생성
container_params = {
    "media_type": "TEXT",
    "text": caption[:500],
    "access_token": ACCESS_TOKEN,
}

# 이미지가 있으면 이미지 포스트로
if IMAGE_HOST:
    image_url = f"{IMAGE_HOST}/card_sq_{meta['date']}.jpg"
    container_params["media_type"] = "IMAGE"
    container_params["image_url"] = image_url

res1 = requests.post(f"{BASE}/{USER_ID}/threads", params=container_params)
data1 = res1.json()
container_id = data1.get("id", "")

if not container_id:
    print("❌ Threads 컨테이너 생성 실패:", data1)
    exit(1)

print(f"Threads 컨테이너: {container_id}")

# 2. 30초 대기 (Meta 권장)
time.sleep(30)

# 3. 게시
res2 = requests.post(
    f"{BASE}/{USER_ID}/threads_publish",
    params={"creation_id": container_id, "access_token": ACCESS_TOKEN},
)
data2 = res2.json()

if res2.status_code == 200 and data2.get("id"):
    print(f"✅ Threads 포스팅 완료: {data2['id']}")
    meta["threads_posted"] = True
else:
    print("❌ Threads 포스팅 실패:", data2)
    meta["threads_posted"] = False

with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
