#!/usr/bin/env python3
"""
Claude API 기반 사주 분석 + 이메일 발송
주문 정보를 받아 사주 해석 생성 → 운영자 이메일로 발송
"""
import os, smtplib, json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# .env 자동 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GMAIL_USER        = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD= os.getenv("GMAIL_APP_PASSWORD", "")
OPERATOR_EMAIL    = "shinmoney7@gmail.com"

# 지지(地支) → 오행·특성
SIJIN = {
    0:  ("자시", "子", "水", "밤 11시~새벽 1시"),
    2:  ("축시", "丑", "土", "새벽 1시~3시"),
    4:  ("인시", "寅", "木", "새벽 3시~5시"),
    6:  ("묘시", "卯", "木", "새벽 5시~7시"),
    8:  ("진시", "辰", "土", "오전 7시~9시"),
    10: ("사시", "巳", "火", "오전 9시~11시"),
    12: ("오시", "午", "火", "오전 11시~오후 1시"),
    14: ("미시", "未", "土", "오후 1시~3시"),
    16: ("신시", "申", "金", "오후 3시~5시"),
    18: ("유시", "酉", "金", "오후 5시~7시"),
    20: ("술시", "戌", "土", "오후 7시~9시"),
    22: ("해시", "亥", "水", "오후 9시~11시"),
}

PRODUCT_ANALYSIS_FOCUS = {
    "연애운":           "연애·이성 인연·궁합·결혼 시기",
    "배우자운·결혼운":  "배우자 인연·결혼 시기·부부 궁합",
    "재물운":           "재물 흐름·투자 시기·사업 재물",
    "평생운":           "전반적 평생운·대운 흐름·핵심 기질",
    "성향·기질 분석":   "타고난 성격·강점·약점·적성",
    "건강운":           "건강 취약점·주의할 시기·관리법",
    "대운·세운":        "대운 10년 흐름·올해 세운",
    "부모운":           "부모와의 인연·부모 건강·덕",
    "자식운":           "자식 인연·자녀 수·자녀 성향",
    "형제간운":         "형제자매 관계·덕·협력 여부",
    "새해운세":         "2026년 전반 운세·월별 핵심",
    "월별운세":         "2026년 월별 상세 운세",
    "수능·입시운":      "학업 운·시험 시기·합격 가능성",
    "재회운":           "전 연인 재회 가능성·시기",
    "사업운":           "사업 시기·파트너·성패 요인",
    "직장운":           "직장 운·이직 시기·승진 가능성",
    "이혼·결별운":      "이별·이혼 시기·원인·향후 운",
    "도화살 전문분석":  "도화살 종류·발현 시기·활용법",
    "이런 사람 만나지 마라": "피해야 할 인연 유형·특징",
    "친구·우정운":           "친구 인연·좋은 우정 시기·인간관계 특성",
}


def get_ganji(year: int) -> str:
    """연도 → 간지 (예: 1990 → 경오년)"""
    cheongan = ["갑","을","병","정","무","기","경","신","임","계"]
    jiji     = ["자","축","인","묘","진","사","오","미","신","유","술","해"]
    return cheongan[(year - 4) % 10] + jiji[(year - 4) % 12] + "년"


def analyze_saju(order: dict) -> str:
    """Claude API로 사주 분석 텍스트 생성"""
    if not ANTHROPIC_API_KEY:
        return ""

    import urllib.request, json as _json

    name     = order["name"]
    year     = order["year"]
    month    = order["month"]
    day      = order["day"]
    hour     = order.get("hour")
    gender   = order.get("gender", "여성")
    cal_type = order.get("cal_type", "양력")
    product  = order.get("product", "평생운")
    focus    = PRODUCT_ANALYSIS_FOCUS.get(product, product)
    ganji    = get_ganji(year)

    hour_desc = "시간 미상"
    if hour is not None and hour in SIJIN:
        h = SIJIN[hour]
        hour_desc = f"{h[0]}({h[1]}, {h[2]}기운, {h[3]})"

    cal_note = "(음력)" if cal_type == "음력" else "(양력)"
    prompt = f"""당신은 30년 경력의 정통 명리학 전문가입니다.
아래 사주 정보를 바탕으로 [{product}] 항목에 대한 깊이 있는 분석을 해주세요.

【의뢰인 정보】
- 이름: {name}
- 성별: {gender}
- 생년월일: {year}년 {month}월 {day}일 {cal_note} ({ganji})
- 출생시간: {hour_desc}
- 분석 항목: {product}
- 핵심 포커스: {focus}

【분석 요청 사항】
1. 사주 구성 특징 (일간 중심 간략 설명)
2. {focus} 관련 핵심 분석 (구체적 시기, 인연 특징, 주의사항 포함)
3. 2026년 현재 운세 흐름
4. 행운을 높이는 실천 조언 2~3가지

형식: 친절하고 따뜻하지만 전문적인 어조로, 총 600~900자 내외.
한자 사용 최소화, 고객이 바로 이해할 수 있는 실용적 표현 사용.
각 섹션은 ▶ 기호로 구분해주세요."""

    payload = _json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = _json.loads(resp.read())
            return result["content"][0]["text"]
    except Exception as e:
        print(f"[Claude API] 분석 오류: {e}")
        return ""


def send_analysis_email(order: dict, analysis_text: str) -> bool:
    """분석 결과를 운영자 이메일로 발송"""
    if not GMAIL_APP_PASSWORD or not analysis_text:
        return False

    name    = order["name"]
    product = order["product"]
    dm      = order.get("delivery_method", "이메일")
    dc      = order.get("delivery_contact", "")

    subject = f"[사주분석 완료] {name}님 - {product}"

    html = f"""
<html><body style="font-family:'Malgun Gothic',sans-serif;max-width:680px;margin:0 auto;padding:24px;background:#f9f6ff;">
<div style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 16px rgba(100,60,200,.08);">

<div style="text-align:center;padding-bottom:24px;border-bottom:2px solid #e8e0ff;">
  <h1 style="color:#6b21a8;font-size:22px;margin:0;">✨ 사주 분석 결과</h1>
  <p style="color:#888;font-size:13px;margin:8px 0 0;">{product}</p>
</div>

<div style="margin:24px 0;padding:16px;background:#f5f0ff;border-radius:8px;font-size:13px;color:#555;">
  <b>의뢰인:</b> {name}&nbsp;&nbsp;|&nbsp;&nbsp;
  <b>항목:</b> {product}&nbsp;&nbsp;|&nbsp;&nbsp;
  <b>전달 방법:</b> {dm} {f"({dc})" if dc else ""}
</div>

<div style="font-size:15px;line-height:1.9;color:#2d2040;white-space:pre-line;">
{analysis_text}
</div>

<div style="margin-top:32px;padding-top:16px;border-top:1px solid #e8e0ff;font-size:12px;color:#aaa;text-align:center;">
  사주마루 AI 분석 시스템 · 고객 전달 후 이 메일은 보관하세요
</div>
</div>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = OPERATOR_EMAIL
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, OPERATOR_EMAIL, msg.as_string())
        print(f"[분석메일] {name} / {product} → 발송 완료")
        return True
    except Exception as e:
        print(f"[분석메일] 발송 실패: {e}")
        return False


def process_order_with_analysis(order: dict) -> dict:
    """주문 1건 → FL 자동입력 + Claude 사주분석 메일 발송"""
    results = {}

    # 1) Fortune LAB 주문
    try:
        import sys
        from pathlib import Path as _P
        sys.path.insert(0, str(_P(__file__).parent))
        from fl_order import place_order
        results["fl"] = place_order(order)
    except Exception as e:
        results["fl"] = {"success": False, "error": str(e)}

    # 2) Claude 사주 분석 (ANTHROPIC_API_KEY 있을 때만)
    if ANTHROPIC_API_KEY:
        print(f"[분석] {order['name']} / {order['product']} 분석 중...")
        analysis = analyze_saju(order)
        if analysis:
            sent = send_analysis_email(order, analysis)
            results["analysis"] = {"success": sent, "chars": len(analysis)}
        else:
            results["analysis"] = {"success": False, "error": "분석 생성 실패"}
    else:
        results["analysis"] = {"success": False, "error": "ANTHROPIC_API_KEY 없음"}

    return results


if __name__ == "__main__":
    # 단독 테스트
    sample = {
        "name": "테스트",
        "gender": "여성",
        "cal_type": "음력",
        "year": 1969, "month": 4, "day": 30,
        "hour": 4,  # 인시
        "product": "직장운",
        "customer_email": OPERATOR_EMAIL,
        "delivery_method": "이메일",
        "delivery_contact": OPERATOR_EMAIL,
    }
    result = process_order_with_analysis(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))
