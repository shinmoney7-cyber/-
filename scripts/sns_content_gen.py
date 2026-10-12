"""
사주마루 SNS 콘텐츠 통합 생성기
Claude API로 플랫폼별 최적화된 콘텐츠 생성
"""
import os
import json
import datetime
import anthropic
from PIL import Image, ImageDraw, ImageFont

CONTENT_TYPE = os.environ.get("CONTENT_TYPE", "weekly_saju")
TODAY = datetime.date.today()
WEEK = TODAY.isocalendar()[1]

client = anthropic.Anthropic()

PROMPT = f"""이번 주({TODAY.strftime('%m월 %d일')} 시작) 사주마루 AI SNS 콘텐츠를 플랫폼별로 작성해줘.

JSON 형식으로 반환:
{{
  "theme": "이번 주 전체 주제 (예: '갑목의 기운, 새로운 시작')",
  "zodiac": "이번 주 관련 12지지 중 하나",
  "youtube_title": "유튜브 쇼츠 제목 (30자 이내, 클릭 유도)",
  "youtube_description": "유튜브 설명 (3줄, 해시태그 포함)",
  "youtube_script": "쇼츠 스크립트 60초 분량 (TTS용, 한국어)",
  "instagram_caption": "인스타 캡션 (150자, 감성적, 해시태그 10개)",
  "facebook_post": "페이스북 포스트 (200자, 친근한 톤, 링크 유도)",
  "naver_blog_title": "블로그 포스트 제목 (SEO 최적화)",
  "naver_blog_content": "블로그 본문 (500자, 사주 설명 + 운세 + CTA)",
  "naver_clip_hook": "네이버 클립 훅 문구 (10자 이내)",
  "tiktok_hook": "틱톡 훅 (15자 이내)",
  "hook": "공통 훅 (15자 이내)",
  "main_text": "본문 3줄",
  "cta": "행동 유도",
  "hashtags": "#사주 #운세 #사주마루 #AI사주 #이번주운세",
  "bg_theme": "dark_navy",
  "accent_color": "gold"
}}

규칙: 한국어만, 신비롭고 프리미엄한 톤, 12지지 언급"""

print(f"[{TODAY}] SNS 콘텐츠 생성 중...")
msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1500,
    messages=[{"role": "user", "content": PROMPT}]
)

raw = msg.content[0].text.strip()
if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
        raw = raw[4:]
content = json.loads(raw.strip())
print("콘텐츠 생성 완료:", content.get("theme", ""))

# 이미지 카드 생성 (공통 1080x1920)
W, H = 1080, 1920
bg_colors = {"dark_navy": (10, 15, 40), "deep_purple": (20, 10, 45)}
accent_colors = {"gold": (255, 200, 80), "rose_gold": (220, 150, 130)}

bg = bg_colors.get(content.get("bg_theme", "dark_navy"), (10, 15, 40))
accent = accent_colors.get(content.get("accent_color", "gold"), (255, 200, 80))

img = Image.new("RGB", (W, H), bg)
draw = ImageDraw.Draw(img)

for y in range(400):
    alpha = y / 400
    r = int(bg[0] + (accent[0] - bg[0]) * alpha * 0.15)
    g = int(bg[1] + (accent[1] - bg[1]) * alpha * 0.15)
    b = int(bg[2] + (accent[2] - bg[2]) * alpha * 0.15)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

draw.ellipse([(W//2 - 200, 180), (W//2 + 200, 580)], outline=accent, width=3)
draw.ellipse([(W//2 - 150, 230), (W//2 + 150, 530)], outline=(*accent, 80), width=1)

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

center_text(draw, "사주마루 AI", 640, font_large, accent)
draw.line([(W//2 - 120, 710), (W//2 + 120, 710)], fill=accent, width=2)
center_text(draw, content.get("hook", ""), 760, font_med, (255, 255, 255))

lines = content.get("main_text", "").split("\n")[:3]
for i, line in enumerate(lines):
    center_text(draw, line.strip(), 860 + i * 70, font_small, (200, 200, 220))

center_text(draw, content.get("cta", "지금 확인하기 →"), 1120, font_med, accent)
center_text(draw, content.get("hashtags", "")[:50], 1780, font_small, (150, 150, 180))

os.makedirs("scripts/sns_output", exist_ok=True)
image_path = f"scripts/sns_output/card_{TODAY}.jpg"
img.convert("RGB").save(image_path, "JPEG", quality=95)
print(f"이미지 저장: {image_path}")

# 정사각형 버전 (인스타/페북용 1080x1080)
img_sq = Image.new("RGB", (1080, 1080), bg)
draw_sq = ImageDraw.Draw(img_sq)
for y in range(300):
    alpha = y / 300
    r = int(bg[0] + (accent[0] - bg[0]) * alpha * 0.15)
    g = int(bg[1] + (accent[1] - bg[1]) * alpha * 0.15)
    b2 = int(bg[2] + (accent[2] - bg[2]) * alpha * 0.15)
    draw_sq.line([(0, y), (1080, y)], fill=(r, g, b2))
draw_sq.ellipse([(440, 100), (640, 300)], outline=accent, width=2)
center_text(draw_sq, "사주마루 AI", 340, font_large, accent)
center_text(draw_sq, content.get("hook", ""), 430, font_med, (255, 255, 255))
lines_sq = content.get("main_text", "").split("\n")[:3]
for i, line in enumerate(lines_sq):
    center_text(draw_sq, line.strip(), 530 + i * 60, font_small, (200, 200, 220))
center_text(draw_sq, content.get("cta", "지금 확인하기 →"), 780, font_med, accent)

square_path = f"scripts/sns_output/card_sq_{TODAY}.jpg"
img_sq.convert("RGB").save(square_path, "JPEG", quality=95)
print(f"정사각형 이미지 저장: {square_path}")

meta = {
    "date": str(TODAY),
    "week": WEEK,
    "content_type": CONTENT_TYPE,
    "content": content,
    "image_path": image_path,
    "square_image_path": square_path,
}
with open("scripts/sns_output/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print("완료:", content.get("theme", ""))
