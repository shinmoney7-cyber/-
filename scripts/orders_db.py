"""
주문 DB — JSON 파일 기반 주문 이력 관리
scripts/orders_data/orders.json 에 저장 (gitignore 대상)
"""
import json, uuid, datetime
from pathlib import Path

_DB_PATH = Path(__file__).parent / "orders_data" / "orders.json"

# 주문 상태 흐름
# pending → paid → processing → verified → delivered → done
# 또는 → cancelled

STATUS_LABELS = {
    "pending":    "주문접수",
    "paid":       "입금확인",
    "processing": "사주분석중",
    "verified":   "발송전확인완료",
    "delivered":  "발송완료",
    "done":       "완료",
    "cancelled":  "취소",
    "error":      "오류",
}


def _load() -> dict:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _DB_PATH.exists():
        return {}
    try:
        return json.loads(_DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(db: dict):
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_order(order: dict) -> str:
    """새 주문 생성, order_id 반환"""
    db = _load()
    oid = str(uuid.uuid4())[:8].upper()
    db[oid] = {
        "order_id":        oid,
        "account":         order.get("account", "sm"),
        "status":          "pending",
        "created_at":      _now(),
        "updated_at":      _now(),
        "name":            order.get("name", ""),
        "gender":          order.get("gender", ""),
        "cal_type":        order.get("cal_type", "양력"),
        "year":            order.get("year"),
        "month":           order.get("month"),
        "day":             order.get("day"),
        "hour":            order.get("hour"),
        "minute":          order.get("minute", 0),
        "product":         order.get("product", ""),
        "delivery_method": order.get("delivery_method", "이메일"),
        "delivery_contact": order.get("delivery_contact", ""),
        "email_uid":       order.get("email_uid", ""),
        "paid":            False,
        "paid_at":         None,
        "fl_url":          None,
        "fl_submitted_at": None,
        "ai_analysis":     None,
        "pdf_path":        None,
        "delivered_at":    None,
        "claude_verified": False,
        "claude_verified_at": None,
        "claude_verify_note": "",
        "history":         [{"time": _now(), "event": "주문접수", "detail": order.get("product", "")}],
    }
    _save(db)
    return oid


def get_order(oid: str) -> dict | None:
    return _load().get(oid)


def list_orders(status: str = None, account: str = None) -> list:
    db = _load()
    orders = list(db.values())
    if status:
        orders = [o for o in orders if o.get("status") == status]
    if account:
        orders = [o for o in orders if o.get("account") == account]
    return sorted(orders, key=lambda o: o.get("created_at", ""), reverse=True)


def update_status(oid: str, status: str, detail: str = ""):
    db = _load()
    if oid not in db:
        return False
    db[oid]["status"] = status
    db[oid]["updated_at"] = _now()
    db[oid]["history"].append({"time": _now(), "event": STATUS_LABELS.get(status, status), "detail": detail})
    _save(db)
    return True


def update_field(oid: str, **kwargs):
    db = _load()
    if oid not in db:
        return False
    for k, v in kwargs.items():
        db[oid][k] = v
    db[oid]["updated_at"] = _now()
    _save(db)
    return True


def mark_paid(oid: str, detail: str = ""):
    db = _load()
    if oid not in db:
        return False
    db[oid]["paid"] = True
    db[oid]["paid_at"] = _now()
    db[oid]["status"] = "paid"
    db[oid]["updated_at"] = _now()
    db[oid]["history"].append({"time": _now(), "event": "입금확인", "detail": detail})
    _save(db)
    return True


def mark_claude_verified(oid: str, note: str = ""):
    db = _load()
    if oid not in db:
        return False
    db[oid]["claude_verified"] = True
    db[oid]["claude_verified_at"] = _now()
    db[oid]["claude_verify_note"] = note
    db[oid]["status"] = "verified"
    db[oid]["updated_at"] = _now()
    db[oid]["history"].append({"time": _now(), "event": "발송전확인완료", "detail": note})
    _save(db)
    return True


def mark_delivered(oid: str, method: str = "", contact: str = ""):
    db = _load()
    if oid not in db:
        return False
    db[oid]["delivered_at"] = _now()
    db[oid]["status"] = "delivered"
    db[oid]["updated_at"] = _now()
    db[oid]["history"].append({"time": _now(), "event": "발송완료", "detail": f"{method} → {contact}"})
    _save(db)
    return True


def find_by_email_uid(email_uid: str) -> dict | None:
    for o in _load().values():
        if o.get("email_uid") == str(email_uid):
            return o
    return None


def find_pending_for_name_product(name: str, product: str) -> dict | None:
    for o in list_orders():
        if o.get("name") == name and o.get("product") == product and o.get("status") in ("pending", "paid", "processing"):
            return o
    return None
