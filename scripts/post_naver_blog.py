"""
네이버 블로그 자동 포스팅 (Naver Open API)
애드포스트 수익 최대화:
- 1800자+ 본문 (애드포스트 최소 요건)
- 핵심 키워드 3-5회 자연스럽게 삽입
- 목차, 이미지 alt 태그, 구조화된 HTML
- 인기 검색어 기반 제목 패턴
필요: NAVER_ACCESS_TOKEN / (CLIENT_ID + CLIENT_SECRET + REFRESH_TOKEN)
"""
import os, json, requests
from pathlib import Path

ACCESS_TOKEN = os.environ.get("NAVER_ACCESS_TOKEN", "")
REFRESH_TOKEN = os.environ.get("NAVER_REFRESH_TOKEN", "")
CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

if not ACCESS_TOKEN and not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("⚠️  Naver API 미설정 — 건너뜀")
    exit(0)

meta_path = Path("scripts/sns_output") / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path("scripts/sns_output/meta.json")

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
account_name = meta.get("account", {}).get("name", "사주마루")
date_str = meta.get("date", "")

# Token 갱신
if REFRESH_TOKEN and CLIENT_ID and CLIENT_SECRET:
    token_res = requests.post(
        "https://nid.naver.com/oauth2.0/token",
        params={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
        },
    )
    new_token = token_res.json().get("access_token", "")
    if new_token:
        ACCESS_TOKEN = new_token
        print("✅ Naver 토큰 갱신 완료")

if not ACCESS_TOKEN:
    print("❌ Naver Access Token 없음")
    exit(1)

# SEO 최적화 제목 패턴
raw_title = content.get("naver_blog_title", "")
if not raw_title:
    hook = content.get("hook", "오늘의 운세")
    raw_title = f"{date_str} {hook} — 사주로 보는 오늘의 운세 총정리 | {account_name}"

title = raw_title[:50]

# SEO/애드포스트 최적화 본문 생성
raw_body = content.get("naver_blog_content", "")
hook = content.get("hook", "")
main_text = content.get("main_text", "")
lucky = content.get("lucky_element", "빨간색 · 숫자 7")
cta = content.get("cta", "지금 무료로 사주 확인하기")
hashtags = content.get("hashtags", "#사주 #운세 #사주마루")

# 이미지 URL (GitHub Pages)
image_host = os.environ.get("IMAGE_HOST_URL", "").rstrip("/")
img_sq = f"{image_host}/sns_output/{ACCOUNT_ID}/card_sq_{date_str}.jpg" if image_host else ""
img_v  = f"{image_host}/sns_output/{ACCOUNT_ID}/card_v_{date_str}.png"  if image_host else ""

def img_tag(url: str, alt: str) -> str:
    if not url:
        return ""
    return f'<div style="text-align:center;margin:20px 0"><img src="{url}" alt="{alt}" style="max-width:100%;border-radius:12px"></div>'

# 1800자+ 구조화 본문
if raw_body and len(raw_body) > 500:
    body_html = raw_body.replace("\n", "<br>")
else:
    body_html = f"""
<h2>📌 오늘의 사주 운세 핵심 요약</h2>
{img_tag(img_sq, f"{date_str} 오늘의 사주 운세")}
<p style="font-size:16px;line-height:1.8">{hook}</p>

<h2>🔮 오늘의 상세 운세 분석</h2>
<p style="line-height:1.9">{main_text.replace(chr(10), '<br>')}</p>

<h2>⭐ 오늘의 행운 요소</h2>
<ul style="line-height:2">
  <li>행운의 색상/숫자: <strong>{lucky}</strong></li>
  <li>오늘 피해야 할 것: 성급한 결정, 충동 지출</li>
  <li>오늘 집중할 것: 인간관계, 창의적 활동</li>
</ul>

<h2>📅 이번 주 사주 운세 미리보기</h2>
<p>이번 주는 전반적으로 <strong>변화의 기운</strong>이 강합니다. 특히 재물운과 인연운이 교차하는 시기로,
중요한 결정은 수요일 이후로 미루는 것이 유리합니다. 사주팔자에서 이번 주를 주목해야 하는 이유는
천간과 지지의 충(沖)이 발생하는 구간이기 때문입니다.</p>

{img_tag(img_v, "이번주 운세 카드")}

<h2>💡 사주 운세 보는 방법 — 초보자 가이드</h2>
<p>사주(四柱)는 태어난 연도·월·일·시의 네 가지 기둥을 분석하여 운명의 흐름을 파악하는 동양 철학입니다.
오늘 운세를 정확히 보려면 <strong>일주(日柱)</strong>를 먼저 확인하고, 현재 대운(大運)과 세운(歲運)의
흐름을 파악해야 합니다. {account_name}에서는 AI를 활용해 더 빠르고 정확하게 분석을 제공합니다.</p>

<h2>🌟 자주 묻는 질문 (FAQ)</h2>
<p><strong>Q. 오늘 재물운이 좋은 띠는?</strong><br>
A. {lucky.split('·')[0].strip()} 기운을 가진 띠가 오늘 재물운에 유리합니다.
특히 뱀띠, 닭띠, 소띠가 해당됩니다.</p>

<p><strong>Q. 사주 무료 상담은 어떻게 받나요?</strong><br>
A. 아래 링크를 통해 간단한 생년월일을 입력하면 {account_name} AI가 즉시 분석해드립니다.</p>

<p><strong>Q. 오늘 운세가 나쁘면 어떻게 해야 하나요?</strong><br>
A. 운세는 참고 지표일 뿐입니다. 나쁜 운세일수록 더 신중하게 행동하면 오히려 좋은 결과를 만들 수 있습니다.</p>

<hr style="margin:30px 0">
<div style="background:#f9f0ff;border-left:4px solid #9b59b6;padding:20px;border-radius:8px">
<h3>🎁 {cta}</h3>
<p><a href="https://forms.gle/t2sSNES5NYow77vz5" style="color:#9b59b6;font-weight:bold">
▶ 무료 사주 상담 신청하기 →</a></p>
<p style="font-size:13px;color:#666">매일 한정 인원만 무료 상담 가능합니다. 서둘러 신청하세요!</p>
</div>

<p style="margin-top:30px;color:#888;font-size:13px">{hashtags}</p>
"""

blog_content = f"""
<div style="max-width:720px;margin:0 auto;font-family:'Noto Sans KR',sans-serif">
{body_html}
</div>
"""

# 네이버 블로그 포스팅 API
res = requests.post(
    "https://openapi.naver.com/blog/writePost.json",
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    },
    data={"title": title, "contents": blog_content},
)

data = res.json()
if res.status_code == 200:
    print(f"✅ 네이버 블로그 게시 완료: {title}")
    meta["naver_blog_posted"] = True
    meta["naver_blog_title"] = title
else:
    print(f"❌ 네이버 블로그 게시 실패 ({res.status_code}): {data}")
    print(f"  ▷ 수동 게시 제목: {title}")
    meta["naver_blog_posted"] = False

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

exit(0)  # 비치명적
