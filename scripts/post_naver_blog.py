"""
네이버 블로그 자동 포스팅 (Naver Open API)
필요: NAVER_ACCESS_TOKEN (OAuth 인증 필요)
https://developers.naver.com/docs/login/api/api.md
"""
import os, json, requests

ACCESS_TOKEN = os.environ.get("NAVER_ACCESS_TOKEN", "")
REFRESH_TOKEN = os.environ.get("NAVER_REFRESH_TOKEN", "")
CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

if not ACCESS_TOKEN and not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("⚠️  Naver API 미설정 — 건너뜀")
    exit(0)

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]

# Access Token 갱신
if REFRESH_TOKEN and CLIENT_ID and CLIENT_SECRET:
    token_res = requests.post(
        "https://nid.naver.com/oauth2.0/token",
        params={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
        }
    )
    token_data = token_res.json()
    new_token = token_data.get("access_token", "")
    if new_token:
        ACCESS_TOKEN = new_token
        print("✅ Naver 토큰 갱신 완료")

if not ACCESS_TOKEN:
    print("❌ Naver Access Token 없음")
    exit(1)

title = content.get("naver_blog_title", f"이번 주 사주 운세 — {meta['date']}")
blog_content = content.get("naver_blog_content", "")
if not blog_content:
    blog_content = f"""<h2>{content.get('hook', '')}</h2>
<p>{content.get('main_text', '').replace(chr(10), '<br>')}</p>
<p><strong>{content.get('cta', '지금 사주마루 AI에서 확인하세요')}</strong></p>
<p>{content.get('hashtags', '')}</p>
<p><a href="https://saju-maru.com">사주마루 AI 바로가기</a></p>"""

# 네이버 블로그 포스팅 API
res = requests.post(
    "https://openapi.naver.com/blog/writePost.json",
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    },
    data={
        "title": title,
        "contents": blog_content,
    }
)

data = res.json()
if res.status_code == 200:
    print(f"✅ 네이버 블로그 게시 완료")
    meta["naver_blog_posted"] = True
    with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
else:
    print(f"❌ 네이버 블로그 게시 실패 ({res.status_code}):", data)
    # 블로그 API는 현재 OAuth 범위 검토 중 — 수동 게시 fallback
    print(f"\n수동 게시용 내용:\n제목: {title}\n\n{blog_content[:500]}")
    exit(0)  # 비치명적 실패로 처리
