"""
Solapi SMS 알림 모듈
주문 접수, PDF 발송 완료 등 이벤트를 폰 문자로 전송
"""
import os, hmac, hashlib, datetime, random, string, requests, json

API_KEY    = os.environ.get("SOLAPI_API_KEY", "")
API_SECRET = os.environ.get("SOLAPI_API_SECRET", "")
FROM_NUM   = os.environ.get("SOLAPI_FROM", os.environ.get("NOTIFY_PHONE", ""))
TO_NUM     = os.environ.get("NOTIFY_PHONE", "")


def _auth_header():
    date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    salt = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        (date + salt).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Authorization": f"HMAC-SHA256 apiKey={API_KEY}, date={date}, salt={salt}, signature={signature}",
        "Content-Type": "application/json",
    }


def send_sms(text: str, to: str = "") -> bool:
    if not all([API_KEY, API_SECRET, FROM_NUM]):
        print("⚠️  Solapi 미설정 — SMS 건너뜀")
        return False
    to = to or TO_NUM
    if not to:
        print("⚠️  수신 번호 미설정")
        return False

    payload = {
        "message": {
            "to": to.replace("-", ""),
            "from": FROM_NUM.replace("-", ""),
            "text": text[:80],  # SMS 80바이트 이내
        }
    }
    try:
        res = requests.post(
            "https://api.solapi.com/messages/v4/send",
            headers=_auth_header(),
            json=payload,
            timeout=10,
        )
        data = res.json()
        if res.status_code == 200 and data.get("groupId"):
            print(f"✅ SMS 발송 완료 → {to}")
            return True
        else:
            print(f"❌ SMS 실패: {data}")
            return False
    except Exception as e:
        print(f"❌ SMS 예외: {e}")
        return False


if __name__ == "__main__":
    # 테스트
    send_sms("[사주마루] SMS 알림 테스트 완료")
