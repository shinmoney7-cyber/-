#!/usr/bin/env python3
"""
Fortune LAB PDF 수신 → 커버 교체(사주톡톡→사주마루) → 고객 전달
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
from sms_notify import send_sms

# .env 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GMAIL_USER         = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
OPERATOR_EMAIL     = "shinmoney7@gmail.com"
ADD_COVER_SCRIPT   = Path(__file__).parent / "add_cover.py"

# FL 발신 식별용 키워드 (이메일 From/Subject)
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
    """이메일에서 PDF 첨부파일 목록 반환 [(filename, bytes)]"""
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


def extract_name_from_email(msg):
    """FL 이메일에서 고객 이름 추출"""
    subj = decode_str(msg.get("Subject", ""))
    body = get_body(msg)

    patterns = [
        r"([가-힣]{2,4})\s*님",
        r"의뢰인[:\s]*([가-힣]{2,4})",
        r"고객명[:\s]*([가-힣]{2,4})",
        r"이름[:\s]*([가-힣]{2,4})",
        r"성함[:\s]*([가-힣]{2,4})",
    ]
    skip = {"사주", "마루", "톡톡", "운세", "분석", "결과", "전달", "완료", "확정"}

    for text in [subj, body]:
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                name = m.group(1)
                if name not in skip:
                    return name
    return None


def find_customer_delivery(mail, customer_name):
    """
    '[사주마루]' 주문 이메일에서 해당 고객의 전달 방법·연락처 조회
    Returns: {"method": str, "contact": str, "name": str} or None
    """
    try:
        # 제목에 [사주마루]가 있는 이메일 검색
        _, ids = mail.search(None, 'SUBJECT "[사주마루]"')
    except Exception:
        return None

    all_ids = [i for i in ids[0].split() if i]
    if not all_ids:
        return None

    for eid in reversed(all_ids[-60:]):  # 최근 60개
        try:
            _, data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            body = get_body(msg)
        except Exception:
            continue

        if not body or customer_name not in body:
            continue

        # 이 이메일에서 전달 정보 파싱
        method = contact = ""
        for line in body.splitlines():
            stripped = line.strip()
            if "전달 방법" in stripped:
                contact_part = stripped.split(":", 1)
                if len(contact_part) > 1:
                    method = contact_part[1].strip()
            elif "전달 받을 곳" in stripped or ("연락처" in stripped and not contact):
                contact_part = stripped.split(":", 1)
                if len(contact_part) > 1:
                    contact = contact_part[1].strip()

        if contact:
            return {"method": method or "이메일", "contact": contact, "name": customer_name}

    return None


def apply_cover(pdf_bytes):
    """add_cover.py 호출 → 커버 교체된 PDF bytes 반환"""
    if not ADD_COVER_SCRIPT.exists():
        print("[커버] add_cover.py 없음 → 원본 반환")
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
        print(f"[커버] {result.stdout.strip()}")
        if result.stderr:
            print(f"[커버] stderr: {result.stderr.strip()[:200]}")

        if os.path.exists(out):
            with open(out, "rb") as f:
                return f.read()

    print("[커버] 출력 파일 없음 → 원본 반환")
    return pdf_bytes


def send_to_customer(customer_info, pdf_bytes, pdf_name, subject_hint=""):
    """고객에게 PDF 이메일 전송 (이메일 외 수단은 운영자 알림)"""
    if not GMAIL_APP_PASSWORD:
        print("[전달] GMAIL_APP_PASSWORD 없음")
        return False

    method  = customer_info.get("method", "이메일")
    contact = customer_info.get("contact", "")
    name    = customer_info.get("name", "고객")

    if method == "이메일" and contact and "@" in contact:
        return _email_pdf(contact, name, pdf_bytes, pdf_name, subject_hint)
    else:
        # SMS / 카카오 등 → 운영자에게 알림 후 PDF 첨부
        return _notify_operator(name, method, contact, pdf_bytes, pdf_name)


def _email_pdf(to_addr, name, pdf_bytes, pdf_name, subject_hint):
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[사주마루] {name}님 분석 결과" + (f" - {subject_hint}" if subject_hint else "")
    msg["From"]    = GMAIL_USER
    msg["To"]      = to_addr

    html = f"""<html><body style="font-family:'Malgun Gothic',sans-serif;max-width:640px;margin:0 auto;padding:24px;">
<div style="background:#f9f6ff;border-radius:16px;padding:32px;text-align:center;">
  <h1 style="color:#6b21a8;font-size:22px;margin:0 0 12px;">✨ 사주마루 분석 결과</h1>
  <p style="color:#555;font-size:15px;margin:0 0 8px;">{name}님의 사주 분석 결과를 첨부드립니다.</p>
  <p style="color:#888;font-size:13px;margin:0;">첨부 PDF 파일을 확인해 주세요.</p>
  <hr style="margin:24px 0;border:none;border-top:1px solid #e0d8ff;">
  <p style="color:#aaa;font-size:12px;margin:0;">사주마루 · 정통 만세력 기반 명리분석</p>
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
            srv.sendmail(GMAIL_USER, to_addr, msg.as_string())
        print(f"  ✅ {name}님 → {to_addr} 이메일 전송 완료")
<<<<<<< HEAD
        send_sms(f"[사주마루] {name}님 PDF 발송완료 → {to_addr}")
=======
>>>>>>> origin/main
        return True
    except Exception as e:
        print(f"  ❌ 이메일 전송 실패: {e}")
        return False


def _notify_operator(name, method, contact, pdf_bytes, pdf_name):
    """이메일 외 수단(SMS, 카카오) → 운영자에게 알림 + PDF 첨부"""
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[사주마루 전달 필요] {name}님 · {method} ({contact})"
    msg["From"]    = GMAIL_USER
    msg["To"]      = OPERATOR_EMAIL

    html = f"""<html><body style="font-family:'Malgun Gothic',sans-serif;padding:24px;">
<div style="background:#fff3cd;border-left:4px solid #ffc107;border-radius:8px;padding:20px;">
  <h2 style="margin:0 0 12px;color:#856404;">⚡ 수동 전달 필요</h2>
  <p><b>고객명:</b> {name}님</p>
  <p><b>전달 방법:</b> {method}</p>
  <p><b>연락처:</b> {contact}</p>
  <p style="margin-top:12px;color:#555;">첨부 PDF를 위 연락처({method})로 전달해 주세요.</p>
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
<<<<<<< HEAD
        send_sms(f"[사주마루] {name}님 {method}전달 필요 · {contact}")
=======
>>>>>>> origin/main
        return True
    except Exception as e:
        print(f"  ❌ 운영자 알림 실패: {e}")
        return False


def send_to_operator_as_fallback(name, pdf_bytes, reason=""):
    """고객 정보 매칭 실패 → 운영자에게 원본 전달"""
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[사주마루 PDF 처리] {name or '?'} - 수동 전달 필요 {reason}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = OPERATOR_EMAIL

    body = f"고객명 '{name}'의 사주 결과입니다.\n연락처 정보를 찾지 못해 자동 전달되지 않았습니다. 직접 전달해 주세요.\n{reason}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    att = MIMEBase("application", "pdf")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    safe_name = re.sub(r'[^\w가-힣.\-]', '_', name or "result")
    att.add_header("Content-Disposition", f'attachment; filename="{safe_name}_사주마루.pdf"')
    msg.attach(att)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as srv:
            srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            srv.sendmail(GMAIL_USER, OPERATOR_EMAIL, msg.as_string())
        print(f"  📬 운영자 폴백 전달 완료 (이름: {name})")
    except Exception as e:
        print(f"  ❌ 운영자 폴백 실패: {e}")


def is_fl_email(sender, subject):
    """FL 발신 이메일인지 판단"""
    lower_sender  = sender.lower()
    lower_subject = subject.lower()
    for hint in FL_SENDER_HINTS:
        if hint in lower_sender or hint in lower_subject:
            return True
    return False


def run():
    if not GMAIL_APP_PASSWORD:
        print("[ERROR] GMAIL_APP_PASSWORD 없음")
        sys.exit(1)

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    # 미읽은 메일 전체 조회
    _, ids = mail.search(None, "UNSEEN")
    all_unseen = [i for i in ids[0].split() if i]
    print(f"[Gmail] 미읽은 메일 총 {len(all_unseen)}개")

    # 헤더만 먼저 읽어 FL 이메일 후보 선별
    candidates = []
    for eid in all_unseen:
        _, hdr = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
        raw = hdr[0][1] if hdr and hdr[0] else b""
        parsed = email.message_from_bytes(raw)
        sender  = parsed.get("From", "")
        subject = decode_str(parsed.get("Subject", ""))

        # [사주마루] 우리 자신의 메일은 건너뜀
        if "[사주마루]" in subject:
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
            continue  # PDF 없으면 건너뜀

        subj   = decode_str(msg.get("Subject", ""))
        sender = msg.get("From", "")
        print(f"\n[FL PDF] '{subj}' (from: {sender})")

        customer_name = extract_name_from_email(msg)
        print(f"  추출된 이름: {customer_name or '(없음)'}")

        for pdf_name, pdf_bytes in pdfs:
            print(f"  PDF: {pdf_name} ({len(pdf_bytes):,} bytes)")

            # 1) 커버 교체
            modified = apply_cover(pdf_bytes)

            # 2) 고객 연락처 조회
            if customer_name:
                info = find_customer_delivery(mail, customer_name)
            else:
                info = None

            # 3) 전달
            if info:
                send_to_customer(info, modified, pdf_name, subj)
            else:
                reason = f"(고객명 '{customer_name}' 주문 메일 매칭 실패)" if customer_name else "(이름 추출 불가)"
                send_to_operator_as_fallback(customer_name or "?", modified, reason)

        # 처리 완료 → 읽음 표시
        mail.store(eid, "+FLAGS", "\\Seen")
        processed += 1

    print(f"\n[완료] {processed}건 처리")
    mail.close()
    mail.logout()


if __name__ == "__main__":
    run()
