"""
Twitter/X 자동 포스팅 (Twitter API v2)
필요 GitHub Secrets (계정별 prefix):
  SM_TWITTER_API_KEY, SM_TWITTER_API_SECRET
  SM_TWITTER_ACCESS_TOKEN, SM_TWITTER_ACCESS_TOKEN_SECRET
  (SM/UN/S77 prefix)
"""
import os, json, sys, hmac, hashlib, base64, time, urllib.parse, requests
from pathlib import Path

# ── 환경 로드 ─────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm").upper()

API_KEY = os.environ.get(f"{ACCOUNT_ID}_TWITTER_API_KEY", "")
API_SECRET = os.environ.get(f"{ACCOUNT_ID}_TWITTER_API_SECRET", "")
ACCESS_TOKEN = os.environ.get(f"{ACCOUNT_ID}_TWITTER_ACCESS_TOKEN", "")
ACCESS_TOKEN_SECRET = os.environ.get(f"{ACCOUNT_ID}_TWITTER_ACCESS_TOKEN_SECRET", "")

if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
    print(f"⚠️  Twitter API 미설정 ({ACCOUNT_ID}) — 건너뜀")
    sys.exit(0)

# ── meta.json 로드 ────────────────────────────────────────────
meta_path = Path(__file__).parent / "sns_output" / ACCOUNT_ID.lower() / "meta.json"
if not meta_path.exists():
    meta_path = Path(__file__).parent / "sns_output" / "meta.json"

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
tweet_text = content.get("twitter_post", "")
if not tweet_text:
    hook = content.get("hook", "")
    main = content.get("main_text", "").split("\n")[0] if content.get("main_text") else ""
    tags = content.get("hashtags", "#사주 #운세")[:50]
    tweet_text = f"{hook}\n\n{main}\n\n{tags}"

tweet_text = tweet_text[:280]

# ── OAuth 1.0a 서명 ───────────────────────────────────────────
def make_oauth_header(method: str, url: str, params: dict) -> str:
    oauth = {
        "oauth_consumer_key": API_KEY,
        "oauth_nonce": base64.b64encode(os.urandom(16)).decode().replace("=","").replace("/","").replace("+","")[:32],
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": ACCESS_TOKEN,
        "oauth_version": "1.0",
    }
    all_params = {**params, **oauth}
    sorted_params = "&".join(f"{urllib.parse.quote(str(k),'')  }={urllib.parse.quote(str(v),'')}" for k, v in sorted(all_params.items()))
    base = f"{method.upper()}&{urllib.parse.quote(url,'')}&{urllib.parse.quote(sorted_params,'')}"
    key = f"{urllib.parse.quote(API_SECRET,'')}&{urllib.parse.quote(ACCESS_TOKEN_SECRET,'')}"
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    header = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(str(v),"")}"' for k, v in sorted(oauth.items()))
    return header

# ── 미디어 업로드 (v1.1) ─────────────────────────────────────
def upload_media(image_path: str) -> str | None:
    try:
        url = "https://upload.twitter.com/1.1/media/upload.json"
        with open(image_path, "rb") as f:
            data = f.read()
        import base64 as b64
        encoded = b64.b64encode(data).decode()

        auth_header = make_oauth_header("POST", url, {})
        resp = requests.post(
            url,
            headers={"Authorization": auth_header},
            data={"media_data": encoded},
        )
        if resp.status_code == 200:
            media_id = resp.json().get("media_id_string", "")
            print(f"  미디어 업로드 완료: {media_id}")
            return media_id
        else:
            print(f"  미디어 업로드 실패: {resp.status_code}")
    except Exception as e:
        print(f"  미디어 업로드 오류: {e}")
    return None

# ── 트윗 게시 ─────────────────────────────────────────────────
url = "https://api.twitter.com/2/tweets"

payload: dict = {"text": tweet_text}

# 이미지 첨부
image_path = meta.get("image_card", "")
if image_path and Path(image_path).exists():
    media_id = upload_media(image_path)
    if media_id:
        payload["media"] = {"media_ids": [media_id]}

auth_header = make_oauth_header("POST", url, {})
resp = requests.post(
    url,
    headers={
        "Authorization": auth_header,
        "Content-Type": "application/json",
    },
    json=payload,
)

if resp.status_code in (200, 201):
    tweet_id = resp.json().get("data", {}).get("id", "")
    print(f"✅ Twitter 포스팅 완료: {tweet_id}")
    meta["twitter_posted"] = True
    meta["twitter_id"] = tweet_id
else:
    print(f"❌ Twitter 포스팅 실패: {resp.status_code} {resp.text[:200]}")
    meta["twitter_posted"] = False

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
