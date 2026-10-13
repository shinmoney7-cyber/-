"""
카카오 비즈니스 채널 소식 자동 포스팅
필요 시크릿: KAKAO_REST_API_KEY, KAKAO_CHANNEL_ID
"""
import os, json, requests

REST_API_KEY  = os.environ.get("KAKAO_REST_API_KEY", "")
CHANNEL_ID    = os.environ.get("KAKAO_CHANNEL_ID", "")   # 채널 공개ID (_사주마루 형태)
ACCESS_TOKEN  = os.environ.get("KAKAO_ACCESS_TOKEN", "")  # 카카오 OAuth 액세스토큰

if not REST_API_KEY:
    print("⚠️  KAKAO_REST_API_KEY 미설정 — 건너뜀")
    exit(0)

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
text = (
    f"[사주마루] {content.get('hook', '')}\n\n"
    f"{content.get('main_text', '').replace(chr(10), chr(10))}\n\n"
    f"✨ {content.get('cta', '지금 확인하기')}\n"
    f"👉 https://sajumaru.com\n\n"
    f"{content.get('hashtags', '#사주 #운세 #사주마루')}"
)

# 카카오채널 소식(Channel Post) — 비즈니스 채널 REST API
# 채널 소식 = Channel Post (채널 팔로워 전체에게 노출)
headers = {
    "Authorization": f"KakaoAK {REST_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "template_object": {
        "object_type": "text",
        "text": text[:200],  # 카카오 텍스트 최대 200자
        "link": {
            "web_url": "https://sajumaru.com",
            "mobile_web_url": "https://sajumaru.com",
        },
        "button_title": "사주 보러가기",
    }
}

# 채널 소식 전송 엔드포인트
url = "https://kapi.kakao.com/v1/api/talk/chats/send"
if CHANNEL_ID:
    url = f"https://kapi.kakao.com/v2/api/talk/channels/{CHANNEL_ID}/posts"
    payload_channel = {
        "content": text[:1000],
    }
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    res = requests.post(url, headers=headers, json=payload_channel)
else:
    # 플러스친구 메시지 방식 (구버전 fallback)
    res = requests.post(url, headers=headers, json=payload)

print(f"카카오채널 응답: {res.status_code} {res.text[:200]}")
if res.status_code in (200, 201):
    print("✅ 카카오채널 포스팅 완료")
    meta["kakao_posted"] = True
else:
    print("❌ 카카오채널 포스팅 실패")
    meta["kakao_posted"] = False

with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
