"""이번 주 TikTok 콘텐츠 준비됐다는 이메일 알림"""
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

GMAIL_USER = os.environ.get("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

with open("scripts/tiktok_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
publish_id = meta.get("tiktok_publish_id", "")

status = "✅ TikTok 드래프트 업로드 완료" if publish_id else "⚠️ 수동 업로드 필요"
tiktok_guide = (
    f"TikTok 앱 → 받은 보관함 → 드래프트에서 확인 후 게시\n(publish_id: {publish_id})"
    if publish_id else
    "TikTok 앱 → + 버튼 → 첨부된 이미지 업로드 후 아래 캡션 복사"
)

html = f"""
<html><body style="font-family:sans-serif;background:#0a0f28;color:#fff;padding:24px;">
<div style="max-width:600px;margin:0 auto;">
  <h2 style="color:#ffc850">🔮 사주마루 TikTok 콘텐츠 준비 완료</h2>
  <p style="color:#aaa">{meta['date']} | {meta['content_type']}</p>

  <div style="background:#1a1f3a;border-radius:12px;padding:20px;margin:16px 0;">
    <h3 style="color:#ffc850">📱 Hook (첫 1초)</h3>
    <p style="font-size:20px;font-weight:bold">{content.get('hook','')}</p>

    <h3 style="color:#ffc850">📝 본문</h3>
    <p style="line-height:1.8">{content.get('main_text','').replace(chr(10),'<br>')}</p>

    <h3 style="color:#ffc850">🎯 CTA</h3>
    <p>{content.get('cta','')}</p>

    <h3 style="color:#ffc850">🏷 해시태그</h3>
    <p style="color:#aaa">{content.get('hashtags','')}</p>
  </div>

  <div style="background:#0d2040;border-radius:12px;padding:16px;margin:16px 0;">
    <h3 style="color:#ffc850">📤 게시 상태</h3>
    <p>{status}</p>
    <p style="color:#ccc">{tiktok_guide}</p>
  </div>

  <p style="color:#666;font-size:12px">사주마루 AI 자동 생성 · GitHub Actions</p>
</div>
</body></html>
"""

msg = MIMEMultipart("related")
msg["Subject"] = f"🔮 사주마루 TikTok 콘텐츠 준비 완료 ({meta['date']})"
msg["From"] = GMAIL_USER
msg["To"] = GMAIL_USER
msg.attach(MIMEText(html, "html"))

# 생성된 이미지 첨부
image_path = meta.get("image_path", "")
if os.path.exists(image_path):
    with open(image_path, "rb") as f:
        img = MIMEImage(f.read(), name=os.path.basename(image_path))
        img.add_header("Content-Disposition", "attachment", filename=os.path.basename(image_path))
        msg.attach(img)

if not GMAIL_APP_PASSWORD:
    print("⚠️ GMAIL_APP_PASSWORD 미설정 — 이메일 전송 건너뜀")
    print("콘텐츠:", json.dumps(meta, ensure_ascii=False, indent=2))
    exit(0)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    s.send_message(msg)

print(f"✅ 이메일 전송 완료 → {GMAIL_USER}")
