#!/usr/bin/env python3
"""
Gmail에서 사주마루 주문 이메일을 읽어 FL에 자동 주문
"""
import imaplib, email, os, re, sys
from email.header import decode_header
from pathlib import Path

# .env 자동 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GMAIL_USER         = os.getenv("GMAIL_USER", "shinmoney7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
OPERATOR_EMAIL     = "shinmoney7@gmail.com"

# 시진 → 시작 시간 (시진 범위 중간값)
TIME_MAP = {
    "모름": None,
    "자시": 0,  "축시": 2,  "인시": 4,  "묘시": 6,
    "진시": 8,  "사시": 10, "오시": 12, "미시": 14,
    "신시": 16, "유시": 18, "술시": 20, "해시": 22,
}

MENU_NAMES = [
    "성향·기질 분석", "평생운", "연애운", "배우자운·결혼운", "재물운",
    "건강운", "대운·세운", "부모운", "자식운", "형제간운", "새해운세",
    "월별운세", "수능·입시운", "재회운", "사업운", "이혼·결별운",
    "도화살 전문분석", "이런 사람 만나지 마라",
]


def decode_str(s):
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    return ""


def get_field(lines, key):
    for l in lines:
        if l.strip().startswith(key + ":") or l.strip().startswith(key + ": "):
            return l.split(":", 1)[1].strip()
    return ""


def parse_order_email(body: str) -> list:
    lines = body.splitlines()

    name    = get_field(lines, "성함")
    birth_raw = get_field(lines, "생년월일")
    gender  = get_field(lines, "성별") or "여성"
    time_raw = get_field(lines, "시간") or get_field(lines, "태어난 시간")
    delivery_method = get_field(lines, "전달 방법") or "이메일"
    contact = get_field(lines, "전달 받을 곳") or get_field(lines, "연락처")

    if not name or not birth_raw:
        return []

    # 생년월일 파싱
    cal_type = "음력" if "(음력)" in birth_raw else "양력"
    birth_clean = birth_raw.replace("(음력)", "").strip()
    m = re.match(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", birth_clean)
    if not m:
        return []
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))

    # 시간 파싱
    hour = None
    if time_raw and "모름" not in time_raw:
        for key, val in TIME_MAP.items():
            if key in time_raw:
                hour = val
                break

    # FL 결과는 항상 운영자 이메일로 수신 → 운영자가 고객에게 직접 전달
    customer_email = OPERATOR_EMAIL

    # 신청 상품 파싱 (ㆍ로 시작하는 줄)
    products = []
    in_items = False
    for l in lines:
        if "신청 항목" in l:
            in_items = True
            continue
        if in_items:
            if l.strip().startswith("합계"):
                break
            stripped = l.strip().lstrip("ㆍ").split("(")[0].strip()
            if stripped:
                matched = next((mn for mn in MENU_NAMES if mn in stripped or stripped in mn), stripped)
                products.append(matched)

    if not products:
        return []

    return [
        {
            "name": name,
            "gender": gender,
            "cal_type": cal_type,
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": 0,
            "product": p,
            "customer_email": customer_email,
            "delivery_method": delivery_method,
            "delivery_contact": contact,
        }
        for p in products
    ]


def run():
    if not GMAIL_APP_PASSWORD:
        print("[ERROR] GMAIL_APP_PASSWORD 환경변수가 없습니다.")
        sys.exit(1)

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    # 미읽은 메일 전체 검색 후 Python에서 제목 필터 (IMAP 한국어 인코딩 오류 방지)
    _, ids = mail.search(None, 'UNSEEN')
    all_unseen = [i for i in ids[0].split() if i]

    email_ids = []
    for eid in all_unseen:
        _, hdr = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
        raw_subj = hdr[0][1] if hdr and hdr[0] else b""
        subj = decode_str(email.message_from_bytes(raw_subj).get("Subject", ""))
        if "[사주마루]" in subj:
            email_ids.append(eid)

    print(f"[Gmail] 미읽은 주문 메일: {len(email_ids)}건")

    if not email_ids:
        print("[Gmail] 처리할 주문 없음")
        mail.logout()
        return

    sys.path.insert(0, str(Path(__file__).parent))
    from fl_order import place_order

    for eid in email_ids:
        _, data = mail.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        subject = decode_str(msg.get("Subject", ""))
        body = get_body(msg)

        # 무료체험 메일은 건너뜀
        if "무료체험" in subject:
            mail.store(eid, "+FLAGS", "\\Seen")
            continue

        print(f"\n[Gmail] 처리: {subject}")
        orders = parse_order_email(body)
        if not orders:
            print("  → 파싱 실패, 건너뜀 (미읽음 유지)")
            continue

        all_ok = True
        for order in orders:
            result = place_order(order)
            if result.get("success"):
                dm = order.get("delivery_method", "이메일")
                dc = order.get("delivery_contact", "")
                print(f"  ✅ {order['product']} → FL 주문 완료 [{dm}: {dc}]: {result.get('url')}")
            else:
                print(f"  ❌ {order['product']} → 실패: {result.get('error')}")
                all_ok = False

        if all_ok:
            mail.store(eid, "+FLAGS", "\\Seen")
            print("  → 메일 읽음 처리 완료")
        else:
            print("  → 일부 실패, 메일 미읽음 유지 (다음 실행 시 재처리)")

    mail.close()
    mail.logout()


if __name__ == "__main__":
    run()
