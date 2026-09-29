#!/usr/bin/env python3
"""
사주마루 일일 무료 운세 자동 생성 & 이메일 발송
매일 오전 6시 (KST) GitHub Actions로 실행
"""
import os, smtplib, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import anthropic
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'anthropic', '-q'])
    import anthropic

# .env 자동 로드 (로컬 개발용)
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
GMAIL_USER         = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
FORTUNE_TO         = os.getenv("FORTUNE_TO", GMAIL_USER)  # 수신자 (여러 명: 쉼표 구분)

KST = timezone(timedelta(hours=9))


# ─── 간지 계산 ─────────────────────────────────────────────────────────────
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI     = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
JIJI_ZO  = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]

def ganjija_year(year: int) -> str:
    idx_g = (year - 4) % 10
    idx_j = (year - 4) % 12
    return f"{CHEONGAN[idx_g]}{JIJI[idx_j]}({JIJI_ZO[idx_j]})년"


def generate_fortune(today: datetime) -> dict:
    """Claude API로 오늘·내일 운세 생성"""
    tomorrow = today + timedelta(days=1)
    ganjija  = ganjija_year(today.year)

    prompt = f"""당신은 사주마루의 전문 사주 상담사입니다.
오늘 날짜: {today.strftime('%Y년 %m월 %d일')} ({ganjija})
내일 날짜: {tomorrow.strftime('%Y년 %m월 %d일')}

아래 JSON 형식으로 오늘과 내일의 무료 일일 운세를 작성해주세요.
각 항목은 2~3문장으로 구체적이고 따뜻하게, 사주 전통 용어(오행, 간지 등)를 자연스럽게 섞어서 작성해주세요.

{{
  "today_date": "{today.strftime('%Y년 %m월 %d일')}",
  "tomorrow_date": "{tomorrow.strftime('%Y년 %m월 %d일')}",
  "today_title": "오늘의 한 줄 총운 (20자 이내)",
  "today_chongwoon": "오늘 총운 설명 (2~3문장)",
  "today_jaeul": "재물운 (2문장)",
  "today_aejung": "애정운 (2문장)",
  "today_geongang": "건강운 (2문장)",
  "today_jikup": "직업·학업운 (2문장)",
  "today_lucky_color": "행운의 색 (예: 청록색)",
  "today_lucky_number": "행운의 숫자 (1~99 중 하나)",
  "today_lucky_direction": "행운의 방향 (예: 동남)",
  "today_advice": "오늘의 조언 한 마디 (한 문장)",
  "tomorrow_title": "내일의 한 줄 총운 (20자 이내)",
  "tomorrow_chongwoon": "내일 총운 설명 (2~3문장)",
  "tomorrow_jaeul": "내일 재물운 (2문장)",
  "tomorrow_aejung": "내일 애정운 (2문장)",
  "tomorrow_advice": "내일을 위한 조언 (한 문장)"
}}

반드시 유효한 JSON만 출력하세요. 다른 텍스트 없이."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    # JSON 블록 추출
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def build_html(data: dict, today: datetime) -> str:
    """운세 HTML 이메일 본문 생성"""
    ganjija = ganjija_year(today.year)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>사주마루 일일 운세</title>
</head>
<body style="margin:0;padding:0;background:#F0EBE0;font-family:'Nanum Myeongjo','Noto Serif KR',Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F0EBE0;padding:32px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

  <!-- 헤더 -->
  <tr><td style="background:#2E4A4A;padding:40px 36px 32px;border-radius:8px 8px 0 0;text-align:center;">
    <div style="font-size:13px;color:rgba(255,255,255,.55);letter-spacing:.25em;margin-bottom:10px;">쉽게 보는 사주풀이</div>
    <div style="font-size:36px;font-weight:bold;color:#F0EBE0;letter-spacing:.05em;margin-bottom:6px;">사주마루</div>
    <div style="font-size:13px;color:rgba(255,255,255,.45);letter-spacing:.2em;">{ganjija} 일일 운세</div>
  </td></tr>

  <!-- 오늘 날짜 배너 -->
  <tr><td style="background:#3A5E5E;padding:16px 36px;text-align:center;">
    <span style="font-size:15px;color:#F0D890;letter-spacing:.12em;">✦ {data['today_date']} 오늘의 운세 ✦</span>
  </td></tr>

  <!-- 오늘 총운 -->
  <tr><td style="background:#fff;padding:32px 36px 24px;">
    <div style="background:#F8F4EC;border-left:4px solid #2E4A4A;padding:18px 20px;border-radius:0 6px 6px 0;margin-bottom:28px;">
      <div style="font-size:11px;color:#8B6B3A;letter-spacing:.2em;margin-bottom:8px;">총  운</div>
      <div style="font-size:17px;font-weight:bold;color:#2E4A4A;margin-bottom:10px;">{data['today_title']}</div>
      <div style="font-size:14px;color:#3A2E20;line-height:1.85;">{data['today_chongwoon']}</div>
    </div>

    <!-- 4대 운 그리드 -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td width="48%" valign="top" style="padding-right:8px;padding-bottom:12px;">
          <div style="border:1px solid #E8E0D0;border-radius:6px;padding:16px;">
            <div style="font-size:11px;color:#C8A840;letter-spacing:.15em;margin-bottom:6px;">💰 재물운</div>
            <div style="font-size:13px;color:#2A1E10;line-height:1.75;">{data['today_jaeul']}</div>
          </div>
        </td>
        <td width="48%" valign="top" style="padding-left:8px;padding-bottom:12px;">
          <div style="border:1px solid #E8E0D0;border-radius:6px;padding:16px;">
            <div style="font-size:11px;color:#C84040;letter-spacing:.15em;margin-bottom:6px;">❤️ 애정운</div>
            <div style="font-size:13px;color:#2A1E10;line-height:1.75;">{data['today_aejung']}</div>
          </div>
        </td>
      </tr>
      <tr>
        <td width="48%" valign="top" style="padding-right:8px;">
          <div style="border:1px solid #E8E0D0;border-radius:6px;padding:16px;">
            <div style="font-size:11px;color:#4A8B4A;letter-spacing:.15em;margin-bottom:6px;">🌿 건강운</div>
            <div style="font-size:13px;color:#2A1E10;line-height:1.75;">{data['today_geongang']}</div>
          </div>
        </td>
        <td width="48%" valign="top" style="padding-left:8px;">
          <div style="border:1px solid #E8E0D0;border-radius:6px;padding:16px;">
            <div style="font-size:11px;color:#4A6B8B;letter-spacing:.15em;margin-bottom:6px;">📘 직업·학업운</div>
            <div style="font-size:13px;color:#2A1E10;line-height:1.75;">{data['today_jikup']}</div>
          </div>
        </td>
      </tr>
    </table>

    <!-- 행운 아이템 -->
    <div style="background:#2E4A4A;border-radius:8px;padding:18px 24px;margin-top:4px;display:flex;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:4px 0;">
            <div style="font-size:11px;color:rgba(240,216,144,.6);letter-spacing:.18em;margin-bottom:10px;">오늘의 행운 아이템</div>
          </td>
        </tr>
        <tr>
          <td align="center">
            <span style="display:inline-block;background:rgba(255,255,255,.1);border-radius:20px;padding:6px 16px;margin:0 4px;font-size:12px;color:#F0D890;">
              🎨 {data['today_lucky_color']}
            </span>
            <span style="display:inline-block;background:rgba(255,255,255,.1);border-radius:20px;padding:6px 16px;margin:0 4px;font-size:12px;color:#F0D890;">
              🔢 {data['today_lucky_number']}
            </span>
            <span style="display:inline-block;background:rgba(255,255,255,.1);border-radius:20px;padding:6px 16px;margin:0 4px;font-size:12px;color:#F0D890;">
              🧭 {data['today_lucky_direction']}방
            </span>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding-top:12px;">
            <div style="font-size:13px;color:rgba(240,230,200,.75);font-style:italic;">"{data['today_advice']}"</div>
          </td>
        </tr>
      </table>
    </div>
  </td></tr>

  <!-- 내일 운세 -->
  <tr><td style="background:#3A5E5E;padding:16px 36px;text-align:center;">
    <span style="font-size:15px;color:#F0D890;letter-spacing:.12em;">✦ {data['tomorrow_date']} 내일의 운세 미리보기 ✦</span>
  </td></tr>
  <tr><td style="background:#fff;padding:28px 36px 32px;">
    <div style="background:#F8F4EC;border-left:4px solid #8B6B3A;padding:18px 20px;border-radius:0 6px 6px 0;margin-bottom:20px;">
      <div style="font-size:11px;color:#8B6B3A;letter-spacing:.2em;margin-bottom:8px;">내일 총운</div>
      <div style="font-size:16px;font-weight:bold;color:#4A3520;margin-bottom:8px;">{data['tomorrow_title']}</div>
      <div style="font-size:14px;color:#3A2E20;line-height:1.85;">{data['tomorrow_chongwoon']}</div>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td width="48%" valign="top" style="padding-right:8px;">
          <div style="border:1px solid #E8E0D0;border-radius:6px;padding:14px;">
            <div style="font-size:11px;color:#C8A840;letter-spacing:.15em;margin-bottom:6px;">💰 내일 재물운</div>
            <div style="font-size:13px;color:#2A1E10;line-height:1.75;">{data['tomorrow_jaeul']}</div>
          </div>
        </td>
        <td width="48%" valign="top" style="padding-left:8px;">
          <div style="border:1px solid #E8E0D0;border-radius:6px;padding:14px;">
            <div style="font-size:11px;color:#C84040;letter-spacing:.15em;margin-bottom:6px;">❤️ 내일 애정운</div>
            <div style="font-size:13px;color:#2A1E10;line-height:1.75;">{data['tomorrow_aejung']}</div>
          </div>
        </td>
      </tr>
    </table>
    <div style="margin-top:20px;padding:14px 20px;border:1px dashed #C8B882;border-radius:6px;text-align:center;">
      <div style="font-size:13px;color:#5C3D1A;font-style:italic;">"{data['tomorrow_advice']}"</div>
    </div>
  </td></tr>

  <!-- 공유 CTA -->
  <tr><td style="background:#3A5E5E;padding:20px 36px;text-align:center;">
    <div style="font-size:13px;color:rgba(240,216,144,.8);margin-bottom:12px;">
      이 운세가 도움이 되셨나요? 카카오톡으로 친구에게도 공유해보세요!
    </div>
    <a href="https://shinmoney7-cyber.github.io/-/pages/free-fortune.html" style="display:inline-block;background:#FAE100;color:#391B1B;text-decoration:none;padding:11px 24px;border-radius:24px;font-size:13px;font-weight:bold;letter-spacing:.05em;">
      💬 무료 운세 페이지 공유하기
    </a>
  </td></tr>

  <!-- 광고/CTA -->
  <tr><td style="background:#F8F4EC;padding:28px 36px;border-radius:0 0 8px 8px;text-align:center;">
    <div style="font-size:13px;color:#7A5C30;line-height:1.8;margin-bottom:18px;">
      더 깊이 있는 나만의 사주 분석을 원하신다면?<br>
      사주마루의 <strong>맞춤형 사주 리포트</strong>를 만나보세요.
    </div>
    <a href="https://shinmoney7-cyber.github.io/-/" style="display:inline-block;background:#2E4A4A;color:#F0EBE0;text-decoration:none;padding:12px 28px;border-radius:24px;font-size:13px;letter-spacing:.12em;">
      📋 사주 분석 신청하기
    </a>
    <div style="margin-top:24px;font-size:11px;color:rgba(90,70,40,.4);letter-spacing:.1em;">
      사주마루 · SAJU MARU &nbsp;|&nbsp; 구독 해지: 이 메일에 답장으로 "수신거부" 라고 보내주세요
    </div>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_email(html: str, today: datetime):
    subject = f"[사주마루] {today.strftime('%m월 %d일')} 오늘·내일 무료 운세"
    recipients = [r.strip() for r in FORTUNE_TO.split(",") if r.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"사주마루 <{GMAIL_USER}>"
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, recipients, msg.as_string())

    print(f"[완료] 운세 이메일 발송 → {', '.join(recipients)}")


if __name__ == "__main__":
    today = datetime.now(KST)
    print(f"[사주마루] {today.strftime('%Y-%m-%d')} 일일 운세 생성 중...")

    data = generate_fortune(today)
    print(f"  오늘: {data['today_title']}")
    print(f"  내일: {data['tomorrow_title']}")

    html = build_html(data, today)
    send_email(html, today)
