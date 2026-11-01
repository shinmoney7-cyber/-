"""전체 SNS 자동 포스팅 결과 통합 이메일 알림"""
import os, json, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

GMAIL_USER = os.environ.get("GMAIL_USER", "sajumaru7@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

with open("scripts/sns_output/meta.json", encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]

def status_row(label, key, url_template=None):
    val = meta.get(key, "")
    if val:
        if url_template:
            return f'<tr><td>✅ {label}</td><td><a href="{url_template.format(val)}">{val}</a></td></tr>'
        return f'<tr><td>✅ {label}</td><td>{val}</td></tr>'
    return f'<tr><td style="color:#aaa">⏭ {label}</td><td style="color:#aaa">미설정/건너뜀</td></tr>'

html = f"""
<html><body style="font-family:sans-serif;background:#0a0f28;color:#fff;padding:24px;">
<div style="max-width:640px;margin:0 auto;">
  <h2 style="color:#ffc850">🔮 사주마루 SNS 자동 포스팅 완료</h2>
  <p style="color:#aaa">{meta['date']} | {content.get('theme','')}</p>

  <div style="background:#1a1f3a;border-radius:12px;padding:20px;margin:16px 0;">
    <h3 style="color:#ffc850">📊 게시 결과</h3>
    <table style="width:100%;border-collapse:collapse;">
      {status_row('TikTok', 'tiktok_publish_id')}
      {status_row('YouTube', 'youtube_video_id', 'https://youtube.com/shorts/{}')}
      {status_row('Instagram', 'instagram_media_id')}
      {status_row('Facebook', 'facebook_post_id')}
      {status_row('Naver Blog', 'naver_blog_posted')}
    </table>
  </div>

  <div style="background:#1a1f3a;border-radius:12px;padding:20px;margin:16px 0;">
    <h3 style="color:#ffc850">📝 생성된 콘텐츠</h3>
    <p><strong>테마:</strong> {content.get('theme','')}</p>
    <p><strong>훅:</strong> {content.get('hook','')}</p>
    <p><strong>본문:</strong><br>{content.get('main_text','').replace(chr(10),'<br>')}</p>
    <p><strong>CTA:</strong> {content.get('cta','')}</p>
  </div>

  <div style="background:#0d2040;border-radius:12px;padding:16px;margin:16px 0;">
    <h3 style="color:#ffc850">📱 수동 업로드 필요</h3>
    <p>• 네이버 클립: 첨부 이미지로 앱에서 직접 업로드</p>
    <p>• 네이버 지식인: API 미제공 — 수동 작성 권장</p>
  </div>

  <p style="color:#666;font-size:12px">사주마루 AI 자동 생성 · GitHub Actions</p>
</div>
</body></html>
"""

msg = MIMEMultipart("related")
msg["Subject"] = f"🔮 사주마루 SNS 자동 포스팅 완료 ({meta['date']})"
msg["From"] = GMAIL_USER
msg["To"] = GMAIL_USER
msg.attach(MIMEText(html, "html"))

for path_key in ["image_path", "square_image_path"]:
    image_path = meta.get(path_key, "")
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img = MIMEImage(f.read(), name=os.path.basename(image_path))
            img.add_header("Content-Disposition", "attachment", filename=os.path.basename(image_path))
            msg.attach(img)

if not GMAIL_APP_PASSWORD:
    print("⚠️  GMAIL_APP_PASSWORD 미설정 — 이메일 건너뜀")
    exit(0)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    s.send_message(msg)

print(f"✅ 통합 알림 이메일 전송 완료 → {GMAIL_USER}")
