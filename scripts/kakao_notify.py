"""
카카오 알림톡 + SMS 통합 알림
- Solapi 알림톡(카카오비즈) 우선 → 실패 시 SMS fallback
- 관리자(신정희) + 고객 양방향 알림
환경변수:
  SOLAPI_API_KEY, SOLAPI_API_SECRET, SOLAPI_FROM
  KAKAO_CHANNEL_ID  (솔라피 카카오 채널 ID, 없으면 SMS만)
  NOTIFY_PHONE      (신정희 관리자 번호)
"""
import os, json, time, hmac, hashlib, uuid, requests
from pathlib import Path

# .env 자동 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SOLAPI_API_KEY    = os.getenv("SOLAPI_API_KEY", "")
SOLAPI_API_SECRET = os.getenv("SOLAPI_API_SECRET", "")
SOLAPI_FROM       = os.getenv("SOLAPI_FROM", "")
KAKAO_CHANNEL_ID  = os.getenv("KAKAO_CHANNEL_ID", "")
NOTIFY_PHONE      = os.getenv("NOTIFY_PHONE", "01083863712")   # 신정희
NOTIFY_EMAIL      = os.getenv("NOTIFY_EMAIL", "s70js@kakao.com")  # 신정희 카카오메일
BANK_ACCOUNT      = os.getenv("BANK_ACCOUNT", "신한은행 133-000-695010 (예금주: 신정희)")
SOLAPI_BASE       = "https://api.solapi.com"

ACCOUNT_NAMES = {
    "sm":  "사주마루",
    "un":  "사주보는언니",
    "s77": "사주마루77",
}


def _auth_header() -> dict:
    date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    salt = uuid.uuid4().hex
    msg = date + salt
    sig = hmac.new(SOLAPI_API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return {"Authorization": f"HMAC-SHA256 apiKey={SOLAPI_API_KEY}, date={date}, salt={salt}, signature={sig}"}


def _send_sms_raw(to: str, text: str) -> bool:
    if not all([SOLAPI_API_KEY, SOLAPI_API_SECRET, SOLAPI_FROM, to]):
        print(f"  [SMS] 미설정 — 건너뜀: {text[:30]}")
        return False
    payload = {"message": {"to": to, "from": SOLAPI_FROM, "text": text[:90]}}
    r = requests.post(f"{SOLAPI_BASE}/messages/v4/send", headers=_auth_header(), json=payload, timeout=10)
    ok = r.status_code == 200
    if not ok:
        print(f"  [SMS] 실패 {r.status_code}: {r.text[:100]}")
    return ok


def _send_alimtalk(to: str, template_id: str, variables: dict) -> bool:
    if not all([SOLAPI_API_KEY, SOLAPI_API_SECRET, SOLAPI_FROM, KAKAO_CHANNEL_ID, to]):
        return False
    payload = {
        "message": {
            "to": to,
            "from": SOLAPI_FROM,
            "kakaoOptions": {
                "pfId": KAKAO_CHANNEL_ID,
                "templateId": template_id,
                "variables": variables,
            },
        }
    }
    r = requests.post(f"{SOLAPI_BASE}/messages/v4/send", headers=_auth_header(), json=payload, timeout=10)
    ok = r.status_code == 200
    if not ok:
        print(f"  [알림톡] 실패 — SMS fallback: {r.text[:80]}")
    return ok


def _kakao_or_sms(to: str, text: str, template_id: str = "", variables: dict = None) -> bool:
    """알림톡 시도 → 실패 시 SMS fallback"""
    if template_id and variables and KAKAO_CHANNEL_ID:
        if _send_alimtalk(to, template_id, variables):
            return True
    return _send_sms_raw(to, text)


def _send_admin_email(subject: str, html_body: str):
    """신정희에게 이메일 알림"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    gmail_user = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
    gmail_pw   = os.getenv("GMAIL_APP_PASSWORD", "")
    if not gmail_pw or not NOTIFY_EMAIL:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(gmail_user, gmail_pw)
            s.send_message(msg)
        print(f"  [메일] 신정희 알림: {subject[:40]}")
    except Exception as e:
        print(f"  [메일] 관리자 알림 실패: {e}")


# ──────────────────────────────────────────
# 공개 알림 함수들
# ──────────────────────────────────────────

def notify_new_order(order: dict, order_id: str):
    """신규 주문 접수 — 관리자 + 고객 동시 알림"""
    acct_name = ACCOUNT_NAMES.get(order.get("account", "sm"), "사주마루")
    name      = order.get("name", "")
    product   = order.get("product", "")
    dm        = order.get("delivery_method", "이메일")
    contact   = order.get("delivery_contact", "")

    # 관리자 알림 (신정희) — 카톡+메일 동시
    admin_text = (
        f"[{acct_name}] 신규주문 #{order_id}\n"
        f"성함: {name}\n"
        f"상품: {product}\n"
        f"전달: {dm} {contact}\n"
        f"⚡입금확인 필요"
    )
    if NOTIFY_PHONE:
        _kakao_or_sms(NOTIFY_PHONE, admin_text)
    _send_admin_email(
        f"[{acct_name}] 신규주문 #{order_id} — {name} / {product}",
        f"<pre style='font-family:sans-serif'>{admin_text}</pre>"
    )

    # 고객 알림 (전화번호가 있을 때만)
    customer_phone = _extract_phone(contact, dm)
    if customer_phone:
        customer_text = (
            f"[{acct_name}] 주문접수 완료!\n"
            f"{name}님, #{order_id}\n"
            f"상품: {product}\n"
            f"입금 확인 후 사주 분석을 시작합니다.\n"
            f"문의: shinmoney7@gmail.com"
        )
        _kakao_or_sms(customer_phone, customer_text)


def notify_payment_confirmed(order: dict, order_id: str):
    """입금 확인 — 관리자 + 고객"""
    acct_name = ACCOUNT_NAMES.get(order.get("account", "sm"), "사주마루")
    name      = order.get("name", "")
    product   = order.get("product", "")
    contact   = order.get("delivery_contact", "")
    dm        = order.get("delivery_method", "이메일")

    admin_text = f"[{acct_name}] 입금확인 #{order_id}\n{name} / {product}\n분석 시작합니다."
    if NOTIFY_PHONE:
        _kakao_or_sms(NOTIFY_PHONE, admin_text)
    _send_admin_email(f"[{acct_name}] 입금확인 #{order_id} — {name}", f"<pre>{admin_text}</pre>")

    customer_phone = _extract_phone(contact, dm)
    if customer_phone:
        _kakao_or_sms(customer_phone,
            f"[{acct_name}] 입금 확인됐습니다 😊\n"
            f"{name}님, #{order_id}\n"
            f"지금 사주 분석 시작합니다.\n"
            f"결과는 {dm}으로 발송 예정입니다."
        )


def notify_analysis_started(order: dict, order_id: str):
    """사주 분석 시작 알림 — 고객만"""
    acct_name = ACCOUNT_NAMES.get(order.get("account", "sm"), "사주마루")
    name      = order.get("name", "")
    product   = order.get("product", "")
    contact   = order.get("delivery_contact", "")
    dm        = order.get("delivery_method", "이메일")

    customer_phone = _extract_phone(contact, dm)
    if customer_phone:
        _kakao_or_sms(customer_phone,
            f"[{acct_name}] 분석 시작!\n"
            f"{name}님 {product} 분석을 시작했습니다.\n"
            f"완료 시 {dm}으로 안내드릴게요."
        )


def notify_verified_and_sending(order: dict, order_id: str, verify_note: str = ""):
    """Claude 검증 완료 + 발송 예고 — 관리자 + 고객"""
    acct_name = ACCOUNT_NAMES.get(order.get("account", "sm"), "사주마루")
    name      = order.get("name", "")
    product   = order.get("product", "")
    contact   = order.get("delivery_contact", "")
    dm        = order.get("delivery_method", "이메일")

    admin_text = (
        f"[{acct_name}] 발송전확인 완료 #{order_id}\n"
        f"{name} / {product}\n"
        f"Claude 검증: {verify_note[:40] if verify_note else '완료'}\n"
        f"→ {dm} 발송 진행"
    )
    if NOTIFY_PHONE:
        _kakao_or_sms(NOTIFY_PHONE, admin_text)
    _send_admin_email(
        f"[{acct_name}] 발송전확인 완료 #{order_id} — {name}",
        f"<pre style='font-family:sans-serif'>{admin_text}</pre>"
    )

    customer_phone = _extract_phone(contact, dm)
    if customer_phone:
        _kakao_or_sms(customer_phone,
            f"[{acct_name}] 곧 발송됩니다!\n"
            f"{name}님, #{order_id}\n"
            f"{product} 결과를 {dm}으로 발송 중입니다.\n"
            f"잠시만 기다려주세요 🙏"
        )


def notify_delivered(order: dict, order_id: str):
    """발송 완료 — 관리자 + 고객"""
    acct_name = ACCOUNT_NAMES.get(order.get("account", "sm"), "사주마루")
    name      = order.get("name", "")
    product   = order.get("product", "")
    contact   = order.get("delivery_contact", "")
    dm        = order.get("delivery_method", "이메일")

    admin_text = f"[{acct_name}] 발송완료 #{order_id}\n{name} / {product} → {dm}: {contact}"
    if NOTIFY_PHONE:
        _kakao_or_sms(NOTIFY_PHONE, admin_text)
    _send_admin_email(
        f"[{acct_name}] 발송완료 #{order_id} — {name} / {product}",
        f"<pre style='font-family:sans-serif'>{admin_text}</pre>"
    )

    customer_phone = _extract_phone(contact, dm)
    if customer_phone:
        _kakao_or_sms(customer_phone,
            f"[{acct_name}] 발송 완료! 📩\n"
            f"{name}님, #{order_id}\n"
            f"{product} 결과를 {dm}으로 보냈습니다.\n"
            f"확인 후 궁금한 점은 답장 주세요 😊"
        )


def notify_error(order: dict, order_id: str, error_msg: str):
    """오류 알림 — 관리자만"""
    acct_name = ACCOUNT_NAMES.get(order.get("account", "sm"), "사주마루")
    error_text = (
        f"[{acct_name}] ❌ 오류 #{order_id}\n"
        f"{order.get('name','')} / {order.get('product','')}\n"
        f"{error_msg[:60]}"
    )
    if NOTIFY_PHONE:
        _kakao_or_sms(NOTIFY_PHONE, error_text)
    _send_admin_email(
        f"[{acct_name}] ❌ 오류 #{order_id} — {order.get('name','')}",
        f"<pre style='font-family:sans-serif;color:#c00'>{error_text}\n\n전체 오류:\n{error_msg}</pre>"
    )


def send_customer_guide(order: dict, order_id: str):
    """고객 주문 안내 메시지 전송"""
    acct_name = ACCOUNT_NAMES.get(order.get("account", "sm"), "사주마루")
    name      = order.get("name", "")
    birth_str = f"{order.get('year','')}.{order.get('month','')}.{order.get('day','')} ({order.get('cal_type','양력')})"
    gender    = order.get("gender", "")
    product   = order.get("product", "")
    dm        = order.get("delivery_method", "이메일")
    contact   = order.get("delivery_contact", "")

    bank_line = f"\n【입금 계좌】\n{BANK_ACCOUNT}" if BANK_ACCOUNT else ""
    guide_text = (
        f"[{acct_name}] 주문 접수 안내\n\n"
        f"안녕하세요 {name}님 😊\n"
        f"주문번호: #{order_id}\n\n"
        f"【접수된 정보】\n"
        f"성함: {name}\n"
        f"생년월일: {birth_str}\n"
        f"성별: {gender}\n"
        f"신청 상품: {product}\n"
        f"결과 전달: {dm}\n"
        f"전달처: {contact}\n"
        f"{bank_line}\n"
        f"입금 확인 후 분석을 시작합니다.\n"
        f"오류가 있으면 답장 주세요.\n"
        f"감사합니다 🙏"
    )

    customer_phone = _extract_phone(contact, dm)
    if customer_phone:
        _kakao_or_sms(customer_phone, guide_text[:300])

    # 이메일 전달인 경우 이메일로도 안내
    if dm == "이메일" and "@" in contact:
        _send_guide_email(contact, name, order_id, guide_text, acct_name)


def _send_guide_email(to_email: str, name: str, order_id: str, guide_text: str, acct_name: str):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    gmail_user = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
    gmail_pw   = os.getenv("GMAIL_APP_PASSWORD", "")
    if not gmail_pw:
        return

    html = f"""
<html><body style="font-family:sans-serif;max-width:520px;margin:0 auto;">
<div style="background:#1a1a2e;color:#e8d5b7;padding:24px;border-radius:12px;">
  <h2 style="color:#ffd700;margin-bottom:4px">🔮 {acct_name}</h2>
  <p style="color:#aaa;margin:0 0 20px">주문 접수 확인</p>
  <pre style="background:#0d0d1a;padding:16px;border-radius:8px;color:#e8d5b7;font-size:14px;white-space:pre-wrap">{guide_text}</pre>
  <p style="color:#888;font-size:12px;margin-top:16px">본 메일에 회신하시면 확인 후 답변드립니다.</p>
</div>
</body></html>
"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{acct_name}] 주문 접수 확인 #{order_id}"
    msg["From"]    = gmail_user
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(gmail_user, gmail_pw)
            s.send_message(msg)
        print(f"  [이메일] 안내 발송: {to_email}")
    except Exception as e:
        print(f"  [이메일] 안내 실패: {e}")


def _extract_phone(contact: str, delivery_method: str) -> str:
    """연락처에서 전화번호 추출"""
    if not contact:
        return ""
    # 카카오톡, SMS, 전화 전달 방법이면 번호로 사용
    if delivery_method in ("카카오톡", "SMS", "문자", "전화"):
        digits = "".join(c for c in contact if c.isdigit())
        if len(digits) >= 10:
            return digits
    # 연락처에 숫자가 10자리 이상이면 번호
    digits = "".join(c for c in contact if c.isdigit())
    if len(digits) >= 10:
        return digits
    return ""
