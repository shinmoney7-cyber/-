"""
밴드(BAND) 자동 포스팅 (BAND Open API)
필요 시크릿: BAND_ACCESS_TOKEN, BAND_KEY (밴드 고유키)
발급: https://developers.band.us → 앱 등록 → OAuth2
"""
import os, json, requests

ACCESS_TOKEN = os.environ.get("BAND_ACCESS_TOKEN", "")
BAND_KEY     = os.environ.get("BAND_KEY", "")  # 밴드 고유 band_key

if not all([ACCESS_TOKEN, BAND_KEY]):
    print("⚠️  BAND_ACCESS_TOKEN / BAND_KEY 미설정 — 건너뜀")
    exit(0)

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
post_text = (
    f"✨ {content.get('hook', '')}\n\n"
    f"{content.get('main_text', '')}\n\n"
    f"🔮 {content.get('cta', '지금 확인하기')}\n"
    f"👉 https://sajumaru.com\n\n"
    f"{content.get('hashtags', '#사주 #운세 #사주마루')}"
)

BASE = "https://openapi.band.us"

res = requests.post(
    f"{BASE}/v2.1/band/post/create",
    params={
        "access_token": ACCESS_TOKEN,
        "band_key": BAND_KEY,
        "content": post_text[:10000],
    },
)
data = res.json()

result_code = data.get("result_code", -1)
if result_code == 1:
    post_key = data.get("result_data", {}).get("post_key", "")
    print(f"✅ 밴드 포스팅 완료: {post_key}")
    meta["band_posted"] = True
else:
    print(f"❌ 밴드 포스팅 실패: {data}")
    meta["band_posted"] = False

with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
