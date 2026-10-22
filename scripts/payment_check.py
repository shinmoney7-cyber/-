#!/usr/bin/env python3
"""
입금 확인 스크립트
Gmail에서 계좌이체/입금 알림 이메일을 파싱해 orders_db에 입금 처리
토스, 카카오페이, 은행 입금 알림 지원
"""
import imaplib, email, os, re, sys
from email.header import decode_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from orders_db    import list_orders, mark_paid, update_status
from kakao_notify import notify_payment_confirmed, notify_analysis_started

GMAIL_USER         = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# 입금 이메일 발신자/제목 키워드
PAYMENT_HINTS = [
    "입금", "이체", "결제", "토스", "카카오페이", "kakao", "toss",
    "무통장", "계좌이체", "페이코", "네이버페이",
    "신한", "shinhan",  # 신한은행 입금 알림
]

# 상품 금액 매핑 (확인용)
PRODUCT_PRICES = {
    "성향·기질 분석": 19800,
    "평생운":        29800,
    "연애운":        19800,
    "배우자운·결혼운": 29800,
    "재물운":        19800,
    "건강운":        19800,
    "대운·세운":     29800,
    "새해운세":      29800,
    "사업운":        29800,
    "도화살 전문분석": 19800,
}


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


def extract_amount_and_name(body: str, subject: str) -> tuple:
    """본문에서 금액과 입금자명 추출"""
    amount = None
    payer_name = None
    text = subject + " " + body

    # 금액 추출 (숫자+원 패턴)
    amount_patterns = [
        r"(\d{1,3}(?:,\d{3})*)\s*원",
        r"₩\s*(\d{1,3}(?:,\d{3})*)",
    ]
    for pat in amount_patterns:
        m = re.search(pat, text)
        if m:
            amount = int(m.group(1).replace(",", ""))
            break

    # 입금자명 추출
    name_patterns = [
        r"입금자[:\s]+([가-힣]{2,4})",
        r"보내는\s*분[:\s]+([가-힣]{2,4})",
        r"의뢰인[:\s]+([가-힣]{2,4})",
        r"([가-힣]{2,4})\s*님.*입금",
    ]
    for pat in name_patterns:
        m = re.search(pat, text)
        if m:
            payer_name = m.group(1)
            break

    return amount, payer_name


def find_matching_order(payer_name: str, amount: int) -> dict | None:
    """입금자명으로 pending 주문 매칭"""
    # 이름 완전 일치
    pending = [o for o in list_orders(status="pending") if o.get("name") == payer_name]
    if pending:
        return pending[0]

    # 금액으로 보조 매칭 (이름 없을 때)
    if amount and not payer_name:
        for o in list_orders(status="pending"):
            expected = PRODUCT_PRICES.get(o.get("product", ""), 0)
            if expected and abs(expected - amount) < 100:
                return o

    return None


def run():
    if not GMAIL_APP_PASSWORD:
        print("[ERROR] GMAIL_APP_PASSWORD 없음")
        sys.exit(1)

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    _, ids = mail.search(None, "UNSEEN")
    all_unseen = [i for i in ids[0].split() if i]
    print(f"[입금확인] 미읽은 메일: {len(all_unseen)}개")

    candidates = []
    for eid in all_unseen:
        _, hdr = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
        raw = hdr[0][1] if hdr and hdr[0] else b""
        parsed = email.message_from_bytes(raw)
        sender  = parsed.get("From", "").lower()
        subject = decode_str(parsed.get("Subject", ""))
        full    = sender + " " + subject.lower()
        if any(hint in full for hint in PAYMENT_HINTS):
            candidates.append((eid, subject))

    print(f"[입금확인] 입금 이메일 후보: {len(candidates)}개")

    processed = 0
    for eid, subject in candidates:
        _, data = mail.fetch(eid, "(RFC822)")
        msg  = email.message_from_bytes(data[0][1])
        body = get_body(msg)

        amount, payer_name = extract_amount_and_name(body, subject)
        print(f"\n[입금] 제목: {subject[:50]}")
        print(f"  금액: {amount:,}원" if amount else "  금액: 파싱 실패")
        print(f"  입금자: {payer_name or '파싱 실패'}")

        order = find_matching_order(payer_name, amount)
        if order:
            oid = order["order_id"]
            detail = f"입금 {amount:,}원 / {payer_name}" if amount else payer_name or ""
            mark_paid(oid, detail)
            print(f"  ✅ 주문 #{oid} {order['name']} / {order['product']} 입금확인")
            notify_payment_confirmed(order, oid)
            notify_analysis_started(order, oid)
        else:
            print(f"  ⚠️ 매칭 주문 없음 (입금자: {payer_name}, 금액: {amount})")

        mail.store(eid, "+FLAGS", "\\Seen")
        processed += 1

    print(f"\n[완료] {processed}건 처리")
    mail.close()
    mail.logout()


if __name__ == "__main__":
    run()
