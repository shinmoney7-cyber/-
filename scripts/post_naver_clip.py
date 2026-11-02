"""
네이버 클립 자동 포스팅
네이버 클립은 공식 오픈 API 미제공 → 네이버 스마트에디터 API 또는 이메일 알림으로 대체
현재: 수동 업로드 가이드 이메일 전송
"""
import os, json, smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

GMAIL_USER = os.environ.get("GMAIL_USER", "sajumaru7@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")
meta_path = Path("scripts/sns_output") / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path("scripts/sns_output/meta.json")

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]

html = f"""
<html><body style="font-family:sans-serif;background:#03C75A;color:#fff;padding:24px;">
<div style="max-width:600px;margin:0 auto;background:#fff;color:#333;border-radius:12px;padding:24px;">
  <h2 style="color:#03C75A">📱 네이버 클립 업로드 가이드</h2>
  <p style="color:#666">{meta['date']} | 수동 업로드 필요</p>

  <div style="background:#f5f5f5;border-radius:8px;padding:16px;margin:16px 0;">
    <h3>🎯 훅 문구 (첫 화면)</h3>
    <p style="font-size:20px;font-weight:bold;color:#03C75A">{content.get('naver_clip_hook', content.get('hook',''))}</p>

    <h3>📝 캡션</h3>
    <p>{content.get('main_text','').replace(chr(10),'<br>')}</p>
    <p><strong>{content.get('cta','')}</strong></p>
    <p style="color:#888">{content.get('hashtags','')}</p>
  </div>

  <div style="background:#e8f8ef;border-radius:8px;padding:16px;">
    <h3>📤 업로드 방법</h3>
    <ol>
      <li>네이버 앱 → 클립 → + 버튼</li>
      <li>첨부된 이미지/영상 선택</li>
      <li>위 캡션 복사하여 붙여넣기</li>
      <li>해시태그 추가 후 게시</li>
    </ol>
  </div>
  <p style="color:#999;font-size:12px">사주마루 AI 자동 생성 · GitHub Actions</p>
</div>
</body></html>
"""

msg = MIMEMultipart("related")
msg["Subject"] = f"📱 네이버 클립 업로드 가이드 ({meta['date']})"
msg["From"] = GMAIL_USER
msg["To"] = GMAIL_USER
msg.attach(MIMEText(html, "html"))

# 영상이 있으면 첨부
video_path = meta.get("video_shorts") or meta.get("video_path", "")
if video_path and os.path.exists(video_path):
    from email.mime.base import MIMEBase
    from email import encoders
    with open(video_path, "rb") as vf:
        vpart = MIMEBase("video", "mp4")
        vpart.set_payload(vf.read())
        encoders.encode_base64(vpart)
        vpart.add_header("Content-Disposition", "attachment", filename=os.path.basename(video_path))
        msg.attach(vpart)

image_path = meta.get("image_path", "")
if os.path.exists(image_path):
    with open(image_path, "rb") as f:
        img = MIMEImage(f.read(), name=os.path.basename(image_path))
        img.add_header("Content-Disposition", "attachment", filename=os.path.basename(image_path))
        msg.attach(img)

if not GMAIL_APP_PASSWORD:
    print("⚠️  GMAIL_APP_PASSWORD 미설정")
    print(f"클립 훅: {content.get('naver_clip_hook', content.get('hook',''))}")
    exit(0)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    s.send_message(msg)

print(f"✅ 네이버 클립 가이드 이메일 전송 완료")
