#!/usr/bin/env python3
"""
월간/주기 주문 분석 보고서
매달 1일, 7일, 15일, 30일에 GitHub Actions로 실행
- 전체 주문 현황, 계정별/상품별 매출, 기간 통계
- 신정희에게 이메일 + SMS 발송
"""
import os, sys, json, smtplib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, str(Path(__file__).parent))

_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from kakao_notify import _kakao_or_sms, _auth_header, NOTIFY_PHONE, NOTIFY_EMAIL

GMAIL_USER         = os.getenv("GMAIL_USER", "sajumaru7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

ORDERS_FILE = Path(__file__).parent / "orders_data" / "orders.json"

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

ACCOUNT_NAMES = {
    "sm":  "사주마루",
    "un":  "사주보는언니",
    "s77": "사주마루77",
}

STATUS_KO = {
    "pending":    "주문접수",
    "paid":       "입금확인",
    "processing": "분석중",
    "verified":   "발송전확인",
    "delivered":  "발송완료",
    "done":       "완료",
    "cancelled":  "취소",
    "error":      "오류",
}


def load_orders() -> list:
    if not ORDERS_FILE.exists():
        return []
    try:
        return json.loads(ORDERS_FILE.read_text())
    except Exception:
        return []


def period_label(today: datetime) -> tuple[str, datetime]:
    """오늘 날짜 기준 보고 기간 결정"""
    day = today.day
    if day == 1:
        # 전월 전체
        first_day = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day  = today.replace(day=1) - timedelta(days=1)
        label = f"{first_day.strftime('%Y년 %m월')} 전체 결산"
    elif day == 7:
        first_day = today.replace(day=1)
        last_day  = today
        label = f"이번 달 1~7일"
    elif day == 15:
        first_day = today.replace(day=1)
        last_day  = today
        label = f"이번 달 1~15일"
    else:  # 30
        first_day = today.replace(day=1)
        last_day  = today
        label = f"이번 달 1~30일"
    return label, first_day, last_day


def analyze(orders: list, since: datetime, until: datetime) -> dict:
    filtered = []
    for o in orders:
        created = o.get("created_at", "")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(created[:19])
        except ValueError:
            continue
        if since <= dt <= until:
            filtered.append(o)

    total = len(filtered)
    by_status = defaultdict(int)
    by_account = defaultdict(int)
    by_product = defaultdict(int)
    revenue_by_account = defaultdict(int)
    revenue_total = 0

    for o in filtered:
        st  = o.get("status", "pending")
        acct = o.get("account", "sm")
        prod = o.get("product", "")
        by_status[st]   += 1
        by_account[acct] += 1
        by_product[prod] += 1
        if st not in ("cancelled", "error"):
            price = PRODUCT_PRICES.get(prod, 0)
            revenue_by_account[acct] += price
            revenue_total += price

    return {
        "total": total,
        "filtered": filtered,
        "by_status": dict(by_status),
        "by_account": dict(by_account),
        "by_product": dict(by_product),
        "revenue_by_account": dict(revenue_by_account),
        "revenue_total": revenue_total,
    }


def build_html(label: str, data: dict, since: datetime, until: datetime) -> str:
    rows_status = "".join(
        f"<tr><td>{STATUS_KO.get(k, k)}</td><td style='text-align:right'>{v}건</td></tr>"
        for k, v in sorted(data["by_status"].items(), key=lambda x: -x[1])
    )
    rows_account = "".join(
        f"<tr><td>{ACCOUNT_NAMES.get(k, k)}</td>"
        f"<td style='text-align:right'>{v}건</td>"
        f"<td style='text-align:right'>{data['revenue_by_account'].get(k, 0):,}원</td></tr>"
        for k, v in sorted(data["by_account"].items(), key=lambda x: -x[1])
    )
    rows_product = "".join(
        f"<tr><td>{k}</td><td style='text-align:right'>{v}건</td>"
        f"<td style='text-align:right'>{PRODUCT_PRICES.get(k, 0) * v:,}원</td></tr>"
        for k, v in sorted(data["by_product"].items(), key=lambda x: -x[1])
    )
    period_str = f"{since.strftime('%Y.%m.%d')} ~ {until.strftime('%Y.%m.%d')}"

    return f"""
<html><body style="font-family:'Noto Sans KR',sans-serif;max-width:600px;margin:0 auto;background:#f5f5f5;padding:20px">
<div style="background:#1a1a2e;color:#e8d5b7;border-radius:16px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#4a0080,#1a1a2e);padding:24px 28px">
    <h1 style="margin:0;font-size:22px;color:#ffd700">🔮 사주마루 주문 분석 보고서</h1>
    <p style="margin:6px 0 0;color:#aaa;font-size:14px">{label} | {period_str}</p>
  </div>
  <div style="padding:24px 28px">

    <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap">
      <div style="flex:1;min-width:120px;background:#0d0d1a;border-radius:10px;padding:16px;text-align:center">
        <div style="font-size:32px;font-weight:700;color:#ffd700">{data['total']}</div>
        <div style="font-size:12px;color:#888;margin-top:4px">총 주문</div>
      </div>
      <div style="flex:1;min-width:120px;background:#0d0d1a;border-radius:10px;padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:700;color:#7fff7f">{data['revenue_total']:,}</div>
        <div style="font-size:12px;color:#888;margin-top:4px">예상 매출 (원)</div>
      </div>
      <div style="flex:1;min-width:120px;background:#0d0d1a;border-radius:10px;padding:16px;text-align:center">
        <div style="font-size:32px;font-weight:700;color:#87ceeb">{data['by_status'].get('delivered', 0) + data['by_status'].get('done', 0)}</div>
        <div style="font-size:12px;color:#888;margin-top:4px">발송 완료</div>
      </div>
    </div>

    <h3 style="color:#ffd700;margin:0 0 8px">계정별 현황</h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px;font-size:14px">
      <tr style="background:#0d0d1a;color:#aaa">
        <th style="padding:8px 12px;text-align:left">계정</th>
        <th style="padding:8px 12px;text-align:right">주문수</th>
        <th style="padding:8px 12px;text-align:right">매출</th>
      </tr>
      {rows_account}
    </table>

    <h3 style="color:#ffd700;margin:0 0 8px">상태별 현황</h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px;font-size:14px">
      <tr style="background:#0d0d1a;color:#aaa">
        <th style="padding:8px 12px;text-align:left">상태</th>
        <th style="padding:8px 12px;text-align:right">건수</th>
      </tr>
      {rows_status}
    </table>

    <h3 style="color:#ffd700;margin:0 0 8px">상품별 현황</h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px;font-size:14px">
      <tr style="background:#0d0d1a;color:#aaa">
        <th style="padding:8px 12px;text-align:left">상품</th>
        <th style="padding:8px 12px;text-align:right">건수</th>
        <th style="padding:8px 12px;text-align:right">금액</th>
      </tr>
      {rows_product}
    </table>

    <p style="color:#555;font-size:12px;margin-top:16px;text-align:center">
      자동 생성 보고서 · sajumaru7@gmail.com
    </p>
  </div>
</div>
</body></html>
"""


def build_sms(label: str, data: dict) -> str:
    acct_lines = "\n".join(
        f"  {ACCOUNT_NAMES.get(k, k)}: {v}건 / {data['revenue_by_account'].get(k, 0):,}원"
        for k, v in sorted(data["by_account"].items(), key=lambda x: -x[1])
    )
    return (
        f"[사주마루] {label} 보고\n"
        f"총 {data['total']}건 / {data['revenue_total']:,}원\n"
        f"{acct_lines}\n"
        f"발송완료: {data['by_status'].get('delivered', 0) + data['by_status'].get('done', 0)}건"
    )


def send_report_email(subject: str, html_body: str):
    if not GMAIL_APP_PASSWORD or not NOTIFY_EMAIL:
        print("[보고서] 이메일 미설정 — 건너뜀")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.send_message(msg)
        print(f"  [보고서] 이메일 발송: {NOTIFY_EMAIL}")
    except Exception as e:
        print(f"  [보고서] 이메일 실패: {e}")


def run():
    today  = datetime.now()
    label, since, until = period_label(today)

    orders = load_orders()
    print(f"[월간보고] 전체 주문: {len(orders)}건")
    print(f"[월간보고] 분석 기간: {since.date()} ~ {until.date()} ({label})")

    data = analyze(orders, since, until)
    print(f"[월간보고] 기간 내 주문: {data['total']}건 / 예상매출: {data['revenue_total']:,}원")

    html    = build_html(label, data, since, until)
    sms_txt = build_sms(label, data)
    subject = f"[사주마루] {label} 주문 보고서 — {today.strftime('%Y.%m.%d')}"

    send_report_email(subject, html)

    if NOTIFY_PHONE:
        _kakao_or_sms(NOTIFY_PHONE, sms_txt[:300])
        print(f"  [보고서] SMS 발송: {NOTIFY_PHONE}")

    print("[완료] 월간 보고서 발송 완료")


if __name__ == "__main__":
    run()
