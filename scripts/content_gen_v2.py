"""
사주채널 통합 콘텐츠 생성기 v2
- 3계정 × 시간대별 최적화
- 플랫폼별 포맷 + 이미지 카드 생성
"""
import os, json, sys, datetime, re
import anthropic
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# ── 환경 로드 ─────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_KEY:
    print("❌ ANTHROPIC_API_KEY 미설정")
    sys.exit(1)

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ── 설정 ─────────────────────────────────────────────────────
NOW_UTC = datetime.datetime.utcnow()
NOW_KST = NOW_UTC + datetime.timedelta(hours=9)
TODAY_STR = NOW_KST.strftime("%Y-%m-%d")
HOUR_KST = int(os.environ.get("HOUR_KST", NOW_KST.strftime("%H")))

WEEKDAYS_KR = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
TODAY_KR = f"{NOW_KST.strftime('%m월 %d일')} {WEEKDAYS_KR[NOW_KST.weekday()]}"

ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")  # sm / un / s77

with open(Path(__file__).parent.parent / "data" / "accounts.json", encoding="utf-8") as f:
    config = json.load(f)

account = next(a for a in config["accounts"] if a["id"] == ACCOUNT_ID)
time_slot = config["time_slots"].get(f"{HOUR_KST:02d}", config["time_slots"]["06"])

OUT_DIR = Path(__file__).parent / "sns_output" / ACCOUNT_ID
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[{NOW_KST.strftime('%H:%M')} KST] {account['name']} — {time_slot['title']} 콘텐츠 생성")

# ── 콘텐츠 생성 프롬프트 ──────────────────────────────────────
SLOT_GUIDES = {
    "morning_fortune": "아침에 오늘의 운세를 알고 싶은 사람들을 위한 콘텐츠. 희망차고 에너지 넘치는 톤.",
    "short_video": "숏폼 영상용 60초 스크립트. 훅→본론→CTA 구조. 빠르고 임팩트있게.",
    "blog_seo": "네이버 블로그 SEO 최적화 포스트. 키워드: '오늘 운세', '사주 무료', '이번주 운세'. 상세하고 전문적.",
    "midday_tip": "짧고 임팩트있는 사주 꿀팁. 점심에 공유하기 좋은 가벼운 내용.",
    "youtube_main": "유튜브 영상 대본. 5분 분량. 사주 심층 분석. SEO 제목 중요.",
    "promo_cta": "사주 상담 예약 유도. 무료 상담 or 구글폼 링크. 신뢰감 있는 CTA.",
    "evening_fortune": "퇴근 후 저녁 운세. 내일을 위한 조언. 따뜻하고 위로가 되는 톤.",
    "jisik_qna": "네이버 지식인 답변용. 사주 관련 질문에 전문적으로 답변. 채널 홍보 포함.",
    "night_preview": "내일/이번주 운세 예고. 궁금증 유발. 짧고 강렬한 훅."
}

PROMPT = f"""당신은 {account['name']} 채널의 콘텐츠 전문가입니다.
페르소나: {account['persona']}
오늘: {TODAY_KR}
현재 슬롯: {time_slot['title']} ({SLOT_GUIDES.get(time_slot['type'], '')})

아래 JSON 형식으로 콘텐츠를 생성하세요. 모든 텍스트는 한국어:

{{
  "theme": "오늘의 사주 테마 (10자 이내)",
  "zodiac_sign": "오늘의 사주 12지지 중 하나 (자/축/인/묘/진/사/오/미/신/유/술/해)",
  "lucky_element": "오늘의 행운 요소 (숫자/색/방향 중 하나)",

  "hook": "모든 플랫폼 공통 훅 문구 (15자 이내, 임팩트 강하게)",
  "main_text": "본문 3줄 (각 줄 30자 이내, 줄바꿈 포함)",
  "cta": "행동 유도 문구 (20자 이내)",

  "instagram_caption": "인스타 캡션 (200자, 감성적, 해시태그 15개)",
  "facebook_post": "페이스북 포스트 (250자, 친근한 톤, 공유 유도)",
  "threads_post": "쓰레드 포스트 (150자, 간결하고 대화체)",
  "twitter_post": "트위터 포스트 (140자 이내, 트렌디한 톤, 해시태그 3개)",

  "tiktok_hook": "틱톡 첫 3초 훅 (10자 이내, 강렬하게)",
  "tiktok_script": "틱톡/릴스 60초 스크립트 (자막용, 한 문장씩 줄바꿈)",

  "youtube_title": "유튜브 제목 (50자 이내, SEO+클릭유도)",
  "youtube_description": "유튜브 설명 (300자, 해시태그+링크 공간 포함)",
  "youtube_script": "유튜브 쇼츠 대본 (60초, TTS 최적화)",

  "naver_blog_title": "네이버 블로그 제목 (SEO, 검색어 포함)",
  "naver_blog_content": "블로그 본문 (800자, 소제목 포함, 마크다운 불가)",
  "naver_clip_hook": "네이버 클립 훅 (8자 이내)",

  "jisik_question": "지식인에서 답변할 만한 질문 예시",
  "jisik_answer": "전문적인 답변 (300자, 마지막에 채널 언급)",

  "hashtags": "#사주 #운세 #{account['handle']} #사주마루 #무료사주 #오늘운세 #사주풀이"
}}"""

# API 호출
msg = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=2000,
    messages=[{"role": "user", "content": PROMPT}]
)

raw = msg.content[0].text.strip()
raw = re.sub(r"^```json?\s*", "", raw)
raw = re.sub(r"```\s*$", "", raw)
content = json.loads(raw.strip())
print(f"✅ 콘텐츠 생성 완료: {content.get('theme', '')}")

# ── 이미지 카드 생성 ─────────────────────────────────────────
def make_image_card(content: dict, account: dict, size=(1080, 1080)) -> Path:
    """PIL로 사주 이미지 카드 생성"""
    W, H = size
    img = Image.new("RGB", (W, H), color=tuple(int(account["bg"].lstrip("#")[i:i+2], 16) for i in (0,2,4)))
    draw = ImageDraw.Draw(img)
    accent = tuple(int(account["accent"].lstrip("#")[i:i+2], 16) for i in (0,2,4))

    # 배경 그라디언트 효과 (간단히 레이어)
    for i in range(H // 2):
        alpha = int(40 * (1 - i / (H // 2)))
        draw.line([(0, i), (W, i)], fill=(*accent, alpha) if len(accent) == 3 else accent)

    # 폰트 (시스템 폰트 fallback)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 72)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 36)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 28)
    except Exception:
        font_large = ImageFont.load_default()
        font_med = font_large
        font_small = font_large

    # 계정명
    draw.text((W//2, 80), account["name"], fill=accent, font=font_small, anchor="mm")

    # 날짜
    draw.text((W//2, 130), TODAY_KR, fill=(180, 180, 200), font=font_small, anchor="mm")

    # 지지 이모지 매핑
    zodiac_map = {"자":"🐭","축":"🐂","인":"🐯","묘":"🐰","진":"🐲","사":"🐍","오":"🐴","미":"🐑","신":"🐒","유":"🐓","술":"🐕","해":"🐗"}
    zodiac = content.get("zodiac_sign", "자")
    zodiac_emoji = zodiac_map.get(zodiac, "⭐")

    # 메인 이모지
    draw.text((W//2, H//2 - 100), zodiac_emoji, fill=(255, 255, 255), font=font_large, anchor="mm")

    # 훅 문구
    hook = content.get("hook", "오늘의 운세")
    draw.text((W//2, H//2 + 30), hook, fill=(255, 255, 255), font=font_med, anchor="mm")

    # 본문 (3줄)
    main = content.get("main_text", "")
    lines = [l.strip() for l in main.split("\n") if l.strip()][:3]
    for i, line in enumerate(lines):
        draw.text((W//2, H//2 + 120 + i*45), line, fill=(200, 200, 220), font=font_small, anchor="mm")

    # CTA
    cta = content.get("cta", "지금 확인하기")
    # CTA 박스
    cta_y = H - 160
    draw.rounded_rectangle([(W//2 - 200, cta_y - 25), (W//2 + 200, cta_y + 25)], radius=20, fill=accent)
    draw.text((W//2, cta_y), cta, fill=(0, 0, 0), font=font_small, anchor="mm")

    # 하단 URL
    draw.text((W//2, H - 80), "forms.gle/t2sSNES5NYow77vz5", fill=(120, 120, 140), font=font_small, anchor="mm")

    out_path = OUT_DIR / f"card_{TODAY_STR}_{HOUR_KST:02d}h.jpg"
    img.save(str(out_path), "JPEG", quality=92)
    return out_path

# ── 이미지 세로형 (Reels/TikTok) 생성 ───────────────────────
def make_vertical_card(content: dict, account: dict) -> Path:
    path = make_image_card(content, account, size=(1080, 1920))
    out = OUT_DIR / f"vertical_{TODAY_STR}_{HOUR_KST:02d}h.jpg"
    path.rename(out)
    return out

# ── 저장 ──────────────────────────────────────────────────────
card_path = make_image_card(content, account)
vertical_path = make_vertical_card(content, account)
print(f"✅ 이미지 카드 생성: {card_path.name}")

meta = {
    "date": TODAY_STR,
    "hour_kst": HOUR_KST,
    "account": account,
    "slot": time_slot,
    "content": content,
    "image_card": str(card_path),
    "image_vertical": str(vertical_path),
}

meta_path = OUT_DIR / "meta.json"
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

# 레거시 호환 (기존 스크립트가 이 경로 사용)
legacy_dir = Path(__file__).parent / "sns_output"
legacy_dir.mkdir(exist_ok=True)
with open(legacy_dir / "meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"✅ meta.json 저장 완료 → {meta_path}")
