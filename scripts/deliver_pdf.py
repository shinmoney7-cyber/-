#!/usr/bin/env python3
"""
Fortune LAB PDF 수신 → Claude 인적사항 검증 → 커버 교체 → 고객 전달
- 발송 전 Claude가 인적사항 전체를 재확인하고 orders_db에 기록
- kakao_notify로 단계별 알림
"""
import imaplib, email, os, re, smtplib, sys, subprocess
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent))

# .env 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from orders_db    import find_pending_for_name_product, mark_claude_verified, mark_delivered, list_orders
from kakao_notify import notify_verified_and_sending, notify_delivered, notify_error

GMAIL_USER         = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
OPERATOR_EMAIL     = "shinmoney7@gmail.com"
ADD_COVER_SCRIPT   = Path(__file__).parent / "add_cover.py"
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")

FL_SENDER_HINTS = ["coredev", "fortune", "사주", "분석결과", "결과전달", "운세"]


def decode_str(s):
    parts = decode_header(s or "")
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")
    return ""


def get_pdf_attachments(msg):
    pdfs = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = decode_str(part.get_filename() or "")
        ct = part.get_content_type()
        if (filename and filename.lower().endswith(".pdf")) or ct == "application/pdf":
            data = part.get_payload(decode=True)
            if data:
                pdfs.append((filename or "result.pdf", data))
    return pdfs


def extract_name_and_product(msg):
    """FL 이메일에서 고객 이름 + 상품 추출"""
    subj = decode_str(msg.get("Subject", ""))
    body = get_body(msg)

    name_patterns = [
        r"([가-힣]{2,4})\s*님",
        r"의뢰인[:\s]*([가-힣]{2,4})",
        r"고객명[:\s]*([가-힣]{2,4})",
        r"성함[:\s]*([가-힣]{2,4})",
    ]
    skip = {"사주", "마루", "톡톡", "운세", "분석", "결과", "전달", "완료"}

    product_hints = {
        "연애": "연애운", "재물": "재물운", "건강": "건강운", "평생": "평생운",
        "취업": "취업운", "신년": "새해운세", "사업": "사업운",
    }

    name = None
    product = None

    for text in [subj, body]:
        for pattern in name_patterns:
            m = re.search(pattern, text)
            if m and m.group(1) not in skip:
                name = m.group(1)
                break
        for hint, pname in product_hints.items():
            if hint in text:
                product = pname
                break
        if name:
            break

    return name, product


def claude_verify_order(order: dict, pdf_text_summary: str = "") -> tuple[bool, str]:
    """
    Claude API로 발송 전 인적사항 검증
    Returns: (ok: bool, note: str)
    """
    if not ANTHROPIC_API_KEY:
        note = "ANTHROPIC_API_KEY 미설정 — 자동승인"
        print(f"  [검증] {note}")
        return True, note

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    birth = f"{order.get('year')}.{order.get('month')}.{order.get('day')} ({order.get('cal_type','양력')})"
    hour  = f"{order.get('hour')}시" if order.get('hour') is not None else "모름"

    prompt = f"""다음 주문 인적사항을 검토하고 발송 가능 여부를 판단해줘.

【주문번호】{order.get('order_id','')}
【계정】{order.get('account','')}
【성함】{order.get('name','')}
【성별】{order.get('gender','')}
【생년월일】{birth}
【태어난 시간】{hour}
【상품】{order.get('product','')}
【전달 방법】{order.get('delivery_method','')}
【전달처】{order.get('delivery_contact','')}

확인 항목:
1. 성함이 2-4자 한국 이름 형식인가?
2. 생년월일이 유효한 날짜인가? (1900-2010년 사이)
3. 성별이 남성 또는 여성인가?
4. 전달처 정보가 있는가? (이메일이면 @ 포함, 전화면 숫자 10자리 이상)
5. 상품명이 인식 가능한가?

JSON으로만 답해: {{"ok": true/false, "note": "한줄 확인 메모"}}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        import json
        # JSON 추출
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            result = json.loads(m.group())
            ok   = bool(result.get("ok", True))
            note = result.get("note", "검증완료")
            print(f"  [Claude 검증] ok={ok} — {note}")
            return ok, note
    except Exception as e:
        note = f"검증 오류: {e} — 자동승인"
        print(f"  [검증] {note}")
        return True, note

    return True, "검증 응답 파싱 실패 — 자동승인"


def find_order_for_name(name: str, product: str = None) -> dict | None:
    """이름(+상품)으로 처리 중인 주문 조회"""
    if product:
        order = find_pending_for_name_product(name, product)
        if order:
            return order
    # 상품 매칭 없으면 이름만으로
    for o in list_orders():
        if o.get("name") == name and o.get("status") in ("pending", "paid", "processing"):
            return o
    return None


def find_customer_delivery(mail, customer_name: str) -> dict | None:
    """주문 이메일에서 고객 전달 정보 조회 (기존 로직 유지)"""
    try:
        _, ids = mail.search(None, 'SUBJECT "[사주마루]"')
    except Exception:
        return None

    all_ids = [i for i in ids[0].split() if i]
    if not all_ids:
        return None

    for eid in reversed(all_ids[-60:]):
        try:
            _, data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            body = get_body(msg)
        except Exception:
            continue

        if not body or customer_name not in body:
            continue

        method = contact = ""
        for line in body.splitlines():
            stripped = line.strip()
            if "전달 방법" in stripped:
                parts = stripped.split(":", 1)
                if len(parts) > 1:
                    method = parts[1].strip()
            elif "전달 받을 곳" in stripped or ("연락처" in stripped and not contact):
                parts = stripped.split(":", 1)
                if len(parts) > 1:
                    contact = parts[1].strip()

        if contact:
            return {"method": method or "이메일", "contact": contact, "name": customer_name}

    return None


def apply_cover(pdf_bytes: bytes) -> bytes:
    if not ADD_COVER_SCRIPT.exists():
        return pdf_bytes
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "original.pdf")
        out = os.path.join(tmp, "output.pdf")
        with open(inp, "wb") as f:
            f.write(pdf_bytes)
        result = subprocess.run(
            [sys.executable, str(ADD_COVER_SCRIPT), inp, out],
            capture_output=True, text=True, timeout=90
        )
        if result.stdout.strip():
            print(f"  [커버] {result.stdout.strip()}")
        if os.path.exists(out):
            with open(out, "rb") as f:
                return f.read()
    return pdf_bytes


def _email_pdf(to_addr: str, name: str, pdf_bytes: bytes, pdf_name: str, order_id: str, acct_name: str = "사주마루") -> bool:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[{acct_name}] {name}님 사주 분석 결과 (#{order_id})"
    msg["From"]    = GMAIL_USER
    msg["To"]      = to_addr

    html = f"""<html><body style="font-family:'Malgun Gothic',sans-serif;max-width:640px;margin:0 auto;padding:24px;">
<div style="background:#f9f6ff;border-radius:16px;padding:32px;text-align:center;">
  <h1 style="color:#6b21a8;font-size:22px;margin:0 0 12px;">✨ {acct_name} 분석 결과</h1>
  <p style="color:#555;font-size:15px;margin:0 0 8px;">{name}님의 사주 분석 결과를 첨부드립니다.</p>
  <p style="color:#888;font-size:13px;margin:0;">주문번호: #{order_id}</p>
  <hr style="margin:24px 0;border:none;border-top:1px solid #e0d8ff;">
  <p style="color:#aaa;font-size:12px;margin:0;">{acct_name} · 정통 만세력 기반 명리분석</p>
</div></body></html>"""

    msg.attach(MIMEText(html, "html", "utf-8"))

    att = MIMEBase("application", "pdf")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    safe_name = re.sub(r'[^\w가-힣.\-]', '_', name)
    att.add_header("Content-Disposition", f'attachment; filename="{safe_name}_{acct_name}.pdf"')
    msg.attach(att)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as srv:
            srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            srv.sendmail(GMAIL_USER, to_addr, msg.as_string())
        print(f"  ✅ {name}님 → {to_addr} 이메일 전송 완료")
        return True
    except Exception as e:
        print(f"  ❌ 이메일 전송 실패: {e}")
        return False


def _notify_operator(name: str, method: str, contact: str, pdf_bytes: bytes, order_id: str) -> bool:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[사주마루 전달필요] #{order_id} {name}님 · {method} ({contact})"
    msg["From"]    = GMAIL_USER
    msg["To"]      = OPERATOR_EMAIL

    html = f"""<html><body style="padding:24px;">
<div style="background:#fff3cd;border-left:4px solid #ffc107;padding:20px;border-radius:8px;">
  <h2 style="color:#856404;margin:0 0 12px;">⚡ 수동 전달 필요</h2>
  <p><b>주문번호:</b> #{order_id}</p>
  <p><b>고객명:</b> {name}님</p>
  <p><b>전달 방법:</b> {method}</p>
  <p><b>연락처:</b> {contact}</p>
  <p>첨부 PDF를 위 연락처로 전달해 주세요.</p>
</div></body></html>"""

    msg.attach(MIMEText(html, "html", "utf-8"))
    att = MIMEBase("application", "pdf")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    safe_name = re.sub(r'[^\w가-힣.\-]', '_', name)
    att.add_header("Content-Disposition", f'attachment; filename="{safe_name}_사주마루.pdf"')
    msg.attach(att)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as srv:
            srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            srv.sendmail(GMAIL_USER, OPERATOR_EMAIL, msg.as_string())
        print(f"  📬 운영자 알림 발송 ({method}: {contact})")
        return True
    except Exception as e:
        print(f"  ❌ 운영자 알림 실패: {e}")
        return False


def is_fl_email(sender: str, subject: str) -> bool:
    lower_s = sender.lower()
    lower_j = subject.lower()
    for hint in FL_SENDER_HINTS:
        if hint in lower_s or hint in lower_j:
            return True
    return False


def run():
    if not GMAIL_APP_PASSWORD:
        print("[ERROR] GMAIL_APP_PASSWORD 없음")
        sys.exit(1)

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    _, ids = mail.search(None, "UNSEEN")
    all_unseen = [i for i in ids[0].split() if i]
    print(f"[Gmail] 미읽은 메일: {len(all_unseen)}개")

    candidates = []
    for eid in all_unseen:
        _, hdr = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
        raw = hdr[0][1] if hdr and hdr[0] else b""
        parsed = email.message_from_bytes(raw)
        sender  = parsed.get("From", "")
        subject = decode_str(parsed.get("Subject", ""))
        if "[사주마루]" in subject or "[사주보는언니]" in subject or "[사주마루77]" in subject:
            continue
        if is_fl_email(sender, subject):
            candidates.append(eid)

    print(f"[Gmail] FL PDF 후보: {len(candidates)}개")

    processed = 0
    for eid in candidates:
        _, data = mail.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])

        pdfs = get_pdf_attachments(msg)
        if not pdfs:
            continue

        subj = decode_str(msg.get("Subject", ""))
        print(f"\n[FL PDF] '{subj}'")

        customer_name, product_hint = extract_name_and_product(msg)
        print(f"  이름: {customer_name or '?'} / 상품: {product_hint or '?'}")

        for pdf_name, pdf_bytes in pdfs:
            print(f"  PDF: {pdf_name} ({len(pdf_bytes):,} bytes)")

            # 1) orders_db에서 주문 찾기
            order = None
            if customer_name:
                order = find_order_for_name(customer_name, product_hint)

            # 2) Claude 인적사항 검증
            if order:
                oid       = order["order_id"]
                acct_name_map = {"sm": "사주마루", "un": "사주보는언니", "s77": "사주마루77"}
                acct_name = acct_name_map.get(order.get("account", "sm"), "사주마루")

                print(f"  주문 #{oid} 발견 → Claude 검증 중...")
                ok, note = claude_verify_order(order)

                if not ok:
                    msg_err = f"Claude 검증 불합격: {note}"
                    notify_error(order, oid, msg_err)
                    print(f"  ❌ 검증 실패 → 운영자에게 경고: {note}")
                    _notify_operator(order["name"], "검증실패-확인필요", OPERATOR_EMAIL, pdf_bytes, oid)
                    continue

                # DB에 검증 완료 기록
                mark_claude_verified(oid, note)
                notify_verified_and_sending(order, oid, note)

                # 3) 커버 교체
                modified = apply_cover(pdf_bytes)

                # 4) 전달
                method  = order.get("delivery_method", "이메일")
                contact = order.get("delivery_contact", "")

                if method == "이메일" and contact and "@" in contact:
                    sent = _email_pdf(contact, order["name"], modified, pdf_name, oid, acct_name)
                else:
                    sent = _notify_operator(order["name"], method, contact, modified, oid)

                if sent:
                    mark_delivered(oid, method, contact)
                    notify_delivered(order, oid)
                else:
                    notify_error(order, oid, "전달 실패")

            else:
                # 주문 DB 미매칭 → 기존 방식 (이메일에서 전달 정보 찾기)
                print(f"  ⚠️ 주문 DB 매칭 실패 — 이메일에서 전달 정보 검색...")
                info = find_customer_delivery(mail, customer_name) if customer_name else None

                modified = apply_cover(pdf_bytes)

                if info:
                    method  = info.get("method", "이메일")
                    contact = info.get("contact", "")
                    name    = info.get("name", customer_name or "?")
                    if method == "이메일" and contact and "@" in contact:
                        _email_pdf(contact, name, modified, pdf_name, "??", "사주마루")
                    else:
                        _notify_operator(name, method, contact, modified, "??")
                else:
                    # 완전 폴백: 운영자에게 전달
                    reason = f"주문 DB+이메일 매칭 실패 (이름: {customer_name})"
                    _notify_operator(customer_name or "?", "확인필요", OPERATOR_EMAIL, modified, "??")

        mail.store(eid, "+FLAGS", "\\Seen")
        processed += 1

    print(f"\n[완료] {processed}건 처리")
    mail.close()
    mail.logout()


if __name__ == "__main__":
    run()
