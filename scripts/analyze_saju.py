#!/usr/bin/env python3
"""
사주마루 사주 분석 자동화
사용법: python scripts/analyze_saju.py

실행하면 고객 정보 입력 프롬프트가 뜨고,
Claude API로 항목별 분석 후 고객 이메일로 발송.
"""
import os, sys, smtplib, json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import anthropic
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'anthropic', '-q'])
    import anthropic

# .env 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
GMAIL_USER         = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

KST = timezone(timedelta(hours=9))

# ─── 항목 정의 ────────────────────────────────────────────────────────────
ITEMS = {
    "성향·기질 분석":    "타고난 성격, 강점, 약점, 대인관계 스타일을 오행과 일간을 중심으로 심층 분석",
    "평생운":           "인생 전체의 큰 흐름, 황금기, 주의 시기, 10년 대운 흐름을 상세히 풀이",
    "연애운":           "현재 연애 흐름, 이성과의 인연, 연애 스타일, 좋은 인연이 올 시기 분석",
    "배우자운·결혼운":  "결혼 적령기, 배우자의 특성, 궁합이 잘 맞는 상대방 유형 분석",
    "재물운":           "재물복의 방향, 돈이 들어오는 시기, 투자·사업 적합도 분석",
    "건강운":           "타고난 건강 취약 부위, 에너지 넘치는 시기, 주의해야 할 시기 분석",
    "대운·세운":        "현재 10년 대운의 흐름과 올해(세운) 월별 운세 흐름 종합 분석",
    "부모운":           "부모님과의 인연, 부모덕, 서로에게 미치는 기운 분석",
    "자식운":           "자녀와의 인연, 자식복, 자녀 양육에 도움이 되는 시기 분석",
    "형제간운":         "형제자매와의 관계, 형제덕, 서로 도움이 되는 시기 분석",
    "새해운세":         "2026년 한 해의 전체 흐름, 월별 길흉, 조심해야 할 시기 분석",
    "월별운세":         "향후 12개월간 달마다 바뀌는 운기 흐름 상세 분석",
    "수능·입시운":      "학업운, 시험운, 집중력이 최고로 오르는 시기, 합격 가능성 분석",
    "재회운":           "헤어진 상대와 다시 만날 가능성, 재회 시기, 인연의 흐름 분석",
    "사업운":           "사업 시작·확장 적기, 사업 아이템 적합도, 파트너 운 분석",
    "이혼·결별운":      "관계 정리의 흐름, 이별 시기, 새 시작의 기운 분석",
    "도화살 전문분석":  "타고난 매력도, 이성을 끄는 기운, 도화살의 긍정·부정적 영향 분석",
    "이런 사람 만나지 마라": "나와 충돌하는 사주 유형, 피해야 할 인연의 특징 분석",
}

SAJU_SYSTEM = """당신은 30년 경력의 사주명리학 전문가입니다.
사주팔자를 깊이 이해하고, 고객이 실생활에서 바로 활용할 수 있도록
따뜻하면서도 구체적인 풀이를 제공합니다.

분석 원칙:
- 음양오행, 십신, 지장간, 신살을 종합적으로 활용
- 단순한 길흉 판단보다 구체적인 시기와 방향 제시
- 긍정적 관점 유지, 주의사항도 부드럽게 전달
- A4 5~7페이지 분량으로 상세하게 작성
- 소제목을 활용해 읽기 쉽게 구성
- 존댓말 사용"""


def get_input(prompt, required=True):
    val = input(prompt).strip()
    if required and not val:
        print("필수 입력입니다.")
        return get_input(prompt, required)
    return val


def collect_customer_info():
    print("\n" + "="*50)
    print("  사주마루 분석 정보 입력")
    print("="*50)
    name    = get_input("고객 이름: ")
    birth   = get_input("생년월일 (예: 1990-03-15): ")
    time    = get_input("태어난 시간 (예: 14:30, 모르면 엔터): ", required=False) or "모름"
    gender  = get_input("성별 (남/여): ")
    email   = get_input("고객 이메일: ")

    print("\n분석할 항목을 선택하세요 (번호 입력, 쉼표로 구분)")
    item_list = list(ITEMS.keys())
    for i, name_item in enumerate(item_list, 1):
        print(f"  {i:2}. {name_item}")
    print("   0. 전체 선택")

    sel = get_input("\n선택 (예: 1,3,5 또는 0): ")
    if sel == "0":
        selected = item_list
    else:
        indices = [int(x.strip())-1 for x in sel.split(",") if x.strip().isdigit()]
        selected = [item_list[i] for i in indices if 0 <= i < len(item_list)]

    return {
        "name": name, "birth": birth, "time": time,
        "gender": gender, "email": email, "items": selected
    }


def analyze_item(client, customer, item_name):
    item_desc = ITEMS[item_name]
    prompt = f"""
[고객 정보]
- 이름: {customer['name']}
- 생년월일: {customer['birth']}
- 출생 시간: {customer['time']}
- 성별: {customer['gender']}

[분석 요청 항목]
{item_name}: {item_desc}

위 고객의 사주를 바탕으로 [{item_name}]를 상세히 분석해주세요.
소제목을 활용하고, 구체적인 시기와 방향을 포함해 A4 5~7페이지 분량으로 작성해주세요.
"""
    print(f"  → {item_name} 분석 중...", end="", flush=True)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SAJU_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    result = msg.content[0].text
    print(" 완료")
    return result


def text_to_html(text):
    lines = text.split("\n")
    html = []
    for line in lines:
        line = line.strip()
        if not line:
            html.append("<br>")
        elif re.match(r'^#{1,3}\s', line):
            level = len(re.match(r'^(#+)', line).group(1))
            content = re.sub(r'^#+\s*', '', line)
            size = {1: "22px", 2: "19px", 3: "17px"}.get(level, "17px")
            html.append(f'<p style="font-size:{size};font-weight:800;color:#3B2A14;margin:20px 0 8px;">{content}</p>')
        elif line.startswith("**") and line.endswith("**"):
            html.append(f'<p style="font-weight:800;color:#3B2A14;margin:10px 0 4px;">{line[2:-2]}</p>')
        else:
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            html.append(f'<p style="margin:6px 0;line-height:1.85;">{line}</p>')
    return "\n".join(html)


def build_email_html(customer, analyses):
    now = datetime.now(KST).strftime("%Y년 %m월 %d일")
    sections = ""
    for item_name, content in analyses.items():
        sections += f"""
<tr><td style="padding:0 0 40px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="background:linear-gradient(90deg,#3B2A14,#6B4C2A);padding:14px 28px;border-radius:10px 10px 0 0;">
      <span style="font-size:18px;font-weight:800;color:#EDD9AE;letter-spacing:.04em;">✦ {item_name}</span>
    </td></tr>
    <tr><td style="background:#FDFAF4;border:1px solid rgba(60,40,20,.12);border-top:none;border-radius:0 0 10px 10px;padding:24px 28px;font-family:'Apple SD Gothic Neo',sans-serif;font-size:15px;color:#2A1F0E;line-height:1.9;">
      {text_to_html(content)}
    </td></tr>
  </table>
</td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0EBE0;font-family:'Apple SD Gothic Neo','맑은 고딕',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F0EBE0;">
<tr><td align="center" style="padding:40px 16px;">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;">

  <!-- 헤더 -->
  <tr><td style="background:linear-gradient(135deg,#1A1008 0%,#3B2A14 100%);padding:40px 36px;border-radius:14px 14px 0 0;text-align:center;">
    <div style="font-size:13px;color:rgba(237,217,174,.7);letter-spacing:.25em;margin-bottom:10px;">쉽게 보는 사주풀이</div>
    <div style="font-size:38px;font-weight:800;color:#EDD9AE;letter-spacing:.06em;">사주마루</div>
    <div style="margin:14px auto 0;width:60px;height:1px;background:rgba(237,217,174,.3);"></div>
    <div style="margin-top:14px;font-size:15px;color:rgba(237,217,174,.85);">{customer['name']}님의 사주 분석 결과</div>
    <div style="margin-top:6px;font-size:13px;color:rgba(237,217,174,.5);">{now} 발행</div>
  </td></tr>

  <!-- 고객 정보 -->
  <tr><td style="background:#FAF6EE;padding:20px 36px;border-left:1px solid rgba(60,40,20,.1);border-right:1px solid rgba(60,40,20,.1);">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="font-size:13px;color:#7A5530;font-weight:700;width:90px;">생년월일</td>
        <td style="font-size:14px;color:#2A1F0E;font-weight:700;">{customer['birth']} · {customer['gender']} · 출생시 {customer['time']}</td>
      </tr>
      <tr><td style="padding:4px 0;" colspan="2"></td></tr>
      <tr>
        <td style="font-size:13px;color:#7A5530;font-weight:700;">분석 항목</td>
        <td style="font-size:14px;color:#2A1F0E;font-weight:700;">{", ".join(analyses.keys())}</td>
      </tr>
    </table>
  </td></tr>

  <!-- 구분선 -->
  <tr><td style="background:#FAF6EE;padding:0 36px;">
    <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(90,60,20,.2),transparent);"></div>
  </td></tr>

  <!-- 분석 본문 -->
  <tr><td style="background:#FAF6EE;padding:28px 36px 10px;border-left:1px solid rgba(60,40,20,.1);border-right:1px solid rgba(60,40,20,.1);">
    <table width="100%" cellpadding="0" cellspacing="0">
      {sections}
    </table>
  </td></tr>

  <!-- 푸터 -->
  <tr><td style="background:#1A1008;padding:24px 36px;border-radius:0 0 14px 14px;text-align:center;">
    <div style="font-size:13px;color:rgba(237,217,174,.5);letter-spacing:.2em;">사주마루 · SAJU MARU</div>
    <div style="margin-top:8px;font-size:12px;color:rgba(237,217,174,.3);">궁금한 점은 카카오 채널로 문의해주세요</div>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def send_email(to_email, customer_name, html_content):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[사주마루] {customer_name}님의 사주 분석 결과가 도착했습니다"
    msg["From"]    = f"사주마루 <{GMAIL_USER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    print(f"\n  이메일 발송 중 → {to_email} ...", end="", flush=True)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        s.sendmail(GMAIL_USER, to_email, msg.as_string())
    print(" 완료!")


def main():
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY가 없습니다. scripts/.env 파일을 확인하세요.")
        sys.exit(1)
    if not GMAIL_APP_PASSWORD:
        print("❌ GMAIL_APP_PASSWORD가 없습니다. scripts/.env 파일을 확인하세요.")
        sys.exit(1)

    customer = collect_customer_info()

    if not customer["items"]:
        print("선택된 항목이 없습니다.")
        sys.exit(1)

    print(f"\n총 {len(customer['items'])}개 항목 분석 시작...\n")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    analyses = {}
    for item in customer["items"]:
        analyses[item] = analyze_item(client, customer, item)

    print("\n이메일 생성 중...")
    html = build_email_html(customer, analyses)

    # 고객에게 발송
    send_email(customer["email"], customer["name"], html)
    # 내 사본 저장 (선택)
    send_email(GMAIL_USER, f"[사본] {customer['name']}", html)

    print(f"\n✅ 완료! {customer['name']}님께 분석 결과 발송 완료.")


if __name__ == "__main__":
    main()
