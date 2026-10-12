"""
사주마루 AI — TikTok 콘텐츠 생성기
Claude API로 이번 주 사주 콘텐츠 생성 + Pillow로 이미지 카드 생성
"""
import os
import json
import datetime
import anthropic
from PIL import Image, ImageDraw, ImageFont
import io

CONTENT_TYPE = os.environ.get("CONTENT_TYPE", "weekly_saju")
TODAY = datetime.date.today()
WEEK = TODAY.isocalendar()[1]

CONTENT_PROMPTS = {
    "weekly_saju": f"""이번 주({TODAY.strftime('%m월 %d일')} 시작) TikTok용 사주 콘텐츠를 작성해줘.

형식 (JSON):
{{
  "hook": "첫 1초 시선끌기 문구 (15자 이내, 궁금증 유발)",
  "main_text": "본문 3줄 (각 줄 20자 이내, 이번 주 운세)",
  "cta": "행동 유도 문구 (예: '지금 바로 내 사주 확인 →')",
  "hashtags": "#사주 #운세 #사주마루 #AI사주 #사주풀이 #이번주운세 #사주명리",
  "bg_theme": "dark_navy 또는 deep_purple 중 하나",
  "accent_color": "gold 또는 rose_gold 중 하나"
}}

규칙:
- 한국어만
- 클릭베이트지만 진실성 있게
- 신비롭고 프리미엄한 톤
- 12지지 중 하나 언급""",

    "daily_tip": f"""오늘({TODAY.strftime('%m월 %d일')}) 사주 팁 TikTok 콘텐츠 (JSON):
{{
  "hook": "첫 문구",
  "main_text": "팁 내용 3줄",
  "cta": "행동 유도",
  "hashtags": "#사주팁 #오늘의운세 #사주마루 #AI사주",
  "bg_theme": "dark_navy",
  "accent_color": "gold"
}}""",

    "promotion": """사주마루 AI 앱 홍보 TikTok 콘텐츠 (JSON):
{
  "hook": "AI 사주 시대 - 무료로 내 사주 보기",
  "main_text": "3가지 특별 기능 소개",
  "cta": "지금 바로 시작하기",
  "hashtags": "#사주마루 #AI사주 #무료사주 #사주앱 #운세앱",
  "bg_theme": "deep_purple",
  "accent_color": "rose_gold"
}"""
}

client = anthropic.Anthropic()

print(f"[{TODAY}] 콘텐츠 생성 시작: {CONTENT_TYPE}")
msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{"role": "user", "content": CONTENT_PROMPTS.get(CONTENT_TYPE, CONTENT_PROMPTS["weekly_saju"])}]
)

raw = msg.content[0].text.strip()
if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
        raw = raw[4:]
content = json.loads(raw.strip())
print("생성된 콘텐츠:", json.dumps(content, ensure_ascii=False, indent=2))

# 이미지 카드 생성 (1080x1920 세로형)
W, H = 1080, 1920
bg_colors = {
    "dark_navy": (10, 15, 40),
    "deep_purple": (20, 10, 45),
}
accent_colors = {
    "gold": (255, 200, 80),
    "rose_gold": (220, 150, 130),
}

bg = bg_colors.get(content.get("bg_theme", "dark_navy"), (10, 15, 40))
accent = accent_colors.get(content.get("accent_color", "gold"), (255, 200, 80))

img = Image.new("RGB", (W, H), bg)
draw = ImageDraw.Draw(img)

# 그라데이션 효과 (상단)
for y in range(400):
    alpha = y / 400
    r = int(bg[0] + (accent[0] - bg[0]) * alpha * 0.15)
    g = int(bg[1] + (accent[1] - bg[1]) * alpha * 0.15)
    b = int(bg[2] + (accent[2] - bg[2]) * alpha * 0.15)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# 장식 원
draw.ellipse([(W//2 - 200, 180), (W//2 + 200, 580)],
             outline=accent, width=3)
draw.ellipse([(W//2 - 150, 230), (W//2 + 150, 530)],
             outline=(*accent, 80), width=1)

# 텍스트: 브랜드
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 52)
    font_med = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 38)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 30)
except Exception:
    font_large = ImageFont.load_default()
    font_med = font_large
    font_small = font_large

def center_text(draw, text, y, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (W - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=color)

# 브랜드 로고 텍스트
center_text(draw, "사주마루 AI", 640, font_large, accent)
draw.line([(W//2 - 120, 710), (W//2 + 120, 710)], fill=accent, width=2)

# Hook 문구
center_text(draw, content.get("hook", ""), 760, font_med, (255, 255, 255))

# 본문 3줄
lines = content.get("main_text", "").split("\n")[:3]
for i, line in enumerate(lines):
    center_text(draw, line.strip(), 860 + i * 70, font_small, (200, 200, 220))

# CTA
center_text(draw, content.get("cta", "지금 확인하기 →"), 1120, font_med, accent)

# 하단 해시태그
center_text(draw, content.get("hashtags", "")[:50], 1780, font_small, (150, 150, 180))

# 저장
os.makedirs("scripts/tiktok_output", exist_ok=True)
out_path = f"scripts/tiktok_output/tiktok_{TODAY}_{CONTENT_TYPE}.jpg"
img.convert("RGB").save(out_path, "JPEG", quality=95)
print(f"이미지 저장: {out_path}")

# 메타데이터 저장
meta = {
    "date": str(TODAY),
    "content_type": CONTENT_TYPE,
    "content": content,
    "image_path": out_path,
    "caption": f"{content.get('hook', '')} {content.get('main_text', '')} {content.get('cta', '')} {content.get('hashtags', '')}".strip()
}
with open("scripts/tiktok_output/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print("완료:", json.dumps(meta, ensure_ascii=False))
