#!/usr/bin/env python3
"""
Gmail에서 사주마루/언니/77 주문 이메일을 읽어 FL에 자동 주문
- 계정 자동 감지 (제목의 [사주마루], [사주보는언니], [사주마루77])
- orders_db에 주문 저장
- kakao_notify로 관리자+고객 알림
"""
import imaplib, email, os, re, sys
from email.header import decode_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# .env 자동 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from orders_db   import create_order, update_status, update_field, find_by_email_uid
from kakao_notify import notify_new_order, notify_error, send_customer_guide

GMAIL_USER         = os.getenv("GMAIL_USER", "sajumaru7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
OPERATOR_EMAIL     = "sajumaru7@gmail.com"

# 제목 → 계정 ID 매핑
SUBJECT_ACCOUNT_MAP = {
    "[사주마루77]":   "s77",
    "[사주보는언니]":  "un",
    "[사주마루]":      "sm",
}

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
    "도화살 전문분석", "이런 사람 만나지 마라", "친구·우정운",
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


def detect_account(subject: str) -> str:
    for marker, acct in SUBJECT_ACCOUNT_MAP.items():
        if marker in subject:
            return acct
    return "sm"


def parse_order_email(body: str, account: str = "sm", email_uid: str = "") -> list:
    lines = body.splitlines()

    name    = get_field(lines, "성함")
    birth_raw = get_field(lines, "생년월일")
    gender  = get_field(lines, "성별") or "여성"
    time_raw = get_field(lines, "시간") or get_field(lines, "태어난 시간")
    delivery_method = get_field(lines, "전달 방법") or "이메일"
    contact = get_field(lines, "전달 받을 곳") or get_field(lines, "연락처")

    if not name or not birth_raw:
        return []

    cal_type = "음력" if "(음력)" in birth_raw else "양력"
    birth_clean = birth_raw.replace("(음력)", "").strip()
    m = re.match(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", birth_clean)
    if not m:
        return []
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))

    hour = None
    if time_raw and "모름" not in time_raw:
        for key, val in TIME_MAP.items():
            if key in time_raw:
                hour = val
                break

    # 신청 상품 파싱
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

    # 연락처가 이메일이면 customer_email로 사용, 아니면 운영자 이메일
    cust_email = contact.strip() if contact and "@" in contact else OPERATOR_EMAIL

    return [
        {
            "account":          account,
            "name":             name,
            "gender":           gender,
            "cal_type":         cal_type,
            "year":             year,
            "month":            month,
            "day":              day,
            "hour":             hour,
            "minute":           0,
            "product":          p,
            "customer_email":   cust_email,
            "delivery_method":  delivery_method,
            "delivery_contact": contact,
            "email_uid":        email_uid,
        }
        for p in products
    ]


def run():
    if not GMAIL_APP_PASSWORD:
        print("[ERROR] GMAIL_APP_PASSWORD 없음")
        sys.exit(1)

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    _, ids = mail.search(None, 'UNSEEN')
    all_unseen = [i for i in ids[0].split() if i]

    # 사주 브랜드 주문 이메일만 필터
    email_ids = []
    for eid in all_unseen:
        _, hdr = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
        raw_subj = hdr[0][1] if hdr and hdr[0] else b""
        subj = decode_str(email.message_from_bytes(raw_subj).get("Subject", ""))
        if any(k in subj for k in SUBJECT_ACCOUNT_MAP):
            email_ids.append((eid, subj))

    print(f"[Gmail] 미읽은 주문 메일: {len(email_ids)}건")

    if not email_ids:
        mail.logout()
        return

    from saju_analysis import process_order_with_analysis

    for eid, subject in email_ids:
        # 무료체험 스킵
        if "무료체험" in subject:
            mail.store(eid, "+FLAGS", "\\Seen")
            continue

        _, data = mail.fetch(eid, "(RFC822)")
        msg  = email.message_from_bytes(data[0][1])
        body = get_body(msg)

        account = detect_account(subject)
        print(f"\n[주문] {subject} → 계정: {account}")

        orders = parse_order_email(body, account=account, email_uid=str(eid.decode() if isinstance(eid, bytes) else eid))
        if not orders:
            print("  → 파싱 실패 (미읽음 유지)")
            continue

        all_ok = True
        for order in orders:
            # 중복 주문 방지
            existing = find_by_email_uid(order["email_uid"]) if order.get("email_uid") else None
            if existing:
                print(f"  ⚠️ 이미 처리된 주문 #{existing['order_id']} 건너뜀")
                continue

            # DB에 주문 저장
            oid = create_order(order)
            print(f"  📋 주문 저장: #{oid} {order['name']} / {order['product']}")

            # 고객 안내 메시지 즉시 발송
            send_customer_guide(order, oid)

            # 관리자 + 고객 알림
            notify_new_order(order, oid)

            # FL 주문 + AI 분석
            try:
                update_status(oid, "processing", "FL 주문 시작")
                results = process_order_with_analysis(order)
                fl_res  = results.get("fl", {})
                ai_res  = results.get("analysis", {})

                if fl_res.get("success"):
                    update_field(oid,
                        fl_url=fl_res.get("url", ""),
                        fl_submitted_at=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    dm = order.get("delivery_method", "이메일")
                    dc = order.get("delivery_contact", "")
                    ai_note = "AI분석발송" if ai_res.get("success") else "AI분석스킵"
                    print(f"  ✅ #{oid} {order['product']} → FL완료 + {ai_note} [{dm}: {dc}]")
                else:
                    err = fl_res.get("error", "알수없음")
                    update_status(oid, "error", err)
                    notify_error(order, oid, err)
                    print(f"  ❌ #{oid} {order['product']} → FL실패: {err}")
                    all_ok = False

            except Exception as e:
                update_status(oid, "error", str(e))
                notify_error(order, oid, str(e))
                print(f"  ❌ 예외: {e}")
                all_ok = False

        if all_ok:
            mail.store(eid, "+FLAGS", "\\Seen")
            print("  → 메일 읽음 처리")
        else:
            print("  → 일부 실패, 미읽음 유지")

    mail.close()
    mail.logout()

    # 주문 처리 완료 후 소셜 미디어 포스팅 트리거 (처리된 주문이 있을 때만)
    if email_ids:
        _trigger_social_posting()


def _trigger_social_posting():
    """주문 처리 후 소셜 미디어 포스팅 트리거 (오케스트레이터 호출)"""
    import subprocess, datetime as _dt
    try:
        scripts_dir = Path(__file__).parent
        orchestrator = scripts_dir / "orchestrator.py"
        if not orchestrator.exists():
            print("[소셜] orchestrator.py 없음 — 건너뜀")
            return

        # 현재 KST 시간 기준으로 적절한 시간대 선택
        now_kst = _dt.datetime.utcnow() + _dt.timedelta(hours=9)
        hour = now_kst.hour
        # 낮 시간대(6~22시)에만 포스팅
        if not (6 <= hour <= 22):
            print(f"[소셜] 야간({hour}시) — 포스팅 건너뜀")
            return

        print(f"\n[소셜] 주문 처리 완료 → 소셜 포스팅 트리거 ({hour}시)")
        result = subprocess.run(
            [sys.executable, str(orchestrator)],
            env={**os.environ, "HOUR_KST": str(hour)},
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            print("[소셜] 포스팅 완료")
        else:
            print(f"[소셜] 포스팅 실패: {result.stderr[:200]}")
    except Exception as e:
        print(f"[소셜] 트리거 오류 (무시): {e}")


if __name__ == "__main__":
    run()
